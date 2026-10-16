<!-- Riverview~ Controlled Document
File: docs/components/STATUS_DASHBOARD_COOKBOOK.md
Component: STEWARD-DASHBOARD
File Revision: 1.1.16
Purpose: Troubleshoot and recover the read-only status dashboard
Authority: Diagnostic and read-only operations only
Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Link consolidated recovery guide and correct CME unit name
Changed: 2026-10-11 UTC | RV-M3.2-001 | Link durable notification receipt diagnostics
Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-CURRENT-DOCS-RELEASE | Document immutable composite docs release provenance and verification
Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Require checksum-verified stream-delivery migration before enabling SSE
Changed: 2026-10-15 UTC | RV-WEBSITE-PL027 | Add expected cross-workflow target focus and return-path diagnostics
Changed: 2026-10-15 UTC | RV-WEBSITE-PL025 | Record isolated account-cookie workflow browser regression and production access limitation
Changed: 2026-10-15 UTC | RV-WEBSITE-PL026 | Explain workflow selector, canvas interaction, revision labels and static legend
Changed: 2026-10-15 UTC | RV-WEBSITE-PL004 | Document persisted assignment graph/node references, missing states and safe diagnostic links
Changed: 2026-10-15 UTC | RV-WEBSITE-PL008 | Explain worker registration versus heartbeat health and bounded inventory totals
Changed: 2026-10-15 UTC | RV-WEBSITE-PL006 | Clarify overview cursor, projection, component health and Grace execution meanings
Changed: 2026-10-15 UTC | RV-WEBSITE-PL011 | Explain older/newer sequence paging and activity cursor recovery
Changed: 2026-10-15 UTC | RV-WEBSITE-PL012 | Explain event provenance and projection diagnostic limits
Changed: 2026-10-15 UTC | RV-WEBSITE-PL014 | Explain projection refresh, cache, freshness and status transitions
Changed: 2026-10-15 UTC | RV-WEBSITE-PL016 | Document reusable named-tab navigation and Firefox verification.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL010/015/020/023/024 | Explain Grace readiness, chat controls, action states and milestone copy.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL019 | Document independent transcript scrolling and narrow-screen composer recovery.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL036 | Document navigation rail preferences, accessible states, and compact affordances.
Changed: 2026-10-15 UTC | RV-WEBSITE-PL003 | Document exact graph/node title lookup and unresolved-title behavior.
Changed: 2026-10-16 UTC | RV-WEBSITE-PL029 | Explain delivery, person-seen, receipt and decision lifecycle boundaries.
Changed: 2026-10-16 UTC | RV-WEBSITE-PL038 | Add searchable graph registry traceability catalog and qualify references.
Changed: 2026-10-16 UTC | RV-WEBSITE-PL038-POST-PR45 | Link the final post-integration browser verification.
History: Git and revision/backup manifest
-->
# Status dashboard read-only troubleshooting cookbook

The dashboard links to the [complete Riverview operations and recovery guide](RIVERVIEW_OPERATIONS_COOKBOOK.md), covering PostgreSQL, migrations, CME, event processing, workers, verification, and backups.
The [notification delivery contract](NOTIFICATION_DELIVERY.md) and
[notification troubleshooting cookbook](NOTIFICATION_DELIVERY_COOKBOOK.md)
cover durable visual receipts. Receipt acknowledgment is not a Steward decision.

**Task:** RV-M3.1-001 · **Component:** STEWARD-DASHBOARD · **Execution model:** request-driven.  
The dashboard does not own assignments, dispatch workers, mutate the ledger, or
gate CME execution.

## Readable diagnostic documents and workflow viewer

Dashboard diagnostic-reference links open a formatted HTML presentation of
controlled component Markdown. The renderer formats headings, tables and code
blocks, hides file-metadata comments, escapes source HTML, and emits no scripts.
Only HTTPS, in-page anchors and component-document links are clickable. The
controlled Markdown remains the source; there is no parallel HTML document.

The **Workflows** view reads authenticated `GET /api/v1/graphs` and
`GET /api/v1/graphs/<graph_id>` projections from the deployed
`process_graphs/*/*.json` registry. It shows graph revision, stable node IDs,
node type, typed transitions and cross-workflow jump destinations. Selecting a
node shows its source, documentation and evidence references. Following a jump
loads the target workflow, checks the exact target node ID, focuses it and shows
its details; **Back to source node** restores the originating jump. A missing
target is shown as unavailable and retains that return path. A disabled jump
button means the target workflow is not present in the loaded graph index. The
browser is read-only. It highlights live execution only when the API supplies an exact
persisted process-node identity with a current execution position. Assignment detail
also displays the nullable `process_graph_id` and `process_node_id` fields as recorded;
those references alone do not establish that execution is currently at that node.
Missing identity is shown as not recorded and is never inferred.

