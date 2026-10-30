<!-- Controlled document revision 1.0.5 | 2026-10-29 EDT -->
# Grace delivery planning: state sizing and retry correction

## Observed failure
The user successfully submitted objective:grace-conversation:db6e6c9a-5902-5084-af92-5876c2d04993 through the original conversation. It is GROUNDED revision2 with valid objective.submit authority and no assignment. Do not resubmit it.
Readable sanitized owner journal entries show repeated PlanProposal results followed by OFFICE_STATE_SIZE_LIMIT at66922bytes against65536. The old precheck counts spaced JSON while AuthorityRegistry writes compact sorted JSON. The failure request ID is stable, so only the first failure event persists while attempt events keep accumulating. This is not evidence of a missing execution grant.
Live canonical byte count and bucket composition are not yet observed. The correction may remove a false size failure; it does not claim to create capacity when compact state actually exceeds the cap.

## Reviewed correction
The final candidate matches the registry's canonical JSON size calculation. It preserves all plan-cache entries and the existing outcome retention policy; no cap increase, state wipe, history eviction or fabricated completion. If persistence still cannot succeed, the service records a revision-bound terminal fence. That fence uses a separate stable objective/revision/code event key, preserving an older request-key failure and remaining idempotent after replay/restart.
Only resident_reasoning.py and resident_execution/service.py are overlaid. Current pipeline/publication guard, Dashboard, Comms5, source-worker9f56 mapping, grants and SSH remain unchanged.
Patch SHA2565390089e56ea062d64939d2786f28d93ed3a974055d24449bb4794bb185d14a0. Runtime candidates: reasoning866d6c9a222bad3bb0a320145c526690b934bc6bc58afb6638c510d474bd43c4; servicef5d9cc2543622147d0771935480b7b849038f7c2da570f299f87516b3b36f5c4.
The patch includes isolated regression/test adjustments; runtime hunks use exact current immutable predecessors. Test hunks use the retained Engineering test checkout, as identified in the original report. It is a reviewed candidate artifact, not a deployed source release or another source-worker acceptance.

## Tests and review
33 tests ran:15passed,18skipped,0failed. Skips require RIVERVIEW_TEST_PG_DSN, unavailable. Passed:3 existing offline resident tests,3 new canonical-size/retention/replay cases,1 legacy-event collision/fence reconstruction regression,8 existing Grace diagnostic cases.
The earlier eviction candidate was rejected and is not part of the final change.
Root retrieved bytes and verified full gzip and raw-export SHA256, then reviewed the patch/helper. A transmitted base64 typo was corrected against published per-chunk digest and confirmed by the complete gzip and JSON digests. No source bytes were substituted.
Helper review caught a duplicated staging-path segment; revision1.0.1 corrects it. Camrui verified both actual staged paths/hashes and bash syntax. Read-only dry-run reached the idle/systemd boundary and stopped with systemd_bus_unavailable; no protected write or restart. Original report helper1.0.0 and its hypothetical /home/admin1 entry are historical; use only the exact entry below.

## Post-install database boundary finding
Read-only retained-session inspection at10:29:41.959EDT found proposal_state_persistence failing with OFFICE_STATE_STORE_UNAVAILABLE, ValueError/InvalidParameterValue SQLSTATE22023. The database function in institutional_authority/migrations/0003_resident_office_state_api.sql checks octet_length(p_state::text) on JSONB against65536. Compact Python JSON and PostgreSQL JSONB text are not equivalent representations. Thus matching the registry client serialization did not establish agreement with the database guard.
The generic exception branch maps this database rejection to OFFICE_STATE_STORE_UNAVAILABLE, which is absent from the terminal fence set. That explains continuing reasoning attempts. The earlier66922bytes is historical spaced-Python sizing, not a current database byte count. Current failure diagnostics lack the required bucket counts. Do not classify every22023 as a size failure or fence transient database outages.
Successor preparation is running in the retained Camrui thread, run grace-db-state-boundary-fix-20261029-01, executioncc98c712-fadf-4ed9-ba10-9e4980230872. Scope: distinguish only a proven size rejection, emit value-free metrics and persist the existing revision fence, with regression tests. No installation, schema/cap change or cache eviction has occurred. Exact results must be reviewed before an operator update command is issued.

