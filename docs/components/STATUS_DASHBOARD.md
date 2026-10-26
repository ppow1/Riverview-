<!--
Changed: 2026-10-20 UTC | RV-WEB-SNAPSHOT-V1-V2-INTEGRATION-001 | Document the same-origin V2 route and shared authenticated snapshot/archive boundary.
Riverview~ Controlled Document
File: docs/components/STATUS_DASHBOARD.md
Component: STEWARD-DASHBOARD
File Revision: 1.1.19
Changed: 2026-10-23 UTC | RV-WORKER-HEALTH-SNAPSHOT-20261023 | Distinguish live registered engineering capabilities from assignment-lease activity.
Changed: 2026-10-26 UTC | RV-V2-COMFYUI-RUNTIME-READOUT-20261026 | Document sanitized ComfyUI version, queue counts, device and VRAM projection.
Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Document authenticated GPU and inference telemetry projection.
Changed: 2026-10-22 UTC | RV-V2-HW-AI-ENHANCEMENTS-207 | Specify per-slot context counters and unavailable KV-cache bytes.
Changed: 2026-10-22 UTC | RV-HW-LIVE-STREAM-ACTIVITY-001 | Specify authenticated content-free stream activity projection.
Changed: 2026-10-22 UTC | RV-V2-MOUNTED-STORAGE-001 | Define per-host read-only storage projection and host gaps.
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Specify bounded private Release archival and Steward/CSRF authorization.
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Specify byte-identical archive/download handoff and local recovery.
Changed: 2026-10-19 UTC | RV-C1-PR152-SCOPE-PROVENANCE-001 | Document role-gated objective access, owner checks, and minimized conversation progress
Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Add conversation-origin-filtered durable Engineering progress and authenticated UI refresh contract.
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Specify bounded raster omission while preserving snapshot records and vector representations.
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Separate the fixed raster ceiling from structured-content and manifest headroom.
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Specify private Release archival, Steward/CSRF gate, protected credential and local fallback.
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Specify same-Blob archive and browser-download handoff, digest matching, and independent failure behavior.
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-V1-V2-COMPAT-20261020 | Specify dashboard-version manifest identity and capture-specific Release asset names while retaining legacy V1 package acceptance.
Purpose: Specify operational projections and exact-grant Grace objective and conversation interfaces
Authority: Reads require dashboard authentication; objective and resident conversation operations require exact institutional grants
Changed: 2026-10-11 UTC | RV-M3.2-001 | Document bounded visual notification and receipt routes
Changed: 2026-10-16 UTC | RV-WORKER-HEALTH-REPORTING-001 | Clarify lease-health semantics and unobserved worker process state
Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-CURRENT-DOCS-RELEASE | Define accurate code/deployment provenance for composite docs release
Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-PROVENANCE-SECTION-ORDER | Place deployment provenance separately from the API route contract
Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add governed objective intake and result projections
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Integrate the isolated resident conversation view and versioned API
Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Keep persisted historical interruption notices out of current response error state
Changed: 2026-10-12 UTC | RV-ACCOUNT-ACCESS-REFINEMENT | Document password login, grant controls and configurable SMTP administration
Changed: 2026-10-14 UTC | RV-GRACE-HEALTH-PROJECTION-ACL-001 | Grant dashboard runtime SELECT only on Grace execution health for status projection
Changed: 2026-10-15 UTC | RV-WEBSITE-PL011 | Document sequence-based older and newer activity pagination
Changed: 2026-10-15 UTC | RV-WEBSITE-PL012 | Document event provenance fields and diagnostic boundary
Changed: 2026-10-15 UTC | RV-WEBSITE-PL014 | Document refresh cache policy and projection status meanings
Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Document bounded authenticated conversation streaming writes and migration dependency
Changed: 2026-10-15 UTC | RV-WEBSITE-PL027 | Document focused cross-workflow jump navigation and return behavior
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
| `GET /api/v1/objectives?conversation_id=<uuid>&limit=<n>` | The bounded, progress-only objective projection filtered by immutable conversation origin; includes lifecycle stage, latest meaningful event, verifier summary/rework state and Steward-action-needed flag for the persistent Talk with Grace activity panel. No request text, scope, submitter, acceptance criteria, artifact path/digest, source digest, transcript body or artifact content. | Requires an active account session. A non-Steward account must provide a conversation it owns; the route validates ownership through the existing `ConversationService.history()` exact read-authority and owner check, then filters objectives by that principal and exact conversation. Default 25, max 100. |
| `GET /api/v1/status` | Database/schema/migration identity, event cursor and lifecycle counts, CME heartbeat/freshness, aggregate per-worker health counts, verifier relation presence, source/deployment identity. | Fixed size. |
| `GET /api/v1/resources/telemetry` | Bounded, request-driven GPU inventory/metrics and allowlisted inference readiness/model/slot context projection for verified hosts. | Account/bearer authenticated; GET/HEAD only; GPU SSH uses a dedicated systemd credential and host-side forced command. Queue depth and KV-cache allocation bytes remain unavailable for current llama.cpp builds. |

