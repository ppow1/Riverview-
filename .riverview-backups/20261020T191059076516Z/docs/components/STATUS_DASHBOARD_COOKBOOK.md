<!-- Riverview~ Controlled Document
File: docs/components/STATUS_DASHBOARD_COOKBOOK.md
Component: STEWARD-DASHBOARD
File Revision: 1.1.31
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
Changed: 2026-10-16 UTC | RV-WEBSITE-PR42-PRODUCTION-ACCEPTANCE | Record the installed immutable website release, verified Camrui access route, acceptance boundaries, and rollback target.
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Document capability-registered offline snapshot contents, authority and troubleshooting
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Document Windows local-CA trust diagnosis and workflow viewer controls
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Record PR #65 source reconciliation and full-inventory ZIP verification
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Document privacy-filtered document navigation timing in browser diagnostics
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Distinguish synthetic full-inventory fixture verification from actual-dashboard acceptance
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Record read-only Camrui release, proposal registry, and strict TLS status evidence
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Link final exact-source browser export and offline integrity report
Changed: 2026-10-16 UTC | RV-WEBSITE-PR71-PRODUCTION-ACCEPTANCE | Record immutable Camrui release, strict-TLS snapshot verification, permission-bounded completeness, and rollback evidence
Changed: 2026-10-16 UTC | RV-WEBSITE-PR67-SNAPSHOT-CSP-FIX | Record f957 production installation, migration evidence, partial live acceptance and the CSP rasterization correction.
Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Record real-dashboard DOM verification and complete responsive long-page tile captures
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Document raster budget fallback, package-size diagnostics, and ZIP recovery checks
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Document the 76 MiB raster ceiling and structured-content reserve
Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Document optional private GitHub Release archive provisioning, errors, retention and recovery.
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

## Download Snapshot and offline diagnostics (PL-NEW-041)

**Download Snapshot** creates one ZIP in the current browser session. It uses the
versioned authenticated capability registry at `GET /api/v1/capabilities`, the
existing read-only `GET /api/v1/snapshot` projection, and the current workflow
registry exposed by `GET /api/v1/snapshot/workflow-index` plus authenticated
`GET /api/v1/graphs/<graph_id>` reads. The workflow definitions are the checked-in
`process_graphs/*/*.json` files; PostgreSQL contributes only the already exposed
runtime execution-position projection, not canonical graph definitions. No
workflow registry or operational source is inferred by the browser exporter.

The ZIP schema is `rv.website.diagnostic-snapshot.v1`. It contains the live
capability registry, per-page inventories, sanitized offline HTML with dashboard
CSS, full-content SVG/PNG visual maps, bounded recent browser diagnostics, the
existing redacted operational snapshot, and one original canonical graph JSON,
runtime-status JSON, and full-extent SVG per workflow. PNG previews and overlapping
detail tiles are included while they fit the raster budget. `workflow-index.json`
includes counts, source paths, file references, available runtime state, and
outbound/incoming jump references.
The graph JSON is copied from the authenticated API with its transient status
projection kept separately; node and edge IDs and all represented fields stay
unchanged. Page visual maps annotate controls with their registry IDs and each
page JSON records the view, control states, dimensions, and visual outcomes.

Only pages reachable through the current user's existing navigation are
captured. An unavailable page/control, incomplete image, graph/API failure, or
oversized page is identified in the manifest. The capability registry describes
features; it does not assert that actions work. Coverage reports controls as
rendered, available, disabled, unavailable, or not observed, and lists rendered
controls with no registry entry. Current account permissions are respected.

### Private GitHub snapshot archive

Archival is enabled only when the dashboard unit is deliberately configured
with `RIVERVIEW_SNAPSHOT_GITHUB_REPOSITORY=OWNER/PRIVATE_REPOSITORY` and a
systemd `LoadCredential` named `snapshot-github-token`. Keep the token in a
root-owned protected source file (for example
`/etc/riverview/snapshot-github-token`); never put it in an environment file,
repository, command line, dashboard HTML, JavaScript, or browser storage. Use a
fine-grained token scoped only to the dedicated private repository with
contents read/write permission. Releases are created as drafts, uploaded, and
then published; the backend verifies that GitHub reports the repository as
private before creating a release. Do not configure a public repository.

Install the optional example as a reviewed systemd drop-in only after the
private repository and credential are provisioned:

