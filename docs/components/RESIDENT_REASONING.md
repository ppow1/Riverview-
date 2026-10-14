<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_REASONING.md
Component: RESIDENT-REASONING
File Revision: 1.0.6
Purpose: Define resident context regrounding and bounded reasoning-provider routing
Authority: Exact office-state grant required; provider output is a proposal, never permission
Changed: 2026-10-11 UTC | RV-M4.2-001 | Establish isolated resident reasoning contract
Changed: 2026-10-11 UTC | RV-M4.2-ROUTE-MINIMUM-BUDGET | Reject fallback configurations whose minimum per-attempt budget exceeds the requested total
Changed: 2026-10-11 UTC | RV-M4.2-MARKDOWN-WHITESPACE | Normalize compact metadata formatting for clean controlled diff checks
Changed: 2026-10-11 UTC | RV-M4.2-LOCAL-PROVIDER-INTEGRATION | Document strict loopback provider adapter and actual host timeout boundary
Changed: 2026-10-11 UTC | RV-M4.2-LOCAL-PROVIDER-RESULT | Record actual model timeout separately from the verified mock HTTP contract
Changed: 2026-10-13 UTC | RV-REASONING-ESCALATION-CONTRACT | Specify task-escalation request/result boundary and integration limit
Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Pass canonical Grace role and authority boundaries into her assignment reasoning provider
History: Git and .riverview-backups/manifest.jsonl
-->
# Resident regrounding and reasoning routing

- **Milestone:** M4.2 — Resident regrounding and reasoning routing
- **Status:** Isolated engineering in progress; local provider contract tests pass, but actual model plan call and resident service are not operationally commissioned
- **Implementation:** `src/riverview_core/resident_reasoning.py`; `src/riverview_core/local_reasoning_provider.py`
- **Process graph:** `rv:resident-reasoning:runtime`
**Owner:** Resident runtime / CME integration

## Purpose and authority boundary

`ResidentReasoner` loads the currently bound office implementation, re-reads an
assignment at a consequential reasoning boundary, requires verified grounding
and regrounding, routes a bounded plan proposal, and stores its provenance and
plan in the authority registry's office-keyed state. It does not create or
transition assignments, execute tools, issue grants, or authorize any proposal.
Converting a proposal into an objective or work order remains a separately
authorized workflow. CME scheduling and worker execution do not depend on the
resident reasoning provider.

## Task escalation contract (integration pending)

`src/riverview_core/reasoning_escalation.py` defines a separate typed
`EscalationRequest`/`EscalationResult` contract for a provider selected because
of task complexity, a capability gap, or low confidence. This is distinct from
the existing fallback route, which tries another explicitly configured
provider only after the current provider fails or times out. The contract
correlates the original office, objective, assignment revision, model binding,
implementation revision, complete verified context fingerprint, exact target
provider, token limit (maximum 512), and timeout (maximum 60 seconds).

The caller must use the existing authority registry to authorize
`resident.reasoning.escalate` on `provider:<provider-id>` before the router is
called. The router returns a typed proposal only; it cannot create or dispatch
an assignment. Current source does not yet connect task-difficulty recognition
in `ResidentReasoner` to this router, persist escalation outcomes, or configure
an 80B provider. Unit tests use synthetic local providers and do not prove a
live route. Unavailable provider, capacity, timeout, invalid output, or changed
context returns a typed non-success result; the caller must retain the durable
objective and schedule a bounded retry or explicit Steward decision.

The implementation consumes M4.1's `AuthorityRegistry` and the frozen
`worker_adapter.knowledge_provider_v1` contract. No second knowledge API is
introduced.

`LocalReasoningProvider` is an optional implementation of the existing
`ReasoningProvider` contract. It sends bounded requests only to a literal
loopback OpenAI-compatible `/v1` endpoint, pins the served model name and
implementation SHA-256 to the bound implementation revision, and accepts only
the exact typed, one-step proposal schema. Transport errors return sanitized
`UNAVAILABLE`; malformed or incomplete responses become invalid proposals.
The adapter cannot execute work or authorize its proposal. Six isolated HTTP
contract tests pass. A real call to the installed Qwen3-0.6B model on Camrui
returned `UNAVAILABLE` at the 30-second bound before a complete proposal was
produced; no `ResidentReasoner` invocation, authority-state write, persistent
inference service, or change to the M3.3 worker path occurred. Evidence is in
`evidence/checkouts/M4.2-LOCAL-REASONING/20261011T1340Z-fce3c30/`.

For `office:grace` only, the provider prepends the same versioned Director of
Operations role profile used by the conversation service. Other offices retain
the generic resident proposal instruction and do not inherit Grace's identity.
Assignment facts and verified knowledge continue through the existing bounded,
redacted `ReasoningRequest`; provider output remains an unapproved typed
proposal. Unit coverage confirms the office-specific context and no-permission
boundary. This source change is not deployed or live-model verified.

## Interfaces

```python
class AssignmentContextReader(Protocol):
    def read(self, assignment_id: str) -> Mapping[str, Any]: ...

class ReasoningProvider(Protocol):
    provider_id: str
    def propose(self, request: ReasoningRequest) -> PlanProposal: ...

class ResidentReasoner:
    def propose(self, assignment_id: str, *, trigger: str,
                token_budget: int) -> ReasoningResult: ...
```

