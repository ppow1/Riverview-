<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.25
Purpose: Define durable identities, exact scoped authority, and office-state continuity
Authority: Grants are Steward-issued; absence or uncertainty denies the action
Changed: 2026-10-11 UTC | RV-M4.1-001 | Remove trailing-space Markdown hardbreaks
Changed: 2026-10-11 UTC | RV-M4.1-DB-BOUNDARY | Specify separate schema, runtime, manager, and authority-owner identities
Changed: 2026-10-11 UTC | RV-M4.1-DASHBOARD-COOKBOOK-ROUTE | Verify local dashboard documentation route for the expanded authority procedures
Changed: 2026-10-11 UTC | RV-M4.1-LEAST-PRIVILEGE | Require a dedicated registry schema and scoped manager DML without owner or schema-create access
Changed: 2026-10-11 UTC | RV-M4.1-NOINHERIT-MANAGER | Require the manager login to inherit no other database role grants
Changed: 2026-10-11 UTC | RV-M4.1-FRESH-SCHEMA-MIGRATION-LEDGER | Make authority migrations self-contained for a dedicated fresh schema
Changed: 2026-10-11 UTC | RV-M4.1-OWNER-SCHEMA-USAGE | Grant protected table owner schema USAGE for PostgreSQL FK enforcement without CREATE
Changed: 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE | Document isolated atomic exact assignment.create application boundary and live-route limitation
Changed: 2026-10-11 UTC | RV-M3.3-GOVERNED-INTAKE-ROUTE | Document bounded loopback request API and isolated exact-grant route evidence
Changed: 2026-10-11 UTC | RV-M4.1-BOOTSTRAP-WRITE-AHEAD | Persist bootstrap bearer before commit and support safe restart
Changed: 2026-10-11 UTC | RV-M4.1-LIVE-BOOTSTRAP-EVIDENCE | Record verified root-local live Steward bootstrap without claiming service integration
Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT | Specify isolated runtime exact-grant function and current deployment boundary
Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT-RECORDS | Link migration 0002 in the component migration inventory
Changed: 2026-10-11 UTC | RV-M4.1-BOUND-OCCUPANT-WRITE | Require the current occupant identity as well as an exact office-state grant
Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Add runtime-safe exact-grant office snapshot and state API
Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Distinguish live migration checksums from isolated migration 0003
Changed: 2026-10-11 UTC | RV-M4.1-LIVE-EXACT-GRANT | Record deployed migration and function-only runtime ACL
Changed: 2026-10-11 UTC | RV-M4.1-MIGRATION-CONTRACT-CURRENT-STATE | Document checksum ledger/registry/function migration order
Changed: 2026-10-11 UTC | RV-M4.1-GRACE-BOOTSTRAP-STATUS | Clarify historical M3.3 blockers and current additive Grace identity bootstrap work
Changed: 2026-10-11 UTC | RV-M4.1-GRACE-IDENTITY-COMMISSIONING | Document the live fixed-identity bootstrap and exact grant result
Changed: 2026-10-11 UTC | RV-M3.3-STATUS-RECONCILIATION | Correct current summary text superseded by later M3.3 live commissioning
Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Add exact-grant check for linked authenticated account principals
Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Specify explicit continuity opt-in on audited implementation CAS and its least-privilege runtime query
History: Git and .riverview-backups/manifest.jsonl
-->
# Institutional identity and authority registry

**Milestone:** M4.1 — Office, occupant, implementation and state separation
**Status:** Additive live authority schema, privilege boundary, and root-local Steward bootstrap verified; service integration remains unverified
**Implementation:** `src/riverview_core/institutional_authority/registry.py`
**Migrations:** `0000_authority_migration_ledger.sql` bootstraps the checksum ledger if absent; `0001_institutional_authority.sql` creates registry tables and trigger; `0002_exact_grant_authorization.sql` creates the protected runtime credential exact-grant function; `0003_resident_office_state_api.sql` adds resident snapshot and compare-and-swap state functions; `0004_exact_principal_grant_authorization.sql` adds an exact-grant check for a principal established by a separately authenticated, linked Riverview account session.
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
issued grant. Both resident authorization and each office-state write also
compare the grant principal with the currently bound occupant principal under a
binding-row lock. Reissuing an exact grant to a former occupant cannot restore
its authority. This identity check occurs before resident knowledge/provider
calls and again in the state-write transaction, so replacement races fail
closed.

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

