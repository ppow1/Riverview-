<!--
Riverview~ Controlled Document
File: docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md
Component: RIVERVIEW-OPERATIONS
File Revision: 1.0.4
Purpose: Provide a safe, evidence-grounded operations and recovery entry point
Authority: Diagnostics are read-only; state-changing operations are explicitly identified
Changed: 2026-10-11 UTC | RV-M4.1-001 | Link identity and authority diagnosis
Changed: 2026-10-11 UTC | RV-M3.3-KNOWLEDGE-OPERATIONS | Add fail-closed repository knowledge operations
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-LIVE-BACKUP-FAILURE | Restore observed PostgreSQL backup-path failure and recovery
History: Git and revision/backup manifest
-->
# Riverview operations and recovery guide

This guide consolidates tested Camrui procedures and links to component-specific contracts. It describes the commissioned development environment, not a generic production deployment. Commands that inspect state are read-only. A `restart` changes process state but not ledger state; migrations, credential changes, assignment edits, backup restoration over an existing database, and data deletion are separately controlled operations.

## 1. Start with a read-only health check

Run on Camrui. These checks do not print credentials or database contents.

```bash
hostnamectl --static
id
systemctl is-active postgresql@16-main.service riverview-event-processor.service riverview-cme-monitor.service riverview-status-dashboard.service ssh.service
pg_lsclusters
ss -ltn '( sport = :5432 or sport = :8766 )'
systemctl show riverview-event-processor.service riverview-cme-monitor.service riverview-status-dashboard.service -p Id -p ActiveState -p SubState -p MainPID -p NRestarts
```

Commissioned listener ownership is PostgreSQL on loopback port 5432 and the read-only dashboard on loopback port 8766. The dashboard's remote access is through an authorized SSH forward; it is not an internet-facing listener. On the observed host all four Riverview/PostgreSQL/SSH units were active. A different result is not repaired by restarting every unit: continue with the owning service below.

Read only the selected unit's recent, sanitized journal:

```bash
journalctl -u riverview-event-processor.service --since=-30min --no-pager
journalctl -u riverview-cme-monitor.service --since=-30min --no-pager
journalctl -u riverview-status-dashboard.service --since=-30min --no-pager
journalctl -u postgresql@16-main.service --since=-30min --no-pager
```

Look for start/ready/heartbeat records, repeated retry or failure classes, process exit codes, and timestamps. Never dump full process environments, `pgpass`, dashboard token files, or credential-bearing command lines into evidence. If symptoms affect multiple services, diagnose PostgreSQL first, then its consumers.

## 2. PostgreSQL and ledger

### Symptoms and diagnosis

| Symptom | Read-only diagnostic | Expected result and interpretation |
|---|---|---|
| Connection refused / projections unavailable | `systemctl is-active postgresql@16-main.service; pg_lsclusters; ss -ltn '( sport = :5432 )'` | Cluster `16 main` is `online`; loopback port 5432 listens. Otherwise inspect the PostgreSQL unit journal before action. |
| Wrong database or schema | The identity and catalog queries below | Expected database `riverview`, schema `riverview_dev`, owner `riverview_core`. A mismatch means stop: do not run migrations against the discovered target. |
| Tables missing / status `not_initialized` | Query `to_regclass` and migration history below | PostgreSQL can be reachable while a component's tables are absent. Dashboard `not_initialized` is not healthy/commissioned. |
| Migration drift | Compare version/checksum catalog output with tracked SQL file hashes at the deployed commit | Any mismatch is an integrity stop. Preserve state and identify the exact migration; never edit an applied migration or rerun guessed DDL. |
| Disk or connection pressure | `df -h /var/lib/postgresql; sudo -u postgres psql -X -d riverview -c 'BEGIN READ ONLY; SELECT state,count(*) FROM pg_stat_activity GROUP BY state ORDER BY state; COMMIT;'` | Full disk, unexpectedly growing sessions, or inability to connect requires the database operator. Do not remove WAL files or terminate unidentified sessions. |

