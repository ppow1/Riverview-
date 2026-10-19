<!-- Riverview Controlled Evidence
File: evidence/checkouts/COMMS5-COMPLETION/20261018T0200Z-6b44b39/checkout.md
Component: COMMS5-CURRENT-RUNTIME-OPERATIONS
File Revision: 1.0.2
Task: RV-COMMS5-COMPLETION-20261017
Captured: 2026-10-18T01:54:33Z
Verification refreshed after integration rebase: 2026-10-18T01:57:12Z
Environment: Camrui Ubuntu development checkout; PostgreSQL integration tests use disposable schemas
Initial worktree baseline: 6b44b39ae474e6389f26c97a2c70200f09f33e55
Rebased integration target: ac707ef71335f889dd21ae28210ce9906eec9d38
Authority: Test evidence only; no production mutation, merge, deployment, service restart, or grant change
-->

# Comms5 completion checkout evidence

## Source behavior exercised

- Existing external-reasoning provider MCP operations remain list, claim,
  submit-response, and status in `external_reasoning_mcp.py`.
- The production Grace cycle now polls the existing exchange for completed
  responses, rechecks the original exact escalation grant, reasons over the
  response as advisory input, persists an unapproved proposal and correlated
  event, then acknowledges consumption. The interrupted-before-ack path uses
  the durable event and stable exchange key to avoid duplicate reasoning.
- `comms5_revalidate_and_queue_work` accepts only eligible durable stale-base
  pre-execution failures with no result or verification record. It refreshes
  repository grounding, preserves the blocked source assignment, creates an
  idempotent successor step and queues it through existing Grace/CME dispatch.
- Resource-policy set/lock/status use the additive 0012 store. The scheduler
  applies the stored policy inside its existing transactional lease path and
  restricts selection to registered active workers with the required capability.

## Executed checks

| Command | Result |
|---|---|
| `PYTHONPATH=.:src /tmp/rv-comms5-oauth-test-venv-20261017/bin/pytest -p no:cacheprovider -q tests` | Exit 0 after rebase; 386 passed, 204 skipped. Skips are marked PostgreSQL/environment-dependent. |
| `sudo -n -u postgres env PYTHONPATH=.:src RIVERVIEW_TEST_PG_DSN='dbname=postgres' /tmp/rv-comms5-oauth-test-venv-20261017/bin/pytest -p no:cacheprovider -q tests/test_external_reasoning_exchange.py tests/test_assignment_scheduler.py tests/test_comms5_resource_policy_postgres.py` | Exit 0; 14 passed against test-created disposable PostgreSQL schemas. |
| `python3 -m compileall -q src/riverview_core/resident_execution scripts/run_grace_execution_service.py src/riverview_core/assignment_scheduler/scheduler.py` | Exit 0. |
| `python3 scripts/process_graph.py validate` | Exit 0; 22 graphs. |
| `python3 scripts/process_graph.py generate` | Exit 0; 22 graphs, 556 nodes; no stale projections. |
| `python3 scripts/process_graph.py check` | Exit 0; 22 graphs, 556 nodes. |
| `python3 scripts/revision_control.py check --baseline /tmp/comms5-rev-target.json` | Exit 0; no missing revision increments or predecessor backups. Baseline inventory was generated from integration commit `ac707ef71335f889dd21ae28210ce9906eec9d38`. |
| `git diff --check` | Exit 0. |

The repository-root `pytest -q` discovery command is not the supported suite:
it collects the archival `docs/history/RV-M1.1-002/rev1.0.0/tests` test and
fails collection because that historical file imports `runtime_baseline` as a
top-level module. Running the current `tests/` directory succeeds as recorded
above. An initial broad run also exposed an outdated scheduler mock which did
not include the new optional policy-schema probe; the fixture was updated and
the final suite passed.

## Live production read-only checks

At capture time, Camrui reported `riverview-comms5-camrui.service` active and
healthy on `127.0.0.1:11826` (HTTP 200 health); anonymous MCP returned HTTP 401.
The Grace owner-session unit was active on release
`6b44b39ae474e6389f26c97a2c70200f09f33e55`. The external reasoning MCP unit
was disabled/inactive, migration 0012 and its policy table were absent, and a
read-only AuthorityRegistry query found no `resident.reasoning.escalate` grant.
No live mailbox exchange, production rework, merge, deployment, service restart,
credential/grant change, or migration was performed.

## Decision

Source and isolated PostgreSQL verification: **PASS**. Production Comms5 and
Grace predecessor health: **PASS** for the read-only checks above. Production
mailbox round trip and rework acceptance: **NOT VERIFIED / BLOCKED** by the
inactive external MCP service, absent provider mapping and exact escalation
grant, and unapplied migration 0012 required for policy operations. The source
branch must still be reviewed and integrated; production changes are outside
the current authorization boundary.
