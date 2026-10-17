<!--
Riverview~ Controlled Document
File: docs/components/EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md
Component: RESIDENT-REASONING
File Revision: 1.0.4
Purpose: Diagnose durable external reasoning exchange transitions safely
Authority: Read-only diagnostics first; no production migration or transport operation
Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial troubleshooting guide
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Add adapter checks, authentication handling, and external-client test boundaries
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Correct adapter status guidance and token-map commissioning boundary
History: Git and .riverview-backups/manifest.jsonl
-->
# External reasoning exchange troubleshooting

## MCP transport readiness and diagnostics (2026-10-16)

The durable exchange remains transport-neutral. Its development adapter
implements a listener and tools, but does not implement an authorization
server, issue tokens, perform browser wake, or connect an external provider.
The bearer-to-provider map is operator-provisioned and must be tied to a
separately reviewed issuer grant. Keep Grace-only consumption and delivery
lease operations private to the Riverview runtime.

The current development adapter is available through authenticated Streamable
HTTP at `/mcp` when run locally. Its reference unit listens only at
`127.0.0.1:11827`; `GET /healthz` checks exchange relations and the required
narrow runtime ACL, while protected-resource metadata publishes the configured
issuer and scope list. Authenticated `GET /mcp` returns 405 by design because
server-initiated SSE is not implemented. POST clients must advertise both
`application/json` and `text/event-stream`; this server returns one JSON
object and does not open an SSE stream. A successful loopback MCP
handshake is not evidence of a public route or internet reachability.

For a future **ChatGPT web** connection, use the supported plugin/hosted MCP
connection flow at the final HTTPS `/mcp` route and its supported user OAuth
setup. Current OpenAI MCP authentication guidance describes OAuth protected-
resource/authorization metadata and the authorization-code + PKCE flow for
user-authenticated connectors. Do not assume the legacy Caddy-held static
bearer is a ChatGPT web connector credential. The separate Codex-host MCP
configuration supports bearer tokens, but that does not make its local config
or static bearer available to ChatGPT web. See
<https://developers.openai.com/plugins/build/auth> and
<https://developers.openai.com/plugins/build/app-quickstart>. Reconfirm the
platform requirements at commissioning time.

Do not configure an external client against the historical Comms5 route merely
because its DNS name responds. The legacy route uses a separate predecessor
tool/schema and its public `401` only proves that the HTTPS authentication
boundary was reached. It does not prove that current exchange tools are served.
The 2026-10-16 preflight is recorded in
`evidence/checkouts/EXTERNAL-MCP-CONNECTION/20261016T220001Z-b318a2f/checkout.md`.
That record confirms the current production limitation: no MCP/doorbell service
is installed and migration 0011 is absent. Do not expose unauthenticated MCP or
claim external acceptance until an independent network client completes MCP
initialization, tool discovery, and a correlated request/response round trip.

The independent development client test is
`tests/test_external_reasoning_mcp.py`; the PostgreSQL-backed adapter round-trip
is `ExternalReasoningExchangePostgresTests.test_mcp_provider_scoped_round_trip_uses_durable_exchange`.
The tests use synthetic provider tokens and synthetic advisory data only. They
do not prove an internet route, authorization-server issuance, ChatGPT client
compatibility, migration 0011 production installation, Grace outbound request
delivery, or production Grace consumption.

