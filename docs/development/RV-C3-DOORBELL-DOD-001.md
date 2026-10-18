<!--
Riverview~ Controlled Document
File: docs/development/RV-C3-DOORBELL-DOD-001.md
Component: CHATGPT-DOORBELL
File Revision: 1.0.1
Purpose: Evidence-based eight-gate component DoD assessment and blocker register
Changed: 2026-10-18 UTC | RV-C3-DOORBELL-DOD-001 | Record PR #99 source integration and remaining live commissioning blockers
Owner: Codex 3 / New-Core
Execution Model: Request-driven acceptance record
Observability: Versioned checkout evidence and canonical process graph
Dependencies: COMPONENT_DEFINITION_OF_DONE.md Rev 1.6; doorbell code and external Comms5/Grace owners
Inputs: Test results, status contract, host qualification, interface contracts
Outputs: Gate statuses, evidence references, blockers and completion decision
Authority: Assessment only; no production deployment or wake authorized
Contracts: docs/components/CHATGPT_DOORBELL.md; docs/components/CHATGPT_DOORBELL_COOKBOOK.md
Tests: evidence/checkouts/CHATGPT-DOORBELL/<checkout>/
History: Git and .riverview-backups/manifest.jsonl
-->
# RV-C3-DOORBELL-DOD-001 — Component acceptance record

**Component:** `CHATGPT-DOORBELL` · **DoD standard:** Rev 1.6 · **Status:** **NOT DONE**  
**Source integration:** COMPLETE — PR [#99](https://github.com/ppow1/Riverview-/pull/99) merged to `main` at `d209ce33c3b863e9d21b9421f62100a5493a093f` (head `7f59d2a7915670593caa50d02c8942533c341651`; both required controlled-checkout checks passed).
**Operational commissioning:** BLOCKED — dedicated browser authentication/MFA, current exact-conversation verification, Comms5 mailbox lifecycle availability, and full Comms5-to-Grace acceptance remain outstanding.
**Environment:** Camrui Ubuntu qualification only; no production service deployment and no live wake performed.
**Current interface evidence:** Comms5 capability catalog lacks mailbox lifecycle operations; Codex 1 is coordinating the contract in [issue #96](https://github.com/ppow1/Riverview-/issues/96).

## Eight-gate assessment

| # | Gate | Status | Evidence and remaining acceptance |
|---|---|---|---|
| 1 | Code and contracts | PARTIAL | Versioned Linux bridge, exact target binding, fixed wake, bounded timeout, identity-preserving result, local status schema and unit tests exist. Caller is not connected to a durable Comms5 source; Comms5 and Grace contracts are not commissioned. |
| 2 | Functionality demonstrated | PARTIAL | Unit and negative tests demonstrate bridge contract and metadata safety. No authorized live ChatGPT wake, mailbox claim/response, PostgreSQL completed state, Grace consumption, deployed fault/restart/replay, or production acceptance. |
| 3 | Complete versioned documentation | PASS | [`CHATGPT_DOORBELL.md`](../components/CHATGPT_DOORBELL.md) documents actual boundaries, config, auth, lifecycle, security, retries and rollback; this record and status schema are versioned. |
| 4 | Troubleshooting cookbook | PASS | [`CHATGPT_DOORBELL_COOKBOOK.md`](../components/CHATGPT_DOORBELL_COOKBOOK.md) maps workflow nodes to commands, signals, safe recovery and owners, including a consolidated read-only procedure. |
| 5 | Versioned visualization flowcharts | PASS | Canonical workflow graph retains stable IDs and distinguishes installed adapter steps from external prerequisites; generated focused Mermaid is synchronized. Structural validity is not runtime proof. |
| 6 | Steward-level live operational visualization | PARTIAL | The graph is registered in the existing graph registry/dashboard route. Owner-local machine-readable status is schema-tested, but no live dashboard consumes authoritative browser/mailbox status, independent status observer, or Steward drill-down is commissioned. |
| 7 | Operational autonomy and blocker clearance | PARTIAL | Service unit defines graphical-session startup and restart behavior, but it is not deployed; durable request intake and unattended resume are not integrated. External blockers below remain unresolved. |
| 8 | Registered canonical process graph | PASS | `rv:chatgpt-doorbell:browser-runtime` is registered and generated via `scripts/process_graph.py`; existing node IDs retained. Cross-component operations are explicit dependency nodes, not claimed runtime transitions. |

**Release decision:** NOT DONE. Do not deploy, enable the production unit, or trigger ChatGPT until the authentication, interface, live acceptance, live visibility, autonomy and authorization gates pass. This assessment is not a Steward waiver.

## External blocker register

| Blocker | Type / detection | Owner / authority | Durable state and timeout | Resume condition and evidence |
|---|---|---|---|---|
| `CHATGPT_AUTH_MFA` | Credential/commissioning; local status `login_required` or `unknown` | Steward completes supported login/MFA | Dedicated profile status; no password/cookie capture. No automatic expiry is assumed. | Steward confirms authenticated access and exact conversation; status/preflight evidence; no wake without separate acceptance authorization. |
| `COMMS5_MAILBOX_OPS` | Dependency; capability catalog omits discover/ack/claim/respond/complete operations | Codex 1; issue #96 | Contract gap retained in issue #96 and status blocker; no timeout can safely be invented by this adapter. | Versioned operation/schema/error/lease/idempotency contract implemented and capability query passes; resume from `chatgpt-mailbox-access`. |
| `MAILBOX_TO_GRACE_ACCEPTANCE` | Dependency; no same-lineage completed response consumed by Grace | Codex 1 + Codex 2, each for owned interface | Acceptance record remains NOT DONE; timeout follows owning request/claim contract once defined. | One authorized bounded test proves request, claim, correlated response, completed state, and Grace consumption with same IDs. |
| `STEWARD_LIVE_VIEW` | Observability; no dashboard reader for this runtime status | Existing Steward/dashboard owner with Codex 3 adapter contract | Local status only; freshness threshold 60 seconds. | Dashboard consumes authenticated read-only authoritative status, shows stale/unavailable correctly, and passes independent client failure/recovery tests. |
| `PRODUCTION_DEPLOYMENT` | Approval/readiness; no production deployment approval | Steward / deployment owner | Not deployed. Authorization must precede service enablement. | Controlled deployment and rollback evidence after all technical acceptance prerequisites pass. |

## Test and evidence record

The authoritative run record belongs under
`evidence/checkouts/CHATGPT-DOORBELL/<UTC>-<source-commit>/`. It must state exact commands, UTC timestamps, exit codes, pass/fail counts, branch/commit, host/environment, status snapshot classification, and exceptions. Tests prove source behavior only. Existing qualification evidence is
[`runtime-qualification.json`](../../evidence/checkouts/CHATGPT-DOORBELL/20261017T233224Z/runtime-qualification.json); it records an authenticated/target qualification state at that earlier time and must not be treated as current auth or mailbox acceptance.

No production service or live ChatGPT wake was invoked for this task. The six unresolved operational acceptance dimensions are deliberately retained as PARTIAL blockers rather than inferred as PASS.

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1.0.0 | 2026-10-18 | Initial evidence-based DoD assessment and blocker register for RV-C3-DOORBELL-DOD-001 |
| 1.0.1 | 2026-10-18 | Record PR #99 merge and distinguish completed source integration from blocked live commissioning |