Use local peer authentication as the PostgreSQL OS account for read-only catalog queries; this avoids passwords in the command line. The `BEGIN READ ONLY` wrapper makes the intent explicit:

```bash
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c 'BEGIN READ ONLY; SELECT current_database(),current_user,version(); SELECT nspname,pg_get_userbyid(nspowner) AS owner FROM pg_namespace WHERE nspname = '\''riverview_dev'\''; SELECT version,applied_at,checksum FROM riverview_dev.schema_migrations ORDER BY applied_at,version; SELECT to_regclass('\''riverview_dev.assignments'\''),to_regclass('\''riverview_dev.events'\''),to_regclass('\''riverview_dev.assignment_leases'\''),to_regclass('\''riverview_dev.worker_registry'\''),to_regclass('\''riverview_dev.verification_records'\''),to_regclass('\''riverview_dev.cme_monitor_health'\''),to_regclass('\''riverview_dev.cme_monitor_events'\''); COMMIT;'
```

The output should identify `riverview` and the intended schema. Migration order and checksums are authoritative in `schema_migrations`; missing optional worker/verification relations must be reported as unavailable or not initialized, not as zero healthy workers. The currently commissioned chain includes the ledger, scheduler lease, worker attempts/knowledge/verification/recovery, and CME monitoring migrations. Verify exact recorded rows against the checked-in migration files and release commit before any DDL.

Inspect assignment lifecycle and event causality without payload text:

```bash
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c 'BEGIN READ ONLY; SELECT state,count(*) FROM riverview_dev.assignments GROUP BY state ORDER BY state; SELECT seq,event_id,assignment_id,event_type,correlation_id,causation_id,recorded_at FROM riverview_dev.events ORDER BY seq DESC LIMIT 50; COMMIT;'
```

Do not display event `payload`, worker results, objective text, credential hashes, or private data in a routine diagnostic. Empty assignment or event tables are not evidence of a healthy worker.

### Safe recovery

1. Capture the time, failing service, current source/deployment identity, and sanitized error class.
2. If PostgreSQL is active but a client fails, inspect the relevant service journal and schema/catalog identity. Do not reset credentials or change `pg_hba.conf` as a first response.
3. If the PostgreSQL service itself is failed, inspect its journal and disk availability. Restart only `postgresql@16-main.service` after identifying a transient process failure and checking no maintenance operation is in progress:

   ```bash
   sudo -n systemctl restart postgresql@16-main.service
   systemctl is-active postgresql@16-main.service
   pg_lsclusters
   ```

4. Confirm consumer health from their own bounded projections after connectivity returns. Do not restart all consumers automatically; the event processor and monitor retry/reacquire according to their contracts.

Escalate on schema ownership mismatch, checksum mismatch, corruption, disk exhaustion, authentication failure, or an unexplained data-count change. Never drop `public`, `riverview_dev`, or database `riverview` to clear a test or migration error.

## 3. Migrations, backups, and restoration

### Migration controls

