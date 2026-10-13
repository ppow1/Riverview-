<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_CONVERSATION.md
Component: RESIDENT-CONVERSATION
File Revision: 1.0.1
Purpose: Specify authenticated persistent conversation with the office-bound Grace resident
Authority: Dashboard authentication plus exact resident.conversation.read/send grants; chat is not work authorization
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Initial isolated conversation contract and operator procedure
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Set a short CPU-model response budget and record observed timeout evidence
History: Git and .riverview-backups/manifest.jsonl
-->
# Grace resident conversation

**Status:** Isolated engineering implementation on the proposed M3.4 workstream. The roadmap's M3.4 sequencing proposal has not been formally accepted; this work does not claim roadmap acceptance, production commissioning, or full Component Definition of Done.

## Identity and authority

The resident office, currently bound occupant, model implementation, and human conversation owner are separate records. Conversation rows are keyed by office and authenticated human principal. Rebinding an office to another occupant or model does not delete history. The current resident runtime reads its binding through `AuthorityRegistry.authorize_office_state`; the caller must independently hold an exact active `resident.conversation.read` or `resident.conversation.send` grant for `office:<office-id>`.

The dashboard bearer authenticates access to the API entry point. The `X-Riverview-Authority` header supplies the second, exact-grant credential, following the established objective API pattern. Missing, revoked, wrong-scope, or unavailable authority fails closed. The human credential is not written to browser storage or logs. The resident credential is provisioned separately through a protected service credential. Neither a message nor a model response promotes or approves an objective or work order.

## Versioned HTTP contract `rv.resident.conversation.v1`

All endpoints also require the dashboard bearer. The exact office-scoped authority credential is sent in `X-Riverview-Authority`.

| Method and route | Purpose | Result |
| --- | --- | --- |
| `GET /api/v1/resident/conversations` | List the caller's recent office conversations | `rv.resident.conversations.v1`, bounded item list |
| `POST /api/v1/resident/conversations` | Send a message, creating a conversation if needed | `rv.resident.response.v1`; body has only `conversation_id?`, `client_message_id`, and `message` |
| `GET /api/v1/resident/conversations/{conversation_id}` | Retrieve the latest 100 durable events | `rv.resident.conversation.v1` |
| `GET /api/v1/resident/conversations/{conversation_id}/responses/{request_id}` | Inspect one turn's durable response state | `rv.resident.response.v1` |

`client_message_id` is a UUID used as an idempotency key. Repeating a submitted key never starts another inference call. Messages are limited to 8192 UTF-8 bytes. Conversation context is assembled from at most the 16 newest persisted user/assistant messages and the fixed office-resident system instruction. The resident sends at most 64 output tokens per turn and allows 120 seconds for inference. The serialized provider request must fit 32 KiB. If it does not, the user message remains recorded and the turn is marked `context_too_large`; required context is not silently truncated. Older history is visible through the bounded history API but is outside the explicitly stated recent-context policy.

Response states are `completed`, `pending`, `unavailable`, or `interrupted`. Provider identity, served model ID, model revision, token counts where supplied, and finish reason are stored with assistant events. Provider changes never rewrite previous records. An incomplete, wrong-model, over-bound, failed, or timed-out inference does not create an assistant success event; the user event and sanitized failure code remain visible.

The browser keeps the opaque conversation UUID in local storage and keeps the human authority credential only in the active page. A page reload therefore reloads history after the user re-enters the exact-grant credential. The dashboard session token remains in tab-scoped session storage under the existing dashboard contract.

## Model adapter and binding

The existing `LocalReasoningProvider` has been extended with a plain-text completion operation using its existing loopback-only `/v1/chat/completions` endpoint validation, model-name check, configured model SHA binding, bounded request and response sizes, timeout, and sanitized failures. It does not expose tools or an execution interface. `provider_ref` in the current office binding selects the adapter; the bound implementation revision must exactly equal its configured model SHA-256. A replacement model is selected by a new existing resident implementation and office binding. The office/occupant identity and conversation tables remain independent of the model.

