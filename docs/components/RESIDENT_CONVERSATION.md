<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_CONVERSATION.md
Component: RESIDENT-CONVERSATION
File Revision: 1.1.3
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
Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Record deployed 390 CSS-pixel responsive fixture while retaining physical-device and Windows verification as pending
Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Add persistent same-origin browser credential transport, exact-grant rechecks, and denial retry suppression
Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Record diagnosed credential retention gap, grant audit, and browser restart evidence
History: Git and .riverview-backups/manifest.jsonl
-->
# Grace resident conversation

**Status:** Isolated engineering implementation on the proposed M3.4 workstream. The roadmap's M3.4 sequencing proposal has not been formally accepted; this work does not claim roadmap acceptance, production commissioning, or full Component Definition of Done.

## Identity and authority

The resident office, currently bound occupant, model implementation, and human conversation owner are separate records. Conversation rows are keyed by office and authenticated human principal. Rebinding an office to another occupant or model does not delete history. The current resident runtime reads its binding through `AuthorityRegistry.authorize_office_state`; the caller must independently hold an exact active `resident.conversation.read` or `resident.conversation.send` grant for `office:<office-id>`.

The dashboard bearer authenticates access to the API entry point. The `X-Riverview-Authority` header supplies the second, exact-grant credential, following the established objective API pattern. Missing, revoked, wrong-scope, or unavailable authority fails closed. On first use, `POST /api/v1/resident/conversation-session` validates both conversation grants for the same principal and returns a 30-day, host-only, `Secure`, `HttpOnly`, `SameSite=Strict` cookie scoped only to `/api/v1/resident/conversations`. The cookie transports the existing authority credential; it creates no new grant or principal. Every history, response-status, and send operation rechecks the current exact database grant, so revocation takes effect immediately. The browser JavaScript cannot read the cookie; it is never put in local/session storage, a URL, an application log, or an operational snapshot. `DELETE /api/v1/resident/conversation-session` clears it. A 403 stops automatic history retries until the Steward explicitly reconnects. The separate resident service credential remains provisioned only through protected service credentials. Neither a message nor a model response promotes or approves an objective or work order.

## Versioned HTTP contract `rv.resident.conversation.v1`

All endpoints also require the dashboard bearer. The exact office-scoped authority credential is sent in `X-Riverview-Authority`.

| Method and route | Purpose | Result |
| --- | --- | --- |
| `GET /api/v1/resident/conversations` | List the caller's recent office conversations | `rv.resident.conversations.v1`, bounded item list |
| `POST /api/v1/resident/conversation-session` | Validate both exact grants and establish/refresh this browser's protected credential cookie | `rv.resident.conversation-session.v1`; returns principal, exact scope, expiry; never returns the credential |
| `DELETE /api/v1/resident/conversation-session` | Clear the current browser's conversation cookie | `rv.resident.conversation-session.v1`, status `disconnected` |
| `POST /api/v1/resident/conversations` | Send a message, creating a conversation if needed | `rv.resident.response.v1`; body has only `conversation_id?`, `client_message_id`, and `message` |
| `GET /api/v1/resident/conversations/{conversation_id}` | Retrieve the latest 100 durable events | `rv.resident.conversation.v1` |
| `GET /api/v1/resident/conversations/{conversation_id}/responses/{request_id}` | Inspect one turn's durable response state | `rv.resident.response.v1` |

`client_message_id` is a UUID used as an idempotency key. Repeating a submitted key never starts another inference call. Messages are limited to 8192 UTF-8 bytes. Conversation context is assembled from at most the 16 newest persisted user/assistant messages and the fixed office-resident system instruction. The resident sends at most 64 output tokens per turn and allows 120 seconds for inference. The serialized provider request must fit 32 KiB. If it does not, the user message remains recorded and the turn is marked `context_too_large`; required context is not silently truncated. Older history is visible through the bounded history API but is outside the explicitly stated recent-context policy.

Each dashboard request runs on a bounded request thread. The conversation store and its exact-grant authorizer share one long-lived psycopg connection, so every operation on that connection is protected by a reentrant connection lock and a transaction-scope guard. The office-binding registry connection has a separate lock around its runtime binding reads. Locks are held only during database operations; model inference for distinct conversations remains concurrent. A database operation that returns with a non-idle transaction is rolled back and reported as unavailable, never acknowledged as successful. User-event persistence completes before inference starts. A successful API response is returned only after the assistant event's transaction exits; both events are expected to be visible from a fresh independent PostgreSQL connection at that point.