Migration 0002 and its function-only ACL are deployed on Camrui from exact
source `36622e573f9e030aba909967be76fc4cd646b620`, after a protected backup and
disposable restore rehearsal. The runtime can execute only the exact grant
function and cannot directly access authority tables. A rollback-only live
runtime-role transaction verified exact allow, wrong-action deny, table-read
deny and manager-function deny. Evidence:
`evidence/checkouts/M4.1-DB-BOUNDARY/20261011T090700Z-live-exact-grant/`.
The worker adapter code is not yet installed in a worker service. The isolated
`AuthorizedAssignmentIntake` application entry point now checks exact
`assignment.create` and atomically holds the matching grant lock across
assignment/event persistence; tests verify grant denial, attribution, replay,
and fail-closed registry errors. This does not change the lower-level
`PostgresLedger.create` persistence API or prevent direct SQL writes. Every
application route must use the authorized intake. A bounded loopback HTTP
adapter now connects `POST /api/v1/assignments` to that intake; it rejects
non-loopback binds, applies request-size and field limits, accepts a bearer only
in the Authorization header, and emits no payload or credential in logs. Its
isolated PostgreSQL HTTP test verifies denied requests have no rows, an
authorized request persists Steward attribution and the created event, and an
idempotent retry adds no duplicate. The `riverview-assignment-intake.service`
unit reserves loopback port 8768; live installation/commissioning remains
unverified. Earlier M3.3 isolated engineering added the read-only
`RepositoryKnowledgeProvider` and worker tests. Later live commissioning and
waiting-assignment isolation evidence in the current milestone status below and
`docs/development/M3.3-001_REVISION_RECORD.md` supersede the precommissioning
limitation recorded in this section's history. The live governed route,
authorized worker, repository provider, artifact, separate verifier, PostgreSQL
persistence, restart recovery, and dashboard projections passed scoped technical
checks. Formal Steward acceptance and full Component DoD remain open. Direct
inserts and invented authority scope strings remain prohibited. M4.1 does not
implement chat, work-order promotion, provider routing, or the complete Grace
director.

### Current milestone status (2026-10-11)

