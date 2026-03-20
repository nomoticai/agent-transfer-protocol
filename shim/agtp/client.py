"""
AGTP Client.

Sends AGTP requests over HTTP using X-AGTP-* headers.
This is the shim layer -- when native AGTP transport exists,
replace the _send() method with a native AGTP transport call.
All AGTP semantics (headers, body, validation) remain unchanged.

Usage:
    from agtp import AGTPClient, AGTPRequest

    client = AGTPClient(
        base_url="http://localhost:8080",
        agent_id="agtp://research-bot.engineering.acme.agent",
        principal_id="chris@nomotic.ai",
        authority_scope="documents:query knowledge:query",
    )

    response = client.query(
        intent="Key limitations of HTTP for AI agent traffic",
        scope=["documents:research"],
        format="structured",
    )
    print(response.result)
"""

import json
import logging
from typing import Any, Optional

try:
    import requests
except ImportError:
    raise ImportError(
        "The 'requests' library is required for AGTPClient. "
        "Install it with: pip install requests"
    )

from .models import AGTPRequest, AGTPResponse, CONTENT_TYPE
from .methods import validate_method, validate_parameters, validate_scope
from .status import AGTPStatus
from .exceptions import (
    AGTPError, AGTPScopeViolation, AGTPUnauthorized,
    AGTPValidationError, AGTPDelegationFailure, AGTPAuthorityChainBroken,
)

logger = logging.getLogger("agtp.client")


