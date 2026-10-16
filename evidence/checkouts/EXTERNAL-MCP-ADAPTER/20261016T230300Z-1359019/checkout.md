<!--
Riverview Controlled Evidence
File: evidence/checkouts/EXTERNAL-MCP-ADAPTER/20261016T230300Z-1359019/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Record integrated MCP adapter verification after advancing PR base
Execution Model: Local independent HTTP client and isolated PostgreSQL 16.15
Observability: Full test output, canonical process graph and revision audit
Dependencies: PR #69 feature branch; integration base 5221da7
Authority: No production deployment, migration 0011, public routing, or ChatGPT setup
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Revalidate integrated source after base advancement
Tests: full-suite.log; graph-check.json; revision-audit.json; pycompile.log; diff-check.log
History: Git and artifacts.json SHA-256 manifest
-->
# External reasoning MCP adapter — integrated verification

**Integrated merge commit:** `1359019ed377b791ac5b4004a6ca09d735e6797a`

**Feature branch:** `codex/durable-external-reasoning-exchange`

**Integrated base:** `5221da72286aea73bed2fb1ac9aa043a120df2bd`

**PR:** #69 remains open; not merged. No GitHub review approval was recorded.

PR #69's durable exchange and the previously implemented adapter were integrated
with the current base. The conflict resolution preserved both branches' valid
append-only backup-manifest records and unioned revision inventory entries. The
canonical graph projection was regenerated from the merged source. No history was
rewritten.

## Verification on the integrated source

The repository suite ran as the checkout owner against a disposable PostgreSQL
16.15 cluster on port 55494, not production:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
RIVERVIEW_TEST_PG_DSN='host=/var/run/postgresql port=55494 dbname=postgres user=admin1' \
python3 -m unittest discover -s tests -v
```

**Result: 501 tests passed; 0 failures; 0 skipped; 416.430 seconds.** This
includes the independent standard-library `http.client` MCP test and the
PostgreSQL-backed durable exchange through actual loopback HTTP calls. The
isolated cluster was stopped after the run.

- `python3 scripts/process_graph.py check`: 20 graphs / 513 nodes, PASS.
- `python3 scripts/revision_control.py check --baseline revision-baseline.json`:
  PASS, zero issues.
- `python3 -m py_compile` for the MCP adapter, exchange, runner, and relevant
  tests: PASS.
- `git diff --check`: PASS.

The focused 35-test MCP/exchange suite and prior independent client details are
recorded in the parent evidence directory's `20261016T225107Z-7611210` record.

## Transport, identity, and tested boundary

The adapter serves Streamable HTTP JSON-RPC at `/mcp`, default bind
`127.0.0.1:11827`. The client initializes, negotiates one supported protocol
version, lists four fixed provider-scoped tools, claims eligible durable
requests, submits bounded correlated advisory responses, and reads body-free
status. Provider identity is resolved server-side from a bearer token digest in
a protected service credential; the client cannot supply or override provider
identity in tool arguments. Host/Origin checks, HTTP media negotiation,
request-size and concurrency bounds, expiry and exact provider scopes are
applied.

The independent client is a separate HTTP client process/test path but it
connects over Camrui-local loopback. This is not evidence of reachability from an
external network or ChatGPT. The adapter has no token issuer/introspection or
JWT issuer/audience validation; production needs controlled identity/token
provisioning and a reviewed TLS reverse-proxy path. No public listener or route
was created. ChatGPT was not configured.

## Production boundaries and remaining steps

No Camrui deployment, production database change, migration 0011, Caddy routing,
ChatGPT-side configuration, or external-network test occurred. Before external
commissioning: obtain integration review and required PR checks; apply migration
0011 and narrow grants through the approved procedure; provision expiring
provider identities in the protected credential; deploy the loopback service;
configure reviewed TLS routing and resource metadata; then run an independent
client test from outside Camrui. Grace's request delivery and consumption remain
a distinct end-to-end commissioning test.
