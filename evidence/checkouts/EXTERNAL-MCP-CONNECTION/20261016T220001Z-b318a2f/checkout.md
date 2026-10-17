<!--
Riverview Controlled Evidence
File: evidence/checkouts/EXTERNAL-MCP-CONNECTION/20261016T220001Z-b318a2f/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Record source, deployed, external-route and isolated exchange verification
Execution Model: Read-only production checks plus isolated PostgreSQL tests
Observability: Sanitized service/release, HTTP status, migration metadata and test results
Dependencies: PR #69 branch b318a2fc76a2d17dd01e752b3ecfc41042dc8564; PostgreSQL 16
Authority: No ChatGPT configuration, production migration, service change, or deployment
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-CONNECTION-001 | Capture MCP integration preflight
Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
Tests: tests/test_external_reasoning_exchange.py, tests/test_reasoning_escalation.py, tests/test_resident_reasoning.py
History: New evidence record; immutable source in Git
-->
# External MCP connection verification — blocked before transport

**Observed:** 2026-10-16 22:00 UTC (Camrui, America/New_York)

## Source and integration state

- Current checkout: `/tmp/riverview-comms5-current-audit`, branch `codex/durable-external-reasoning-exchange`, source head `b318a2fc76a2d17dd01e752b3ecfc41042dc8564`.
- PR #69: OPEN, not draft; base `codex/grace-conversation-ui-refinement`; head matches this checkout. GitHub controlled-checkout run `38965791378` succeeded. GitHub reports `mergeable=CONFLICTING`; no merge performed.
- PR #69 implements the transport-neutral PostgreSQL exchange in `src/riverview_core/resident_execution/external_reasoning.py` and migration `0011_external_reasoning_exchange.sql`. It contains no MCP server, MCP tool registration, HTTP listener adapter, authentication integration, ChatGPT provider client, or doorbell integration. Migration 0011 is not part of the active production release.
- Grace's internal surface is `DurableExternalReasoningExchange`: authorize and persist, outbox delivery lease/ack/failure, provider claim, bounded correlated response submission, metadata status/events, and Grace consume/ack. Advice is separate from verified facts and does not authorize or execute work.

## Existing and historical MCP inventory

The current `ppow1/Riverview-` source and active Camrui releases contain no MCP package or MCP/Comms/doorbell systemd unit. No local TCP listener exists on 11825 or 11826. The running dashboard and owner-session service do not register the durable exchange as tools.

At historical `ppow1/Riverview` commit `08c1162c4ad04a21df71ed7814a3e22bd9ba41a2`:

- The Comms4/Relay MCP source `src/riverview/mcp/server.py` registered 20 tools, including the four distinct mailbox operations `mailbox_requests`, `mailbox_acknowledge`, `mailbox_claim`, and `mailbox_submit_advisory_response`.
- The separate Comms5 server `src/riverview/mcp/comms5_server.py` registered 21 tools: `comms5_contract_info`, `comms5_help`, `comms5_capabilities`, `comms5_describe_operation`, `comms5_examples`, `comms5_submit_steward_seed`, `comms5_store_specification`, `comms5_seed_status`, `comms5_seed_lineage`, `comms5_objective_status`, `comms5_cme_status`, `comms5_recent_steward_submissions`, `comms5_transport_probe`, `comms5_resource_policy_status`, `comms5_set_resource_policy`, `comms5_set_resource_policy_lock`, `comms5_confirm_and_promote_seed`, `comms5_form_and_queue_work`, `comms5_revalidate_and_queue_work`, `comms5_cancel_draft`, and `comms5_supersede_seed`.
- Historical Comms used stdio and a separate Streamable HTTP wrapper on loopback port 11825. Comms5 used stdio or Streamable HTTP on loopback port 11826. Historical deployment records identify `https://riverview-comms.ionoge.com/comms5/mcp`, Caddy bearer authentication, and a reverse-tunnel path to the loopback service. The deployment record is historical and is not proof that the current PR #69 database/schema is behind that route.
- The historical Playwright doorbell files are Windows-profile/runtime-specific. No Camrui/Linux doorbell adapter or service is present in this checkout or active release.

The stated “19 external tools” count is not confirmed by the pinned historical source: the two historical servers separately register 20 and 21 tools. No current external tool list is served by the active Riverview release.

## Camrui and public-route observations

