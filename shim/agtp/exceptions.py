"""
AGTP-specific exceptions.
"""

from .status import AGTPStatus


class AGTPError(Exception):
    """Base class for all AGTP errors."""
    status_code = AGTPStatus.SERVER_ERROR

    def __init__(self, message: str, task_id: str = None):
        self.message = message
        self.task_id = task_id
        super().__init__(message)


class AGTPScopeViolation(AGTPError):
    """
    451 Scope Violation.
    
    The requested action is outside the Authority-Scope declared
    in the request headers. This is a governance signal, not a
    protocol error. MUST be logged.
    
    The agent MUST NOT retry the same request without modifying
    its Authority-Scope declaration.
    """
    status_code = AGTPStatus.SCOPE_VIOLATION

    def __init__(self, requested_scope: str, declared_scope: str, task_id: str = None):
        self.requested_scope = requested_scope
        self.declared_scope = declared_scope
        message = (
            f"Scope violation: requested '{requested_scope}' "
            f"is not within declared scope '{declared_scope}'"
        )
        super().__init__(message, task_id)


class AGTPUnauthorized(AGTPError):
    """401 Unauthorized. Agent-ID not recognised or not authenticated."""
    status_code = AGTPStatus.UNAUTHORIZED


class AGTPMethodNotFound(AGTPError):
    """404 Not Found. Method or resource not found."""
    status_code = AGTPStatus.NOT_FOUND


class AGTPConflict(AGTPError):
    """409 Conflict. Method conflicts with current state."""
    status_code = AGTPStatus.CONFLICT


class AGTPDelegationFailure(AGTPError):
    """
    550 Delegation Failure.
    A delegated sub-agent failed to complete the requested task.
    """
    status_code = AGTPStatus.DELEGATION_FAILURE


class AGTPAuthorityChainBroken(AGTPError):
    """
    551 Authority Chain Broken.
    Delegation chain contains an unverifiable identity link.
    MUST be logged.
    """
    status_code = AGTPStatus.AUTHORITY_CHAIN_BROKEN


class AGTPValidationError(AGTPError):
    """400 Bad Request. Malformed AGTP request."""
    status_code = AGTPStatus.BAD_REQUEST
