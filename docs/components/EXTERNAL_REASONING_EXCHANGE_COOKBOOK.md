<!--
Riverview~ Controlled Document
File: docs/components/EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md
Component: RESIDENT-REASONING
File Revision: 1.1.4
Purpose: Diagnose durable external reasoning exchange transitions safely
Authority: Read-only diagnostics first; no production migration or transport operation
Changed: 2026-10-16 UTC | RV-EXTERNAL-REASONING-EXCHANGE-001 | Initial troubleshooting guide
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Add adapter checks, authentication handling, and external-client test boundaries
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Correct adapter status guidance and token-map commissioning boundary
Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Document required Accept negotiation and rejection behavior
Changed: 2026-10-17 UTC | RV-MCP-CHATGPT-OAUTH-RESOURCE-001 | Document OAuth issuer/JWKS validation, open discovery, and tunnel prerequisites
Changed: 2026-10-17 UTC | RV-MCP-CHATGPT-OAUTH-RESOURCE-001 | Record official Tunnel operation, authentication separation, and OAuth resource-server implementation
Changed: 2026-10-17 UTC | RV-MCP-CHATGPT-OAUTH-RESOURCE-001 | Document HTTP 401/403 OAuth challenges from the MCP handler
Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Document Grace's live durable response consumer, idempotent acknowledgement and restart diagnostics.
Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Record the owner-session unit name and isolated full-round-trip acceptance boundary.
History: Git and .riverview-backups/manifest.jsonl
-->
# External reasoning exchange troubleshooting

## Grace consumer checks (2026-10-18)

The `riverview-grace-execution-owner-session.service` runner consumes existing
`response_received` exchanges during each bounded cycle. A healthy MCP
listener alone does not demonstrate Grace consumption. Check the Grace health
projection and sanitized log event `grace_external_reasoning_consume_failed`
using request/correlation IDs. Never log response bodies or provider tokens.

If an exchange remains `response_received`:

1. Confirm the Grace execution service is active and its `RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP` maps the request provider to the configured Grace principal.
2. Check that the original request still passes the exact `resident.reasoning.escalate` grant and has not expired.
3. Check `grace_objective_events` for `resident.reasoning.external_advisory_evaluated` with the exact request and correlation IDs. If present, the durable evaluation precedes a pending acknowledgement; the next Grace cycle should acknowledge idempotently.
4. If no event exists, inspect the sanitized failure class and grounding/binding state. The response must remain recoverable; do not mark it consumed manually.
5. Confirm the result is only an unapproved proposal. Work-order creation and execution require their separate existing lifecycle checks.

In this source branch, `GraceExecutionService.request_external_reasoning(...)`
persists an explicitly selected external advisory request before delivery;
the current exchange does not add an MCP request-creation tool. The existing
provider-side MCP operations remain `reasoning_exchange_list_requests`,
`reasoning_exchange_claim_request`, `reasoning_exchange_submit_response`, and
`reasoning_exchange_status`. The owner-session's bounded `run_once` cycle is
the Grace consumer and invokes the existing `consume` followed by
`acknowledge_consumed` methods. Isolated PostgreSQL tests exercise request
creation through this service method, provider claim/response, Grace's model
reasoning, durable proposal/event persistence, interruption before ack, and
idempotent recovery after service recreation. Production acceptance remains
blocked until a valid provider mapping and exact AuthorityRegistry grant are
provisioned and the currently inactive external MCP service is commissioned.

## Stale-base rework checks (2026-10-18)

`comms5_revalidate_and_queue_work` accepts only a durable blocked pre-execution
stale-revision failure without worker results or verifier records. It obtains a
fresh VERIFIED package/repository revision from the configured trusted
knowledge provider. A caller-provided evidence reference is recorded as
provenance but never establishes the new base itself. The original assignment
stays blocked. A successor step waits for existing dependencies and Grace
review; downstream steps are rewired to depend on that successor. If the
provider cannot produce a fresh verified revision, no objective or assignment
mutation is committed.

