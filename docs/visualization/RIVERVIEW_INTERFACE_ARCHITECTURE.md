<!-- Document Revision: 1.0.0 -->
# Riverview interface architecture

## Purpose

Riverview V2 is the current functional integration shell. It is not a finished map of the institution. Grow the interface by exposing existing capabilities and evidence in a hierarchy, not by adding a permanent tab for every capability.

## Progressive disclosure

Use the same route shape on desktop, mobile, command-chair displays, Stream Deck actions, and eventual Quest/XR views:

1. **Institution overview:** institution/department health, significant attention, active/blocked work, resources, and recently changed evidence.
2. **Department or system:** Offices/Residents, Engineering, Communications, Compute/AI, Governance, Archives, and physical systems.
3. **Capability:** named operation/service/workflow with owner, lifecycle, dependencies, source, and access class.
4. **Detailed status:** current value/state, last updated, freshness/unknown condition, related work and dependencies.
5. **Evidence:** authoritative record, event/audit history, validation result, diagnostic artifact, or release identity.
6. **Authorized action:** operation-specific controls, exact record ID, role/grant check, confirmation, outcome, and audit result.

Only a small set of stable top-level destinations should remain visible. Group the rest by department/system and reveal them on demand through navigation search, workflow search, links from related work, and a consistent breadcrumb. Keep direct URLs stable for a capability, not tied to its current menu placement.

## Separate capability, component, navigation, artwork, and live visualization

- **Functional capability:** backend operation and API contract, lifecycle, data ownership, and authorization. It exists independently of a web page.
- **Reusable UI component:** status card, state badge, timestamp/freshness label, event/attention row, telemetry plot, dependency graph, evidence list, search/filter, confirmation dialog, or error state. A component is not its own data store.
- **Navigation/layout:** small stable shell, department grouping, search, breadcrumbs, recent/favorite access. Navigation only locates capabilities and never grants them.
- **Historical artwork:** immutable binary plus provenance, date, original path/hash, intended meaning, and a flag that distinguishes concept art from implementation. Artwork never makes live status claims.
- **Live operational visualization:** a read-only projection of authoritative server data with source, record identity, timestamp, and stale/unknown handling. It may use maps or a cinematic command-room layout while retaining links to the source evidence.

## One operational data plane, multiple presentations

V2 should consume the existing authenticated Riverview APIs, backed by their owning databases, service supervisors, notification publisher, and artifact systems. A mobile view, chair display, Stream Deck plugin, or spatial view should use the same contract and IDs. Do not mirror state into presentation-specific JSON/SQLite stores. Where source domains differ (for example The Estate file runtime versus Riverview PostgreSQL), use an explicit, read-only adapter only after establishing which system is authoritative for that capability; do not merge similarly named records by display text.

Separate **read projections** from **commands**. Read projections can combine authorized status and linked evidence. Commands call the existing operation API with the same identity, exact object ID, lifecycle preconditions, CSRF/session protections, and audit path used on the web. Stream Deck is a command launcher, not a privileged identity. XR should begin read-only. A V2 hidden button, a physical control, or a spatial object must never bypass server authorization.

## Presentation rules

- State the backend source, “as of” time, and record link on live cards; show `unknown`/`stale` as such, never as zero or healthy.
- Distinguish current production, historical proof, proposal, fixture, and concept art visually and in accessible text.
- Make active and blocked work navigable through owner → stage → dependency/blocker → evidence.
- Give each action an exact target, eligibility explanation, confirmation, result, and durable audit link.
- Keep notification preferences separate from notification delivery history; both read from their existing authoritative systems.
- Use the same semantic status vocabulary across display sizes: healthy, attention, blocked, unknown, stale, completed, and failed, with text labels in addition to color.
- Allow saved filters and recent destinations to personalize navigation without changing shared institutional data.

## Reusable presentation building blocks

Build from current V2 components and API clients: authenticated shell/session, capability group navigation, work/objective row, progress stage, notification/attention card, resource/host card, Grace trace, evidence/provenance panel, confirmation flow, report/status panel, responsive layout, and accessible map/list alternative. Extend these where necessary; do not create a second auth client, another dispatcher, another settings store, or a standalone CMS of live facts.

## Channel mapping

| Channel | Best initial role | Data/action rule |
|---|---|---|
| V2 desktop | Full drill-down, filters, evidence, authorized action | Existing server APIs, full role enforcement. |
| Mobile browser | Attention, current assignments, quick read-only status, confirmation flows only where usable | Same responsive V2 session/API; no separate mobile state. |
| Command chair / panoramic displays | Overview, service/resource maps, blocked work and attention | Read-only shared projection; avoid dense forms on display wall. |
| Stream Deck | Small number of named navigation and pre-authorized operator actions | Call established control/API layer; show action target and result. |
| Quest/WebXR | Spatial overview, room/system location, selected read-only status/evidence | Reuse same read APIs; no XR-specific authority or duplicate model of operational state. |

The Estate concept images and Quest experiment inform composition, rooms, and spatial affordances. They are not final layout instructions or proof that the pictured system is live. See the [visual asset catalog](RIVERVIEW_VISUAL_ASSET_CATALOG.md).
