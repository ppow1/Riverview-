<!-- Controlled document revision 1.0.1 | 2026-10-29 EDT -->
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

## One operator command
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
