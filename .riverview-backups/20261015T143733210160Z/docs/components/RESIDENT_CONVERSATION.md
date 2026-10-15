<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_CONVERSATION.md
Component: RESIDENT-CONVERSATION
File Revision: 1.1.23
Purpose: Specify authenticated persistent conversation with the office-bound Grace resident
Authority: Dashboard authentication plus exact resident.conversation.read/send grants; chat is not work authorization
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Initial isolated conversation contract and operator procedure
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Set a short CPU-model response budget and record observed timeout evidence
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Document model-specific inference prefix and real browser verification approach
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Record committed-source local Firefox and PostgreSQL commissioning evidence
Changed: 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Serialize shared PostgreSQL connection use and fail closed on leaked transactions
Changed: 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Record successful Camrui recommission and remaining temporary-model limitation
Changed: 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Record live pending-turn interruption recovery and verified browser rendering
Changed: 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Reproduce exact predecessor six-versus-four event visibility gap in isolated PostgreSQL
Changed: 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Retain the exact predecessor reproduction source and sanitized result
Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Specify complete conversational rendering, accessible controls, factual details, and safe copy behavior
Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Record dashboard-only live release and distinguish local commissioning from Steward Windows acceptance
Changed: 2026-10-13 UTC | RV-GRACE-MULTI-STAGE-001 | Record exact OCTO1 provider opt-in, readiness states, and the unimplemented routing/deferral boundary
Changed: 2026-10-13 UTC | RV-GRACE-MULTI-STAGE-001 | Clarify local slot contention is not global OCTO1 slot telemetry
Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Document opt-in audited router continuity, grant revalidation, provenance, and durable claims
Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-CAPABILITY-001 | Pin deferred retries to their original capability and request context; emit redacted retry diagnostics
Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Supply canonical Grace office identity and responsibilities to all model turns
Changed: 2026-10-14 UTC | RV-GRACE-DOPS-TOOLBOX-001 | Ground ordinary and resumed turns in bounded read-only institutional projections with durable context provenance
Changed: 2026-10-14 UTC | RV-GRACE-DOPS-TOOLBOX-001 | Include the existing Grace execution health projection and classify snapshot evidence explicitly
Changed: 2026-10-14 UTC | RV-GRACE-DOPS-OBSERVATION-PERSISTENCE-001 | Retain the bounded input observation snapshot in the append-only response event
Changed: 2026-10-14 UTC | RV-GRACE-80B-COMPLETION-BUDGET-001 | Bound conversation output at 512 tokens and record non-stop finish diagnostics
Changed: 2026-10-13 UTC | RV-GRACE-MULTI-STAGE-001 | Document endpoint/model pair pinning and explicit dashboard opt-in
Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Record deployed 390 CSS-pixel responsive fixture while retaining physical-device and Windows verification as pending
Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Add persistent same-origin browser credential transport, exact-grant rechecks, and denial retry suppression
Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Record diagnosed credential retention gap, grant audit, and browser restart evidence
Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Record Camrui live Firefox inference, PostgreSQL durability, and dashboard restart recovery
Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Connect linked account Steward sessions to existing exact conversation grants
Changed: 2026-10-13 UTC | RV-GRACE-CONVERSATION-WORKORDER-CONTRACT | Document explicit, exact-grant promotion of a persisted user message
Changed: 2026-10-13 UTC | RV-GRACE-MULTISTAGE-ROUTING-001 | Specify opt-in model routing, durable deferral and reversible model binding
Changed: 2026-10-13 UTC | RV-GRACE-MULTISTAGE-ROUTING-001 | Constrain CPU fallback to non-factual acknowledgements and clarify readiness unknowns
Changed: 2026-10-14 UTC | RV-GRACE-ROUTING-DIAGNOSTICS-001 | Prefer 80B outside narrow provisional class; persist bounded per-attempt metadata and use stage-specific timeouts
Changed: 2026-10-13 UTC | RV-GRACE-ROUTER-ACL-READINESS-001 | Verify runtime-readable migration and active authority binding without reading protected migration ledgers
Changed: 2026-10-14 UTC | RV-GRACE-ROUTING-INTEGRATION-001 | Reconcile merged startup-readiness and routing-diagnostics requirements
Changed: 2026-10-15 UTC | RV-GRACE-SINGLE-RESIDENT-IDENTITY-001 | Specify one Grace identity across autonomic, vision and reasoning stage prompts
Changed: 2026-10-15 UTC | RV-GRACE-CHAT-CONTEXT-BOUND-001 | Bound routed messages to the provider limit while preserving system context and the latest turn
Changed: 2026-10-15 UTC | RV-GRACE-AUTONOMIC-LATENCY-BOUND-001 | Cap 0.6B acknowledgment generation at 32 tokens and set its measured 60-second socket timeout
History: Git and .riverview-backups/manifest.jsonl
-->
# Grace resident conversation

## Institutional and operational context

Every ordinary and resumed model turn receives the same stable role context
from `resident_execution/grace_role_context.py` (role-context revision 1.0.0):
Grace is the continuing occupant of `office:grace` and Director of Operations;
Alfred is the separate Chief of Staff; the Steward retains final authority.
The context describes CME progression, operational awareness, Engineering and
resource coordination, routing, observation, recovery, and exception escalation.
It explicitly grants no permission. The backend continues to authorize actions
through the existing exact-grant and governed workflow services.

