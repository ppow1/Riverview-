<!--
Riverview~ Controlled Evidence Record
File Revision: 1.0.0
Component: RESIDENT-CONVERSATION / RESIDENT-MODEL-ROUTER
Task: RV-C3-GRACE-REASONING-RELIABILITY-001
-->
# Grace deferred reasoning recovery — development checkout

**Captured:** 2026-10-18 03:00 UTC
**Host:** `admin1-Default-string` (Camrui)
**Branch:** `codex/grace-reasoning-reliability-active-20261017`
**Parent/source release:** `ac707ef71335f889dd21ae28210ce9906eec9d38` (`codex/grace-conversation-ui-refinement`)
**Evidence class:** Isolated development worktree; no production deployment or live model calls.

## Verification results

- Focused: `PYTHONPATH=src python3 -m pytest -q tests/test_resident_model_router.py tests/test_local_reasoning_provider.py tests/test_resident_conversation.py tests/test_status_dashboard.py` — PASS, **91 passed, 39 skipped**, 11.37s (final 2026-10-18 run).
- Active suite: `PYTHONPATH=src python3 -m pytest -q tests` — PASS, **391 passed, 203 skipped**, 49.64s (final 2026-10-18 run). PostgreSQL integration tests skipped because `RIVERVIEW_TEST_PG_DSN` was unset; no database writes were made.
- Process graph: `python3 scripts/process_graph.py check` — PASS, 22 graphs / 555 nodes. Graph source and projections were regenerated with `python3 scripts/process_graph.py generate`.
- Revision control: `python3 scripts/revision_control.py check --baseline /tmp/rv-c3-revision-inventory.json` — PASS, no issues. Baseline inventory was generated from a detached worktree at the parent commit; all modified predecessors have retrievable SHA-256-matching backups.
- Syntax: `PYTHONPATH=src python3 -m py_compile src/riverview_core/resident_execution/conversation.py src/riverview_core/resident_execution/model_router.py` — PASS.
- Whitespace: `git diff --check` — PASS.
- Root pytest collection: `PYTHONPATH=src python3 -m pytest -q` — BLOCKED during collection by archived test `docs/history/RV-M1.1-002/rev1.0.0/tests/test_runtime_baseline.py` importing unavailable `runtime_baseline`. The current `tests/` suite passes; archived files were not changed.

## Scope and limitations

Synthetic tests cover provider error classification (including terminal authentication/input classes), >32 KiB prompt trimming with protected instructions and active request, independent model capability readiness, bounded retry/backoff, durable status contract, missing-binding block behavior, and exactly-once response behavior. Database restart/attempt-cap integration tests exist but were skipped without the isolated PostgreSQL test DSN. OctoMiner 1 SSH/history remained unavailable; no live inference, service restart, deployment, or endpoint change was attempted. The likely Oct 17 prompt-limit incident diagnosis remains high confidence, not proven.

## Changed controlled source revisions

- `conversation.py` 1.2.15; `model_router.py` 1.2.6; migration `0012_bounded_deferred_retries.sql` 1.0.0.
- Tests: `test_resident_conversation.py` 1.0.35; `test_resident_model_router.py` 1.0.16; `test_local_reasoning_provider.py` 1.1.12.
- Component specification 1.1.36; generated flow 1.0.22; graph ID/revision retained at `rv:resident-conversation:browser-chat` / 1.0.21; process graph source revision recorded in `.riverview-revisions.json`.
- Steward punch list 1.0.3, PL-NEW-043. Predecessor backups and hashes are indexed in `.riverview-backups/manifest.jsonl`.
