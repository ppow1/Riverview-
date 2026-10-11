<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Define durable identities, exact scoped authority, and office-state continuity
Authority: Grants are Steward-issued; absence or uncertainty denies the action
Changed: 2026-10-11 UTC | RV-M4.1-001 | Initial identity and authority contract
History: Git and .riverview-backups/manifest.jsonl
-->
# Institutional identity and authority registry

**Milestone:** M4.1 — Office, occupant, implementation and state separation  
**Status:** Isolated PostgreSQL implementation in progress; not live commissioned  
**Implementation:** `src/riverview_core/institutional_authority/registry.py`  
**Migration:** `src/riverview_core/institutional_authority/migrations/0001_institutional_authority.sql`  
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
only SHA-256 digests. Expired, revoked, inactive, malformed and unknown
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

The isolated contract tests exercise token digest lookup, exact grant matching,
revocation, expiry validation, append-only events, and state continuity. The
current Camrui `riverview_core` database identity owns existing application
tables. This milestone's migration has **not** been applied to shared
`riverview_dev`, and no service uses this registry yet. Therefore the Python
registry check is not claimed as a database-enforced boundary against arbitrary
SQL from a process holding the current owner credential. Before live assignment
creation is authorized, deployment must separate the authority writer from
ordinary runtime database roles or use an equivalently enforced database
boundary, then bind the worker/assignment control path to `authorize()`.

This boundary is why the M3.3 shared assignment demonstration remains blocked;
direct inserts or invented grant strings are not an acceptable substitute.
M4.1 does not implement chat, work-order promotion, provider routing, or the
Grace director.

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

See [the focused flow](INSTITUTIONAL_AUTHORITY_FLOW.md),
[the operations cookbook](INSTITUTIONAL_AUTHORITY_COOKBOOK.md), and
[`RV-M4.1-001`](../development/M4.1-001_REVISION_RECORD.md).