## Historical operator command (already applied)
In the established desktop-ja3rpnq\wille PowerShell session:

~~~powershell
& "C:\Users\Public\Documents\Riverview\GraceReasoningState\Update-RiverviewGraceReasoningState.ps1"
~~~

Already staged; native parser0errors. Launcher SHA2564786636160b05905d2ebcbfe10d5735a1ce372f1b4eb25ce1942c2ec9ca6227a.
It clears the display, checks identity, uses existing ssh.exe -n -T camrui with BatchMode and sudo-n, checks helper SHA256636ba2453061c8522f5caededac9935ccf870b1896cea67a827c4719ecc246bf, runs dry-run, applies only on success, then displays/copies the report.
Exact Camrui helper:
/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-delivery-planning-failure-20261028/owner-release-update-reasoning-state.sh
Modes: --dry-run, --apply, --rollback. Root required for mutation.
The existing release procedure clones publication-fence-r1, overlays only the2files, checks exact unit/drop-in/helper/source hashes and whole-tree equivalence, checks stable sole-MainPID cgroup before staging/switch, atomically switches the owner pointer and restarts only the owner unit. It checks startup and restores the predecessor on candidate health failure. Rollback accepts stopped/failed units without requiring candidate health. Candidate path suffix:grace-canonical-state-20261029-r1. Previous release remains intact.

## Continuation
Status: INSTALLED; delivery acceptance remains incomplete. Operator apply returned UPDATED/exit0. Subsequent read-only operator SSH confirmed the current pointer and both exact candidate hashes above. Do not rerun the installer. Existing Codex thread01a17fdf-6d58-7050-92cc-1762ac986518.
After installation, Comms objective and command operations returned BACKEND_UNAVAILABLE/dashboard_operation_http_status while CME status and grant reads worked. PostgreSQL readiness, disk and inode checks were healthy; Dashboard deferred-resume logged OperationalError. Restarting only riverview-status-dashboard.service restored objective reads and independent Camrui command execution (execution4830ff50-dd6b-423d-8755-3ed15d0cfa97; auditf7cb47a8-193e-4501-bee7-f8cbbd09bd6f), without changing grants. This establishes recovery, not the exact original connection fault. The SAME objective remains GROUNDED revision2 with no assignment and repeated reasoning attempts through10:29EDT. The exact retained Codex session is inspecting current owner diagnostics under execution242f6589-ceac-4bb7-abbe-85b80405ba28. Query the SAME delivery objective after identifying that failure. If it advances, require independent artifact acceptance, canonical completion, conversation.result_published and an automatic message visible in the original chat. If it remains blocked, inspect new fixed-field size metrics; no prompt/state bodies are logged. Do not increase limits or evict plans without the actual breakdown and an appropriate reviewed change. Preserve original objective and failure history. Delivery success remains unverified.

## Reviewed successor ready for operator application
Status: PREPARED AND TESTED, NOT APPLIED. Supersedes the preparation-in-progress note above. Use the already-staged entry in the existing desktop-ja3rpnq\\wille PowerShell session:

~~~powershell
& "C:\Users\Public\Documents\Riverview\GraceDbStateBoundary\Update-RiverviewGraceDbStateBoundary.ps1"
~~~

