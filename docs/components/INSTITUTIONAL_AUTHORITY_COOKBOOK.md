<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.4
Purpose: Diagnose and safely recover institutional authority registry state
Authority: Read-only diagnostics first; grant changes require authenticated Steward
Changed: 2026-10-11 UTC | RV-M4.1-001 | Keep evidence references as readable paths in safe dashboard renderer
History: Git and .riverview-backups/manifest.jsonl
-->
# Institutional authority registry cookbook

**Current state:** isolated implementation only; no shared-schema migration or
live authority deployment. These queries are examples for the selected schema
after reviewed commissioning. Replace `<schema>` only with the reviewed
development schema name. Do not paste bearer values into a shell command.

## Confirm migration readiness

```sh
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT version, checksum FROM riverview_dev.schema_migrations ORDER BY version"
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT to_regclass('riverview_dev.institutional_principals') AS principals,
          to_regclass('riverview_dev.authority_grants') AS grants"
```

Expected before deployment: first query shows the current commissioned migration
chain; second query returns null for both authority relations. Do not apply the
authority migration by hand. A partial schema or checksum mismatch is a stop
condition until compared with the protected backup and official runner.

## Inspect identity and grant state (read only)

```sh
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT principal_id,principal_kind,status,created_at
     FROM riverview_dev.institutional_principals ORDER BY created_at"
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT grant_id,principal_id,action,scope_ref,granted_by,policy_ref,
          valid_from,valid_until,revoked_at
     FROM riverview_dev.authority_grants ORDER BY created_at"
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT office_id,occupant_id,implementation_id,binding_revision,updated_at
     FROM riverview_dev.office_bindings"
sudo -n -u postgres psql -d riverview -X -c \
  "SELECT office_id,revision,updated_at FROM riverview_dev.office_runtime_state"
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
- **1.0.1 — 2026-10-11:** Add observed live ownership state, limited isolated role-boundary proof, and explicit non-deployment guidance.
- **1.0.4 — 2026-10-11:** Present evidence references as readable paths supported by the dashboard's documentation-link policy.
- **1.0.3 — 2026-10-11:** Record the executed read-only Camrui role preflight and result.
- **1.0.2 — 2026-10-11:** Correct the read-only SQL example and link exact-head CI evidence.
