<!--
Riverview~ Controlled Document
File: docs/components/CME_MONITOR.md
Component: CME
File Revision: 1.0.5
Changed: 2026-10-24 UTC | RV-CME-GRACE-BLOCKED-OBJECTIVE-ESCALATION-20261024 | Document Grace objective escalation observation.
Purpose: Specify the assignment progress and health monitoring service
Authority: Observation and CME-owned durable event writes only
Changed: 2026-10-10 UTC | RV-M2.4-002 | Record final full-suite commissioning verification
History: Git and revision/backup manifest
-->
# CME monitoring service

**Component:** CME  
**Milestone:** M2.4 — CME monitoring service  
**Status:** Isolated technical criteria PASS at `a44091bc32e82580dd8a3350e1ecfa47b0157b36`; Camrui deployment status and evidence are recorded in `docs/development/M2.4-001_REVISION_RECORD.md`. Full component DoD remains open.
**Implementation:** `src/riverview_core/cme/monitor.py`  
**Execution model:** Continuous scheduled polling over durable PostgreSQL assignment state.  
**Owner:** CME; execution, assignment policy, human resources, and capacity scheduling remain in their owning components.

## Responsibility and boundaries

`CMEPostgresMonitor` observes every nonterminal assignment, its latest durable event, optional CME-owned deadline, and current assignment lease. It records monitor health and deduplicated attention or recovery-request events in CME-owned tables. It does not claim leases, change assignment state, run recovery, dispatch work, verify outcomes, or execute engineering actions. A stalled item cannot block a later item because each scan reads the full active set and does not wait on a worker.

The monitor also reads Grace's column-scoped objective status and event records. When a GROUNDED objective has a durable revision-matched `execution.reasoning_failed` event with `status=BLOCKED`, it appends one `grace_objective_blocked` CME event keyed by objective revision and fence runtime. The decision recommends Steward review before retry. It never resumes reasoning, changes the objective, creates an assignment, or calls an external model. This covers objectives that are fenced before any Engineering assignment exists.

An emitted `recovery_requested` row is an observable request for the existing recovery path to reconcile. It is not proof that recovery ran. The M2.3 worker recovery coordinator remains responsible for expired-lease reconciliation before the next worker claim.

## Persistent data and migration

Migration `0005_cme_monitoring.sql` is applied explicitly to a selected schema after the M1.2 ledger, M1.4 lease, and M2.1–M2.3 worker migrations. Monitor startup never applies DDL. `cme_assignment_deadlines` stores an optional timezone-aware UTC deadline without changing earlier assignment creation or event schemas. `CMEPostgresMonitor.set_deadline()` checks that the assignment exists and upserts only CME-owned deadline metadata.

`cme_monitor_health` stores the service identity, latest process instance, health state, heartbeat, last successful scan, most recent persisted failure class, and scan counts. `cme_monitor_events` is append-only and keyed by stable event keys. Repeated scans, monitor replacement, and process restart do not create duplicate alerts for the same assignment/progress or lease generation. Alert resolution is another durable event linked by `attention_key`.

## Detection and health semantics

- Last meaningful progress is the latest durable assignment event timestamp. Lease heartbeat is tracked separately and is never counted as work progress.
- A queued, ready, running, awaiting-verification, or rework-required assignment is stalled when elapsed time from its latest durable event reaches the explicitly configured `stall_after_seconds` threshold.
- A deadline is missed when a configured deadline is at or before the monitor's UTC scan time and the assignment is nonterminal.
- An expired running lease that is also stalled creates one `recovery_requested` event for that lease generation.
- `blocked` and `awaiting_steward` assignments create assignment-local attention records; unrelated rows continue to be scanned.
- A Grace objective with an explicit durable revision-scoped reasoning block creates one `grace_objective_blocked` event with the failure count and safe error code; repeated scans are idempotent.
- Worker health is `healthy` only while its most recent lease heartbeat is within the configured freshness limit and the lease remains unexpired. A registered worker with no heartbeat is `unknown`; an inactive or expired/stale worker is `unavailable` or `stale` respectively.
- CME health is `not_initialized` before its first successful scan, `healthy` with a fresh successful scan, `stale` after the configured observation freshness threshold, `degraded` after a recorded scan failure, and `unavailable` when a status client cannot reach PostgreSQL.

## Interfaces

```python
CMEPostgresMonitor(
    dsn: str,
    *,
    schema: str = "public",
    stall_after_seconds: float,
    worker_freshness_seconds: float = 30,
    poll_interval: float = 1,
    max_backoff_seconds: float = 30,
    service_id: str | None = None,
)
monitor.set_deadline(assignment_id: str, deadline_at: datetime) -> None
monitor.scan_once() -> dict
monitor.status(*, freshness_seconds: float = 30) -> dict
monitor.run_forever(stop_event: threading.Event | None = None) -> None
```

Only one process per schema/service identity holds the PostgreSQL advisory lock. Unexpected process death releases the lock; a replacement obtains it and re-scans durable active assignments. Each query and write is assignment-scoped; service status and attention are externally readable JSON-like values. PostgreSQL errors during continuous operation are logged without credentials, recorded when the database is reachable, and retried with bounded exponential backoff. Unreachable status reads return `unavailable` rather than healthy.

The process entry point is `python -m riverview_core.cme`. The installed service uses `scripts/run_cme_monitor.py` to validate the exact systemd credential mount and copy its protected PostgreSQL passfile into a mode-0600 service-private runtime directory before starting the monitor. Ambient libpq overrides and passwords in the DSN are rejected. The service reads `RIVERVIEW_DATABASE_DSN`, `RIVERVIEW_CME_SCHEMA`, `RIVERVIEW_CME_STALL_AFTER_SECONDS`, `RIVERVIEW_CME_WORKER_FRESHNESS_SECONDS`, `RIVERVIEW_CME_POLL_INTERVAL_SECONDS`, and `RIVERVIEW_CME_MAX_BACKOFF_SECONDS` from a root-owned unit. SIGTERM/SIGINT request orderly shutdown.

## Installation, rollback, and limitations

The systemd service is installed independently at `/etc/systemd/system/riverview-cme-monitor.service`; its root-owned release is selected by `/opt/riverview-cme-monitor/current`. Deployment never changes the event processor or dashboard service. The unit uses the existing Riverview runtime identity, credential source, PostgreSQL role, and schema; it writes only the CME-owned monitor tables. See the cookbook for operational checks and recovery.

For isolated testing, create a unique disposable schema and apply migrations explicitly:

```python
apply_migrations(dsn, schema=schema)
apply_migrations(dsn, schema=schema,
    migrations_dir=core / "assignment_scheduler/migrations")
apply_migrations(dsn, schema=schema,
    migrations_dir=core / "worker_adapter/migrations")
apply_migrations(dsn, schema=schema,
    migrations_dir=core / "cme/migrations")
```

The migration is additive and applied only after the complete ledger, scheduler and worker migration chain. Rollback requires a verified schema backup and a reviewed maintenance operation; do not drop monitor tables while an installed process is active. Alert delivery, resource scheduling, HR workflows, and automatic recovery actuation remain separate roadmap work.

See [the flow](CME_MONITOR_FLOW.md), [the cookbook](CME_MONITOR_COOKBOOK.md), and [the M2.4 evidence record](../development/M2.4-001_REVISION_RECORD.md).
