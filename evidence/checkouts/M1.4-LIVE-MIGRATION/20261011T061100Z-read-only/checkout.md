<!-- Riverview~ Controlled Evidence -->
<!-- File Revision: 1.0.0 -->
# M1.4 live migration status correction

- **Task:** RV-M1.4-LIVE-DEPENDENCY-CORRECTION
- **Observation source commit:** `efc687769ebe683adb5e0f3e3c14dbd15480f3e3` on the M4.1 database-boundary branch.
- **Current branch:** `codex/m3.3-repository-knowledge`; this bundle preserves the exact read-only evidence for roadmap and cookbook reconciliation.
- **Scope:** PostgreSQL peer-authenticated catalog inspection and local SQL checksum comparison only.

`riverview_dev.schema_migrations` contains `0001_assignment_leases`, applied at `2026-10-10 18:27:04.341175-04:00`. Its recorded SHA-256 is `ce29c2994904f54706db883f61127bf05ee195ecbdce90e7242886e86711b717`, equal to the checked-in SQL. The migration was applied in the later worker/monitor dependency chain. The evidence does not establish a standalone M1.4 scheduler service, live lease claiming, or M1.4 acceptance/full Component DoD.

`live-peer-inspection.txt` is an exact copy of the read-only output. `migration-sql-checksum.txt` verifies the current checked-in SQL bytes. No database write was performed by this inspection.
