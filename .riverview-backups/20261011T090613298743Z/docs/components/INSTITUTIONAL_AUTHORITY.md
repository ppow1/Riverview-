<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.13
Purpose: Define durable identities, exact scoped authority, and office-state continuity
Authority: Grants are Steward-issued; absence or uncertainty denies the action
Changed: 2026-10-11 UTC | RV-M4.1-001 | Remove trailing-space Markdown hardbreaks
Changed: 2026-10-11 UTC | RV-M4.1-DB-BOUNDARY | Specify separate schema, runtime, manager, and authority-owner identities
Changed: 2026-10-11 UTC | RV-M4.1-DASHBOARD-COOKBOOK-ROUTE | Verify local dashboard documentation route for the expanded authority procedures
Changed: 2026-10-11 UTC | RV-M4.1-LEAST-PRIVILEGE | Require a dedicated registry schema and scoped manager DML without owner or schema-create access
Changed: 2026-10-11 UTC | RV-M4.1-NOINHERIT-MANAGER | Require the manager login to inherit no other database role grants
Changed: 2026-10-11 UTC | RV-M4.1-FRESH-SCHEMA-MIGRATION-LEDGER | Make authority migrations self-contained for a dedicated fresh schema
Changed: 2026-10-11 UTC | RV-M4.1-OWNER-SCHEMA-USAGE | Grant protected table owner schema USAGE for PostgreSQL FK enforcement without CREATE
Changed: 2026-10-11 UTC | RV-M4.1-BOOTSTRAP-WRITE-AHEAD | Persist bootstrap bearer before commit and support safe restart
Changed: 2026-10-11 UTC | RV-M4.1-LIVE-BOOTSTRAP-EVIDENCE | Record verified root-local live Steward bootstrap without claiming service integration
Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Specify isolated runtime exact-grant function and current deployment boundary
Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT-RECORDS | Link migration 0002 in the component migration inventory
History: Git and .riverview-backups/manifest.jsonl
-->
# Institutional identity and authority registry

**Milestone:** M4.1 — Office, occupant, implementation and state separation
**Status:** Additive live authority schema, privilege boundary, and root-local Steward bootstrap verified; service integration remains unverified
**Implementation:** `src/riverview_core/institutional_authority/registry.py`
**Migrations:** `0000_authority_migration_ledger.sql` bootstraps the checksum ledger if absent; `0001_institutional_authority.sql` creates registry tables and trigger; `0002_exact_grant_authorization.sql` creates the protected runtime exact-grant function.
**Process graph:** `rv:institutional-authority:identity-and-grants`

## Identity model

Institutional identity is durable and distinct from what currently occupies or
implements an office:

- `institutional_offices` stores the stable office role.
- `institutional_principals` stores Steward, resident, human, service and worker
  identities independently of models or processes.
- `resident_occupants` identifies the active occupant record separately from its
  principal.
- `resident_implementations` identifies a replaceable model, tool or other
  implementation with provider and revision references.
- `office_bindings` points the office to its current occupant and implementation;
  each replacement increments a binding revision and appends an audit event.
- `office_runtime_state` is keyed by office, not occupant or model. Replacing an
  occupant or implementation therefore preserves durable office state.

## Credential and grant contract

Credentials are 256-bit random bearer values returned once. PostgreSQL stores
only SHA-256 digests. The root-local initial bootstrap may accept a securely
pre-generated token so its protected file can be fsynced before the database
transaction commits; if the transaction rolls back, that token is not
authorized and can be retried. The fixed helper
`scripts/bootstrap_authority_steward.py` supports this write-ahead sequence and
resumes from the same root-only token file after interruption. Expired,
revoked, inactive, malformed and unknown
credentials fail closed. The first active Steward is created by a trusted
root-local bootstrap operation; bootstrap is one-time and is not an HTTP route.
The token must be placed in an access-controlled secret store by the operator
and must never enter logs, source, evidence, or ordinary snapshots.

After bootstrap, principal creation, office binding, grant issue/revoke, and
credential issue/revoke require the active Steward credential with the exact
management action and `institution` scope. Operational authorization requires
an active credential plus an exact `(action, scope_ref)` grant. There are no
wildcards, inherited grants, implicit role grants, or guessed fallback.
`valid_until` and credential expiration must be future timezone-aware times.
Revoking a replaced occupant's office-scoped state grants is part of the
transaction that changes the binding. The current occupant requires a separately
issued grant.

Authority and binding events are append-only. Office state writes are bounded to
64 KiB JSON objects and use an expected-revision compare-and-swap when supplied.
The registry returns `AuthorityDenied` for a negative authorization result and
`RegistryUnavailable` when it cannot obtain authoritative database state; callers
must not interpret either as permission.

## Current security boundary and deployment limitation

Camrui has the dedicated `riverview_authority` schema, protected registry
ownership, a separate manager, and the root-local Steward bootstrap described
in dated live evidence. Migration
`migrations/0002_exact_grant_authorization.sql` adds a `SECURITY DEFINER`
function which accepts only a SHA-256 credential digest, exact action, and exact
scope, and returns matching principal/grant identifiers. It uses fully
qualified authority relations, a pinned `pg_catalog, pg_temp` search path,
bounded inputs, and row locks held through the caller's transaction. It returns
no credential digest or registry rows. The boundary provisioner grants runtime
schema `USAGE` and `EXECUTE` on this one function while keeping direct table
access denied; the manager and `PUBLIC` cannot execute it.

