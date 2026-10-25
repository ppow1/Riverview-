<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_PERMISSION_PROFILES.md
Component: RESIDENT-PERMISSION-PROFILES
Document Revision: 1.1.1
Changed: 2026-10-25 UTC | RV-DYNAMIC-PERMISSIONS-20261025 | Document canonical dynamic declarations, effective authorization projection, and current registry limitations.
Status: Deployed permissions API contract; Steward-only management
Owner: Steward; future HR and Security duties remain uncommissioned
Changed: 2026-10-14 UTC | RV-RESIDENT-PERMISSIONS-001 | Define profiles, capabilities, resources and Steward review
Changed: 2026-10-14 UTC | RV-RESIDENT-PERMISSIONS-001 | Enforce registered resource bindings, identity continuity, and fail-closed classification/export
History: Git
-->
# Resident permission profiles, capabilities, and resources

## Authority and reused registries

`AuthorityRegistry` remains the source of resident/principal identity, office,
occupant, exact grants, binding revisions, and institutional audit. The new
profile layer is additive: an active profile may further restrict an exact
grant; it never issues, widens, or substitutes for one. All action execution
continues to require the existing exact `(principal, action, scope)` grant.
Missing profiles retain the pre-existing exact-grant behavior while adoption
is staged. An active profile with no matching allow rule denies.

The worker registry remains the source of registered executor identities and
their declared capability names. Assignment leases remain the source of current
worker concurrency. The capability catalog describes an operation, its owning
office, authority action, implementation, and dependencies. The resource
catalog describes a host, service, database, filesystem, adapter, model, or
institutional boundary. Provider health, capacity, busy state, and freshness
remain dynamic observations from their owning services; registration is not a
health claim and neither capability nor resource availability grants access.

Historical `src/riverview/resources/registry.py` selection concepts and
occupational capability descriptions informed this schema. Their old Estate
Codex telemetry path is not used as current Riverview authority or readiness.

## Permission profiles

Migration `0008_resident_permission_profiles.sql` adds capability and resource
metadata, resource-to-capability bindings, four tier definitions, profile and
rule records, pending profile drafts, and append-only profile audit events.
The supported tier identifiers are `observer`, `operator`, `administrator`,
and `institutional_administrator`. Tier names are onboarding defaults only;
the migration seeds bounded cumulative tier defaults; a title or tier never
creates an authority grant. Every resulting action still requires its
independent exact grant, active profile, registered capability/resource pair,
and current resource readiness.

An explicit rule addresses one capability and a registered resource (or the
resource selector `*`, which remains bounded by the separate exact-grant
scope). It records allow/deny, read/write/execute/administer/delegate access,
approval requirement, data classification, export policy, provenance, expiry,
and revocation. A profile records resident/office identity, tier, profile
revision, status, classification ceiling, export mode, creator and approver.

Policy precedence is deterministic:

1. An explicit resident rule is more specific than its inherited tier rule.
2. A more resource-specific rule wins within the same source.
3. Deny wins when specificity is equal. A resident-specific allow can be an
   audited exception to an inherited tier denial.
4. Expired and revoked rules do not match. No matching allow means deny.
5. A capability must be registered for the requested resource before any
   profile rule is considered. Dynamic resource health and capacity are still
   separate readiness checks.
6. The existing exact grant is checked independently. A profile allow cannot
   authorize a missing, expired, revoked, or mismatched exact grant.
7. A matching rule marked `approval_required` is held for a separate approval;
   the current enforcement adapter fails closed until such an approval path is
   supplied to the operation.

An explicit deny is selected before classification/export filtering, so a
restrictive allow cannot be reached by asking for a different classification.
An allow is then checked against both the profile ceiling and rule-level
classification/export limits. A revoked or suspended profile denies, while a
principal with no profile remains in legacy exact-grant-only mode during staged
adoption. An active profile also becomes invalid if the resident is inactive or
their current office no longer matches the office recorded at approval.

Profile changes save into a pending draft separate from the effective profile.
The current active rules remain effective while edits await Steward approval.
Activation and revocation use expected-revision compare-and-swap and append an
audit event. The database functions require an active Steward principal and
the existing exact `office.manage` grant on `institution`. A stale revision,
unknown capability/resource, database error, or unavailable registry does not
activate a change.

The dashboard routes are `/api/v1/resident-permissions` (read),
`PUT /api/v1/resident-permissions/{principal}` (save a pending profile), and
`POST /api/v1/resident-permissions/{principal}/approve|revoke` (explicit
Steward decision). They use the existing account session, CSRF, and exact
institutional authority. Account role alone is insufficient. The runtime gets
function execution only after DBA preflight/application through the established
authority boundary helper; profile/catalog tables remain inaccessible to it.

### Dynamic V2 capability inventory

V2 reads `capabilities`, `resources`, resident rules, inherited tier rules, and
exact grants from the authenticated `/api/v1/resident-permissions` response. Its
editor and inventory derive their rows from that response; capability IDs are
not copied into website code. Adding a row and its resource binding to the
canonical `capability_catalog` / `capability_resources` source makes the row
available on the next page refresh without a website release. Registry
visibility is discovery only: activation still uses the existing pending
profile, institutional Steward decision, and exact authority grants. It does
not mean an executor is registered, healthy, or authorized to execute.

