<!--
Riverview Controlled Document
File: docs/components/COMMS5_CAMRUI_MIGRATION.md
Component: COMMS5-CAMRUI-ADAPTER
File Revision: 1.0.8
Status: Source implementation and live deployment tracker
Date: 2026-10-17
History: New file; no predecessor existed.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Record authenticated OAuth/MCP acceptance and identify the unchanged Comms4 upstream outage.
Changed: 2026-10-17 UTC | RV-COMMS5-DASHBOARD-READ-DEPLOY-001 | Record PR #89 deployment and measured production operation coverage.
Changed: 2026-10-17 UTC | RV-COMMS5-FUNCTIONAL-20261017 | Map proposal, objective-status and recent-submission operations to the current durable proposal/objective services; distinguish source from deployed coverage.
Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Complete the authenticated transport probe and report actual worker inventory without fabricating an unset resource policy.
Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Add idempotent, exact-grant-checked dispatch request intake while leaving actual assignment creation to the existing CME execution service.
Changed: 2026-10-17 UTC | RV-COMMS5-REMAINING-OPS-20261017 | Record PR #100 queue-intake behavior, verified source coverage, and current deployment boundary.
Previous: 2026-10-17 UTC | RV-COMMS5-TOOL-CATALOG-AUDIT-001 | Link exact preserved input schemas and record current loopback deployment state.
Previous: 2026-10-17 UTC | RV-COMMS5-DASHBOARD-READ-001 | Record read-only dashboard projection implementation before production deployment.
-->

# Comms5 Camrui migration matrix

Historical contract source: `ppow1/Riverview` PR #15 head `048787f574d42ff073a9f94f571dc79943d60fa4`, `src/riverview/mcp/comms5_server.py`, with operation metadata from `src/riverview/mcp/comms5.py`. The checked-in catalog has 21 original tool names, exact descriptions, FastMCP-generated input schemas, original annotations, and the historical OAuth scope metadata. Camrui does not install or recreate the historical Windows-only tables.

Exact historical input schemas, annotations, authentication metadata, and captured response-description limits are recorded per tool in [`COMMS5_TOOL_CATALOG_AUDIT.md`](COMMS5_TOOL_CATALOG_AUDIT.md). All tools remain discoverable. The current source maps objective status to the durable objective, step, assignment, verifier, execution-intent and current exact-grant projections; recent Steward submissions combine metadata from the objective and proposal registries. Both omit private request/proposal bodies. Seed/specification lifecycle operations use the current revisioned proposal registry and authorized promotion path. CME status remains a dashboard projection. The transport probe measures the Comms5-to-dashboard request correlation. `comms5_form_and_queue_work` records a durable, idempotent Steward request against an already grounded, dependency-ready step; actual assignment creation remains the persistent Grace execution service's responsibility and rechecks its separate `assignment.create` grant. Three operations remain stubs because no equivalent current durable contract exists: stale-base revalidation, resource-policy mutation, and policy lock.