`ExactGrantAuthorizer` calls this function on the caller's active PostgreSQL
cursor. `PostgresWorkerAdapter` requires the grant-bound bearer at worker
registration (`worker.register`) and checks `assignment.execute` or
`assignment.verify` at claim/start/action/verification for the exact scope.
Missing grants and unavailable registry fail closed. Disposable PostgreSQL
tests exercise the real function, runtime/manager ACLs, wrong action/scope,
revocation, and worker execution.

The new migration and adapter are **not yet applied/deployed on Camrui**. The
live schema currently has the previously commissioned registry/bootstrap
boundary; runtime has no execute grant on this new function, and no live worker
service consumes grants. Deployment requires the new migration checksum, a
protected pre-change backup, successful boundary dry-run/apply, and post-apply
ACL and application-path checks. M3.3 remains blocked until controlled
deployment, a real approved worker, and the separately owned real knowledge
provider are available. Direct inserts and invented authority scope strings
remain prohibited. M4.1 does not implement chat, work-order promotion, provider
routing, or the Grace director.

### Database privilege boundary package

`src/riverview_core/institutional_authority/db_boundary.py` and
`scripts/provision_authority_boundary.py` provide a DBA-operated, dry-run-first
transition for the nine authority relations, append-only trigger, and exact-
grant authorization function.
The helper rejects a runtime or authority manager that owns the selected
schema or can assume its owner role. PostgreSQL schema ownership can grant
object-drop authority independently of relation ownership. The runtime must
therefore have a distinct schema owner/migration identity; relation transfer
alone is insufficient.

The authority registry must use a dedicated schema containing only its nine
tables, its migration ledger, append-only trigger, and versioned
`authorize_exact_grant(bytea,text,text)` function. Never run the boundary helper
against a mixed application schema: it revokes broad schema access before
granting the runtime only the exact authorization function. The
manager is a dedicated non-superuser LOGIN. It receives only schema `USAGE` and
`SELECT`/`INSERT`/`UPDATE`/`DELETE` on the nine registry tables. The protected
`NOLOGIN` table owner also requires schema `USAGE` for PostgreSQL foreign-key
checks executed as relation owner; it does not receive schema `CREATE`. The
manager is `NOINHERIT`
and cannot be a member of any other database role; it cannot create objects,
drop tables, execute either protected function directly, or inherit the
`NOLOGIN` table-owner role. After migration 0002 and a successful boundary
apply, the runtime receives schema `USAGE` and function `EXECUTE` only for the
exact-grant check; authority-table and trigger access remain denied. Until that
apply, the live ACL remains in its pre-function state. The manager is still a
trusted authority capability: a
compromised manager can issue direct DML and bypass application-level grant
checks, so its secret must be isolated from worker, CME, event-processor, and
dashboard runtimes. The helper performs no identity/grant creation or work
authorization.

Camrui has an additive `riverview_authority` schema with migration ledger and
protected manager credential; the existing `riverview_dev` schema and runtime
tables remain outside the boundary. A dedicated live backup/restore rehearsal
and isolated privilege testing were completed before applying the boundary.
The root-local Steward bootstrap, protected token persistence, manager
authorization, and runtime SQL denial are verified in
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T081700Z-live-bootstrap/`. No
service uses this registry yet; live service integration, application-path
authorization, recovery and remaining component Definition of Done verification
remain open.
See the [boundary procedure](INSTITUTIONAL_AUTHORITY_COOKBOOK.md#versioned-privilege-boundary-provisioner-isolated-controlled-use).

## Interfaces

`AuthorityRegistry` provides:

- `bootstrap_steward(principal_id)` — trusted local bootstrap only; returns the
  initial bearer once.
- `create_principal(steward_token, principal_id, kind, office_id=None)` — add a
  distinct principal and return one credential once.
- `issue_credential(...)`, `revoke_credential(...)` — rotate and revoke bearer
  credentials without storing plaintext.
- `grant(...)`, `revoke_grant(...)`, `authorize(credential, action, scope_ref)` —
  exact scope checks; no authority is implied by a principal's label.
- `create_office(...)`, `create_occupant(...)`, `create_implementation(...)`,
  `bind_office(...)`, `office_snapshot(...)` — keep institutional role,
  occupant, implementation and state separate.
- `set_office_state(credential, office_id, state, expected_revision=None)` —
  persist bounded office-keyed state after an exact office-state grant.

All routines are synchronous and transactional in the selected schema. No DDL
runs at construction or service startup. Apply the versioned migration explicitly
only after backup, restore rehearsal, owner/privilege review, and a release plan.
The authority migration chain is self-contained for a fresh dedicated schema:
`0000_authority_migration_ledger.sql` creates only `schema_migrations` if absent,
then `0001_institutional_authority.sql` creates the registry. The runner records
checksums and rejects later drift. Existing schemas with a compatible ledger are
preserved; the bootstrap migration uses `IF NOT EXISTS`.

See [the focused flow](INSTITUTIONAL_AUTHORITY_FLOW.md),
[the operations cookbook](INSTITUTIONAL_AUTHORITY_COOKBOOK.md), and
[`RV-M4.1-001`](../development/M4.1-001_REVISION_RECORD.md).