The same authenticated telemetry projection includes ComfyUI's fixed private endpoint status, version, count of running/pending queue entries, and reported device name/type/index plus free/total VRAM. It strips queue entries, prompt content, task identifiers, and inputs before returning the response. A ComfyUI API response indicates the endpoint is responding; it is not a service-manager assertion. The browser uses the existing authenticated resource API and displays source-unavailable states without inference.
| `GET /api/v1/resident/conversations/<uuid>/stream-activity?limit=<n>` | Up to 12 recent stream states and content-free timestamped delta character counts for the authenticated conversation; response text is never included. | Dashboard session/bearer plus existing exact `resident.conversation.read` grant and conversation-owner check. Default 12, maximum 12; GET/HEAD only. |
| `GET /api/v1/objectives?limit=<n>` | Bounded objective, assignment, artifact, verification and source-revision summaries. | Steward account role required for the global list. Dashboard bearer alone and non-Steward account sessions are denied. Default 25, max 100. |
| `GET /api/v1/objectives/<id>` | One objective's persisted lifecycle and verified result summary. | Steward account role receives the existing summary. A non-Steward account is filtered by its principal and receives the progress-only shape only after the originating conversation passes the existing exact `resident.conversation.read` grant and conversation-owner check. No artifact body. |
| `POST /api/v1/objectives` | Persist a bounded human request and attempt commit-pinned grounding. | Dashboard bearer plus `X-Riverview-Authority` exact `objective.submit` grant for supplied scope; maximum JSON body 16 KiB. |
| `POST /api/v1/objectives/<id>/proposal` | Persist a typed PlanProposal after grounding and human-criteria validation. | Dashboard bearer plus `X-Riverview-Authority` exact `assignment.create` grant for the objective scope. A proposal is not authority. |
| `POST /api/v1/objectives/<id>/cancel` | Cancel only queued/ready pre-execution work. | Dashboard bearer plus exact `assignment.cancel` grant for the objective scope. |
| `GET /api/v1/assignments?after=<id>&limit=<n>` | Keyset page of lifecycle, owner, workflow/step, version, correlation and last persisted progress event. | Default 25, max 100. No progress percent. |
| `GET /api/v1/assignments/<id>` | One assignment, 20 latest visible lifecycle events, 5 attempts and 5 independent-verification summaries. | Fixed limits; no event payload/evidence URI. |
| `GET /api/v1/events?after_seq=<n>&limit=<n>` or `?before_seq=<n>&limit=<n>` | Institution event cursor page with event, assignment, actor, correlation, causation and payload-schema identity. The website appends newer sequences and prepends older sequences using the returned cursors. | Default 25, max 100; no payload body, separate task ID or event-specific diagnostic reference. Sequence cursors are exclusive and stable; the response reports when more records remain. |
| `GET /api/v1/workers?after=<id>&limit=<n>` | Bounded worker identity, active/inactive state, latest lease heartbeat health and visible active-lease count. | Default 25, max 100; keyset by worker ID. |
| `GET /api/v1/attention?limit=<n>` | Bounded CME attention and recovery event records. | Default 25, max 100; sanitized error class only. |
| `GET /api/v1/notifications?limit=<n>` | Durable visual notices, dispatcher freshness, and pending decision-request state. | Default 25, max 50; fixed summaries only. |
| `POST /api/v1/notifications/<uuid>/delivered` | Record successful visible rendering by the dashboard client. | Empty body; service bearer only; not human identity or Steward authority. |
| `POST /api/v1/notifications/<uuid>/acknowledge` | Explicit receipt acknowledgment after delivery. | Empty body; cannot alter the linked decision request or assignment. |
| `GET /api/v1/snapshot` | Bounded server-observed operational snapshot. | At most 50 assignments and 25 events/attention/worker rows. |
| `POST /api/v1/snapshot/archive` | Validate and archive the generated redacted diagnostic ZIP as a versioned, capture-specific asset in the private GitHub Release repository; return release URL and metadata. | Steward account session plus CSRF; `application/zip`; one concurrent upload; maximum 97 MiB request and 96 MiB uncompressed members. Dashboard bearer alone is insufficient. Requires `RIVERVIEW_SNAPSHOT_GITHUB_REPOSITORY` and systemd `snapshot-github-token`; errors retain browser local-download fallback. |

