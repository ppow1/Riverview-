<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.33
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
Changed: 2026-10-11 UTC | RV-M4.1-LIVE-EXACT-GRANT | Record protected backup/restore, additive migration and live least-privilege verification
Changed: 2026-10-11 UTC | RV-M4.1-LIVE-STATE-COOKBOOK-CORRECTION | Make current-state banner and preflight expectations match live migration 0002
Changed: 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE-COOKBOOK-LINK-FIX | Keep evidence references readable in the dashboard's approved documentation-link scope
Changed: 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE-COOKBOOK | Record isolated exact assignment.create path and explicit live-route boundary
Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT-RECORDS | Record the post-bootstrap live migration baseline and isolated grant-check result
Changed: 2026-10-14 UTC | RV-RESIDENT-PERMISSIONS-001 | Add profile migration/read-only diagnostics and fail-closed troubleshooting
Changed: 2026-10-17 UTC | RV-M33-RETIRE-MIGRATION-001 | Document the single-migration runner, exact release layout, backup gate, and missing-0008 stop condition
Changed: 2026-10-17 UTC | RV-M33-MIGRATION-CHAIN-0008-0009 | Record exact predecessor migration effects, isolated chain evidence, and gated release sequence
Changed: 2026-10-17 UTC | M33-0008-ATOMIC-RUNTIME-ACL | Apply migration 0008 and the five-function runtime boundary atomically; document ACL checks and rollback
Changed: 2026-10-17 UTC | M33-0008-ATOMIC-RUNTIME-ACL | Clarify post-commit restore coordination and data reconciliation
Changed: 2026-10-17 UTC | M33-0008-ATOMIC-RUNTIME-ACL | Require the atomic runtime boundary runner and reuse valid backup closeout evidence
Changed: 2026-10-17 UTC | M33-0008-PRODUCTION-ACCEPTANCE | Record installed immutable runner release, migration 0008, runtime ACLs and production checks
Changed: 2026-10-17 UTC | M33-0009-PRODUCTION-CLOSEOUT | Update current-state banner to installed migration chain
History: Git and .riverview-backups/manifest.jsonl
-->
# Institutional authority registry cookbook

**Current state:** Camrui has the dedicated `riverview_authority` schema,
protected table ownership, manager credential, root-local Steward identity, and
authority migrations 0000–0009 applied with verified checksums. The profile
runtime ACL is installed. The worker-adapter assignment intake library is not
a live route; the separate M33 commissioning units remain stopped. The isolated
`AuthorizedAssignmentIntake` library checks exact `assignment.create` and binds
the grant lock to assignment/event persistence, but no live route uses it.
The low-level ledger API and direct SQL are not authorization boundaries. The
registry belongs in its separate schema; never use the mixed `riverview_dev`
application schema. Do not paste bearer or database credential values into a
shell command.

## Confirm migration readiness

```sh
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT to_regnamespace('riverview_authority') AS authority_schema,
          to_regclass('riverview_authority.schema_migrations') AS migration_ledger,
          to_regclass('riverview_authority.institutional_principals') AS principals,
          to_regclass('riverview_authority.authority_grants') AS grants"
```

Expected on the current Camrui baseline: all four objects exist and migration
0002 is recorded with the checksum in the live commissioning evidence. If the schema
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

## Assignment-create authorization boundary (isolated; not live route)

The application library `src/riverview_core/assignment_intake.py` exposes
`AuthorizedAssignmentIntake.create`. It requires an exact active
`assignment.create` grant for the supplied authority reference, derives the
actor from the database authorization result, and keeps the grant-row lock open
through assignment and `assignment.created` event persistence in the same
transaction. Missing, revoked, wrong-scope, or unavailable authority must fail
closed before persistence. The caller cannot supply an actor identity.

This is not yet wired to a browser, resident, API, or worker service. Do not
create live assignments through raw `PostgresLedger.create`, direct SQL, or by
manufacturing a scope/grant. The four passing isolated integration tests are recorded in
`evidence/checkouts/M3.3-ASSIGNMENT-INTAKE/acceptance.json` (repository evidence
path; evidence files are not served through the dashboard documentation route).

For an isolated regression, configure `RIVERVIEW_TEST_PG_DSN` only with a
throwaway PostgreSQL test database and run:

```bash
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<disposable PostgreSQL test database DSN>' \
  python3 -m unittest tests.test_assignment_intake -v
```

Expected: 4 tests pass, zero skips; each unique `rvtest_*` schema is removed.
A missing DSN is a skipped test and is not verification. The test requires a
PostgreSQL test role able to create isolated schemas and apply the versioned
migrations; never point it at Camrui's shared `riverview` database.

If intake raises `AssignmentIntakeDenied`, preserve the denial and verify the
request's exact authority reference against an authorized Steward-issued grant;
do not widen scope or retry with a guessed identity. If it raises
`AssignmentIntakeUnavailable`, treat authority as unknown, perform no fallback
write, and diagnose the authority function/registry/database dependency using
the read-only checks above. Post-recovery, rerun the isolated test suite and
confirm assignment/event counts are unchanged in the intended live database
before any separately authorized deployment. Escalate any unexpected persisted
row, lock timeout, credential exposure, or disagreement between grant identity
and actor attribution.

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

## M33 retirement event migration 0009 (fixed scope)

Camrui's active core path is `/opt/riverview-core`, a symlink directly to
`/opt/riverview/releases/<source-commit>`; there is no `/opt/riverview-core/current`.
Keep that active pointer and the separate `/opt/riverview-m33/current` pointer
unchanged for the one-shot registration retirement. Install the approved
committed package as a new root-owned directory under `/opt/riverview/releases/`
using the immutable package procedure in `RUNTIME_BASELINE.md`; retain the old
release and invoke the tools by their versioned release path. Reuse the existing
interpreter `/opt/riverview-core/.venv/bin/python`. Do not run
`deploy/install_baseline.sh`: it changes the baseline unit and starts a service.

Migration `0009_worker_registration_retirement_event.sql` is checksum-pinned
to `0b5aa767a0209b22ec476721da02c47618443ee1b06e752aa1e416f6dbccaef6` and its
source declares dependencies `0001` through `0008`. The production runner
`scripts/apply_m33_retirement_migration.py` is deliberately narrower than the
generic migration sweep. It accepts no caller-selected database or schema,
verifies exactly the source inventory and checksums for migrations `0000`–`0008`,
requires the authority ledger to contain that exact ordered predecessor chain,
and refuses missing, drifted, already-unexplained, or later migration rows. It
applies only 0009 in one transaction. Before and after, it compares all
authority schema/relation ownership and ACLs plus every authority table row
count; the sole allowed data-count delta is the single migration-ledger row.
The SQL itself only expands the authority-event `event_type` check constraint;
it creates no role, grant, table, or worker registration change.

Before an authorized shared-database apply, follow the PostgreSQL ledger
cookbook: verify target identity and migration source hashes, create a new
protected full custom-format backup outside the repository, verify its digest
and `pg_restore --list`, restore it to a unique disposable database, and compare
authority/Core counts and ACLs. Do not overwrite or remove prior backups. The
fixed helper has separate modes; use its 0008 modes only after the execution
gate in the next section is authorized. Its existing 0009 modes remain separate.

```sh
sudo -n -u postgres env PYTHONPATH=/opt/riverview/releases/<approved-commit>/src \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview/releases/<approved-commit>/scripts/apply_m33_retirement_migration.py --check-0008
sudo -n -u postgres env PYTHONPATH=/opt/riverview/releases/<approved-commit>/src \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview/releases/<approved-commit>/scripts/apply_m33_retirement_migration.py --apply-0008
```

`--check-0008` is read-only. `--apply-0008` applies only 0008 and, before the
same outer transaction commits, invokes the established
`provision_authority_boundary` operation and verifies its exact postconditions.
The SQL bytes and migration checksum are unchanged. The transaction checks the
exact 0000–0007 ledger, reviewed 0008 and dependent 0009 hashes, expected
object/seed state, and pre-existing data/ownership; it transfers the new profile
objects to `riverview_authority_owner`, retains the established manager DML
boundary on allowlisted authority tables, preserves runtime schema `USAGE`
without `CREATE`, and grants the runtime only the five reviewed permission
functions. It revokes `PUBLIC` execution and denies function execution to the
manager. Any failed role, ownership, ACL, object, seed, or ledger postcondition
rolls the whole transaction back, including the ledger insert and grants. The
idempotent check path for an already-applied 0008 refuses to proceed if the
runtime boundary is missing or drifted; it does not repair a committed partial
deployment.

