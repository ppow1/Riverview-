<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Diagnose and safely recover institutional authority registry state
Authority: Read-only diagnostics first; grant changes require authenticated Steward
Changed: 2026-10-11 UTC | RV-M4.1-001 | Initial authority troubleshooting procedures
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
