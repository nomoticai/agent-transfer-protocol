"""
AGTP Shim Example: Echo Server and Client Demo

Demonstrates a complete AGTP over HTTP shim implementation.
Run this file to start the demo server, then run the client
in a separate terminal.

Start server:
    python examples/echo_server.py

Run client (separate terminal):
    python examples/echo_server.py --client
"""

import sys
import logging
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
)

# ── Server ──────────────────────────────────────────────────────────────────

def run_server():
    from agtp import AGTPServer, AGTPRequest

    server = AGTPServer(
        agent_id="agtp://echo-service.examples.agtp",
        log_all_requests=True,
    )

    @server.handler("QUERY")
    def handle_query(request: AGTPRequest):
        intent = request.parameters.get("intent", "")
        return {
            "results": [
                {
                    "content": f"Echo: {intent}",
                    "source": "echo-service",
                    "confidence": 1.0,
                }
            ],
            "result_count": 1,
            "session_context_updated": False,
        }

    @server.handler("SUMMARIZE")
    def handle_summarize(request: AGTPRequest):
        source = request.parameters.get("source", "")
        length = request.parameters.get("length", "standard")
        return {
            "summary": f"[{length.upper()} SUMMARY] {source[:100]}...",
            "source_hash": "sha256:abc123",
            "confidence": 0.88,
        }

    @server.handler("NOTIFY")
    def handle_notify(request: AGTPRequest):
        recipient = request.parameters.get("recipient", "unknown")
        content = request.parameters.get("content", "")
        print(f"\n  📨 NOTIFY → {recipient}: {content}\n")
        return {
            "notification_id": f"notif-{int(time.time())}",
            "delivered": True,
        }

    @server.handler("ESCALATE")
    def handle_escalate(request: AGTPRequest):
        """
        ESCALATE is a first-class method — not an error.
        An agent that escalates appropriately is functioning correctly.
        """
        reason = request.parameters.get("reason", "")
        context = request.parameters.get("context", {})
        priority = request.parameters.get("priority", "normal")
        print(f"\n  🚨 ESCALATE [{priority.upper()}] reason={reason}")
        print(f"     context: {context}\n")
        return {
            "escalation_id": f"esc-{int(time.time())}",
            "routed_to": request.parameters.get("recipient", "default-handler"),
            "status": "pending_review",
            "task_paused": True,
        }

    @server.handler("CONFIRM")
    def handle_confirm(request: AGTPRequest):
        return {
            "attestation_id": f"attest-{int(time.time())}",
            "confirmed_at": time.time(),
            "status": request.parameters.get("status"),
        }

    @server.handler("LEARN")
    def handle_learn(request: AGTPRequest):
        return {
            "learn_id": f"learn-{int(time.time())}",
            "scope": request.parameters.get("scope"),
            "stored": True,
        }

    print("\n" + "="*60)
    print("  AGTP Echo Server")
    print("  Spec: draft-hood-independent-agtp-00")
    print("  Transport: HTTP shim (X-AGTP-* headers)")
    print("  Endpoint: http://localhost:8080/agtp")
    print("  Health:   http://localhost:8080/agtp/health")
    print("="*60 + "\n")

    server.run(host="0.0.0.0", port=8080)


# ── Client ──────────────────────────────────────────────────────────────────

def run_client():
    from agtp import AGTPClient, AGTPScopeViolation

    print("\n" + "="*60)
    print("  AGTP Client Demo")
    print("  Connecting to: http://localhost:8080")
    print("="*60 + "\n")

    # Give the server a moment to start if running in same process
    time.sleep(1)

    with AGTPClient(
        base_url="http://localhost:8080",
        agent_id="agtp://demo-client.examples.agtp",
        principal_id="chris@nomotic.ai",
        authority_scope="documents:query documents:summarize knowledge:learn escalation:escalate",
    ) as client:

        print("1. QUERY")
        print("-" * 40)
        response = client.query(
            intent="What are the key limitations of HTTP for AI agent traffic?",
            scope=["documents:research"],
            format="structured",
        )
        print(f"   Status: {response.status}")
        print(f"   Task:   {response.task_id}")
        print(f"   Result: {response.result}\n")

        print("2. SUMMARIZE")
        print("-" * 40)
        response = client.summarize(
            source="HTTP was designed for human-initiated request/response cycles. "
                   "AI agents require intent-based methods, protocol-level identity, "
                   "and governance primitives that HTTP cannot provide.",
            length="brief",
            format="prose",
        )
        print(f"   Status: {response.status}")
        print(f"   Result: {response.result}\n")

        print("3. LEARN")
        print("-" * 40)
        response = client.learn(
            content="AGTP is the transport layer for AI agent traffic",
            scope="session",
            category="protocol-knowledge",
            confidence=0.99,
        )
        print(f"   Status: {response.status}")
        print(f"   Result: {response.result}\n")

        print("4. NOTIFY")
        print("-" * 40)
        response = client.notify(
            recipient="agtp://ops-team.acme.agent",
            content="AGTP demo client completed QUERY and LEARN operations successfully",
            urgency="informational",
        )
        print(f"   Status: {response.status}")
        print(f"   Result: {response.result}\n")

        print("5. ESCALATE (first-class method, not an error)")
        print("-" * 40)
        response = client.escalate(
            task_id="task-demo-001",
            reason="confidence_threshold",
            context_data={
                "attempted_action": "QUERY",
                "confidence": 0.45,
                "threshold": 0.75,
                "query": "What is the legal liability for agent actions?",
            },
            priority="normal",
            recipient="agtp://human-review.acme.agent",
        )
        print(f"   Status: {response.status}")
        print(f"   Result: {response.result}\n")

        print("6. SCOPE VIOLATION (451 governance signal)")
        print("-" * 40)
        # Try to BOOK without booking:book in our scope
        try:
            response = client.book(
                resource_id="flight-AA2847",
                principal_id="chris@nomotic.ai",
                time_slot="2026-04-15T08:00:00Z",
            )
        except AGTPScopeViolation as e:
            print(f"   AGTP 451 Scope Violation (expected):")
            print(f"   {e.message}")
            print(f"   This is a governance signal — logged for audit.\n")

        print("7. CONFIRM")
        print("-" * 40)
        response = client.confirm(
            target_id="task-demo-001",
            status="accepted",
            reason="Human reviewer approved the escalated action",
        )
        print(f"   Status: {response.status}")
        print(f"   Result: {response.result}\n")

    print("="*60)
    print("  Demo complete.")
    print("  All AGTP request/response headers transmitted as")
    print("  X-AGTP-* HTTP headers over standard HTTP transport.")
    print("  Upgrade path: swap transport layer for native AGTP.")
    print("="*60 + "\n")


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--client" in sys.argv:
        run_client()
    elif "--demo" in sys.argv:
        # Run server in background thread, then run client
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        time.sleep(2)
        run_client()
    else:
        run_server()