The active Grace execution source calls
`riverview_authority.evaluate_resident_permission(TEXT,TEXT,TEXT,TEXT,TEXT,BOOLEAN)`
after each exact-grant decision. The active dashboard additionally uses the
profile list, save, approve, and revoke APIs. Therefore all five function
signatures in `db_boundary.RUNTIME_PERMISSION_SIGNATURES` are required for the
shared `riverview_core` role. Runtime table DML remains denied. The current
production schema already has `USAGE` (not `CREATE`) for runtime, manager, and
owner; `riverview_core`, manager, and owner have no role memberships; existing
authority tables and exact-grant functions satisfy their established owner and
function-only boundary. These are read-only production observations; the new
function privileges have only been validated in isolated PostgreSQL.

After installing the reviewed immutable release, the authorized execution
sequence is:

```sh
release=/opt/riverview/releases/<approved-full-commit>
sudo -n -u postgres env PYTHONPATH="$release/src" \
  /opt/riverview-core/.venv/bin/python \
  "$release/scripts/apply_m33_retirement_migration.py" --check-0008
# Require READY, the exact approved checksum, and the protected backup gate.
sudo -n -u postgres env PYTHONPATH="$release/src" \
  /opt/riverview-core/.venv/bin/python \
  "$release/scripts/apply_m33_retirement_migration.py" --apply-0008
```

The apply command performs migration SQL, checksum-ledger insert, object
ownership transfer, ACL provisioning, and postflight within one transaction.
No service restart is needed: before commit, active sessions see the legacy
exact-grant-only path; after commit, every new profile object and its runtime
function boundary become visible together. A lock, permission, or postcondition
failure aborts the transaction; do not follow it with standalone `GRANT` SQL or
an unrestricted migration runner.

Read-only postflight (as the PostgreSQL administrator) must return five rows
with owner `riverview_authority_owner`, runtime `EXECUTE=true`, manager
`EXECUTE=false`, and `PUBLIC EXECUTE=false`; it also verifies the runtime can
use but cannot create in the schema and cannot read profile tables:

```sh
sudo -n -u postgres psql -X -v ON_ERROR_STOP=1 -P pager=off -d riverview <<'SQL'
BEGIN READ ONLY;
SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS signature,
       p.proowner::regrole::text AS owner,
       has_function_privilege('riverview_core',p.oid,'EXECUTE') AS runtime_execute,
       has_function_privilege('riverview_authority_manager',p.oid,'EXECUTE') AS manager_execute,
       EXISTS (SELECT 1 FROM aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) a
               WHERE a.grantee=0 AND a.privilege_type='EXECUTE') AS public_execute
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='riverview_authority'
  AND p.proname IN ('list_resident_permission_profiles',
    'save_resident_permission_profile','approve_resident_permission_profile',
    'revoke_resident_permission_profile','evaluate_resident_permission')
ORDER BY p.proname;
SELECT has_schema_privilege('riverview_core','riverview_authority','USAGE') AS runtime_schema_usage,
       has_schema_privilege('riverview_core','riverview_authority','CREATE') AS runtime_schema_create,
       has_table_privilege('riverview_core','riverview_authority.resident_permission_profiles','SELECT') AS runtime_profile_table_select;
SELECT version,checksum FROM riverview_authority.schema_migrations
WHERE version='0008_resident_permission_profiles';
ROLLBACK;
SQL
```

Expected: the five rows exactly match the allowlist; runtime `USAGE=true`,
`CREATE=false`, profile table `SELECT=false`, and the ledger checksum equals
`570c7aeb16fca04c64c4e010f1534d0efebe92628ddacd8f05f6eb1eda12d339`.
Do not treat a successful migration process exit alone as acceptance.

If the runner fails before commit, PostgreSQL transaction rollback removes all
0008 DDL, the checksum row, and ACL changes; retain the structured failure and
do not rerun until its cause is corrected and a fresh exact preflight passes.
After a successful commit, 0008 has no down migration. Do not drop objects or
delete ledger rows. Prefer a separately reviewed forward correction for a
post-commit integrity defect. Restoring the whole protected database backup is
not an in-place rollback: it requires a separately authorized recovery window,
service coordination, and reconciliation of all writes made after the backup
snapshot. Do not restore automatically or claim a post-commit failure can be
transactionally rolled back; use the incident recovery plan and preserve
current evidence first.
The exact code check/apply commands for 0009 from a versioned release are:

```sh
sudo -n -u postgres env PYTHONPATH=/opt/riverview/releases/<approved-commit>/src \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview/releases/<approved-commit>/scripts/apply_m33_retirement_migration.py --check
sudo -n -u postgres env PYTHONPATH=/opt/riverview/releases/<approved-commit>/src \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview/releases/<approved-commit>/scripts/apply_m33_retirement_migration.py --apply
```

`--check` is read-only. `--apply` requires OS user `postgres`, local peer access
to only database `riverview`, fixed schema `riverview_authority`, the exact
reviewed SQL checksum, the exact prior ledger, and no unrelated migration
files. The runbook's supplied production ledger observation is `0000`–`0007`;
because 0009 declares 0008 as a predecessor, the expected result is a
fail-closed `prior_migrations_missing_or_unrelated_pending`. Do not apply 0009
or run the retirement helper until 0008 is applied and the exact chain is
verified.

### Migration 0008 effect and production preparation gate

The Steward authorized preparation and isolated validation only. Migration
`0008_resident_permission_profiles.sql` has SHA-256
`570c7aeb16fca04c64c4e010f1534d0efebe92628ddacd8f05f6eb1eda12d339` and
depends on migrations 0001–0007. It is additive: nine tables
(`capability_catalog`, `resource_catalog`, `capability_resources`,
`resident_permission_tiers`, `resident_permission_profiles`,
`resident_permission_profile_drafts`, `resident_permission_tier_rules`,
`resident_permission_rules`, `resident_permission_events`); two explicit
indexes; six functions (five resident-profile APIs plus the append-only event
trigger function); one append-only trigger; and one migration-ledger row. It
seeds four permission tiers, 18 capability metadata rows, 11 resource metadata
rows, 26 capability/resource bindings, and 50 inherited tier-default rules.
The migration leaves resident profiles, drafts, resident-specific rules, and
profile audit events empty. It does not modify/delete any pre-existing row,
grant authority or credentials, activate a profile, or change service
configuration. Its only pre-existing data change is appending its checksum to
`schema_migrations`.

The five profile API functions revoke `PUBLIC` EXECUTE and pin their
`SECURITY DEFINER` search paths. 0008 does not grant them to runtime or manager
roles. `ExactGrantAuthorizer` detects the paired profile objects and calls
`evaluate_resident_permission`; with no resident profile this returns the
legacy exact-grant-only result, but only if the runtime has the required
function EXECUTE privilege. The corrected 0008 runner must invoke the existing
`provision_authority_boundary` within the same transaction and verify its
postconditions before commit. Use only that reviewed atomic path; never issue a
standalone grant or apply the broader provisioner separately. If the corrected
runner is not installed, its role/schema preflight fails, or any ACL check
drifts, stop before commit. The manager's worker-registry UPDATE privilege is
a separate retirement-helper precondition and is not granted by 0008.

Only after explicit production-execution authorization, the sequence is:

1. Merge the reviewed atomic-runtime-boundary correction after exact-head
   controlled CI. Build from its exact integrated commit, verify the package
   manifest, and install to a new
   root-owned immutable `/opt/riverview/releases/<full-commit>` directory.
   Camrui's `/opt/riverview-core` is a direct symlink to a release; preserve
   the existing 64e8 release and do not invent a `/current` subdirectory,
   switch pointers, or restart services. Use the existing
   `/opt/riverview-core/.venv/bin/python` for one-shot commands.
2. Verify host/database/schema identity; require the exact 0000–0007 ledger
   and source checksums; verify 0008 and 0009 source checksums and ensure no
   extra migration source or ledger entries exist.
3. Verify the existing protected backup/restore closeout is for this same
   production database and predates the migration, and confirm no database
   writes or migration-state changes invalidate it. Reuse that evidence if it
   remains applicable; otherwise create and verify a new protected backup and
   disposable restore before proceeding. Stop on any discrepancy.
