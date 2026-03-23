---
title: "AGTP Web3 Bridge Specification"
abbrev: "AGTP-WEB3"
docname: draft-hood-agtp-web3-bridge-00
category: info
submissiontype: independent
ipr: trust200902
area: "Applications and Real-Time"
workgroup: "Independent Submission"
keyword:
  - AI agents
  - Web3
  - blockchain
  - agent identity
  - decentralized identity

stand_alone: yes
pi:
  toc: yes
  sortrefs: yes
  symrefs: yes
  strict: yes
  compact: yes

author:
  - fullname: Chris Hood
    organization: Nomotic, Inc.
    email: chris@nomotic.ai
    uri: https://nomotic.ai

normative:
  RFC2119:
  RFC8174:
  AGTP:
    title: "Agent Transfer Protocol (AGTP)"
    author:
      fullname: Chris Hood
    seriesinfo:
      Internet-Draft: draft-hood-independent-agtp-02
    date: 2026

informative:
  AGTP-CERT:
    title: "AGTP Agent Certificate Extension"
    author:
      fullname: Chris Hood
    seriesinfo:
      Internet-Draft: draft-hood-agtp-agent-cert-00
    date: 2026
  W3C-DID:
    title: "Decentralized Identifiers (DIDs) v1.0"
    author:
      org: W3C
    date: 2022
    target: https://www.w3.org/TR/did-core/
  EIP-137:
    title: "Ethereum Name Service"
    author:
      org: Ethereum Foundation
    date: 2016
    target: https://eips.ethereum.org/EIPS/eip-137

--- abstract

The Agent Transfer Protocol (AGTP) uses a PKI-based trust model: agent
identity is anchored to DNS-verified domain ownership and CA-issued
X.509 certificates. Web3 systems offer an alternative identity model
based on blockchain address ownership, smart contract verification, and
decentralized naming systems including the Ethereum Name Service (ENS)
and Unstoppable Domains. This document specifies the AGTP Web3 Bridge:
a framework for mapping Web3 identity anchors to AGTP trust tiers,
resolving Web3 names to canonical AGTP Agent-IDs, and operating AGTP
sessions with agents whose identity is anchored to blockchain rather
than DNS. Web3-anchored agents are treated as Trust Tier 2 (Org-Asserted)
in the absence of additional verification. This document also defines
the conditions under which a Web3 identity MAY be elevated to Trust
Tier 1 through a hybrid verification procedure.

--- middle

# Introduction

## Two Identity Models

AGTP's default trust model is PKI-based. An agent's identity is anchored
to a real-world domain (e.g., `acme.tld`), verified through DNS ownership
challenge per, and bound to a CA-signed certificate chain.
This model inherits decades of web PKI infrastructure and integrates
cleanly with enterprise certificate management systems.

Web3 systems provide a different identity model. In Web3, identity is
anchored to a blockchain address: a cryptographic key pair whose public
address is a first-class identifier. Ownership of a blockchain address
is proven by signing a challenge with the corresponding private key.
Web3 naming systems (ENS, Unstoppable Domains) map human-readable names
to blockchain addresses, analogous to DNS mapping names to IP addresses.

These models are not mutually exclusive. An organization may hold both
a verified DNS domain and blockchain-anchored assets. An agent may
legitimately derive its identity from either model. AGTP must
interoperate with both.

## Scope and Status

This document is informational. The Web3 ecosystem is evolving rapidly,
and a fully normative specification would risk premature standardization
of mechanisms that have not stabilized. This document defines:

- The `resolution_layer` field values for Web3 identity anchors
  (already defined in {{AGTP}} Section 6.6)
- Mapping rules from Web3 identity to AGTP Trust Tiers
- Name resolution procedures for ENS and Unstoppable Domains
- A hybrid verification procedure for Trust Tier 1 elevation
- Security considerations specific to Web3-anchored agents

Implementers **MAY** use this document as guidance. A future normative
revision will be issued as the Web3 identity landscape stabilizes.

# Terminology

The key words "**MUST**", "**MUST NOT**", "**REQUIRED**", "**SHALL**",
"**SHALL NOT**", "**SHOULD**", "**SHOULD NOT**", "**RECOMMENDED**",
"**NOT RECOMMENDED**", "**MAY**", and "**OPTIONAL**" in this document
are to be interpreted as described in BCP 14 {{RFC2119}} {{RFC8174}} when,
and only when, they appear in all capitals.

Blockchain Address:
: A cryptographic public key hash serving as a first-class identifier
  on a blockchain network (e.g., an Ethereum address of the form
  0x... or a Solana address in base58 encoding).

ENS (Ethereum Name Service):
: A distributed naming system built on the Ethereum blockchain that
  maps human-readable names (e.g., `acme.eth`) to Ethereum addresses
  and other records. Defined in {{EIP-137}}.

