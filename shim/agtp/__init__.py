"""
AGTP — Agent Transfer Protocol Python Shim Library

Implements AGTP over HTTP using X-AGTP-* headers.
When native AGTP transport is available, replace the
transport layer — all AGTP semantics remain unchanged.

Draft specification: draft-hood-independent-agtp-00
https://datatracker.ietf.org/doc/draft-hood-independent-agtp/

Quick start:

    # Client
    from agtp import AGTPClient

    with AGTPClient(
        base_url="http://localhost:8080",
        agent_id="agtp://my-agent.acme.agent",
        principal_id="user@example.com",
        authority_scope="documents:query knowledge:query",
    ) as client:
        response = client.query(intent="What is ATP?")
        print(response.result)

    # Server
    from agtp import AGTPServer

    server = AGTPServer(agent_id="agtp://my-service.acme.agent")

    @server.handler("QUERY")
    def handle_query(request):
        return {"answer": "42"}

    server.run(port=8080)
"""

from .client import AGTPClient
from .server import AGTPServer
from .models import AGTPRequest, AGTPResponse, AGTP_VERSION, CONTENT_TYPE
from .status import AGTPStatus
from .methods import (
    CORE_METHODS,
    EXTENDED_METHODS,
    ALL_REGISTERED_METHODS,
    validate_method,
    validate_parameters,
    validate_scope,
)
from .exceptions import (
    AGTPError,
    AGTPScopeViolation,
    AGTPUnauthorized,
    AGTPMethodNotFound,
    AGTPConflict,
    AGTPDelegationFailure,
    AGTPAuthorityChainBroken,
    AGTPValidationError,
)

__version__ = "0.1.0"
__author__ = "Chris Hood"
__spec__ = "draft-hood-independent-agtp-00"

__all__ = [
    "AGTPClient",
    "AGTPServer",
    "AGTPRequest",
    "AGTPResponse",
    "AGTPStatus",
    "AGTPError",
    "AGTPScopeViolation",
    "AGTPUnauthorized",
    "AGTPMethodNotFound",
    "AGTPConflict",
    "AGTPDelegationFailure",
    "AGTPAuthorityChainBroken",
    "AGTPValidationError",
    "AGTP_VERSION",
    "CONTENT_TYPE",
    "CORE_METHODS",
    "EXTENDED_METHODS",
    "ALL_REGISTERED_METHODS",
    "validate_method",
    "validate_parameters",
    "validate_scope",
]