## MCP transport readiness and diagnostics (2026-10-16)

The durable exchange remains transport-neutral. The adapter is an OAuth
resource server; it does not implement an authorization server, issue tokens,
perform browser wake, or connect an external provider. Its root-protected
subject/client-to-provider map must be provisioned only after the issuer and
exact AuthorityRegistry grant are approved. Keep Grace-only consumption and
delivery lease operations private to the Riverview runtime.

The current development adapter is available through authenticated Streamable
HTTP at `/mcp` when run locally. Its reference unit listens only at
`127.0.0.1:11827`; `GET /healthz` checks exchange relations and the required
narrow runtime ACL, while protected-resource metadata publishes the configured
issuer and scope list. Initialization and `tools/list` are unauthenticated
protocol calls; each listed tool advertises OAuth scopes and every `tools/call`
validates the bearer JWT. Missing/invalid tokens receive HTTP 401 with
`WWW-Authenticate` and MCP `_meta["mcp/www_authenticate"]`; authenticated tokens
without scope receive 403 with `insufficient_scope`. `GET /mcp` returns 405 because
server-initiated SSE is not implemented. POST clients must advertise both
`application/json` and `text/event-stream`; this server returns one JSON
object and does not open an SSE stream. A successful loopback MCP
handshake is not evidence of a public route or internet reachability.
POST rejects a missing/unacceptable media-type pair with HTTP 406 and a
non-JSON request body type with HTTP 415; rejected requests are closed without
logging or parsing the body.

For a ChatGPT web connection, the external authorization server must expose
OAuth/OIDC discovery, authorization-code + PKCE `S256`, token endpoint auth
metadata, CIMD or DCR registration, and tokens whose audience exactly matches
the configured MCP resource URL. The adapter validates issuer, audience,
signature, expiration, scope, subject, and client ID/authorized party on each
tool call. Authorization server, user consent and token issuance remain
external. Do not treat legacy Caddy static bearer authentication as compatible
with ChatGPT. See OpenAI's official [MCP authentication contract](https://developers.openai.com/plugins/build/auth) for current requirements.

