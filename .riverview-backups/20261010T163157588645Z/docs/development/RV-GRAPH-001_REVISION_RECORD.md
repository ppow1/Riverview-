# Riverview~ RV-GRAPH-001 process graph standard record

**Document Revision:** 1.0.0  
**Task:** RV-GRAPH-001  
**Component:** RV-PROCESS-GRAPH  
**Date:** 2026-10-10 UTC  
**Status:** STANDARD IMPLEMENTED; M1.1/M1.2 INTEGRATIONS VERIFIED

## Authority and requirements

Steward directive Part B authorized a Riverview-wide process graph standard
before further component diagrams. It requires immutable globally unique node
identity, independent node revision, extensible node/edge types, explicit
runtime/dependency/failure/recovery/verification/escalation/documentation
semantics, resolvable cross-component jumps, machine-readable schema and source,
documentation, verification references, generated aggregate/focused Mermaid
views, graph validation tests, Definition of Done enforcement, and preservation
of existing M1.1/M1.2 work. M1.3 is the first native integration. Future diagnostic
and learning capabilities are extension points only.

The canonical representation is workflow JSON under `process_graphs/`. Mermaid
is generated output synchronized into the existing component flow documents.
`scripts/process_graph.py generate` writes projections and preserves predecessors;
`scripts/process_graph.py check` verifies graph schema/references, globally unique
IDs, typed edges, external jump targets, JSON sidecar revisions/checksums,
aggregate content and Mermaid synchronization. CI runs this check.

## Decisions

- Immutable IDs use `rv:<component-slug>:<workflow-slug>:<semantic-node-slug>`;
  layout and label changes do not alter identity. `node_revision` and
  `graph_revision` are separate from repository file revisions.
- Built-in nodes: process, entry, exit, decision, measurement, failure, recovery,
  verification, jump, escalation. Namespaced `x-<namespace>:<type>` additions
  are preserved for forward compatibility.
- Built-in edges: runtime transition, prerequisite, diagnostic branch, recovery
  route, verification, jump, escalation, documentation. Cross-workflow runtime
  edges fail validation; prerequisite edges explicitly do not claim runtime
  calls.
- All jump edges point to a registered cross-component target. M3.1's target is
  a planned registry node, not a dashboard implementation claim.
- Aggregate JSON is the complete logical registered graph; workflow documents
  are focused projections. Operators follow stable jump IDs instead of relying
  on one continuous large drawing.
- Existing RUNTIME-BASELINE and POSTGRES-LEDGER component identifiers, flow docs,
  cookbooks and semantic steps are retained and mapped to graph IDs. No
  diagnostic-learning architecture is implemented in this task.

## Implementation and integration results

Schema: `process_graphs/schema/riverview-process-graph.schema.json`. Canonical
graphs: `process_graphs/runtime-baseline/runtime-baseline.json`, the two
`process_graphs/postgres-ledger/*.json` workflows, and the M3.1 planned target.
M1.3 native graph is `process_graphs/event-processor/assignment-progression.json`.
Aggregate: `process_graphs/generated/riverview-process-graph.json`; aggregate
visual: `process_graphs/generated/RIVERVIEW_PROCESS_GRAPH.md`.

The M1.1 and M1.2 flow diagrams are regenerated from canonical JSON. The M1.1
cookbook and existing M1.2 cookbook references remain preserved. The M3.1
dashboard target remains explicitly planned. RV-M1.3-001 introduces an event
processor graph with pending systemd deployment gates.

Validation tests cover JSON Schema conformance, stable/global IDs, missing
references, invalid edge types, runtime/dependency separation, jump resolution,
extension compatibility, sidecar checksum enforcement, and exact generated view
synchronization. Current graph inventory is five workflows and 79 nodes. Initial
complete test execution passed 66 tests, including all six M1.2 and four new M1.3
PostgreSQL tests with zero skips; graph-specific tests passed 9/9. Evidence:
`evidence/checkouts/EVENT-PROCESSOR/20261010T1628Z-3fd6fd2/checkout.md`.

## Affected files and checkout

Controlled predecessors were captured in `.riverview-backups/manifest.jsonl`;
JSON graph/schema file revisions and SHA-256 values are in
`.riverview-revisions.json`. Existing documents have incremented native
revisions. Exact changed paths, backup hashes, and the full checkout revision
audit are recorded after CI completes. CI must pass before this record is
considered verified. This task does not claim completion of M1.1/M1.2 full
component DoD or M1.3 acceptance.