| Tool | Original purpose | Original authorization | Current implementation | Dependencies / remaining work |
|---|---|---|---|
| `comms5_contract_info` | Version and compatibility identity | READ_ONLY | Static versioned contract payload | No database dependency; Implemented; pure read-only |
| `comms5_help` | Discovery, limits, safety guidance, and examples | READ_ONLY | Historical bounded Comms5 help payload preserved from source | No database dependency; Implemented; pure read-only |
| `comms5_capabilities` | Operation list, authorization classes, limits | READ_ONLY | Historical operation registry, including all 21 tool functions | No database dependency; Implemented; pure read-only |
| `comms5_describe_operation` | Describe one named operation | READ_ONLY | Historical operation registry lookup | No database dependency; Implemented; unknown names return historical bounded error object |
| `comms5_examples` | Bounded operation examples | READ_ONLY | Historical static examples payload | No database dependency; Implemented; pure read-only |
| `comms5_submit_steward_seed` | Submit a bounded draft; this never promotes or creates work. | DRAFT_WRITE | IMPLEMENTED; idempotent DRAFT in `ProposalRegistry` | Authenticated Steward ingress; no execution authority is created |
| `comms5_store_specification` | Store a bounded specification and optional typed non-shell formation contract. | DRAFT_WRITE | IMPLEMENTED; current proposal revision and provenance; formation fields remain advisory | Exact current proposal schema; no work order is created |
| `comms5_seed_status` | Return bounded seed, specification, objective linkage, and promotion status metadata. | READ_ONLY | IMPLEMENTED over current proposal record and links | Legacy seed IDs map to stable current proposal IDs; output is bounded |
| `comms5_seed_lineage` | Return authoritative bounded seed lineage. | READ_ONLY | IMPLEMENTED over proposal events, reviews, and work-order links | No legacy seed/result tables are installed |
| `comms5_objective_status` | Return bounded objective, stages, authority, intent, and work metadata. | READ_ONLY | IMPLEMENTED through authenticated internal current-runtime operation | Includes durable steps/events, latest verification, execution intent and current exact submission-grant state; excludes request and acceptance text |
| `comms5_cme_status` | Return the authoritative CME runtime projection. | READ_ONLY | IMPLEMENTED through authenticated dashboard status projection | Returns live CME health/status fields from the existing dashboard projection; no scheduler or executor action is invoked. |
| `comms5_recent_steward_submissions` | Return bounded recent submission metadata. | READ_ONLY | IMPLEMENTED across objective and proposal registries | Returns metadata only; combines current Steward-submitted objectives and proposal records, with bounded pagination/truncation status |
| `comms5_transport_probe` | Run one read-only end-to-end transport correlation probe. | READ_ONLY | PR #100 source: IMPLEMENTED; requires authenticated MCP principal, probes the live dashboard status API, and returns both caller probe ID and dashboard request ID | A successful call proves this request reached Camrui through its authenticated Comms5 ingress and loopback dashboard hop; it does not claim general network availability outside that request |
| `comms5_resource_policy_status` | Return the durable Codex resource policy and its audit projection. | READ_ONLY | PR #100 source: IMPLEMENTED status query; reports `policy_state=not_configured` and actual registered worker capability/scope metadata | No preference/lock is fabricated; policy mutation and selection enforcement remain unavailable |
| `comms5_set_resource_policy` | Set policy only from authenticated Steward transport attestation. | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Legacy resource-policy persistence absent; current policy mutation contract not equivalent; Use current audited authority API only after an exact scoped operation exists |
| `comms5_set_resource_policy_lock` | Lock or unlock policy only from authenticated Steward transport attestation. | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Legacy policy-lock persistence absent; Implement via current audited policy mechanism if one is commissioned |
| `comms5_confirm_and_promote_seed` | Approve the exact eligible proposal revision and promote it into the existing objective pipeline. | STEWARD-GATED_WRITE | IMPLEMENTED through `ProposalLifecycle.decide` + `promote` | Requires explicit confirmation, ready revision, resolved reviews, exact content digest and existing `objective.submit`; intake failure preserves approved proposal and reports prerequisite |
| `comms5_form_and_queue_work` | Form the approved typed intent and enqueue exactly one work order. | STEWARD-GATED_WRITE | PR #100 source: IMPLEMENTED as an append-only `work_order.dispatch_requested` event after explicit confirmation, current `objective.submit` grant revalidation, exact grant-ID match, and dependency readiness. Idempotent retries reuse the same event; target/payload conflicts fail closed. | It records queue intent only; the existing Grace Execution Service remains the sole dispatcher and separately rechecks `assignment.create`. It does not claim an assignment exists until CME creates one. |
| `comms5_revalidate_and_queue_work` | Revalidate one stale approved base and queue one bounded successor.

    This preserves the original failed attempt and exact authority scope. It
    never widens paths, changes the capability, or executes Codex; material
    repository drift fails closed for renewed specification approval.
    | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Current recovery contracts require the Grace dispatch service identity and durable stale-base evidence; Comms5 has no delegated recovery endpoint |