The **Documentation and diagnostics** view replaces the fixed Activity and
Workflows diagnostic shortcuts with a searchable index built on demand from the
same authenticated graph registry. It displays each registered graph's component,
workflow, graph revision, process/failure/recovery nodes, linked component
troubleshooting documents, source provenance, and declared test/evidence
references. A search narrows matching nodes and references within each matching
workflow. Component documents retain the freshness and recovery instructions;
the index does not manufacture a freshness value. Declared evidence paths are
traceability pointers only: they do not establish that a test passed or prove
semantic test coverage. If a workflow has no declared references, the interface
states that none are declared. The index is limited to the first 50 registry
entries and reports the returned workflow count; review the Workflows view for
interactive graph inspection.

An unknown graph ID returns `404 process_graph_not_found`. Source unavailability
is displayed as unavailable, with no stale highlight. Check the canonical source
and generated views locally:

Use the **Workflow** selector to switch among registered graphs. Select a node
with a mouse click or keyboard Enter/Space to show its stable ID, node revision,
and available references. The graph revision label describes the loaded graph;
each selected node reports its own revision. The process/decision/failure/recovery
legend is a visual key, not a set of controls. Both the graph registry and graph
detail requests use same-origin browser credentials, so an active account session
cookie is sufficient; the workflow viewer does not require a recovery bearer token.

The isolated browser regression can be run without production access:

```sh
python3 scripts/verify_workflow_account_cookie_browser.py \
  --output evidence/checkouts/WEBSITE-PL025/<new-run-directory>
```

It uses a synthetic account-cookie fixture and the checked-out `workflow.js`; it
does not establish acceptance against a deployed account or release. For live
acceptance, run the deployed dashboard browser check after account-session access
is available and retain its redacted report and screenshots.

### Assignment graph and diagnostic references

Assignment detail displays the persisted `process_graph_id` and
`process_node_id` values returned by the read-only assignment projection. A
missing value appears as “No … ID recorded”; do not derive an ID from the
workflow label, step name, event text, or current graph. These assignment
references are not by themselves proof of current live execution position.
The diagnostic reference is linked only when it matches a component Markdown
document path accepted by the dashboard route; unknown reference formats remain
plain text.

Reproduce the assignment-detail check without production access:

```sh
python3 scripts/verify_assignment_graph_linkage_browser.py \
  --output evidence/checkouts/WEBSITE-PL004/<new-run-directory>
PYTHONPATH=.:src pytest -q tests/test_status_dashboard.py -k assignment_detail_exposes
```

The Firefox fixture uses synthetic assignments with both populated and missing
identity fields. It checks the displayed IDs, explicit missing state, safe
cookbook URL, account-cookie-only API requests, and absence of browser errors.
It does not verify production data or prove that the referenced node is a live
execution position. If the database projection omits either value, inspect the
assignment's persisted nullable fields through the approved read-only source;
do not backfill or alter ledger records as a presentation repair.

```sh
python3 scripts/process_graph.py check
python3 scripts/revision_control.py check --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json
```

If a registered jump does not resolve, inspect its `jump_target_id`, verify that
the destination graph and node IDs exist, then run the graph check above. If the
destination request fails in the browser, use **Back to source node** to restore
the prior context; the viewer does not infer a substitute target. The canonical
navigation path is recorded in `process_graphs/steward-dashboard/status.json`.

The service reads from its selected root-owned release. Deploy a new verified
full-SHA release to update code and graph data together; never hot-edit the
installation or copy an uncommitted graph.

Run the reproducible, read-only Firefox commissioning check on Camrui with an
assignment that has a completed worker attempt and independent verification:

```sh
python3 scripts/verify_status_dashboard_browser.py \
  --assignment-id <completed-assignment-id> \
  --output /tmp/riverview-dashboard-browser-check
```

