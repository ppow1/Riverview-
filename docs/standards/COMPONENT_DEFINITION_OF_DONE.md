# Riverview~ Component Definition of Done (DoD)

**Revision:** Rev 1.1  
**Status:** Active engineering standard  
**Effective:** 2026-10-09  
**Applies to:** every new or modified Riverview~ component, including the institutional Core, adapters, databases, workers, CME, and Steward-facing services.  
**Supersedes:** initial unversioned Component Definition of Done.  
**Authority:** Steward-approved project engineering requirement; changes require an explicit revision, review, and commit.

## Principle

**Passing tests does not mean done.** A component is done only when its code, executable evidence, documentation, troubleshooting cookbook, versioned flowcharts, and real Steward-visible operational status are complete **together**. No component may be declared done merely because a stub, mock, diagram, or snapshot exists. Report partial status plainly. The operational view must distinguish *unavailable*, *not initialized*, *stale*, *degraded*, and *healthy*.

## Seven mandatory deliverables

1. **Code and contracts.** Committed implementation, identified version/commit, accountable owner, purpose, inputs/outputs, authority and security boundaries, dependencies, configuration, event schemas, failure and recovery semantics, notification behavior, and idempotency/replay contract. No hidden control path.
2. **Functionality demonstrated.** Deployed in the declared target environment and exercised end to end. Evidence must cover normal operations, failures, concurrency/isolation where relevant, restart/replay, persistence, and negative cases. Distinguish development tests from production readiness. Never infer success from a command being dispatched.
3. **Complete versioned documentation.** Component specification explains architecture, contracts, deployment, configuration, lifecycle, limitations, dependencies, data ownership, migrations and upgrade/rollback process, and security/authorization. Changes affecting behavior update documentation in the same change.
4. **Troubleshooting and recovery cookbook.** A new engineer can diagnose and recover using reproducible commands, expected output, fault symptoms, error codes, escalation thresholds, safe recovery procedures, verification checks, and known limitations. Include a consolidated **read-only** diagnostic path. Destructive operations require explicit authority and backup safeguards.
5. **Versioned visualization flowcharts.** Source-controlled process diagram includes normal path, state transitions, error/rollback/retry branches, dependencies, notifications, and recovery. Diagrams reflect the actual implementation, not future behavior mislabeled as deployed.
6. **Steward-level live operational visualization.** Accessible Steward view bound to actual authoritative durable state, showing component identity, version, current status, heartbeat/freshness, assignments/events or equivalent domain metrics, failures, alerts, and drill-down/recovery guidance. Permission filtering applies. Static screenshots, standalone JSON, mock dashboards, or a flowchart alone do **not** satisfy this gate. A read-only diagnostic snapshot is useful evidence but not a live Steward view.

7. **Operational autonomy and blocker clearance.** Prove the component performs its intended recurring work unattended after boot, restart, dependency interruption, and recovery. Inventory every one-time setup step, permission requirement, credential renewal, manual command, Steward decision, escalation, external dependency, and waiting state. For each blocker document the trigger, owner, policy, durable status, detection/timeout, notification, recovery/retry, authorization to resume, and evidence that work actually resumes. Required Steward approvals remain mandatory; automation must route, record, await, and resume on authorized decision, never bypass approval. If an approval or external dependency is unresolved, the component must visibly remain blocked with accountable ownership and escalation, not claim completion. No indefinite invisible waits or undocumented manual intervention. An explicit one-time commissioning step may be acceptable only when completed, reproducible, documented, and not required for normal restart or recovery.

### Blocker register and unattended-run evidence

Each component's acceptance record must include a blocker register with: `blocker_id`, type (commissioning / credential / permission / approval / escalation / dependency / fault / manual action), detection signal, owning office, authority required, timeout, durable state, alert destination, retry/resume trigger, and test evidence. Record every unresolved blocker and its operational impact.

The unattended-run test must demonstrate the component's declared normal lifecycle without a human issuing follow-up commands; simulated failures and approval holds must be included where relevant. An approval hold passes only if the request, notification, wait state, authorized decision, and automatic continuation are verified end to end. Do not claim operational autonomy for a library with no running process.

## Cross-cutting acceptance gates