- `riverview-status-dashboard.service` and `riverview-grace-execution-owner-session.service` were active. The dashboard release pointer resolved to `f957bddb5eda39d4fbd5860ee29f7c32831553b7`; the owner-session pointer resolved to `af87c1a1b8ef4deeb8770c64da8bb4556bc85866`.
- Read-only local service/listener inventory found no Comms, MCP, or doorbell service and no local listener on 11825/11826. These releases predate PR #69.
- Read-only PostgreSQL catalog query found `riverview_dev.schema_migrations` and no row matching `0011` or `external_reasoning`. No migration was applied.
- DNS for the historical Comms5 host resolved to `64.227.21.54`; TLS verification succeeded. A GET and an unauthenticated JSON-RPC `initialize` POST to the documented historical path both returned HTTP 401 from Caddy (`unauthorized`). This proves only that Camrui reached a public HTTPS authentication boundary. It did not prove that authenticated MCP initialization, tool discovery, or request handling work, nor that the upstream serves PR #69.
- An independent web-client open attempt could not access the MCP route. No separate-network authenticated client was available. External-network acceptance is therefore **NOT VERIFIED**.
- Current OpenAI MCP connector guidance uses Streamable HTTP and OAuth 2.1/OAuth resource metadata for user-authenticated access. The legacy route's Caddy-held bearer arrangement is not demonstrated as compatible with the ChatGPT connector. Official references were consulted at `https://developers.openai.com/plugins/build/auth` and `https://developers.openai.com/plugins/build/app-quickstart`; no ChatGPT connection was configured.

## Isolated exchange test

Command:

```text
sudo -n -u postgres env PYTHONPATH=/tmp/riverview-comms5-current-audit/src RIVERVIEW_TEST_PG_DSN='host=<disposable-socket> port=55494 dbname=postgres user=postgres' python3 -m unittest tests.test_external_reasoning_exchange tests.test_reasoning_escalation tests.test_resident_reasoning -v
```

A separate PostgreSQL 16 cluster was initialized under `/tmp/rv-external-exchange-pg.dCyF8N`, socket-only, on a separate port. It was stopped after the run. **30 tests passed, 0 failed, 0 skipped.** No production database or objective was used. The deterministic provider exercised persistence, nonblocking admission, duplicate/idempotent claim and response, exact-grant denial/recheck, stale correlation/fencing, finite expiry/late response, bounded delivery retry, unrelated assignment progress, and restart recovery through adapter reconstruction after response persistence and before Grace consumption.

The full per-test output is preserved in `tests.log`; `artifacts.json` records and verifies its SHA-256 and size.

This is isolated database/service evidence only. It is not an MCP protocol test, live ChatGPT call, external-provider response, or production round trip. Simulated transport failure is not live provider-availability evidence.

## Failure and recovery outcomes

| Test | Result / limit |
|---|---|
| Unauthenticated public route | 401 from Caddy; access correctly rejected, authenticated protocol remains untested. |
| Missing/late response | Isolated deadline and late-response case reaches one durable `expired` state/event; no live remote request was left pending. |
| Duplicate response | Identical idempotency retry returns the same digest; conflicting/stale request correlation is rejected in isolated PostgreSQL. |
| Restart | Exchange adapter reconstruction after durable response recovers for Grace consumption; process-restart-before-delivery preserves eligibility. No production service restart was done. |
| Provider unavailable | Isolated delivery failure and bounded retry pass; no live provider outage/recovery test. |
| Doorbell wake | Not applicable to executed tests; current Linux doorbell integration is absent. No browser wake was attempted. |
| Grace consume | Actual `ResidentReasoner` receives advisory separately from verified facts; durable consumption key is idempotent in isolated tests. |

## Stop condition and next prerequisite

Do not configure ChatGPT to the historical Comms5 URL: that route is not proven to reach the new exchange and its tool surface uses the predecessor Comms5 authority/schema. PR #69's current service needs a reviewed MCP adapter and server-side mapping from authenticated transport principal to the registered external provider identity. The public endpoint, supported user authentication flow, tool allowlist, and current database linkage must then be deployed and verified before a ChatGPT connector is configured.

PR #69 is still open and conflicting; migration 0011 is absent in production. Under the task boundary, no merge, production migration, release activation, or ChatGPT-side configuration was performed. Completion is blocked at MCP transport/authentication and external independent-client acceptance.