The router's stage-specific system instruction must preserve that same resident
identity. It describes the 0.6B autonomic, 30B vision/interim, or 80B reasoning
as the capability serving the current turn, never as a separate Grace, resident,
office, or agent. The stage may constrain the response, but it cannot redefine
Grace's title, institutional identity, authority, or continuity.

`resident_execution/operational_context.py` supplies the named read-only
capability `grace.operations.snapshot.read.v1` by adapting the existing
`DashboardProjection`; it is not a new database reader or model-selected tool
interface. It includes bounded CME health, assignment/workflow identities,
objective status and verification decision, worker readiness, Grace execution
health, and Steward attention summaries. It excludes request and acceptance text, conversation
bodies, payloads, artifact paths, and credentials. The snapshot labels
projection status and observation timestamps, and the append-only conversation
response event stores the bounded snapshot with its capability, status,
timestamps, and canonical SHA-256 digest. The same metadata shape is retained
for deferred and failed requests when a snapshot was obtained, so later
continuation can distinguish the original observation from a refreshed one.
Unavailable or oversized context is labeled; it does not create authority or
an action. Model-generated instructions inside values are not executable.
Additional historical knowledge retrieval, richer resource readiness, and
typed action tools remain future integration work.

**Status:** Isolated engineering implementation on the proposed M3.4 workstream. The roadmap's M3.4 sequencing proposal has not been formally accepted; this work does not claim roadmap acceptance, production commissioning, or full Component Definition of Done.

## Identity and authority

The resident office, currently bound occupant, model implementation, and human conversation owner are separate records. Conversation rows are keyed by office and authenticated human principal. Rebinding an office to another occupant or model does not delete history. The current resident runtime reads its binding through `AuthorityRegistry.authorize_office_state`; the caller must independently hold an exact active `resident.conversation.read` or `resident.conversation.send` grant for `office:<office-id>`.

The dashboard authentication cookie authenticates the API entry point. For the linked Steward account, the dashboard takes `authority_principal_id` only from the server-validated account session; it validates `resident.conversation.read` and `resident.conversation.send` against that principal using the protected institutional authority function. No role implies either grant, and the account identity is revalidated on every request. The legacy Connect to Grace path remains available to recovery-token sessions and continues to use `X-Riverview-Authority` plus the existing path-scoped `Secure`, `HttpOnly`, `SameSite=Strict` cookie. Both paths call the same exact-grant decision and fail closed for missing, revoked, wrong-scope, expired, or unavailable authority. The linked account path issues no second authority credential and creates no grant or principal. Every history, response-status, and send operation rechecks the current exact database grants, so grant revocation takes effect on the next request. The separate resident service credential remains provisioned only through protected service credentials. Ordinary messages and model responses do not promote or approve an objective. A Steward may explicitly select a persisted user message and submit it through the separate Engineering objective intake route; that route checks conversation ownership and the independent `objective.submit` exact grant.

## Versioned HTTP contract `rv.resident.conversation.v1`

All endpoints require the existing dashboard bearer or an active account session. The linked Steward account path derives its principal from that server-validated session; recovery-token sessions continue to use the exact office-scoped credential in `X-Riverview-Authority`.

The explicit work-order promotion route is intentionally narrower than normal
conversation send. A Steward account session may POST
`/api/v1/resident/conversations/{conversation_id}/work-orders` with
`source_sequence` and `acceptance_criteria`. The server retrieves the source
message itself and verifies that it is a user message owned by the authenticated
principal. The request scope is fixed to `work-order:engineering`; the caller
cannot choose a broader scope. It requires `resident.conversation.read` and
`objective.submit` exact grants and records the conversation ID/sequence on the
objective receipt event. The account role and the legacy dashboard recovery
token do not substitute for those grants. A successful response means objective
intake/grounding only; assignment creation and execution remain separately
authorized.

| Method and route | Purpose | Result |
| --- | --- | --- |
| `GET /api/v1/resident/conversations` | List the caller's recent office conversations | `rv.resident.conversations.v1`, bounded item list |
| `POST /api/v1/resident/conversation-session` | Validate both exact grants for the linked Steward session or legacy credential | `rv.resident.conversation-session.v1`; returns principal and exact scope, never a credential |
| `DELETE /api/v1/resident/conversation-session` | Clear the current browser's conversation cookie | `rv.resident.conversation-session.v1`, status `disconnected` |
| `POST /api/v1/resident/conversations` | Send a message, creating a conversation if needed | `rv.resident.response.v1`; body has only `conversation_id?`, `client_message_id`, and `message` |
| `GET /api/v1/resident/conversations/{conversation_id}` | Retrieve the latest 100 durable events | `rv.resident.conversation.v1` |
| `GET /api/v1/resident/conversations/{conversation_id}/responses/{request_id}` | Inspect one turn's durable response state | `rv.resident.response.v1` |

