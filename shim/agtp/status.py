"""
AGTP Status Codes.

Standard codes mirror HTTP semantics.
ATP-specific codes (451, 550, 551) have no HTTP equivalent.
"""


class AGTPStatus:
    # 2xx Success
    OK                   = 200
    ACCEPTED             = 202
    NO_CONTENT           = 204

    # 4xx Client errors
    BAD_REQUEST          = 400
    UNAUTHORIZED         = 401
    FORBIDDEN            = 403
    NOT_FOUND            = 404
    TIMEOUT              = 408
    CONFLICT             = 409
    UNPROCESSABLE        = 422
    RATE_LIMITED         = 429

    # ATP-specific governance codes
    SCOPE_VIOLATION      = 451  # Action outside declared Authority-Scope
                                # Governance signal, not a protocol error.
                                # MUST be logged.

    # 5xx Server errors
    SERVER_ERROR         = 500
    UNAVAILABLE          = 503

    # ATP-specific delegation codes
    DELEGATION_FAILURE   = 550  # Sub-agent failed to complete delegated task
    AUTHORITY_CHAIN_BROKEN = 551  # Delegation chain contains unverifiable entry
                                   # MUST be logged.

    # Human-readable names
    NAMES = {
        200: "OK",
        202: "Accepted",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        408: "Timeout",
        409: "Conflict",
        422: "Unprocessable",
        429: "Rate Limited",
        451: "Scope Violation",
        500: "Server Error",
        503: "Unavailable",
        550: "Delegation Failure",
        551: "Authority Chain Broken",
    }

    @classmethod
    def name(cls, code: int) -> str:
        return cls.NAMES.get(code, f"Unknown ({code})")

    @classmethod
    def is_success(cls, code: int) -> bool:
        return 200 <= code < 300

    @classmethod
    def is_governance_signal(cls, code: int) -> bool:
        """451, 550, 551 are governance signals requiring audit logging."""
        return code in (cls.SCOPE_VIOLATION,
                        cls.DELEGATION_FAILURE,
                        cls.AUTHORITY_CHAIN_BROKEN)