The assignment reader must return a current mapping with matching `id` and a
stable, non-empty `revision`. Context must be sanitized: recursive keys
containing `token`, `credential`, `password`, `secret`, `dsn`, `api_key`, or
`private_key` are rejected, and assignment plus grounding values may not exceed
32 KiB serialized. Providers receive assignment/knowledge context, current
office binding and implementation revisions, prior plan, trigger, request ID,
and a divided token budget. They never receive credentials or an authority
capability.

Grounding calls reuse the exact callable signatures
`ground_assignment(assignment)` and
`reground_assignment(assignment, trigger)` from knowledge-provider v1. Both
results must have `KnowledgeStatus.VERIFIED`, complete retrieval, and validated
source references before reasoning runs. Other knowledge status values are
persisted as non-authorizing evidence and return `WAITING_FOR_EVIDENCE`.

`PlanProposal` is structured as a bounded summary and 1–20 ordered steps.
Each step has a unique `step_id`, an objective, acceptance criteria, and
dependencies that refer only to preceding steps. `tokens_used` must be a
non-negative integer and cannot exceed that provider attempt's allocated
budget. A proposal is explicitly unverified; no command or action interface is
exposed.

## Routing, budgets, and failure semantics

The active `office_bindings` row selects the primary provider by its exact
`provider_ref`; it is never selected from free text. Fallback IDs must be
explicitly configured, unique, present in the provider map, and limited to two
per primary. At most eight providers may be configured. The total requested
token budget is divided across primary plus fallbacks so a timeout cannot
silently allocate the full budget again. The route shares a process-wide cap of
eight in-flight provider/knowledge calls; timed-out threads are daemons and
remain bounded by that cap until they exit. Per-call timeouts are greater than
zero and at most 30 seconds. The total token budget must be at least the number
of route candidates; otherwise routing is rejected before provider invocation.

Only timeout/provider exception permits trying the next configured route.
Invalid schema, over-budget output, provider identity mismatch, changed office
binding, or changed assignment revision stops the route. `UNAVAILABLE` is never
treated as verified. A new `ResidentReasoner` reads the previous plan from
office state; the new context is grounded again before it is supplied to a
provider.

| `ReasoningStatus` | Meaning |
|---|---|
| `PROPOSED` | Proposal passed schema/budget/freshness checks and was durably stored; it is not authorized or independently verified. |
| `WAITING_FOR_EVIDENCE` | Assignment/knowledge context is absent, oversized, or not VERIFIED. No provider is called. |
| `AUTHORITY_DENIED` | Exact active `office.state.write` grant is absent or revoked. No assignment context/provider call is made. |
| `UNAVAILABLE` | Registry, route, provider, or durable authority state is unavailable. |
| `STALE_CONTEXT` | The office binding or assignment revision changed during reasoning; proposal is discarded. |
| `STATE_CONFLICT` | Office state compare-and-swap or bounded write failed; proposal is not reported successful. |
| `INVALID_PROPOSAL` | Provider output is not the typed plan schema or exceeds its allocated token budget. |

The office-state `resident_reasoning_v1` value retains at most the latest 32
outcome summaries, source references, source revision/hash, retrieval status,
provider ID, trigger, detail code, and latest plan by assignment ID. Grounding
values and raw prompts are not persisted by this component. Writes use the
existing exact `(office.state.write, office:<id>)` grant and expected state
revision. The authority registry appends its normal office-state revision event.

## Process and recovery

1. Verify exact office-state authority and read the active binding/state.
2. Load the current assignment revision; reject credential-shaped or oversized
   context.
3. Call knowledge-provider v1 grounding and regrounding for the trigger.
4. Persist non-verified outcomes and wait without invoking reasoning.
5. Route to the exact bound provider and bounded configured fallbacks.
6. Validate proposal schema/token use and re-read office binding and assignment
   revision; discard stale results.
7. Persist the proposal with compare-and-swap; return `PROPOSED` only after the
   durable write succeeds.
8. On restart, instantiate a new runtime, reload authoritative office/assignment
   state, reground, then provide the persisted prior plan to the selected
   implementation.

The component-specific flow and operational diagnostics are in
[`RESIDENT_REASONING_FLOW.md`](RESIDENT_REASONING_FLOW.md) and
[`RESIDENT_REASONING_COOKBOOK.md`](RESIDENT_REASONING_COOKBOOK.md).

## Verification and limits

Isolated PostgreSQL tests cover durable resume across runtime replacement,
grounding failure, explicit timeout fallback, provider replacement with
unchanged grants, unavailable routes, credential-key rejection, assignment
revision changes, revocation, and token-budget enforcement. They use fake
providers and are integration tests of the contract/state boundary only. The
loopback provider contract is separately covered by six fake-HTTP tests, but its
actual model call did not complete within the bounded host request as recorded
above. No resident service, browser chat, work-order promotion, or Grace
objective-to-artifact cycle is commissioned by these tests. M4.2 full DoD and
Steward acceptance remain open.
