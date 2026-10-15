<!--
Riverview~ Controlled Document
File: docs/components/GRACE_ENGINEERING_DEMO_COMMISSIONING.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.7
Purpose: Prepare the first bounded authenticated Grace-to-Codex Engineering demonstration
Authority: Existing Steward grants, AuthorityRegistry, CME, worker, verifier, and conversation contracts
Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Record exact source, database, grant, worker, and rollback gates
Changed: 2026-10-15 UTC | RV-GRACE-CODEX-SANDBOX-READINESS-001 | Record the fail-closed host sandbox blocker and commissioning preflight
Changed: 2026-10-15 UTC | RV-GRACE-DEMO-BLOCKERS-001 | Record AppArmor cause, reviewed host-policy option, exact standing grants, and deployment stop gates
Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Record the successful per-executable sandbox trial, exact grants, and repeatable owner-session staging/rollback
Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Record full isolated PostgreSQL regression and unchanged production baseline
Changed: 2026-10-15 UTC | RV-GRACE-DEMO-PROVISIONER-001 | Record pushed PR head, successful CI, and pending human review gate
Changed: 2026-10-15 UTC | RV-AUTH-LEGACY-PROFILE-COMPAT | Record migration 0008 compatibility correction and current production-safe release gate
Changed: 2026-10-15 UTC | RV-GRACE-HEALTH-WRITER-ACL-001 | Record the restricted-role heartbeat ACL defect and controlled rollback
Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md; docs/components/GRACE_EXECUTION_PIPELINE.md
Tests: tests/test_codex_cli_adapter.py; tests/test_worker_service.py; PostgreSQL integration suite
History: Git and .riverview-backups/manifest.jsonl
-->

# Grace Engineering Demonstration Commissioning

**Current status (2026-10-15): NO-GO pending a corrected release.** The first authorized activation attempt was stopped before restarting the dashboard. The owner-session process loaded integrated source `b7ddfc7…`, preserved Grace's occupant and binding revision 9, and logged `InsufficientPrivilege` for both health writes and service cycles. Read-only ACL inspection showed `riverview_core` had SELECT but no INSERT/UPDATE on `riverview_dev.grace_execution_health`, and no SELECT access to `grace_objectives` or `grace_objective_events`, which the existing loop reads. The owner-session unit was stopped, and the dashboard and Grace release/configuration pointers were restored to their predecessors (`98287c9…` and `abfbaf9…`). The dashboard remained healthy. Additive migration `0007_grace_runtime_objective_and_health_acl` is being prepared with selected column grants and one sequence USAGE grant for those existing pipeline operations; it does not modify authority tables, migration ledgers, unrelated relations, or event history. Migration 0008 remains absent, Grace's binding/occupant are unchanged, and no dashboard restart occurred during the failed attempt. The migration must pass restricted-role PostgreSQL integration, full suite, graph validation and controlled revision audit, then be reviewed, integrated, packaged and staged. Take a fresh protected backup before applying 0007. Do not retry activation until those gates pass. Earlier commissioning notes remain historical and are superseded where they differ from this update.

The standard checksum-verified application command, after the corrected immutable Grace release is installed at `current` and a fresh backup is verified, is:

```sh
sudo -n -u postgres env PYTHONPATH=/opt/riverview-grace-execution/current/src \
  /opt/riverview-core/.venv/bin/python -c 'from riverview_core.postgres_migrations import apply_migrations; print(apply_migrations("dbname=riverview user=postgres", schema="riverview_dev", migrations_dir="/opt/riverview-grace-execution/current/src/riverview_core/resident_execution/migrations"))'
```

Expected result is exactly `['0007_grace_runtime_objective_and_health_acl']`; the runner also verifies every previously applied migration checksum and aborts on drift. Do not invoke the institutional-authority migration directory or apply the separate migration 0008.

## Legacy authority compatibility correction

