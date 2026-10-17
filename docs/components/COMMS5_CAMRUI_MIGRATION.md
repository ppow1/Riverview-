<!--
Riverview Controlled Document
File: docs/components/COMMS5_CAMRUI_MIGRATION.md
Component: COMMS5-CAMRUI-ADAPTER
File Revision: 1.0.1
Status: Source implementation and live deployment tracker
Date: 2026-10-16
History: New file; no predecessor existed.
Changed: 2026-10-17 UTC | RV-COMMS5-TOOL-CATALOG-AUDIT-001 | Link exact preserved input schemas and record current loopback deployment state.
-->

# Comms5 Camrui migration matrix

Historical contract source: `ppow1/Riverview` PR #15 head `048787f574d42ff073a9f94f571dc79943d60fa4`, `src/riverview/mcp/comms5_server.py`, with operation metadata from `src/riverview/mcp/comms5.py`. The checked-in catalog has 21 original tool names, exact descriptions, FastMCP-generated input schemas, original annotations, and the historical OAuth scope metadata. Camrui does not install or recreate the historical Windows-only tables.

Exact historical input schemas, annotations, authentication metadata, and captured response-description limits are recorded per tool in [`COMMS5_TOOL_CATALOG_AUDIT.md`](COMMS5_TOOL_CATALOG_AUDIT.md). All tools remain discoverable. The five static contract/discovery operations are implemented without database access. Every other operation returns an MCP tool result with `isError=true`, `status=NOT_IMPLEMENTED`, and `executed=false`; these stubs do not write or claim success.

| Tool | Original purpose | Original authorization | Current implementation | Dependencies / remaining work |
|---|---|---|---|
| `comms5_contract_info` | Version and compatibility identity | READ_ONLY | Static versioned contract payload | No database dependency; Implemented; pure read-only |
| `comms5_help` | Discovery, limits, safety guidance, and examples | READ_ONLY | Historical bounded Comms5 help payload preserved from source | No database dependency; Implemented; pure read-only |
| `comms5_capabilities` | Operation list, authorization classes, limits | READ_ONLY | Historical operation registry, including all 21 tool functions | No database dependency; Implemented; pure read-only |
| `comms5_describe_operation` | Describe one named operation | READ_ONLY | Historical operation registry lookup | No database dependency; Implemented; unknown names return historical bounded error object |
| `comms5_examples` | Bounded operation examples | READ_ONLY | Historical static examples payload | No database dependency; Implemented; pure read-only |
| `comms5_submit_steward_seed` | Submit a bounded draft; this never promotes or creates work. | DRAFT_WRITE | NOT_IMPLEMENTED MCP tool error | Historical seed/specification tables absent on Camrui; no verified equivalent intake contract; Map to current proposal draft lifecycle and exact authorized ingress; preserve idempotency |
| `comms5_store_specification` | Store a bounded specification and optional typed non-shell formation contract. | DRAFT_WRITE | NOT_IMPLEMENTED MCP tool error | Historical specification schema absent; current proposal registry exists but contract differs; Map to proposal registry with revision/provenance/privacy scope |
| `comms5_seed_status` | Return bounded seed, specification, objective linkage, and promotion status metadata. | READ_ONLY | NOT_IMPLEMENTED MCP tool error | Legacy seed store/schema absent; Define projection over proposal lifecycle only if IDs and privacy semantics match |
| `comms5_seed_lineage` | Return authoritative bounded seed lineage. | READ_ONLY | NOT_IMPLEMENTED MCP tool error | Legacy seed/result stores absent; Join current proposal, objective, assignment, artifact, and verification records |
| `comms5_objective_status` | Return bounded objective, stages, authority, intent, and work metadata. | READ_ONLY | NOT_IMPLEMENTED MCP tool error | Current objective ledger exists; no validated Comms5 projection or operation grant wired; Map through read-only ledger/projection APIs and exact grants |
| `comms5_cme_status` | Return the authoritative CME runtime projection. | READ_ONLY | NOT_IMPLEMENTED MCP tool error | CME monitor exists; no verified matching Comms5 principal grant; Use CMEPostgresMonitor status through scoped read API and exact grant |
| `comms5_recent_steward_submissions` | Return bounded recent submission metadata. | READ_ONLY | NOT_IMPLEMENTED MCP tool error | Current proposal registry exists; historical submission projection is absent; Implement a paginated privacy-safe projection through current registry |
| `comms5_transport_probe` | Run one read-only end-to-end transport correlation probe. | READ_ONLY | NOT_IMPLEMENTED MCP tool error | No current Comms5 transport diagnostics mapping is approved; Add bounded correlation-only diagnostic; no protected payload return |
| `comms5_resource_policy_status` | Return the durable Codex resource policy and its audit projection. | READ_ONLY | NOT_IMPLEMENTED MCP tool error | Current resource registry exists; legacy policy/claim schema absent; Map to current resource registry/assignment state and exact access grant |
| `comms5_set_resource_policy` | Set policy only from authenticated Steward transport attestation. | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Legacy resource-policy persistence absent; current policy mutation contract not equivalent; Use current audited authority API only after an exact scoped operation exists |
| `comms5_set_resource_policy_lock` | Lock or unlock policy only from authenticated Steward transport attestation. | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Legacy policy-lock persistence absent; Implement via current audited policy mechanism if one is commissioned |
| `comms5_confirm_and_promote_seed` | Record Pat's approval and atomically materialize one exact draft objective.

    This governed write verifies transport-attested Steward authority, explicit
    confirmation, the eligible specification ID/version/hash, and idempotency,
    then records bounded authority and creates the canonical objective record.
    It does not execute Codex or other work, run shell commands, cancel or
    supersede work, grant arbitrary authority, or bypass Grace, Relay,
    capability, or reconciliation gates. Client identity is provenance only.
     | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Current proposal lifecycle exists but seed IDs and legacy authority materialization differ; Bind to exact proposal revision + current approval/promote contract; never trust body principal |
