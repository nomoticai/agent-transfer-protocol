# Intellectual Property and Patent Disclosure

## Core Specification

The core Agent Transfer Protocol (AGTP) specification — including all
base methods (QUERY, SUMMARIZE, BOOK, SCHEDULE, LEARN, DELEGATE,
COLLABORATE, CONFIRM, ESCALATE, NOTIFY), header fields, status codes,
connection model, and IANA registrations defined in
`draft-hood-independent-agtp-01` — is dedicated to the public domain
under CC0 and is intended for open implementation without royalty
obligation.

## Extensions with Pending Patent Claims

The following extensions referenced in the specification may be subject
to pending patent applications by the author:

**System and Method for Transport-Layer Cryptographic Identity
Certification of AI Agents via the Agent Transfer Protocol with
Authority-Scope Binding, Session-Level Revocation Propagation, and
Certificate Transparency Infrastructure**
Described at a high level in Section 8.2 of the specification and
fully specified in `draft-hood-agtp-agent-cert-00` (pending). Covers
cryptographic binding of agent identity and authority scope to AGTP
header fields at the transport layer via X.509 v3 extended certificates,
including the authority_scope_commitment mechanism enabling O(1)
per-request scope enforcement by infrastructure Scope-Enforcement
Points, session-level revocation propagation via AGTP NOTIFY broadcast,
and AGTP Certificate Transparency Log infrastructure for tamper-evident
governance metadata. Referenced in Sections 8.2, 6.1.6, 6.4.5, 8.4.1,
8.4.7, and 8.7 of this specification.

**System and Method for Transport-Layer Binding of Governed AI Agent
Packages to the Agent Transfer Protocol with ATP-Native Activation
Methods, Header Field Integration, and Integrity-Preserving Replay
Attack Prevention**
An optional AGTP extension that provides AGTP-native transmission and
activation of governed agent packages in the `.nomo` format, including
governance-attribute header fields (AGTP-ACTIVATE-Tier,
AGTP-ACTIVATE-Zone, AGTP-ACTIVATE-Archetype, AGTP-ACTIVATE-Merkle-Root)
derived from the package's embedded governance identity document,
header field derivation mapping governance identity fields to AGTP
protocol headers at activation completion, and three AGTP-session-layer
replay prevention mechanisms addressing non-overlapping attack surfaces.
Referenced in Sections 5.7, 6.1.6, 6.7.1, 6.7.6, 8.4.7, and the
`activation` Authority-Scope domain (Appendix A) of this specification.

**System and Method for an Open AI Agent Package Format with Declarative
Manifest, Merkle-Based Integrity Binding, and Two-Tier Governed
Deployment Architecture**
Covers the `.agent` and `.nomo` open and governed deployment package
formats defined in Section 2 and Section 5.5 of the specification,
including the declarative manifest structure, integrity hash binding,
behavioral trust score embedding, and the two-tier open/governed
deployment architecture that distinguishes `.agent` from `.nomo`.

**System and Method for Multi-Level Pre-Packaging Behavioral
Verification of AI Agent Manifests with Machine-Computed Trust Score
Embedding, Discrepancy Classification, and Graceful Analysis
Degradation**
Covers the behavioral trust score computation mechanism embedded in
`.agent` and `.nomo` packages at packaging time, including multi-level
pre-packaging verification, machine-computed trust score derivation,
discrepancy classification, and graceful degradation of behavioral
analysis for agents with incomplete or partial behavioral histories.

**System and Method for Cryptographic Identity Birth Certification of
AI Agents with Archetype-Derived Behavioral Prior Initialization and
Certificate Cross-Verification**
Covers the Agent Birth Certificate mechanism defined in Section 5.7 of
the specification, including cryptographic issuance of identity
documents at agent registration time, archetype-derived behavioral prior
initialization, canonical Agent-ID derivation from the certificate hash,
and cross-verification between the Birth Certificate, AGTP Agent
Certificate, and governance-layer registry records.

Implementers of the core AGTP specification are not affected by any
intellectual property claims on these extensions.

## Royalty-Free Commitment

The licensor (Chris Hood / Nomotic, Inc.) is prepared to grant a
royalty-free license to implementers for any patent claims that cover
contributions in the AGTP specification and its referenced extensions,
consistent with the IETF's IPR framework under RFC 8179.

This commitment applies to any party implementing AGTP, including the
core specification and the extensions listed above, without
discrimination and without requirement for a formal license agreement.

## IETF IPR Disclosures

Formal IPR disclosures have been filed with the IETF Secretariat in
accordance with RFC 8179 and are publicly available at:

https://datatracker.ietf.org/ipr/

## Contact

For questions regarding intellectual property or licensing:

Chris Hood
chris@nomotic.ai
Nomotic, Inc.
https://nomotic.ai
```

---

**Where this fits in the repo structure:**
```
/
├── README.md
├── LICENSE                          (CC0 text — generated by GitHub)
├── PATENTS.md                       (this file)
├── CHANGELOG.md                     (add later, tracks -00, -01, etc.)
├── draft-hood-independent-agtp-01.md
├── draft-hood-independent-agtp-01.xml
├── draft-hood-independent-agtp-01.txt
└── draft-hood-independent-agtp-01.html