`client_message_id` is a UUID used as an idempotency key. Repeating a submitted key never starts another inference call. Messages are limited to 8192 UTF-8 bytes. Conversation context is assembled from at most the 16 newest persisted user/assistant messages and the fixed office-resident system instruction. The readiness router preserves all supplied system messages and the latest user turn, trimming only the oldest user/assistant context required to fit its additional stage instruction within the provider's 18-message contract. This trim affects only the inference context; durable history is unchanged. Ordinary turns send at most 512 output tokens. The 0.6B autonomic capability is capped at 32 output tokens and one sentence of no more than 20 words for brief acknowledgments/status; a lower caller-supplied bound remains effective. A non-`stop` finish remains incomplete and cannot become a terminal response; safe diagnostics retain the bounded finish reason, completion-token count and configured limit without retaining response text. Router request timeouts are capped at 60 seconds for 80B reasoning and brief 0.6B autonomic responses, and 15 seconds for provisional 30B; a lower caller-supplied bound remains effective. These are provider socket timeouts, not a guarantee of a hard end-to-end deadline. The serialized provider request must fit 32 KiB. If it does not, the user message remains recorded and the turn is marked `context_too_large`; system context is never silently discarded. Older history is visible through the bounded history API but is outside the explicitly stated recent-context policy.

Routing sends exact acknowledgments/status greetings to the 0.6B when ready. Only a short allowlisted definition/simple-fact pattern may use the 30B as a provisional response. All other user requests default to the 80B when its readiness probe confirms the pinned model; if it is unavailable or busy, the original request is durably deferred for the 80B. The 30B is not an automatic substitute for substantive reasoning. A 30B inference failure may produce a constrained 0.6B acknowledgment only when that provider is ready; otherwise the turn remains deferred.

Assistant event metadata includes an allowlisted `provider_attempts` list with provider ID, reasoning stage, UTC start/end timestamps, elapsed milliseconds, outcome, bounded provider error code, finish reason, completion-token count and limit, fallback reason, and final served provider. It contains no prompt, completion text, credential, or raw exception. Deferred and failed responses retain the attempt diagnostics known at that point. An HTTP client disconnect does not cancel a synchronous provider call: the server finishes and persists a successful result before attempting to write the response, so a browser refresh can recover it from conversation history. The browser may report a closed request while the durable response is subsequently committed; this is not evidence by itself that the model provider failed.

Each dashboard request runs on a bounded request thread. The conversation store and its exact-grant authorizer share one long-lived psycopg connection, so every operation on that connection is protected by a reentrant connection lock and a transaction-scope guard. The office-binding registry connection has a separate lock around its runtime binding reads. Locks are held only during database operations; model inference for distinct conversations remains concurrent. A database operation that returns with a non-idle transaction is rolled back and reported as unavailable, never acknowledged as successful. User-event persistence completes before inference starts. A successful API response is returned only after the assistant event's transaction exits; both events are expected to be visible from a fresh independent PostgreSQL connection at that point.

Response states are `completed`, `pending`, `unavailable`, or `interrupted`. Provider identity, served model ID, model revision, token counts where supplied, and finish reason are stored with assistant events. Provider changes never rewrite previous records. An incomplete, wrong-model, over-bound, failed, or timed-out inference does not create an assistant success event; the user event and sanitized failure code remain visible.

The browser keeps the opaque conversation UUID in local storage. The persistent grant cookie survives refresh, dashboard restart, and UI release changes; its path, HttpOnly, Secure, and SameSite attributes restrict exposure, while the authority registry remains the source of truth. The dashboard bearer remains in tab-scoped session storage under its existing dashboard contract. Disconnect explicitly clears the grant cookie. If a 403 occurs, UI polling/navigation does not retry the protected route; an explicit reconnect is required.

## 2026-10-12 authorization recovery

The Windows snapshot at 02:33 UTC showed repeated 403 responses from the conversation-list route. The pinned pre-refinement dashboard and UI release both used the same `X-Riverview-Authority` header, an `autocomplete="off"` password field, and page-memory-only credential handling; the UI deployment did not change the authority server or revoke grants. Thus refresh/release reload discarded the prior in-page credential, while the new browser request carried a credential that the exact-grant function rejected. The browser-presented value is intentionally unavailable to server logs and was not inspected. The dashboard refresh timer does not poll conversation routes; browser history requests were triggered by conversation navigation/refresh/send. The new client also latches a denial so repeated tab changes do not retry until explicit reconnect.

Read-only live verification through the protected authority function confirms the installed `steward:camrui` token currently receives ALLOW for both `resident.conversation.read` and `resident.conversation.send`, each scoped exactly to `office:office:grace`. No grant, principal, credential file, or database record was changed during that check. The fix establishes a 30-day host-only `Secure; HttpOnly; SameSite=Strict` cookie scoped to conversation API paths, only after both grants validate for one principal. The cookie contains the same registry credential, is inaccessible to page JavaScript, and grants no authority of its own; the same grants are checked on every request and revocation applies immediately. Dashboard bearer auth remains separately required. A stale/invalid browser token is rejected and automatic conversation retries stop.

