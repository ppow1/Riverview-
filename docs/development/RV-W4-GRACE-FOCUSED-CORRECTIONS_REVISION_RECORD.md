# RV-W4-GRACE-FOCUSED-CORRECTIONS — Revision Record

**Document revision:** 1.0.0
**Task:** RV-W4-GRACE-FOCUSED-CORRECTIONS
**Component:** RESIDENT-ORCHESTRATION / RESIDENT-REASONING
**Timestamp UTC:** 2026-10-21 UTC
**Branch:** `codex/w4-grace-focused-corrections-20261021`
**Integration baseline:** `0cdbddd3baf1c1bdd45f2007d708a4156656e96c`
**Authority:** Isolated source changes, tests, package verification, and PR review only. No production mutation, migration, service restart, merge, or deployment.

## Findings and changes

1. `GraceExecutionService.run_once()` previously invoked provider/model reasoning ahead of dispatch, worker execution, verification, completion reconciliation, and conversation result publication. The existing cycle now advances that admitted work first, then performs durable proposal/external reasoning through the existing fair objective selector. This uses the existing CME and owner-session cycle and does not add a queue.
2. A typed proposal now separates `system_owned_criteria` from Engineering step acceptance criteria. Every original criterion must be preserved exactly and assigned either to a recognized durable lifecycle event or to a deliverable step. Lifecycle criteria do not create receipt work orders. The provider contract directs sufficient single deliverables to one step while retaining legitimate dependency-ordered multi-step plans. Lifecycle classification requires explicit system action language so generic mentions of conversations or grounding remain deliverable requirements.
3. Independent verification retains integrity, provenance, authorization-scope, and structural checks. It also rejects authoritative negative decisions in JSON and independently checks explicit literal/path clauses against substantive artifact content, excluding echoed acceptance metadata. Grace remains responsible for substantive acceptance review. A verifier failure remains durable evidence and is not automatically converted to Codex rework or success. Conversation-origin objectives complete only after accepted verification and Grace's correlated `OBJECTIVE_COMPLETE` decision.

## Changed source and tests

| File | Change |
|---|---|
| `src/riverview_core/resident_execution/service.py` | Ready-work-first owner-session cycle ordering |
| `src/riverview_core/resident_reasoning.py` | Typed lifecycle criteria and explicit evidence mapping |
| `src/riverview_core/local_reasoning_provider.py` | Prompt/schema separation of lifecycle criteria and deliverables |
| `src/riverview_core/resident_execution/pipeline.py` | Exact criterion coverage, durable lifecycle evidence, Grace completion gate |
| `src/riverview_core/resident_execution/verifier.py` | Negative JSON decisions and explicit artifact literals |
| `src/riverview_core/resident_execution/codex_workflow.py` | Integrate semantic artifact checks with existing independent verifier |
| `src/riverview_core/resident_execution/external_reasoning.py` | Preserve lifecycle criteria in exact review subject |
| `src/riverview_core/resident_execution/external_reasoning_mcp.py` | Transport lifecycle criteria in the existing advisory contract |
| `tests/test_grace_execution.py` | Ready-work order, one-step deliverable, exact criterion durability, Grace completion decision |
| `tests/test_local_reasoning_provider.py` | Provider schema/prompt and one-step planning regression |
| `tests/test_resident_reasoning.py` | Narrow lifecycle evidence classification regression |
| `tests/test_codex_cli_adapter.py` | Negative JSON and substantive explicit-literal acceptance regressions |
| `tests/test_external_reasoning_exchange.py` | Exact lifecycle criteria remain digest-bound in the advisory review subject |

Component documentation, canonical Grace integration graph, generated graph views, and revision metadata are updated. The original completed production smoke-test objective and all production records remain untouched.

## Predecessor preservation

Before source edits, predecessor files were copied and hashed with `scripts/revision_control.py backup --task RV-W4-GRACE-FOCUSED-CORRECTIONS`. The exact paths, revisions, SHA-256 values, and timestamps are retained in `.riverview-backups/manifest.jsonl`. Restoration uses the recorded backup bytes and verifies the listed SHA-256 before controlled recovery. Release rollback is independent: preserve the current immutable release pointer and restore that pointer through the existing Camrui controlled-release procedure. This package does not activate or change that pointer.

## Verification

The full canonical `pg_virtualenv -t sh -c 'RIVERVIEW_TEST_PG_DSN="host=$PGHOST port=$PGPORT dbname=$PGDATABASE user=$PGUSER" PYTHONPATH=src python3 -m unittest discover -s tests -v'` run completed on a disposable PostgreSQL 16 cluster: **764 tests, 0 failures, 1 skipped**. The skip is the existing dashboard runtime-role fixture, which the generic isolated cluster does not provision. After the full run, the final lifecycle classifier/provider regressions ran against the edited source: **2 passed**. `python3 scripts/process_graph.py check`: **22 graphs / 593 nodes PASS**. `python3 scripts/revision_control.py check --baseline /tmp/rv-w4-grace-revision-baseline.json`: **PASS, zero issues**. `PYTHONPATH=src python3 -m compileall -q src scripts tests` and `git diff --check`: **PASS**.

An immutable full-source release candidate is built from the final committed revision with `scripts/build_camrui_package.py` and checked with `scripts/verify_camrui_package.py`. The artifact SHA-256 and independent review status are reported separately; no deployment is authorized by this record.

## Expected performance effect and limitations

The prior latency diagnosis measured one 80B reasoning request at 54.912 seconds provider-side and 56.207 seconds end-to-end. Ready dispatch, execution, verification, completion, and publication now precede those potentially slow requests, removing that measured wait from the critical path of already-authorized work in the same owner-session cycle. The model call still consumes time later in the cycle, so this change does not claim higher model throughput. Full live production commissioning and independent human acceptance remain separate gates.