Launcher SHA25658d735c127343159ecd24924ee2c3f6410fdeec2ca89412911a9556a648daabe; native parser0errors; staging executionc3e3984b-5fef-45f8-adb1-11b2020ddf14, audit045b6ebe-5925-4a4a-8620-74ff14dd656f.
Camrui helper: /home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-db-state-boundary-20261029/owner-release-update-db-state-boundary.sh; SHA25649364dc585ff8baf4af24337f95a68e96b370c26fb7a1ec47658bb6ce6d5af30.
The entry verifies helper hash, dry-runs and applies only on success using existing Wille SSH/sudo. It clones exact canonical-state-r1 and overlays only reasoning1.0.34 (1e4999abeeca03d4015d3516f41b911107d13ccf7275f0113586e5a55aff359c) and service1.0.65 (dd4091bbe4478d398c6717bf4f4fdd2ad4c1e97bf0cdbf07734f83c1658776c0). Candidate suffix grace-db-state-boundary-20261029-r1. Existing idle/startup/rollback checks retained; --rollback restores canonical-state-r1.
Classifier requires the exact underlying InvalidParameterValue, SQLSTATE22023, checked-in fixed guard message, and valid remaining input shapes. Other22023 and transient errors remain unavailable. It emits value-free component sizes and returns OFFICE_STATE_SIZE_LIMIT for the separate objective/revision fence. No cap/schema/state/cache change. This makes failure handling correct; it does not solve capacity or complete delivery.
95distinct relevant-module tests:19passed,76DB-backed skipped,0failed. Focused8passed are a subset, not8additional. Test DSN unavailable; live database function body/version and exact JSONB byte count remain unverified. Current signature mismatch fails closed as unavailable. Patch c66537594cccc6b1898ded1a4865e579d6d22b98d0e1246057e58cc0ef004474, helper syntax and patch dry-run passed. Full transferred gzip/JSON hashes verified after re-fetching corrupted chunk12; root reviewed runtime hunks, tests and helper diff.
After UPDATED: verify exact pointer/hashes through Comms, inspect SAME objective for revision-bound size failure and no continued attempts, retrieve safe size metrics, then prepare the actual capacity remedy from evidence. Require artifact acceptance and automatic conversation delivery before reporting the mission complete. Preserve all lineage. Source patch/helper/launcher/report/root-review are committed with this PR.

## Verified successor installation and next capacity milestone
2026-10-29: operator applied helper49364dc5...d5af30 with dry-run0/apply0/UPDATED. Independent Comms/Camrui inspection confirms exact db-state-boundary-r1 pointer and both reviewed hashes1e4999ab...aff359c/dd4091bb...58776c0. No new reasoning attempts returned after10:50:41EDT; the new size failure was recorded10:51:04EDT, with subsequent objective read around11:05EDT. Retry suppression is observed; delivery remains GROUNDEDrev2/noassignment, not complete.
Latest diagnostic OFFICE_STATE_JSONB_TEXT_SIZE_LIMIT at10:51:04.109383EDT: compact64450bytes, Python spaced estimate66922bytes, DB text bucket over65536 (exact DB size unavailable); plans25/62844bytes, outcomes1/1558bytes, other office2bytes, reasoning runtime64424bytes. All are value-free counts/bytes. The 25-plan cache is the dominant capacity bottleneck.
Do not rerun either installer. Next preparation run grace-lossless-plan-cache-20261029-01 (executioncb45d710-2c36-4840-9843-f043ac6ccb3b) evaluates reuse of canonical plan storage or a bounded lossless archive with legacy replay/rollback compatibility. No state eviction, physical cap increase, schema/grant change or silent revision-fence bypass. Inspect actual institutional recovery route before resuming this objective; a fresh governed objective may be preferable if existing recovery is unsuitable. Candidate is not yet reviewed or deployed. Require independent artifact acceptance and automatic conversation delivery for final success.

## Current continuation pointer
The lossless capacity candidate has now been reviewed, corrected and tested (22focusedpassed/0skipped/0failed), and its Windows launcher is staged and parser/hash verified. It is NOT APPLIED. Continue from [GRACE_LOSSLESS_PLAN_CACHE_RUNBOOK.md](GRACE_LOSSLESS_PLAN_CACHE_RUNBOOK.md), which supersedes the earlier preparation-in-progress notes. Exact command in Wille PowerShell: `& "C:\Users\Public\Documents\Riverview\GracePlanCache\Update-RiverviewGracePlanCache.ps1"`. After independent installation verification, use a fresh bounded conversation workorder; preserve the old objective/fence. No capacity acceptance or automatic delivery success yet.
