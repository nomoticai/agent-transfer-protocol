"""
AGTP Request and Response models.
These represent AGTP protocol messages independent of transport.
"""

from dataclasses import dataclass, field
from typing import Any, Optional
import time
import uuid


AGTP_VERSION = "AGTP/1.0"
CONTENT_TYPE = "application/agtp+json"


@dataclass
class AGTPRequest:
    """
    Represents an AGTP request message.
    
    In the shim layer, this is transported over HTTP with
    X-AGTP-* headers. When native AGTP transport exists,
    these fields map directly to protocol headers.
    """
    method: str                          # QUERY, SUMMARIZE, BOOK, etc.
    agent_id: str                        # Canonical 256-bit agent identifier
    principal_id: str                    # Accountable human/org identifier
    authority_scope: str                 # Space-separated scope tokens
    parameters: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    delegation_chain: Optional[list] = None
    priority: str = "normal"            # critical, normal, background
    ttl: Optional[int] = None           # Max response latency ms
    version: str = AGTP_VERSION

    def __post_init__(self):
        # Auto-generate task_id and session_id if not provided
        if not self.task_id:
            self.task_id = f"task-{uuid.uuid4().hex[:12]}"
        if not self.session_id:
            self.session_id = f"sess-{uuid.uuid4().hex[:12]}"
        # Normalise method to uppercase
        self.method = self.method.upper()

    def to_dict(self) -> dict:
        """Serialise to AGTP JSON body."""
        body = {
            "method": self.method,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "parameters": self.parameters,
            "context": self.context,
        }
        return body

    def to_http_headers(self) -> dict:
        """
        Map AGTP headers to HTTP X-AGTP-* headers for shim transport.
        When native AGTP transport is available, these become
        first-class protocol headers.
        """
        headers = {
            "X-AGTP-Version":        self.version,
            "X-AGTP-Method":         self.method,
            "X-AGTP-Agent-ID":       self.agent_id,
            "X-AGTP-Principal-ID":   self.principal_id,
            "X-AGTP-Authority-Scope": self.authority_scope,
            "X-AGTP-Session-ID":     self.session_id,
            "X-AGTP-Task-ID":        self.task_id,
            "X-AGTP-Priority":       self.priority,
            "Content-Type":          CONTENT_TYPE,
        }
        if self.ttl:
            headers["X-AGTP-TTL"] = str(self.ttl)
        if self.delegation_chain:
            headers["X-AGTP-Delegation-Chain"] = ",".join(self.delegation_chain)
        return headers

    @classmethod
    def from_http_headers(cls, headers: dict, body: dict) -> "AGTPRequest":
        """
        Reconstruct an AGTPRequest from HTTP X-AGTP-* headers.
        Used on the server side of the shim.
        Handles case-insensitive header lookup (Flask lowercases headers).
        """
        # Build case-insensitive lookup
        h = {k.upper(): v for k, v in headers.items()}

        delegation_chain = None
        if h.get("X-AGTP-DELEGATION-CHAIN"):
            delegation_chain = h["X-AGTP-DELEGATION-CHAIN"].split(",")

        # Method falls back to body if header missing
        method = h.get("X-AGTP-METHOD") or body.get("method", "")

        return cls(
            method=method,
            agent_id=h.get("X-AGTP-AGENT-ID", ""),
            principal_id=h.get("X-AGTP-PRINCIPAL-ID", ""),
            authority_scope=h.get("X-AGTP-AUTHORITY-SCOPE", ""),
            parameters=body.get("parameters", {}),
            context=body.get("context", {}),
            session_id=h.get("X-AGTP-SESSION-ID"),
            task_id=h.get("X-AGTP-TASK-ID") or body.get("task_id"),
            delegation_chain=delegation_chain,
            priority=h.get("X-AGTP-PRIORITY", "normal"),
            ttl=int(h["X-AGTP-TTL"]) if h.get("X-AGTP-TTL") else None,
            version=h.get("X-AGTP-VERSION", AGTP_VERSION),
        )


@dataclass
class AGTPResponse:
    """
    Represents an AGTP response message.
    """
    status: int                          # AGTP status code
    task_id: str
    result: dict = field(default_factory=dict)
    attribution: dict = field(default_factory=dict)
    server_agent_id: Optional[str] = None
    continuation_token: Optional[str] = None
    version: str = AGTP_VERSION

    def __post_init__(self):
        # Auto-populate attribution record
        if not self.attribution:
            self.attribution = {
                "timestamp": time.time(),
                "task_id": self.task_id,
                "server_agent_id": self.server_agent_id,
            }

    def to_dict(self) -> dict:
        """Serialise to AGTP JSON body."""
        return {
            "status": self.status,
            "task_id": self.task_id,
            "result": self.result,
            "attribution": self.attribution,
        }

    def to_http_headers(self) -> dict:
        """Map AGTP response headers to HTTP X-AGTP-* headers."""
        headers = {
            "X-AGTP-Version":   self.version,
            "X-AGTP-Status":    str(self.status),
            "X-AGTP-Task-ID":   self.task_id,
            "Content-Type":     CONTENT_TYPE,
        }
        if self.server_agent_id:
            headers["X-AGTP-Server-Agent-ID"] = self.server_agent_id
        if self.continuation_token:
            headers["X-AGTP-Continuation-Token"] = self.continuation_token
        return headers

    @classmethod
    def from_http_response(cls, http_response) -> "AGTPResponse":
        """Reconstruct an AGTPResponse from an HTTP response."""
        body = http_response.json() if http_response.content else {}
        return cls(
            status=int(http_response.headers.get("X-AGTP-Status", http_response.status_code)),
            task_id=http_response.headers.get("X-AGTP-Task-ID", ""),
            result=body.get("result", {}),
            attribution=body.get("attribution", {}),
            server_agent_id=http_response.headers.get("X-AGTP-Server-Agent-ID"),
            continuation_token=http_response.headers.get("X-AGTP-Continuation-Token"),
            version=http_response.headers.get("X-AGTP-Version", AGTP_VERSION),
        )
