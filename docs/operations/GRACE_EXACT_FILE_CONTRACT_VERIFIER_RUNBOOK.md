# Grace exact file contract verifier
Revision: 1.0.1. 2026-10-29 EDT. Continuation of PR #369.

## Problem and resulting behavior
Objective objective:grace-conversation:64e77b71-7ddf-5f12-8029-64464f2c7fc9 formed and dispatched s1 successfully. Its worker produced the exact23-byte GRACE-DELIVERY-20261029 artifact. Verifier1.0.5 rejected its three persisted file-existence, exact-content, and UTF-8 clauses as unsupported. Protected diagnostic completed successfully; do not repeat it.

The correction adds only these deterministic clause forms. Existence requires the persisted artifact path. Exact content requires byte equality to the literal UTF-8 encoding, without trimming or substring matching. UTF-8 requires strict decoding. Step checks bind to artifact requirements declaring the same clause; unknown prose remains unsupported. Existing provenance, integrity, publication and generic literal checks are retained. Verifier revision becomes1.0.6.

## Deployment state
INSTALLED. Operator dry-run0/apply0 UPDATED; independently verified through Comms5. Predecessor was9f56cb72f3bd2961babf2527a26bd843526e18ce-grace-artifact-formation-20261029-r2.
Candidate is9f56cb72f3bd2961babf2527a26bd843526e18ce-grace-exact-file-contract-20261029-r1.

Only src/riverview_core/resident_execution/codex_workflow.py is overlaid:
- predecessor1.2.25 SHA25662aa0b6316d6f5d97d749d5bacedf2ec28f2793efa70f62a93b42ed5fd377d09
- candidate1.2.26 SHA2566c5c87e5031727de4d72455f9f8ac6d315bf73278510bb029c2429fdfbbb5571
- reviewed patch SHA25642bb36e229955ad97865370fb45796cd04aabae40bd63cb8e1f51b418dbeee49
- helper SHA256bbf55301ecee441ba192315cf98f827e14adf0cf5e49e1ef117ce0f9f4d8b8fd

Provider1.3.34, reasoner1.0.36, service1.0.66, verifier.py, source-worker mapping and grants remain unchanged. No persistent data/schema changes.

## Operator command
In existing desktop-ja3rpnq\\wille PowerShell:
```powershell
& "C:\Users\Public\Documents\Riverview\GraceExactFileContract\Update-RiverviewGraceExactFileContract.ps1"
```
Launcher staged through Comms execution2d09837d-5632-48d5-a309-b2c7252285d2, parser errors0, SHA2561eed2e1e4bdcd067b7c865b5b61eff6847010eb0541e48ecbb9e7b15ff3b9068. It clears terminal, verifies operator identity/helper hash, runs dry-run then apply only on success, displays report and copies clipboard.

This operator step uses the established Wille SSH/sudo path because the bounded Gateway Codex identity cannot switch protected service releases. No new grant or SSH identity is required.

Helper stage: /home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-artifact-exact-verifier-20261029/owner-release-update-exact-file-contract.sh
It verifies exact pointer, unit/drop-ins, predecessor/candidate hashes, and idle owner before switching. It clones the current release, overlays only codex_workflow.py, verifies all other files unchanged, then restarts only riverview-grace-execution-owner-session.service and checks startup health. Existing rollback behavior is retained. Manual --rollback restores the predecessor using the same helper and identity; preserve objective/session history.

If current_pointer_mismatch: inspect actual pointer and source hash first; the update may already be installed. Do not bypass pins or repeatedly rerun.

## Validation
Adapter/verifier baseline34passed; candidate35passed. Added acceptance fixture covers the exact observed three clauses, newline, space, substring, non-UTF8, wrong path, unknown prose, and unrelated-artifact binding. Source diff whitespace, in-memory parse, shell syntax pass. PostgreSQL-dependent revision-revalidation test skipped because RIVERVIEW_TEST_PG_DSN was not configured.

Supplemental source-change suite: baseline and candidate each8passed,3failed,1errored. Exact isolated predecessor comparison executiond49908c4-69c3-420e-89a8-cce31995d8c2. Same failing names:
- test_fixed_pytest_target_runs_in_offline_bubblewrap_sandbox
- test_offline_test_runner_accepts_explicit_system_python_and_rejects_relative_path
- test_failed_pytest_diagnostics_are_bounded_redacted_and_actionable (error)
- test_pinned_pr62_two_step_patch_chain_is_independently_replayed

Observed sandbox interpreter ownership check leads to bare-False return/unpacking error; PR62 preflight reports UNAVAILABLE. These failures are baseline-proven, not fixed here. This does not constitute a live source-worker regression test.

## Continuation
After UPDATED, independently inspect actual owner pointer and codex_workflow.py hash through exact Camrui thread01a17fdf-6d58-7050-92cc-1762ac986518. Query canonical objective/assignment status. Determine whether existing canonical verifier-revalidation/rework path picks up the new verifier revision; do not manually overwrite an old verification or forge completion. If fresh intake is necessary, use a new user message and existing Work Order action, not the old idempotent message.

Success still requires independent canonical ACCEPTED, objective completion, and automatic conversation.result_published. Installer success alone does not meet it. Current old assignment remains rework_required until verified otherwise.

## Source and audit
Implementation execution197b734d-9841-442b-8183-51657d512250; source review bundle gzipSHAa089d16659f12d7ce7524f74c82e0fa7cbe60d3e136213ef1e0b391222afb07b and rawJSONSHAe5d1e2cb366b819e44f657bdf66d718447e9aa878ba1ef7586cf059f0f63a1e3 independently validated. Exact patch/helper hashes verified by ROOT, helper reconstructed from reviewed formation predecessor. GitHub patch and helper are recovery/review artifacts; this PR remains unmerged and is not evidence of deployment.

## Installation verification and next intake
Operator reported helperbbf553... dry-run0/apply0 UPDATED. Independent Comms inspection execution5a99eacd-86ba-4813-9f27-b3c6c246c755, exact-session run grace-exact-verifier-installed-inspect-20261029-01, status receipt f64f6956-7e18-448e-9111-a2fb7ccbb4d6 confirmed current resolves to exact-file-contract-20261029-r1, codex_workflow.py SHA6c5c87e5031727de4d72455f9f8ac6d315bf73278510bb029c2429fdfbbb5571 and CodexArtifactVerifier.REVISION1.0.6. Other pinned provider/reasoner/service hashes match. Do not rerun installer.

Canonical existing objective64e77b71... remains WORK_ORDER_CREATED; assignment rework_required, latest verification1.0.5 REJECTED. No new dispatch or completion. Revalidation code service.py requires engineering.rejection_reviewed with OBJECTIVE_SATISFIED matching exact attempt/rejection before it can reverify an artifact; version change alone does not override the review gate. Comms exposes no corresponding rejection-review command, and reasoning exchange list returned no routed requests.

Next fastest acceptance is fresh intake through existing authenticated Grace conversation: NEW user message, Send, then that message's Create Work Order action. Use the same requested report/token. Do not click old message again (idempotent old objective), forge review events, bypass planning with direct Engineering submission, or change grants. Current Comms interface cannot submit conversation messages/work orders, so this intake step uses the user's existing browser. Once submitted, discover objective via recent_steward_submissions and monitor canonical lifecycle autonomously. Completion still unverified.
