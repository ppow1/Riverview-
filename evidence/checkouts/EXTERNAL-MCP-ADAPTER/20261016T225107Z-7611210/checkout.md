<!--
Riverview Controlled Evidence
File: evidence/checkouts/EXTERNAL-MCP-ADAPTER/20261016T225107Z-7611210/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.1
Purpose: Record implementation, independent MCP client and isolated PostgreSQL verification
Execution Model: Local loopback Streamable HTTP; disposable PostgreSQL 16.15
Observability: Protocol outcomes, test summaries, graph/revision checks and artifact digests
Dependencies: PR #69 branch codex/durable-external-reasoning-exchange
Authority: No production deployment, migration 0011, Caddy route, or ChatGPT configuration
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Verify source MCP transport and durable provider exchange
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Normalize Markdown evidence formatting
Tests: full-suite.log; focused-tests.log; graph-check.json; revision-audit.json; pycompile.log
History: Git and artifacts.json SHA-256 manifest
-->
# External reasoning MCP adapter verification

**Source revision:** `7611210aeb04db0292d03964b6c4b2cb7f473589`

**Branch:** `codex/durable-external-reasoning-exchange`

**Integration base:** `50e1e44`

**PR:** #69 (open; not merged)

**Observed:** 2026-10-16 UTC

## Integration

Refreshed the PR base from `origin/codex/grace-conversation-ui-refinement` and
merged it into the feature branch at `c37c8e17aeaddb29c285fd1c7714a12c56726a89`.
The only conflict was `.riverview-backups/manifest.jsonl`; the resolution kept
the full valid union of append-only records. The earlier uncommitted exchange
verification record was preserved as commit `ac67e44` before integration.

## Implemented

- Added an authenticated, sessionless MCP Streamable HTTP JSON-RPC adapter over
  `DurableExternalReasoningExchange`, defaulting to loopback port 11827.
- Added bearer-digest-to-fixed-provider/principal/scope/expiry mapping loaded
  from a protected systemd credential. Provider identity is not accepted in
  tool arguments; no Steward, resident, or Engineering authority is conveyed.
- Registered four provider-scoped tools: list pending request, claim correlated
  request, submit bounded structured advisory, and inspect body-free status.
  Grace consumption and Engineering functions are not exposed.
- Added runtime-readiness checks for migration relations and narrow exchange
  permissions, without applying migrations or reading authority ledgers.
- Added loopback-only systemd unit and a non-secret environment template. These
  are source artifacts only and were not installed or started.
- Updated exchange recovery selection for pending requests and added provider-
  scoped, body-free status.
- Updated the canonical resident-reasoning workflow and generated views.

## Independent client and database result

`tests/test_external_reasoning_mcp.py` uses Python's independent `http.client`
transport to make actual TCP loopback HTTP requests to a separately running
server. It verifies MCP initialization, protocol selection, `notifications/initialized`,
tool discovery, protected-resource metadata, unauthenticated denial, Host
rejection, Accept negotiation, and prevention of client-selected provider
identity.

The PostgreSQL integration test submits a synthetic exchange and drives list,
claim, response submission, and status using those HTTP MCP requests—not a
mocked JSON-RPC dispatcher. The adapter persists through the existing exchange
ledger; the result remains advisory-only and status omits response contents.

Focused command (run as the test owner against the isolated PostgreSQL socket):

```text
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='host=/var/run/postgresql port=55494 dbname=postgres user=admin1' python3 -m unittest tests.test_external_reasoning_exchange tests.test_external_reasoning_mcp tests.test_reasoning_escalation tests.test_resident_reasoning -v
```

Result: **35 tests passed, 0 failures, 0 skips**.

Full repository command:

```text
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='host=/var/run/postgresql port=55494 dbname=postgres user=admin1' python3 -m unittest discover -s tests -v
```

Result: **500 tests passed, 0 failures, 0 skips** in 431.849 seconds.
The disposable PostgreSQL 16.15 cluster used a separate data directory and
port 55494. It was stopped after verification. The test-only `admin1` and
`riverview_core` roles existed only inside that temporary cluster.

`python3 -m py_compile` passed for the touched Python implementation, runner,
and tests. `python3 scripts/process_graph.py check` passed for 20 workflows /
513 nodes. `python3 scripts/revision_control.py check --baseline revision-baseline.json`
passed with zero issues. `git diff --check` passed.

## Protocol and authentication boundary

Transport is Streamable HTTP JSON-RPC POST at `/mcp`. The adapter supports MCP
protocol versions `2025-03-26`, `2025-06-18`, and `2025-11-25`; it returns one
JSON response and does not implement server-initiated SSE, so authenticated
GET `/mcp` returns 405. POST requires both `application/json` and
`text/event-stream` in `Accept`. Authorization uses a bearer token whose
SHA-256 digest is mapped server-side to one provider principal and exact local
scopes. Protected-resource metadata and a 401 challenge are implemented.

This does **not** implement or commission an OAuth authorization server, token
issuance/introspection, an external TLS endpoint, or ChatGPT configuration.
The issuer URL and provider-token map require separate controlled provisioning.
The tests establish an independent loopback HTTP client path, not access from
the public internet or another network.

## Production boundary and remaining commissioning gates

No Camrui service was installed, enabled, started, or restarted. Migration 0011
was not applied. Caddy/public routing and ChatGPT were not changed. No
production database, objective, conversation, or authority record was touched.

Before a real external client can use the exchange, production requires the
approved migration and least-privilege database grants, a provisioned
authorization server and expiring provider identity mapping, a reviewed public
TLS/reverse-proxy route to the loopback service, deployment/health verification,
and a client outside the host completing initialization, tool discovery, and
a durable synthetic advisory round trip. Grace's existing delivery and
consumption workflow must then be commissioned independently.