The correction checks `pg_catalog` for the exact profile table and evaluator signature after the existing exact-grant function allows the request. With neither object installed, legacy exact grants remain effective. With both objects installed, the evaluator runs and can narrow the grant through active-profile status, explicit denials, expiration, revocation, and resource scope. One object without the other, unexpected database errors, malformed decisions, or visible migration-ledger disagreement/checksum drift produce an unavailable authorization result. The dashboard runtime is not granted access to the protected migration ledger. No migration, production authority record, or service was changed for this correction.

## Demonstration path

1. The authenticated Steward sends the bounded objective in Talk with Grace, then uses the message menu's **Create Engineering work order…** action and supplies acceptance criteria. The dashboard route persists the objective with conversation origin and requires `objective.submit` on `work-order:engineering`.
2. The persistent Grace service grounds the request, asks the currently bound 80B to formulate a typed proposal, and persists provider/model provenance. A proposal does not authorize execution.
3. The service dispatches only after `assignment.create` succeeds. Existing CME events and leases move the assignment to a registered executor. The Codex action checks the pinned local source revision, creates a fresh clone, allows one fixed `deliverable.md`, and exposes no command/path/model controls to Grace.
4. A distinct verifier reopens the artifact and checks assignment path, file type, mode, size, digest, source pin and literal acceptance criteria. Only persisted `ACCEPTED` verification completes the objective.
5. A durable idempotent outbox rechecks the current Grace binding and conversation-send grant, has the bound 80B evaluate the evidence, and appends one result to the original conversation.

## Current verified baseline

- Engineering checkout: `ppow1/Riverview-`, branch `codex/grace-deferred-80b-route`; current pushed source commit `1108f3cbcc7ff1e51746433c8c4dba15182a71ed`. PR #34 targets `codex/grace-conversation-ui-refinement`, remains open/non-draft and mergeable. Controlled-checkout CI run `38681197322` passed the full test, canonical graph, and controlled revision steps. GitHub has no review decision yet; PR #34 is not merged.
- The earlier package `/tmp/riverview-grace-demo-a4c955d.tar.gz` and SHA-256 `a1c1a5701cb73f44816e1021bb8f1b78dbecf3035aae414d040aed2049583625` apply only to predecessor commit `a4c955dc7062d1930d96166086f25afcffed4e85`; they are historical review evidence and do not package the current PR head. No immutable package has been built from `1108f3cb...` or an integrated merge commit.
- Production dashboard: `/opt/riverview-status-dashboard/current` resolves to release `98287c9a344f8ead203b55d50366b02014d9ce62`; the dashboard remains active. The owner-session execution unit is `LoadState=not-found`, and `/etc/riverview/grace-execution.env` is absent. The dedicated dispatch, executor, and verifier credential files now have root:root 0600 metadata; the existing resident credential is reused at its canonical protected location. No service activation is included.
- Grace is `resident:grace`, occupant `occupant:grace:initial`, office binding `office:grace` revision 9, implementation `implementation:grace:readiness-router:608aa519346c` (`grace.readiness_router.v1`).
- Read-only comparison of all source checksums with the installed PostgreSQL migration ledger passed for the relevant authority migrations 0000–0006, assignment/event ledger, leases, event cursor, worker attempts/knowledge/verification/recovery/retry limit, Grace objectives/health/conversation/deferred responses/dashboard health read/deferred execution claims, CME monitoring and durable notifications. No new migration is required by this demonstration change. Authority migration 0008 and the proposed Level 4 permission profile are not required and remain unapplied.
- The root `riverview_core` service role and selected schema objects exist. A fresh backup/restore is a commissioning prerequisite; it has not been performed as part of this read-only preparation.

## Exact-grant and identity gate

All resources being available is separate from permission. The current live authority inspection showed:

| Principal | Required action and exact scope | Current evidence |
|---|---|---|
| Steward `steward:camrui` | `objective.submit` — `work-order:engineering` | Provisioned through AuthorityRegistry; post-create authorization passed. |
| Bound Grace `resident:grace` | `office.state.write` — `office:office:grace` | Active. |
| Bound Grace `resident:grace` | `resident.conversation.send` — `office:office:grace` | Provisioned through AuthorityRegistry; post-create authorization passed. |
| Dispatch `service:grace-engineering-dispatch` | `assignment.create` — `work-order:engineering` | Dedicated service principal, credential, and grant provisioned. |
| Executor `worker:grace-engineering` | `worker.register`, `assignment.execute` — `work-order:engineering` | Dedicated worker principal, credential, and grants provisioned. |
| Verifier `verifier:grace-engineering` | `worker.register`, `assignment.verify` — `work-order:engineering` | Separate worker-kind principal, credential, and grants provisioned. |

Do not issue these grants from SQL or infer them from Grace's title, a website checkbox, or provider readiness. Provision credentials and exact grants only through the existing Steward-authorized AuthorityRegistry procedure, then read back principal/action/scope/expiry/revocation metadata without displaying credential material. The current grant state is the concrete institutional blocker to a live work order.

### Current scope semantics and minimum standing grant set

The live office identity is `office:grace`. Existing code treats this identifier as an opaque office ID and creates the typed grant scope by prefixing its namespace: `office:` + `office_id`. The exact office-scoped scope is therefore `office:office:grace`. This is the deployed contract, not a second office identity. The active `office.state.write` grant and all office-scoped conversation checks use that exact value. Do not normalize it to `office:grace` or create a parallel scope; any future migration must explicitly preserve old grant history and be independently reviewed.

The live Grace binding remains revision 9 with occupant `occupant:grace:initial`. Under the Steward's exact-scope authorization, `scripts/provision_grace_engineering_demo.py --apply` created only the missing identities, credentials, and seven exact grants through AuthorityRegistry. Post-create authorization checks passed. The procedure changed no binding, migration, dashboard, or service state. Existing M33 identities were not reused.

The minimum standing authority set for the already implemented website-to-Codex path is now provisioned:

| Identity | Exact action | Exact scope | Purpose |
|---|---|---|---|
| `steward:camrui` | `objective.submit` | `work-order:engineering` | Submit an objective through Grace's authenticated website. This is the Steward's initial requested objective, not an additional approval prompt for each later execution step. |
| Bound `resident:grace` | `office.state.write` | `office:office:grace` | Existing grant; required for office-bound operational reasoning state. |
| Bound `resident:grace` | `resident.conversation.send` | `office:office:grace` | Let the service return a completed, independently verified result to the originating conversation. |
| Dedicated dispatch principal used by `dispatch-token` | `assignment.create` | `work-order:engineering` | Dispatch eligible, grounded Grace proposals into the existing Engineering assignment/CME path. |
| Dedicated executor `worker:grace-engineering` (configured ID; principal kind `worker`) | `worker.register`, `assignment.execute` | `work-order:engineering` | Register and execute only the configured bounded Codex artifact capability. |
| Distinct verifier `verifier:grace-engineering` (configured ID; provision with principal kind `worker`) | `worker.register`, `assignment.verify` | `work-order:engineering` | Register and independently verify the assignment artifact. |

