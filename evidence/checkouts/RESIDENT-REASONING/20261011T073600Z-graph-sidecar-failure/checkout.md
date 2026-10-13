<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/RESIDENT-REASONING/20261011T073600Z-graph-sidecar-failure/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Preserve first full-suite failure caused by the new graph missing its checksum sidecar
Authority: Private PostgreSQL test cluster only; shared Camrui state not accessed by tests
Changed: 2026-10-11 UTC | RV-M4.2-001 | Retain failed graph/revision validation and isolated fixture cleanup
History: artifacts.json checksums
-->
# First M4.2 full-suite failure

The complete suite reached the process-graph tests and failed with `GraphError: JSON file revision sidecar is missing or invalid: process_graphs/resident-reasoning/runtime.json`. The graph was newly created but had not yet been registered in `.riverview-revisions.json`; this is an engineering-record defect, not a graph-runtime failure. The suite reported 135 run with one graph setup error; graph setup prevented its remaining subtests from running. Private PostgreSQL cleanup queries returned zero `rvtest_*` schemas and zero fixture roles. The private cluster was stopped. The correction is to register the canonical JSON graph's revision, byte count and SHA-256 in the repository sidecar before running graph validation, then regenerate all graph views.