```sh
sudo install -d -o root -g root -m 0755 /etc/systemd/system/riverview-status-dashboard.service.d
sudo install -o root -g root -m 0644 deploy/systemd/riverview-status-dashboard-snapshot-archive.conf.example \\
  /etc/systemd/system/riverview-status-dashboard.service.d/snapshot-archive.conf
sudo systemd-analyze verify /etc/systemd/system/riverview-status-dashboard.service
```

Edit the repository slug in the installed drop-in, run `daemon-reload`, and
restart the dashboard only in a separately approved deployment window. The
credential must exist before enabling the drop-in. Missing or invalid archive
configuration makes only archival unavailable; the dashboard itself continues
to start. No background worker or server-side file staging is used. Successful
Releases are permanent and are not automatically expired.

The browser sends its generated ZIP to the authenticated dashboard backend
over the same origin. The endpoint requires a Steward account cookie and CSRF
token, validates the package bound, ZIP CRC, every manifest SHA-256/size and the
manifest redaction declaration, then calls GitHub. It returns a UTC timestamp
plus random identifier, release URL, asset name, archive size and SHA-256. The
Release body stores these metadata fields for historical lookup. On failure,
the browser reports a safe error and downloads the same ZIP locally. Do not
retry by copying ZIPs into the repository or committing them to Git.

If cleanup of a failed draft is unsuccessful, locate it by the generated
`rvdiag-...` tag and inspect its assets. Delete only that draft and its exact
generated tag after confirming no asset was published. A successfully
published release is the durable archive and must not be removed as part of a
retry.

The bounded interaction history stores at most 120 interactions, 200 API request
summaries, and 50 browser errors in tab session storage. Request summaries contain
method, sanitized endpoint, response status, elapsed time, safe correlation ID,
and interaction ID where available. The exporter never records headers, request
or response bodies, cookies, passwords, form contents, or conversation text.
The archive also includes up to five document-navigation timing summaries with
DNS, connection/TLS, request/response, DOM/load duration and transfer-size values;
raw URLs and document names are excluded.
Page HTML and visuals redact account rows and conversation/request content; form
values and selected values are cleared. Offline HTML is inert: scripts, form
actions, and link destinations are removed, and non-data external media is omitted
and reported. The package is limited to 96 MiB of uncompressed member data. PNG previews and
detail tiles have a 76 MiB cumulative ceiling. At that ceiling, 16 MiB remains
available for structured HTML/JSON/SVG/status/diagnostics and 4 MiB is reserved
for the manifest; unused raster headroom also remains available to required
members. ZIP headers add small overhead to the downloaded file and are outside
the uncompressed member check. The manifest reports uncompressed bytes by
category and lists every omitted raster path and reason. If the raster budget is
reached, the exporter retains diagnostics, sanitized HTML, page/workflow JSON,
workflow status and SVG while omitting only PNG previews or detail tiles.
Affected page/workflow visual status is `incomplete` and the top-level
`capture_complete` flag is false; canonical workflow data remains usable. Full
page captures are bounded to 50,000 CSS pixels; taller content is explicitly
marked incomplete. Pages taller than 1,800 CSS pixels include overlapping
readable PNG detail tiles under `website/pages/<page-id>/details/` while budget
allows. A mandatory non-raster member that alone causes the hard package ceiling
to be exceeded fails with `snapshot_package_bound_exceeded:<member>:<attempted>/<limit>`; inspect the named source/category before retrying.

The registry is a versioned static JSON contract served through the authenticated
capability API; each page and control declares a capability version. The collector
iterates that registry and the authenticated canonical workflow index rather than
maintaining its own page or graph list. An isolated Firefox run used the repository's
actual dashboard HTML, CSS, application scripts, capability registry, and canonical
graph files with synthetic read-only API/session responses. It captured all 10
registered pages, 55 controls with zero uncovered rendered controls, and every
workflow (20 workflows, 494 nodes, 656 edges, 26 cross-workflow references). The 20,067-pixel desktop documentation view
has 12 readable tiles; at 720 pixels, the full 42,192-pixel view has 25 tiles. Both
ZIPs are complete and the workflow JSON/SVG are byte-identical across viewports.
Evidence: [`actual-dashboard browser report`](../../evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-actual-dashboard-final9/browser-acceptance.json)
and [`archive inspection`](../../evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-actual-dashboard-final9/archive-inspection.json).
These fixture-only API and session responses are not evidence of authenticated
production acceptance or a deployed PR #67 release. The Camrui readiness facts are
in `evidence/checkouts/WEBSITE-SNAPSHOT-041/20261016T-snapshot-fullsource-final4/production-readiness.json`.

