<!--
Riverview Controlled Document
File: docs/development/RV-EXTERNAL-MCP-ADAPTER-001_REVISION_RECORD.md
Component: RESIDENT-REASONING
File Revision: 1.0.1
Purpose: Record authenticated external reasoning MCP adapter implementation and verification
Authority: Provider-scoped advisory exchange only; no production migration or deployment
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Implement and independently exercise the MCP adapter
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Remove trailing-space Markdown hardbreaks
History: Git and .riverview-backups/manifest.jsonl
-->
# RV-EXTERNAL-MCP-ADAPTER-001 — MCP adapter implementation

**Implementation source commit:** `7611210aeb04db0292d03964b6c4b2cb7f473589`

**Branch:** `codex/durable-external-reasoning-exchange`

**PR:** #69, OPEN; no merge or production deployment performed

**Status:** Source and isolated acceptance verified; external network and provider commissioning remain open.

## Scope delivered

PR #69's durable exchange is connected to a standard-library Streamable HTTP
MCP server. The listener binds loopback by default. It advertises supported
MCP protocol versions, performs initialize/tool discovery, enforces Host and
Origin allowlists, authenticates every MCP endpoint request, and exposes only
four fixed provider-scoped tools. The caller cannot select its provider ID in
arguments. Provider tokens are stored as SHA-256 digests in a protected
systemd credential and map to one provider principal, bounded scopes, and an
expiry. The adapter does not provide Grace consumption or Engineering tools.

The MCP adapter reuses `DurableExternalReasoningExchange` and `PostgresLedger`.
It introduces no scheduler, mailbox, inference client, or alternate reasoning
loop. The server does not apply migration 0011. Its readiness projection checks
only exchange tables and required narrow ACLs.

## Integration reconciliation

Before integrating, the current PR base was fetched and its source state
verified. PR #69 had one integration conflict in the append-only predecessor
backup manifest. The feature branch was merged with the current integration
branch and the conflict was resolved by preserving the valid record union.
Commit `c37c8e17aeaddb29c285fd1c7714a12c56726a89` records that merge. No Git
history was rewritten. PR #69 remains open; this assignment did not authorize
merging it.

## Verification

The test-only PostgreSQL 16.15 cluster and loopback HTTP server were isolated
from production. The independent Python `http.client` test exercised HTTP
initialization, tool discovery, auth denial, metadata, Host rejection, media
negotiation, and fixed provider identity. A PostgreSQL-backed test drove the
actual list/claim/submit/status tools over HTTP and asserted durable state,
response digest, and body-free status.

- Focused reasoning/exchange regression suite: **35 passed, 0 failed, 0 skipped**.
- Full repository unittest discovery: **500 passed, 0 failed, 0 skipped**.
- Python compilation: passed for changed implementation, launcher, and tests.
- Canonical process graphs: **20 graphs / 513 nodes; PASS**.
- Controlled predecessor revision audit: **PASS, zero issues**.
- Git whitespace check: PASS.

Test logs, checksums, the exact revision baseline, graph/revision outputs, and
limitations are recorded in
[`isolated adapter evidence`](../../evidence/checkouts/EXTERNAL-MCP-ADAPTER/20261016T225107Z-7611210/checkout.md).

## Production and external status

Nothing was deployed to Camrui; migration 0011 was not applied; no public Caddy
route or ChatGPT configuration was changed. The token map is operator-
provisioned and the adapter does not implement OAuth token issuance or
introspection/JWT issuer-audience validation. The HTTP tests connect to a
loopback listener and do not establish public-internet reachability or external
ChatGPT interoperability.

Production commissioning still requires the approved migration and narrow
runtime grants, actual authorization-server/token-map provisioning, controlled
service deployment, a reviewed external TLS route, and an external-network
MCP client demonstration. Grace outbound delivery and consumption are separate
operational acceptance steps; this change proves the inbound MCP seam only.
