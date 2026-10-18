<!--
Riverview~ Controlled Document
File: docs/development/RV-W1-REGISTRY-PROCESS-CONCURRENCY-001_REVISION_RECORD.md
Component: UNIVERSAL-WORK-REGISTRY
File Revision: 1.0.0
Purpose: Record independent-process concurrency verification for the file-backed registry
Authority: Test evidence only; no execution authority or cross-host commissioning claim
Changed: 2026-10-18 UTC | RV-W1-REGISTRY-PROCESS-CONCURRENCY-001 | Add subprocess writer regression
History: Git and .riverview-backups/manifest.jsonl
-->

# W1 registry process concurrency revision record

## Scope

The Universal Work Registry already had concurrent-write coverage using
threads. This increment adds independent subprocess clients to verify that
separate Python processes preserve all worker, session, and work-order writes
through the existing lock-directory and atomic-replace implementation. No
registry runtime behavior, schema, authority, scheduler, registration CLI, or
dashboard behavior changes.

## Predecessors

Before editing, exact predecessor bytes were copied under
`.riverview-backups/20261018T225253966Z/`:

- `tests/test_work_registry.py` — SHA-256
  `2521a77fde72e8d69de95cb365b886e8cbbe87736a5e347dbe0c50ba401f600d`
- `docs/components/WORK_REGISTRY.md` — SHA-256
  `6951a06d08e183baa2edc0e65c4eef1f148d4c6e1d266380a9b7e1a353ff4da4`
The append-only backup manifest records each modified source revision, digest,
task ID, and restoration path. Backups were byte-copied and verified before
changes.

## Verification

On the isolated Windows W1 branch, these focused PowerShell commands passed
with `$env:PYTHONPATH='src'`:

- `python -m unittest discover -s tests -p test_work_registry.py`
  — 15 tests passed, including eight independent subprocess writers.
- `python -m unittest discover -s tests -p test_work_registry_monitor.py`
  — 3 tests passed, including Windows PowerShell execution and dynamic v4
  fallback discovery.
- `python -m unittest discover -s tests -p test_work_registry_dashboard.py`
  — 3 tests passed.
- `python -m unittest discover -s tests -p test_work_registry_startup.py`
  — 3 tests passed.

The four commands passed 24 tests total. `py_compile` and `git diff --check`
also passed. This verifies multiple local processes on Windows only; it does
not claim a working shared Windows/Linux network filesystem or production
installation.