### RV-WEBSITE-SNAPSHOT-BOUND-20261020 repair evidence

The deployed exporter failed when cumulative uncompressed ZIP members exceeded
96 MiB. The bound was checked in `ZipStore.add` for every member; it was not a
record-count limit. A baseline full-source Firefox fixture on the deployed
source commit captured 10 pages and 22 workflows at 71,115,604 uncompressed
bytes: workflow visuals 50,113,354 bytes, page visuals 18,836,817 bytes, page
records 1,308,874 bytes, workflow records 631,897 bytes, and registry/diagnostic/
manifest material 224,662 bytes. This fixture has empty operational rows and
synthetic browser history; it demonstrates visual dominance but does not measure
the Steward's current production download. Browser-history retention is bounded
to 120 interactions, 200 requests, and 50 errors, and conversation/request
bodies are excluded by the exporter.

When the raster budget is exceeded, the exporter now omits only redundant PNG
previews/detail tiles. Canonical JSON, SVG, sanitized HTML and diagnostics remain
in the archive; the manifest names omitted raster members, reports category
byte totals, and marks the package incomplete. If a mandatory non-raster
member exceeds the hard bound, the displayed error includes the path and byte
threshold.

Run the isolated full-source bound regression without production access:

```sh
python3 scripts/verify_diagnostic_snapshot_browser.py \
  --actual-dashboard-fixture --package-bound-stress-fixture --single-capture \
  --output evidence/checkouts/STEWARD-DASHBOARD/<new-run-directory>
```

Expected: exit 0, valid ZIP CRCs and manifest hashes, package below 96 MiB, one
or more raster omissions listed, every canonical graph JSON/SVG and sanitized
page HTML/JSON present, diagnostics present, and no synthetic cookie, private
conversation text or form value in the package. The harness uses an isolated
synthetic cookie and synthetic APIs; it does not establish deployed acceptance.

If a deployed snapshot manifest reports `Invalid image request` for every PNG,
check the dashboard's `img-src` Content Security Policy before changing the
policy. The collector should rasterize SVG through the already allowed `data:`
image scheme; do not add a broad image source to bypass a renderer mismatch.
Registered pages unavailable to the current session must be reported with their
access status and omission reason, not converted into generic JavaScript capture
failures. PL-NEW-043 tracks this production acceptance correction.

To inspect an export offline, unzip it and open `website/pages/<page-id>.html` in
a browser. These pages contain no live dashboard scripts or API links; workflow
JSON and images are independently readable from the ZIP. A global combined
workflow visualization is a future parking-lot initiative and is deliberately
not included. The separate workflow-viewer fit-to-screen/pan/zoom improvement is
tracked as PL-NEW-042 and does not affect full-graph export.

The workflow viewer toolbar provides **Fit**, **Zoom out**, **Zoom in**,
**Reset**, and **Full screen** controls. Fit is reapplied when the graph or
canvas size changes; pointer drag pans the graph and the mouse wheel zooms.
Reset restores the initial unit-scale view. These controls change only the
browser presentation and do not alter workflow definitions.

This read-only export does not verify a production account-cookie login or
production SSE/reconnect/deferred-response delivery. Those acceptance results
remain unverified until safely tested with an existing authorized session and
conversation; do not create a production conversation or objective to verify the
snapshot.

### PR #71 production release and snapshot acceptance

PR #71 head `fd09129bbadd44738ac38fde837e37164f243964` passed exact-head
controlled CI run `38972694228` (484 tests, 2 skipped; 20 graphs / 494 nodes;
revision audit with zero issues) and merged as
`50e1e44b498927e5df67e5c08aec3cda8267dd72`. The immutable release is installed at
`/opt/riverview-status-dashboard/releases/50e1e44b498927e5df67e5c08aec3cda8267dd72`
with deployment ID `website-pr71-50e1e44b498927e5df67e5c08aec3cda8267dd72`.
Package SHA-256 is `c60f7fca6325ed2a746c8a611cb0b9b5fc4afb64508401166c2770ab4f106a53`.
The previous f957 release remains the rollback target at
`/opt/riverview-status-dashboard/releases/f957bddb5eda39d4fbd5860ee29f7c32831553b7`;
root-only prestate, package and rollback evidence is under
`/var/backups/riverview-status-dashboard/website-pr71-20261016T220335Z/`.