The **Snapshot** action generates one bounded, redacted ZIP Blob,
posts that Blob through the authenticated archive endpoint, checks the confirmed
response's SHA-256 and byte count against the same Blob, and requests a browser
download from it. The result retains the GitHub Release URL, a **Copy GitHub
Link** action, and a **Download ZIP** retry link. Archive failure is reported
while the browser download is still requested. If starting the browser download
throws after archive success, the verified archive remains linked and the local
retry link stays available. Browser APIs do not confirm that a user saved the
file, so the interface says that a download was requested. The local link also
supports local-only fallback without creating a server-side ZIP copy.

New manifests identify `dashboard_version`, `capture_id`, `captured_at`, and
`source_commit`. V1 and V2 assets are named
`riverview-v1-<capture-timestamp>-<capture-id>.zip` and
`riverview-v2-<capture-timestamp>-<capture-id>.zip`, respectively; both use
the configured shared private archive repository and the same endpoint. Older
V1 manifests without `dashboard_version` remain accepted as V1. The isolated
V2 shell is currently a separate fixture-only interface; its button remains
disabled until its authenticated API integration is implemented and browser
verified. Backend V2 package acceptance is not evidence of V2 UI acceptance.
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

The objective-grounding provider uses `RIVERVIEW_KNOWLEDGE_ROOT` and
`RIVERVIEW_KNOWLEDGE_COMMIT`, independently of dashboard identity. Set both to
the immutable approved knowledge package and its exact source commit. Do not
reuse `RIVERVIEW_SOURCE_COMMIT` as the knowledge pin. The provider resolves the
configured root when the Dashboard process starts, so restart only the Dashboard
after changing the knowledge package pointer or pin.

The status response schema identifier is `rv.dashboard.status.v1`; it includes Grace execution heartbeat and freshness when the runtime migration is installed. Active workers configured in Grace are matched to the capability snapshot written with Grace's heartbeat and to their active `work-order:engineering` registration; an idle capability can therefore be healthy without an active assignment lease. Workers not present in that live capability snapshot continue to use their latest assignment-lease heartbeat and remain unknown or stale when there is no fresh lease evidence. `GET /api/v1/workers` exposes the telemetry source, live registered capabilities, last Grace heartbeat, last lease heartbeat, scope, and active lease count separately. This is process/configuration readiness evidence, not proof that every remote worker dependency is reachable or that a specific assignment is authorized. List/detail
responses carry `status`, bounded `items`, and pagination state. Database
unavailability returns a status projection whose `projection_status` is
`unavailable`; HTTP query failures return 503. A reachable PostgreSQL instance
with missing required relations returns HTTP 200 with `status=not_initialized`;
this is a valid domain state, not a transport failure. The browser skips the
optional attention query while its relation is absent and displays that state.
CME values are
`healthy`, `degraded`, `stale`, `unavailable`, or `not_initialized`; a missing
heartbeat is unknown/not initialized, never healthy. A configured Grace worker
capability is healthy only while present in the persisted runtime capability
snapshot and the Grace service heartbeat is fresh and healthy. Other worker
status is derived from recorded assignment-lease heartbeats; no lease means
`unknown`. A future-dated heartbeat is `unverified`. Event time/correlation is retained as
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