| Signal | First read-only check | Safe response |
|---|---|---|
| HTTP 401 / `WWW-Authenticate` | Confirm the configured resource metadata URL and credential-map expiry without printing token material | Obtain a valid issuer token and confirm its digest-to-provider entry; never copy the bearer into logs or evidence |
| HTTP 403 `host_not_allowed` / `origin_not_allowed` | Compare the request Host/Origin with the reviewed allowlists | Correct only the exact reverse-proxy host/origin values; do not use wildcard hosts |
| `provider_not_registered` at startup | Compare credential-map provider/principal pairs with provider registrations derived at startup | Preserve requests and correct the reviewed identity mapping; do not accept provider IDs from tool arguments |
| `awaiting_delivery` remains | Inspect bounded status and event codes; test adapter health and current DB migration outside the public endpoint | Keep the exchange durable; retry the pull operation after adapter readiness returns |
| `awaiting_external_claim` / `awaiting_response` | Use `reasoning_exchange_list_requests` then reclaim with the same authenticated principal | Reuse the current request and correlation IDs; fencing and response idempotency reject stale/duplicate actions |
| HTTP 413 or `tool_arguments_invalid` | Check the documented 64 KiB HTTP, 32 KiB context and 16 KiB response bounds | Reduce only the submitted advisory/context within the existing schema; do not raise limits blindly |
| `GET /mcp` returns 405 | This is expected; Streamable HTTP sends JSON-RPC requests by POST | Use POST with JSON content and Accept headers; SSE is intentionally not implemented |

Use only an isolated PostgreSQL test schema during this development phase. The
exchange stores bounded reasoning context, so do not print request/response
payloads or include them in logs/evidence. Query `status(request_id,
correlation_id)` and `events(...)` for the diagnostic projection.

| State or error | Safe interpretation | Next step |
|---|---|---|
| `awaiting_delivery` | Durable request exists; a delivery attempt has not been acknowledged | Check deadline, provider ID, backoff, delivery lease and sanitized event codes. The transport should take a short lease then acknowledge or fail the attempt. |
| `awaiting_external_claim` | Transport acknowledged delivery; no external claim is durable yet | Check connector availability/schema through its own future diagnostics. Do not create a second request; reuse the idempotency key. |
| `awaiting_response` | A provider claim is active or reclaimable after its lease expires | Check claim fence/expiry metadata. A stale fence cannot submit a response. |
| `response_received` | A correlated, bounded advisory and digest are committed | Grace may acquire a consumption lease. A process restart must resume this state; do not redeliver the request. |
| `grace_consumed` | Grace's existing reasoning path acknowledged a durable result reference | A retry returns the same advisory under the stable consumption key. The continuation must use that key idempotently. |
| `expired` | Deadline passed before completion | Preserve the record. A genuinely new reasoning request requires a new authorized decision and idempotency key. |
| `failed` | Delivery was non-retryable or reached five attempts | Preserve the sanitized failure event. Repair the transport before creating a new request. |
| `exact_grant_required` / `authority_check_unavailable` | Router admission was denied or its authority check failed | No exchange should be created. Use the existing AuthorityRegistry inspection and grant process; never insert a row to bypass it. |
| `idempotency key was reused for a different request` | Caller supplied a key whose immutable context differs | Preserve the existing request. Use the original request for retry or a new authorized request with a new key. |
| `active response claim and fencing token required` | Claim is stale, belongs to another provider, or its lease expired | Reclaim through the selected provider identity and use its newest fence. |
| `response ... schema` / correlation mismatch | Response is malformed or belongs to another exchange | Preserve diagnostics; do not relax response validation. |

The exchange service performs no background polling and makes no provider
network call. It is safe for the existing Grace/CME cycle to keep handling
unrelated assignments while an exchange is pending. A future event consumer
may invoke bounded operations, but it must not block the assignment event
processor while waiting for ChatGPT.

## Isolated PostgreSQL verification

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<private disposable PostgreSQL 16 socket DSN>' \
  python3 -m unittest tests.test_external_reasoning_exchange -v
```

Expected: all exchange integration tests execute (no DSN skip), use a unique
`rvtest_*` schema, and drop only that schema in teardown. Never use the shared
`riverview_dev` database for this suite. After an interrupted isolated run,
identify only the schema created by that run before cleanup.

The package/runtime projection is intentionally metadata-only. No MCP endpoint,
browser session, ChatGPT application schema, Playwright profile, or production
service is exercised by these tests.
