# RV-W1-ISSUE-POLL-001 checkout evidence

**Document Revision:** 1.0.0

- Source commit: `381f863cf2503c75e4f35a863c8e3fbeec68f64d`
- Branch: `feature/w1-control-board-state-accuracy`
- PR: [#127](https://github.com/ppow1/Riverview-/pull/127), open and unmerged
- Issue: [#120](https://github.com/ppow1/Riverview-/issues/120)
- Environment: Windows local development checkout, Python 3.14.6
- Operator attribution: Windows Codex alias W1 verified by assigned worktree and monitoring record; runtime session UUID remains unverified.

## Change and boundary

The opt-in `scripts/poll_issue_assignments.py` reads GitHub issue comments through the caller's existing `gh` authentication and writes metadata-only local receipts. It stores comment IDs/URLs, source author when available, timestamps, and body digests. It does not store or interpret comment text, change the work registry or v4 status, execute comment instructions, invoke the assignment bridge, launch a process, or wake an existing session. A person must inspect the linked source comment and separately invoke the existing bridge. That bridge records assignment state but has no session wake transport.

No credentials or grants were changed. No production path was read or written. The live API exercise was GET-only and used a temporary local receipt file; the path and comment hashes are omitted from this report.

## Exact-head verification

The following focused suite ran on the source commit above:

```text
python -m pytest -q tests/test_issue_assignment_poller.py tests/test_work_assignment_bridge.py tests/test_work_registry.py tests/test_work_registry_dashboard.py tests/test_work_registry_monitor.py tests/test_work_registry_startup.py
45 passed in 7.46s; exit code 0
```

It covers metadata-only storage, idempotent replay, edited comment versions, cursor overlap, failed API and file writes, corrupt state, deleted author identity, stale-lock recovery, concurrent thread/process writers, no-shell API invocation, and capped watch backoff.

```text
python -m py_compile scripts/poll_issue_assignments.py scripts/record_work_assignment.py scripts/register_work.py tests/test_issue_assignment_poller.py
exit code 0

git diff HEAD^ HEAD --check -- . ':(exclude).riverview-backups/**'
exit code 0
```

Canonical-LF graph check: `python scripts/process_graph.py check` passed with **23 workflows / 581 nodes**. On this Windows checkout, the ordinary check fails with `JSON file revision sidecar checksum mismatch: process_graphs/schema/riverview-process-graph.schema.json`; that schema is unchanged and materializes as CRLF while the sidecar records canonical LF. For the passing check, graph JSON files were normalized temporarily and all unchanged checkout bytes were restored. Both results are retained in the adjacent graph check records.

The live read-only issue poll discovered **164** comments, wrote 164 metadata/hash receipts, and a second poll saw 7 overlapping comments with **0 duplicate receipts**. The temporary cache contained no raw `body` field. Existing CLI authentication was used as found; no auth or credential changes were made. GitHub reported no PR checks for this branch when queried, so no hosted CI result is claimed.

## Revision and predecessor evidence

The changed file sidecars match all seven controlled source/document/graph paths. Six pre-existing files have verified predecessor artifacts, source commit/blob IDs, new revisions, hashes, and restoration instructions in [`predecessors.json`](predecessors.json); all 20 task backup records/artifacts verify against their recorded SHA-256. `revision-audit.json` records the scoped pass.

The repository-wide `revision_control.check` baseline reports 692 `missing_revision` findings in historical evidence files outside this W1 change; none of the changed or new W1 paths are among them. This remains a repository-level records migration issue, not a claim that the global audit passed.

## Remaining limitations

- The poller is an opt-in development CLI. It is not installed as a background service, startup hook, or production integration.
- It discovers comments and leaves assignment interpretation and any explicit registry event to a human. It cannot command or wake an existing Codex session.
- The local receipt cache must not be shared between Windows and Camrui until atomic rename and lock behavior are verified on the selected shared storage.
- The seven historical aliases still lack verified runtime session UUIDs.
- The Windows raw process-graph checksum mismatch and repository-wide missing revision findings are documented above.
- PR review and exact-head hosted checks remain pending; no merge, deployment, or production activation is claimed.

## Coordination

W1 acknowledgment and progress were posted to issue #120. The read-only W3 handoff about PR #116's base, W1 graph/sidecar ownership, and safe future revision-index reconciliation is in [comment 6253567313](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6253567313). The milestone-4 test/live-poll evidence is in [comment 6253676121](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6253676121).
