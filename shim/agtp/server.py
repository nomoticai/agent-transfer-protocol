"""
AGTP Server (HTTP Shim).

Receives HTTP requests with X-AGTP-* headers, extracts the AGTP
request, validates it, routes it to the appropriate method handler,
and returns an AGTP response.

Usage:
    from agtp import AGTPServer

    server = AGTPServer(agent_id="agtp://my-service.acme.agent")

    @server.handler("QUERY")
    def handle_query(request):
        # request is an AGTPRequest
        results = my_search(request.parameters["intent"])
        return {"results": results}

    @server.handler("SUMMARIZE")
    def handle_summarize(request):
        summary = my_summarizer(request.parameters["source"])
        return {"summary": summary, "confidence": 0.92}

    # Run the Flask development server
    server.run(host="0.0.0.0", port=8080)

    # Or get the Flask app for production WSGI deployment
    app = server.app
"""

import json
import logging
import time
from typing import Any, Callable, Optional
from functools import wraps

try:
    from flask import Flask, request as flask_request, jsonify, Response
except ImportError:
    raise ImportError(
        "Flask is required for AGTPServer. "
        "Install it with: pip install flask"
    )

from .models import AGTPRequest, AGTPResponse, CONTENT_TYPE
from .methods import validate_method, validate_parameters, validate_scope, CORE_METHODS
from .status import AGTPStatus
from .exceptions import (
    AGTPError, AGTPScopeViolation, AGTPValidationError,
    AGTPUnauthorized,
)

logger = logging.getLogger("agtp.server")