Isolated PostgreSQL + Firefox verification uses the real already-running loopback Qwen CPU service and demonstrates one initial denied request, no retry after six seconds and a tab switch, authorized cookie connection, real persisted model turns, page refresh and dashboard-process restart without credential re-entry, 403 for an explicit invalid header even when a cookie exists, logout clearing, and immediate rejection after test-credential revocation. Evidence: [`20261012T-auth-session-browser-isolated-1`](../../evidence/checkouts/RESIDENT-CONVERSATION/20261012T-auth-session-browser-isolated-1/). This is isolated commissioning evidence; Windows Steward browser confirmation remains distinct.

The controlled Camrui release `m3.4-camrui-grace-auth-0382ce1` was then exercised in Firefox using the installed protected Steward credential (held in process memory and never emitted). The browser established the cookie, accessed the latest conversation, received a real `qwen3-0.6b-q8_0-local` response, returned HTTP 403 for an invalid explicit authority header, refreshed with history restored and the input cleared, then survived a dashboard service restart and completed another model turn without re-entry. A fresh independent PostgreSQL connection reconciled 5 user events, 4 assistant events, and the prior interrupted event; the latest assistant event carried the expected model ID, provider, and pinned model SHA. No database migration, grant, credential file, or other service was changed. Full evidence, including the pseudonymous conversation reference and rollback steps, is [`20261012T-auth-session-live-0382ce1`](../../evidence/checkouts/RESIDENT-CONVERSATION/20261012T-auth-session-live-0382ce1/).

This Camrui Firefox verification does not prove the Steward's Windows browser profile already has the new cookie. The Windows browser needs one explicit Connect using its current authorized credential if no valid browser credential is autofilled; after that, the cookie survives refreshes and dashboard releases until expiry or grant revocation. Do not copy the credential to chat, URLs, logs, or snapshots. Physical Windows-browser confirmation remains pending.

## 2026-10-13 linked Steward account authorization

The account login is linked to the active `steward:camrui` institutional principal, which already holds both exact `office:office:grace` conversation grants. The former browser connector required the legacy principal credential separately and did not use the account session. The revised dashboard obtains the linked principal only from the currently validated account session and calls a protected principal-keyed exact-grant function for both actions. The same check runs for every conversation operation; there is no role-derived grant, grant issuance, or alternate conversation authorization store. The recovery-token bearer and legacy Connect flow remain available. Migration `0004_exact_principal_grant_authorization.sql` and the boundary provisioner provide runtime execute access while leaving the manager unable to call either authorization function. Deployment and live browser acceptance are reported separately from this source contract.

## Model adapter and binding

The existing `LocalReasoningProvider` has been extended with a plain-text completion operation using its existing loopback-only `/v1/chat/completions` endpoint validation, model-name check, configured model SHA binding, bounded request and response sizes, timeout, and sanitized failures. It does not expose tools or an execution interface. `provider_ref` in the current office binding selects the adapter; the bound implementation revision must exactly equal its configured model SHA-256. A replacement model is selected by a new existing resident implementation and office binding. The office/occupant identity and conversation tables remain independent of the model. An optional, UTF-8 bounded `RIVERVIEW_GRACE_CHAT_PREFIX` is passed into the provider; it modifies only the provider's copy of the latest user message and is never persisted as conversation content.

For an isolated development run, the previously installed Qwen3-0.6B Q8_0 GGUF is at `$HOME/.cache/riverview/models/Qwen3-0.6B-Q8_0.gguf` with expected SHA-256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`. The pinned llama.cpp binary is `/tmp/rv-llama-build/bin/llama-server`. The test harness binds only to a free `127.0.0.1` port, passes `--n-gpu-layers 0`, and uses the isolated PostgreSQL test DSN. For this Qwen3 chat run it configures `/no_think\n`, a prompt hint already used in the repository's local inference qualification. The hint is confined to the inference copy and does not change durable user messages. The harness stops only the exact process it started. No model is downloaded or loaded by application startup.

The provider now accepts a remote endpoint only when the caller explicitly opts in
and the endpoint/model pair exactly matches one of the approved OCTO1 routes
(`http://192.168.1.160:8080/v1` with the observed Qwen3-Next-80B model ID, or
`http://192.168.1.160:18080/v1` with the observed Huihui 30B model ID). The
dashboard opt-in is `RIVERVIEW_GRACE_ALLOW_APPROVED_OCTO1=1`; it defaults off.
The exact served model ID remains checked against configuration, and the office
implementation revision remains checked before and after inference. Provider
concurrency is bounded (one slot by default); contention reports `endpoint_busy`
at the provider boundary. `readiness()` checks only `/health` and `/v1/models`
for the configured endpoint. It reports model `READY`, `MODEL_LOADING`,
`MODEL_BUSY`, `UNAVAILABLE`, `TIMEOUT`, or `ERROR`; `MODEL_BUSY` currently means
this provider instance's bounded semaphore is occupied, not that every caller
has observed OCTO1's global slot state. An unreachable HTTP endpoint does not
prove the host is powered off or booting. This is provider plumbing,
not a three-stage selector or durable deferred-question worker. The active
production binding remains the loopback 0.6B until a separately approved
binding/configuration deployment. OCTO1's HTTP API is unauthenticated and
unencrypted as documented; requests must remain on the trusted LAN, and this
integration must not be exposed through WAN routing.