A real Firefox session at `https://192.168.1.155/` used the protected dashboard
recovery token. Its temporary profile trusted only the verified Riverview LAN
root CA and kept `acceptInsecureCerts=false`. The browser downloaded a
57,940,967-byte ZIP (SHA-256
`5e908c300943ad4daeff5021633531ece87b6435991852c6e377abd6f4d90c12`); CRC and
manifest file hashes passed. Every workflow JSON/SVG/PNG matched canonical source
IDs: 20 workflows, 494 nodes, 656 edges, 26 cross-workflow links, no unresolved
references. All 28 page PNGs were valid. The manifest correctly reports 8/10
pages and `capture_complete=false`: Account and Resident Permissions are hidden
to this recovery-token session. No access was bypassed; the archive contained no
token and the browser made only GET requests. Evidence:
[`PR #71 production acceptance`](../../evidence/checkouts/WEBSITE-PR71-PRODUCTION/20261016T220708Z-50e1e44/production-browser-acceptance.json),
[`release manifest`](../../evidence/checkouts/WEBSITE-PR71-PRODUCTION/20261016T220708Z-50e1e44/release-manifest.json).

Two initial unauthenticated 401 probes preceded login; the account-cookie-only
resident conversations GET returned 403. There were no JavaScript errors. No
session-creation POST, SSE test, objective, conversation, proposal, or other
production mutation was made. Account-cookie login and production SSE/reconnect
remain unverified. The dashboard unit is active with zero restarts; PostgreSQL,
Grace execution owner, CME, assignment intake, event processor, M33 worker and
verifier, and Grace inference units remained active. Grace/CME projections were
healthy; the worker projection was `stale` both before and after release. Read-only
counts remained one objective, ten assignments and zero proposals. All 21
migration ledger rows matched source checksums, including already-applied 0010;
this website release applied no DDL. No rollback was needed.

### Windows HTTPS trust

Camrui presents a leaf certificate for `CN=riverview.ionoge.com`, issued by
`Riverview Camrui LAN Root CA`. Its SAN includes both `DNS:riverview.ionoge.com`
and `IP:192.168.1.155`, and strict TLS validation succeeds on Camrui when the
local root is trusted. The observed evidence does not indicate a server-chain
or IP-name mismatch. Windows was not inspected directly; the reported PowerShell
inner exception is consistent with the Windows client not trusting this private
LAN root. The expected root is
`/usr/local/share/ca-certificates/riverview-camrui-lan.crt`, SHA-256
`D7823E13473A2F1F86A50781071CA7D6E08CA0B8D960C327739C85BA14DDC32D`.

Transfer the CA certificate through an already authenticated channel (for
example, strict-host-key SSH/SCP after verifying Camrui's SSH host key from a
trusted source). Do not bootstrap trust by downloading it over the failing
HTTPS connection. Once Camrui's SSH host key is already verified in the Windows
user's `known_hosts`, PowerShell 7 can copy the public CA certificate with:

```powershell
$certPath = Join-Path $env:TEMP 'riverview-camrui-lan.crt'
scp -o StrictHostKeyChecking=yes admin1@192.168.1.155:/usr/local/share/ca-certificates/riverview-camrui-lan.crt $certPath
```

Inspect the local file before importing:

```powershell
$certPath = Join-Path $env:TEMP 'riverview-camrui-lan.crt'
$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($certPath)
$sha256 = [Convert]::ToHexString($cert.GetCertHash([System.Security.Cryptography.HashAlgorithmName]::SHA256))
$basicConstraints = $cert.Extensions | Where-Object {
    $_ -is [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]
} | Select-Object -First 1
if ($cert.Subject -ne $cert.Issuer -or
    $null -eq $basicConstraints -or -not $basicConstraints.CertificateAuthority -or
    $sha256 -ne 'D7823E13473A2F1F86A50781071CA7D6E08CA0B8D960C327739C85BA14DDC32D' -or
    $cert.NotBefore -gt [DateTime]::UtcNow -or $cert.NotAfter -le [DateTime]::UtcNow) {
    throw 'The Riverview CA certificate identity, constraints, fingerprint, or validity did not match.'
}
$store = [System.Security.Cryptography.X509Certificates.X509Store]::new(
    [System.Security.Cryptography.X509Certificates.StoreName]::Root,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser)
$store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
$store.Add($cert)
$store.Close()
Invoke-WebRequest -Uri 'https://192.168.1.155/'
```