The protected token path defaults to `/home/admin1/.config/riverview/status-dashboard.token`.
The utility refuses a permissive token file or existing output directory, never
prints the token, and writes a redacted JSON report and browser screenshots only
to the requested new directory. It verifies live status/attention/assignment
routes, browser JavaScript parseability, graph nodes/decisions/transitions/jumps,
formatted cookbook safety, navigation, and browser errors. It does not mutate
assignments or services.

## CME attention endpoint and 503 responses

Before the M2.4 migration, `/api/v1/attention` returned HTTP 503 when the
`cme_monitor_events` relation was absent. The projection correctly reported
`status=not_initialized`, but the HTTP status caused the browser to record a
request error on each refresh interval. A missing optional relation is now
returned as HTTP 200 with the explicit `not_initialized` domain status, and the
browser skips polling that endpoint until the status projection confirms the
relation exists. An actual database/query failure still returns HTTP 503.

Check relation and service state before diagnosing repeated errors:

```sql
SELECT to_regclass('riverview_dev.cme_monitor_events') AS attention_relation;
SELECT service_id,status,last_heartbeat_at,last_scan_at
FROM riverview_dev.cme_monitor_health;
```

Use `/api/v1/status` to distinguish a missing relation from an unavailable
source. Do not interpret HTTP success with `status=not_initialized` as evidence
that CME monitoring is operational.

## Credential delivery

The unit loads pgpass with systemd LoadCredential. Its root-owned read-only
0440 mount is validated with runtime_baseline.systemd_credential_path, then
copied with copy_systemd_credential to /run/riverview-status-dashboard/pgpass
inside the service-owned 0700 RuntimeDirectory. This produces the 0600 passfile
required by libpq. The token remains a separate credential and is never logged.

## Worker health

The overview shows rows from the bounded, keyset-paginated
`GET /api/v1/workers` inventory. Each row separates registry state (`active`,
`inactive`, or unknown) from heartbeat health (`healthy`, `stale`, `unknown`, or
`unverified`). An inactive registration is labeled **Registry inactive**; it is
not described as a heartbeat result. Health is derived from the latest
assignment-lease heartbeat; a missing heartbeat is unknown, a future heartbeat
is unverified, and expired lease does not mean a worker is healthy.

Inventory totals count only records in pages already loaded. The summary says
**more records available** while a cursor remains and **all records observed**
after the final page. Do not treat a partial-page count as a registry-wide
total. A missing worker/lease relation is `not_initialized`; a read failure is
unavailable, and neither state fabricates worker health.

The isolated regression covers active and inactive registrations, healthy,
stale and unknown heartbeat states, reconciliation after loading the final
page, and a narrow browser viewport:

```sh
python3 scripts/verify_worker_inventory_browser.py \
  --output evidence/checkouts/WEBSITE-PL008/<new-run-directory>
PYTHONPATH=.:src pytest -q tests/test_status_dashboard.py -k worker_inventory_separates
```

The fixture is synthetic and read-only; it does not claim live worker inventory
or host, task, capability, execution or failure detail that the API does not
provide.

## Overview status labels

The event cursor is the last observed institution event sequence; it is not a
total event count. Projection health and freshness describe the bounded,
read-only ledger query. CME and worker states come from their own monitor or
lease heartbeat observations and can differ from projection health. Grace
execution status reports whether its execution projection and heartbeat are
available; `not_initialized` there does not mean that the separate chat surface
is unavailable. Use the source-specific state and observation time shown in
each card; do not infer one subsystem's health from another subsystem's label.

Status refresh uses same-origin `fetch` with browser cache bypass
(`cache: no-store`). The header time is the API's `observed_at` value, not
the browser's refresh time. A successful required ledger read reports
`projection_status=healthy` and `freshness=current`; a reachable database
missing required ledger tables reports `not_initialized` and
`freshness=unknown`; a database/query failure reports `unavailable`.
Refresh errors replace the freshness display with an unavailable message and
do not present last-known values as current. A manual refresh and periodic
status polling request a new bounded projection; event and detail refreshes
are separate requests. A successful response with optional-relation
`status=not_initialized` is a domain state, not a transport failure.

## Activity event paging

The Activity view keeps events in ascending sequence order. **Load older
events** requests `before_seq` using the first visible sequence and prepends the
returned page. **Load newer events** requests `after_seq` using the last
observed sequence and appends results. Both cursors are exclusive; repeated or
overlapping responses are deduplicated by `event_id`. The newer control can
check for events beyond the current tail, while background refresh continues
to use the same last-sequence cursor. Event payloads remain excluded from this
projection.