The dashboard service enables chat only when its protected `resident-token`, office ID, model endpoint, model identifier, and SHA configuration are all present. Non-loopback OCTO1 configuration additionally requires the explicit opt-in flag; the flag does not change the office binding. Database migrations are an explicit operator action; API startup never applies schema changes. No unit file, installed service, shared database, secret, or running model was modified for this implementation.

## Browser conversation workspace

The Talk with Grace view renders every persisted Steward and Grace message in separate responsive bubbles. Content is escaped as text, preserves line breaks and paragraphs, wraps long unbroken strings, and is not shortened with ellipses. The history pane scrolls vertically; refresh reloads the authoritative event history. New content scrolls into view only when the reader was already near the bottom. Interrupted and failed turns remain visible as distinct system messages, and an active request shows a generating indicator.

The multiline composer grows with entered text up to a viewport-bounded height. Enter submits and Shift+Enter inserts a newline; the visible “Insert line break” button provides a touch-friendly alternative. Submission disables duplicate sends. An unsent draft is kept in the browser session's sessionStorage under the conversation identifier and is cleared only after the API acknowledges a response. A failed request keeps the typed text and instructs the user to refresh before retrying because the request may already be durable.

The three-dot menu beside Send provides factual conversation details from persisted conversation/event metadata: identifier, creation and activity times, current turn status, latest model/provider/revision, measured duration when event timestamps permit it, and recorded interruption information. Local timestamps include UTC in details. Each message menu provides details, copy text, and copy persisted event sequence where available. Copy is local to the user's clipboard; it does not forward or transmit content. The UI does not edit committed events. Historical edit/resubmit, forwarding, attachments, image upload/generation, and engineering-proposal actions remain disabled or explicitly unavailable; ordinary chat never grants work authority.

Keyboard focus is returned to the opening control after dialogs close, and native details/summary controls support keyboard activation. Layout adapts to narrow viewports and keeps message text and composer controls within the viewport. Copy uses the browser Clipboard API with a local document-copy fallback. No credential value is placed in message metadata or operational logs.

The UI can later host an inline engineering proposal card, but no approval card, objective creation, or executor is implied by this presentation change. Proposal generation and governed approval remain owned by the separate conversation-to-engineering integration. Actual assistant output length remains bounded by the bound provider's configured output limit; layout tests do not claim the model produced that length.

## Recovery and troubleshooting

| Symptom | Diagnostic | Expected interpretation | Safe recovery | Escalate when |
| --- | --- | --- | --- | --- |
| API returns `resident_conversation_unavailable` | Check dashboard structured startup record `resident_conversation_start_failed` and confirm the conversation migration is applied in the selected test/development schema | Missing protected resident credential/config, migration, database, or provider setup; startup logs only the exception class | Correct the development configuration or apply the reviewed migration to an isolated schema, then restart only the isolated dashboard process | Shared service configuration or database would have to change, or source provenance is not the pinned release |
| API returns `resident_conversation_not_authorized` | The browser pauses retries; use the visible Connect control once, then inspect the protected exact-grant decision without printing credentials | The current cookie/header is not authorized, has expired/revoked, or lacks either exact action; a dashboard token is not a conversation grant | Connect with a current Steward conversation credential. The UI clears typed input after the exchange; on success the host-only HttpOnly cookie is reused after refresh. Do not copy the credential into URLs, screenshots, or logs. | The installed Steward credential is allowed by the exact-grant function but the browser Connect request is denied, or the office binding check fails |
| History is empty after refresh | `GET /api/v1/resident/conversations`, then `GET /api/v1/resident/conversations/{id}` using the browser cookie and dashboard bearer | UUID is not in this principal/office, cookie is absent/expired, or no user turn was committed | Reconnect once if prompted and choose a listed conversation; inspect migration/database identity if the authorized list is unexpectedly empty | The same DB/schema and owner principal are confirmed but events are missing |
| Turn stays pending after process interruption | `GET /api/v1/resident/conversations/{id}/responses/{request_id}` | Pending means a durable user event has no response result yet | On the next single-process service start, startup reconciliation records `response_interrupted` / `service_restarted`; submit a new message only after inspecting the persisted history | Multiple service instances may be active or a request is still executing; do not force-retry an uncertain call |
| Response is `model_timeout` / `model_unavailable` | Inspect response status and loopback `/health` of the specifically configured development model | No assistant response was accepted; the user turn is preserved | Restore the configured local model and send a new turn; a repeated idempotency key will not re-invoke inference | Endpoint is not loopback, model SHA does not match its office binding, or a non-development service would need modification |
| Response is `context_too_large` | Inspect history size and request byte budget; no prompt is stored in logs | The bounded relevant context could not fit the existing 32 KiB provider contract | Start a new conversation or continue with a concise follow-up that explicitly restates required context; do not silently drop essential content | Correct operation requires changing the established ResidentReasoner bound |
| Deferred attempt is `response_incomplete` | Inspect the sanitized `provider_attempts` fields or `grace_deferred_resume_attempt` journal entry for `finish_reason`, `completion_tokens`, and `completion_token_limit`; do not retrieve the message body | `length` with tokens equal to the limit means generation was truncated; it is not a terminal response | Keep the request pending and retry only with an approved larger bounded output limit; preserve the original capability and idempotency lease | The provider reports an unknown finish reason, the count exceeds the configured limit, or the corrected bounded request also truncates |
| API history count differs from independent PostgreSQL count, or dashboard has an idle-in-transaction session | Query `pg_stat_activity` for `application_name='riverview-status-dashboard'`; verify deployed source identity; compare authorized API event sequences with a separate PostgreSQL connection | Before `30085f040d16c666ab8e715e2b9f8c384d1adf9c`, concurrent dashboard request threads could interleave transaction scopes on the shared psycopg conversation connection | Stop accepting new chat requests by restoring the preserved dashboard release/configuration; preserve database and evidence; deploy the serialized-connection fix and verify every acknowledged event through a fresh connection. Never manually commit an unknown open transaction | Counts still differ after the fix, rollback is unhealthy, or source/deployment identity is uncertain |

