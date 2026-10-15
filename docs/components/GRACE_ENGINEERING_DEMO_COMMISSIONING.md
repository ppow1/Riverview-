<!--
Riverview~ Controlled Document
File: docs/components/GRACE_ENGINEERING_DEMO_COMMISSIONING.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.1
Purpose: Prepare the first bounded authenticated Grace-to-Codex Engineering demonstration
Authority: Existing Steward grants, AuthorityRegistry, CME, worker, verifier, and conversation contracts
Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Record exact source, database, grant, worker, and rollback gates
Changed: 2026-10-15 UTC | RV-GRACE-CODEX-SANDBOX-READINESS-001 | Record the fail-closed host sandbox blocker and commissioning preflight
Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md; docs/components/GRACE_EXECUTION_PIPELINE.md
Tests: tests/test_codex_cli_adapter.py; tests/test_worker_service.py; PostgreSQL integration suite
History: Git and .riverview-backups/manifest.jsonl
-->

# Grace Engineering Demonstration Commissioning

**Status: NO-GO for live demonstration.** Source integration and tests are ready for review. Live exact-scope grants are incomplete and the Grace execution worker is not installed. No production state was changed by this preparation.

## Demonstration path

1. The authenticated Steward sends the bounded objective in Talk with Grace, then uses the message menu's **Create Engineering work order…** action and supplies acceptance criteria. The dashboard route persists the objective with conversation origin and requires `objective.submit` on `work-order:engineering`.
2. The persistent Grace service grounds the request, asks the currently bound 80B to formulate a typed proposal, and persists provider/model provenance. A proposal does not authorize execution.
3. The service dispatches only after `assignment.create` succeeds. Existing CME events and leases move the assignment to a registered executor. The Codex action checks the pinned local source revision, creates a fresh clone, allows one fixed `deliverable.md`, and exposes no command/path/model controls to Grace.
4. A distinct verifier reopens the artifact and checks assignment path, file type, mode, size, digest, source pin and literal acceptance criteria. Only persisted `ACCEPTED` verification completes the objective.
5. A durable idempotent outbox rechecks the current Grace binding and conversation-send grant, has the bound 80B evaluate the evidence, and appends one result to the original conversation.

## Current verified baseline

- Engineering checkout: `ppow1/Riverview-`, branch `codex/grace-deferred-80b-route`; PR #34 is open, cleanly mergeable, and its controlled-checkout check passed. It has no recorded review approval and is not merged.
- PR-head source before this owner-session follow-up: `2f397070a0629ec3eed29598bfe4c3fe9454dc6e`. The follow-up requires review, CI and a new immutable package before it can become a candidate.
- Production dashboard: `/opt/riverview-status-dashboard/current` resolves to release `98287c9a344f8ead203b55d50366b02014d9ce62`; dashboard service is active. `riverview-grace-execution.service` is not installed. No production activation is included here.
- Grace is `resident:grace`, occupant `occupant:grace:initial`, office binding `office:grace` revision 9, implementation `implementation:grace:readiness-router:608aa519346c` (`grace.readiness_router.v1`).
- Read-only comparison of all source checksums with the installed PostgreSQL migration ledger passed for the relevant authority migrations 0000–0006, assignment/event ledger, leases, event cursor, worker attempts/knowledge/verification/recovery/retry limit, Grace objectives/health/conversation/deferred responses/dashboard health read/deferred execution claims, CME monitoring and durable notifications. No new migration is required by this demonstration change. Authority migration 0008 and the proposed Level 4 permission profile are not required and remain unapplied.
- The root `riverview_core` service role and selected schema objects exist. A fresh backup/restore is a commissioning prerequisite; it has not been performed as part of this read-only preparation.

## Exact-grant and identity gate

All resources being available is separate from permission. The current live authority inspection showed:

| Principal | Required action and exact scope | Current evidence |
|---|---|---|
| Steward `steward:camrui` | `objective.submit` — `work-order:engineering` | Missing. Existing active conversation read/send grants are on `office:office:grace` only. |
| Bound Grace `resident:grace` | `office.state.write` — `office:office:grace` | Active. |
| Bound Grace `resident:grace` | `resident.conversation.send` — `office:office:grace` | Missing in the inspected grant rows; required for result return. |
| Configured dispatch principal from `dispatch-token` | `assignment.create` — `work-order:engineering` | No commissioned Grace dispatch credential/grant was found. Identify or create only through the approved AuthorityRegistry procedure. |
| Executor identity | `worker.register`, `assignment.execute` — `work-order:engineering` | `worker:grace-engineering` is absent. Existing M33 executor identities have separate scopes and must not be reused. |
| Verifier identity, distinct from executor | `worker.register`, `assignment.verify` — `work-order:engineering` | `verifier:grace-engineering` is absent. Existing M33 verifier identities have separate scopes and must not be reused. |

Do not issue these grants from SQL or infer them from Grace's title, a website checkbox, or provider readiness. Provision credentials and exact grants only through the existing Steward-authorized AuthorityRegistry procedure, then read back principal/action/scope/expiry/revocation metadata without displaying credential material. The current grant state is the concrete institutional blocker to a live work order.

## Commissioning checklist

### Source and release

- [ ] PR #34 and its dependency/base branch receive the repository-required review and all required CI checks.
- [ ] Review the owner-session diff and confirm the 512-token model correction, 0.6B fallback, active binding, source revisions and unrelated work are unchanged.
- [ ] Merge only when repository review policy is satisfied; build from the exact integrated immutable commit, not a branch name.
- [ ] Verify package manifest, source commit, archive SHA-256 and canonical package checker. Confirm `.riverview-backups/` is excluded.
- [ ] Stage the immutable dashboard and Grace execution release trees with root ownership and no group/world write access. Record the rollback release before switching symlinks.

