# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/CHATGPT_DOORBELL_COOKBOOK.md
# Component: CHATGPT-DOORBELL
# File Revision: 1.0.0
# Purpose: Diagnose and recover the fixed browser wake and C2 durable exchange adapter
# Execution Model: Read-only operator guidance; recovery is owned by the durable exchange
# Observability: Owner-local doorbell status plus Grace/exchange status and sanitized events
# Dependencies: CHATGPT_DOORBELL.md, CHATGPT_DOORBELL_DISPATCH.md, EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md
# Authority: Diagnostics are read-only; enabling or waking the browser requires separate authorization
# Changed: 2026-10-19 UTC | RV-C2-DOORBELL-RESUME-20261019 | Add node-level diagnosis, retry, restart, and safe recovery guidance
# History: New file; Git and .riverview-revisions.json

# ChatGPT Doorbell and Dispatcher Recovery Cookbook

## Purpose and scope

This cookbook covers the existing local ChatGPT fixed-wake bridge and C2's
default-off `DoorbellWakeWorker`. It does not authorize enabling the worker,
starting a browser, contacting ChatGPT, replaying a wake, or changing a provider,
grant, target binding, service, or database. Production and real-browser
acceptance require separate Steward authorization.

The durable external-reasoning exchange is authoritative for request state,
lease ownership, fences, retry timing, deduplication, and receipt events. The
browser's local journal is supporting metadata only. The worker passes only
request/correlation identity and the configured exact target to the bridge; it
does not receive proposal or response bodies.

## Ownership and execution model

- **Component:** `CHATGPT-DOORBELL`; C2 owns `DoorbellWakeWorker` and runtime
  composition.
- **Related owner:** `RESIDENT-REASONING` / C3 owns durable request, claim,
  receipt, retry, and recovery semantics.
- **Execution:** one request-driven worker cycle is called by the existing
  recurring Grace owner-session loop. Feature composition is off unless
  `RIVERVIEW_CHATGPT_DOORBELL_ENABLED=1` is explicitly configured.
- **Identity:** the provider ID must already exist in the configured exchange;
  the internal owner is `service:grace-chatgpt-doorbell`; the target is loaded
  from the existing private doorbell configuration.
- **Visibility:** `node tools/riverview_browser_runtime.cjs --status` emits the
  owner-local `rv.chatgpt-doorbell.status.v1` snapshot. The owning Grace and
  exchange views provide durable request state and sanitized transition events.
  The local snapshot is not a live Steward dashboard.

## Flow and diagnostic mapping

The canonical flow is registered in
`process_graphs/resident-reasoning/runtime.json` and projected in
`process_graphs/generated/RIVERVIEW_PROCESS_GRAPH.md`.

| Graph node | Expected result | First read-only check | Resume point |
| --- | --- | --- | --- |
| `doorbell-owner-loop-poll` | Existing owner cycle continues; optional worker is polled once | Inspect sanitized Grace cycle logs and owner-session service status | Next normal owner cycle |
| `doorbell-runtime-opt-in` | Feature remains disabled by default; when enabled, provider and target validate | Inspect the release's non-secret feature flag and provider ID configuration; use bridge `--status` for target readiness | Keep disabled until exact settings and authority are reviewed |
| `doorbell-durable-claim` | C3 returns one due metadata-only claim with a valid fence and enough lease time | Query exchange `status(request_id, correlation_id)` and `events(...)` through the authorized diagnostic client | Let the exchange lease expire or wait for its retry eligibility |
| `doorbell-fixed-wake` | C2 calls the bridge once with the original IDs and exact configured target | Check owner-local bridge status; inspect only the stable failure code | For known pre-send failure, allow exchange backoff; for ambiguity, stop automatic retry |
| `doorbell-durable-receipt` | C3 persists exactly one fenced outcome | Read exchange status/events for the same request/correlation IDs and owner actor | Let durable state control eligibility; never submit a manual receipt |
| `doorbell-worker-failure` | Failure is reported as a stable code and does not stop the rest of Grace's cycle | Inspect sanitized service logs and dependency status | Resolve the named dependency; continue at the next owner cycle |
| `doorbell-lease-recovery` | Existing request remains authoritative; stale lease/fence cannot replay a wake | Re-read exchange status/events after lease expiry or service restart | Resume only when the exchange reports eligible work |

## Read-only diagnostics

Run these from the deployed source release only when separately authorized to
inspect that environment. These commands do not submit a wake:

```bash
node tools/riverview_browser_runtime.cjs --preflight
node tools/riverview_doorbell_bridge.cjs --preflight
node tools/riverview_browser_runtime.cjs --status
systemctl --user status riverview-doorbell-browser.service --no-pager
systemctl status riverview-grace-execution-owner-session.service --no-pager
journalctl --user -u riverview-doorbell-browser.service --since '30 minutes ago' --no-pager
journalctl -u riverview-grace-execution-owner-session.service --since '30 minutes ago' --no-pager
```

