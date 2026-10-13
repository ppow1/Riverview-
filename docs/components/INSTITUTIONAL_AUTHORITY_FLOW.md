<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY_FLOW.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.4
Purpose: Map root-local bootstrap, authorization, office state and recovery
Authority: Deny when principal, credential, grant, or source state is uncertain
Changed: 2026-10-11 UTC | RV-M4.1-001 | Remove trailing-space Markdown hardbreaks
Changed: 2026-10-11 UTC | RV-M4.1-DB-BOUNDARY-GRAPH | Regenerate focused authority diagram for the database privilege boundary
Changed: 2026-10-11 UTC | RV-M4.1-LEAST-PRIVILEGE | Render dedicated-schema gate and scoped manager DML path
History: Git and .riverview-backups/manifest.jsonl
-->
# Institutional authority and office continuity flow

**Canonical workflow:** `rv:institutional-authority:identity-and-grants`
**Generated from:** canonical JSON graph. Do not hand-edit the Mermaid block.
**Cookbook:** [diagnosis and recovery](INSTITUTIONAL_AUTHORITY_COOKBOOK.md)

```mermaid
flowchart LR
  subgraph g_rv_institutional_authority_identity_and_grants["INSTITUTIONAL-AUTHORITY / identity-and-grants.v1"]
    g_rv_institutional_authority_identity_and_grants_bootstrap_a48d6fd3(["Trusted root-local first Steward provisioning"])
    g_rv_institutional_authority_identity_and_grants_migration_ledger_bootstrap_b3ae001f["Create authority checksum ledger when absent using idempotent migration 0000"]
    g_rv_institutional_authority_identity_and_grants_migration_ready_c4bb91b6["Reviewed migration is applied to the selected schema"]
    g_rv_institutional_authority_identity_and_grants_principal_create_ee96873b["Create durable principal identity and one-time credential"]
    g_rv_institutional_authority_identity_and_grants_grant_create_462e1d10["Steward issues an exact action and scope grant"]
    g_rv_institutional_authority_identity_and_grants_authorize_fa36becb{"Active identity, credential, exact grant, action and scope all match?"}
    g_rv_institutional_authority_identity_and_grants_authorized_action_492c71b2["Perform only the authorized operation and append audit evidence"]
    g_rv_institutional_authority_identity_and_grants_deny_e8ae7e89[["Reject missing, revoked, expired or mismatched authority"]]
    g_rv_institutional_authority_identity_and_grants_replace_binding_ccca04a9["Replace occupant or implementation under Steward grant"]
    g_rv_institutional_authority_identity_and_grants_office_state_e5a8ca22["Office-keyed state and revision survive occupant/model replacement"]
    g_rv_institutional_authority_identity_and_grants_unavailable_ecf79c11[["Registry/database unavailable; do not authorize"]]
    g_rv_institutional_authority_identity_and_grants_recover_dedfc857["Restore authoritative DB availability and re-check grant before resuming"]
    g_rv_institutional_authority_identity_and_grants_complete_b22cd8fd(["Authorized operation completed with durable state/event evidence"])
    g_rv_institutional_authority_identity_and_grants_db_boundary_preflight_7ebcafd7(["DBA preflights exact authority-table privilege boundary"])
    g_rv_institutional_authority_identity_and_grants_schema_owner_gate_a70328d4{"Runtime and NOINHERIT manager are distinct from schema owner and have no unsafe role memberships?"}
    g_rv_institutional_authority_identity_and_grants_transfer_protected_objects_ce82dd28["Protect the dedicated schema and transfer allowlisted tables; grant manager DML only"]
    g_rv_institutional_authority_identity_and_grants_runtime_denial_verified_c2b31279["Runtime schema/table access denied; manager DML works without DDL or owner inheritance"]
    g_rv_institutional_authority_identity_and_grants_boundary_preflight_failure_44d08c3b[["Mixed schema, unsafe ownership/membership or incomplete role precondition fails closed"]]
    g_rv_institutional_authority_identity_and_grants_dedicated_schema_gate_c3990d8d{"Schema contains only authority tables, migration ledger and append-only trigger?"}
  end
  g_rv_institutional_authority_identity_and_grants_migration_ledger_bootstrap_b3ae001f -->|Migration runner applies checksum-ledger bootstrap before registry migration| g_rv_institutional_authority_identity_and_grants_migration_ready_c4bb91b6
  g_rv_institutional_authority_identity_and_grants_bootstrap_a48d6fd3 -->|prerequisite: Trusted DB bootstrap requires reviewed schema| g_rv_institutional_authority_identity_and_grants_migration_ready_c4bb91b6
  g_rv_institutional_authority_identity_and_grants_migration_ready_c4bb91b6 --> g_rv_institutional_authority_identity_and_grants_principal_create_ee96873b
  g_rv_institutional_authority_identity_and_grants_principal_create_ee96873b --> g_rv_institutional_authority_identity_and_grants_grant_create_462e1d10
  g_rv_institutional_authority_identity_and_grants_grant_create_462e1d10 --> g_rv_institutional_authority_identity_and_grants_authorize_fa36becb
  g_rv_institutional_authority_identity_and_grants_authorize_fa36becb -->|Exact active grant| g_rv_institutional_authority_identity_and_grants_authorized_action_492c71b2
  g_rv_institutional_authority_identity_and_grants_authorize_fa36becb -->|diagnostic_branch: Credential/grant mismatch| g_rv_institutional_authority_identity_and_grants_deny_e8ae7e89
  g_rv_institutional_authority_identity_and_grants_authorized_action_492c71b2 -->|When the action changes office binding| g_rv_institutional_authority_identity_and_grants_replace_binding_ccca04a9
  g_rv_institutional_authority_identity_and_grants_replace_binding_ccca04a9 -->|verification| g_rv_institutional_authority_identity_and_grants_office_state_e5a8ca22
  g_rv_institutional_authority_identity_and_grants_authorized_action_492c71b2 --> g_rv_institutional_authority_identity_and_grants_complete_b22cd8fd
  g_rv_institutional_authority_identity_and_grants_authorize_fa36becb -->|diagnostic_branch: Authoritative query fails| g_rv_institutional_authority_identity_and_grants_unavailable_ecf79c11
  g_rv_institutional_authority_identity_and_grants_unavailable_ecf79c11 -->|recovery_route| g_rv_institutional_authority_identity_and_grants_recover_dedfc857
  g_rv_institutional_authority_identity_and_grants_recover_dedfc857 -->|Re-check instead of reusing old decision| g_rv_institutional_authority_identity_and_grants_authorize_fa36becb
  g_rv_institutional_authority_identity_and_grants_deny_e8ae7e89 -->|escalation: Steward may issue a new narrow grant| g_rv_institutional_authority_identity_and_grants_grant_create_462e1d10
  g_rv_institutional_authority_identity_and_grants_migration_ready_c4bb91b6 -->|prerequisite: Reviewed privilege boundary follows migration readiness| g_rv_institutional_authority_identity_and_grants_db_boundary_preflight_7ebcafd7
  g_rv_institutional_authority_identity_and_grants_db_boundary_preflight_7ebcafd7 --> g_rv_institutional_authority_identity_and_grants_dedicated_schema_gate_c3990d8d
  g_rv_institutional_authority_identity_and_grants_dedicated_schema_gate_c3990d8d -->|Dedicated schema and role checks pass; DBA explicitly applies| g_rv_institutional_authority_identity_and_grants_transfer_protected_objects_ce82dd28
  g_rv_institutional_authority_identity_and_grants_dedicated_schema_gate_c3990d8d -->|diagnostic_branch: Mixed schema or unapproved object rejected| g_rv_institutional_authority_identity_and_grants_boundary_preflight_failure_44d08c3b
  g_rv_institutional_authority_identity_and_grants_transfer_protected_objects_ce82dd28 -->|verification| g_rv_institutional_authority_identity_and_grants_runtime_denial_verified_c2b31279
  g_rv_institutional_authority_identity_and_grants_dedicated_schema_gate_c3990d8d -->|Dedicated schema contains no unrelated objects| g_rv_institutional_authority_identity_and_grants_schema_owner_gate_a70328d4
  g_rv_institutional_authority_identity_and_grants_schema_owner_gate_a70328d4 -->|diagnostic_branch: Runtime/manager role or schema-owner relationship is unsafe| g_rv_institutional_authority_identity_and_grants_boundary_preflight_failure_44d08c3b
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

## Diagnostic mapping

| Step ID | Expected result | Failure signal | First read-only check | Recovery/resume |
|---|---|---|---|---|
| `rv:institutional-authority:identity-and-grants:bootstrap` | One active Steward identity | Steward missing or duplicate bootstrap | Count active Steward principals | Use the protected local bootstrap procedure; never reset the schema |
| `rv:institutional-authority:identity-and-grants:authenticate` | Active credential digest maps to an active principal | `AuthorityDenied` | Check principal and credential status without selecting digest | Rotate through Steward identity management; resume at authorization |
| `rv:institutional-authority:identity-and-grants:authorize` | Exact action and scope grant exists and is valid | denied/expired/revoked grant | Read grant ID, action, scope, and validity window | Steward issues a new least-scope grant; retry the denied operation |
| `rv:institutional-authority:identity-and-grants:replace-binding` | Binding revision increments and office state stays stable | foreign-key or state-revision conflict | Read binding, occupant, implementation, and office-state revisions | Correct the target identity; do not rewrite office state |
| `rv:institutional-authority:identity-and-grants:registry-unavailable` | Service reports unavailable, not authorized | PostgreSQL error or stale connection | Check registry DB health and migration ledger | Restore DB access; re-evaluate exact grant before retry |

Only a bound current occupant/implementation is shown as current. No browser
authorization API exists in this milestone.
