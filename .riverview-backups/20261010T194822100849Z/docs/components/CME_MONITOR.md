<!--
Riverview~ Controlled Document
File: docs/components/CME_MONITOR.md
Component: CME
File Revision: 1.0.0
Purpose: Specify the assignment progress and health monitoring service
Authority: Observation and CME-owned durable event writes only
Changed: 2026-10-10 UTC | RV-M2.4-001 | Initial M2.4 contract
History: Git and revision/backup manifest
-->
# CME monitoring service

**Component:** CME  
**Milestone:** M2.4 — CME monitoring service  
**Status:** Isolated engineering; live service commissioning and full component DoD remain open.  
**Implementation:** `src/riverview_core/cme/monitor.py`  
**Execution model:** Continuous scheduled polling over durable PostgreSQL assignment state.  
**Owner:** CME; execution, assignment policy, human resources, and capacity scheduling remain in their owning components.

## Responsibility and boundaries

`CMEPostgresMonitor` observes every nonterminal assignment, its latest durable event, optional CME-owned deadline, and current assignment lease. It records monitor health and deduplicated attention or recovery-request events in CME-owned tables. It does not claim leases, change assignment state, run recovery, dispatch work, verify outcomes, or execute engineering actions. A stalled item cannot block a later item because each scan reads the full active set and does not wait on a worker.

An emitted `recovery_requested` row is an observable request for the existing recovery path to reconcile. It is not proof that recovery ran. The M2.3 worker recovery coordinator remains responsible for expired-lease reconciliation before the next worker claim.

## Persistent data and migration

Migration `0005_cme_monitoring.sql` is applied explicitly to a selected schema after the M1.2 ledger, M1.4 lease, and M2.1–M2.3 worker migrations. Monitor startup never applies DDL. `cme_assignment_deadlines` stores an optional timezone-aware UTC deadline without changing earlier assignment creation or event schemas. `CMEPostgresMonitor.set_deadline()` checks that the assignment exists and upserts only CME-owned deadline metadata.

`cme_monitor_health` stores the service identity, latest process instance, health state, heartbeat, last successful scan, most recent persisted failure class, and scan counts. `cme_monitor_events` is append-only and keyed by stable event keys. Repeated scans, monitor replacement, and process restart do not create duplicate alerts for the same assignment/progress or lease generation. Alert resolution is another durable event linked by `attention_key`.

## Detection and health semantics

- Last meaningful progress is the latest durable assignment event timestamp. Lease heartbeat is tracked separately and is never counted as work progress.
- A `running` assignment is stalled when elapsed time from its latest durable event reaches the explicitly configured `stall_after_seconds` threshold.
- A deadline is missed when a configured deadline is at or before the monitor's UTC scan time and the assignment is nonterminal.
- An expired running lease that is also stalled creates one `recovery_requested` event for that lease generation.
- `blocked` and `awaiting_steward` assignments create assignment-local attention records; unrelated rows continue to be scanned.
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

The process entry point is `python -m riverview_core.cme`. It reads `RIVERVIEW_DATABASE_DSN`, `RIVERVIEW_CME_SCHEMA`, `RIVERVIEW_CME_STALL_AFTER_SECONDS`, `RIVERVIEW_CME_WORKER_FRESHNESS_SECONDS`, `RIVERVIEW_CME_POLL_INTERVAL_SECONDS`, and `RIVERVIEW_CME_MAX_BACKOFF_SECONDS` from the environment. The DSN must be delivered through the host's protected service environment; it is never logged. SIGTERM/SIGINT request orderly shutdown.

## Installation, rollback, and limitations

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

The migration is additive. Rollback requires a verified schema backup and a reviewed maintenance operation; do not drop monitor tables while an installed process is active. No shared `riverview_dev` migration or deployed systemd unit is claimed by isolated tests. Alert delivery, a Steward browser dashboard, resource scheduling, HR workflows, and automatic recovery actuation remain separate roadmap work.

See [the flow](CME_MONITOR_FLOW.md), [the cookbook](CME_MONITOR_COOKBOOK.md), and [the M2.4 evidence record](../development/M2.4-001_REVISION_RECORD.md).
