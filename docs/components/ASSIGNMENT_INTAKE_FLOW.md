<!--
Riverview~ Controlled Document
File: docs/components/ASSIGNMENT_INTAKE_FLOW.md
Component: ASSIGNMENT-INTAKE
File Revision: 1.0.1
Purpose: Generated governed assignment request workflow
Authority: Generated from canonical process graph JSON; do not hand-edit Mermaid
Changed: 2026-10-11 UTC | RV-M3.3-GOVERNED-INTAKE-ROUTE | Register generated request flow
History: .riverview-backups/manifest.jsonl and Git
-->
# Governed assignment request flow

**Workflow:** Governed assignment create v1  
**Canonical source:** `process_graphs/assignment-intake/governed-request.json`  
**Generation:** `python3 scripts/process_graph.py generate`

```mermaid
flowchart LR
  subgraph g_rv_assignment_intake_governed_request["ASSIGNMENT-INTAKE / governed-request.v1"]
    g_rv_assignment_intake_governed_request_request_9a790d39(["Loopback Steward assignment request"])
    g_rv_assignment_intake_governed_request_bounded_request_bc78466c["Require JSON type, bounded body and allowed request fields"]
    g_rv_assignment_intake_governed_request_grant_decision_d7629d49{"Require active exact assignment.create grant for authority_ref"}
    g_rv_assignment_intake_governed_request_exact_grant_jump_4bbe81c5["Resolve exact action and scope in the Authority registry"]
    g_rv_assignment_intake_governed_request_reject_request_b84c36cb[["Reject malformed, unauthorized or unavailable request without assignment rows"]]
    g_rv_assignment_intake_governed_request_atomic_write_7fbd2ab4["Persist assignment and created event under the grant row lock"]
    g_rv_assignment_intake_governed_request_accepted_5a5d31df(["Return bounded assignment identity and lifecycle state"])
    g_rv_assignment_intake_governed_request_recovery_50ec42c5["Retry an ambiguous response with identical idempotency key"]
  end
  g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9["Registered target<br/>rv:institutional-authority:identity-and-grants"]
  g_rv_assignment_intake_governed_request_request_9a790d39 --> g_rv_assignment_intake_governed_request_bounded_request_bc78466c
  g_rv_assignment_intake_governed_request_bounded_request_bc78466c -->|Valid bounded request| g_rv_assignment_intake_governed_request_grant_decision_d7629d49
  g_rv_assignment_intake_governed_request_bounded_request_bc78466c -->|diagnostic_branch: Invalid or oversized request| g_rv_assignment_intake_governed_request_reject_request_b84c36cb
  g_rv_assignment_intake_governed_request_grant_decision_d7629d49 --> g_rv_assignment_intake_governed_request_exact_grant_jump_4bbe81c5
  g_rv_assignment_intake_governed_request_exact_grant_jump_4bbe81c5 -->|jump| g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9
  g_rv_assignment_intake_governed_request_grant_decision_d7629d49 -->|Exact active grant| g_rv_assignment_intake_governed_request_atomic_write_7fbd2ab4
  g_rv_assignment_intake_governed_request_grant_decision_d7629d49 -->|diagnostic_branch: Denied or authority unavailable| g_rv_assignment_intake_governed_request_reject_request_b84c36cb
  g_rv_assignment_intake_governed_request_atomic_write_7fbd2ab4 -->|Transaction committed| g_rv_assignment_intake_governed_request_accepted_5a5d31df
  g_rv_assignment_intake_governed_request_atomic_write_7fbd2ab4 -->|diagnostic_branch: Client response lost or commit ambiguous| g_rv_assignment_intake_governed_request_recovery_50ec42c5
  g_rv_assignment_intake_governed_request_recovery_50ec42c5 -->|recovery_route: Replay identical idempotent request| g_rv_assignment_intake_governed_request_request_9a790d39
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