For an isolated development run, the previously installed Qwen3-0.6B Q8_0 GGUF is at `$HOME/.cache/riverview/models/Qwen3-0.6B-Q8_0.gguf` with expected SHA-256 `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`. The pinned llama.cpp binary is `/tmp/rv-llama-build/bin/llama-server`. The test harness must bind only to a free `127.0.0.1` port, pass `--n-gpu-layers 0`, and use the isolated PostgreSQL test DSN. It must stop only the exact process it started. No model is downloaded or loaded by application startup.

The dashboard service enables chat only when its protected `resident-token`, office ID, loopback model endpoint, model identifier, and SHA configuration are all present. Database migrations are an explicit operator action; API startup never applies schema changes. No unit file, installed service, shared database, secret, or running model was modified for this implementation.

## Recovery and troubleshooting

| Symptom | Diagnostic | Expected interpretation | Safe recovery | Escalate when |
| --- | --- | --- | --- | --- |
| API returns `resident_conversation_unavailable` | Check dashboard structured startup record `resident_conversation_start_failed` and confirm the conversation migration is applied in the selected test/development schema | Missing protected resident credential/config, migration, database, or provider setup; startup logs only the exception class | Correct the development configuration or apply the reviewed migration to an isolated schema, then restart only the isolated dashboard process | Shared service configuration or database would have to change, or source provenance is not the pinned release |
| API returns `resident_conversation_not_authorized` | Repeat the exact dashboard-authenticated request with an authorized `X-Riverview-Authority`; inspect the exact office/action grant through the authority operator procedure | The dashboard bearer is valid but the second exact grant is absent/revoked/wrong-scope | Request proper grant through the existing AuthorityRegistry; never substitute the resident credential for the human grant | Registry is unavailable, the credential principal is unexpected, or the current occupant check fails |
| History is empty after refresh | `GET /api/v1/resident/conversations`, then `GET /api/v1/resident/conversations/{id}` with both credentials | UUID is not in this principal/office, or no user turn was committed | Re-enter the authority credential and choose a listed conversation; inspect migration/database identity if the list is unexpectedly empty | The same DB/schema and owner principal are confirmed but events are missing |
| Turn stays pending after process interruption | `GET /api/v1/resident/conversations/{id}/responses/{request_id}` | Pending means a durable user event has no response result yet | On the next single-process service start, startup reconciliation records `response_interrupted` / `service_restarted`; submit a new message only after inspecting the persisted history | Multiple service instances may be active or a request is still executing; do not force-retry an uncertain call |
| Response is `model_timeout` / `model_unavailable` | Inspect response status and loopback `/health` of the specifically configured development model | No assistant response was accepted; the user turn is preserved | Restore the configured local model and send a new turn; a repeated idempotency key will not re-invoke inference | Endpoint is not loopback, model SHA does not match its office binding, or a non-development service would need modification |
| Response is `context_too_large` | Inspect history size and request byte budget; no prompt is stored in logs | The bounded relevant context could not fit the existing 32 KiB provider contract | Start a new conversation or continue with a concise follow-up that explicitly restates required context; do not silently drop essential content | Correct operation requires changing the established ResidentReasoner bound |

Do not delete conversation rows or alter shared credentials as routine recovery. Database cleanup is limited to the unique disposable test schema created by the test harness.

## Verification status

Isolated PostgreSQL tests exercise exact read/send grants, persistent history, retry idempotency, model replacement with the same office and conversation, missing-model failure, oversized context, and restart reconciliation. The installed 0.6B CPU model's first open-ended browser chat exceeded 120 seconds and was truthfully saved as `model_timeout`; that run is not successful inference evidence. Browser and actual CPU-model outcomes are recorded in the linked checkout evidence; unit tests alone do not establish browser commissioning or operational Grace. Shared dashboard deployment, Steward browser acceptance, conversation privacy/retention policy approval, multi-process conversation serialization, and the proposed M3.4 formal sequencing decision remain open.

Process graph: [`RESIDENT_CONVERSATION_FLOW.md`](RESIDENT_CONVERSATION_FLOW.md), graph ID `rv:resident-conversation:browser-chat`.