4. Under separate execution authorization, apply only 0008 with the fixed
   `apply_m33_retirement_migration.py --apply-0008` mode. In one transaction it
   checks the exact 0000–0007 ledger and 0008/0009 checksums, applies 0008,
   records only the 0008 checksum, and runs the established authority boundary
   provisioner before commit. This transfers profile objects to the protected
   owner, preserves manager DML scope, and grants runtime access to exactly the
   five audited profile functions while denying PUBLIC execution and runtime
   table DML. A failed ACL check rolls the migration back. Do not invoke a
   general migration sweep.
5. Verify the 0000–0008 ledger and checksum, all five owner/runtime/manager/
   PUBLIC function ACLs, schema `USAGE`/no-`CREATE`, no runtime profile-table
   access, expected seed counts, and empty resident profiles/drafts/rules/events.
   The installed runtime and dashboard code have been checked for these
   function dependencies; no service restart is required because DDL and ACL
   become visible together at commit.
6. Run `apply_m33_retirement_migration.py --check`; it must report `READY` on
   the exact 0000–0008 chain. Applying 0009 and retiring registrations each
   require their own explicit execution authorization and the existing
   guarded helper's prerequisites.
7. These migrations are additive; do not drop objects or edit ledger rows as
   rollback. Preserve the pre-migration release and backup. If failure occurs,
   stop writes and preserve evidence; restore the verified backup only under
   a separately authorized recovery decision. This plan does not switch
   service pointers or restart services.

For the one-shot utility package, build only from a clean, reviewed, committed
checkout with the existing package builder and verifier. Transfer the archive
through the established Windows `camrui` SSH alias. On Camrui, verify the
archive hash and package checksum manifest, then extract to a previously
nonexistent `/opt/riverview/releases/<commit>` directory, owned by root and
read-only to service accounts. Retain `/opt/riverview-core` at its existing
direct symlink target and leave `/opt/riverview-m33/current` and all service
units unchanged. Invoke the candidate's scripts by that exact versioned path;
use the existing interpreter at `/opt/riverview-core/.venv/bin/python`. This
installs the one-shot tool without activating new code for any running service.

The controlled Windows packaging commands are:

```powershell
$commit = (git rev-parse HEAD).Trim()
$archivePath = Join-Path $env:TEMP ("riverview-m33-retirement-" + $commit + ".tar.gz")
python scripts/build_camrui_package.py $archivePath
python scripts/verify_camrui_package.py $archivePath
scp $archivePath ("camrui:/var/tmp/riverview-m33-retirement-" + $commit + ".tar.gz")
```

After the local verifier reports the intended committed source and the archive
SHA-256 has been recorded, the authorized Camrui operator installs into a fresh
versioned directory as follows. Substitute only the verified full commit and
archive digest; do not change `current` or `/opt/riverview-core`:

```sh
commit=<verified-40-character-commit>
archive="/var/tmp/riverview-m33-retirement-${commit}.tar.gz"
release="/opt/riverview/releases/${commit}"
expected_sha256=<verified-archive-sha256>
test "$(sudo -n sha256sum "$archive" | cut -d' ' -f1)" = "$expected_sha256"
sudo -n test ! -e "$release"
sudo -n install -d -o root -g root -m 0755 /opt/riverview/releases
stage=$(sudo -n mktemp -d /opt/riverview/releases/.m33-retirement-XXXXXXXX)
sudo -n tar -xzf "$archive" --no-same-owner --no-same-permissions -C "$stage"
sudo -n chown -R root:root "$stage"
sudo -n chmod -R a+rX "$stage"
sudo -n chmod -R go-w "$stage"
sudo -n sh -c "cd '$stage' && sha256sum --check --strict PACKAGE_SHA256SUMS"
test "$(sudo -n cat "$stage/SOURCE_COMMIT")" = "$commit"
sudo -n mv "$stage" "$release"
```

The package and new release remain available for audit; the existing immutable
release and active symlink remain unchanged. If any check fails, do not rename
the staging directory into a release and do not run a candidate script.

Historical preflight note (superseded 2026-10-17): the production ledger was
0000–0007. The approved 0008 and 0009 migrations have since been applied and
verified against their exact checksums after protected backup/restore. Do not
reapply either migration. The M33 registration-retirement helper was attempted
once and failed closed on the manager authorization boundary; see the dated
production closeout below.


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

Historical read-only preflight on 2026-10-11: `current_user=postgres` for the
diagnostic; `riverview_dev` and its application tables were owned by
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

