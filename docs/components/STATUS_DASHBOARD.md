<!--
Riverview~ Controlled Document
File: docs/components/STATUS_DASHBOARD.md
Component: STEWARD-DASHBOARD
File Revision: 1.1.1
Purpose: Specify operational projections and exact-grant Grace objective and conversation interfaces
Authority: Reads require dashboard authentication; objective and resident conversation operations require exact institutional grants
Changed: 2026-10-11 UTC | RV-M3.2-001 | Document bounded visual notification and receipt routes
Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-CURRENT-DOCS-RELEASE | Define accurate code/deployment provenance for composite docs release
Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-PROVENANCE-SECTION-ORDER | Place deployment provenance separately from the API route contract
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add governed objective intake and result projections
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Integrate the isolated resident conversation view and versioned API
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Keep persisted historical interruption notices out of current response error state
Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Document password login, grant controls and configurable SMTP administration
Changed: 2026-10-14 UTC | RV-GRACE-HEALTH-PROJECTION-ACL-001 | Grant dashboard runtime SELECT only on Grace execution health for status projection
History: Git and revision/backup manifest
-->
# Steward status dashboard

**Component:** STEWARD-DASHBOARD  
**Milestone:** M3.1 — Read-only status projection and browser dashboard  
**Status:** Engineering implementation; commissioning evidence recorded separately.  
**Source baseline:** `main` at `e9c66afabe88fe02403a35c8ede83eba54bca2e2` (M2.4 PR #14).  
**Execution model:** Request-driven browser/API projections and objective intake; durable execution is performed by the separately supervised CME/Grace worker service.
**Port:** `127.0.0.1:8766`, reserved to `riverview-status-dashboard.service`.

## Reuse assessment

The old `ppow1/Riverview` sources were cloned read-only at the then-current default
branch for inspection. New Riverview reuses these verified design patterns, not
legacy runtime state or dependencies:

| Predecessor | Retained design | Deliberately not imported |
| --- | --- | --- |
| `operator/vnext_projection.py` | Pure status projection; unknown is not healthy; heartbeat age; bounded activity; state derived from authoritative evidence. | Its Riverview/ Estate/PostgreSQL models and resource topology do not match New Riverview tables. |
| `operator/vnext.py`, `tests/test_operator_vnext.py` | Shell-first navigation, independent async hydration, resident-bound session isolation patterns for later chat, and failure-local UI updates. | Resident chat/session endpoints are not present in New Riverview; no mock provider or legacy gateway is copied. |
| `operator/snapshot.py` | Explicit allowlist/redaction, bounded data, manifest metadata, excluding private conversation and secret material. | Legacy database reads, broad UI payload, archived runtime state and old service dependencies. |
| `residents/gateway.py` | Keep resident identity/session API as a later distinct capability; conversation is not authority. | Existing identity/personality data or resident implementations are not copied. |
| RV-018.6 and PL-0007 evidence | Keep named resident selection, per-resident session continuity, no silent seed/work promotion, cached shell-first navigation, localized updates and measured interaction. | Historical acceptance claims are not treated as New Riverview evidence. |
| Legacy Operator event/correlation views | Display immutable event/correlation/causation identities with diagnostic references. | Legacy event tables and unbounded event reconstruction. |
| Estate Office of the Steward command center and AI service/model selector records | Preserve a future contextual command surface and separate model/resource selection from institutional role and authority. | Estate command API, model catalog, runtime implementation and permissions are not imported. |

Source audit paths: `/tmp/rv-old-audit` and `/tmp/estate-audit` are temporary
read-only clones, not repository dependencies. New Riverview status uses its own
PostgreSQL ledger and CME projections.

## Authenticated dashboard and bounded action API contract `rv.dashboard.v1`

The browser and future API/AI consumers share the same authenticated HTTP entry
point. Status and operational projections are read-only. In addition to receipt
operations, narrow objective and resident-conversation operations require a
second exact-grant authority credential; the dashboard bearer alone grants no
institutional action. Other mutating HTTP methods return `405 read_only_method`;
no direct browser database write exists. Application APIs accept either the
protected legacy bearer token or a verified account session cookie. The bearer
is backed by a protected systemd credential. Its source file is owner-only;
systemd exposes a read-only credential copy in its exact credential directory.
Only that exact systemd path may use mode 0400 or 0440; ordinary files require
owner-only permissions. Symlinks are rejected and token reads use a no-follow
file descriptor. Comparison is constant-time. Account sessions use random
server-checked tokens in `Secure`, `HttpOnly`, host-only, `SameSite=Lax` cookies
and a separate session-bound CSRF token. The legacy bearer remains available as
an administrative recovery path. The listener accepts only the
IPv4/IPv6 loopback literal, validates the Host header, does not enable CORS, and
does not place credentials in URLs. Authentication is per-service bearer access,
not resident identity or delegated authority. Account roles only authorize
website projections and account controls. Operators receive no engineering
execution grant by virtue of login. Each existing narrow write
independently resolves an exact AuthorityRegistry grant; chat cannot promote
itself into executable work.

The service reads PostgreSQL in read-only transactions, with a two-second SQL
statement timeout and short connection timeout. It uses only the configured
schema identifier, bounded keyset/sequence pages (maximum 100), and stable
allowlisted fields. `privacy_domain != institution` assignments/events are
omitted. Event payloads, authority grants, artifact content, credentials and
private conversation content are not projected. Objective summaries show at
most 512 characters of the authorized human request, lifecycle, artifact digest,
verification decision and pinned source revision.

| Route | Purpose | Parameters and limit |
| --- | --- | --- |
| `GET /api/v1/status` | Database/schema/migration identity, event cursor and lifecycle counts, CME heartbeat/freshness, aggregate per-worker health counts, verifier relation presence, source/deployment identity. | Fixed size. |
| `GET /api/v1/objectives?limit=<n>` | Bounded objective, assignment, artifact, verification and source-revision summaries. | Default 25, max 100. |
| `GET /api/v1/objectives/<id>` | One objective's persisted lifecycle and verified result summary. | Fixed summary; no artifact body. |
| `POST /api/v1/objectives` | Persist a bounded human request and attempt commit-pinned grounding. | Dashboard bearer plus `X-Riverview-Authority` exact `objective.submit` grant for supplied scope; maximum JSON body 16 KiB. |
| `POST /api/v1/objectives/<id>/proposal` | Persist a typed PlanProposal after grounding and human-criteria validation. | Dashboard bearer plus `X-Riverview-Authority` exact `assignment.create` grant for the objective scope. A proposal is not authority. |
| `POST /api/v1/objectives/<id>/cancel` | Cancel only queued/ready pre-execution work. | Dashboard bearer plus exact `assignment.cancel` grant for the objective scope. |
| `GET /api/v1/assignments?after=<id>&limit=<n>` | Keyset page of lifecycle, owner, workflow/step, version, correlation and last persisted progress event. | Default 25, max 100. No progress percent. |
| `GET /api/v1/assignments/<id>` | One assignment, 20 latest visible lifecycle events, 5 attempts and 5 independent-verification summaries. | Fixed limits; no event payload/evidence URI. |
| `GET /api/v1/events?after_seq=<n>&limit=<n>` | Institution event cursor page with event/correlation/causation identity. | Default 25, max 100; no payload. |
| `GET /api/v1/workers?after=<id>&limit=<n>` | Bounded worker identity, active/inactive state, latest lease heartbeat health and visible active-lease count. | Default 25, max 100; keyset by worker ID. |
| `GET /api/v1/attention?limit=<n>` | Bounded CME attention and recovery event records. | Default 25, max 100; sanitized error class only. |
| `GET /api/v1/notifications?limit=<n>` | Durable visual notices, dispatcher freshness, and pending decision-request state. | Default 25, max 50; fixed summaries only. |
| `POST /api/v1/notifications/<uuid>/delivered` | Record successful visible rendering by the dashboard client. | Empty body; service bearer only; not human identity or Steward authority. |
| `POST /api/v1/notifications/<uuid>/acknowledge` | Explicit receipt acknowledgment after delivery. | Empty body; cannot alter the linked decision request or assignment. |
| `GET /api/v1/snapshot` | Bounded server-observed operational snapshot. | At most 50 assignments and 25 events/attention/worker rows. |
| `GET /api/v1/graphs` | Index of registered canonical focused process graphs. | Reads versioned package registry; bounded by checked-in graph count. |
| `GET /api/v1/graphs/<graph_id>` | Canonical nodes, typed edges, decisions, references, and execution-position state. | One registered focused workflow; no graph mutation. |
| `POST /api/v1/auth/enrollment` / `.../enrollment/verify` | Request access and verify a single-use email challenge. | Generic anti-enumeration request response; 15-minute challenge; email delivery must be configured. |
| `POST /api/v1/auth/login` / `POST /api/v1/auth/session` | Authenticate email and password; issue persistent session. | Verified, approved account and unexpired grant required; password hash and session verifier remain server-side. |
| `POST /api/v1/auth/password-reset`, `/api/v1/auth/password-set` | Request reset or establish/reset password using single-use email challenge. | Generic public response; password reset revokes prior sessions. |
| `GET` / `DELETE /api/v1/auth/session` | Read current account identity or log out. | Cookie-authenticated; DELETE requires CSRF. |
| `GET /api/v1/account/enrollments`, `GET /api/v1/account/users` | Steward enrollment queue and bounded account listing. | Steward website role required. |
| `POST /api/v1/account/enrollments/{id}/decision`, `/api/v1/account/users/{id}/{disable,roles,sessions,grant}` | Deny or approve with Viewer/Operator/Steward role and one-time/90-day/one-year/permanent grant; disable accounts, change roles or revoke access. | Steward role plus CSRF; one-time permits one session ever, maximum 24 hours. Expiration/revocation is checked on every request. |
| `GET/PUT /api/v1/account/email-settings`, `POST /api/v1/account/email-settings/test` | View/update SMTP settings and send test email. | Steward role; CSRF on mutations; password is encrypted server-side and never returned to browser. |
| `POST /api/v1/auth/steward-bootstrap/verify` | Confirm the single-use challenge issued by the local-only bootstrap command. | Cannot issue a challenge or grant a role; requires the pre-authorized exact challenge. |
| `GET /docs/components/<name>.md` | Safe, formatted view of an allowlisted component document. | Repository-controlled component Markdown only; raw HTML is escaped. |

## Deployment identity

`source_commit` identifies the dashboard service code revision. `deployment_id`
identifies the exact installed release. A docs-only refresh may combine the
unchanged dashboard code with newer component cookbooks and canonical process
graphs; its root-owned release manifest must record each source revision and
package checksum. In that case, set `RIVERVIEW_SOURCE_COMMIT` to the dashboard
code commit and assign a new, unique `RIVERVIEW_DEPLOYMENT_ID`. Do not report a
docs/graph commit as the dashboard code revision or reuse an existing release
directory for changed bytes.

The status response schema identifier is `rv.dashboard.status.v1`; it includes Grace execution heartbeat and freshness when the runtime migration is installed. The summary counts healthy, stale, unknown and future-dated unverified active workers. `GET /api/v1/workers` pages individual identities; each status uses the latest recorded assignment-lease heartbeat. No heartbeat is unknown, not healthy. The overview shows worker IDs, health and lease counts. List/detail
responses carry `status`, bounded `items`, and pagination state. Database
unavailability returns a status projection whose `projection_status` is
`unavailable`; HTTP query failures return 503. A reachable PostgreSQL instance
with missing required relations returns HTTP 200 with `status=not_initialized`;
this is a valid domain state, not a transport failure. The browser skips the
optional attention query while its relation is absent and displays that state.
CME values are
`healthy`, `degraded`, `stale`, `unavailable`, or `not_initialized`; a missing
heartbeat is unknown/not initialized, never healthy. Worker status is derived
only from recorded assignment-lease heartbeats; no lease means `unknown`. A
future-dated heartbeat is `unverified`. Event time/correlation is retained as
recorded, not inferred from browser refresh time.

Machine-readable route schema: `docs/components/STATUS_DASHBOARD_API.schema.json`.

Account authentication's durable schema, transport configuration, bootstrap
procedure, and operational limitations are specified in
`docs/components/ACCOUNT_AUTHENTICATION.md`. When no approved email relay is
configured, account enrollment and sign-in return `email_delivery_unavailable`;
the dashboard bearer recovery path continues to work. The account schema is
separately migrated and is not created at dashboard startup.

### Canonical process graph and diagnostic documents

The graph index and graph detail routes use the dashboard bearer token. The
browser renders their canonical JSON response as a read-only SVG with workflow
selection, node identities/revisions, typed edges, decisions, node references,
and resolvable cross-workflow jump controls. There is no second maintained graph
source. The execution-position field stays `unknown` while assignment state does
not persist a canonical process-node identity; in that state the viewer
highlights no node and displays the reason. It does not infer a node from prose.

Component-document routes read only regular files from the package's
`docs/components` directory. The standard-library renderer supports headings,
paragraphs, lists, tables, code fences, and safe links. It escapes source HTML;
only HTTPS, in-page anchors, and component-document links become anchors. No
script is emitted, and all content remains sourced from controlled Markdown.

## Browser, refresh and later console constraints

The first page shell renders before projection hydration. Overview, assignments
activity, workflows, and assignments are client-side views in one document. Navigation switches existing
DOM immediately; it does not call AI or reconstruct institutional state. Status
refresh and event refresh are separate bounded requests; assignment detail is
lazy-loaded. Failure of a source or worker cannot block navigation or CME.
Refresh failures are visible and bounded in a browser-local diagnostic ring.
Documentation links open readable HTML views. Graph fetching is isolated to the
workflow view and does not block status refresh or CME execution.

The component reserves one application origin for future authenticated resident
conversation, context-specific commands, capability/resource registry and AI/API
clients. Those routes are not implemented in M3.1. Future chat must have
resident-bound durable sessions independently refreshable from status views.
Conversation must remain non-authoritative; only an explicit, authenticated,
policy-checked approval can promote a specification to a durable objective or
work order. Future UI buttons call the same versioned authenticated command API
as residents/AI; they never write PostgreSQL directly. Contextual verbs must be
derived from entity lifecycle and authority, with precondition/version,
idempotency and correlation identifiers; pending, denied and failed commands
must remain distinguishable. Capability discovery cannot grant permission.
Model selection and resource scheduling remain separate from resident role and
authority. These are architectural constraints, not delivered M3.1 features.

## Snapshot contract

The server snapshot reports an observed-state flag (false when the source is unavailable), observed time, source revision/deployment identity,
projection status and freshness, CME/worker health, bounded visible assignment
event, attention and worker summaries, stable graph/cookbook references, and explicit redaction
metadata. The browser adds at most 20 sanitized request errors and 100 navigation
timings from the current tab. It contains no token, headers, database DSN,
payload body, unrestricted conversations, resident session, work-order or
capability-registry data. Fields not implemented are named in `client_state` or
omitted; absence is never represented as an empty healthy registry.

## Grace resident conversation integration

The shared dashboard serves the `Talk with Grace` view and versioned resident
conversation routes specified in
[`RESIDENT_CONVERSATION.md`](RESIDENT_CONVERSATION.md). Requests require the
dashboard bearer plus `resident.conversation.read` or
`resident.conversation.send` authority for `office:<office-id>`. Conversation
events are stored with the existing resident execution records. Current model
selection comes from the office implementation binding and must match the
implementation revision. Model output cannot create or authorize an objective
or work order.

The conversation timeline retains prior failed/interrupted response events. The
current response banner is cleared when a later assistant event succeeds; an
older recovery notice does not appear as a current turn failure.

This is isolated engineering on the proposed, not formally accepted M3.4
sequencing workstream. It does not claim shared-service deployment, Steward
browser acceptance, M3.4 milestone acceptance, or full Component DoD. The
conversation contract records configuration, troubleshooting, and recovery.

## Runtime and deployment

The status projection reads `grace_execution_health` when that relation exists.
Migration `src/riverview_core/resident_execution/migrations/0005_dashboard_grace_health_read.sql`
grants the dashboard database role `riverview_core` SELECT on that single table
in the selected application schema. It grants no authority-schema migration
ledger access and no privileges on unrelated relations. Apply it only through
the reviewed migration runner after protected backup and checksum preflight.
The regression test runs the projection as `riverview_core`, confirms the
pre-migration `InsufficientPrivilege` result, then verifies the single-table
grant restores the current status projection.

Port 8766 is reserved for this service, bound to `127.0.0.1`; existing
`riverview-event-processor.service`, `riverview-cme-monitor.service`, and
`riverview-baseline.service` are separate. The CME monitor is a read-only observer
of assignments/leases with writes limited to CME health and attention records;
it has no dashboard dependency. Remote access, when needed, uses an authenticated SSH
forward rather than an internet/LAN listener. systemd runs the root-owned release
as OS account `riverview`; systemd `LoadCredential` provides the existing
PostgreSQL passfile and separate dashboard bearer token. The token source is
owner-only under the Steward account. The process has no database write route or
DDL/startup migration path. See `deploy/riverview-status-dashboard.service` and
`docs/components/STATUS_DASHBOARD_COOKBOOK.md`.

Deployment procedure copies a verified commit to a versioned root-owned
`/opt/riverview-status-dashboard/releases/<commit>` directory, verifies the
package hash, updates only the dashboard `current` symlink and new dedicated
systemd unit, and captures the existing symlink/unit before first install.
Rollback restores that symlink/unit from the recorded predecessor and restarts
only the dashboard unit. PostgreSQL migration changes are not part of M3.1.

## Verification and status

Roadmap technical PASS requires real PostgreSQL rows rendered through the
browser/API, stale/unavailable differentiation, unrelated work remaining
independent, navigation/refresh measurements, redacted bounded snapshot, and a
dashboard service restart/reconnection. Isolated tests, a browser screenshot or
a successful HTTP response alone do not pass. Full Component DoD additionally
requires Steward-visible installed unattended operation, independent external
observer, full console/chat/command and later M3 features as applicable, blocker
clearance, operational fault/recovery and explicit Steward acceptance. This
document does not claim those future obligations complete.