The isolated Firefox regression exercises initial, older and newer pages and
checks sequence order and duplicate suppression together with the adjacent
overview and worker states:

```sh
python3 scripts/verify_worker_inventory_browser.py \
  --output evidence/checkouts/WEBSITE-PL011/<new-run-directory>
PYTHONPATH=.:src pytest -q tests/test_status_dashboard.py -k activity_has_explicit
```

### Event meaning and provenance

Activity cards humanize the event type and show the recorded timestamp,
sequence/event identity, actor, correlation and causation IDs, payload schema,
and the related assignment link when present. A missing causation ID is shown
as a root event with no parent recorded. Assignment identity is the task
reference currently available in this projection; service events have no
assignment task reference.

The bounded event projection excludes payload bodies and does not provide an
event-specific diagnostic reference or a separate task ID. The card labels
those limits and links to this cookbook as the dashboard-level troubleshooting
entry point. Do not infer a task, parent event, or diagnostic from the event
type. To investigate a particular event, use its recorded event/correlation/
causation IDs with the authoritative event owner and retain the payload
redaction boundary.

## Fast read-only checks

```sh
systemctl is-active riverview-status-dashboard.service
systemctl show riverview-status-dashboard.service -p ActiveState -p SubState -p MainPID
curl --fail --silent --show-error http://127.0.0.1:8766/
ss -ltn '( sport = :8766 )'
```

Use a browser Authorization token from the protected Steward credential for
`/api/v1/*`; never put it in a URL, shell history, report or log. The unit's
standard output records service identity/commit only; journald excludes request
URLs and headers. A dashboard credential may be rotated by updating its
owner-only source file and restarting only this unit. Do not read or replace the
existing PostgreSQL credential.

## State meanings

| Display | Meaning | First check / recovery |
| --- | --- | --- |
| `healthy` | A successful bounded read of the initialized ledger; a healthy CME/worker state additionally needs a fresh recorded heartbeat. | Check `observed_at`, source commit, service identity and component-specific heartbeat. |
| `stale` | A persisted heartbeat is older than the configured 30-second freshness window. | Check only the owning service's unit/journal and database reachability; do not restart unrelated services. |
| `degraded` | CME recorded a failure or missing successful scan while still reachable. | Use `systemctl status riverview-cme-monitor.service` if installed and the CME cookbook. Dashboard does not restart CME. |
| `not_initialized` | PostgreSQL is reachable but the requested component tables/health row do not exist. | Confirm selected database/schema/migration ledger. Never run DDL from dashboard startup. |
| `unavailable` | No trustworthy current read was returned. Browser last-known data is not labelled healthy. | Check PostgreSQL and dashboard journal; retry after cause is resolved. |
| `unknown` / `unverified` | No lease heartbeat exists or a timestamp is future-dated. | Preserve uncertainty; inspect source clock/lease evidence. |

## Process-first fault isolation

| Workflow node | Expected evidence | Failure signal | First diagnostic | Recovery and resume |
| --- | --- | --- | --- | --- |
| Request and authenticate | HTTP request ID and successful bearer comparison | HTTP 401, 400 invalid Host, 405 write method | Browser request state; verify loopback URL and protected token source | Re-enter authorized token; never relax loopback/verb checks. |
| Open read-only projection | PostgreSQL read transaction, schema and current observation timestamp | `projection_unavailable`/503 or status `unavailable` | `systemctl status riverview-status-dashboard.service`; inspect sanitized journal error type | Resolve DB/socket/credential availability; GET again. Dashboard makes no writes. |
| Detect initialization | relation and migration inventory | `not_initialized` | status `relations` and source schema | Correct service configuration or separately authorized migration; restart is not a migration. |
| Project lifecycle/events | bounded page, institution privacy filter, event cursor | empty/not found or page source error | assignment ID, event sequence and correlation ID | Inspect ledger contract; use next keyset/sequence cursor; no full history rebuild. |
| Render/update | local tab switch and localized view update | browser-local sanitized error entry | snapshot browser error ring and request ID | Refresh affected panel only; slow/unavailable DB must not hold navigation. |
| Export snapshot | bounded JSON file and explicit redaction metadata | snapshot bound exceeded or API failure | browser-local recent error code and captured timestamp | retry after page refresh; export includes no credentials or event payload. |
| Restart/reconnect | same release/port; current state re-read from PostgreSQL | systemd failed/inactive or authentication lost | `systemctl status` and `journalctl -u ... -n 50 --no-pager` | restart only the dashboard unit; reauthenticate; CME and assignments continue independently. |