Do not delete conversation rows or alter shared credentials as routine recovery. Database cleanup is limited to the unique disposable test schema created by the test harness.

## Verification status

Isolated PostgreSQL tests exercise exact read/send grants, persistent history, retry idempotency, fake-provider implementation replacement with the same office and conversation, missing-model failure, oversized context, and restart reconciliation. Durability regressions additionally query through a new PostgreSQL connection before inference (user event) and after API acknowledgment (assistant event), stress concurrent independent conversation requests, compare API and committed row sequences, and assert the service connection is idle with no transaction after completed requests. A real Firefox run against committed source `1fa9d6104fc07609e3d8bbda8bf836b0b22e19c1` used the already-installed Qwen3-0.6B Q8_0 CPU model (pinned model SHA-256, 4096-token context, zero GPU layers, `/no_think` hint). Both browser turns generated and rendered: the initial turn took 31.95 seconds and the resumed turn took 27.92 seconds. PostgreSQL retained three user events, two assistant events, and one controlled interrupted event; ordinary chat created zero objectives. Browser refresh reloaded the same conversation. The isolated dashboard HTTP server and resident runtime objects were torn down and recreated against the same database, which reconciled the pending turn and allowed a subsequent response. The test does not establish a systemd or whole-host process restart.

Evidence is `evidence/checkouts/RESIDENT-CONVERSATION/20261011T-committed-source-browser-verified/`; its `artifacts.json` pins checksums and artifact revisions. The later live Camrui recommission is recorded at `evidence/checkouts/RESIDENT-CONVERSATION/20261011T230000Z-live-durability/`. It deployed commit `30085f040d16c666ab8e715e2b9f8c384d1adf9c`; two real Firefox browser turns used the existing CPU-only Qwen3-0.6B binding. For each turn the user event was visible to a fresh PostgreSQL connection before inference completed, and after acknowledgment API and independent database sequences/counts matched (2/2, then 4/4). The conversation survived browser refresh and a dashboard systemd restart, then accepted a second turn. The pinned model ID and SHA matched the office binding; missing conversation authority returned 403; dashboard status, assignments, events, workers, attention, notifications, and objectives routes returned 200. PostgreSQL held nine assignments, two conversations and eight conversation events; the Grace objectives table remained absent. No dashboard connection was idle in transaction. A new protected database backup was archive-verified and restored to a disposable database before deployment. The previous release remains available for rollback.

The live recovery drill also restarted only the dashboard after PostgreSQL showed a pending user event but before the model response. Startup reconciliation persisted `response_interrupted` with `service_restarted`; the response-status API agreed. A new ordinary turn then completed through the same conversation. The first browser wait in the drill timed out at its 30-second test predicate; inspection showed the CPU model had completed just after that bound. Fresh API/PostgreSQL comparison and a new Firefox history load confirmed the successful response and four rendered rows (including the durable interruption). The timeout and its resolution are retained in the checkout evidence rather than counted as a successful browser assertion.

The exact original six-versus-four symptom was reproduced against preserved pre-fix commit `ea6748729fabfa3b93e3abb457f4e0e46357be26` in an isolated PostgreSQL cluster. With four rows committed, the reproducer held an outer connection transaction (modeling an overlapping request scope), invoked a third completed service turn in a nested transaction, and read history through the same connection before outer commit: the API saw six events, a fresh PostgreSQL connection saw four, and the shared connection remained `INTRANS`. No production data or services were involved. The reproducer and checksummed output are `evidence/checkouts/RESIDENT-CONVERSATION/20261011T234000Z-pre-fix-six-four/`.

The CPU inference service is a transient systemd unit bound to loopback and is not configured to restart on host reboot. Dashboard restart recovery was tested while that model unit remained active; host-reboot model recovery is not claimed. An alternate real model was not used. Conversation privacy/retention policy approval, multi-process connection coordination, formal M3.4 sequencing decision, and full Component Definition of Done remain open. This live commissioning is technical evidence only; it does not itself claim formal roadmap acceptance.

Process graph: [`RESIDENT_CONVERSATION_FLOW.md`](RESIDENT_CONVERSATION_FLOW.md), graph ID `rv:resident-conversation:browser-chat`.


## 2026-10-12 interface refinement verification