That early feasibility experiment is superseded by the dedicated schema,
versioned provisioner and live migration 0002/function-only ACL recorded below.
The current live evidence is still limited to the database authorization
boundary: no worker service consumes it and no live assignment grant has been
created. Do not manually create operational grants or use `riverview_dev` for
authority records. Any further migration requires a fresh protected
backup/restore rehearsal and must prove runtime table access remains denied.

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

## Exact-grant runtime function — isolated result and live preflight

Migration `0002_exact_grant_authorization.sql` creates
`riverview_authority.authorize_exact_grant(bytea,text,text)`. It is
`SECURITY DEFINER`, has a fixed `pg_catalog, pg_temp` search path, uses
fully-qualified relation names, locks credential/principal/grant rows for the
caller's transaction, bounds arguments, and returns only principal and grant
IDs. Migration 0002 revokes default `PUBLIC` execute. The boundary helper then
transfers function ownership to the NOLOGIN table owner, revokes execution from
the manager and PUBLIC, and grants the runtime only schema USAGE plus this
function's EXECUTE privilege. Direct authority-table access remains denied.

The shared Camrui state was checked read-only before migration on 2026-10-11 with:

```sh
sudo -n -u postgres psql -X -P pager=off -d riverview -c \
  "SELECT version,checksum FROM riverview_authority.schema_migrations ORDER BY version; SELECT to_regprocedure('riverview_authority.authorize_exact_grant(bytea,text,text)') AS exact_grant_function; SELECT has_schema_privilege('riverview_core','riverview_authority','USAGE') AS runtime_schema_usage"
```

At that pre-deployment check, migration entries were `0000_authority_migration_ledger`
(`8043b6f310f98e8e9613abbec71befcb4e3734d6fb374c36c6ccafe36b965fd6`) and
`0001_institutional_authority`
(`347e415b662675d492400a0af145edc9ca92e5122ee3e22886d9656b578fad36`). The
function was absent and runtime schema USAGE was false. The later deployment
and its independently checked result are recorded below.

The function, runtime/manager ACL and worker integration were exercised on a
disposable PostgreSQL 16.15 socket-only cluster using:

```sh
RIVERVIEW_TEST_PG_DSN='host=/tmp/rv-m41-authcheck-pg port=55441 dbname=riverview_test user=admin1' \
  PYTHONPATH=src python3 -m unittest \
    tests.test_institutional_authority_boundary tests.test_worker_adapter \
    tests.test_cme_monitor -v
```

Result: 22 tests passed, no failures/errors/skips. Coverage includes exact grant
success, wrong action/scope, revoked credentials, registration denial, worker
denial after revocation, manager function denial, runtime table denial, and
existing concurrent/recovery monitor behavior. This was isolated verification
only; it did not prove Camrui runtime ACL or deployed-worker behavior. The
subsequent live database result is recorded below; the worker adapter itself
remains undeployed in a service.

**Executed safe deployment sequence:** create a new protected full `riverview` backup
under the PostgreSQL-owned backup parent; restore it to a uniquely named
disposable database and compare Core/authority counts and ACLs; verify packaged
migration bytes and checksum; apply only authority migration 0002; run the
boundary helper read-only and confirm it selects exactly `riverview_authority`;
only then apply the boundary grant; verify as `riverview_core` that the exact
function succeeds for a known test grant while all nine tables and the trigger
remain inaccessible; verify as manager that function execution is denied; then
rerun the helper read-only expecting `apply_required=false`. Keep `riverview_dev`,
the M1.1 runtime, event processor, monitor, dashboard and SSH unchanged. If the
migration checksum, schema inventory, owners or preflight differs, stop without
applying. Do not drop migration 0002 or the authority schema to roll back; retain
the function and revoke only the exact runtime function/schema grants through a
reviewed restoration procedure if a post-apply check fails.