## Deployment and rollback

1. Record current dashboard symlink and unit checksum before first install/change.
2. Verify package manifest against committed source and install only to a new
   versioned release directory owned by root and not writable by `riverview`.
3. Provision the bearer token through an owner-only file and systemd credential;
   preserve existing DB credentials and deliver them through the existing
   `LoadCredential=pgpass:/etc/riverview/pgpass` contract.
4. Configure only `riverview-status-dashboard.service`, bound to `127.0.0.1:8766`.
5. Check the versioned release/commit, service identity, loopback listener and
   authenticated status read. Restart this unit once and repeat the check.
6. On failure, stop only the dashboard service, restore its prior unit/link from
   the deployment record, reload systemd and restart only that unit. Confirm the
   event processor and baseline service did not change.

The durable Grace conversation stream requires the resident-execution migration
`0008_resident_conversation_stream_delivery.sql`. Before activating an integrated
release that enables SSE, verify all earlier resident-execution migration checksums,
then apply only a missing reviewed migration through the established migration
runner after a protected backup and disposable restore. This migration adds one
stream-delivery table and grants the runtime role SELECT/INSERT/UPDATE on that
table only; it does not change authority permissions or canonical conversation
history. Dashboard startup never applies migrations. If the migration is absent,
has a checksum mismatch, or the runtime table ACL is incomplete, stop activation;
do not fall back to broad database privileges. The legacy non-streaming API remains
available for clients that cannot stream.

For a docs-only release, preserve the existing dashboard executable and static
assets; install updated component documents and synchronized canonical graph
views into a new root-owned immutable release directory. Preserve predecessor
releases. Record the dashboard code commit separately from the documentation
and graph commit in a release manifest and checksum list. Keep `source_commit`
bound to the code commit, set a unique deployment identifier, and change only
the dashboard systemd unit and `current` release link. Verify all documented
routes and process graphs against the candidate before switching; after restart
verify loopback HTTP, authenticated status, service health and dependent service
continuity. On failure restore only the prior dashboard link/unit and restart
only `riverview-status-dashboard.service`.


## Documentation tab and return navigation (PL-NEW-016)

The dashboard sets its browsing-context name to `rv-dashboard-main`. Same-origin
allowlisted component documentation links target `rv-dashboard-documentation`,
so opening a later guide reuses that documentation tab. The rendered guide's
“Riverview dashboard” link targets the named main context and preserves its
existing tab. These links intentionally omit `rel=noreferrer`: that relation
implies `noopener`, which prevents reuse of a named browsing context. This only
applies to trusted same-origin documentation links.

Verify the full behavior in an isolated Firefox fixture:

```sh
python3 scripts/verify_worker_inventory_browser.py \
  --output evidence/checkouts/WEBSITE-PL016/<new-unique-run>/
```

The account-cookie fixture must report `documentation_link_uses_reusable_named_tab`,
`documentation_return_reuses_dashboard_window`, and
`second_document_reuses_documentation_tab` as true, retain exactly two
browsing contexts, and report no browser errors. Latest evidence:
`evidence/checkouts/WEBSITE-PL016/20261015T212500Z-documentation-navigation/`.
The earlier failed iteration is retained separately and is not acceptance evidence.


## Grace readiness, chat controls and milestone labels (PL-NEW-010/015/020/023/024)

Grace conversation access and durable objective execution are separate surfaces.
An available conversation does not prove the objective schema, Grace executor,
CME dispatcher or workers are commissioned. If the objective source reports
`not_initialized`, verify the selected database/schema and reviewed resident
execution migration inventory. Refresh only re-reads the projection; dashboard
startup and Refresh never apply migrations or commission runtime services. Use
the [Grace execution commissioning cookbook](GRACE_EXECUTION_COOKBOOK.md) for
its authorized service and migration checks.

In the conversation view, Disconnect ends the browser's Grace session and hides
the transcript while persisted history remains. Refresh history reloads the
selected saved conversation. Enter sends; Shift+Enter and Insert line break add
a newline. Menu options marked unavailable or future remain disabled. The M3.1
header names the dashboard milestone; roadmap progress, deployed release, and
commissioning acceptance are independent records.

