# Riverview!

**A living, event-driven AI institution in service of the Steward's purpose.**

This repository is the **new, clean-start implementation** of Riverview!, distinct from the historical `ppow1/Riverview` codebase. Historical Riverview and Estate artifacts are references, **not automatically inherited dependencies**.

## Founding engineering requirements

- **Event-driven and unattended:** durable events drive concurrent assignments, including recovery after restart; no conversation turn is required to keep work moving.
- **Institutional core:** separate authority, resident identity, durable state, event transport, work coordination, execution, verification, CME monitoring, notification, and visualization contracts. One authoritative lifecycle per assignment.
- **CME:** always-on, simple, concurrent progress-monitoring and recovery coordination; residents can inspect and request actions through permission-aware interfaces. It does not govern the institution or perform all engineering itself.
- **Office / Occupant / Implementation / State:** persistent offices and authority, replaceable occupants and models, durable institutional continuity.
- **Regrounding:** residents reload authoritative rules, assignment state, and scope at defined boundaries; conversation memory is not institutional authority.
- **Reasoning escalation:** selectable, configurable, transport-independent providers, including existing Playwright / Doorbell / MCP integrations, local inference, and optional APIs.
- **Notifications from day one:** visual, audio, and SMS alerts, delivery/acknowledgment status, and durable Steward decision requests. Future app/SMS/voice replies use the same authenticated authority contract.
- **Self-documenting construction:** every component is delivered with working code, versioned flowchart, diagnostic/troubleshooting cookbook, live operational visualization, and event/notification/recovery contracts. Documentation evolves with implementation.
- **Spatial representation:** stable identities, relationships, and spatial metadata support dashboard, castle/city, 3D, and future Quest/VR renderers without governing the underlying behavior.
- **Undercurrent:** independent high-privacy trust domain with private events, encrypted storage, minimal content logging, controlled export, and defined purge procedures. The ordinary institution cannot automatically inspect private content.
- **Complexity budget:** one owner per responsibility; no parallel hidden control paths, hard-coded resident or GPU assumptions, or undocumented dependencies.

## Development discipline

Build from the core outward. Define contracts before adapters. Reassess historical components against the new contracts; reuse, simplify, or rewrite on evidence. Each increment must be explainable, diagnosable, visible, testable, and committed to this repository.

## Status

**Specification / foundation stage.** No deployed Riverview! runtime is claimed. The original repository remains unchanged.

## Initial document locations

- `docs/architecture/CORE_CONTRACT.md` — institutional core specification.
- `docs/security/UNDERCURRENT_BOUNDARY.md` — private-domain boundary specification.
- `docs/architecture/VISUAL_REFERENCE.md` — historical castle/city and institutional visualization mapping.
- `docs/standards/COMPONENT_DEFINITION_OF_DONE.md` — synchronized implementation, diagram, cookbook, visualization, and event requirements.