**Camrui exact-grant commissioning, 2026-10-11:** Exact source commit
`36622e573f9e030aba909967be76fc4cd646b620` passed controlled-checkout CI run
`38126965396`. A fresh protected backup was stored at
`/var/lib/postgresql/backups/riverview/m4.1/rv-m41-exact-grant-20261011T090346Z/riverview.dump`
(postgres:postgres, mode 0600, 97,847 bytes, SHA-256
`f25af3984fa29f7f0a035c9fc0b01a6086e9eadbcb3b26ea77f2a7181255e4c7`). Its
custom archive listed successfully and restored to a unique disposable database
with nine Core migrations, two authority migrations, four assignments, eleven
events, and ten authority relations. That database was removed and verified
absent. Only after restore verification, a root-owned package extracted from
the exact commit applied migration 0002 and the reviewed boundary helper. The
first preflight returned `apply_required=true`; apply returned `APPLIED`; repeat
migration returned no pending steps and postflight returned
`apply_required=false`. Live SQL confirms migration checksum
`84be0433c2e603875489a3e4311199f19b97eddc6a5ec55eef6dd47010cb091d`, function
owner `riverview_authority_owner`, fixed search path, runtime `EXECUTE=true`,
manager `EXECUTE=false`, runtime schema USAGE=true/CREATE=false, and direct
runtime table SELECT=false. A transaction-only runtime-role check allowed one
exact grant, denied another action, denied direct table read, and denied manager
function execution; all synthetic authority rows were rolled back and absence
was confirmed. PostgreSQL, event processor, CME monitor, notification
dispatcher, dashboard and SSH remained active; `riverview_dev` retained nine
migrations, four assignments, and eleven events. The root-owned package remains
at `/var/tmp/riverview-m41-source-36622e5`. Full outputs and checksums are in
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T090700Z-live-exact-grant/`.
This dated paragraph records the live database function/ACL commissioning at
that time. Subsequent isolated engineering added the application-level
`AuthorizedAssignmentIntake` boundary, documented above; it is not deployed or
used by a live route. A commissioned real worker and the external real
knowledge provider remain unavailable.

- **1.0.22 — 2026-10-11:** Keep the repository evidence path readable without an unsupported dashboard hyperlink.
- **1.0.21 — 2026-10-11:** Document isolated exact assignment-create authorization, failure handling, regression command, and the still-undeployed live route.
- **1.0.20 — 2026-10-11:** Correct cookbook current-state banner and distinguish historical pre-deployment checks from live exact-grant commissioning.
- **1.0.19 — 2026-10-11:** Record live additive exact-grant deployment after protected backup/restore and runtime role checks; retain worker/assignment/provider gates.
- **1.0.18 — 2026-10-11:** Record the live authority migration baseline and exact-grant isolated test result; define safe deployment sequencing.
- **1.0.1 — 2026-10-11:** Add observed live ownership state, limited isolated role-boundary proof, and explicit non-deployment guidance.
- **1.0.4 — 2026-10-11:** Present evidence references as readable paths supported by the dashboard's documentation-link policy.
- **1.0.3 — 2026-10-11:** Record the executed read-only Camrui role preflight and result.
- **1.0.2 — 2026-10-11:** Correct the read-only SQL example and link exact-head CI evidence.

## Resident permission profile diagnostics (read-only)

The resident permission migration and Steward view described here are source
only. Do not infer that migration 0008 or its runtime function ACL is live until
an approved commissioning verifies its exact checksum and protected function
permissions. Do not run any migration in this development increment.

After approved commissioning, inspect profile metadata and audit events through
a DBA read-only transaction. These queries do not read credentials or Grace
conversation content:

```sh
sudo -n -u postgres psql -d riverview -X -v ON_ERROR_STOP=1 -c \
  "BEGIN READ ONLY; SELECT version,checksum FROM riverview_authority.schema_migrations WHERE version='0008_resident_permission_profiles'; SELECT principal_id,office_id,tier_id,status,revision,classification_ceiling,export_mode,approved_by,approved_at FROM riverview_authority.resident_permission_profiles ORDER BY principal_id; SELECT principal_id,capability_id,resource_id,effect,access_level,approval_required,data_classification,export_mode,valid_until,revoked_at FROM riverview_authority.resident_permission_rules ORDER BY principal_id,capability_id,resource_id,created_at; SELECT principal_id,actor_id,event_type,profile_revision,recorded_at FROM riverview_authority.resident_permission_events ORDER BY recorded_at,event_id; COMMIT;"
