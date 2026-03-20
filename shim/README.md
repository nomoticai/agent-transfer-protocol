# agtp — Agent Transfer Protocol Python Shim

A Python implementation of the **Agent Transfer Protocol (AGTP)** over HTTP,
using `X-AGTP-*` headers as a shim transport.

**IETF Internet-Draft:** `draft-hood-independent-agtp-00`  
**Datatracker:** https://datatracker.ietf.org/doc/draft-hood-independent-agtp/  
**Spec repo:** https://github.com/nomoticai/agent-transfer-protocol

---

## What This Is

AGTP is a dedicated application-layer protocol for AI agent traffic. It defines:

- **Intent-based methods** — QUERY, SUMMARIZE, BOOK, DELEGATE, ESCALATE, and more
- **Protocol-level identity** — Agent-ID, Principal-ID, Authority-Scope on every request
- **Governance primitives** — ESCALATE as a first-class method, scope enforcement, attribution

This library implements AGTP **over HTTP** using `X-AGTP-*` headers. It is a shim:
when native AGTP transport exists, swap the transport layer — all AGTP semantics remain
unchanged.

```
Your Agent Code
    ↓
AGTPClient (this library)
    ↓
X-AGTP-* headers over HTTP  ← shim transport (swap for native AGTP later)
    ↓
AGTPServer (this library)
    ↓
Your Handler Logic
```

---

## Installation

```bash
pip install agtp
```

Or from source:

```bash
git clone https://github.com/nomoticai/agent-transfer-protocol
cd agent-transfer-protocol/python-shim
pip install -e ".[dev]"
```

---

## Quick Start

### Server

```python
from agtp import AGTPServer, AGTPRequest

server = AGTPServer(
    agent_id="agtp://my-service.engineering.acme.agent"
)

@server.handler("QUERY")
def handle_query(request: AGTPRequest):
    # request.parameters contains the AGTP method parameters
    # request.agent_id, .principal_id, .authority_scope are available
    results = my_search(request.parameters["intent"])
    return {"results": results, "confidence": 0.91}

@server.handler("ESCALATE")
def handle_escalate(request: AGTPRequest):
    # ESCALATE is a first-class method — not an error.
    # An agent that escalates appropriately is functioning correctly.
    notify_human(request.parameters["reason"], request.parameters["context"])
    return {"escalation_id": "esc-001", "status": "pending_review"}

server.run(port=8080)
```

### Client

```python
from agtp import AGTPClient

with AGTPClient(
    base_url="http://localhost:8080",
    agent_id="agtp://research-agent.engineering.acme.agent",
    principal_id="chris@nomotic.ai",
    authority_scope="documents:query documents:summarize escalation:escalate",
) as client:

    # QUERY
    response = client.query(
        intent="Key limitations of HTTP for AI agent traffic",
        format="structured",
    )
    print(response.result)

    # SUMMARIZE
    response = client.summarize(
        source="Long document text here...",
        length="brief",
    )
    print(response.result)

    # ESCALATE — a governance primitive, not an error
    response = client.escalate(
        task_id="task-001",
        reason="confidence_threshold",
        context_data={"confidence": 0.45, "threshold": 0.75},
        priority="normal",
    )
    print(response.result)
```

---

## Core Methods

| Method | Category | Intent | Idempotent |
|--------|----------|--------|-----------|
| QUERY | Acquire | Semantic data retrieval | Yes |
| SUMMARIZE | Compute | Synthesize content | Yes |
| BOOK | Transact | Reserve a resource | No |
| SCHEDULE | Orchestrate | Plan future actions | No |
| LEARN | Compute | Update agent context | No |
| DELEGATE | Orchestrate | Transfer task to sub-agent | No |
| COLLABORATE | Orchestrate | Coordinate peer agents | No |
| CONFIRM | Transact | Attest to a prior action | Yes |
| ESCALATE | Orchestrate | Defer to human authority | Yes |
| NOTIFY | Communicate | Push information | No |

---

## AGTP Status Codes

Standard HTTP codes plus three AGTP-specific governance signals:

| Code | Name | Meaning |
|------|------|---------|
| 451 | Scope Violation | Action outside declared Authority-Scope. **Governance signal. MUST be logged.** |
| 550 | Delegation Failure | Sub-agent failed to complete delegated task |
| 551 | Authority Chain Broken | Delegation chain contains unverifiable identity |

```python
from agtp import AGTPClient, AGTPScopeViolation

try:
    response = client.book(resource_id="flight-AA2847", principal_id="user@example.com")
except AGTPScopeViolation as e:
    # 451 — agent attempted action outside its Authority-Scope
    # This is a governance signal, not a bug. Log it.
    print(f"Scope violation: {e.message}")
```

---

## Authority-Scope

```python
# Narrow scope
client = AGTPClient(..., authority_scope="documents:query")

# Multiple scopes
client = AGTPClient(..., authority_scope="documents:query documents:summarize booking:book")

# Domain wildcard
client = AGTPClient(..., authority_scope="documents:*")

# Full access (use with caution)
client = AGTPClient(..., authority_scope="*:*")
```

---

## Agent Naming

AGTP agents use the `agtp://` URI scheme:

```
# Canonical form (256-bit cryptographic identifier)
agtp://3a9f2c1d8b7e4a6f0c2d5e9b1a3f7c0d4e8b2a5f9c3d7e1b0a4f8c2d6e0b

# Human-friendly hierarchical form (optional layer)
agtp://research-bot.engineering.acme.agent
agtp://procurement-agent.finance.acme.agent
agtp://customer-service.acme.nomo
```

---

## Running the Demo

```bash
# Install dependencies
pip install agtp

# Terminal 1 — start the echo server
python examples/echo_server.py

# Terminal 2 — run the client demo
python examples/echo_server.py --client

# Or run both in one command
python examples/echo_server.py --demo
```

---

## Running Tests

```bash
pip install agtp[dev]
pytest tests/ -v
```

---

## The Upgrade Path

The shim maps AGTP headers to HTTP `X-AGTP-*` headers:

```
AGTP Header          →  HTTP Header
──────────────────────────────────────
Agent-ID             →  X-AGTP-Agent-ID
Principal-ID         →  X-AGTP-Principal-ID
Authority-Scope      →  X-AGTP-Authority-Scope
ATP-Method           →  X-AGTP-Method
ATP-Version          →  X-AGTP-Version
...
Content-Type         →  application/agtp+json
```

When native AGTP transport is available, replace the `_send()` method in
`AGTPClient` with a native transport call. All method logic, validation,
and handler code remains unchanged.

---

## AGTP vs HTTP

| Criterion | AGTP | HTTP |
|-----------|------|------|
| Agent-native methods | Yes | No |
| Intent semantics at protocol level | Native | None (GET/POST) |
| Built-in agent identity | Yes | No |
| Authority scope enforcement | Protocol-level | Application-layer |
| Escalation as first-class primitive | Yes | No |
| Method registry extensibility | Yes (Expert Review) | Frozen (IETF Review) |

---

## License

MIT License — see LICENSE file.

The AGTP specification itself is CC0 (public domain).  
See https://github.com/nomoticai/agent-transfer-protocol for the spec.

---

## Contributing

Implementation reports help advance the IETF standardisation process.
If you build something with this library, please open an issue describing
your use case. Reports will be incorporated into subsequent I-D revisions.

Spec feedback: https://github.com/nomoticai/agent-transfer-protocol/issues  
IETF discussion: agent2agent@ietf.org
