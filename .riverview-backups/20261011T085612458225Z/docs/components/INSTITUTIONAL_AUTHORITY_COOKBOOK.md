<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.17
Purpose: Diagnose and safely recover institutional authority registry state
Authority: Read-only diagnostics first; grant changes require authenticated Steward
Changed: 2026-10-11 UTC | RV-M4.1-001 | Keep evidence references as readable paths in safe dashboard renderer
Changed: 2026-10-11 UTC | RV-M4.1-COOKBOOK-DB-BOUNDARY | Document isolated database boundary provisioning and schema-owner gate
Changed: 2026-10-11 UTC | RV-M4.1-LEAST-PRIVILEGE | Require dedicated registry schema and deny manager DDL/owner membership
Changed: 2026-10-11 UTC | RV-M4.1-ROLE-SCOPE-REVIEW-FIX | Align operations checks with the isolated authority schema
Changed: 2026-10-11 UTC | RV-M4.1-DEDICATED-SCHEMA-COOKBOOK | Use null-safe catalog checks for the not-yet-created authority schema
Changed: 2026-10-11 UTC | RV-M4.1-PREFLIGHT-DIAGNOSTIC | Document safe boundary detail and SQLSTATE-only database failures
Changed: 2026-10-11 UTC | RV-M4.1-FRESH-SCHEMA-MIGRATION-LEDGER | Describe fresh-schema authority migration order and checksum ledger bootstrap
Changed: 2026-10-11 UTC | RV-M4.1-NOINHERIT-MANAGER-DOC | Document NOINHERIT manager with no role memberships
Changed: 2026-10-11 UTC | RV-M4.1-OWNER-SCHEMA-USAGE | Diagnose and repair FK-check schema USAGE for protected table owner
Changed: 2026-10-11 UTC | RV-M4.1-APPLY-REQUIRED-DRY-RUN | Verify read-only preflight reports incomplete grants before apply
Changed: 2026-10-11 UTC | RV-M4.1-BOOTSTRAP-WRITE-AHEAD | Document restart-safe Steward credential bootstrap
Changed: 2026-10-11 UTC | RV-M4.1-LIVE-BOOTSTRAP-EVIDENCE | Record actual Camrui backup, restore, ACL and Steward bootstrap results
Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Add exact-grant function deployment preflight and isolated runtime recovery path
History: Git and .riverview-backups/manifest.jsonl
-->
# Institutional authority registry cookbook

**Current state:** Camrui has the dedicated `riverview_authority` schema,
protected table ownership, manager credential and root-local Steward identity
documented below. Migration 0002 and the runtime exact-grant function are newly
implemented and isolated-tested, but are **not yet applied** to Camrui; the live
runtime currently has no authority-schema `USAGE` or grant-function execution,
and no live worker consumes grants. The registry belongs in its separate schema;
never use the mixed `riverview_dev` application schema. Do not paste bearer or
database credential values into a shell command.

## Confirm migration readiness

```sh
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT to_regnamespace('riverview_authority') AS authority_schema,
          to_regclass('riverview_authority.schema_migrations') AS migration_ledger,
          to_regclass('riverview_authority.institutional_principals') AS principals,
          to_regclass('riverview_authority.authority_grants') AS grants"
```

Expected on the current Camrui baseline: all four objects exist. If the schema
or any of these relations is absent, compare with the dated deployment evidence
before proceeding. A partial schema or checksum mismatch is a stop condition,
not permission to create objects by hand.

## Inspect identity and grant state (read only)

```sh
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT principal_id,principal_kind,status,created_at
     FROM riverview_authority.institutional_principals ORDER BY created_at"
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT grant_id,principal_id,action,scope_ref,granted_by,policy_ref,
          valid_from,valid_until,revoked_at
     FROM riverview_authority.authority_grants ORDER BY created_at"
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT office_id,occupant_id,implementation_id,binding_revision,updated_at
     FROM riverview_authority.office_bindings"
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT office_id,revision,updated_at FROM riverview_authority.office_runtime_state"
```

Expected: only provisioned identities appear. A grant is usable only when its
principal is active, credential unexpired/unrevoked, and action and scope match
exactly. Missing rows, stale timestamps, unexpected broad grants, or conflicting
binding revisions are not healthy/authorized states.

## Symptoms and responses