A Firefox/WebDriver integration run exercised the changed browser workspace against a
disposable PostgreSQL schema and the already-running local CPU model. It verified a real
model response, exact rendering of a 770-character multiline user message, persisted
history after refresh, explicit interruption after a controlled supporting-service
restart, a successful follow-up response, independent PostgreSQL event counts, unauthorized
403, factual conversation/model details, message details and local Copy, composer
processing and multiline behavior, and long-message wrapping. It created no objectives.
The report is
[`browser-commissioning.json`](../../evidence/checkouts/RESIDENT-CONVERSATION/20261012T-ui-refinement-isolated-13/browser-commissioning.json).
The same isolated environment ran the full automated suite: 228 passed, no skips or
failures; graph and revision checks passed. Firefox headless clamps its top-level window at 500 CSS pixels. A same-origin iframe
loaded the deployed shell and production stylesheet at exactly 390 CSS pixels and verified
a 378-pixel document width, active mobile breakpoint, full long-message rendering, visible
composer/Send, and correct menu placement. Physical phone and Steward Windows-browser
verification remain outstanding. This isolated/candidate evidence does not constitute
formal milestone acceptance or full Component Definition of Done.


## 2026-10-12 controlled dashboard deployment

After isolated browser and full-suite acceptance plus PR #27 controlled-checkout CI, the
Steward dashboard was deployed on Camrui using a new root-owned release
`/opt/riverview-status-dashboard/releases/5cbf315b95b5b644296910b4c7a16e5ae358e55b-grace-chat-ui`.
The package was cloned from the prior immutable `30085f...` runtime release and only
`index.html`, `app.css`, and `app.js` were replaced with the three matching files from
commit `5cbf315b95b5b644296910b4c7a16e5ae358e55b`; all three SHA-256 values matched
repository and deployed bytes. The old release remains intact at
`/opt/riverview-status-dashboard/releases/30085f040d16c666ab8e715e2b9f8c384d1adf9c-grace-chat-durability`
and is the rollback target. A separate root-owned systemd drop-in,
`/etc/systemd/system/riverview-status-dashboard.service.d/40-grace-chat-ui.conf`
(revision 1.0.0), updates only dashboard source/deployment identity. No migrations,
credentials, inference configuration, CME, worker, verifier, event processor, notification,
or assignment services were changed. Only `riverview-status-dashboard.service` was
restarted; it remained active with zero systemd restart failures.

Post-deployment read-only Firefox acceptance on `127.0.0.1:8766` observed a healthy
projection and CME, completed assignment with one attempt and an independent verification,
attention HTTP 200, all checked cookbook links HTTP 200, valid canonical workflow view,
responsive navigation, and zero browser errors. A second browser session opened Talk with
Grace and verified the composer, Send button, menu placement, pre-wrapped text, details
dialog, and 403 denial for an invalid conversation credential. It did not send a live
message because the Steward office-scoped credential was not present in this execution
context. The prior isolated real-model test did send and persist two turns using the active
Qwen3-0.6B CPU service, including restart recovery. Evidence and rollback provenance are
in [`20261012T-ui-live-deployed`](../../evidence/checkouts/RESIDENT-CONVERSATION/20261012T-ui-live-deployed/).

The deployed styles were checked at an exact 390-pixel CSS viewport using a same-origin
Firefox iframe fixture, but a physical phone and the Steward's Windows browser have not
been verified from Camrui. Refresh Talk with Grace in the existing Windows SSH browser
session and send a message there to complete Steward-facing acceptance. This deployment is
not formal Steward acceptance and does not close full Component Definition of Done
obligations. Rollback consists of restoring the
previous `current` symlink target, removing only the new 40 drop-in, daemon-reloading, and
restarting the dashboard; preserve the candidate release and database state.

## Multi-stage reasoning and reversible model binding (development increment)

`GraceModelRouter` (`resident_execution/model_router.py`) is an opt-in provider
behind the existing office implementation binding. The binding continues to pin
the router implementation revision; each assistant event records the provider's
actual served model and the selected stage. The router selects the configured
80B for substantive requests, a ready 30B for short provisional text turns, and
the 0.6B for constrained greeting/status acknowledgements when 30B is
unavailable. Other questions defer or route to 80B; the autonomic model is not
used to invent factual answers. The
current browser conversation payload is text-only; this does not commission
image upload or prove the 30B visual request path.

When a substantive turn cannot use the 80B, the user message and one
response_deferred event remain in the conversation ledger. The opt-in dashboard
resumption loop rechecks the original sender's exact grant and current Grace
occupant, then validates the deferred capability. Matching implementation
identity remains the normal path. A changed router may resume only when the
current office binding is the direct successor in an immutable
office_model_implementation_changed event whose CAS call explicitly opted
into grace.reasoning.80b continuity. The event must name the exact predecessor
revision, successor revision, current binding revision, and registered
grace.readiness_router.v1 provider. Ordinary rebinds, unrelated providers,
indirect/older transitions, missing capabilities, and revoked original sender
grants remain paused. The original user and deferred events are never rewritten;
the terminal response records original and executing implementation identities,
the revalidated grant, and actual served model. Resumption rebuilds context from
events preceding the original deferred user event and appends that request as
the final user message. Later turns cannot replace its objective or influence
capability selection. The persisted `required_capability` is passed to the
router: `grace.reasoning.80b` selects only the bound 80B provider. If it is
unavailable, busy, or returns an invalid response, the lease is released and
the request remains pending; neither 30B nor 0.6B may satisfy it.

