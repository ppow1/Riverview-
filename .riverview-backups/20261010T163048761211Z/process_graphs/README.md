# Riverview universal process graph standard

**Document Revision:** 1.0.0  
**Standard ID:** RV-PROCESS-GRAPH  
**Status:** Active project standard  
**Authority:** Riverview Steward; extensions require a versioned change record.

## Canonical source and views

The canonical process model is the set of workflow JSON files under this
directory. The aggregate JSON is generated at
`process_graphs/generated/riverview-process-graph.json`; focused Mermaid diagrams
are generated into the Mermaid fences in component flow documents, and the
aggregate Mermaid projection is in
`process_graphs/generated/RIVERVIEW_PROCESS_GRAPH.md`. Do not hand-edit generated
views. Run `python3 scripts/process_graph.py generate` after changing canonical
graphs. CI runs `python3 scripts/process_graph.py check` and fails if the JSON
aggregate or any Mermaid view is stale. Generator updates preserve the previous
controlled document revision before changing generated content.

## Identity and revisions

Node IDs are immutable, globally unique values of the form
`rv:<component-slug>:<workflow-slug>:<semantic-node-slug>`. They identify the
logical step, not its position or label. Keep an ID when the node is moved or
renamed; never recycle a retired ID. Track logical-node changes using
`node_revision`, independently of the stable ID. Graph files have a separate
`graph_revision`; repository file revisions for JSON are recorded in
`.riverview-revisions.json`.

## Types and edges

Built-in node types are `process`, `entry`, `exit`, `decision`, `measurement`,
`failure`, `recovery`, `verification`, `jump`, and `escalation`. Organizations may
add namespaced extension types matching `x-<namespace>:<type>`; consumers must
preserve unknown namespaced values. A jump node carries `jump_target_id`, and a
typed `jump` edge must point to that exact, registered node.

Built-in edge types distinguish `runtime_transition`, `prerequisite`,
`diagnostic_branch`, `recovery_route`, `verification`, `jump`, `escalation`, and
`documentation`. Runtime transitions describe observed execution only. Use
`prerequisite` for ordering/dependency relationships; do not imply a runtime call
unless code or an operational trace verifies one. Cross-component references
must resolve in the aggregate registry. The graph records source files, document
links, and verification evidence; these references are validated as repository
paths.

## Graphs and scale

Each workflow owns a focused JSON graph and one generated Mermaid projection.
The aggregate contains every registered node and edge. Large views retain
logical jump nodes and cross-component links; component operators should use
focused workflow projections for detailed review. Graph registration is required
for new components and synchronized whenever behavior, state transitions,
dependencies, failure handling, recovery, or verification changes.

The schema is `process_graphs/schema/riverview-process-graph.schema.json`.
The conversion, validation, aggregate generation, and diagram synchronization
pipeline is `scripts/process_graph.py`. A successful check proves structural and
source-view consistency only; it does not prove runtime behavior or acceptance.

## Imported first integrations

`RUNTIME-BASELINE` retains its existing commissioning and recovery path in
`runtime-baseline/runtime-baseline.json`. `POSTGRES-LEDGER` retains its migration,
transaction, and assignment lifecycle flows in the two PostgreSQL graphs. Their
existing cookbook and component references remain attached. The M3.1 dashboard
node is a reserved, explicitly planned target to make existing documentary jump
links resolvable; it does not assert that the dashboard exists. M1.3 is the first
component whose design and implementation will be authored natively against this
standard.

Graph reference slots are deliberately available for cookbook diagnostics,
systematic fault isolation, persistent troubleshooting evidence, verification
loops, variable diagnostic pass limits, escalation hierarchies, and institutional
learning. Those systems are future roadmap work and are not implemented here.
