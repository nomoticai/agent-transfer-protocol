"""
AGTP Shim Tests.
Run with: python -m pytest tests/ -v
"""

import pytest
from agtp.models import AGTPRequest, AGTPResponse, AGTP_VERSION
from agtp.methods import (
    validate_method, validate_parameters, validate_scope,
    validate_authority_scope_format, is_idempotent,
)
from agtp.status import AGTPStatus
from agtp.exceptions import (
    AGTPScopeViolation, AGTPValidationError,
)


# ── Model Tests ──────────────────────────────────────────────────────────────

class TestAGTPRequest:
    def test_auto_generates_task_id(self):
        req = AGTPRequest(
            method="QUERY",
            agent_id="agtp://test.agent",
            principal_id="user@example.com",
            authority_scope="documents:query",
        )
        assert req.task_id.startswith("task-")

    def test_auto_generates_session_id(self):
        req = AGTPRequest(
            method="QUERY",
            agent_id="agtp://test.agent",
            principal_id="user@example.com",
            authority_scope="documents:query",
        )
        assert req.session_id.startswith("sess-")

    def test_method_uppercased(self):
        req = AGTPRequest(
            method="query",
            agent_id="agtp://test.agent",
            principal_id="user@example.com",
            authority_scope="documents:query",
        )
        assert req.method == "QUERY"

    def test_to_http_headers_contains_required_fields(self):
        req = AGTPRequest(
            method="QUERY",
            agent_id="agtp://test.agent",
            principal_id="user@example.com",
            authority_scope="documents:query",
        )
        headers = req.to_http_headers()
        assert headers["X-AGTP-Version"] == AGTP_VERSION
        assert headers["X-AGTP-Method"] == "QUERY"
        assert headers["X-AGTP-Agent-ID"] == "agtp://test.agent"
        assert headers["X-AGTP-Principal-ID"] == "user@example.com"
        assert headers["X-AGTP-Authority-Scope"] == "documents:query"
        assert headers["Content-Type"] == "application/agtp+json"

    def test_roundtrip_http_headers(self):
        original = AGTPRequest(
            method="SUMMARIZE",
            agent_id="agtp://agent.acme.agent",
            principal_id="admin@acme.com",
            authority_scope="documents:summarize documents:query",
            parameters={"source": "test content"},
        )
        headers = original.to_http_headers()
        body = original.to_dict()
        reconstructed = AGTPRequest.from_http_headers(headers, body)

        assert reconstructed.method == original.method
        assert reconstructed.agent_id == original.agent_id
        assert reconstructed.principal_id == original.principal_id
        assert reconstructed.authority_scope == original.authority_scope


# ── Status Code Tests ────────────────────────────────────────────────────────

class TestAGTPStatus:
    def test_governance_signals(self):
        assert AGTPStatus.is_governance_signal(451)
        assert AGTPStatus.is_governance_signal(550)
        assert AGTPStatus.is_governance_signal(551)
        assert not AGTPStatus.is_governance_signal(200)
        assert not AGTPStatus.is_governance_signal(404)

    def test_success_codes(self):
        assert AGTPStatus.is_success(200)
        assert AGTPStatus.is_success(202)
        assert AGTPStatus.is_success(204)
        assert not AGTPStatus.is_success(400)
        assert not AGTPStatus.is_success(451)

    def test_names(self):
        assert AGTPStatus.name(200) == "OK"
        assert AGTPStatus.name(451) == "Scope Violation"
        assert AGTPStatus.name(550) == "Delegation Failure"
        assert AGTPStatus.name(551) == "Authority Chain Broken"


# ── Method Validation Tests ───────────────────────────────────────────────────

class TestMethodValidation:
    def test_valid_core_method(self):
        validate_method("QUERY")  # Should not raise

    def test_valid_extended_method(self):
        validate_method("FETCH")  # Should not raise

    def test_experimental_method_allowed(self):
        validate_method("X-CUSTOM")  # Should not raise

    def test_unknown_method_raises(self):
        with pytest.raises(AGTPValidationError):
            validate_method("NONEXISTENT")

    def test_method_case_insensitive(self):
        validate_method("query")   # Should not raise
        validate_method("Query")   # Should not raise

    def test_idempotent_methods(self):
        assert is_idempotent("QUERY")
        assert is_idempotent("SUMMARIZE")
        assert is_idempotent("CONFIRM")
        assert is_idempotent("ESCALATE")
        assert not is_idempotent("BOOK")
        assert not is_idempotent("LEARN")
        assert not is_idempotent("DELEGATE")

    def test_query_requires_intent(self):
        with pytest.raises(AGTPValidationError) as exc:
            validate_parameters("QUERY", {})
        assert "intent" in str(exc.value)

    def test_book_requires_resource_and_principal(self):
        with pytest.raises(AGTPValidationError):
            validate_parameters("BOOK", {"resource_id": "only-this"})

    def test_escalate_requires_valid_reason(self):
        with pytest.raises(AGTPValidationError) as exc:
            validate_parameters("ESCALATE", {
                "task_id": "task-001",
                "reason": "invalid_reason",
                "context": {},
            })
        assert "reason" in str(exc.value)

    def test_escalate_valid_reason(self):
        validate_parameters("ESCALATE", {
            "task_id": "task-001",
            "reason": "confidence_threshold",
            "context": {"note": "below threshold"},
        })  # Should not raise

    def test_confirm_requires_valid_status(self):
        with pytest.raises(AGTPValidationError):
            validate_parameters("CONFIRM", {
                "target_id": "task-001",
                "status": "maybe",
            })

    def test_run_requires_procedure_id(self):
        with pytest.raises(AGTPValidationError) as exc:
            validate_parameters("RUN", {"command": "rm -rf /"})
        assert "procedure_id" in str(exc.value)

    def test_learn_requires_valid_scope(self):
        with pytest.raises(AGTPValidationError):
            validate_parameters("LEARN", {
                "content": "something",
                "scope": "invalid_scope",
            })