Resumption claims each request in the durable
resident_deferred_execution_claims table before provider execution. One active
ten-minute lease prevents concurrent execution across threads and service
processes; the lease is released on every attempt and expires after a process
crash. Terminal-event checks and the conversation row lock make reply insertion
idempotent. Deferred retry failures emit structured journal diagnostics keyed
by request ID with selected provider/model/stage, UTC start/end, elapsed time,
bounded outcome/error code, finish reason, completion-token count/limit, and
fallback reason. They never contain message text, model output, credentials,
or raw exception details.

An explicitly authorized upgrade uses
AuthorityRegistry.update_office_implementation(...,
deferred_compatibility_capabilities=("grace.reasoning.80b",)). The option
defaults to no continuity and remains behind the existing exact office.manage
grant and binding-revision compare-and-swap. The runtime's
authorized_office_implementation_successor SECURITY DEFINER function reveals
only a boolean and requires the current resident credential plus exact
office.state.write grant. It exposes neither audit rows nor migration ledgers.
The restricted authority-boundary provisioning grants execute on this one
allowlisted function, not table access.

Apply resident-execution migrations
0004_deferred_conversation_responses.sql and
0006_deferred_execution_claims.sql, and authority migration
0006_authorized_implementation_successor.sql, before enabling continuity.
The loop is started only with
`RIVERVIEW_GRACE_ENABLE_MODEL_ROUTER=1`; the setting additionally requires the
30B and 80B model SHA-256 configuration values. The existing 0.6B endpoint/model/
digest settings remain required. OCTO1 access remains gated by the explicit
`RIVERVIEW_GRACE_ALLOW_APPROVED_OCTO1=1` setting.

At startup, the dashboard runtime reads only the deferred-response migration
marker in its own `riverview_dev` schema. It does not inspect
`riverview_authority.schema_migrations`, whose ledger remains unreadable to the
runtime by design. Instead it validates the current resident credential and
active model binding through `AuthorityRegistry.authorize_office_state`, the
existing exact-grant security-definer API, and requires the returned provider
and implementation digest to match the configured router. The deployment
runner is responsible for checksum-verifying authority migration
`0005_audited_model_rebinding.sql` before activation. A missing resident
migration, unavailable authority API/grant, or mismatched active binding keeps
conversation startup fail-closed without widening database permissions.

The readiness probe can distinguish `READY`, endpoint-reported `MODEL_LOADING`,
and this process's own `MODEL_BUSY` state. An unreachable endpoint is
`UNAVAILABLE`; this HTTP signal alone cannot distinguish an OCTO1 host that is
powered off from one booting or a model still starting. No power action is taken.
The documented Wake-on-LAN and SSH shutdown procedure remains a separately
authorized operational capability and is not invoked by this router.

`AuthorityRegistry.update_office_implementation` changes only the model
implementation on an existing office binding. It requires the existing exact
`office.manage` grant, an expected binding revision, and an existing model
implementation. It preserves office and occupant identity, increments the
binding revision, and appends `office_model_implementation_changed`. Rollback is
the same operation targeting the returned predecessor implementation while
passing the new current binding revision; stale rollback attempts are rejected.
Authority migration `0005_audited_model_rebinding.sql` adds the event type. On
Camrui, authority migration `0005_audited_model_rebinding` and
resident-execution migrations `0001_grace_objectives`, `0002_execution_health`,
and `0004_deferred_conversation_responses` were applied additively on
2026-10-13 and remain recorded. The readiness-router implementation is
registered, but its office binding was rolled back through the authority API
to the local 0.6B implementation at binding revision 3 after release
`ddfe62cd3def0ada61340fe8c5dfc124adf4eb3c` failed conversation startup because
of the protected-ledger visibility defect described above. The corrected
release is not deployed, and a browser conversation through the 80B has not
been verified.

This readiness correction is not deployed. Production already has the additive
migrations and registered router implementation, but Grace remains bound to the
0.6B at revision 3. Activating the corrected release still requires approved
dashboard configuration, a Steward-authorized CAS rebind, a dashboard-only
restart, and browser evidence showing the served 80B model plus persistent
conversation history. No service was restarted and no office binding was
changed by this correction.

**Current status update (2026-10-14):** The failed cfdda4 commissioning was
rolled back safely. Production is reported restored to dashboard release
807262be9a1a54e29ff7f8bd7f8f51b8aa4767ad with Grace binding revision 6 and the
already-applied dashboard health projection permission. The pending deferred
requests retain the prior router implementation fingerprint
87ccad04629151f564185ffdef5e961fad4608d805307b431fbe48dbea804cc1; the
successor fingerprint is 608aa519346c4643050b1dff6bc0f0a4d65d2cb9d64b9c07cf1d8faeae3b8c7e.
This continuity correction and its two new migrations are development-only.
They have not been migrated, deployed, or rebound in production.