This imports only the verified local root into the current user's Trusted Root
store; it does not disable validation or install the server leaf certificate.
The browser/PowerShell request must still use `https://192.168.1.155/` (or the
SAN-covered hostname resolving to Camrui). A Windows-side exception remains
unconfirmed until the Steward runs the strict request there.

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
curl --fail --silent --show-error http://127.0.0.1:8767/
ss -ltn '( sport = :8767 )'
```

On current Camrui, the systemd dashboard backend binds `127.0.0.1:8767` because
the preserved `60-lan-proxy.conf` drop-in selects that port. The LAN TLS proxy
serves the browser at `https://192.168.1.155/` on port 443 and redirects HTTP
port 8766 to TLS. The certificate subject alternative names include the Camrui
LAN IP. Public DNS for `riverview.ionoge.com` resolves to a separate public
IONOGE site; do not use that DNS name for the Camrui dashboard. Preserve the
existing proxy and dashboard drop-ins when installing a website release.

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
| Download Snapshot | one bounded ZIP with page inventories/visuals, workflow JSON/SVG/PNG/status, and safe browser diagnostics | unavailable page/graph, incomplete visual, package bound, or download failure | ZIP manifest omissions, per-page/per-workflow outcomes, and browser-local safe error class | verify the current account can access the page; retry after the projection/API issue is understood. Do not treat missing output as a complete capture; no cookies, credentials, form values, or conversation bodies are exported. |
| Restart/reconnect | same release/port; current state re-read from PostgreSQL | systemd failed/inactive or authentication lost | `systemctl status` and `journalctl -u ... -n 50 --no-pager` | restart only the dashboard unit; reauthenticate; CME and assignments continue independently. |

## Deployment and rollback

1. Record current dashboard symlink and unit checksum before first install/change.
2. Verify package manifest against committed source and install only to a new
   versioned release directory owned by root and not writable by `riverview`.
3. Provision the bearer token through an owner-only file and systemd credential;
   preserve existing DB credentials and deliver them through the existing
   `LoadCredential=pgpass:/etc/riverview/pgpass` contract.
4. Preserve the effective dashboard bind and existing LAN TLS proxy. On current
   Camrui the dashboard backend is `127.0.0.1:8767`, while Nginx provides the
   LAN-only TLS URL; do not replace the systemd drop-ins with the unit example's
   default port.
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

### PR #42 website release — 2026-10-16

PR #42 was integrated by merge commit
`50ed988f84398bde7aa9df5bb3f163d753748fed`; the verified website source
`928649bd1ff695fe9a95915647a49943ffe921fe` is installed at
`/opt/riverview-status-dashboard/releases/928649bd1ff695fe9a95915647a49943ffe921fe`
with deployment ID `website-pr42-928649bd1ff695fe9a95915647a49943ffe921fe`.
The source package SHA-256 is
`19890d22e18caa4896a6e944cf021397d11d95a54ba96a4928e86e2529b46c6b`; its
manifest and shell compatibility checks passed. The predecessor
`af87c1a1b8ef4deeb8770c64da8bb4556bc85866` remains installed. Only the dashboard
release pointer, a new release-identity drop-in, and the dashboard service were
changed for activation; existing Codex 1 drop-ins and dependent services were
preserved. No database migration, grant, objective, CME, model, or worker change
was made. The existing resident-execution migrations 0001–0009 and checksums
matched, including stream-delivery migration 0008 and its exact runtime table
privileges.