```

Expected: 0008 has the release-manifest checksum; the runtime cannot directly
read profile/catalog/audit tables; it can execute the five profile functions,
and the manager cannot execute those functions. If the dashboard reports
`resident_permission_registry_unavailable`, compare the checksum, function
owner and pinned `search_path`, runtime `EXECUTE`, and manager denial with the
`provision_authority_boundary.py --dry-run` report. Never grant runtime table
access or repair ACLs with ad hoc SQL.

For an effective action denial, inspect the exact `(principal, action, scope)`
grant first, then the active profile revision, resource rule, expiry,
classification/export restriction, and approval hold. A pending draft does not
change effective policy. A stale revision returns HTTP 409; reload and
re-review before saving. An offline, busy, degraded, or unknown resource is a
readiness/capacity condition, not an authorization decision. Resume only after
rechecking both the exact grant and the current profile revision.

## M33 0008 production acceptance — 2026-10-17

PR #78 merged the atomic runtime-ACL correction at integration commit
`3f1b38ceb8460fa1fefa10094d2d04676e3b6f02`. The verified immutable runner
release is installed at
`/opt/riverview/releases/3f1b38ceb8460fa1fefa10094d2d04676e3b6f02` with
package SHA-256
`47f4d34b02e9d73ab35cd2cce3af56060753add37d189d243a00e84ff3b0d19c`.
It was invoked from this versioned path; `/opt/riverview-core` remains pointed
to the prior `64e8f14ad6d71102a864755739a1c8a61506235c` release and no service
was restarted or release pointer switched.

The preflight returned `READY`; `--apply-0008` returned `APPLIED`, and the
postflight `--check-0008` returned `ALREADY_APPLIED` with the pinned checksum
`570c7aeb16fca04c64c4e010f1534d0efebe92628ddacd8f05f6eb1eda12d339`. At this 0008 acceptance checkpoint the
ledger contained 0000–0008; 0009 was applied later as recorded below. All five profile API
functions are owned by `riverview_authority_owner`, executable by
`riverview_core`, and not executable by `PUBLIC` or the manager. Runtime schema
USAGE is present without CREATE; profile table access remains denied to the
runtime. Manager profile table SELECT/UPDATE remains scoped. All profile,
draft, resident-rule, and profile-event tables are empty. A read-only evaluator
call as `riverview_core` returned `legacy_exact_grant_only`.

The Grace execution, dashboard, event processor, CME monitor, and notification
dispatcher remained active. A strict-CA TLS GET of `https://192.168.1.155/`
returned HTTP 200 with certificate verification result 0. The running core
release pointer is unchanged. Production evidence is in
`evidence/checkouts/M33-0008-PRODUCTION/20261017T025938Z/production-acceptance.json`.
The protected backup closeout is PASS and its archive digest and `pg_restore`
listing were verified. The earlier failed preliminary schema-comparison record
remains preserved alongside the later PASS closeout; see the evidence's
`backup-applicability.txt` for that discrepancy and chronology. Migration 0008
has no down migration; do not restore a whole-database backup without separate
recovery authorization and post-snapshot write reconciliation.

- **1.0.23 — 2026-10-14:** Add source-only resident profile migration diagnostics and explicit runtime/manager function-only ACL expectations.
- **1.0.26 — 2026-10-17:** Make authority 0008 DDL, owner transfer, five-profile-function runtime grants, and ACL postconditions atomic; document exact live role/schema baseline and recovery.
- **1.0.27 — 2026-10-17:** Clarify whole-database restore after committed 0008 requires an authorized recovery window and reconciliation of post-backup writes.
- **1.0.28 — 2026-10-17:** Require the corrected atomic runtime boundary in the 0008 runner and allow reuse of applicable verified backup evidence.
- **1.0.29 — 2026-10-17:** Record Camrui migration 0008 production execution, function ACL postflight, service continuity, and the installed non-active release.


### M33-0009 production closeout (2026-10-17)

Production authority migration 0009 is applied and verified. The ledger contains 0000–0009 with expected checksums, including `0009_worker_registration_retirement_event` SHA-256 `0b5aa767a0209b22ec476721da02c47618443ee1b06e752aa1e416f6dbccaef6`. It only extends the authority event type constraint. It does not retire registrations or change grants.

The separately authorized guarded helper failed closed with `InsufficientPrivilege`. The manager role has no `USAGE` on `riverview_dev`, no `SELECT` on `worker_registry`, and no table or column `UPDATE`. No fallback role or ad hoc grant was used, so the worker registry and authority event history were unchanged. The active-release pointer was not changed. Before resuming retirement, establish and review a narrow authorized execution boundary; do not grant these broad schema/table privileges merely to satisfy the helper.
