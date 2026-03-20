"""
AGTP Method Definitions.

Core methods from draft-hood-independent-agtp-00 Section 6.2.
Each method defines: required parameters, optional parameters,
idempotency, and required scope tokens.
"""

from typing import Set
from .exceptions import AGTPValidationError, AGTPScopeViolation


# ---------------------------------------------------------------------------
# Method registry
# ---------------------------------------------------------------------------

CORE_METHODS = {
    "QUERY", "SUMMARIZE", "BOOK", "SCHEDULE", "LEARN",
    "DELEGATE", "COLLABORATE", "CONFIRM", "ESCALATE", "NOTIFY",
}

# Tier 2 standard extended methods (defined in draft-hood-agtp-standard-methods-00)
EXTENDED_METHODS = {
    # ACQUIRE
    "FETCH", "SEARCH", "SCAN", "PULL", "IMPORT", "FIND",
    # COMPUTE
    "EXTRACT", "FILTER", "VALIDATE", "TRANSFORM", "TRANSLATE",
    "NORMALIZE", "PREDICT", "RANK", "MAP",
    # TRANSACT
    "REGISTER", "SUBMIT", "TRANSFER", "PURCHASE", "SIGN",
    "MERGE", "LINK", "LOG", "SYNC", "PUBLISH",
    # COMMUNICATE
    "REPLY", "SEND", "REPORT",
    # ORCHESTRATE
    "MONITOR", "ROUTE", "RETRY", "PAUSE", "RESUME", "RUN", "CHECK",
}

ALL_REGISTERED_METHODS = CORE_METHODS | EXTENDED_METHODS

# Methods that are idempotent
IDEMPOTENT_METHODS = {
    "QUERY", "SUMMARIZE", "CONFIRM", "ESCALATE",
    "FETCH", "SEARCH", "SCAN", "CHECK", "VALIDATE",
    "EXTRACT", "FILTER", "PREDICT", "RANK", "MAP",
    "FIND", "REPORT",
}

# Methods that modify state
STATE_MODIFYING_METHODS = ALL_REGISTERED_METHODS - IDEMPOTENT_METHODS

# Required parameters per core method
REQUIRED_PARAMS = {
    "QUERY":       ["intent"],
    "SUMMARIZE":   ["source"],
    "BOOK":        ["resource_id", "principal_id"],
    "SCHEDULE":    ["steps", "trigger"],
    "LEARN":       ["content", "scope"],
    "DELEGATE":    ["target_agent_id", "task", "authority_scope", "delegation_token"],
    "COLLABORATE": ["collaborators", "objective"],
    "CONFIRM":     ["target_id", "status"],
    "ESCALATE":    ["task_id", "reason", "context"],
    "NOTIFY":      ["recipient", "content"],
}

# Minimum scope required to invoke each core method
# Format: domain:action
REQUIRED_SCOPE = {
    "QUERY":       None,                  # Any scope permits QUERY
    "SUMMARIZE":   "documents:summarize",
    "BOOK":        "booking:book",
    "SCHEDULE":    None,                  # Depends on what is scheduled
    "LEARN":       "knowledge:learn",
    "DELEGATE":    "agents:delegate",
    "COLLABORATE": "agents:collaborate",
    "CONFIRM":     None,                  # Any scope permits CONFIRM
    "ESCALATE":    "escalation:escalate",
    "NOTIFY":      None,                  # Any scope permits NOTIFY
    "PURCHASE":    "payments:purchase",   # Tier 2 — explicit scope required
    "TRANSFER":    "payments:transfer",   # Tier 2 — explicit scope required
    "SIGN":        "documents:sign",      # Tier 2 — explicit scope required
    "RUN":         "execute:run",         # Tier 2 — explicit scope required
}

# ESCALATE reason codes
ESCALATE_REASONS = {
    "confidence_threshold",
    "scope_limit",
    "ethical_flag",
    "ambiguous_instruction",
    "resource_unavailable",
}

# CONFIRM status values
CONFIRM_STATUSES = {"accepted", "rejected", "deferred"}

# LEARN scope values
LEARN_SCOPES = {"session", "principal", "global"}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_method(method: str) -> None:
    """Raise AGTPValidationError if method is not registered."""
    m = method.upper()
    if m not in ALL_REGISTERED_METHODS:
        if m.startswith("X-"):
            return  # Experimental methods are permitted
        raise AGTPValidationError(
            f"Unknown method '{method}'. Use X- prefix for experimental methods."
        )


def validate_parameters(method: str, parameters: dict) -> None:
    """Raise AGTPValidationError if required parameters are missing."""
    method = method.upper()
    required = REQUIRED_PARAMS.get(method, [])
    missing = [p for p in required if p not in parameters]
    if missing:
        raise AGTPValidationError(
            f"Method {method} requires parameters: {', '.join(missing)}"
        )

    # Method-specific validation
    if method == "ESCALATE":
        reason = parameters.get("reason", "")
        if reason not in ESCALATE_REASONS:
            raise AGTPValidationError(
                f"ESCALATE reason must be one of: {', '.join(sorted(ESCALATE_REASONS))}. "
                f"Got: '{reason}'"
            )

    if method == "CONFIRM":
        status = parameters.get("status", "")
        if status not in CONFIRM_STATUSES:
            raise AGTPValidationError(
                f"CONFIRM status must be one of: {', '.join(sorted(CONFIRM_STATUSES))}. "
                f"Got: '{status}'"
            )

    if method == "LEARN":
        scope = parameters.get("scope", "")
        if scope not in LEARN_SCOPES:
            raise AGTPValidationError(
                f"LEARN scope must be one of: {', '.join(sorted(LEARN_SCOPES))}. "
                f"Got: '{scope}'"
            )

    if method == "RUN":
        if "procedure_id" not in parameters:
            raise AGTPValidationError(
                "RUN requires 'procedure_id' parameter. "
                "Free-form execution strings are not permitted."
            )


def validate_scope(method: str, declared_scope: str, task_id: str = None) -> None:
    """
    Check that the declared Authority-Scope permits the requested method.
    
    Raises AGTPScopeViolation (451) if the method requires a scope token
    that is not present in the declared scope.
    
    This is the protocol-level defense against authority laundering.
    """
    method = method.upper()
    required = REQUIRED_SCOPE.get(method)

    if required is None:
        return  # Method has no scope requirement

    declared_tokens: Set[str] = set(declared_scope.strip().split())

    # Check for wildcard grant
    if "*:*" in declared_tokens:
        return

    # Check domain wildcard (e.g. "booking:*")
    domain = required.split(":")[0]
    if f"{domain}:*" in declared_tokens:
        return

    # Check exact token
    if required in declared_tokens:
        return

    raise AGTPScopeViolation(
        requested_scope=required,
        declared_scope=declared_scope,
        task_id=task_id,
    )


def validate_authority_scope_format(scope: str) -> None:
    """
    Validate Authority-Scope token format.
    Tokens must be lowercase ASCII with a single colon separator.
    """
    if not scope or not scope.strip():
        raise AGTPValidationError("Authority-Scope must not be empty.")

    tokens = scope.strip().split()
    for token in tokens:
        if token == "*:*":
            continue
        parts = token.split(":")
        if len(parts) != 2:
            raise AGTPValidationError(
                f"Invalid scope token '{token}'. "
                "Format must be domain:action or domain:*"
            )
        domain, action = parts
        if not domain or not action:
            raise AGTPValidationError(
                f"Invalid scope token '{token}'. "
                "Both domain and action must be non-empty."
            )


def is_idempotent(method: str) -> bool:
    return method.upper() in IDEMPOTENT_METHODS