Application startup does not apply DDL. Scheduler, worker adapter, verifier/recovery, and monitor migrations are explicit and ordered. Migration tests must point `RIVERVIEW_TEST_PG_DSN` only at a disposable test database; fixtures create unique `rvtest_*` schemas. For example:

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<disposable PostgreSQL test database DSN>' python3 -m unittest tests.test_postgres_ledger tests.test_assignment_scheduler tests.test_worker_adapter tests.test_outcome_verifier tests.test_worker_recovery tests.test_cme_monitor -v
```

The integration suite must report that all intended PostgreSQL tests ran, with zero skips. A missing DSN or skipped database tests is not a pass. This command is not for the shared Camrui `riverview_dev` schema. An interrupted fixture may leave a test schema: list candidates explicitly with `SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'rvtest_%' ORDER BY schema_name;`, identify the owning test run, and remove only a verified disposable schema after review. Never use wildcard deletion.

### Backup and restore readiness

### Observed PostgreSQL backup path permission failure

During the 2026-10-11 M4.1 rehearsal, `pg_dump` returned `Permission denied`
when the PostgreSQL operating-system account attempted to create a backup
under `/var/lib/riverview/backups/m4.1`. The state directory is deliberately
`riverview:riverview`, mode `0700`; PostgreSQL cannot traverse it. This is a
filesystem boundary, not a database outage. **Do not chmod/chown this directory
or relax its mode.**

Check path and database independently without displaying database contents:

```bash
sudo -n stat -c '%A %a %U:%G %n' /var/lib/riverview
sudo -n -u postgres test -x /var/lib/riverview; printf 'postgres_traverse_exit=%s\n' "$?"
sudo -n pg_isready -d riverview
```

Expected: state directory `drwx------ 700 riverview:riverview`,
`postgres_traverse_exit=1` and PostgreSQL accepting connections. If
`pg_isready` fails, follow the PostgreSQL outage procedure above; do not
conflate it with the path failure.

The safe recovery is a new protected destination under the PostgreSQL-owned
tree. In the verified rehearsal, archive
`/var/lib/postgresql/backups/riverview/m4.1/riverview-20261011T070500Z.dump`
was owned by `postgres:postgres`, mode `0600`, SHA-256
`378a1a4cba4605a673d8cf22b8bfcbb4277bce272158cae6e79c7d6ecfd0720b`; its
`pg_restore --list` and restore to a uniquely named disposable database
passed, with matching migration/table counts (9 migrations, 4 assignments,
11 events, 1 attempt, 1 verification). The disposable database was removed
after verification. Detailed artifact and failed-attempt evidence is retained
at commit `f807d95d688b8a486db34eb5aa4be9f78c8f998d`, path
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T070500Z-backup-restore/`.

After recovery, require the archive checksum to match, `pg_restore --list` to
exit zero, and a disposable restore's migration/catalog counts to match the
captured pre-backup values. Retain a failed archive/restore for diagnosis;
never restore over `riverview`. Escalate if the protected PostgreSQL-owned
destination is unavailable, the checksum/list/restore fails, counts differ,
or any operator proposes changing the private state-directory permissions.

Before a reviewed schema/deployment operation, write a full custom-format dump to a new protected directory, verify its checksum and archive listing, and restore it to a uniquely named disposable database. The following demonstrates backup creation and integrity checks; choose a unique run suffix and retain the resulting path in the approved commissioning record:

```bash
BACKUP_DIR=$(sudo -n -u postgres mktemp -d /var/lib/postgresql/riverview-backup.XXXXXXXX)
BACKUP_FILE="$BACKUP_DIR/riverview.dump"
sudo -n -u postgres sh -c 'umask 077; pg_dump -Fc -d riverview -f "$1"' sh "$BACKUP_FILE"
sudo -n sha256sum "$BACKUP_FILE"
sudo -n -u postgres pg_restore --list "$BACKUP_FILE" >/dev/null
```

Expected: `mktemp` creates a new, collision-resistant mode-0700 directory owned by `postgres`; `pg_dump` exits 0 and with `umask 077` creates a mode-0600 file; a stable SHA-256 is recorded; and `pg_restore --list` exits 0. Preserve the prior dump; do not overwrite it. The documented M1.2 and M1.3 commissioning records contain actual protected-backup and disposable-restore evidence.

To prove recoverability, use a new unique database name; `createdb` fails if it already exists and does not overwrite it. Replace the example suffix with a fresh UTC run identifier, confirm the printed name is not `riverview`, and retain the exact name in evidence:

```bash
RESTORE_DB=rv_restore_YYYYMMDDTHHMMSSZ
sudo -n -u postgres createdb --template=template0 --owner=riverview_core "$RESTORE_DB"
sudo -n -u postgres pg_restore --no-owner --dbname="$RESTORE_DB" "$BACKUP_FILE"
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d "$RESTORE_DB" -c 'BEGIN READ ONLY; SELECT version,checksum FROM riverview_dev.schema_migrations ORDER BY version; SELECT count(*) FROM riverview_dev.assignments; SELECT count(*) FROM riverview_dev.events; COMMIT;'
```