| Symptom | Likely cause | Safe response | Escalate when |
|---|---|---|---|
| `AuthorityDenied` | Unknown/revoked/expired credential or no exact grant | Inspect identifiers and validity metadata; request the narrowly scoped grant through Steward authority | Identity or grant rows conflict with the auditable event chain |
| `RegistryUnavailable` | Migration absent, PostgreSQL unavailable, or query failure | Check `systemctl status postgresql`, `journalctl -u postgresql -n 60 --no-pager`, and migration relation presence | Checksum drift, partial migration, backup restore, or ownership mismatch is found |
| Old occupant can no longer update office state | Expected grant revocation on occupant replacement | Steward explicitly grants the new occupant `office.state.write` for that office | Old binding/authority event is absent or revocation did not commit atomically |
| Office state disappears after replacement | State was keyed to the implementation rather than office, or an unreviewed manual edit occurred | Stop writes; compare office state revision and backup before recovery | Do not reconstruct state from resident memory or overwrite the database |
| Bootstrap reports an existing Steward | Initial bootstrap already completed | Do not repeat, truncate, or reset; use the authenticated credential-rotation procedure | Every Steward credential is lost; use the protected administrator recovery plan |

## Security and recovery warnings

- Never select, print, export, or paste `credential_sha256` values or plaintext
  bearer tokens. The system stores only digests; no report needs the raw token.
- Never insert a grant directly with SQL, invent an authority reference, disable
  the append-only event trigger, or update an old audit event.
- Never drop the authority schema or restore over the active database to fix a
  denied request. First preserve a protected backup and diagnose the exact cause.
- Current `riverview_core` ownership allows privileged direct SQL. Until the
  reviewed DB-role separation and worker-control integration exist, this module
  is not deployed as an operational authorization boundary.

After any authorized recovery, confirm the active principal, exact grant,
current office binding/state revisions, append-only event continuity, and the
separate component service health. Resume only the denied action after a fresh
`authorize()` check; a previous successful decision is not reused after a
binding or grant change.


## Database privilege boundary preflight

**Historical preflight:** the following observation predates the 2026-10-11
authority-schema commissioning recorded at the end of this cookbook. It describes
the earlier `riverview_dev`-only state and is retained as evidence, not a current
instruction to bootstrap the authority schema again.

The authority tables are not installed on Camrui yet. Before deployment, check
the current role and schema ownership without exposing credentials or rows:

```sh
sudo -n -u postgres psql -X --set=ON_ERROR_STOP=1 -d riverview -c \
  "BEGIN READ ONLY; SELECT current_user; SELECT nspname,pg_get_userbyid(nspowner) AS schema_owner FROM pg_namespace WHERE nspname='riverview_dev'; SELECT rolname,rolsuper,rolcreaterole,rolcreatedb,rolbypassrls FROM pg_roles WHERE rolname='riverview_core'; SELECT to_regclass('riverview_dev.institutional_principals') AS authority_registry; COMMIT;"
```

Observed on Camrui at the time of this preflight: `current_user=postgres` for the
read-only diagnostic; `riverview_dev` and its application tables are owned by
`riverview_core`; that role has no superuser, CREATEROLE, CREATEDB, or BYPASSRLS
attributes but has schema CREATE. `institutional_principals` is absent. The exact
command above exited 0. The output is retained in
`evidence/checkouts/M4.1/20261011T043300Z-d281463/authority-live-preflight.txt`.
Schema ownership does not itself prove safe authority isolation. Do not apply
the isolated migration to shared state.

