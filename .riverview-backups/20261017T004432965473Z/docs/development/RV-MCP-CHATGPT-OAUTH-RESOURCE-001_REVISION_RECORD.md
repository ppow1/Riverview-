<!--
Riverview~ Controlled Document
File Revision: 1.0.1
Component: EXTERNAL-REASONING-MCP-TRANSPORT
Task: RV-MCP-CHATGPT-OAUTH-RESOURCE-001
Purpose: Record OAuth resource-server adaptation and Tunnel investigation
Authority: Source and isolated verification only; production and account commissioning remain gated
-->
# RV-MCP-CHATGPT-OAUTH-RESOURCE-001 — OAuth resource server and Tunnel path

## Scope

Added OAuth access-token validation to the existing external-reasoning MCP
adapter and verified OpenAI Secure MCP Tunnel as the preferred transport for
the private Camrui listener. No OAuth authorization server, tunnel client,
production grant, service activation, public route, or ChatGPT app is created by
this increment.

The adapter validates JWT signature, issuer, exact resource audience, expiry,
scope, subject, and client ID/authorized-party against a protected exact
subject/client-to-provider map. Protocol initialization and tool discovery are
unauthenticated; each tool advertises OAuth security metadata, and tool calls
require the token. Missing/invalid tokens return HTTP 401 plus the
`WWW-Authenticate` header and MCP challenge metadata; authenticated requests
without required scope return 403. The launcher rejects the predecessor static bearer
configuration. The existing four advisory tools and durable PostgreSQL
exchange remain the only external operations.

## Source and preserved predecessors

Changed files include `external_reasoning_mcp.py`, its tests and launcher,
service/configuration templates, pinned PyJWT dependency, OAuth/Tunnel
documentation, and the canonical resident-reasoning process graph. Exact
predecessor bytes and checksums are in `.riverview-backups/manifest.jsonl` and
the timestamped task backups.

## Verification

The 10 focused MCP tests and full 507-test isolated PostgreSQL suite passed;
one dashboard runtime-role test was skipped because its production role is not
defined in the disposable cluster. Python compilation, 20-graph/513-node
validation, controlled revision audit, and whitespace check passed. Exact
commands, temporary database boundary, HTTP OAuth handler evidence, and current
limitations are in
`evidence/checkouts/EXTERNAL-MCP-CHATGPT-TUNNEL/20261017T0034Z/checkout.md`.

## Integration and live status

Base checkout: `20d9919b69f6bf8f111c9f1f8c0616f157a813b2` on
`codex/camrui-mcp-commissioning-record-20261016`; PR #74 was the reported open
development vehicle at task start. No merge or deployment occurred. Camrui
SSH for configured account `admin1` was rejected at the known-host IP, so no
live MCP service check or provisioning was made. OpenAI Tunnel is supported as
transport, but it still requires a Platform tunnel ID/key and an independently
reachable OAuth issuer. No issuer or tunnel account configuration was verified.

Do not claim ChatGPT interoperability from synthetic JWT or loopback tests.
Production commissioning requires authorized Camrui access, approved identity
provider and fixed user/client mapping, exact finite AuthorityRegistry grant,
Platform tunnel entitlements/key, live service checks, and an actual ChatGPT
exchange consumed by Grace.
