<!--
Riverview~ Controlled Document
File: docs/components/CME_MONITOR_COOKBOOK.md
Component: CME
File Revision: 1.0.0
Purpose: Provide read-only diagnosis and safe recovery guidance for CME monitor
Authority: Diagnostics are read-only; migrations and state changes require explicit operations
Changed: 2026-10-10 UTC | RV-M2.4-001 | Initial M2.4 cookbook
History: Git and revision/backup manifest
-->
# CME monitor troubleshooting cookbook

## Read-only status and health

Use an authorized PostgreSQL client and the configured service schema. Do not put credentials on the command line.

```sql
SELECT service_id, instance_id, status, last_heartbeat_at, last_scan_at,
       last_error, assignments_observed, workers_registered, workers_enabled
FROM riverview_dev.cme_monitor_health;

SELECT event_type, assignment_id, attention_key, details, recorded_at
FROM riverview_dev.cme_monitor_events
ORDER BY recorded_at DESC, event_id DESC
LIMIT 100;

SELECT a.id, a.state, a.workflow_id, a.workflow_step,
       max(e.recorded_at) AS last_meaningful_progress,
       d.deadline_at, l.worker_id, l.heartbeat_at, l.expires_at
FROM riverview_dev.assignments a
LEFT JOIN riverview_dev.events e ON e.assignment_id=a.id
LEFT JOIN riverview_dev.cme_assignment_deadlines d ON d.assignment_id=a.id
LEFT JOIN riverview_dev.assignment_leases l ON l.assignment_id=a.id
WHERE a.state NOT IN ('completed','cancelled')
GROUP BY a.id,d.deadline_at,l.worker_id,l.heartbeat_at,l.expires_at
ORDER BY a.updated_at,a.id;
```

Replace `riverview_dev` with the explicitly configured schema; quote identifiers using the client library if it is not a trusted static name. The API equivalent is `CMEPostgresMonitor.status()` and returns `not_initialized`, `healthy`, `stale`, `degraded`, or `unavailable`, along with heartbeat age, worker health, attention count, and last scan.

## Failure signals and first action

| Signal | Meaning | First read-only check | Recovery/resume |
|---|---|---|---|
| `not_initialized` | No successful monitor scan is recorded | Check explicit migration history and service logs | Apply the reviewed migration, then start the service |
| `stale` | Persisted heartbeat exceeds the client freshness threshold | Check process state, PostgreSQL reachability, and latest `monitor_failed` event | Restore the dependency or restart the monitor; it reacquires its advisory lock and rescans |
| `degraded` | A scan failed and the database accepted the failure record | Inspect sanitized failure class and PostgreSQL health | Correct the dependency or source issue; bounded retry continues |
| `unavailable` | The status client cannot query PostgreSQL | Check service DSN delivery and database health without printing secrets | Restore connectivity; monitor retry loop resumes when available |
| `assignment_stalled` | Durable progress event age reached configured threshold | Inspect assignment events, worker heartbeat, and lease expiry | Existing worker/recovery workflow owns action; CME does not reassign or execute |
| `deadline_missed` | CME-owned deadline elapsed on active assignment | Verify deadline and assignment state | Assignment owner determines next work; a later deadline/terminal state produces a resolution event |
| `recovery_requested` | A stalled running lease expired; CME recorded a request | Inspect assignment recovery records and lease generation | M2.3 coordinator reconciles before worker claim; confirm its durable result separately |

## Safe restart

The monitor keeps no correctness-critical in-memory cursor. A process restart releases the database advisory lock and the new instance rescans durable assignments. Check the latest `monitor_started` event and fresh `cme_monitor_health.instance_id`. Stable event keys prevent duplicate attention records. Never manually alter assignment states, leases, or monitor event history to make health look green.

M2.4 isolated PostgreSQL recovery evidence is retained in the linked checkout record. Live service installation, shared-schema migration, dashboard integration, alert delivery, and full Component DoD are not implied by this cookbook or by isolated tests.