Response states are `completed`, `pending`, `unavailable`, or `interrupted`. Provider identity, served model ID, model revision, token counts where supplied, and finish reason are stored with assistant events. Provider changes never rewrite previous records. An incomplete, wrong-model, over-bound, failed, or timed-out inference does not create an assistant success event; the user event and sanitized failure code remain visible.

The browser keeps the opaque conversation UUID in local storage. The persistent grant cookie survives refresh, dashboard restart, and UI release changes; its path, HttpOnly, Secure, and SameSite attributes restrict exposure, while the authority registry remains the source of truth. The dashboard bearer remains in tab-scoped session storage under its existing dashboard contract. Disconnect explicitly clears the grant cookie. If a 403 occurs, UI polling/navigation does not retry the protected route; an explicit reconnect is required.

## 2026-10-12 authorization recovery

The Windows snapshot at 02:33 UTC showed repeated 403 responses from the conversation-list route. The pinned pre-refinement dashboard and UI release both used the same `X-Riverview-Authority` header, an `autocomplete="off"` password field, and page-memory-only credential handling; the UI deployment did not change the authority server or revoke grants. Thus refresh/release reload discarded the prior in-page credential, while the new browser request carried a credential that the exact-grant function rejected. The browser-presented value is intentionally unavailable to server logs and was not inspected. The dashboard refresh timer does not poll conversation routes; browser history requests were triggered by conversation navigation/refresh/send. The new client also latches a denial so repeated tab changes do not retry until explicit reconnect.

Read-only live verification through the protected authority function confirms the installed `steward:camrui` token currently receives ALLOW for both `resident.conversation.read` and `resident.conversation.send`, each scoped exactly to `office:office:grace`. No grant, principal, credential file, or database record was changed during that check. The fix establishes a 30-day host-only `Secure; HttpOnly; SameSite=Strict` cookie scoped to conversation API paths, only after both grants validate for one principal. The cookie contains the same registry credential, is inaccessible to page JavaScript, and grants no authority of its own; the same grants are checked on every request and revocation applies immediately. Dashboard bearer auth remains separately required. A stale/invalid browser token is rejected and automatic conversation retries stop.

Isolated PostgreSQL + Firefox verification uses the real already-running loopback Qwen CPU service and demonstrates one initial denied request, no retry after six seconds and a tab switch, authorized cookie connection, real persisted model turns, page refresh and dashboard-process restart without credential re-entry, 403 for an explicit invalid header even when a cookie exists, logout clearing, and immediate rejection after test-credential revocation. Evidence: [`20261012T-auth-session-browser-isolated-1`](../../evidence/checkouts/RESIDENT-CONVERSATION/20261012T-auth-session-browser-isolated-1/). This is isolated commissioning evidence; Windows Steward browser confirmation remains distinct.

## Model adapter and binding

The existing `LocalReasoningProvider` has been extended with a plain-text completion operation using its existing loopback-only `/v1/chat/completions` endpoint validation, model-name check, configured model SHA binding, bounded request and response sizes, timeout, and sanitized failures. It does not expose tools or an execution interface. `provider_ref` in the current office binding selects the adapter; the bound implementation revision must exactly equal its configured model SHA-256. A replacement model is selected by a new existing resident implementation and office binding. The office/occupant identity and conversation tables remain independent of the model. An optional, UTF-8 bounded `RIVERVIEW_GRACE_CHAT_PREFIX` is passed into the provider; it modifies only the provider's copy of the latest user message and is never persisted as conversation content.

For an isolated development run, the previously installed Qwen3-0.6B Q8_0 GGUF is at `$HOME/.cache/riverview/models/Qwen3-0.6B-Q8_0.gguf` with expected SHA-256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`. The pinned llama.cpp binary is `/tmp/rv-llama-build/bin/llama-server`. The test harness binds only to a free `127.0.0.1` port, passes `--n-gpu-layers 0`, and uses the isolated PostgreSQL test DSN. For this Qwen3 chat run it configures `/no_think\n`, a prompt hint already used in the repository's local inference qualification. The hint is confined to the inference copy and does not change durable user messages. The harness stops only the exact process it started. No model is downloaded or loaded by application startup.

The dashboard service enables chat only when its protected `resident-token`, office ID, loopback model endpoint, model identifier, and SHA configuration are all present. Database migrations are an explicit operator action; API startup never applies schema changes. No unit file, installed service, shared database, secret, or running model was modified for this implementation.

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