### PostgreSQL and authority

- [ ] Take a fresh protected `riverview` database backup; verify its checksum and a disposable restore before any migration or service change.
- [ ] Read migration version/checksum ledgers and compare byte-for-byte SHA-256 against the selected release. Current relevant ledgers match source through AuthorityRegistry 0006 and the required `riverview_dev` worker/CME/resident execution migrations; abort on any unexpected or mismatched row.
- [ ] Do not apply authority 0007/0008 or any new migration for this demonstration. Migration 0008's resident profile system is unrelated.
- [ ] Reconfirm Grace occupant/binding revision, Steward identity, model implementation digest and exact active grants immediately before service start.
- [ ] Complete the exact-grant table above using the existing authorized provisioning flow, with expiry, grant IDs, and audit events recorded. Keep dispatch, executor and verifier credentials separate. Do not reuse M33-scoped identities.

### Service and Codex readiness

- [ ] Install the exact immutable Grace execution source release and the reviewed owner-session unit `riverview-grace-execution-owner-session.service`; do not replace or restart unrelated services.
- [ ] Install/pin the currently authenticated Codex CLI binary at `/opt/riverview-codex/bin/codex` outside `/home/admin1`; record its exact version and SHA-256. Only the binary is installed there; do not copy `~/.codex/auth.json`.
- [ ] Verify the existing ChatGPT login with `codex login status` as `admin1`. The unit reads the existing `~/.codex` path in place under `admin1`, with `ProtectHome=tmpfs` and only that directory bind-mounted read-only. No API key or Codex credential is passed in an environment variable. If the login expires, stop/fail closed and reauthenticate through the existing CLI before resuming.
- [ ] Confirm the unit's five protected systemd credentials: `pgpass`, `dispatch-token`, `worker-token`, `verifier-token`, `resident-token`; verify source ownership/mode and loaded-unit metadata without reading their contents.
- [ ] Run the read-only Codex workspace-sandbox preflight in the exact owner-session execution context. It must succeed before worker capability registration or assignment dispatch. Current Camrui evidence is NO-GO: both bubblewrap and unprivileged user-namespace probes return permission denied; the adapter now reports `codex_sandbox_unavailable` and does not dispatch work. Resolve only through an approved host sandbox configuration or a separately approved isolated executor; do not use unsandboxed/danger-full-access execution.
- [ ] Verify root-owned environment configuration pins the current full source revision, exact `work-order:engineering` scope, bound 80B router and approved 0.6B/30B/80B model identities/digests, local source clone and fixed workspace/artifact directories.
- [ ] Start the Grace unit only after all gates pass. Require a fresh `grace_execution_health` heartbeat; separate registered executor and verifier readiness; exact capability `engineering.codex-cli-artifact.v1`; no auth, grant, binding, migration or provider error.

### Acceptance work order

From the existing authenticated Steward website session, send this bounded objective:

> Create `deliverable.md` in the isolated, pinned Riverview repository worktree. Summarize the source-implemented Grace website → objective intake → 80B proposal → CME dispatch → Codex adapter → independent verifier → source-conversation return. Cite the exact source paths listed below and distinguish source implementation from production commissioning. Do not claim live facts, read credentials or conversation bodies, use network access, or modify files other than `deliverable.md`.

Then select **Create Engineering work order…** on that persisted Steward message and use these exact acceptance criteria:

- `# Grace Engineering Work Path`
- `src/riverview_core/status_dashboard/server.py`
- `src/riverview_core/resident_execution/service.py`
- `src/riverview_core/resident_execution/codex_cli.py`
- `src/riverview_core/resident_execution/codex_workflow.py`
- `source implementation is not production commissioning`

The output is one fixed Markdown artifact in the assignment-bound artifact store, produced by actual Codex CLI execution in a fresh clone at the recorded full commit. It is not an upstream branch commit. The independent verifier must persist `ACCEPTED`, path, digest and criteria evidence. The original Grace conversation must show the 80B-reviewed result after refresh with durable served-model provenance. A synthetic test or manually created file is not acceptance.

## Rollback and stop conditions

- On checksum, migration, binding, grant, package, startup, authorization, worker, verifier, or health failure, do not dispatch the objective. If activation already occurred, stop the owner-session and dashboard units changed by this commissioning, restore the prior immutable release pointer, and restart only the changed dashboard service under the approved rollback procedure.
- Restore an office implementation only through `AuthorityRegistry` compare-and-swap using the current binding revision and approved predecessor. Preserve occupant, authority events, migrations, objectives, assignments, leases, artifacts, retries, and pending outbox rows. Do not delete additive migrations or data.
- Leave the objective/assignment durable and non-complete for normal recovery; do not replay a terminal response or substitute another model/executor.
- After rollback, verify dashboard authentication, release identity, Grace binding revision, service health, and unchanged assignment/request metadata. Record sanitized evidence and exact resume condition.

## Evidence status

Source path: implemented. PostgreSQL-backed source integration: run against an isolated disposable PostgreSQL 16 cluster; all 361 tests passed with zero skips after creating the restricted `riverview_core` fixture role only in that disposable cluster. Persistent owner-session contract tests: added in this increment. A real bounded CLI invocation used the existing ChatGPT login without copying credentials or using API billing, but could not create an artifact because Camrui denies both bubblewrap and unprivileged user namespaces. The fail-closed sandbox preflight prevents dispatch under this condition. Production service/grants: absent or missing as listed. Real authenticated browser work order, Codex-created artifact, independent live verification, and Grace result return: **not yet demonstrated**.