A disposable PostgreSQL 16.15 experiment transferred only the test authority
tables to a `NOLOGIN` owner while leaving an application-like role as schema
owner. The schema owner was denied direct SELECT and INSERT on the protected
relations; a separate service-like role with membership in the owner role could
read them. The experiment is recorded at
`evidence/checkouts/M4.1/20261011T043200Z-d281463/role-boundary-summary.json`. CI for the branch head also passed (run [38111853146](https://github.com/ppow1/Riverview-/actions/runs/38111853146)). This is a feasibility result only: a
versioned role-provisioning/migration package, protected service credential,
application integration, and shared-schema deployment have not been delivered.

Until those pieces are implemented and independently tested, treat authority
registry responses as isolated library behavior, not a deployed security
boundary. Do not manually create production grants or run direct SQL to change
identity state. Preserve existing services and use a new protected backup and
restore rehearsal before any future deployment. Stop and escalate if any
proposed deployment cannot prove that ordinary runtime principals lack direct
write access and cannot assume the authority writer role.

After a reviewed boundary package exists, verify as the ordinary app role that
SELECT and DML against the authority tables are denied, verify that the isolated
authority service can perform only its documented registry operations, and
confirm every attempt (including denials) is retained in the authority event
record. A passing isolated role experiment must not be reported as live
commissioning.

## Fresh dedicated authority schema migration

The M4.1 migration directory is self-contained and applies only to the dedicated `riverview_authority` schema after the DBA has created that schema with its distinct NOLOGIN schema owner. `0000_authority_migration_ledger.sql` creates the local `schema_migrations` ledger if missing; `0001_institutional_authority.sql` creates the nine authority tables and append-only trigger; `0002_exact_grant_authorization.sql` adds the protected exact action/scope check. The existing checksum runner records each checksum and refuses drift. A compatible existing ledger is retained; no `riverview_dev` migration is implied.

Isolated regression command (the test creates an empty unique schema with no ledger, applies both migrations, then verifies idempotent rerun):

```sh
RIVERVIEW_TEST_PG_DSN="$RIVERVIEW_TEST_PG_DSN" PYTHONPATH=src \
  python3 -m unittest tests.test_institutional_authority -v
```

Expected: authority registry and boundary tests pass, the ledger contains ordered 0000, 0001 and 0002 checksums, and teardown removes the uniquely named schema. This proves the isolated migration path only; it does not authorize or claim shared Camrui deployment.

## Versioned privilege-boundary provisioner (isolated/controlled use)

The reviewed helper is `scripts/provision_authority_boundary.py`. It accepts
only a fixed allowlist of nine M4.1 relations and the append-only event trigger
function. It does not provision credentials or identities, apply migrations,
change grants, or authorize work. The default command is read-only. The target
database credential is read only from `RIVERVIEW_AUTHORITY_DBA_DSN`; never put
the DSN on the command line, in shell history, logs, evidence, or a report. Use
the established protected secret delivery environment for an authorized DBA
session.

First inspect the target and ownership from a protected DBA session:

```sh
python3 scripts/provision_authority_boundary.py --schema riverview_authority
```

The mixed `riverview_dev` schema is intentionally out of scope and must fail
preflight because it contains unrelated application objects and its schema owner
is the runtime role. A new `riverview_authority` schema fails until migration
relations and separate owner/manager roles exist. A nonzero result is a failed
preflight, not permission to create objects by hand.
For isolated testing, provide `RIVERVIEW_TEST_PG_DSN` and run:

```sh
RIVERVIEW_TEST_PG_DSN="$RIVERVIEW_TEST_PG_DSN" PYTHONPATH=src \
  python3 -m unittest tests.test_institutional_authority_boundary -v
```

The integration test creates a uniquely named dedicated schema and disposable
roles, then removes them in teardown. It rejects unrelated objects, checks
idempotent application, relation ownership, runtime schema/table denial, scoped
manager DML, manager DDL/owner-membership denial, and fail-closed behavior when
runtime or manager can assume the schema owner. A passing isolated test is not
shared-schema commissioning.

### Interpreting preflight failures

The provisioner prints a JSON error with `status=ERROR` and a failure type. For `BoundaryPreflightError`, `detail` contains the reviewed static safety reason, such as `selected schema does not exist` or `selected schema contains non-authority objects: ...`. Database-driver failures expose only SQLSTATE; they do not print DSNs, passwords, SQL parameter values or exception text. A missing target schema is an expected stop until the dedicated schema and required roles are provisioned through the reviewed setup procedure. Do not respond to any preflight error by adding `--apply`, changing `riverview_dev`, or creating objects manually. Preserve the JSON result and correlate it with read-only catalog checks.

### Required role and ownership model

| Identity | Requirement | Authority boundary |
|---|---|---|
| DBA provisioner | PostgreSQL superuser for this narrowly selected DDL operation; protected DBA credential | Executes dry-run first; applies only reviewed allowlisted ownership changes |
| Schema owner | Distinct migration/DBA identity, not assumable by runtime or authority manager | Must not be the runtime or manager: PostgreSQL schema ownership can permit dropping contained objects |
| Runtime role | Non-superuser, no CREATEROLE/CREATEDB/BYPASSRLS; may have ordinary app schema privileges | Must not own the schema or be a member of its owner role; receives no direct authority-table privileges |
| Authority manager | Dedicated non-superuser `NOINHERIT` LOGIN with protected secret, no role memberships | `USAGE` and `SELECT`/`INSERT`/`UPDATE`/`DELETE` only on nine authority tables; no schema CREATE, table ownership or owner-role membership |
| Authority owner | NOLOGIN, non-superuser role created by the helper | Owns exactly the nine allowlisted tables and append-only trigger function; schema USAGE only for PostgreSQL FK checks; no schema CREATE |

The manager credential is a trusted authority capability: a compromised
manager can perform direct DML against authority tables and bypass application
grant checks. Table ownership, schema CREATE and owner-role inheritance are
withheld to prevent DDL/drop bypass. Keep it out of worker/CME/dashboard
runtimes and never reuse the shared runtime credential. The manager must later
be bound to the registry service through an independently verified credential
path.

`--apply` is DDL, requires a PostgreSQL superuser, and is not a harmless health
check. Never run it against `riverview_dev`: that schema contains unrelated
application objects and is owned by the runtime. Apply only to a fresh dedicated
`riverview_authority` schema after the schema-owner and manager roles, protected
manager credential delivery, protected full backup, restore rehearsal,
migration state, application compatibility, rollback procedure, and separate
service credential have been reviewed and recorded. The exact remaining
deployment prerequisites are in `RV-M4.1-001`.

After an authorized isolated apply, expected output has `status=APPLIED`, the
nine table names, runtime schema/table access `denied`, manager DML limited to
allowlisted tables, and manager DDL/owner inheritance denied. Post-recovery
checks must rerun the same test and independently confirm denied runtime SQL,
denied manager DDL, and successful exact registry authorization, then
confirm no `rvtest_*` schema or role remains:

```sh
psql "$RIVERVIEW_TEST_PG_DSN" -X -Atc \
  "SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'rvtest_%';"
psql "$RIVERVIEW_TEST_PG_DSN" -X -Atc \
  "SELECT count(*) FROM pg_roles WHERE rolname LIKE 'rvtest_%';"
```

Both counts must be `0`. If teardown fails, inspect only the uniquely generated
test names from the test log and clean only those disposable objects using a
DBA; never run broad `DROP ... CASCADE` against a shared schema. Escalate if the
schema owner is the runtime/manager, manager credential delivery is unavailable,
or a role can assume the DBA/schema-owner identity. No shared deployment was
performed by the original procedure before 2026-10-11 07:51 UTC; see the
current live addendum below.

### Manager foreign-key insert fails with schema permission denied

**Symptom:** The manager can query and directly insert into an authority table,
but inserting a credential, grant, binding, or audit event fails with SQLSTATE
`42501` and `permission denied for schema <authority_schema>`. PostgreSQL
checks referenced keys as the table owner while enforcing a foreign key. The
protected relation owner therefore needs schema `USAGE`, even though the manager
itself already has schema `USAGE` and table DML.

**Read-only diagnosis:** Connect through the protected DBA session, then inspect
owner and grants without selecting secret data:

```sql
SELECT c.relname, pg_get_userbyid(c.relowner) AS table_owner,
       has_schema_privilege(pg_get_userbyid(c.relowner), n.nspname, 'USAGE') AS owner_usage,
       has_schema_privilege(pg_get_userbyid(c.relowner), n.nspname, 'CREATE') AS owner_create
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='riverview_authority' AND c.relkind='r'
ORDER BY c.relname;
```

Expected after correction: all nine registry relations have the dedicated
NOLOGIN owner, `owner_usage=true`, and `owner_create=false`. Runtime schema
usage remains false; manager usage is true and manager create is false.
The provisioner's read-only JSON report must set `apply_required=true` if any
of these allowlisted ownership or privilege conditions is incomplete. Only a
fully compliant current state may report `apply_required=false`.

**Recovery:** Preserve a current protected backup and verify its checksum and
restore rehearsal. Run the reviewed boundary provisioner first without
`--apply`; confirm only the dedicated authority schema is selected. If the
preflight is clean, apply the idempotent boundary correction using the protected
DBA credential. It grants schema `USAGE` to the protected relation owner while
retaining no `CREATE`, manager membership, or runtime access. Do not grant
schema usage to `PUBLIC` or the runtime, and do not change relation ownership.
Repeat the manager FK-insert integration test, runtime-denial check, manager
DDL-denial check, and boundary preflight. Stop if target identity, owner, or
existing grants differ from the reviewed schema.

### Initial Steward bootstrap and restart

The first Steward bootstrap is root-local and one-time. Run only the committed,
root-owned source copy after the authority schema preflight reports
`apply_required=false`. The helper is fixed to database `riverview`, schema
`riverview_authority`, manager passfile `/etc/riverview/authority/manager.pgpass`,
and token path `/etc/riverview/authority/steward.token`; it accepts no command
arguments or caller-selected paths. It creates a 256-bit random token, writes
and fsyncs the file as `root:root 0600`, then asks the registry to persist only
the SHA-256 digest and exact initial Steward grants. The token never appears in
stdout, command arguments, logs, or PostgreSQL rows.

```sh
sudo -n env PYTHONPATH=/var/tmp/riverview-m41-source-<commit>/src \
  python3 /var/tmp/riverview-m41-source-<commit>/scripts/bootstrap_authority_steward.py
sudo -n stat -c '%U:%G mode=%a size=%s' /etc/riverview/authority/steward.token
```

Expected status is `BOOTSTRAPPED`, or `ALREADY_BOOTSTRAPPED` only when the
existing protected token authenticates the active Steward. If the process
stops after writing the token but before database commit, rerun the same helper;
it reuses the pre-persisted token. If the database result is ambiguous, preserve
the file and verify the exact `identity.manage` grant through the registry
before retrying. Never delete or replace a token after an uncertain commit.
If the helper reports an error, inspect its redacted status and PostgreSQL
availability; do not print or copy the token. Post-check that only its SHA-256
digest is stored, that the three bootstrap grants are exact institution-scoped
grants, and that manager/runtime ACL checks still pass.

**Camrui commissioning addendum, 2026-10-11:** A protected full backup and
disposable restore rehearsal passed before additive migrations and the isolated
`riverview_authority` boundary were applied to database `riverview`. The initial
boundary omitted schema `USAGE` for the NOLOGIN relation owner; manager inserts
with foreign keys then failed with SQLSTATE `42501`. The corrected provisioner
grants the owner only `USAGE`, retains `CREATE=false`, and verifies this state.
The isolated regression exercises manager inserts through credential, grant
and audit-event foreign keys. The current protected backup is
`/var/lib/postgresql/backups/riverview/m4.1/rv-m41-fk-20261011T080500Z/riverview.dump`
(SHA-256 `60ce7aa35c95871c510098b28126f6a738f63f1efde773bf9ad0a96e6f164444`,
mode 0600). It restored into disposable database
`rv_restore_m41_fk_20261011t080500z` with the recorded Core and authority counts;
that exact restore database was verified idle and removed afterward.

Commit `4276af8a8296b9c3042076a78881b2ec6d9b766e` passed CI before live use.
The corrected boundary apply returned `APPLIED`; subsequent dry-run returned
`apply_required=false`. Root-local helper returned `BOOTSTRAPPED` and a new
process returned `ALREADY_BOOTSTRAPPED`. Independent protected-file digest
verification found one matching active credential, exactly three
institution-scoped bootstrap grants, and one bootstrap event. The token file is
root:root mode 0600 and its contents were not logged. Runtime SELECT and manager
CREATE attempts both returned permission denied; manager owner membership is
false. PostgreSQL, event processor, CME monitor, notifications, dashboard and
SSH remained active. `riverview_dev` still has nine migrations, four
assignments, and eleven events. These are commissioning results for the
database boundary and initial Steward identity only; no application service
uses the authority registry yet.
- **1.0.1 — 2026-10-11:** Add observed live ownership state, limited isolated role-boundary proof, and explicit non-deployment guidance.
- **1.0.4 — 2026-10-11:** Present evidence references as readable paths supported by the dashboard's documentation-link policy.
- **1.0.3 — 2026-10-11:** Record the executed read-only Camrui role preflight and result.
- **1.0.2 — 2026-10-11:** Correct the read-only SQL example and link exact-head CI evidence.
