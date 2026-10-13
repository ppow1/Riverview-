# M4.1 live authority boundary preflight

- Task: `RV-M4.1-LIVE-BOUNDARY-PREFLIGHT`
- Source commit: `fbcdf58030c7b7e6bcfe55c5f197f6afd19064a2`
- Host: Camrui; PostgreSQL 16.15; read-only catalog inspection.
- Result: M4.1 live schema/role boundary NOT READY. `riverview_authority`, the manager role, owner role and nine authority tables are absent. `riverview_dev` remains owned by runtime role `riverview_core`, has 67 catalog objects, and the runtime has schema USAGE. The dedicated-schema boundary helper therefore must not be applied to this mixed schema.
- Helper's source checkout is not traversable by OS account `postgres`; exact helper was staged read-only under `/tmp` and run with a local peer connection. It exited 1 with its sanitized `BoundaryPreflightError` as expected for an absent selected schema. There was no `--apply` and no database mutation.
- No roles, schema, credentials, migration, assignments, workers or services changed.
- The independent protected-backup/restore rehearsal is recorded at `../20261011T070500Z-backup-restore/`.