Production checks on the installed release returned HTTP 200 at the backend and
the LAN TLS URL, with strict curl TLS verification successful. Authenticated
status was healthy/current and CME was healthy. Live Firefox verified assignment
detail, graph navigation/rendering, documentation links, and no console errors;
the searchable catalog returned 19 workflows and narrowed to 5 for `grace`.
One existing objective remained visible as COMPLETED, and the existing assignment
projection showed 10 rows; no objective was created, retried, or changed. A
temporary headless Firefox profile needed its test-only `acceptInsecureCerts`
capability because it did not trust the local Riverview root CA; the OS trust
store independently validated the production certificate. Positive account
login, authenticated account-cookie graph access, and live SSE/reconnect/deferred
recovery remain unverified because they require a Steward session or a
conversation mutation. Evidence and the dashboard-only rollback plan are under
`evidence/checkouts/WEBSITE-PR42-PRODUCTION/20261016T172206Z-928649b/`.


### Integrated PR #67 website release — 2026-10-16

The Steward-authorized release installed integration commit
`f957bddb5eda39d4fbd5860ee29f7c32831553b7` at
`/opt/riverview-status-dashboard/releases/f957bddb5eda39d4fbd5860ee29f7c32831553b7`.
The active deployment ID is
`website-integrated-f957bddb5eda39d4fbd5860ee29f7c32831553b7`; the immutable
package SHA-256 is
`626e0c7e60a28461534d38d1061d488a9e26cebc764872164cdfb4b1cc9243cd`.
The previous PR #42 release remains at
`/opt/riverview-status-dashboard/releases/928649bd1ff695fe9a95915647a49943ffe921fe`
and the `current` link and dashboard identity drop-in are recorded in the
root-only rollback evidence at
`/var/backups/riverview-status-dashboard/website-pr67-f957bdd/`.

Before migration, the protected custom database dump
`/var/lib/postgresql/backups/riverview/website-pr67-20261016T205244Z/riverview.dump`
was checksummed and listed successfully. It restored into a disposable database;
the source and restored assignment, event, objective, and conversation-event
counts matched. Migration `0010_institutional_proposal_registry.sql` matched
SHA-256
`3909705a38ec19f31be99088fa7fbfc8dfe9e9c6d28a55095f978d4bf10d4e18` and was
applied through the committed runner. The production ledger now records that
checksum; all five registry tables and their scoped grants were verified. The
proposal table currently has zero records; pre-existing objectives and execution
records were unchanged. Migration rollback means keeping the additive tables and
disabling the owning API, not dropping them.

The exact integration source passed controlled CI run `38961577839`, 66 focused
dashboard/runtime tests (8 PostgreSQL-dependent skips), process graph validation
(20 graphs / 494 nodes / 656 edges), and the controlled revision audit. The
dashboard service is active on the immutable release; PostgreSQL, Grace execution
owner, CME monitor, event processor, assignment intake, M33 worker and verifier
were active after activation. Strict HTTPS returned HTTP 200 with the host OS
trusting the installed Riverview certificate. Firefox on the host could not
validate the LAN CA in its isolated Snap profile, so the browser regression used
the same live service over loopback HTTP without a TLS bypass.

Live Firefox verified the authenticated read-only dashboard projection, the
existing completed assignment and its recorded attempt/verifications, the
existing completed objective, ten attention rows, CME status, workflow graph
rendering/navigation, and 19 documentation links, with zero browser errors.
The one live diagnostic ZIP downloaded successfully and passed CRC inspection.
Its workflow index contains 20 entries with all 494 node and 656 edge records,
20 JSON definitions, 20 SVGs, 26 resolved cross-workflow references, and zero
unresolved references. However, its manifest correctly says
`capture_complete: false`: the browser session could access only 8 of 10 pages,
and no page or workflow PNGs were produced. The original page outcomes exposed a
collector error when a restricted navigation returned without an `omissions`
array; the SVG-to-PNG renderer attempted a Blob URL that the strict dashboard
CSP blocks. PL-NEW-043 tracks the correction. A focused synthetic-API browser
regression now runs the actual dashboard assets under the production CSP and
passes all 10 page PNGs, all workflow PNGs, workflow/node/edge identity, and
cross-viewport checks; this is not yet production acceptance of that correction.
Evidence: [`sanitized production acceptance`](../../evidence/checkouts/WEBSITE-PR67-SNAPSHOT-CSP/20261016T211638Z/production-acceptance-summary.json)
and [`isolated CSP browser report`](../../evidence/checkouts/WEBSITE-PR67-SNAPSHOT-CSP/20261016T211638Z/isolated-browser-acceptance.json).

