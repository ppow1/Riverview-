<!-- Riverview~ Controlled Evidence | File Revision: 1.0.0 | Task: RV-WORKER-REGISTRY-RETIRE-001 -->
# M33 worker registration retirement verification

- Repository: `ppow1/Riverview-`
- Branch: `codex/website-improvements`
- Source commit: `e49447855a2abc9b70bfe6f0c4b28ba8cc4f597e`
- Reconciled target parent: `e5a373e43594785c885c6972baecccbc37c6ec34`
- Captured: 2026-10-17 UTC
- Execution host: `admin1-Default-string` (Linux); PowerShell/Windows bridge unavailable

## Verified source behavior

The fixed operation covers only `worker:m33:executor:e92ec51590b34cd3` and
`worker:m33:verifier:e92ec51590b34cd3`. It requires the root-owned revoked
commissioning state file, active Steward principal with institution-scoped
`identity.manage`, exact seven-row/five-active registry baseline, revoked M33
grants and credentials, all three exact M33 units `inactive/dead` with PID 0,
no unexpired M33 leases, no executable M33 assignments, and existing database
role `UPDATE` permission. The transaction changes those two active flags and
appends two Steward-attributed events; all assignment, attempt, result, Grace,
and unrelated registry state is preserved. Every mismatch fails closed.

## Verification

- Focused PostgreSQL suite: **48 passed, 0 failures, 0 skips**, using a fresh,
  temporary PostgreSQL 16 cluster on a private Unix socket. Cluster stopped and
  removed after tests. Includes retirement success/audit, invalid authorization,
  active grant/credential/lease/work guards, history preservation, authority and
  worker-adapter regression tests, and dashboard active-count exclusion.
- Process graph validation: **PASS**, 21 graphs.
- Graph projection check: **PASS**, 21 workflows / 520 nodes.
- Revision audit against `evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json`: **PASS**, zero issues.
- Python compilation: **PASS** for retirement source, command, and affected tests.
- `git diff --check`: historical captured predecessor/evidence files contain
  preserved formatting whitespace; no source or documentation errors were
  reported outside those immutable captures.

## Production state — not executed

No production database query or write, migration, service action, or retirement
was performed from this Linux session. The previously attempted direct SSH
identity to `admin1@192.168.1.155` was rejected with
`Permission denied (publickey,password)`; no private identity material was
printed. The authorized Windows-to-Camrui connection is not available in this
execution environment. The supplied 2026-10-16 inventory remains the last
production inventory evidence; the expected three-active-worker postcondition
is not claimed as observed.

Production completion requires a Camrui operator using the established
Windows SSH path to verify/apply authority migration 0009 under the migration
cookbook, run the documented read-only manager-role privilege probe, stop if it
returns false or errors, and only if it returns true run the fixed helper with
`--apply`. Capture its redacted result and the SQL/systemd postflight in the
procedure. Do not grant UPDATE, use a database superuser workaround, or retry an
ambiguous outcome without read-only inspection.