Release-shipped declarations are reconciled through the existing authority
release migration from
`src/riverview_core/institutional_authority/capability_declarations/`; the
controlled-checkout declaration gate requires new dashboard API operations to
declare a capability or an explicit exclusion. The installed declaration
contract includes operation identity, input schema, authorization contract,
executor implementation reference, dependencies, and registration blocker.
Grace's existing `GraceCapabilityRegistry.snapshot()` bridge reads the same
catalog, derives only the resident credential's authorized exact scopes, and
rechecks the exact grant at invocation. Neither that bridge nor the V2
inventory grants authority by discovery.

The current list function returns enabled catalog records. If a resident rule
or historical reference points to a capability absent from that response, V2
shows it as unavailable and retains the reference in the view. It disables
profile editing in that case because the existing save function accepts only
enabled catalog entries; this avoids silently dropping those references. The
API does not expose whether the absent entry was disabled, deprecated, or
removed, so the UI reports that distinction as unavailable rather than
guessing. Existing grant records and append-only profile audit remain separate
and visible.

The authority catalog currently supplies capability ID, description, authority
action, owner office, implementation reference, dependencies, approval default,
enabled state, declaration source, input schema, authorization contract,
availability policy, registration blocker, and resource bindings. The V2
permission API does not supply a live executor identity or health observation.
The existing permission store augments
the Steward response by invoking the canonical profile evaluator for each
registered action/resource at its catalog classification, non-export
condition, and action-derived access level, then intersects that result with
the exact active grant for the same action and resource scope. V2 labels these
conditions and shows explicit/inherited rules, grant scope, restrictions,
approval, expiry, and provenance. This bounded result does not establish
executor readiness or successful operation; the per-operation authorization
check remains authoritative.

The V2 page is a Steward management view. It does not expose the all-residents
profile response to resident sessions. Grace's existing capability bridge
provides a principal-bound authorized-scope snapshot for the resident
credential; other resident operations remain guarded by the same exact-grant
and profile evaluator at invocation. Worker executor declarations remain in
the worker registry. No capability is granted by making it visible in V2.

## Grace initial proposal

Grace is the Director of Operations. Her proposed onboarding tier is
`institutional_administrator`, represented as a pending, Steward-reviewed
profile only after the schema is commissioned. Desired capability areas are:

- bounded shell/SSH operations on individually registered Riverview hosts;
- filesystem read/write under explicitly approved path scopes;
- database reads through named projections and writes through governed
  transactions or migrations;
- service monitoring, diagnostics, and explicitly approved recovery;
- CME progression and objective/work-order coordination;
- resource/capability inspection and Engineering dispatch through registered
  adapters; and
- Codex CLI coordination and output inspection under the supervised CLI
  authentication contract.

The catalog seed records those capability descriptions and dependency edges but
issues no grants. It omits root access, arbitrary shell authority, unrestricted
database access, OCTO model/hardware control, and any cross-scope grant. The
Steward must review the host/resource identifiers, exact grants, approval
requirements, data classifications, and exports before creating/activating
Grace's profile. Routine operations can later run without repeated approval
only where a standing exact grant and an active profile rule both allow them.

Helen (`RES-000003`, Human Resources) and Ingrid (`RES-000002`, Security) are
future office integrations. They are not seeded, activated, or assigned
authority by this migration. The dashboard lists only resident identities
already registered in AuthorityRegistry. Future HR and Security controls can
use the same profile revision, approval, audit, expiry, and revocation APIs
once their residents and governance grants are commissioned.

## Steward dashboard and operational visibility

The Steward view shows each registered resident and office, default tier,
profile state/revision, explicit and inherited rules, resources, approval
requirements, classification/export controls, approver, and audit history.
The checklist edits capability and resource policy and saves a pending draft;
an explicit activation action is distinct from editing. The view does not
write account roles or authority grants. It currently lists registered
resource metadata only; dynamic readiness/capacity is not yet joined into this
view and must be checked through the owning service/worker projection. A title
does not preselect a tier; a new checklist starts at Observer for review.

## Failure handling and commissioning limits

- Missing/invalid account session or exact management grant: HTTP 401/403;
  no profile mutation.
- Stale revision: HTTP 409; refresh current profile and retry after review.
- Missing migration/function permission/database response: HTTP 503; fail
  closed and use the authority cookbook's protected migration/ACL recovery.
- Provider offline/busy/degraded/unknown: retain authorized work pending or
  report resource unavailable; never reinterpret it as authorization denial.
- Active profile deny/expiry/export/classification failure: deny the operation
  while preserving the underlying exact-grant and profile audit evidence.

This source increment is not deployed. Migration 0008 has not been applied,
the expanded authority boundary has not been provisioned, no Grace profile has
been saved or activated, and no production grants/bindings changed. Apply the
checksum-pinned migration and updated function-only boundary only in a later
approved commissioning with backup and disposable restore verification.