Selecting a cross-workflow jump loads the registered destination graph, verifies
the exact `jump_target_id` is present, focuses that node, and displays its detail.
The viewer retains the source workflow and originating jump node in the current
page session. Its **Back to source node** control restores that workflow and
focuses the originating jump. Selecting another workflow from the selector starts
a new navigation path. If the target graph or node cannot be loaded, the viewer
reports it as unavailable and keeps the return control available.

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

The browser ZIP exporter caps total uncompressed member payload at 96 MiB and
reserves 4 MiB for the manifest. ZIP headers add small overhead to the final
download and are not part of the uncompressed member-byte check. It always preserves the bounded
operational/browser diagnostics, sanitized HTML, page/workflow JSON, workflow
status and SVG. PNG previews and detail tiles have a 76 MiB cumulative ceiling within the 96 MiB
uncompressed member cap. At that ceiling, 16 MiB remains available for structured
HTML/JSON/SVG/status/diagnostics and 4 MiB is reserved for the manifest; unused
raster headroom is also available to required members. If a PNG would cross either
limit, only that raster preview or tile is omitted; each omitted path and reason
is recorded, affected visual status is `incomplete`, and `capture_complete` is
false. The manifest reports uncompressed bytes by component category. A mandatory
non-raster member that exceeds the hard package ceiling fails with its member
path and attempted/cap byte counts. No server limit or diagnostic redaction
rule changes.

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
owner-only under the Steward account. Dashboard runtime APIs include narrowly
authorized conversation and stream-record writes; migration 0008 grants the
conversation runtime only SELECT/INSERT/UPDATE on
`resident_conversation_streams`. The process has no DDL or startup-migration path.
See `deploy/riverview-status-dashboard.service` and
`docs/components/STATUS_DASHBOARD_COOKBOOK.md`.

Deployment procedure copies a verified commit to a versioned root-owned
`/opt/riverview-status-dashboard/releases/<commit>` directory, verifies the
package hash, updates only the dashboard `current` symlink and new dedicated
systemd unit, and captures the existing symlink/unit before first install.
Rollback restores that symlink/unit from the recorded predecessor and restarts
only the dashboard unit. Conversation-stream migrations are applied separately
through the reviewed migration runner after protected backup and checksum
preflight.

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

### Authenticated hardware and inference telemetry

`GET /api/v1/resources/telemetry` is protected by the same `_authorized()` account-session or Dashboard bearer gate as every other projection. It is a request-driven, uncached read; writes return `405`. The collector has fixed Camrui and OCTOMINER1 model endpoint allowlists and one OCTOMINER1 GPU source using `nvidia-smi` over a dedicated SSH identity. That identity is delivered with systemd `LoadCredential`, requires strict host-key checking, and is forced on the GPU host to `/usr/local/libexec/rv-gpu-telemetry` with no PTY, forwarding, or arbitrary command. The remote command exposes only GPU name/index, utilization, memory, temperature, power, fan when supported, and allowlisted Grace service labels; UUIDs and PIDs are discarded before returning to the Dashboard.

The model projection includes a bounded numeric `slot_context` view from each fixed llama.cpp `/slots` endpoint: slot index, processing boolean, configured context tokens, prompt-token count, processed prompt-token count, and cached prompt-token count when present. Raw task IDs, prompt text, token data, and arbitrary slot fields are discarded. Context counts are per slot; server capacity is the sum of measured per-slot capacities and must not be presented as one slot's limit. Current server builds expose no KV-cache allocation bytes and `/metrics` returns not-supported, so `kv_cache_bytes` is explicitly unavailable. Queue depth remains unavailable. This extension does not alter model startup parameters or inference behavior.