The later live M3.3 commissioning recorded in `docs/development/M3.3-001_REVISION_RECORD.md`
supersedes the pre-commissioning M3.3 blocker statements in historical notes
below and in older M4.1 checkpoints. M3.3 scoped technical criteria are PASS
and ready for Steward review; this does not claim formal acceptance or full
Component DoD. Current M4.1 engineering adds a fixed-identity Grace office,
resident principal, occupant, local-model binding and exact office-state grant
through `scripts/provision_grace_resident.py`. Its implementation and six
safety tests passed before deployment. The subsequent live commissioning used
root-owned source commit `fb536bb647d7d7a655a56155f687c74bec219945`. A fresh
process retry returned `ALREADY_PROVISIONED`; an independent registry check
verified the binding, model revision and only `office.state.write` on
`office:office:grace`. The bearer remains in a root:root 0600 file and was not
emitted. Live evidence is
`evidence/checkouts/M4.1-GRACE-IDENTITY/20261011T1330Z-fb536bb/`. The helper is
not a resident service and adds no assignment or tool grant. M4.1 service
integration and M4.4 remain in progress.

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
`authorize_exact_grant(bytea,text,text)` and
`authorize_exact_principal_grant(text,text,text)` functions. Never run the boundary helper
against a mixed application schema: it revokes broad schema access before
granting the runtime only the exact authorization function. The
manager is a dedicated non-superuser LOGIN. It receives only schema `USAGE` and
`SELECT`/`INSERT`/`UPDATE`/`DELETE` on the nine registry tables. The protected
`NOLOGIN` table owner also requires schema `USAGE` for PostgreSQL foreign-key
checks executed as relation owner; it does not receive schema `CREATE`. The
manager is `NOINHERIT`
and cannot be a member of any other database role; it cannot create objects,
drop tables, execute protected functions directly, or inherit the
`NOLOGIN` table-owner role. After migration 0002 and 0004 and a successful boundary
apply, the runtime receives schema `USAGE` and function `EXECUTE` only for the
exact-grant checks; authority-table and trigger access remain denied. The linked-principal function does not authenticate a user. It accepts a principal ID obtained by the dashboard from its current account-authenticated session, then requires an active institutional Steward and an exact action/scope grant within its validity window and without revocation. Migration
0003 adds two similarly constrained `SECURITY DEFINER` functions: the runner
can read the current authorized office snapshot and perform a bounded
compare-and-swap write to office-keyed state. Both functions recheck the exact
`office.state.write` grant against the active occupant while holding the office
binding lock. The boundary provisioner verifies function ownership, pinned
search path, and runtime/manager ACL drift. These new functions are only
isolated-test verified in this increment; no shared-schema migration or
Camrui service change is claimed. Migration 0002's exact-grant runtime ACL is
deployed and verified on Camrui. The manager is still a
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
  persist bounded office-keyed state only when the exact grant principal is the
  currently bound resident; stale/re-granted former occupants are denied.
- `authorize_office_state(credential, office_id)` — atomically return the
  current office snapshot only after exact grant and active occupant identity
  match, locking the binding while validating.

All routines are synchronous and transactional in the selected schema. No DDL
runs at construction or service startup. Apply the versioned migration explicitly
only after backup, restore rehearsal, owner/privilege review, and a release plan.
The authority migration chain is self-contained for a fresh dedicated schema:
`0000_authority_migration_ledger.sql` creates only `schema_migrations` if absent,
`0001_institutional_authority.sql` creates the registry and append-only trigger,
and `0002_exact_grant_authorization.sql` adds the protected exact-grant
function; `0003_resident_office_state_api.sql` adds the two bound-office
snapshot/CAS functions; `0004_exact_principal_grant_authorization.sql` adds the
principal-keyed exact-grant check without issuing authority. The runner records checksums and rejects later drift. Existing
schemas with a compatible ledger are preserved; the bootstrap migration uses
`IF NOT EXISTS`. On Camrui the 0000–0002 checksums are recorded; migration
0003 is only applied in the isolated PostgreSQL integration test here. The
exact-grant function ACL is verified, while resident-service commissioning
remains open.

See [the focused flow](INSTITUTIONAL_AUTHORITY_FLOW.md),
[the operations cookbook](INSTITUTIONAL_AUTHORITY_COOKBOOK.md), and
[`RV-M4.1-001`](../development/M4.1-001_REVISION_RECORD.md).


## Deferred-request compatibility for an authorized router upgrade

An implementation-only office rebind continues to require exact office.manage,
an expected binding revision, and a registered model. The optional
deferred_compatibility_capabilities argument defaults to empty. For an explicitly
approved Grace router transition it may contain only grace.reasoning.80b; the CAS
audit event records that opt-in with the direct predecessor and successor
identities and revisions. The successor must use the registered
grace.readiness_router.v1 provider.

The runtime uses authority migration
0006_authorized_implementation_successor.sql through the boolean SECURITY
DEFINER function authorized_office_implementation_successor. It revalidates
the current resident credential, active office occupant, and exact
office.state.write grant, then matches the current binding revision to the one
audited direct transition. The restricted runtime gets EXECUTE on this
allowlisted function only; authority event and migration tables remain
unreadable. This check authorizes continuity for that transition and capability
only; it creates no grant and does not replace the original user's exact
conversation grant.