| `comms5_cancel_draft` | Append-only cancel of a draft; never cancels an objective or work order. | STEWARD-GATED_WRITE | IMPLEMENTED as an explicit-confirmation transition of the current proposal to ARCHIVED | Current proposal event is append-only and transition is idempotent; rejects stale/ineligible states |
| `comms5_supersede_seed` | Append an old-draft-to-new-draft replacement relation. | STEWARD-GATED_WRITE | IMPLEMENTED as an explicit-confirmation SUPERSEDED transition linked to a current DRAFT replacement | Relationship is recorded in proposal lifecycle event; replacement must remain unreviewed DRAFT |

## Runtime boundary

Camrui adapter binds to `127.0.0.1:11826` only. It requires both Caddy-injected `X-Riverview-Comms5: 1` / `X-Riverview-Comms5-Principal: steward` and a distinct backend-hop bearer credential delivered by systemd credentials. OAuth validation is performed by the Ionoge Comms5 OAuth service through Caddy `forward_auth`; that authenticated response supplies the `steward` principal, and Caddy sets the trusted hop marker on the backend request. The old connector bearer route remains a separate compatibility path. The MCP process logs no request line, body, arguments, or bearer values.

Comms5 uses a fixed loopback-only dashboard client with the existing protected dashboard bearer. Read projections use fixed allowlisted paths. The proposal/objective operations use one fixed POST endpoint, `/api/v1/internal/comms5/operation`, and a closed tool allowlist; redirects, caller URLs, caller headers, and caller credentials are rejected. The dashboard independently verifies the bearer, Caddy-attested Steward marker, fixed principal mapping, bounded payload, and each existing proposal/objective lifecycle rule. The dashboard owns PostgreSQL operations; Comms5 receives no database credential. No migration is required for the current proposal/objective mappings. Work-order dispatch remains separate and is not performed by approval/promotion.

## Validation status — 2026-10-17 UTC

- Source catalog: 21 tools compared against historical FastMCP discovery; all 21 were returned through the authenticated production public route. PR #89 deployed six fully implemented, three partial, and twelve stubbed tools. PR #94 deployed 15 implemented, one partial, and five stubs. PR #100 source implements 18, with no partials and three truthful stubs. PR #100 has not been deployed; production remains on PR #94 until a controlled deployment is recorded.
- In the Camrui development shell, the new source's authenticated dashboard client returned the live CME projection as healthy with 7 workers registered. An isolated local MCP HTTP listener using that client returned HTTP 200 for `comms5_cme_status`; no objective content was queried, no production Comms5 release was switched, and this does not establish a public-route deployment test. The partial transport probe measured only the Comms5-to-dashboard loopback hop.
- Camrui adapter release `588aee804fc6ada3cdf78f4bfded2f8306c783ea` active at loopback `127.0.0.1:11826`; `/healthz` returned 200 before and after a controlled reverse-tunnel disconnect/reconnect. Reconnect elapsed 6 seconds.
- Ionoge OAuth source `048787f574d42ff073a9f94f571dc79943d60fa4` active at loopback `127.0.0.1:11827`. A pre-restart dynamic client remained registered across an OAuth unit restart; after the loopback health endpoint returned 200, authorization and MCP exchange succeeded.
- Public OAuth DCR, discovery, authorization-code + PKCE S256, callback state, resource-bound token exchange, MCP initialize, initialized notification, 21-tool discovery, `comms5_contract_info`, token-family revoke, and rejection of unauthenticated/revoked requests passed. Exact UTC-stage results and sanitized details are in the dated runbook/troubleshooting record.
- The live Caddy Comms5 OAuth route now copies only the OAuth-validated `steward` principal, overwrites the backend marker, and no longer deletes that marker. Public OAuth discovery returns 200; unauthenticated Comms5 returns 401.
- Comms4 route/config was not changed. Its unauthenticated endpoint returns 401, but authorized `ping` currently returns 502 because Ionoge has no listener on upstream `127.0.0.1:11825`; that upstream recovery is an unresolved separate issue.
- No legacy Comms5 database tables were installed or needed. The ChatGPT Plus account UI itself has not yet been used; production protocol acceptance is not equivalent to ChatGPT application acceptance.