The preflight/status commands return bounded local metadata and readiness; they
must not print page text, assistant responses, cookies, credentials, bearer
tokens, or proposal/response bodies. Inspect only sanitized stable error codes
and IDs needed for correlation. If a command reports an unsupported option,
check the exact deployed release's contract before trying another command.

For durable state, call the existing authorized exchange diagnostic methods
`status(request_id, correlation_id)` and `events(request_id, correlation_id)`.
The exchange cookbook documents their bounded projection and state meanings:
[`EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md`](EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md).
Do not query or copy request payloads for routine diagnosis.

## Error and recovery guide

| Signal | Meaning | Safe recovery |
| --- | --- | --- |
| `doorbell_enable_flag_invalid` | Feature flag is neither `0` nor `1` | Keep the feature disabled and correct the exact setting through normal release controls |
| `doorbell_provider_id_required` | Opt-in omitted the existing provider identity | Keep disabled; use the already registered provider ID; do not create or rotate credentials |
| `doorbell_provider_not_registered` | Provider is absent or inconsistent in the exchange map | Keep disabled; reconcile the approved existing map and release configuration |
| `doorbell_target_or_worker_invalid` | Existing target configuration or worker construction failed | Keep disabled; inspect owner-local status and correct only through reviewed deployment configuration |
| `doorbell_owner_loop_hook_unavailable` | Release's Grace service does not implement the optional worker hook | Use a compatible reviewed release; do not remove the compatibility check |
| `claim_metadata_invalid` | Claim identity, provider, attempt, fence, or lease metadata failed validation | Do not ring. Preserve the request and let the durable lease recover |
| `RIV-PLY-0002` | Invalid request envelope or timeout setting | Correct caller configuration; preserve the original request and correlation IDs |
| `RIV-PLY-0003`, `0004`, `0009`, `0014` | Transport/CDP uncertainty, timeout, or result lineage mismatch | Receipt is ambiguous; do not automatically wake again. Reconcile the existing exchange and bridge status |
| `RIV-PLY-0005`–`0008`, `0010`–`0013`, `0015`–`0016` | Known pre-send browser/config/runtime failures according to the bridge contract | C2 classifies only its enumerated known pre-send codes as retryable; let the exchange enforce bounded backoff and attempt limits |
| `receipt_write_failed` / `receipt_unavailable` | Wake outcome may exist but receipt could not be recorded | Do not manually repeat the wake. Let the fenced lease expire, then inspect exchange state before any further action |
| `ambiguous` | A send may have happened or its lineage is uncertain | Terminal to automatic resend; operator review of authoritative state is required |
| `failed` after retry exhaustion | Existing exchange reached its bounded retry limit | Preserve the record and sanitized events; repair the dependency before a new authorized request is created |

### Restart and resume

After a Grace owner-session or browser service restart:

1. Check service status and the owner-local bridge status without starting a wake.
2. Read the exchange's durable state and events for the existing request and
   correlation IDs through the authorized diagnostic method.
3. If the request remains leased, let that lease expire; never reuse its old
   fence, token, or attempt identity.
4. If it is awaiting bounded retry, allow the existing owner loop to claim it
   when due. The exchange, not the local browser journal, decides eligibility.
5. If it is `awaiting_external_claim`, `awaiting_response`, `response_received`,
   `grace_consumed`, `expired`, or terminal `failed`, continue through the
   existing exchange/provider/Grace workflow. Do not create another request to
   make the status appear healthy.

## Rollback and change safety

The feature is default-off. A reviewed release rollback restores the prior
source/configuration and keeps `RIVERVIEW_CHATGPT_DOORBELL_ENABLED=0`. Browser
unit changes affect only `riverview-doorbell-browser.service`; they must not
alter Grace, Comms5, PostgreSQL, credentials, or grants. Preserve the exact
deployed predecessor and verify rollback using the owning deployment record.
Do not perform production rollback or service activation as part of these
development tests.

## Verification commands

Focused synthetic regressions:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_external_reasoning_doorbell_dispatcher.py'
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_grace_doorbell_runtime_wiring.py'
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_chatgpt_doorbell.py'
node tests/test_riverview_doorbell_bridge_node.cjs
```

The combined disposable PostgreSQL acceptance needs C3's exchange and owner
loop at the assembled W3 integration head. It creates/drops only an isolated
test database and fixture schemas. Exact checkout commands and output are
retained under `evidence/checkouts/CHATGPT-DOORBELL/`.

## Current limitations and DoD status

- C3's exchange and owner-loop dependency is available in the published PR #135
  and assembled W3 source, but is not included in C2's isolated source branch.
- C2 has no production activation. Provider authorization, configured target,
  local authenticated browser, and live ChatGPT behavior remain unverified.
- The browser status is an owner-local snapshot. The live Steward-view gate is
  partial until the shared dashboard consumes authoritative status.
- Disposable database, synthetic bridge, and unit tests prove development
  behavior only; they do not establish unattended deployed operation or a real
  external review.
