# M33-0009 production execution evidence

- Timestamp: 2026-10-17T03:21:39Z (evidence capture directory timestamp).
- Source commit and staged immutable helper release: `bac5495c4b7d61fd250d88f6af4beead3c79ccfb`. The active dashboard/core pointer remained on release `64e8f14ad6d71102a864755739a1c8a61506235c`.
- Migration `0009_worker_registration_retirement_event` applied through the checksum-pinned runner. The read-only production ledger query records the exact 0000–0009 chain and the reviewed 0009 SHA-256.
- The separate retirement helper was invoked once against its exact fixed M33 IDs and returned `InsufficientPrivilege` (exit 1) before writes. No alternate role, direct SQL write, or privilege change was used.
- Catalog inspection established that `riverview_authority_manager` lacks schema USAGE and registry SELECT/UPDATE on `riverview_dev.worker_registry`. The two M33 registrations therefore remain active. Three Grace registrations remain active; two historical M31 rows remain inactive; no retirement events exist.
- All three M33 units were inactive/dead with PID 0. Grace execution, Grace CPU inference, dashboard, event processor, CME monitor and notification dispatcher were active/running. Grace and CME reported healthy; event processor cursor was `assignment-intake.v1` sequence 58. Dashboard HTTPS returned 200 with certificate verification.
- `migration-postcheck.json` records an attempted runner CLI invocation that returned `local_postgres_operator_required`; it is not evidence of migration failure. The direct read-only ledger result in `postflight.txt` independently verifies the applied migration.
- The protected backup/restore closeout passed before migration 0009; the archive itself is retained outside this evidence directory at the protected path recorded in the cookbook.

**Disposition:** Migration 0009 complete; M33 registration retirement blocked at the existing database authorization boundary.
