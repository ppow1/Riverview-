<!--
Riverview~ Controlled Development Record
File: docs/development/RV-GRACE-ENGINEERING-CAPABILITY-GAPS-001_REVISION_RECORD.md
Component: RESIDENT-ORCHESTRATION
Document Revision: 1.0.1
Purpose: Record implementation and validation for multi-file Codex, multi-step CME, and Grace continuation gaps
Authority: Development-only; no production migration, grant, service, or deployment authority
Changed: 2026-10-16 UTC | RV-GRACE-ENGINEERING-CAPABILITY-GAPS-001 | Record isolated implementation and production limitation
Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Append superseding artifact-contract implementation record without rewriting historical findings
Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md; docs/components/GRACE_PERSISTENT_EXECUTION.md; docs/components/WORKER_ADAPTER.md
Tests: Canonical unittest suite on disposable PostgreSQL; process graph and revision audits
History: Git and .riverview-backups/manifest.jsonl
-->
# Grace Engineering capability gaps — implementation record

## 2026-10-20 superseding artifact contract correction

The 2026-10-16 statement below that described the then-current single-output
adapter is retained as a historical record of that implementation. It is
superseded by `RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001`: new Codex artifact
assignments carry exact names, safe relative paths, supported media types,
per-artifact acceptance criteria and size limits in the persisted proposal and
dispatch record. The worker, independent verifier, recovery path and Grace
review handoff now process the complete contract-defined set. No universal
filename is configured or accepted as a fallback.

## Source changes

- **A — multi-file source changes:** Added the separate `engineering.codex-cli-source-change.v1` typed capability. It requires an immutable repository commit, explicit allowed path list, criteria, fixed test targets, and bounded timeout. It creates a changed-file inventory and SHA-256 protected patch in a disposable clone, runs fixed tests inside offline bubblewrap, and has an independent verifier that reapplies the patch to a second clean clone and reruns tests. The legacy `deliverable.md` adapter is unchanged. The worker adapter recognizes this capability only with its own registration and the exact same-scope `assignment.execute` grant. It is not automatically dispatchable from Grace's persistent service because the current proposal/work-order representation has no per-step path-scope field; no broad environment allowlist substitutes for that field.
- **B — durable multi-step proposals:** Resident proposal validation now permits up to 20 dependency-ordered steps. Migration `0009_durable_objective_steps.sql` persists ordered steps and distinct assignment identities, carries predecessor state forward, and grants `riverview_core` only the selected columns it needs. CME dispatches only dependency-ready steps, each through normal lease, attempt, verifier, retry, and recovery records. The objective completes only after all durable steps have independent accepted verification. Production migration 0009 was not applied.
- **C — model-reviewed continuation:** Grace result review now requires a typed decision (`OBJECTIVE_COMPLETE`, `ADDITIONAL_EVIDENCE_REQUIRED`, `ENGINEERING_STEP_PROPOSED`, or `STEWARD_AUTHORIZATION_REQUIRED`). A continuation is restricted to the original objective and accepted criteria, revalidates the active binding, is durably appended as another objective step, and is dispatched only through ordinary CME authorization. Result outbox idempotency is scoped to the completion cycle. Model text never creates grants.
- **Owner-session diagnosis:** Persistent Codex uses service-local writable runtime state and a read-only bind of the existing ChatGPT `auth.json`; it does not copy credentials or use API billing. Startup now requires the CLI package's executable `codex-code-mode-host` companion and reports a sanitized preflight failure if absent.

## Validation evidence

- Canonical command: `RIVERVIEW_TEST_PG_DSN=<disposable PostgreSQL 16 DSN> PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- Result: 428 tests passed; 1 existing dashboard-role test skipped because the disposable cluster did not define that runtime role.
- Focused run for the modified pipeline, provider, adapter, and PostgreSQL tests: 70 passed.
- Multi-file Codex adapter test creates two source files and one test in a temporary pinned Git clone, inventories and hashes the patch, runs a fixed offline sandbox test, then has an independent verifier replay it in another clone. The CLI in this test is synthetic; it is not evidence of real Codex model execution.
- Multi-step PostgreSQL integration verifies assignment identity per step, dependency blocking until predecessor verification, same-objective continuation, and cycle-scoped return receipts. The reasoning provider is a bounded test double.
- `python3 scripts/process_graph.py validate`: 19 graphs PASS. `python3 scripts/process_graph.py check`: 19 graphs / 463 nodes PASS.
- `python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json`: PASS, no findings.
- `systemd-analyze verify deploy/systemd/riverview-grace-execution-owner-session.service`: PASS.

## Production commissioning status and limitation

The originating production objective remains uncompleted:

- Objective: `objective:grace-conversation:2c573041-cc5e-4b54-9f93-8163de91e52c`.
- Assignment: `assignment:grace:6759a4f47a95aad779e0bd76699fed9a71098ae8`.
- Durable state last verified during commissioning: assignment blocked as `WORKER_RETRYABLE_NO_ARTIFACT`, after the configured three recovery-safe retries. No artifact, accepted verifier record, or Grace completion response was produced.
- The production Codex package at `/opt/riverview-codex/bin` lacks executable `/opt/riverview-codex/bin/codex-code-mode-host`. A direct CLI experiment without a real file was correctly rejected by the artifact verifier. The existing production retry ceiling must not be bypassed.

This PR does not deploy code, apply migration 0009, change grants, reopen the blocked assignment, or alter production services. The next production action is to stage and verify the complete approved Codex CLI package (including the Code Mode host) through the release process, then obtain the required authorized disposition to resume the assignment after retry exhaustion. No Codex credentials may be copied, refreshed, or exposed by this change.