The proposal registry migration is present, but positive proposal API access is
not verified: the available dashboard bearer token correctly received 403 on
the authenticated proposal search route. No proposal, objective or conversation
was created or changed. Steward account-cookie authentication, proposal reads,
Grace conversation cookie/session handling, SSE/reconnect/deferred recovery and
mutating objective intake remain unverified. The current healthy f957 release
has not been rolled back. The source correction must pass controlled review and
release checks before the diagnostic snapshot is called complete in production.


### Integrated PR #67 website release — 2026-10-16

The Steward-authorized release installed integration commit
`f957bddb5eda39d4fbd5860ee29f7c32831553b7` at
`/opt/riverview-status-dashboard/releases/f957bddb5eda39d4fbd5860ee29f7c32831553b7`.
The active deployment ID is
`website-integrated-f957bddb5eda39d4fbd5860ee29f7c32831553b7`; the immutable
package SHA-256 is
`626e0c7e60a28461534d38d1061d488a9e26cebc764872164cdfb4b1cc9243cd`.
The previous PR #42 release remains at
`/opt/riverview-status-dashboard/releases/928649bd1ff695fe9a95915647a49943ffe921fe`
and the `current` link and dashboard identity drop-in are recorded in the
root-only rollback evidence at
`/var/backups/riverview-status-dashboard/website-pr67-f957bdd/`.

Before migration, the protected custom database dump
`/var/lib/postgresql/backups/riverview/website-pr67-20261016T205244Z/riverview.dump`
was checksummed and listed successfully. It restored into a disposable database;
the source and restored assignment, event, objective, and conversation-event
counts matched. Migration `0010_institutional_proposal_registry.sql` matched
SHA-256
`3909705a38ec19f31be99088fa7fbfc8dfe9e9c6d28a55095f978d4bf10d4e18` and was
applied through the committed runner. The production ledger now records that
checksum; all five registry tables and their scoped grants were verified. The
proposal table currently has zero records; pre-existing objectives and execution
records were unchanged. Migration rollback means keeping the additive tables and
disabling the owning API, not dropping them.

The exact integration source passed controlled CI run `38961577839`, 66 focused
dashboard/runtime tests (8 PostgreSQL-dependent skips), process graph validation
(20 graphs / 494 nodes / 656 edges), and the controlled revision audit. The
dashboard service is active on the immutable release; PostgreSQL, Grace execution
owner, CME monitor, event processor, assignment intake, M33 worker and verifier
were active after activation. Strict HTTPS returned HTTP 200 with the host OS
trusting the installed Riverview certificate. Firefox on the host could not
validate the LAN CA in its isolated Snap profile, so the browser regression used
the same live service over loopback HTTP without a TLS bypass.

Live Firefox verified the authenticated read-only dashboard projection, the
existing completed assignment and its recorded attempt/verifications, the
existing completed objective, ten attention rows, CME status, workflow graph
rendering/navigation, and 19 documentation links, with zero browser errors.
The one live diagnostic ZIP downloaded successfully and passed CRC inspection.
Its workflow index contains 20 entries with all 494 node and 656 edge records,
20 JSON definitions, 20 SVGs, 26 resolved cross-workflow references, and zero
unresolved references. However, its manifest correctly says
`capture_complete: false`: the browser session could access only 8 of 10 pages,
and no page or workflow PNGs were produced. The original page outcomes exposed a
collector error when a restricted navigation returned without an `omissions`
array; the SVG-to-PNG renderer attempted a Blob URL that the strict dashboard
CSP blocks. PL-NEW-043 tracks the correction. A focused synthetic-API browser
regression now runs the actual dashboard assets under the production CSP and
passes all 10 page PNGs, all workflow PNGs, workflow/node/edge identity, and
cross-viewport checks; this is not yet production acceptance of that correction.

The proposal registry migration is present, but positive proposal API access is
not verified: the available dashboard bearer token correctly received 403 on
the authenticated proposal search route. No proposal, objective or conversation
was created or changed. Steward account-cookie authentication, proposal reads,
Grace conversation cookie/session handling, SSE/reconnect/deferred recovery and
mutating objective intake remain unverified. The current healthy f957 release
has not been rolled back. The source correction must pass controlled review and
release checks before the diagnostic snapshot is called complete in production.


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
