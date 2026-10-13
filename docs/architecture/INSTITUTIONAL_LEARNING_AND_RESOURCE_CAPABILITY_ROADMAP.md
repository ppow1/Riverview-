<!-- RIVERVIEW~ CONTROLLED DOCUMENT
File Revision: 1.0.0
Component: INSTITUTIONAL-LEARNING-AND-RESOURCE-ARCHITECTURE
Status: Roadmap note; not an implementation contract or authority grant
Purpose: Preserve a documentation-first path for institutional learning and composable resources
Authority: Steward-approved institutional authority registry remains authoritative
PL-0016: Referenced by the Steward, but no matching source document is present in this checkout; reconcile before claiming conformance.
-->

# Institutional learning and resource capability roadmap

## Learning boundary

Riverview already has useful foundations, not a commissioned general learning
system. `AI_HINTS.md` requires documentation-first work. `RepositoryKnowledgeProvider`
reads commit-pinned repository facts and reports learning writes as unavailable.
`ResidentReasoner` regrounds assignments and keeps bounded office-state plans and
provider outcomes. Neither component is an authoritative cross-session fact store.
The PostgreSQL authority registry owns identities, grants, and office state; it
must not be repurposed as an untyped knowledge table.

Near-term work should extend those records through explicit typed contracts:

1. Before discovery, retrieve applicable governance, architecture, process graph,
   diagnostic cookbook, and prior evidence. Record the source revision and query
   boundary so repeated sessions can reuse established facts.
2. Separate durable facts (approved procedure, verified dependency, stable
   identity) from dynamic observations (health, capacity, current binding, DNS,
   model availability). Dynamic observations carry observed time and freshness.
3. Store verified learning only in the authoritative owner for that fact, with
   source, revision or observation time, verifier, confidence/status, and history.
   Never promote a model answer or a worker's own claim directly to fact.
4. Reground before consequential actions and on source, binding, resource, or
   policy change. A contradiction marks the earlier record superseded with
   provenance; it does not erase history or silently rewrite authority.
5. Reuse established results across sessions and model/provider changes through
   stable institutional IDs and retrieval contracts, not chat transcript search
   as the source of truth.

PL-0016 must be located and mapped to these boundaries before this roadmap note
can be described as conformant to it. No separate learning subsystem is proposed
here.

## Capability and resource assessment

Capability existence and current readiness are separate questions. Reuse the
existing worker/capability registration, exact-grant, lease, health, attempt,
verification, and CME event records. An Engineering assessment should persist:

- requested capability and version;
- registered adapter/resource identity and provenance;
- dependencies and their observed readiness (`online`, `offline`, `busy`,
  `degraded`, or `unknown`);
- capacity, concurrency, timeout, and validation freshness;
- exact authorization decision and scope;
- alternative provider assessment, if one is already registered;
- decision, failure, recovery, and verification references in the canonical
  process graph.

For the first Codex CLI slice, register only the bounded adapter, its isolated
workspace dependency, its credential/configuration readiness, its resource
capacity, and a separate verifier. Do not infer readiness from an installed
binary or from an interactive Codex session. Do not grant a model shell or
institutional authority.

## Institutional resource requests

If Engineering lacks a required resource, preserve a durable pending request and
continue with work that does not depend on that resource. The intended path is
Engineering assessment → HR/Helen request → allocated, denied, or unavailable
decision → Engineering continuation. Helen is not commissioned; no request is
sent on her behalf and no allocation is presumed. Steward decisions and
provisioning continue through current exact-grant authority mechanisms.

## Future Estate and controls integration

Treat hardware, compute, services, and facilities as resources in one identity
and capability model. Future records may describe OctoMiner digital twins,
model deployment and power-control capabilities, the Estate inventory, routers,
computers, tablets, HDMI matrix, audio processing, command chair, and other
equipment. A digital twin is a read-only projection until a separately authorized
control adapter is commissioned. Resource identity, health, capacity, and
authority must remain distinct. This campaign does not implement hardware
control or alter GPU, router, DNS, or WAN configuration.