class AGTPServer:
    """
    AGTP server that receives requests over HTTP and routes them
    to registered method handlers.
    
    The server validates AGTP headers and method parameters before
    invoking handlers, so handlers can focus on business logic.
    """

    def __init__(
        self,
        agent_id: str,
        path: str = "/agtp",
        require_agent_id: bool = False,
        trusted_agents: list = None,
        log_all_requests: bool = True,
    ):
        """
        Initialise an AGTP server.

        Args:
            agent_id:          This server's agent identifier
            path:              URL path to mount the AGTP endpoint on
            require_agent_id:  If True, reject requests with no Agent-ID
            trusted_agents:    If set, only accept requests from these Agent-IDs
            log_all_requests:  Log every incoming AGTP request
        """
        self.agent_id = agent_id
        self.path = path
        self.require_agent_id = require_agent_id
        self.trusted_agents = set(trusted_agents) if trusted_agents else None
        self.log_all_requests = log_all_requests
        self._handlers: dict[str, Callable] = {}
        self.app = self._create_app()

    def _create_app(self) -> Flask:
        app = Flask("agtp_server")

        @app.route(self.path, methods=["POST"])
        def agtp_endpoint():
            return self._handle_request()

        @app.route("/agtp/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "ok",
                "agent_id": self.agent_id,
                "registered_methods": sorted(self._handlers.keys()),
                "version": "AGTP/1.0",
            })

        return app

    def handler(self, method: str):
        """
        Decorator to register a method handler.

        The decorated function receives an AGTPRequest and should
        return a dict (which becomes the 'result' in the response),
        or an AGTPResponse for full control over the response.

        Example:
            @server.handler("QUERY")
            def handle_query(request):
                return {"answer": "42", "confidence": 1.0}
        """
        method = method.upper()

        def decorator(func: Callable):
            self._handlers[method] = func
            logger.info("Registered AGTP handler for %s", method)
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def _handle_request(self) -> Response:
        """Main request handling pipeline."""
        start_time = time.time()

        # ── 1. Parse headers ─────────────────────────────────────────────
        headers = dict(flask_request.headers)
        content_type = headers.get("Content-Type", "")

        if CONTENT_TYPE not in content_type and content_type:
            # Be lenient about content-type during shim period
            logger.debug("Non-AGTP content type: %s", content_type)

        try:
            body = flask_request.get_json(force=True, silent=True) or {}
        except Exception:
            body = {}

        # ── 2. Build AGTPRequest ──────────────────────────────────────────
        try:
            agtp_request = AGTPRequest.from_http_headers(headers, body)
        except Exception as e:
            return self._error_response(
                AGTPStatus.BAD_REQUEST,
                f"Could not parse AGTP request: {e}",
                task_id=body.get("task_id"),
            )

        # ── 3. Log ────────────────────────────────────────────────────────
        if self.log_all_requests:
            logger.info(
                "AGTP %s [task=%s agent=%s principal=%s scope='%s']",
                agtp_request.method,
                agtp_request.task_id,
                agtp_request.agent_id,
                agtp_request.principal_id,
                agtp_request.authority_scope,
            )

        # ── 4. Identity checks ────────────────────────────────────────────
        if self.require_agent_id and not agtp_request.agent_id:
            return self._error_response(
                AGTPStatus.UNAUTHORIZED,
                "Agent-ID header is required",
                task_id=agtp_request.task_id,
            )

        if self.trusted_agents and agtp_request.agent_id not in self.trusted_agents:
            logger.warning(
                "AGTP 401 Untrusted agent: %s", agtp_request.agent_id
            )
            return self._error_response(
                AGTPStatus.UNAUTHORIZED,
                f"Agent '{agtp_request.agent_id}' is not in the trusted agent list",
                task_id=agtp_request.task_id,
            )

        # ── 5. Method validation ──────────────────────────────────────────
        try:
            validate_method(agtp_request.method)
            validate_parameters(agtp_request.method, agtp_request.parameters)
        except AGTPValidationError as e:
            return self._error_response(
                AGTPStatus.BAD_REQUEST,
                str(e),
                task_id=agtp_request.task_id,
            )

        # ── 6. Scope enforcement ──────────────────────────────────────────
        try:
            validate_scope(
                agtp_request.method,
                agtp_request.authority_scope,
                task_id=agtp_request.task_id,
            )
        except AGTPScopeViolation as e:
            # 451 MUST be logged
            logger.warning(
                "AGTP 451 Scope Violation [task=%s agent=%s method=%s scope='%s']",
                agtp_request.task_id,
                agtp_request.agent_id,
                agtp_request.method,
                agtp_request.authority_scope,
            )
            return self._error_response(
                AGTPStatus.SCOPE_VIOLATION,
                str(e),
                task_id=agtp_request.task_id,
            )

        # ── 7. Route to handler ───────────────────────────────────────────
        handler = self._handlers.get(agtp_request.method)
        if not handler:
            return self._error_response(
                AGTPStatus.NOT_FOUND,
                f"No handler registered for method {agtp_request.method}. "
                f"Registered methods: {sorted(self._handlers.keys())}",
                task_id=agtp_request.task_id,
            )

        # ── 8. Invoke handler ─────────────────────────────────────────────
        try:
            result = handler(agtp_request)
        except AGTPError as e:
            # Re-raise AGTP errors as proper responses
            if AGTPStatus.is_governance_signal(e.status_code):
                logger.warning(
                    "AGTP %d %s [task=%s]",
                    e.status_code,
                    AGTPStatus.name(e.status_code),
                    agtp_request.task_id,
                )
            return self._error_response(
                e.status_code,
                str(e),
                task_id=agtp_request.task_id,
            )
        except Exception as e:
            logger.exception(
                "AGTP handler error for %s [task=%s]",
                agtp_request.method, agtp_request.task_id,
            )
            return self._error_response(
                AGTPStatus.SERVER_ERROR,
                f"Handler error: {e}",
                task_id=agtp_request.task_id,
            )

        # ── 9. Build response ─────────────────────────────────────────────
        if isinstance(result, AGTPResponse):
            agtp_response = result
        else:
            agtp_response = AGTPResponse(
                status=AGTPStatus.OK,
                task_id=agtp_request.task_id,
                result=result if isinstance(result, dict) else {"value": result},
                server_agent_id=self.agent_id,
            )

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "AGTP %s -> %d [task=%s %dms]",
            agtp_request.method,
            agtp_response.status,
            agtp_request.task_id,
            elapsed_ms,
        )

        return self._build_http_response(agtp_response)

    def _build_http_response(self, agtp_response: AGTPResponse) -> Response:
        """Convert an AGTPResponse to an HTTP response."""
        headers = agtp_response.to_http_headers()
        body = json.dumps(agtp_response.to_dict())

        # Map AGTP status to HTTP status
        # 451, 550, 551 are ATP-specific — map to 400/500 range for HTTP
        http_status = agtp_response.status
        if http_status == AGTPStatus.SCOPE_VIOLATION:
            http_status = 400  # HTTP doesn't have 451 with this meaning
        elif http_status in (AGTPStatus.DELEGATION_FAILURE,
                             AGTPStatus.AUTHORITY_CHAIN_BROKEN):
            http_status = 502  # Bad Gateway for delegation failures

        response = Response(body, status=http_status, headers=headers)
        return response

    def _error_response(
        self,
        status: int,
        message: str,
        task_id: str = None,
    ) -> Response:
        """Build a standard AGTP error response."""
        agtp_response = AGTPResponse(
            status=status,
            task_id=task_id or "unknown",
            result={"error": message, "status_name": AGTPStatus.name(status)},
            server_agent_id=self.agent_id,
        )
        return self._build_http_response(agtp_response)

    def run(self, host: str = "127.0.0.1", port: int = 8080, debug: bool = False):
        """Run the development server. Use a WSGI server for production."""
        logger.info(
            "Starting AGTP shim server on %s:%d (agent_id=%s)",
            host, port, self.agent_id,
        )
        logger.info(
            "Registered method handlers: %s",
            sorted(self._handlers.keys()),
        )
        self.app.run(host=host, port=port, debug=debug)