Unstoppable Domains:
: A blockchain-based naming system providing human-readable domain names
  (e.g., `acme.crypto`, `acme.nft`) anchored to blockchain addresses.

DID (Decentralized Identifier):
: A globally unique identifier defined by {{W3C-DID}} that enables
  verifiable, decentralized digital identity without dependence on a
  centralized registry.

Web3 Trust Anchor:
: A blockchain address, ENS name, Unstoppable Domain name, or DID that
  serves as the primary identity anchor for a Web3-registered agent.

# Web3 Identity Anchors and AGTP Trust Tiers

## Default Trust Tier Assignment

{{AGTP}} Section 6.6 defines the `resolution_layer` field in the Agent
Manifest Document and specifies that Web3-anchored agents **MUST** be
treated as Trust Tier 2 (Org-Asserted) in the absence of additional
verification:

| resolution_layer Value | Default Trust Tier | Notes |
|---|---|---|
| `dns` | Tier 1 (if DNS challenge passed) | Standard AGTP default |
| `pki` | Tier 2 | PKI without DNS challenge |
| `web3-ens` | Tier 2 | ENS name ownership verified |
| `web3-unstoppable` | Tier 2 | Unstoppable Domains ownership verified |
| `web3-did` | Tier 2 | DID method-specific verification |
| `agtp-registry` | Tier 2 | Direct registry registration, no domain anchor |
{: title="resolution_layer Values and Default Trust Tiers"}

Trust Tier 2 means the agent's identity is asserted and verifiable
(ownership of the blockchain address is provable) but the agent has
not been verified as representing a specific real-world organization
through DNS. The `trust_warning: "org-label-unverified"` field
**MUST** appear in the Agent Manifest Document for all Web3-anchored
agents at default Trust Tier 2.

## Trust Tier 1 Elevation for Web3 Agents

A Web3-anchored agent **MAY** be elevated to Trust Tier 1 through a
hybrid verification procedure that combines blockchain address ownership
proof with DNS ownership verification:

1. The agent operator proves ownership of the blockchain address by
   signing an AGTP-issued challenge with the corresponding private key.

2. The agent operator publishes a DNS TXT record at `_agtp.[domain.tld]`
   containing the blockchain address:

~~~~
_agtp.acme.tld. IN TXT "agtp-web3=0x1a2b3c...; chain=ethereum"
~~~~

3. The AGTP governance platform verifies both the blockchain signature
   and the DNS TXT record.

4. On successful dual verification, the agent is registered at Trust
   Tier 1 with `resolution_layer: web3-ens` (or equivalent) and the
   DNS anchor recorded in the Agent Manifest Document.

This hybrid procedure establishes that the same entity controls both
the blockchain address and the DNS domain, providing a trust level
equivalent to standard DNS-anchored verification.

# Name Resolution

## ENS Resolution

ENS names (e.g., `acme.eth`) resolve to Ethereum addresses through
the ENS registry smart contract. AGTP implementations that support
ENS resolution **MUST**:

1. Query the ENS registry contract for the address record associated
   with the ENS name.

2. Verify that the resolved address matches the `blockchain_address`
   field in the agent's registration record.

3. Verify that the agent's canonical Agent-ID is recorded in the ENS
   name's text records under the key `agtp-agent-id`.

ENS text record format:

~~~~
Key: agtp-agent-id
Value: 3a9f2c1d8b7e4a6f...
~~~~

AGTP resolution **MUST** treat the ENS text record as informational
only. The canonical Agent-ID in the AGTP registry is authoritative.
If the ENS text record conflicts with the AGTP registry, the AGTP
registry value **MUST** be used.

## Unstoppable Domains Resolution

Unstoppable Domains names resolve through a blockchain registry
contract specific to each domain extension (`.crypto`, `.nft`, `.x`,
etc.). AGTP implementations that support Unstoppable Domains resolution
**MUST** follow the same verification procedure as ENS, adapted for
the specific registry contract of the domain extension.

Unstoppable Domains record format:

~~~~
Key: agent.agtp.id
Value: 3a9f2c1d8b7e4a6f...
~~~~

## DID Resolution

W3C Decentralized Identifiers {{W3C-DID}} provide a method-agnostic
framework for decentralized identity. AGTP implementations that support
DID resolution **MUST**:

1. Resolve the DID Document using the DID method-specific resolver.

2. Extract the AGTP-specific service endpoint from the DID Document:

~~~~json
{
  "service": [
    {
      "id": "#agtp",
      "type": "AgentTransferProtocol",
      "serviceEndpoint": "agtp://agtp.acme.tld/agents/my-agent",
      "agtp_agent_id": "3a9f2c1d8b7e4a6f..."
    }
  ]
}
~~~~

