<!-- Controlled document revision 1.0.1 | 2026-10-29 EDT -->
# Grace lossless plan-cache capacity correction

Status: INSTALLED; current pointer and both exact runtime hashes independently verified through Comms/Camrui at approximately12:17EDT2026-10-29. Fresh-request capacity/delivery acceptance remains pending. This is the next action after the installed and verified db-state-boundary-r1 correction. Do not repeat the earlier installers.

## Why this change
The attempted proposal state contained 25 plan entries occupying 62,844 compact bytes; total compact state 64,450, Python spaced estimate 66,922, and PostgreSQL JSONB text exceeded 65,536. These describe the attempted write, including its new plan, not a separate persisted-state read. The installed size classifier now records the deterministic failure and suppresses same-revision retries. The original delivery objective remains GROUNDED rev2/no assignment; last attempt10:50:41EDT, last failure10:51:04EDT, no subsequent attempts observed through later Comms checks.

The sole office-state plan reader is ResidentReasoner.propose(), which passes prior_plan into provider/reasoning requests. Canonical objective proposals are stored later and cannot replace that context without changing replay semantics. The candidate keeps the current plan in legacy plans, archives all other entries in versioned deterministic zlib/base64 canonical JSON with SHA256, and merges archive plus legacy on read. Legacy values win same-assignment overlaps after rollback updates; all other entries survive.

Physical office-state limit remains65,536bytes. Encoded archive limit65,536characters; complete decoded plan map limit262,144bytes. Invalid streams, digest mismatch, nesting errors and over-bound maps return a fixed archive-invalid result without invoking the provider or writing state, and use the existing revision fence. Encoding checks the same merged bound as decoding before any write. There is no unbounded decompression flush.

## Historical operator command (already installed; do not rerun)
Run in the existing desktop-ja3rpnq\wille PowerShell session:
~~~powershell
& "C:\Users\Public\Documents\Riverview\GracePlanCache\Update-RiverviewGracePlanCache.ps1"
~~~
The staged launcher clears the display, checks Wille identity, verifies the helper hash through existing ssh.exe -n -T -o BatchMode=yes camrui, dry-runs, applies only on success, displays and copies the report. No new key or grant. Launcher SHA25667b6c9866f842457f9b3d98c8ab3008d2724a54a8fc86d81a1e80750a4e4133c; native parser0errors.
Staging execution7b5ca667-88f8-4541-833b-0257a539b87b; audit24b1cf18-79bc-4e05-a953-92a6f03ae611; commandSHA256dc064ec82965c468a175c20c2c77451cbca9c4e1399a7e59370fe5e2b4fc47b8.

Helper /home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-lossless-plan-cache-20261029/owner-release-update-lossless-plan-cache.sh, revision1.0.1, SHA25649de4332235f82fc60de302714a60216a9eb160212690f4c76dc1b2853163d65.
Predecessor owner release suffix grace-db-state-boundary-20261029-r1; candidate suffix grace-lossless-plan-cache-20261029-r2, both under /opt/riverview-grace-execution/releases/9f56cb72f3bd2961babf2527a26bd843526e18ce-.
Only two runtime files are overlaid:
- resident_reasoning.py1.0.36: aa8fbd39c18d413ff814d89cb63cbdcbe8680b92bdc42d637f166e1f025cd56c.
- resident_execution/service.py1.0.66: 73b5085d53645b1e9be20a12590e02071c0cc3fe75c51cbdf00dcf18045ad2be.

The helper retains exact predecessor/unit/drop-in/helper hashes, clone/tree equivalence, stable idle cgroup checks, atomic current pointer, owner-only restart/startup health and rollback. Dashboard/Comms/source-worker mapping/grants/credentials are unchanged. Modes --dry-run/--apply/--rollback; mutation uses existing Wille sudo authority.

## Validation and limits
Final focused tests:14archive +8Grace failure-diagnostic =22passed,0skipped,0failed. Tests cover replay of archived prior plans, old raw format, exact deterministic round trip, append/update, legacy overlap after rollback, merged-bound rejection before registry write, corruption/digest/bomb/recursion failures and persisted archive-invalid fence. Helper bash syntax and candidate in-memory compile passed; patch dry-run recorded. No PostgreSQL integration or live capacity acceptance yet.
A deliberately repetitive 25-plan synthetic fixture of62,844plan bytes resulted in4,278compact state bytes (4,335Python spaced estimate). This is not a measurement or promise for Grace's actual values; Python spacing is not PostgreSQL JSONB text semantics. Compression is bounded capacity relief, not infinite storage. Poor compression or eventual bounds still fail explicitly.

Rollback restores the exact prior owner release. Older code preserves the opaque archive field and current legacy plan while writing; it cannot use archived entries as prior-plan prompt context. Returning to the new runtime merges those entries and any legacy updates. No archive/state removal is part of rollback.

Root reviewed the original patch and incremental correction as one series, verified complete gzip/raw JSON transfer hashes, reconstructed the helper from the reviewed predecessor/diff, and verified its complete SHA256. See patches/grace_plan_cache_20261029/README.md for patch order, digests and test predecessor caveat. The uncorrected first patch is not accepted alone.

## After application
Independently verify current pointer and two runtime hashes through Comms1.1. Preserve the old objective and failure history; do not silently bypass its revision fence.
After installation verification, prefer a fresh bounded work-order request from the authenticated original Grace conversation's existing message menu. The old exact recovery route exists at POST /api/v1/grace-recovery/{request_uuid}/decision with Steward session/CSRF, but only an eligible pending one-shot request can be approved; none was approved here.
Fresh acceptance: create reports/grace_delivery_20261029.txt with exactly GRACE-DELIVERY-20261029, independently verify it, and automatically report completion in the same conversation. Require real plan persistence, worker dispatch, verifier ACCEPTED, canonical COMPLETED, conversation.result_published and visible assistant completion. Discover the new objective through recent_steward_submissions rather than asking Pat to locate IDs.
No live acceptance or full autonomy completion has been claimed. If live persistence remains too large, use safe metrics and actual failure codes; do not discard history or invent completion.

## Installed verification
A repeated invocation returned dry-run2/current_pointer_mismatch. Independent inspection executionc6852b84-4b6a-462b-b69d-4e711de2786e and result executionec094cb5-b9d4-4401-ba99-e8cf0058bdfb (audita0915424-94cc-4fa4-a743-61559ad9f0bd) found current already resolves to the reviewed lossless-plan-cache-r2 release; reasoningaa8fbd39...5cd56c/service73b5085d...5ad2be match. The dry-run expects db-state-boundary-r1, so the repeated block is explained by already-current candidate, not unknown drift. Nothing was changed by that repeated invocation. Prior successful apply receipt/time was not supplied. Do not reinstall or loosen predecessor checks. Proceed to the fresh conversation acceptance above; no new objective was visible in recent submissions at inspection time.