| `comms5_form_and_queue_work` | Form the approved typed intent and enqueue exactly one work order. | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Current assignment intake exists; legacy stage/authority lineage is not equivalent; Use existing objective/assignment intake and exact authorization/idempotency path |
| `comms5_revalidate_and_queue_work` | Revalidate one stale approved base and queue one bounded successor.

    This preserves the original failed attempt and exact authority scope. It
    never widens paths, changes the capability, or executes Codex; material
    repository drift fails closed for renewed specification approval.
     | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Current recovery contracts exist; legacy work-order IDs are not compatible; Map to current authorized stale-base recovery preserving failed attempt |
| `comms5_cancel_draft` | Append-only cancel of a draft; never cancels an objective or work order. | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Legacy seed lifecycle absent; current proposal transitions differ; Map only to a compatible draft transition with revision audit |
| `comms5_supersede_seed` | Append an old-draft-to-new-draft replacement relation. | STEWARD-GATED_WRITE | NOT_IMPLEMENTED MCP tool error | Legacy seed relation table absent; current proposal supersession contract differs; Add durable relation using existing proposal revision lifecycle if equivalent |

## Runtime boundary

Camrui adapter binds to `127.0.0.1:11826` only. It requires both Caddy-injected `X-Riverview-Comms5: 1` / `X-Riverview-Comms5-Principal: steward` and a distinct backend-hop bearer credential delivered by systemd credentials. OAuth validation is performed by the Ionoge Comms5 OAuth service through Caddy `forward_auth`; the old connector bearer route remains a separate compatibility path. The MCP process logs no request line, body, arguments, or bearer values.

No production database migration is required for the five implemented discovery operations or the stubs. No database connection is opened by the adapter. A future operation is not considered implemented until its Camrui dependency, exact authority action/scope, privacy projection, idempotency, and tests are documented and verified.

## Validation status

- Source catalog: 21 tools compared against historical FastMCP tool discovery.
- Camrui adapter release `588aee804fc6ada3cdf78f4bfded2f8306c783ea` is active on loopback `127.0.0.1:11826`; `/healthz` returned HTTP 200 at 2026-10-17 00:18 EDT.
- Ionoge OAuth source `048787f574d42ff073a9f94f571dc79943d60fa4` is active on loopback `127.0.0.1:11827`; local `/healthz` returned HTTP 200.
- The reverse tunnel did not start: the Camrui systemd manager stopped answering D-Bus/systemctl queries during the authorized start attempt. The pinned known-hosts credential path defect has been identified and corrected in follow-up source, but that correction has not yet been integrated or deployed.
- Caddy has not been changed or reloaded. Public `/comms5/mcp` still returns HTTP 401 and both OAuth discovery URLs return HTTP 404; no public OAuth or MCP path is accepted yet.
- Historical Comms5 database tables are absent on Camrui; no legacy migration was installed or is required for this increment.
- ChatGPT account connection and invocation remain unverified.
