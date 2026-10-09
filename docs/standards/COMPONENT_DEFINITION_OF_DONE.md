# Component definition of done — Riverview!

Every component must ship with five synchronized artifacts: (1) implementation and versioned input/output/authority contracts, (2) an operational flowchart with error/recovery branches, (3) a new-engineer troubleshooting cookbook with commands, expected results, error codes and recovery verification, (4) a live visualization bound to actual durable operational state, and (5) event schemas, notification behavior, and recovery semantics.

Acceptance requires tests of documented normal behavior, faults, restart/replay, isolation and observability. A component may not silently invent progress, imply success from dispatch, or show stale telemetry as healthy. Any code change affecting a contract, state transition, or diagnosis updates its corresponding artifacts in the same change.

The spatial registry supplies stable IDs, parent/relationship metadata, and view coordinates independently of authority. Renderer choices must not determine institutional behavior. A component can appear in organizational, operational, historical, project and spatial views without duplicating authoritative state.

Security-sensitive components expose only policy-approved metadata to general diagnostics and dashboards. Undercurrent private content is never exported into normal logs or documentation by default.

## New-component cookbook template

- Purpose and accountable owner
- Interfaces and dependencies
- Flowchart and state transitions
- Events emitted/consumed, including idempotency keys
- Healthy signals, telemetry freshness and failure codes
- Single consolidated read-only diagnostic procedure
- Recovery procedure, authorization requirements, and verification
- Tests and known limitations
- Visualization mapping and spatial identity