3. Resolve the `serviceEndpoint` URI to the agent's canonical AGTP
   Agent Manifest Document.

4. Verify that the `agtp_agent_id` in the DID Document matches the
   `canonical_id` in the Agent Manifest Document.

# Operating AGTP Sessions with Web3-Anchored Agents

## Session Establishment

AGTP sessions with Web3-anchored agents follow the standard AGTP
session model defined in {{AGTP}}. The `resolution_layer` field in
the Agent Manifest Document declares the trust anchor type; the
requesting agent **MUST** retrieve and verify the manifest before
establishing a session.

If the requesting agent requires Trust Tier 1 (e.g., for financial
transactions or cross-organization delegation), it **MUST** reject
connection attempts from Tier 2 Web3-anchored agents unless the hybrid
verification described in Section 3.2 has been completed and is
reflected in the agent's Trust Tier.

## Authority-Scope Constraints

Web3-anchored agents at Trust Tier 2 **MUST NOT** be granted authority
scopes above `documents:query` and `knowledge:query` without AGTP-CERT
cryptographic identity binding per {{AGTP-CERT}}, as specified in
{{AGTP}} Section 6.1.6.

AGTP-CERT binding for Web3-anchored agents follows the same certificate
issuance process as for DNS-anchored agents, with the blockchain address
ownership proof substituted for or supplemented by the DNS challenge.

## Governance Token Compatibility

Governance Tokens issued for Web3-anchored agents follow the standard
Governance Token format defined in {{AGTP}} Section 6.7.7. The
`agent_id` field in the Governance Token **MUST** match the agent's
canonical AGTP Agent-ID (the 256-bit hash form), not the blockchain
address or Web3 name.

# Security Considerations

## Blockchain Reorganization

Blockchain networks are subject to reorganization events in which
recently confirmed transactions may be reversed. In AGTP context, a
blockchain reorganization could theoretically reverse the publication
of an ENS text record or Unstoppable Domains record used in agent
verification.

Mitigation: AGTP implementations **SHOULD** require a minimum
confirmation depth before treating blockchain-based verification as
complete. The recommended minimum is 12 blocks for Ethereum mainnet.
Implementations operating on proof-of-stake networks with finality
guarantees **MAY** use the finality checkpoint instead of a block
depth threshold.

## ENS Name Expiry

ENS names require periodic renewal. If an ENS name expires and is
acquired by a different party, the new owner could publish an AGTP
agent ID that points to an agent the original owner registered.

Mitigation: AGTP governance platforms **MUST** monitor ENS name
expiry for all registered Web3-anchored agents and treat an expired
ENS name as equivalent to an expired DNS domain per {{AGTP}} Section 9.6.
Agents under an expired ENS name **MUST** be automatically Suspended.

## Private Key Compromise

A blockchain address is only as secure as its private key. Private key
compromise grants an attacker the ability to prove ownership of the
address and potentially re-register agents or modify ENS records.

Mitigation: Web3-anchored agent operators **SHOULD** use hardware
wallets or multi-signature schemes for blockchain addresses used in
AGTP registration. Private key rotation **MUST** trigger immediate
agent re-registration with the new address and **MUST** be logged in
the governance audit trail.

## Smart Contract Vulnerabilities

ENS and Unstoppable Domains registry contracts are smart contracts.
Smart contract vulnerabilities could allow attackers to modify name
resolution records without controlling the associated private key.

Mitigation: AGTP implementations **SHOULD** monitor the security status
of registry contracts they rely on and be prepared to treat affected
resolutions as untrusted pending contract remediation. This document
does not specify a normative procedure for contract vulnerability
response; that is governed by the respective naming system's security
policies.

# IANA Considerations

This document defines no new IANA registrations. The `resolution_layer`
field values `web3-ens`, `web3-unstoppable`, and `web3-did` are defined
in {{AGTP}} Section 6.6.2 and do not require separate registration.

The DNS TXT record key `agtp-web3` used in hybrid verification is a
conventional identifier within the `_agtp` subdomain established by
{{AGTP}} Section 6.1.6. No formal IANA registration is required for
this key.

--- back

# Web3 Ecosystem Status Note

The Web3 identity landscape is evolving rapidly. ENS and Unstoppable
Domains are the most widely deployed blockchain naming systems at the
time of this writing, but the field is not settled. W3C DIDs provide
a method-agnostic framework that may become the preferred abstraction
layer for decentralized identity in agent systems.

This document is intentionally informational to avoid premature
normative commitment. Implementers should treat the procedures in this
document as best-current-practice guidance subject to revision as the
Web3 ecosystem stabilizes.
