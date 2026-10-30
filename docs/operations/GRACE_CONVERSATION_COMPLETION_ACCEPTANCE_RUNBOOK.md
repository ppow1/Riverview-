<!-- Controlled document revision 1.0.0 | 2026-10-28 -->
# Grace conversation completion — isolated live acceptance procedure

## Goal and boundaries

Use one newly created **Talk with Grace** conversation for a single DEVELOPMENT acceptance request. The objective is to create and independently verify `reports/grace_delivery_20261028.txt` with exact UTF-8 contents `GRACE-DELIVERY-20261028`, then have Grace return a completion message to that same originating conversation. Artifact verification and conversation lifecycle acknowledgement are separate evidence. The chat message cannot establish artifact correctness. This procedure has not been run; no conversation or objective was created during discovery. Do not publish to GitHub, deploy, edit source, change grants, reuse an old conversation, manually append a completion, or inspect unrelated conversation content.

## Exact Dashboard workflow

1. Open the existing authenticated Dashboard and **Talk with Grace** using the Steward’s own account session. Do not copy/discover cookies or tokens. Click **New conversation**.
2. In the composer, send this bounded request as the first message:

   > Create `reports/grace_delivery_20261028.txt` with UTF-8 contents exactly `GRACE-DELIVERY-20261028`. Have the existing Engineering worker produce the file and let the independent verifier verify its exact path and contents. After the objective is verified COMPLETED, return a concise completion message in this same originating conversation. The chat message is lifecycle acknowledgement only; it is not evidence that the artifact passed verification.

3. Wait until that user message appears in durable history. On that exact message, open **⋯** and select **Create Work Order…**. The dialog is titled **Create Engineering work order**. Optionally enter this single criterion (one line) in **Acceptance criteria**: `Independent verification confirms reports/grace_delivery_20261028.txt exists with UTF-8 contents exactly GRACE-DELIVERY-20261028.` Click **Submit objective**. The UI submits `{source_sequence: <selected persisted user-message sequence>, acceptance_criteria: [<criterion>]}` to `POST /api/v1/resident/conversations/{conversation_id}/work-orders`; if the criteria box is blank it sends `[]`. The handler accepts a positive integer sequence and an optional list of at most 20 nonempty strings, each at most 1000 characters. The 202 response confirms intake/grounding only, not execution, verification, or completion.
4. For artifact evidence, use only the canonical authenticated objective status projection for this objective and require status `COMPLETED` and verifier `ACCEPTED`. Do not treat a chat claim as artifact verification. For lifecycle evidence, require the same objective’s latest event marker `conversation.result_published`, then refresh the original new conversation and confirm Grace’s automatically published assistant completion message is present there. Do not manually append any message.
5. Record only this test’s conversation ID, persisted source sequence, objective ID, status, verifier decision, and receipt marker/time. Avoid other conversation content. The safe objective projection omits the full receipt payload and completion-cycle value; the marker proves durable publication but does not expose those details. Read only the single resulting assistant completion needed for user-visible confirmation.

## Authentication and routing

The browser UI uses the existing same-origin Dashboard session. Normal chat checks the Steward’s exact `resident.conversation.send` office grant. Work-order intake requires an authenticated Steward account session, same-origin/CSRF, `resident.conversation.read`, and `objective.submit` on fixed `work-order:engineering`; the handler reloads the source event and confirms it is a user message authored by that same principal. The route derives immutable origin from that conversation ID and source sequence. Assignment creation and registered worker/verifier permissions remain separately checked. The Comms5 connector has no conversation send/history/work-order operation, and this environment exposes no generic authenticated Dashboard HTTP client; do not bypass the UI boundary.

The existing implementation is in Dashboard release `/opt/riverview-status-dashboard/releases/8325d3ffe8e53f3deaab4c9e14e471467454a08b-grace-controls-20261028-r2`: `website/v2/deployed/index.html:384-385`, `website/v2/deployed/assets/grace-chat.js:891-928,510-550`, `src/riverview_core/status_dashboard/server.py:1348-1400,2080-2115`. The internal Grace owner runner publishes through its existing durable outbox after verified completion; it rechecks Grace’s own binding and `resident.conversation.send`, and acknowledges only after assistant message persistence. This is automatic service behavior, not a manual action.

## No execution performed

This runbook is a prepared acceptance procedure only. No message, conversation, objective, provider request, database operation, deployment, source edit, or grant change was performed. `discovery.json` holds the exact request, criterion, UI sequence, body-free evidence requirements, and current projection limits.

## Current client limitation and continuation

This procedure remains PREPARED, NOT EXECUTED. Root attempted the permitted Dashboard browser fallback because the Comms5 interface has no conversation send/history/intake operations. The cloud browser returned net::ERR_CERT_COMMON_NAME_INVALID for the established LAN IP; its URL policy then refused observation of the error page. No security-warning bypass or alternate browser surface was attempted. This does not establish a server outage or invalid grants.

The practical next action is the exact bounded request above in the user's already-working authenticated Dashboard. After Create Work Order… / Submit objective, retain the objective ID and original conversation ID/source sequence. Comms5 objective_status can observe the canonical objective and bounded event lineage without taking over the browser. Inspect that lineage for conversation.result_published; a latest-event-only UI projection can be superseded by later feedback events. The original isolated conversation must still be checked for an automatically persisted assistant message. No manual completion append. No new grants, transport or service are required.

Evidence is a delivery smoke test, not a repeat of source-engineering acceptance. The real source workflow already completed, including3 verified dependent steps and3 feedback cycles. This test adds only conversation-origin intake and automatic result delivery. The latest accepted source-target patch remains undeployed per its task scope.