# ── Scope Validation Tests ────────────────────────────────────────────────────

class TestScopeValidation:
    def test_exact_scope_match(self):
        validate_scope("SUMMARIZE", "documents:summarize")  # Should not raise

    def test_domain_wildcard(self):
        validate_scope("SUMMARIZE", "documents:*")  # Should not raise

    def test_global_wildcard(self):
        validate_scope("BOOK", "*:*")  # Should not raise

    def test_scope_violation_raises_451(self):
        with pytest.raises(AGTPScopeViolation) as exc:
            validate_scope("BOOK", "documents:query")
        assert exc.value.status_code == 451

    def test_scope_violation_message(self):
        with pytest.raises(AGTPScopeViolation) as exc:
            validate_scope("SUMMARIZE", "knowledge:learn")
        assert "documents:summarize" in str(exc.value)

    def test_multiple_scopes_permit_method(self):
        # Having other scopes should not affect a valid token
        validate_scope(
            "SUMMARIZE",
            "knowledge:learn documents:summarize booking:query"
        )

    def test_query_permits_any_scope(self):
        # QUERY has no scope requirement
        validate_scope("QUERY", "booking:book")  # Should not raise

    def test_scope_format_valid(self):
        validate_authority_scope_format("documents:query knowledge:learn")

    def test_scope_format_wildcard_domain(self):
        validate_authority_scope_format("documents:*")

    def test_scope_format_global_wildcard(self):
        validate_authority_scope_format("*:*")

    def test_scope_format_invalid_missing_colon(self):
        with pytest.raises(AGTPValidationError):
            validate_authority_scope_format("documents")

    def test_scope_format_empty(self):
        with pytest.raises(AGTPValidationError):
            validate_authority_scope_format("")


# ── Server Integration Tests ─────────────────────────────────────────────────

class TestAGTPServer:
    @pytest.fixture
    def server(self):
        from agtp import AGTPServer
        s = AGTPServer(
            agent_id="agtp://test-server.tests.agtp",
            log_all_requests=False,
        )

        @s.handler("QUERY")
        def handle_query(req):
            return {"answer": req.parameters.get("intent", "")}

        @s.handler("ESCALATE")
        def handle_escalate(req):
            return {
                "escalation_id": "esc-test-001",
                "status": "pending_review",
            }

        return s

    @pytest.fixture
    def client(self, server):
        return server.app.test_client()

    def _agtp_headers(self, method, scope="documents:query"):
        return {
            "X-AGTP-Version": "AGTP/1.0",
            "X-AGTP-Method": method,
            "X-AGTP-Agent-ID": "agtp://test-client.tests.agtp",
            "X-AGTP-Principal-ID": "tester@example.com",
            "X-AGTP-Authority-Scope": scope,
            "X-AGTP-Task-ID": "task-test-001",
            "X-AGTP-Session-ID": "sess-test-001",
            "Content-Type": "application/agtp+json",
        }

    def test_query_returns_200(self, client):
        import json
        response = client.post(
            "/agtp",
            headers=self._agtp_headers("QUERY"),
            data=json.dumps({
                "method": "QUERY",
                "task_id": "task-test-001",
                "parameters": {"intent": "test query"},
            }),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == 200
        assert data["result"]["answer"] == "test query"

    def test_missing_handler_returns_404(self, client):
        import json
        response = client.post(
            "/agtp",
            headers=self._agtp_headers("NOTIFY", scope="*:*"),
            data=json.dumps({
                "method": "NOTIFY",
                "task_id": "task-test-002",
                "parameters": {
                    "recipient": "someone",
                    "content": "hello",
                },
            }),
        )
        assert response.status_code == 404

    def test_scope_violation_returns_400(self, client):
        import json
        # SUMMARIZE requires documents:summarize but we only have documents:query
        response = client.post(
            "/agtp",
            headers=self._agtp_headers("SUMMARIZE", scope="documents:query"),
            data=json.dumps({
                "method": "SUMMARIZE",
                "task_id": "task-test-003",
                "parameters": {"source": "test"},
            }),
        )
        # 451 maps to 400 in HTTP shim
        assert response.status_code == 400
        data = response.get_json()
        assert data["result"]["status_name"] == "Scope Violation"

    def test_escalate_returns_202(self, client):
        import json
        response = client.post(
            "/agtp",
            headers=self._agtp_headers(
                "ESCALATE",
                scope="escalation:escalate"
            ),
            data=json.dumps({
                "method": "ESCALATE",
                "task_id": "task-test-004",
                "parameters": {
                    "task_id": "task-original",
                    "reason": "confidence_threshold",
                    "context": {"note": "below threshold"},
                },
            }),
        )
        assert response.status_code == 200

    def test_health_endpoint(self, client):
        response = client.get("/agtp/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "QUERY" in data["registered_methods"]