class AGTPClient:
    """
    AGTP client that tunnels requests over HTTP.
    
    The shim maps AGTP headers to X-AGTP-* HTTP headers.
    When native AGTP transport is available, swap _send()
    for a native transport implementation.
    """

    def __init__(
        self,
        base_url: str,
        agent_id: str,
        principal_id: str,
        authority_scope: str,
        session_id: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        Initialise an AGTP client.

        Args:
            base_url:        Base URL of the AGTP server (HTTP shim endpoint)
            agent_id:        Canonical agent identifier, e.g. agtp://[id] or
                             agtp://name.department.org.agent
            principal_id:    Accountable human/org identifier
            authority_scope: Space-separated scope tokens,
                             e.g. "documents:query knowledge:learn"
            session_id:      Optional persistent session identifier.
                             Auto-generated if not provided.
            timeout:         Request timeout in seconds
            verify_ssl:      SSL certificate verification
        """
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.principal_id = principal_id
        self.authority_scope = authority_scope
        self.session_id = session_id
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._session = requests.Session()

    def _build_request(
        self,
        method: str,
        parameters: dict,
        context: dict = None,
        task_id: str = None,
        priority: str = "normal",
        ttl: int = None,
        delegation_chain: list = None,
    ) -> AGTPRequest:
        """Construct and validate an AGTPRequest."""
        validate_method(method)
        validate_parameters(method, parameters)
        validate_scope(method, self.authority_scope)

        return AGTPRequest(
            method=method,
            agent_id=self.agent_id,
            principal_id=self.principal_id,
            authority_scope=self.authority_scope,
            parameters=parameters,
            context=context or {},
            session_id=self.session_id,
            task_id=task_id,
            priority=priority,
            ttl=ttl,
            delegation_chain=delegation_chain,
        )

    def _send(self, request: AGTPRequest, path: str = "/agtp") -> AGTPResponse:
        """
        Send an AGTP request over HTTP (the shim transport).
        
        UPGRADE PATH: Replace this method with native AGTP transport
        when available. All AGTP semantics remain unchanged.
        """
        url = f"{self.base_url}{path}"
        headers = request.to_http_headers()
        body = json.dumps(request.to_dict())

        logger.debug(
            "AGTP %s -> %s [task=%s agent=%s]",
            request.method, url, request.task_id, request.agent_id,
        )

        try:
            http_response = self._session.post(
                url,
                data=body,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
        except requests.exceptions.Timeout:
            raise AGTPError(
                f"AGTP request timed out after {self.timeout}s",
                task_id=request.task_id,
            )
        except requests.exceptions.ConnectionError as e:
            raise AGTPError(
                f"AGTP connection failed: {e}",
                task_id=request.task_id,
            )

        response = AGTPResponse.from_http_response(http_response)
        self._handle_governance_signals(response, request)
        return response

    def _handle_governance_signals(
        self, response: AGTPResponse, request: AGTPRequest
    ) -> None:
        """
        Handle ATP-specific governance status codes.
        451, 550, and 551 are governance signals that MUST be logged.
        """
        if response.status == AGTPStatus.SCOPE_VIOLATION:
            logger.warning(
                "AGTP 451 Scope Violation [task=%s agent=%s scope='%s']",
                request.task_id, request.agent_id, request.authority_scope,
            )
            raise AGTPScopeViolation(
                requested_scope=request.authority_scope,
                declared_scope=request.authority_scope,
                task_id=request.task_id,
            )

        if response.status == AGTPStatus.DELEGATION_FAILURE:
            logger.error(
                "AGTP 550 Delegation Failure [task=%s]", request.task_id
            )
            raise AGTPDelegationFailure(
                f"Delegation failure for task {request.task_id}",
                task_id=request.task_id,
            )

        if response.status == AGTPStatus.AUTHORITY_CHAIN_BROKEN:
            logger.error(
                "AGTP 551 Authority Chain Broken [task=%s chain=%s]",
                request.task_id, request.delegation_chain,
            )
            raise AGTPAuthorityChainBroken(
                f"Authority chain broken for task {request.task_id}",
                task_id=request.task_id,
            )

        if response.status == AGTPStatus.UNAUTHORIZED:
            raise AGTPUnauthorized(
                f"Agent '{request.agent_id}' not authorised",
                task_id=request.task_id,
            )

    # -----------------------------------------------------------------------
    # Core method convenience wrappers
    # -----------------------------------------------------------------------

    def query(
        self,
        intent: str,
        scope: list = None,
        format: str = "structured",
        confidence_threshold: float = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """QUERY — semantic data retrieval."""
        params = {"intent": intent, "format": format}
        if scope:
            params["scope"] = scope
        if confidence_threshold is not None:
            params["confidence_threshold"] = confidence_threshold
        req = self._build_request("QUERY", params, context=context, **kwargs)
        return self._send(req)

    def summarize(
        self,
        source: str,
        length: str = "standard",
        focus: str = None,
        format: str = "prose",
        audience: str = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """SUMMARIZE — synthesize content."""
        params = {"source": source, "length": length, "format": format}
        if focus:
            params["focus"] = focus
        if audience:
            params["audience"] = audience
        req = self._build_request("SUMMARIZE", params, context=context, **kwargs)
        return self._send(req)

    def book(
        self,
        resource_id: str,
        principal_id: str,
        time_slot: str = None,
        quantity: int = None,
        options: dict = None,
        confirm_immediately: bool = True,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """BOOK — reserve a resource."""
        params = {
            "resource_id": resource_id,
            "principal_id": principal_id,
            "confirm_immediately": confirm_immediately,
        }
        if time_slot:
            params["time_slot"] = time_slot
        if quantity is not None:
            params["quantity"] = quantity
        if options:
            params["options"] = options
        req = self._build_request("BOOK", params, context=context, **kwargs)
        return self._send(req)

    def schedule(
        self,
        steps: list,
        trigger: str = "immediate",
        trigger_value: str = None,
        on_failure: str = "abort",
        notify: list = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """SCHEDULE — plan future actions."""
        params = {"steps": steps, "trigger": trigger, "on_failure": on_failure}
        if trigger_value:
            params["trigger_value"] = trigger_value
        if notify:
            params["notify"] = notify
        req = self._build_request("SCHEDULE", params, context=context, **kwargs)
        return self._send(req)

    def learn(
        self,
        content: Any,
        scope: str = "session",
        category: str = None,
        confidence: float = None,
        source: str = None,
        ttl_seconds: int = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """LEARN — update agent context."""
        params = {"content": content, "scope": scope}
        if category:
            params["category"] = category
        if confidence is not None:
            params["confidence"] = confidence
        if source:
            params["source"] = source
        if ttl_seconds is not None:
            params["ttl"] = ttl_seconds
        req = self._build_request("LEARN", params, context=context, **kwargs)
        return self._send(req)

    def delegate(
        self,
        target_agent_id: str,
        task: dict,
        authority_scope: str,
        delegation_token: str,
        callback: str = None,
        deadline: str = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """DELEGATE — transfer task to sub-agent."""
        params = {
            "target_agent_id": target_agent_id,
            "task": task,
            "authority_scope": authority_scope,
            "delegation_token": delegation_token,
        }
        if callback:
            params["callback"] = callback
        if deadline:
            params["deadline"] = deadline
        req = self._build_request("DELEGATE", params, context=context, **kwargs)
        return self._send(req)

    def collaborate(
        self,
        collaborators: list,
        objective: str,
        role_assignments: dict = None,
        coordination_model: str = "parallel",
        result_aggregation: str = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """COLLABORATE — coordinate peer agents."""
        params = {
            "collaborators": collaborators,
            "objective": objective,
            "coordination_model": coordination_model,
        }
        if role_assignments:
            params["role_assignments"] = role_assignments
        if result_aggregation:
            params["result_aggregation"] = result_aggregation
        req = self._build_request("COLLABORATE", params, context=context, **kwargs)
        return self._send(req)

    def confirm(
        self,
        target_id: str,
        status: str,
        reason: str = None,
        attestation: dict = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """CONFIRM — attest to a prior action."""
        params = {"target_id": target_id, "status": status}
        if reason:
            params["reason"] = reason
        if attestation:
            params["attestation"] = attestation
        req = self._build_request("CONFIRM", params, context=context, **kwargs)
        return self._send(req)

    def escalate(
        self,
        task_id: str,
        reason: str,
        context_data: dict,
        priority: str = "normal",
        recipient: str = None,
        deadline: str = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """
        ESCALATE — defer to human authority.
        
        ESCALATE is a first-class AGTP method, not an error code.
        An agent that escalates appropriately is functioning correctly.
        """
        params = {
            "task_id": task_id,
            "reason": reason,
            "context": context_data,
            "priority": priority,
        }
        if recipient:
            params["recipient"] = recipient
        if deadline:
            params["deadline"] = deadline
        req = self._build_request("ESCALATE", params, context=context, **kwargs)
        return self._send(req)

    def notify(
        self,
        recipient: str,
        content: Any,
        urgency: str = "informational",
        delivery_guarantee: str = "at_most_once",
        expiry: str = None,
        context: dict = None,
        **kwargs,
    ) -> AGTPResponse:
        """NOTIFY — push information asynchronously."""
        params = {
            "recipient": recipient,
            "content": content,
            "urgency": urgency,
            "delivery_guarantee": delivery_guarantee,
        }
        if expiry:
            params["expiry"] = expiry
        req = self._build_request("NOTIFY", params, context=context, **kwargs)
        return self._send(req)

    def close(self):
        """Close the underlying HTTP session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