Model readiness is sampled from the configured llama.cpp `/health`, `/v1/models`, and `/slots` endpoints. Only safe model basenames and the count of processing slots are projected. The current servers do not expose request queue depth or metrics; queue state therefore remains `unavailable`, never zero. OctoMiner2 has a documented inventory row but its identity/source is not independently verified; its projection remains unavailable. Camrui's GPU inventory is unavailable, while its local 0.6B model endpoint may report readiness and model identity. No inference controls, prompt data, slot details, PIDs, GPU UUIDs, or host credential data are exposed.

The projection schema is `rv.dashboard.resource-telemetry.v1`. Per-source state and source observation timestamps remain visible. Missing credentials, host-key mismatch, source timeout, invalid source data, and unavailable host APIs remain unavailable with sanitized error codes. The Dashboard does not cache prior observations. Operational credential installation and rollback are documented in `STATUS_DASHBOARD_COOKBOOK.md`.

Grace activity is correlated through its durable conversation and response request IDs. Active streamed output is measured only from persisted provider text deltas with database timestamps and character counts; the dashboard may show received streamed characters/second after two timed deltas. This is not model-server token throughput, prompt processing, or GPU work. The current 0.6B/80B/30B `/metrics` endpoints return HTTP 501; `/slots` exposes occupancy and prompt/context fields but no output-token counter. Completed token throughput remains a separate router-call measurement.

## Mounted storage capacity projection

`GET /api/v1/resources/telemetry` adds `storage_status`, `storage_observed_at`, and per-host `storage` records in the same authenticated response. Camrui volumes are read with Linux mountinfo plus `statvfs`; OCTO1 volumes are supplied by the existing restricted `resource-telemetry` forced command. The collector admits only supported persistent filesystems, deduplicates bind aliases and shared network filesystems, and returns total/used/available bytes, percent used, mount point, filesystem/device identifier when available, and observation timestamp. Windows development and OCTO2 remain explicitly unavailable until an approved host collector exists. Unavailable measurements are not zero and are excluded from aggregate totals. Collection is request-driven and read-only; no capacity change, mount action, cleanup, or storage scheduling occurs.

Read-only collection on Camrui was compared against `df -B1 -T / /boot/efi` on 2026-10-22; exact total/used/available byte values and timestamps are retained in `evidence/v2-storage-20261022/camrui-mount-observation.json`. This observation validates only Camrui. The current deployed OCTO1 forced-command does not yet emit mount capacity, and Windows development/OCTO2 remain unconnected.

## V2 same-origin snapshot integration

The dashboard package serves the V2 shell at `/v2/` and its allowlisted assets at `/v2/assets/`. This path uses the dashboard HTTPS origin so the browser can reuse the existing Steward account session and CSRF cookie. The V2 interface calls only the existing `/api/v1/status`, `/api/v1/snapshot`, and `/api/v1/snapshot/archive` routes; archive authorization, Steward role checks, CSRF validation, redaction declaration validation, and the private GitHub Release credential remain server-side. The browser never receives the GitHub credential.

A V2 package uses `rv.website.diagnostic-snapshot.v1`, records `dashboard_version: v2`, capture ID, capture time, source commit and deployment ID, and names the asset `riverview-v2-<timestamp>-<capture-id>.zip`. Its V2 workspace state is separate from common authenticated dashboard diagnostics. One generated Blob is submitted to the archive endpoint and handed to the browser download. An archive error leaves the local download available; an archive receipt is shown only after the endpoint response matches the capture identity, size and digest.

The independently authenticated LAN preview on port 8877 remains fixture-only and local-download-only. It does not call the dashboard API or archive endpoint. To use V2 archival, open `/v2/` from the authenticated HTTPS dashboard origin.