The dispatch identity is the configured `service:grace-engineering-dispatch`; executor and verifier are distinct and use separate bearer credentials. For Codex, the existing adapter is authorized through worker registration/capability plus `assignment.execute`; this source path has no additional `codex.execute` grant. The root-only state record at `/etc/riverview/worker/grace-engineering-demo.json` contains identity and grant references only, never bearer values. Grant audit events in AuthorityRegistry are authoritative. No unrestricted shell, filesystem, or database grant was issued.

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
- [x] Confirm the five protected systemd credentials: `pgpass`, `dispatch-token`, `worker-token`, `verifier-token`, `resident-token`; source ownership/mode verified without reading contents. Both the owner-session unit and one-shot runner now use existing canonical `/etc/riverview/grace/resident.credential` (the former `/etc/riverview/residents/grace-office.credential` source did not exist).
- [x] The per-executable `/usr/bin/bwrap` AppArmor trial and actual bounded Codex artifact run passed. The global unprivileged-userns restriction remains enabled. Direct `unshare -Ur /bin/true` remains denied; this is expected and not the worker sandbox check.
- [ ] Run `scripts/install_grace_owner_session.py --check` after the reviewed immutable execution release is staged at `/opt/riverview-grace-execution/current`; confirm it validates systemd and pins the package source commit into the rendered environment. The current immutable source release is not installed, so this preflight remains pending.
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

## Host sandbox trial result

Read-only Camrui evidence collected 2026-10-15 identifies AppArmor as the blocker: Ubuntu 24.04.3, AppArmor 4.0.1, `kernel.apparmor_restrict_unprivileged_userns=1`, `kernel.unprivileged_userns_clone=1`, and `user.max_user_namespaces=25945`. Both `unshare -Ur /bin/true` and the adapter's `bwrap --ro-bind / / --proc /proc --dev /dev /bin/true` fail with `Operation not permitted` / `setting up uid map: Permission denied`. Kernel audit records show transitions from `unconfined` to `unprivileged_userns` for `/usr/bin/bwrap`, followed by denials for `setpcap`, `sys_admin`, and writes to `/proc/<pid>/uid_map`. No local `/etc/apparmor.d` profile for `/usr/bin/bwrap` was found. This explains the error; it is not evidence that Codex authentication or Riverview grants failed.

The narrow Ubuntu-supported policy pattern is a per-executable AppArmor profile at `/etc/apparmor.d/bwrap`:

```text
abi <abi/4.0>,
include <tunables/global>

profile bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,

  # Site-specific additions and overrides.
  include if exists <local/bwrap>
}
```

This leaves `kernel.apparmor_restrict_unprivileged_userns=1` enabled. The profile grants the `userns` transition to invocations of `/usr/bin/bwrap`, so its allowance applies host-wide to that executable. Bubblewrap's requested sandbox remains mandatory and Codex remains fail-closed if setup fails. The previous AppArmor state was preserved in `/var/backups/riverview-apparmor-bwrap-20261015T0402Z/`; profile syntax validation, load, and the adapter bwrap probe passed. Direct `unshare -Ur /bin/true` remains denied, as expected. The bounded ChatGPT-authenticated Codex call produced one actual `deliverable.md` in a disposable workspace (91 bytes; SHA-256 `aa43782663dfae3c1f74033961e1116e382ef4ee08f8c7f003af2154faf207a4`). No API key was used or copied. This does not count as a Grace assignment.

Rollback if the host trial conflicts with policy: restore the protected `unprivileged_userns` predecessor, remove the newly added `/etc/apparmor.d/bwrap`, reload AppArmor policy, and verify the sysctl remains `1`. The root-only backup contains the original policy file and prestate. No global AppArmor or namespace setting changed.

## Exact deployment sequence and no-go gates

The current PR head is source for review, not an activation artifact. When the PR has its required review and CI, build from the exact integrated commit, verify its archive SHA-256 and canonical package manifest, and stage it into a new root-owned immutable release path. Before production work, record `readlink -f /opt/riverview-status-dashboard/current`, dashboard unit checksum, Grace occupant/binding revision, migration checksums and required service states. Take a new protected full database dump under a new PostgreSQL-owned directory, record its SHA-256, validate `pg_restore --list`, restore to a unique disposable database, and compare migration/assignment/event counts using the commands in `docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md`. Do not restore over `riverview`.

