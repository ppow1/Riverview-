<!--
Riverview Controlled Document
File: docs/components/GRACE_COMMISSIONING_FLOW.md
Component: GRACE-COMMISSIONING
File Revision: 1.0.1
Task: RV-C4-PR115-119-READINESS-001-REMEDIATION
Purpose: Canonical nonproduction commissioning readiness flow
Authority: Isolated preflight only
Changed: 2026-10-18 UTC | RV-C4-PR115-119-READINESS-001-REMEDIATION | Add generated workflow diagram source
-->

# Grace commissioning readiness flow

This diagram is generated from `process_graphs/grace/commissioning-pr115-119.json`.

```mermaid
flowchart LR
  subgraph g_rv_grace_commissioning_pr115_119["GRACE-COMMISSIONING / grace-commissioning-readiness.v1"]
    g_rv_grace_commissioning_pr115_119_provenance_81680457(["Confirm candidate ancestry, PR CI, package identity and source provenance"])
    g_rv_grace_commissioning_pr115_119_isolated_checks_f785f6d9["Run graph/revision/package and disposable PostgreSQL ACL, migration, and worker checks"]
    g_rv_grace_commissioning_pr115_119_identity_gates_163ceb14["Read-only compare Comms5 OAuth route with the distinct external-reasoning provider identity and source-worker grants"]
    g_rv_grace_commissioning_pr115_119_blocked_cb9297cc[["Keep capability NOT_COMMISSIONED and stop if provider, worker, objective, or deployment evidence is missing"]]
    g_rv_grace_commissioning_pr115_119_steward_handoff_71a85f17(["Deliver evidence and exact unresolved decisions for Steward and Operations review"])
  end
  g_rv_grace_commissioning_pr115_119_provenance_81680457 --> g_rv_grace_commissioning_pr115_119_isolated_checks_f785f6d9
  g_rv_grace_commissioning_pr115_119_isolated_checks_f785f6d9 --> g_rv_grace_commissioning_pr115_119_identity_gates_163ceb14
  g_rv_grace_commissioning_pr115_119_identity_gates_163ceb14 -->|diagnostic_branch: mandatory gate absent or unverified| g_rv_grace_commissioning_pr115_119_blocked_cb9297cc
  g_rv_grace_commissioning_pr115_119_identity_gates_163ceb14 -->|evidence packaged for review| g_rv_grace_commissioning_pr115_119_steward_handoff_71a85f17
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
