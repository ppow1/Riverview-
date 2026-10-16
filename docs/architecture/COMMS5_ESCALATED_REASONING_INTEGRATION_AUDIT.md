<!--
Riverview Controlled Document
File: docs/architecture/COMMS5_ESCALATED_REASONING_INTEGRATION_AUDIT.md
Component: EXTERNAL-REASONING-INTEGRATION-AUDIT
File Revision: 1.0.0
Status: Investigation and integration design; no implementation or live-service acceptance claimed
Date: 2026-10-16
Current source inspected: ppow1/Riverview- branch codex/grace-conversation-ui-refinement, 8938819e0e49b498a312f526c4392a1f42c50930
Historical source inspected: ppow1/Riverview commit 08c1162c4ad04a21df71ed7814a3e22bd9ba41a2
Purpose: Reconcile historical Comms5, mailbox and Playwright doorbell work with current Grace reasoning and proposal lifecycle
Authority: Grace retains workflow ownership; PostgreSQL remains current operational authority; Steward authorization and existing execution controls remain binding
History: New file; no predecessor existed
-->

# Historical Comms and Doorbell Recovery: Integration Audit

## Finding

The smallest safe integration is a **bounded external-reasoning exchange attached to Grace's existing durable objective/proposal lifecycle**, with the existing Playwright doorbell used only to wake the designated ChatGPT conversation and MCP used only to exchange typed request/result data. Grace remains the workflow owner. The external response is advisory input; it is not a proposal approval, work order, assignment, execution result, or verifier decision.