Expected: the restore completes without error and ledger/table counts match the pre-backup evidence. A failed restore database is retained until inspected. Once successful evidence is captured and after verifying the exact target name, remove only this disposable restore database with `sudo -n -u postgres dropdb --if-exists "$RESTORE_DB"`; never use that command with `riverview`. Creating/dropping databases is privileged and can destroy data if a name is reused: inspect the exact target first and use only this uniquely named disposable procedure. Do not restore over the live `riverview` database as a troubleshooting shortcut. A production recovery requires stopping affected writers, selecting a verified backup, an explicit incident/recovery decision, a reviewed recovery plan, and a post-restore integrity check. Database restore is not a routine service restart.

Escalate if dump checksum, archive listing, restore, or row-count validation fails. Preserve the failed artifacts and logs; do not advance a migration or delete the backup to make the check pass.

## 4. CME progress monitor

The dedicated service is `riverview-cme-monitor.service`. It polls durable assignments, progress, deadlines, and lease health; it writes only CME-owned health/attention events. It does not dispatch or recover work.

```bash
systemctl status riverview-cme-monitor.service --no-pager
systemctl show riverview-cme-monitor.service -p ActiveState -p SubState -p MainPID -p NRestarts
journalctl -u riverview-cme-monitor.service -n 100 --no-pager
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c 'BEGIN READ ONLY; SELECT service_id,instance_id,status,last_heartbeat_at,last_scan_at,last_error,assignments_observed,workers_registered FROM riverview_dev.cme_monitor_health ORDER BY last_heartbeat_at DESC; SELECT event_type,assignment_id,attention_key,recorded_at FROM riverview_dev.cme_monitor_events ORDER BY recorded_at DESC,event_id DESC LIMIT 50; COMMIT;'
```

Healthy means a fresh successful scan and heartbeat. `stale`, `degraded`, `unavailable`, and `not_initialized` are distinct failure/initialization states. `assignment_stalled` is an observation; `recovery_requested` is a durable request, not proof recovery ran. Duplicate alerts for the same progress/lease generation are prevented by stable keys.

If the process is inactive, first check PostgreSQL, the unit's sanitized failure, and exact migration rows. Once a transient process failure is established and PostgreSQL is healthy, restart only CME:

```bash
sudo -n systemctl restart riverview-cme-monitor.service
systemctl show riverview-cme-monitor.service -p ActiveState -p MainPID -p NRestarts
sleep 6
journalctl -u riverview-cme-monitor.service -n 30 --no-pager
```

Verify a new healthy instance/heartbeat and that prior alert IDs have not duplicated. The monitor reacquires its database advisory lock and rescans. Do not edit attention history, deadlines, assignment state, or leases to clear an alert. Escalate on persistent DB errors, migration drift, repeated service restarts, or an attention event without its owning recovery evidence.

Focused procedure: [CME monitor cookbook](CME_MONITOR_COOKBOOK.md).

## 5. Event processor and durable cursor

The `riverview-event-processor.service` consumes committed assignment events and advances a durable cursor transactionally. Its failure does not stop PostgreSQL, CME observation, or the dashboard.

```bash
systemctl status riverview-event-processor.service --no-pager
systemctl show riverview-event-processor.service -p ActiveState -p SubState -p MainPID -p NRestarts
journalctl -u riverview-event-processor.service -n 100 --no-pager
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c 'BEGIN READ ONLY; SELECT consumer_id,last_seq,updated_at FROM riverview_dev.event_processor_cursors ORDER BY consumer_id; SELECT max(seq) AS latest_committed_event FROM riverview_dev.events; COMMIT;'
```

Compare the cursor with the latest event sequence and recent `processor_started`, `event_processed`, `processor_retry`, or `processor_stopped` journal entries. A gap may be a pending event; a cursor stuck behind repeated retry means investigate the first failing event and sanitized failure class. Never advance the cursor manually, start a second instance with the same processor ID, or delete a poison event.

After confirming a transient process failure, restart only the processor and confirm it reacquires its cursor and advances idempotently:

```bash
sudo -n systemctl restart riverview-event-processor.service
systemctl is-active riverview-event-processor.service
journalctl -u riverview-event-processor.service -n 40 --no-pager
```

If PostgreSQL session loss is suspected, do not terminate a database backend by guess. The M1.3 acceptance procedure identifies the unique granted consumer advisory lock and application name before any fault injection. Preserve the cursor and event history; recovery replays uncheckpointed events idempotently. Focused procedure: [event processor cookbook](EVENT_PROCESSOR_COOKBOOK.md).

## 6. Dashboard and browser / SSH access

The dashboard service is read-only and serves a bounded PostgreSQL projection on `127.0.0.1:8766`. The Steward's remote browser access uses SSH local forwarding; SSH is transport, not an independent system health source.

```bash
systemctl status riverview-status-dashboard.service --no-pager
systemctl show riverview-status-dashboard.service -p ActiveState -p SubState -p MainPID -p NRestarts
ss -ltn '( sport = :8766 )'
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8766/ -o /dev/null -w 'HTTP %{http_code}\n'
```

Expected: the unit is active, the listener is loopback-only, and the shell route returns HTTP 200. Authenticated APIs require the token entered in the browser; do not put tokens in URLs, shell history, command arguments, screenshots, reports, or journal output. Dashboard projection health and CME health are separate. HTTP 200 with `not_initialized` is not a healthy monitor; HTTP 503 indicates a failed required query, not a missing optional relation when that is represented explicitly.

Browser symptoms include token rejection, stale/unavailable banner, failed request count, missing attention list, or unreadable diagnostic page. Recheck local service/journal first; then use the dashboard's Activity/Workflows diagnostic links and [read-only dashboard cookbook](STATUS_DASHBOARD_COOKBOOK.md). The formatted docs endpoint escapes source HTML and restricts clickable links; raw Markdown is not the operational presentation. A browser refresh or tab switch must not restart the institution or require inference.

For remote access, use the authorized SSH alias/key/known-host setup on the client machine and forward local port 8766 to Camrui's loopback port. Do not expose 8766 to LAN or internet and do not change SSH host-key checking to bypass a connection error. If SSH alone fails while Camrui-local checks pass, diagnose client transport/authentication without restarting the dashboard or database. If the browser shows stale state while its host can reach the service, compare API `observed_at`, CME heartbeat, and service journal; do not label cached data healthy.

Recovery of a transient dashboard process failure:

```bash
sudo -n systemctl restart riverview-status-dashboard.service
systemctl is-active riverview-status-dashboard.service
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8766/ -o /dev/null -w 'HTTP %{http_code}\n'
```

Reauthenticate in the browser and confirm projection freshness. Dashboard failure must not interrupt CME or the event processor. Escalate repeated 503s, unexpected non-loopback bindings, token permission errors, or any indication of secret leakage; never weaken authentication or bind policy to restore convenience.

## 7. Worker registration, scheduling, leases, assignments, verification

The scheduler and worker adapter are libraries/integration-tested components; there is **no commissioned always-on worker service** in the current environment. Dashboard worker rows derive from actual registry/lease state. Zero workers means no live worker is available, not healthy execution. The historical M3.1 real-worker acceptance artifact was a bounded `deterministic.sha256.v1` task with a persisted result and independent verification; it does not prove a general code-writing agent or ongoing autonomous Grace.

On the live host, inspect only counts and metadata:

```bash
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c 'BEGIN READ ONLY; SELECT active,count(*) FROM riverview_dev.worker_registry GROUP BY active ORDER BY active; SELECT status,count(*) FROM riverview_dev.worker_attempts GROUP BY status ORDER BY status; SELECT state,count(*) FROM riverview_dev.assignments GROUP BY state ORDER BY state; SELECT decision,count(*) FROM riverview_dev.verification_records GROUP BY decision ORDER BY decision; SELECT decision,count(*) FROM riverview_dev.worker_recovery_records GROUP BY decision ORDER BY decision; COMMIT;'
```

