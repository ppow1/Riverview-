<!--
Riverview Controlled Development Record
File: docs/development/RV-COMMS5-ESCALATION-INITIATION-001_REVISION_RECORD.md
Component: RESIDENT-REASONING / EXTERNAL-REASONING
File Revision: 1.0.0
Purpose: Record active-principal authorization, Grace exchange initiation, isolated lifecycle validation, and production boundary
Authority: Development and disposable test environments only; no production migration, grant, credential, service, or deployment authority
Changed: 2026-10-18 UTC | RV-COMMS5-ESCALATION-INITIATION-001 | Connect active office principal authorization to durable Grace external-reasoning initiation
History: Git and .riverview-backups/manifest.jsonl
-->
# RV-COMMS5-ESCALATION-INITIATION-001 — implementation and validation

## Changes

- Resolve the active resident principal through the authorized office-state snapshot; validate resident principal kind, occupant identity, and positive binding revision. Revalidate the binding at exact-grant authorization time and fail closed on mismatch or malformed state.
- Use the existing exact-grant authorizer for the resident credential and provider scope. Do not infer authority from an office name, model output, or external provider identity.
- Extend the existing typed reasoning proposal contract with an optional, allowlisted advisory escalation intent. The intent is advisory only and creates no work order, approval, or verification result.
- Connect the persistent Grace reasoning cycle to `request_external_reasoning()` using the existing durable exchange. Persist correlation to the original objective and conversation/message, preserve proposal revision and verified source references where present, enforce the existing classification boundary, assign a deterministic idempotency identity and finite deadline, and suppress duplicate active requests.
- Leave PR #109 unchanged. Its stale-base revalidation and resource-policy operations are regression-checked on this follow-up branch.
- The existing full Camrui package includes the changed Grace/exchange components, Comms5 policy components, and their migration sources. The Comms5-only package remains deliberately scoped; it is not a substitute for the full multi-component runtime package.

## Validation

Commands run from the isolated checkout:

```text
PYTHONPATH=src python3 -m unittest tests.test_grace_runtime_provider_wiring tests.test_local_reasoning_provider tests.test_reasoning_escalation -v
  41 passed

RIVERVIEW_TEST_PG_DSN=<temporary PostgreSQL 16 DSN> PYTHONPATH=src python3 -m unittest tests.test_external_reasoning_exchange tests.test_resident_reasoning tests.test_assignment_scheduler tests.test_comms5_resource_policy_postgres -v
  36 passed

RIVERVIEW_TEST_PG_DSN=<temporary PostgreSQL 16 DSN> PYTHONPATH=.:src python3 -m unittest discover -s tests -v
  598 tests; 1 skipped; 0 failures; temporary PostgreSQL 16 cluster dropped after run

PYTHONPATH=src python3 -m unittest tests.test_runtime_baseline.RuntimeBaselineTests.test_package_exact_commit_checksums_and_no_overwrite tests.test_runtime_baseline.RuntimeBaselineTests.test_full_camrui_package_includes_grace_exchange_and_comms5_policy_components
  2 passed

python3 -m compileall -q src/riverview_core scripts tests
python3 scripts/process_graph.py validate
python3 scripts/process_graph.py check
python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json
git diff --check
  all passed; 22 graphs / 557 nodes
```

The one full-suite skip is the existing dashboard runtime-role ACL integration fixture; the disposable cluster does not provision that named runtime role. PostgreSQL integration tests in the changed exchange, scheduler, and policy components ran against the disposable cluster. Tests do not use production credentials, invoke external providers, or mutate production.

## Status and production boundary

- Source changes and disposable tests: complete on `codex/comms5-principal-escalation-20261018`.
- PR #109: preserved unchanged at baseline head `9a42634ac0e97e3de2cc57b64743581bc617f025`.
- Production code, migration 0012, grants, credentials, services, and data: unchanged.
- Production external-reasoning cycle: unverified. Required commissioning remains subject to reviewed integration, protected backup/restore, migration/provider identity and exact grant procedures, full release packaging/staging, and authorized deployment. Final acceptance must correlate a genuine provider response through Grace consumption and acknowledgment.
