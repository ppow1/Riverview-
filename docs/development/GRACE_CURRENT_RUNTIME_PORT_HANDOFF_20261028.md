<!-- Controlled document revision 1.0.1 | 2026-10-28 -->
# Grace current-runtime port handoff — 2026-10-28

## Exact source and staged delta

The captured predecessors are Comms5 release `b6b5ce715508590cc8e56051c00bf7ed17fdbf79` and Dashboard release `8325d3ffe8e53f3deaab4c9e14e471467454a08b`. Exact baseline copies remain under `.riverview-write-acceptance/grace-current-source-8325d3-stage/baseline`; only these four candidate runtime files differ:

- Comms5 `src/riverview_core/comms5/dashboard_backend.py` rev 1.2.4 and `src/riverview_core/comms5/tool_catalog.json` (cancellation tool catalog entry).
- Dashboard-loaded `src/riverview_core/resident_execution/comms5_operations.py` rev 1.1.2 and `pipeline.py` rev 1.1.46.

The staged implementation routes cancellation through authenticated Steward ingress and existing exact `assignment.cancel` principal authorization, retaining lifecycle audit/idempotency. Objective status adds only allowlisted verifier summaries, boolean criterion statuses, and sanitized artifact references. The persisted advisory payload remains unavailable; `cme_advisory_fields_invalid` is not attributed to any specific field and no CME change was made.

## Verification

The prior focused runtime set remains 10 tests passing (exit 0); it was not rerun. The new operator script passed `bash -n` and four offline guard tests (exit 0): clean pointer/hash preflight with no writes, pointer mismatch denial, predecessor hash mismatch denial, and fixture-root refusal for both write modes. The script's fixture override is accepted only for `--dry-run`.

## Operator entry and limits

One entry point is [`scripts/grace_current_controls_20261028.sh`](../../scripts/grace_current_controls_20261028.sh). Exact commands:

```sh
bash scripts/grace_current_controls_20261028.sh --dry-run
bash scripts/grace_current_controls_20261028.sh --apply
bash scripts/grace_current_controls_20261028.sh --rollback
```

Default mode is the read-only dry run. `--apply` requires root, rechecks exact predecessor pointers and hashes, copies each immutable predecessor release, replaces only the four files above, verifies candidate hashes and in-memory static compilation, atomically switches both existing `current` links, restarts only Comms5 and Dashboard, then uses bounded polling for Comms5 `/healthz`, both unit states, and Dashboard's protected status route without reading credentials (expects 401/403). Any apply failure after pointer activation restores both predecessor pointers and restarts those same units. `--rollback` does the same explicit restoration. No command was run against service paths; this environment must not perform protected release writes.

`PORT_MANIFEST.json` records all old/new hashes, revisions, test commands/results, and script hash. This source is staged from the exact readable release bytes; it does not claim the unpublished `9f56cb7` commit is available on GitHub.
 
## Current installer revision 1.0.1 supersedes the initial installation status

The operator's r1 apply failed the health guard and both predecessor pointers
were independently confirmed restored. Dashboard is on port 8767; the original
installer wrongly probed 8766. Current revision checks baseline health before
creating fresh r2 candidates and uses the observed Dashboard port. Four current
isolated lifecycle tests pass, and the corrected script SHA/read-only dry run
were verified on Camrui. The Windows launcher has been replaced and parsed with
zero errors at the same path. R2 installation is not yet performed. Follow
[the current operator runbook](../operations/GRACE_CURRENT_CONTROLS_UPDATE_RUNBOOK.md).