The isolated Firefox run `evidence/checkouts/WEBSITE-CLARITY/20261015T215000Z-guidance-and-controls/` verifies the `not_initialized` case, wording, all seven menu action states, and milestone label. It does not establish production acceptance.


## Conversation clipping and composer recovery (PL-NEW-019)

The transcript owns its own vertical scroll area. The message composer follows
it in document flow instead of sticking over the transcript; after a long history,
scroll the page to the composer while the transcript retains its last-message
scroll position. At narrow widths, the dashboard header stacks and wraps its
account controls so they do not force document-wide horizontal scrolling.

The isolated fixture supplies 40 long synthetic messages and checks that the
transcript overflows vertically, remains at its last message after page scrolling,
and the composer is visible below it without horizontal overflow. The browser
request for 390px was clamped by Firefox to a 500px CSS viewport; physical-device
verification below that width remains open. Passing evidence:
`evidence/checkouts/WEBSITE-PL019/20261015T224500Z-conversation-layout/`.


## Collapsible navigation (PL-NEW-036)

Use the rail control labelled “Collapse navigation” to switch to the compact
icon state; it becomes “Expand navigation” while compact. The preference is
saved in this browser. Every view button retains an accessible name when its
visible text is compacted. The health dot exposes the current source health as
accessible text, and the snapshot download remains available in compact mode.
The application defaults to compact navigation on screens at or below 920px
when no preference has been saved.

The isolated browser run verifies both states, ARIA expansion values, navigation
labels, health status and snapshot visibility. Evidence:
`evidence/checkouts/WEBSITE-PL036/20261015T231000Z-collapsible-navigation/`.


## Assignment task titles and IDs (PL-NEW-003)

Assignment rows retain the stable assignment ID. When both persisted process
graph and node IDs are present, the browser retrieves that canonical graph and
uses the exact matching node's registered label as the task title. The detail
view retains assignment, workflow, graph, and node IDs alongside the label. If
either ID is missing, the graph is unavailable, or the exact node is absent, the
UI reports the title unavailable and does not guess from `workflow_step`.

The authenticated graph API is read-only. The isolated Firefox fixture verifies
a registered title, stable identifiers, explicit missing references, and
cookie-only graph requests. Evidence: `evidence/checkouts/WEBSITE-PL003/20261015T233000Z-canonical-task-title/`.
Assignment purpose, request, deliverable, result, acceptance criteria, evidence,
and blocked-action details are not in this projection; those remain blocked on
the integration-owned assignment contract recorded in the recovered punch list.


## Notification delivery, person-seen, receipt and decision state (PL-NEW-029)

The notification API's `delivered` state means an authenticated dashboard client
confirmed rendering while the Notifications view was visible. It does not report
that a person saw the message. The website explicitly shows “Person seen: not
reported by this source.” `acknowledged` records a separate receipt action and
has no decision authority. A linked decision request and its current status are
shown separately; an `attention_resolved` event describes the attention
condition, not approval, denial, or decision resolution.

The current API has no `seen_at`/`seen_by` state and M3.2 has no decision
resolution operation/outcome contract. Full PL-NEW-029 closure requires the
integration owner to define sourced decision outcomes (`approved`, `denied`,
`resolved`) with actor/time/provenance and preserve the distinction from delivery
and receipts. The website must not infer those states. Passing isolated evidence:
`evidence/checkouts/WEBSITE-PL029/20261016T001000Z-notification-state-clarity/`.


## Searchable workflow and diagnostic catalog (PL-NEW-038)

The Documentation and diagnostics navigation view queries the authenticated
canonical graph index and its graph details when opened. It displays component
and graph revision, process/failure/recovery node labels, component-document
links, source provenance, and declared test/evidence references. Search narrows
matching workflows and then filters their nodes and references. Activity and
Workflows diagnostic shortcuts open this index; the allowlisted documentation
links open in the reusable documentation tab.

The registry currently declares document/source/evidence paths, not effective
freshness policies or semantic coverage outcomes. Use the linked component
documents for freshness/troubleshooting instructions. A reference path does not
mean its test passed, and it is not a semantic coverage result. Full PL-NEW-038
acceptance remains blocked until an authoritative source provides attributable
freshness metadata and test-coverage outcomes. Isolated Firefox evidence:
`evidence/checkouts/WEBSITE-PL038/20261016T023000Z-post-PR45-regression/`.