The current `ppow1/Riverview-` branch inspected (`8938819e0e0`, after PR #65 merge `6c33969684e5fa84c35b2456262f187c004c4b0c`) contains Grace's current PostgreSQL-backed reasoning, proposal, objective, CME, worker and verifier paths, but **no MCP package, Comms endpoint, or doorbell implementation**. The current `reasoning_escalation.py` is an in-process provider call contract, not a durable remote request transport; source search found references only in that module and its tests, with no production caller. Historical code is useful evidence and a source of bounded interaction patterns; it is not a drop-in current service or database authority.

This is a source/documentation audit. No production service, authentication, database, browser profile, or objective was inspected or changed. Historical configuration records below are not asserted to be live today.

## Verified current Riverview components

| Component | Current implementation and contract | Relevance |
|---|---|---|
| Conversation and model routing | `src/riverview_core/resident_execution/conversation.py` (1.2.11), `model_router.py` (1.2.1), `local_reasoning_provider.py` | Persistent office-bound conversation, three-stage model routing, provider provenance and deferred-response handling. No external ChatGPT provider or MCP transport is registered in this tree. |
| Operational grounding | `resident_execution/operational_context.py`; `resident_reasoning.py` (1.0.15) | Bounded, read-only institutional context and typed plan proposals. Reasoning proposes; separate policy and pipeline operations authorize actions. |
| Escalated reasoning contract | `src/riverview_core/reasoning_escalation.py` (1.0.2), `docs/components/RESIDENT_REASONING.md`, `process_graphs/resident-reasoning/runtime.json` | Correlated bounded `ReasoningRequest`/`EscalationRequest`, context fingerprint, exact `resident.reasoning.escalate` check, provider allowlist, token/time limits, and typed outcome. `execute()` calls an in-process provider and returns; this module does not persist a request, claim a remote result, ring a browser, or resume a durable workflow. |
| Proposal record | `resident_execution/proposals.py` (1.1.0), `migrations/0010_institutional_proposal_registry.sql`, `process_graphs/grace/institutional-proposal-lifecycle.json` | Durable institution-wide proposal IDs, immutable revisions, search/tags, review evidence and provenance. A proposal remains separate from its originating conversation and from execution authority. |
| Approval and promotion | `resident_execution/proposal_lifecycle.py` (1.0.0), `docs/components/INSTITUTIONAL_PROPOSALS.md` | Authenticated Steward decision binds exact current proposal revision/digest/purpose. Promotion rechecks `objective.submit` and calls the existing objective pipeline; it does not create or dispatch an assignment itself. |
| Execution and verification | `resident_execution/pipeline.py` (1.1.5), `service.py` (1.0.13), `event_processor.py`, `worker.py`, `verifier.py`, worker adapter and CME contracts | Existing durable objective/step events, exact-grant dispatch, leases, Codex adapter, independent verification and recovery. External reasoning must return to this lifecycle rather than create another dispatcher. |
| API and current UI boundary | `src/riverview_core/status_dashboard/server.py` (1.3.18), authenticated `/api/v1/institutional-proposals` contract | Existing authenticated APIs can formalize proposals, inspect/search/revise them, record revision-bound Steward decisions and promote approved revisions. The website is not an MCP endpoint. |

Evidence scope: repository source at the commit above. It does not establish which branch or release is deployed, whether PR #65's migration is installed, or current external connector availability.

## Historical implementation recovered

Historical source is `ppow1/Riverview` at `08c1162c4ad04a21df71ed7814a3e22bd9ba41a2`.

### There are two historical MCP surfaces

The names are easy to conflate:

- `src/riverview/mcp/server.py` exposes the historical mailbox tools: bounded `mailbox_requests`, `mailbox_acknowledge`, `mailbox_claim`, and `mailbox_submit_advisory_response`. `src/riverview/mcp/http_server.py` wraps that server on loopback port 11825 at `/mcp`.
- `src/riverview/mcp/comms5_server.py` and `comms5_http_server.py` define a separate Comms5 application on loopback port 11826 at `/mcp`. Its service in `src/riverview/mcp/comms5.py` provides versioned Comms5 discovery, specifications, Steward seeds, objective/CME status, resource policy and governed operations. **It does not expose the three mailbox tools.**

Thus, the requested historical Comms5 files are relevant to the later bounded multi-client API and its ingress pattern, while the full-loop mailbox contract is implemented in the historical Comms server and `mailbox/store.py`. Reusing “Comms5” by name alone would not recover the mailbox exchange.

Historical deployment documents describe the Comms5 route as `https://riverview-comms.ionoge.com/comms5/mcp`, behind the existing Caddy HTTPS ingress, proxying to loopback 11826, with a separate reverse tunnel. `docs/operations/RIVERVIEW_COMMS.md` documents Comms on loopback 11825 and its own `/mcp` path. `comms5.py` takes server-injected Caddy attestation headers for Steward-gated operations and does not treat body-supplied client identity as authority. These are historical deployment records only; they do not prove either route currently serves the new Riverview schema.

### Mailbox lifecycle contract

`src/riverview/mailbox/store.py` provides the detailed semantics:

- A request has stable request, correlation and optional causation IDs; sender/requester/type; classification; idempotency key; bounded payload or safe reference; and finite expiry (1–86,400 seconds; payload limit 16 KiB).
- Acknowledgement is repeatable. Reasoning claims are fixed to `chatgpt:riverview_001`; the claim has a bounded lease (the MCP path defaults to 120 seconds). A live lease is exclusive; an expired claim can be reclaimed under the same request/correlation identity. An expired request is terminal and is not revived.
- The response operation requires the matching correlation and active claim, validates bounded summary/evidence references, stores a versioned `rv-008.4-response-v1` envelope and completes the request transactionally. Retries return the existing response rather than creating a second terminal response. Expiry creates one durable escalation.
- `src/riverview/grace/responses.py` validates producer, response ID, request/correlation, classification, schema and evidence; consumes idempotently; and records `grace.response.consumed` / `grace.response.evaluated` events.

The public mailbox response tool fixes its semantics to `advice` and non-escalating. It does not accept arbitrary state updates, shell/filesystem access, work-order creation, or execution authority.

### Playwright doorbell boundary

- `src/riverview/doorbell/browser_bridge.py` requires the named designated conversation and mailbox resource, resolves the active binding from `BindingRegistry`, checks that the local conversation ID matches it, and invokes one named Node operation with request/correlation IDs and a bounded timeout.
- `src/riverview/doorbell/config.py`, `tools/riverview_browser_runtime.cjs`, and `tools/riverview_doorbell_bridge.cjs` bind the browser to a separate Riverview profile, localhost-only CDP, exact ChatGPT conversation ID, fixed wake text, bounded selectors/action, and metadata-only evidence. The bridge verifies that the composer was cleared after send and journals by request/correlation to suppress duplicate successful wakes. It does not scrape or read the ChatGPT response.
- The historical browser code assumes a Windows checkout/runtime (`A:\Riverview`, Windows Chrome and `%LOCALAPPDATA%` Playwright paths). A Camrui/Linux adaptation is therefore required; the protocol and target restrictions can be reused, but paths, process supervision, browser profile ownership, and service hardening cannot be copied unchanged. The authenticated browser profile must remain under its designated OS account and must not be copied into a service credential store.

## Historical evidence and failure boundary

| Boundary | Historical evidence | What it establishes |
|---|---|---|
| Local mailbox lifecycle | `src/riverview/mailbox/rv0045_acceptance.py`, mailbox contract tests and `RIV-MCP-0009_FULL_LOOP_MAILBOX.md` | Local acceptance exercised accepted → acknowledged → claimed → response-completed, duplicate retries, and expiry/escalation behavior. This is local contract evidence, not proof that ChatGPT used a deployed connector. |
| External MCP transport | `docs/operations/RIVERVIEW_COMMS.md` and `RIVERVIEW_COMMS5_DEPLOYMENT.md` | Dated records report authenticated initialization, tool/resource discovery and bounded reads on the public Caddy/MCP path. The documents refer to two different server surfaces and do not prove current deployment/configuration. |
| Browser wake | `RIV-PLY-0002_BROWSER_DOORBELL_END_TO_END.md` | One authorized fixed wake has durable `submit_verified` evidence. A successful wake only proves the fixed message was submitted to one configured target. It does not prove a subsequent reasoning turn or MCP call. The checkpoint records a wake followed by no acknowledgement, claim, response or completion. |
| ChatGPT acknowledgment/claim | `RIV-MCP-0009_FULL_LOOP_MAILBOX.md` | A later live attempt did acknowledge and claim. The earlier response-write shape was rejected by ChatGPT's safety layer before Riverview received it; that failure was at the tool schema/platform boundary, not PostgreSQL. |
| Response tool/schema drift | Same checkpoint | ChatGPT administration showed a repaired typed response tool while an already-open conversation continued exposing the old `mailbox_submit_response` schema. The documented boundary is conversation-level schema binding/cache; updating the server/tool listing alone did not refresh that conversation. A request that expired before schema refresh remained terminal. |
| Grace consumption | `RIV-GRC-0003_REASONING_RESPONSE_CONSUMPTION.md`, `grace/responses.py` | The consumer validates and records an advisory response idempotently. Historical advisory acceptance could complete only its declared legacy `response_return` stage; it did not create Engineering work or demonstrate Codex execution/independent verification. |

The August 15 `RIVERVIEW_COMMS.md` snapshot asserts RV-004.5/RV-008.4 completion, while the more specific troubleshooting checkpoints preserve failed live lineages at wake-only, blocked response-write and stale conversation-schema boundaries. Treat the headline as a dated milestone assertion, not transferable evidence for a single request that traversed every boundary. The supplied records do not establish live behavior on the current new-Riverview deployment.

## Reuse, adapt, retire

| Decision | Components |
|---|---|
| Reuse in place | Current `ReasoningRequest`/`EscalationRequest` correlation and fingerprints; current objective/proposal records and lifecycle; existing event ledger, assignment scheduler, CME service, Codex worker and independent verifier. Historical exact-target doorbell invariants, fixed wake, local-only CDP, submission evidence, bounded MCP tool shape, request/correlation lineage, lease/retry/expiry semantics, and schema-version checks are valuable patterns. |
| Adapt narrowly | Create a current-Riverview external reasoning adapter around the existing escalation contract. Persist one external exchange identity tied to the originating objective and, when applicable, exact proposal revision. Keep exchange delivery/claim state separate from objective/proposal authority, but in the same PostgreSQL transaction/event lineage. Expose only get/claim/submit operations for the caller's assigned request; validate strict schema, correlation, lease, expiry, evidence references, classification and idempotency. Feed validated results back to Grace's configured reasoner; only Grace's typed result evaluation can create/update a proposal or plan. |
| Retire as authority | Do not transplant the old `mailbox_messages`, old `objectives`/`objective_stages`, old `grace_response_consumptions`, Windows runtime paths, or old provider IDs as a second current authority. Do not import historical records into production or make the old Comms endpoint mutate the new database. Retain those files and records as historical provenance. |
| Conditional infrastructure reuse | Reuse the existing `ionoge.com` Caddy/MCP ingress pattern only after confirming the route and service owner for the target environment. The current engineering repository has no MCP package/server and does not prove that the historic Comms5 endpoint shares the current `riverview_dev` database. The historic Comms5 implementation is not a ready-made backend for current Grace. This is a real transport/service integration dependency, not a reason to reuse the legacy mailbox database. |

### Smallest implementation increment

1. **Current DB exchange record/outbox:** add a narrowly scoped durable external-reasoning request/result record linked by foreign/provenance references to the current objective, conversation/source message, and proposal revision where present. Reuse `grace_objective_events` for transition history and current idempotency patterns. The row is a delivery/lease envelope only; current proposal/objective tables remain authoritative. It needs immutable request/correlation/schema/context digests, explicit privacy classification, expiry, status, claimant/lease/fencing identity, response digest/provenance, consumed timestamp, and a unique idempotency key.
2. **Existing escalation adapter:** extend `reasoning_escalation.py` so the authorized external target can enqueue/recover this record and resume through the existing `ResidentReasoner`/`GraceExecutionService`. A timeout or absent MCP action stays pending until finite expiry and produces a diagnostic/Steward attention event. Retries retain the same identity; terminal results cannot be overwritten or replayed.
3. **Narrow MCP operations:** add typed read/claim/submit operations to the approved MCP host/route that can reach the current database under a least-privilege runtime identity. Reject client-supplied authority claims; authenticate the connector at the existing HTTPS ingress and pass trusted principal context server-side. If no active MCP host can be extended, service ownership and deployment of the transport must be resolved before code-level acceptance; do not assume historical Comms5 is present/current.
4. **Camrui/Linux doorbell adapter:** port only the named browser operation and preflight/journal contract. Use an exact binding-selected conversation, separate owner-session browser profile, loopback CDP, systemd supervision, bounded timeout, and metadata-only logs. Never read page response text, select a fuzzy/latest conversation, expose CDP publicly, or copy the session profile/credentials. Doorbell success is a wake event, not a reasoning result.
5. **Grace consumption and lifecycle link:** validate the external response against the originating request and objective snapshot, persist its digest and provider/request metadata, and have Grace reason over it. A result can ground/revise a proposal or request clarification. It cannot set proposal approval, create an assignment, claim work succeeded, or mark an Engineering objective complete. Any work order still follows current proposal-revision review, Steward decision, exact `objective.submit`, separate `assignment.create`, worker lease, independent verifier and final Grace evaluation.
6. **Diagnostics and process graph:** extend the existing resident-reasoning/Grace operational process graph rather than add a second orchestration graph. Add named nodes for enqueue, doorbell, remote tool discovery/claim, response validation/commit, Grace consumption, expiry/schema drift, and retry/recovery. Correlate each node to durable request/objective/event IDs, checkpoint references and sanitized outcome codes. Provide a read-only diagnostic projection through the existing dashboard APIs; do not expose payloads or secrets.

## Dependencies and risks

- **MCP surface mismatch:** current repo has no MCP server. The historical Comms and Comms5 services are distinct and use the predecessor data model. The future implementation must confirm which existing service can safely be extended or establish the narrowly scoped current transport owner; it must not silently connect current Grace to the legacy database.
- **Connector schema freshness:** tool discovery in application administration does not prove that the designated ChatGPT conversation has the current schema. Test the exact configured conversation after refresh before creating a request, and bind each request to the schema version. A schema mismatch is a delivery failure, not permission to replay/extend an expired request.
- **ChatGPT turn behavior:** a Playwright wake may be submitted successfully with no MCP call. Bound this with one durable request, a finite deadline, observed tool-call events, and one wake attempt per idempotency identity. Do not scrape the conversation to infer success.
- **Session security:** the old browser profile is Windows-specific and contains an authenticated session. Migration to Camrui requires clear owner-session security boundaries and an explicit session bootstrap; no browser credential copying.
- **Privacy and retention:** do not forward restricted/local-only source content to an external ChatGPT session. Start with a synthetic, non-sensitive, bounded reasoning task and explicit classification/retention; reject disallowed material before queueing.
- **No verified live-current state:** all historical external route, connector, browser session, and acceptance claims need current metadata-only preflight before commissioning. No production deployment or current live MCP request was part of this audit.

## Decisive acceptance procedure

Use an isolated objective and non-sensitive synthetic content; no production objective is reused. Record a correlation ID and one external-request ID throughout.

1. Submit a bounded objective through the current Grace interface. Verify the durable objective and verified grounding exist, and that Grace's escalation decision passes the current exact grant. Persist one external request with immutable context/source digest, required schema, classification, proposal/objective references, finite expiry and idempotency key.
2. Invoke the designated Playwright doorbell once. Verify exact binding match, authenticated profile readiness, one target, `submit_verified=true`, attempt ID and timestamps. Do not infer that ChatGPT acted from browser submission alone.
3. Through the exact designated ChatGPT conversation, verify the current MCP tool schema; call request read/claim with the same IDs. Persist the claim lease and corresponding events. A second concurrent claimant must be rejected; a post-lease retry may reclaim only the same unexpired request.
4. Submit a strict versioned response with request/correlation IDs, bounded reasoning result, evidence references, response digest and provider metadata. Verify one accepted response, one terminal event and no duplicate on retry. Malformed schema, stale context, wrong correlation/principal, expired request, or duplicate conflicting response must fail closed.
5. Verify the external request is durably correlated to the original objective and any exact proposal revision, then have Grace's actual configured reasoning provider consume and evaluate it. Verify persisted provenance, a durable Grace decision, and the next state chosen from the current proposal/objective lifecycle.
6. Demonstrate downstream consequence separately: either a durable clarified/revised proposal, or (only when an existing authorization/approval and exact grants permit) normal work-order promotion, CME dispatch, real worker output, independent verifier decision and Grace completion. MCP communication success alone is a **transport PASS**, never an Engineering-completion PASS.
7. Restart the owning service between claim/result and Grace consumption in a controlled isolated test. Show recovery without another wake, duplicate result, duplicate proposal/assignment, or loss of the originating conversation/objective. Include fault injections for schema stale, browser offline, no MCP action, expired request, response rejected before server, invalid correlation, and unavailable external route; show diagnostic event/checkpoint and exact resume or terminal disposition.

**Separate measured acceptance gates:** (a) MCP transport round trip; (b) Grace consumption and durable next decision; (c) proposal/work-order lifecycle; (d) worker execution and independent verification, if authorized. Do not combine these into one green status when any later gate has not run.

## Audit limits and next increment

Inspected current source is the immutable branch snapshot named above, not the production release. Historical sources are the `08c1162` checkout and dated operational checkpoints. No current production database, logs, Caddy route, ChatGPT application configuration, or browser profile was queried. The current implementation gap is source-verified; the live route/session state remains unverified.

**Recommended next increment:** a focused design/implementation PR for one current-database-backed external reasoning exchange and a thin typed MCP adapter integrated with the existing escalation request, followed by a Linux doorbell adapter. Keep proposal approval, Engineering dispatch, and verification in their existing authorities. Before implementation, resolve whether an active approved MCP service can host this adapter; do not mistake historical `comms5_server.py` for proof that it can.