## Production deployment record — 2026-10-17 22:16 UTC

- PR #89 merged at `c18b283ae7263b6fa708b80dbf179b8199ec4b64`. The immutable package is `/tmp/riverview-comms5-c18b283.tar.gz`, SHA-256 `c2a7c5681d0f94097bed27f124a3666e6f5cc0d3959ebf4573535573fcd65371`, containing nine source/config/document files plus its manifest and checksum list. Every embedded checksum passed on Camrui.
- Camrui `current` points to `/opt/riverview-comms5-camrui/releases/c18b283ae7263b6fa708b80dbf179b8199ec4b64`; systemd is active and the sole listener is `127.0.0.1:11826`. `/healthz` returned 200. An unauthenticated MCP POST returned 401.
- A one-shot transient systemd invocation loaded the existing protected backend-hop credential without displaying it, then called the running production adapter. `tools/list` returned all 21 historical contracts. `comms5_cme_status` returned `IMPLEMENTED`, healthy CME state, and 7 registered workers. The dashboard-backed source was exercised against the real dashboard endpoint and protected credential; no objective or conversation body was queried.
- Public OAuth discovery returned 200; anonymous public Comms5 MCP returned 401. Anonymous Comms4 MCP also returned 401. Caddy, OAuth, and tunnel configurations were not changed. This is not ChatGPT UI acceptance. Comms4's protected upstream remains separately unverified as recorded above.
- Root-only rollback evidence is at `/var/backups/riverview/comms5-deploy-20261017T221707Z` (directory mode 0700): predecessor unit SHA-256 `6ece4c2f765b57d7aa6bdecca0ca137f491ef14c0497fc540e98b12475e1fdd4`, predecessor release pointer `588aee804fc6ada3cdf78f4bfded2f8306c783ea`, and new package checksum. The predecessor release remains present. Rollback restores that unit and pointer, runs `systemctl daemon-reload`, restarts only `riverview-comms5-camrui.service`, and checks `/healthz`.
- Production capability coverage is 6 fully implemented operations (5 static discovery/contract tools plus CME status), 3 partial operations (objective status, recent Steward submissions, and bounded local transport probe), and 12 explicit non-executing stubs. Assignment intake and CME monitor remain active; `riverview-grace-execution.service` is inactive, so this release did not demonstrate Comms5-to-Codex execution.

## Source implementation increment — PR #94 (2026-10-17)

The PR #94 source increment adds current proposal-registry operations and bounded objective/recent-submission projections, backed by `Comms5Operations` and the authenticated dashboard internal endpoint. It was merged and deployed as commit `2c7adc678de409a50fa6817b3d98492ebb66b451`; production discovery reports 15 implemented, one partial, and five explicit stubs.

## Source implementation increment — PR #95 (2026-10-17; superseded by PR #100)

PR #95 completed the request-scoped transport probe using its supplied probe ID plus the live dashboard `X-Request-ID`, and made resource-policy status a projection of the registered worker/capability inventory while returning `policy_state=not_configured`. PR #100 adds the durable, idempotent, exact-grant-checked queue-request operation through the existing dashboard-owned event ledger. Source coverage is now 18 implemented and three explicit stubs. The remaining stubs are stale-base revalidation and resource-policy set/lock; no equivalent current contracts exist for these operations. PR #100 remains source-only until review, merge, package build, and controlled deployment.

## Source implementation increment — PR #100 (2026-10-17)

PR #100 implements the authenticated `comms5_form_and_queue_work` queue-intake contract through the current objective event ledger. Queue requests are durable and idempotent, require explicit Steward confirmation, recheck the exact current `objective.submit` grant in the transaction, and require a dependency-ready proposal step. Queue intent does not create an assignment or claim dispatch; the Grace execution service remains responsible for later assignment creation under `assignment.create`. Unit, focused routing, isolated PostgreSQL, process-graph, and revision checks passed. Production remains on PR #94 pending integration, immutable release creation, and controlled deployment.