Secure MCP Tunnel is a transport option that can keep the Riverview MCP service
private and avoid inbound firewall/DNS/Caddy changes. It is not the OAuth
issuer: OpenAI documents that OAuth discovery can pass through the tunnel, but
the authorization server itself is not automatically tunneled. The tunnel also
requires an OpenAI Platform `tunnel_id`, a runtime API key for `tunnel-client`,
Tunnels Read+Manage to create/configure, and Read+Use to run/select it, plus
ChatGPT workspace access to custom MCP. The official guide does not state
pricing. Treat Platform API-key/account entitlement and any charge as an
unverified external dependency; do not create a key or tunnel until the account
owner confirms permitted billing and grants. The tunnel key authenticates the
local tunnel client to OpenAI's tunnel control plane; it does not authenticate
ChatGPT users to Riverview or replace OAuth. See the official [Secure MCP Tunnel guide](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

The supported deployment pattern for this adapter is a Linux `tunnel-client`
process on Camrui, running under a dedicated systemd identity and forwarding to
the existing loopback `/mcp` listener. It opens outbound HTTPS to OpenAI and
requires no inbound port or Caddy route. OpenAI's current Tunnel guide explicitly
supports a VM/systemd host and private MCP HTTP target. The ChatGPT setup still
requires the user to choose **Connection: Tunnel**, select the provisioned
tunnel, choose **Authentication: OAuth**, then complete the issuer login and
consent. `No authentication` is not acceptable for this provider-scoped write
surface. No tunnel ID, Platform runtime key, `tunnel-client`, OAuth issuer, or
ChatGPT connection is currently commissioned. The API-key pricing/entitlement
impact is not stated in the official guide and must be confirmed by the account
owner before provisioning.

OAuth remains independently required with Tunnel. The MCP protected-resource
metadata can be delivered through the tunnel, but the authorization server must
be reachable by the browser/ChatGPT OAuth flow. The adapter is only a resource
server: it validates the OAuth signature, exact issuer and audience, expiry,
scope, and a preconfigured subject/client pair mapped to one fixed provider
principal. The OAuth issuer must preserve ChatGPT's `resource` parameter as the
access-token audience and support authorization code with PKCE `S256` plus a
ChatGPT-compatible CIMD or DCR method. An approved issuer and exact provider
identity map remain prerequisites.

Do not configure an external client against the historical Comms5 route merely
because its DNS name responds. The legacy route uses a separate predecessor
tool/schema and its public `401` only proves that the HTTPS authentication
boundary was reached. It does not prove that current exchange tools are served.
The 2026-10-16/17 production evidence is recorded in
`evidence/checkouts/EXTERNAL-MCP-CONNECTION/20261016T234651Z-stage-a-b-auth/checkout.md`.
It records an inactive MCP unit, absent provider mapping and absent exact
escalation grant. Do not enable service or claim external acceptance until a
valid issuer map, exact grant, and independent ChatGPT tool call are evidenced.

The independent development client test is
`tests/test_external_reasoning_mcp.py`; the PostgreSQL-backed adapter round-trip
is `ExternalReasoningExchangePostgresTests.test_mcp_provider_scoped_round_trip_uses_durable_exchange`.
The tests use synthetic provider tokens and synthetic advisory data only. They
do not prove an internet route, authorization-server issuance, ChatGPT client
compatibility, migration 0011 production installation, Grace outbound request
delivery, or production Grace consumption.

| Signal | First read-only check | Safe response |
|---|---|---|
| OAuth tool error / `_meta.mcp/www_authenticate` | Check issuer/audience/expiry/scope error code and the configured resource metadata URL without printing token material | Re-authorize through the approved issuer; verify the exact mapped subject/client pair and scope ceiling. Never log bearer values |
| HTTP 403 `host_not_allowed` / `origin_not_allowed` | Compare the request Host/Origin with the reviewed allowlists | Correct only the exact reverse-proxy host/origin values; do not use wildcard hosts |
| `oauth_authorization_server_incompatible` | Check sanitized issuer metadata status for authorization-code, PKCE `S256`, client registration and token endpoint methods | Select/provision a compatible existing issuer; do not fake or weaken metadata checks |
| `provider_not_registered` at startup | Compare protected subject/client mapping provider/principal pairs with provider registrations derived at startup | Preserve requests and correct only the reviewed mapping; do not accept provider IDs from tool arguments |
| `invalid_token` | Check issuer, audience, signature, `exp`, mapped subject/client and scopes from sanitized counters only | Re-authenticate or correct the issuer/resource configuration; never dump or paste the JWT |
| `awaiting_delivery` remains | Inspect bounded status and event codes; test adapter health and current DB migration outside the public endpoint | Keep the exchange durable; retry the pull operation after adapter readiness returns |
| `awaiting_external_claim` / `awaiting_response` | Use `reasoning_exchange_list_requests` then reclaim with the same authenticated principal | Reuse the current request and correlation IDs; fencing and response idempotency reject stale/duplicate actions |
| HTTP 413 or `tool_arguments_invalid` | Check the documented 64 KiB HTTP, 32 KiB context and 16 KiB response bounds | Reduce only the submitted advisory/context within the existing schema; do not raise limits blindly |
| HTTP 406 / `not_acceptable` | Check that `Accept` lists both `application/json` and `text/event-stream` with nonzero quality values | Correct the client media-type negotiation; keep the server response JSON-only |
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

The unit tests use a synthetic RSA-signed JWT and synthetic provider mapping.
They prove local signature/claim validation only; they do not exercise a live
issuer, OAuth browser flow, ChatGPT connector, Platform tunnel, or production
service. Production commissioning also installs the pinned
`deploy/external-reasoning-mcp-requirements.txt` into the release virtualenv,
checks the protected provider map's ownership/mode, confirms the exact Registry
grant via AuthorityRegistry, then runs the service health and independent MCP
client checks. Do not run the deployment until provider identity and exact grant
are issued.