- **Institutional integrity:** one authoritative lifecycle per assignment; persistent office/occupant/implementation/state separation where applicable; no fabricated progress.
- **Events and recovery:** durable event identities and idempotency keys, failure semantics, restart/replay proof, documented retention and recovery path. Where applicable, notification delivery and acknowledgment states must be visible.
- **Observability:** telemetry has timestamp and freshness thresholds; unavailable or stale sources never display healthy. CME and Steward can distinguish failures from missing data.
- **Security and isolation:** explicit authority boundary and least privilege; Undercurrent/private data never exported into ordinary logs, dashboards, or diagnostics without policy approval.
- **Spatial mapping:** stable component identity, parent/relationship metadata, and optional coordinates are independent of execution and authority. Multiple visual renderers may project the same state.
- **Reproducibility:** test commands, target environment, version/commit, result, timestamp, and unresolved exceptions are recorded.
- **Change synchronization:** behavior/contract/diagnostic changes update tests, cookbook, flowchart, and visualization in the same delivery. No undocumented exceptions.

## Release evidence / DoD checklist

Record a component-specific acceptance record with:

| Gate | Evidence required | Status |
| --- | --- | --- |
| Code | commit, contracts, owner, target environment | PASS / FAIL / PARTIAL |
| Functionality | actual deployment and test logs, fault/restart/replay results | PASS / FAIL / PARTIAL |
| Documentation | versioned specification and operational boundaries | PASS / FAIL / PARTIAL |
| Cookbook | commands, expected results, failure and recovery verification | PASS / FAIL / PARTIAL |
| Flowcharts | committed source reflecting implemented behavior | PASS / FAIL / PARTIAL |
| Steward view | live URL/view, real-state proof, freshness/failure tests | PASS / FAIL / PARTIAL |
| Operational autonomy | blocker register, unattended execution, approval/escalation/recovery/resume tests | PASS / FAIL / PARTIAL |

**Release rule:** all seven must be **PASS**, all cross-cutting gates applicable to the component must pass, and the Steward must explicitly accept the evidence. A component with any PARTIAL or FAIL is **NOT DONE**. Work can continue on it, but do not move to the next component while describing the current one as complete. Exceptions require an explicitly scoped, dated Steward waiver; a waiver is not a PASS.

## Component cookbook minimum contents

Purpose and owner; interfaces/dependencies; process and state diagram; events/idempotency; health signals/freshness/failure codes; read-only diagnostics; authorized recovery and verification; test evidence; known limitations; Steward and spatial view mapping.

## PostgreSQL ledger acceptance baseline (2026-10-09)

- **Code:** PASS — `src/riverview_core/postgres_ledger.py` committed.
- **Functionality:** PARTIAL — six SQLite/PostgreSQL tests passed on Camrui; no persistent production service, fault/restart stress, migrations or independent verifier.
- **Documentation:** PARTIAL — component contract exists; deployment/rollback/migration and full operational contracts incomplete.
- **Cookbook:** PARTIAL — diagnostic cookbook committed; production restore drill and escalation unverified.
- **Flowcharts:** PARTIAL — versioned transaction and lifecycle diagrams committed; full failure/notification/recovery integration not implemented.
- **Steward view:** FAIL — read-only on-demand snapshot works, returns `not_initialized` for `public`; no live dashboard or authoritative permanent tables yet.
- **Operational autonomy:** FAIL — no always-on process, automatic resume, approval routing, escalation or dependency recovery; permanent ledger initialization outstanding.
- **Overall:** **NOT DONE**. Do not present the ledger as production-ready or the snapshot as a live dashboard.

## Revision history

| Revision | Date | Change |
| --- | --- | --- |
| Unversioned | Before 2026-10-09 | Initial five synchronized artifacts and engineering acceptance principle |
| **1.0** | **2026-10-09** | Explicit six-gate measurable DoD, Steward acceptance, release evidence, live-view and telemetry freshness requirements, cross-cutting gates, and PostgreSQL ledger baseline |
| **1.1** | **2026-10-09** | Seventh gate: operational autonomy, explicit blocker register, unattended-run evidence, and durable approval/escalation/resumption rules |

Future revisions must increment the revision, document what changed and why, and identify affected component acceptance records.