If a relation is missing, first check the migration ledger; do not create it manually. For a specific assignment, inspect the browser's bounded detail projection. Use correlation IDs and event sequence to trace causality. A missing claim can mean no ready item, missing capability/scope, or a lease; use the [scheduler cookbook](ASSIGNMENT_SCHEDULER_COOKBOOK.md). A stale/expired fencing generation must be discarded, never replayed. A `running` attempt without an outcome is incomplete, not success. Recovery preserves committed results for separate verification, requeues only a proven retry-safe action, and waits/escalates uncertain external effects.

The worker adapter's integration tests require an isolated PostgreSQL database. Never register a production credential by running a test command against shared `riverview_dev`; M2.1–M2.3 test fixtures own unique schemas. Only an authorized control-plane enrollment may create a real worker identity/credential. Credentials are displayed once at enrollment and must be transferred via the established protected mechanism; never record them in this guide, issue, journal, or evidence.

Completion is not worker-reported. Inspect independent `verification_records` and the assignment's durable state; only accepted evidence permits a verified terminal completion. An awaiting-verification task is not complete; `INCONCLUSIVE`, rejected, `awaiting_steward`, and `WAITING_FOR_EVIDENCE` remain visible blockers. Focused procedures: [scheduler](ASSIGNMENT_SCHEDULER_COOKBOOK.md), [worker and recovery](WORKER_ADAPTER_COOKBOOK.md), and [event ledger](POSTGRES_LEDGER_COOKBOOK.md).

### Repository knowledge grounding

The current repository-backed provider is a bounded read-only implementation
and has passed an isolated PostgreSQL worker/artifact/distinct-verifier cycle.
It is **not configured in the live worker service**. A live request that needs
institutional grounding must remain waiting unless an active provider returns
complete `VERIFIED` evidence; missing provider, missing source pin, partial
retrieval, or `record_learning=UNAVAILABLE` must never be presented as
verification or authority.

For source-checkout diagnosis, the configured source must be a full Git commit
ID, `HEAD` must match it, and the fixed source set must be clean:

```bash
git rev-parse --verify 'HEAD^{commit}'
git status --porcelain --untracked-files=no -- docs/components/WORKER_ADAPTER.md src/riverview_core/worker_adapter/adapter.py src/riverview_core/worker_adapter/continuous.py src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py src/riverview_core/worker_adapter/repository_knowledge.py
PYTHONPATH=src python3 -m unittest tests.test_repository_knowledge -v
```

Expected: the printed full commit exactly matches the configured pin, the
scoped status is empty, and the provider contract tests pass. In an immutable
package, `cat SOURCE_COMMIT` must match that pin and
`sha256sum --strict --check PACKAGE_SHA256SUMS` must report every allowlisted
file `OK`. `NO_MATCH` means an identifier is outside the reviewed allowlist;
`CONTRADICTORY` means assignment/action contract refs disagree; `UNVERIFIED`
means provenance or integrity did not match; `INCOMPLETE` means a retrieval
bound was exceeded; `UNAVAILABLE` means source/provider/learning capability is
absent. Preserve the exact outcome and its references in
`knowledge_observations`; never edit shared assignment authority or hand-rewrite
an observation. The [repository knowledge cookbook](REPOSITORY_KNOWLEDGE_COOKBOOK.md)
defines status-specific safe recovery. Escalate a pin/source conflict, missing
allowlisted file, integrity error, or any request to enable a live provider
without database-enforced Steward grant validation. No learning storage or
institutional learning promotion is commissioned by this provider.

## 8. Baseline diagnostic, known incidents, and service boundaries

The request-driven baseline probe is distinct from the continuous monitor. Its last report may be stale even when the unit has exited successfully. Inspect only its sanitized report and unit metadata:

```bash
systemctl show riverview-baseline.service -p LoadState -p Result -p ExecMainStatus
sudo -n /usr/bin/python3 scripts/read_baseline_report.py
```