The repeatable provisioning and staging procedures are `scripts/provision_grace_engineering_demo.py` and `scripts/install_grace_owner_session.py`. The grant procedure has been run under the explicitly authorized standing-grant scope. The installer has not been applied because the reviewed immutable execution release is not staged; it fails closed if unit or environment destinations already exist. It never enables or starts the unit. To validate after the merged release is staged, run `sudo /opt/riverview-grace-execution/current/scripts/install_grace_owner_session.py --check`; to stage, use `--apply`, record both returned hashes, and install no unrelated service. Roll back only with `--rollback <UNIT_SHA256> <ENV_SHA256>` using those recorded hashes.

Before the later, separately authorized service activation: require the merged immutable release, completed backup/restore check, the five protected credential sources, valid ChatGPT login, passing bwrap and Codex preflight, expected router/digests, and unchanged Grace occupant/binding. Stage only the owner-session unit and environment; inspect systemd metadata without printing credential values. Start only that unit after all these gates, then require a fresh health heartbeat and separate executor/verifier registrations. The dashboard and its recovery-token access are not changed in this procedure.

Stop before any production identity, grant, credential, database, service, or host-policy mutation if the corresponding Steward authorization is absent. On post-activation failure, follow `docs/components/STATUS_DASHBOARD_COOKBOOK.md` and `docs/components/GRACE_EXECUTION_COOKBOOK.md`: stop only units changed by the commissioning, restore the prior immutable release pointer and unit if changed, restart only the exact changed dashboard unit if it was restarted, and leave additive data, leases and nonterminal requests intact. Re-read the active binding through AuthorityRegistry; restore a binding only with a fresh compare-and-swap transition and approved predecessor. Never roll back by deleting records or direct SQL edits.

Ubuntu documents the per-application `userns` AppArmor profile pattern and warns that disabling the restriction globally weakens kernel attack-surface protection: [Ubuntu 24.04 release notes](https://documentation.ubuntu.com/release-notes/24.04/).

## Rollback and stop conditions

- On checksum, migration, binding, grant, package, startup, authorization, worker, verifier, or health failure, do not dispatch the objective. If activation already occurred, stop the owner-session and dashboard units changed by this commissioning, restore the prior immutable release pointer, and restart only the changed dashboard service under the approved rollback procedure.
- Restore an office implementation only through `AuthorityRegistry` compare-and-swap using the current binding revision and approved predecessor. Preserve occupant, authority events, migrations, objectives, assignments, leases, artifacts, retries, and pending outbox rows. Do not delete additive migrations or data.
- Leave the objective/assignment durable and non-complete for normal recovery; do not replay a terminal response or substitute another model/executor.
- After rollback, verify dashboard authentication, release identity, Grace binding revision, service health, and unchanged assignment/request metadata. Record sanitized evidence and exact resume condition.

## Evidence status

The owner-session unit, fixed exact-grant provisioner, and reversible staging installer are source-implemented. Focused tests pass 8/8. Full regression: **369 passed, zero failures, zero skips** against a temporary isolated PostgreSQL 16 cluster using system Python test dependencies and the restricted runtime-role fixture; the cluster and role were confined to that test environment and cleanup completed. `py_compile`, `systemd-analyze verify`, `bash -n`, canonical graph validation/check (19 workflows/440 nodes), controlled revision audit, and `git diff --check` pass. The authorized per-executable AppArmor trial and one actual bounded Codex CLI artifact task in a disposable workspace passed. All seven authorized standing grants and dedicated runtime credentials were provisioned through AuthorityRegistry; a repeat provisioning run returned all seven as existing. Live recheck confirms dashboard release `98287c9a344f8ead203b55d50366b02014d9ce62`, Grace binding revision 9, and occupant `occupant:grace:initial` unchanged. The Grace service/environment remain uninstalled and inactive; no assignment or worker capability has been registered. Authenticated website intake → actual Codex work order execution → distinct live verification → Grace result return remains **not yet demonstrated**. PR #34 is unmerged; no dashboard or Grace service was deployed.