Run from the verified repository/release context as described in the [runtime baseline cookbook](RUNTIME_BASELINE_COOKBOOK.md). Expected M1.1 success is fresh `baseline_ready=true` and no blocker; an old report must not be treated as current. Known commissioning defects and verified recovery include a non-seeking TTY password prompt, systemd credential owner/mode distinction, misleading `UNSAFE_PATH` diagnostic attribution, and Windows-created CRLF package scripts. Their exact root causes and safe recovery are retained in the versioned [runtime baseline procedure](RUNTIME_BASELINE_COOKBOOK.md) and M1.1 evidence; do not repeat the historical fault injection on a live service.

Never restart or reconfigure unrelated units to clear a local component error. Relevant ownership is:

| Service | Responsibility | Does not own |
|---|---|---|
| `postgresql@16-main.service` | Database process and storage | Assignment scheduling, migration policy |
| `riverview-event-processor.service` | Durable ordered event consumer | Worker execution, CME attention |
| `riverview-cme-monitor.service` | Progress/deadline/lease observation; CME metadata | Assignment transition, dispatch, recovery actuation |
| `riverview-status-dashboard.service` | Read-only projection and browser document rendering | Ledger mutation, dispatch, service supervision |
| Worker adapter / scheduler libraries | Tested local worker/lease operations | Currently commissioned worker service or unattended Grace |

## 9. Evidence and escalation

Capture exact UTC time, hostname, source commit, deployed release identity, selected unit properties, sanitized journal excerpt, read-only query result, command exit code, and evidence file hashes. Keep failed attempts as separate evidence; do not overwrite them with a later passing run. The commissioning records linked from each component cookbook establish which operations were actually exercised and which remain isolated tests only.

Stop state-changing work and escalate to the Steward/Operations owner for: migration checksum or schema-owner mismatch; failed or unverified backup/restore; data loss/corruption; unexplained event/cursor discontinuity; a credential/authentication change; non-loopback exposure; uncertain external execution effects; a request to alter a protected terminal assignment; or a need to restore over shared state. Routine process failure can be repaired with the component-local, documented restart after its dependency and failure cause are understood. Never sacrifice event history, backup integrity, authority checks, or privacy to make a status indicator green.

## Component cookbooks and evidence

- [PostgreSQL ledger](POSTGRES_LEDGER_COOKBOOK.md) · [event processor](EVENT_PROCESSOR_COOKBOOK.md) · [CME monitor](CME_MONITOR_COOKBOOK.md)
- [assignment scheduler](ASSIGNMENT_SCHEDULER_COOKBOOK.md) · [worker adapter and recovery](WORKER_ADAPTER_COOKBOOK.md) · [dashboard](STATUS_DASHBOARD_COOKBOOK.md) · [runtime baseline](RUNTIME_BASELINE_COOKBOOK.md)
- [repository knowledge provider](REPOSITORY_KNOWLEDGE_COOKBOOK.md)
- [identity and authority](INSTITUTIONAL_AUTHORITY_COOKBOOK.md) · [authority contract](INSTITUTIONAL_AUTHORITY.md) · [authority flow](INSTITUTIONAL_AUTHORITY_FLOW.md)
- [M1.2 commissioning](../../evidence/checkouts/POSTGRES-LEDGER/20261010T1615Z-3fd6fd2/checkout.md) · [M1.3 commissioning](../../evidence/checkouts/EVENT-PROCESSOR/20261010T1700Z-9ca7cb1/runtime_acceptance.json) · [M2.4 commissioning](../../evidence/checkouts/M3.1-CME-LIVE/20261010T223049Z-702f5db/commissioning.md)

## Revision history

- **1.0.0 — 2026-10-11:** Initial consolidated operational and recovery guide grounded in Camrui service units, component contracts, and retained commissioning findings.
- **1.0.1 — 2026-10-11:** Make backup paths collision-resistant and document a unique disposable database restore/cleanup path.
- **1.0.3 — 2026-10-11:** Document observed fail-closed repository provider diagnostics and recovery boundaries.
- **1.0.4 — 2026-10-11:** Restore the observed PostgreSQL backup-path permission diagnosis and verified safe recovery evidence.
