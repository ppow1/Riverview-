<!--
Riverview~ Controlled Document
File: docs/components/INSTITUTIONAL_AUTHORITY_FLOW.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.8
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
    g_rv_institutional_authority_identity_and_grants_bootstrap_token_persist_48d47baa["Create or reuse and fsync the root-only bearer file before DB commit"]
    g_rv_institutional_authority_identity_and_grants_bootstrap_record_commit_cbb111d7["Persist the initial Steward digest, exact grants and audit event transactionally"]
    g_rv_institutional_authority_identity_and_grants_bootstrap_token_verify_6fd32a89["Verify persisted bearer authorizes exact bootstrap grant and only its digest is stored"]
    g_rv_institutional_authority_identity_and_grants_bootstrap_error_51c2980d[["Bootstrap outcome unavailable or secret persistence failed; retain protected token and fail closed"]]
    g_rv_institutional_authority_identity_and_grants_bootstrap_retry_6882465e["Resume with the same protected token after interruption"]
    g_rv_institutional_authority_identity_and_grants_runtime_worker_registration_33ad4cb1(["Worker registration or a scoped worker action begins with a grant-bound credential"])
    g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9{"Protected exact-grant function validates active credential, action, and exact scope"}
    g_rv_institutional_authority_identity_and_grants_runtime_grant_allowed_24a31d10["Exact active grant allows this transaction-bound worker operation"]
    g_rv_institutional_authority_identity_and_grants_runtime_grant_denied_1e6c02a9[["Missing, revoked, expired, wrong-action, or wrong-scope credential is denied"]]
    g_rv_institutional_authority_identity_and_grants_runtime_grant_unavailable_15bb3150[["Protected grant function or PostgreSQL is unavailable; worker action fails closed"]]
    g_rv_institutional_authority_identity_and_grants_grace_provision_request_421d027a(["Root-local request to bind the fixed Grace resident identity"])
    g_rv_institutional_authority_identity_and_grants_grace_provision_preflight_bf691201["Validate root credentials, local model and fixed authority schema preconditions"]
    g_rv_institutional_authority_identity_and_grants_grace_provision_registry_e56aa743["Idempotently create the Grace office, resident, occupant, model binding and exact office-state grant"]
    g_rv_institutional_authority_identity_and_grants_grace_provision_verify_150fc962["Independently confirm the bound identity and exact office-state grant"]
    g_rv_institutional_authority_identity_and_grants_grace_provision_failure_df8e07b7[["Fail closed on unavailable credentials, conflicting identity, or unsafe protected path"]]
    g_rv_institutional_authority_identity_and_grants_grace_provision_recovery_5e1d3180["Revoke orphan resident bearer records and retry safely after interrupted credential delivery"]
    g_rv_institutional_authority_identity_and_grants_grace_identity_bound_a2ac060a(["Identity-only bootstrap verified; resident runtime and Grace objective execution remain separate work"])
    g_rv_institutional_authority_identity_and_grants_model_rebind_request_030ff994(["Steward requests an implementation-only rebind with current binding revision"])
    g_rv_institutional_authority_identity_and_grants_model_rebind_authority_000bbe96["Require exact office.manage institutional authority"]
    g_rv_institutional_authority_identity_and_grants_model_rebind_cas_76d5147d{"Does current binding revision equal the expected revision?"}
    g_rv_institutional_authority_identity_and_grants_model_rebind_update_daf5f31d["Update only implementation; preserve office and occupant; append audit event"]
    g_rv_institutional_authority_identity_and_grants_model_rebind_stale_a3a922d9[["Reject stale expected revision without mutating the office binding"]]
    g_rv_institutional_authority_identity_and_grants_model_rebind_rollback_be4d1cb4["Restore predecessor implementation through the same CAS API and current revision"]
    g_rv_institutional_authority_identity_and_grants_model_rebind_verify_5bacda7d["Verify occupant identity, implementation, incremented revision and audit evidence"]
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
  g_rv_institutional_authority_identity_and_grants_bootstrap_a48d6fd3 -->|Root-only commissioning helper| g_rv_institutional_authority_identity_and_grants_bootstrap_token_persist_48d47baa
  g_rv_institutional_authority_identity_and_grants_migration_ready_c4bb91b6 -->|prerequisite: Dedicated migration and privilege boundary verified| g_rv_institutional_authority_identity_and_grants_bootstrap_token_persist_48d47baa
  g_rv_institutional_authority_identity_and_grants_bootstrap_token_persist_48d47baa -->|File fsync precedes transaction| g_rv_institutional_authority_identity_and_grants_bootstrap_record_commit_cbb111d7
  g_rv_institutional_authority_identity_and_grants_bootstrap_token_persist_48d47baa -->|diagnostic_branch: Unsafe path or persistence failure| g_rv_institutional_authority_identity_and_grants_bootstrap_error_51c2980d
  g_rv_institutional_authority_identity_and_grants_bootstrap_record_commit_cbb111d7 -->|verification: Database commit succeeds| g_rv_institutional_authority_identity_and_grants_bootstrap_token_verify_6fd32a89
  g_rv_institutional_authority_identity_and_grants_bootstrap_record_commit_cbb111d7 -->|diagnostic_branch: Transaction unavailable or ambiguous| g_rv_institutional_authority_identity_and_grants_bootstrap_error_51c2980d
  g_rv_institutional_authority_identity_and_grants_bootstrap_error_51c2980d -->|recovery_route: Preserve token file; investigate DB result| g_rv_institutional_authority_identity_and_grants_bootstrap_retry_6882465e
  g_rv_institutional_authority_identity_and_grants_bootstrap_retry_6882465e -->|Reuse existing token; never rotate on uncertain commit| g_rv_institutional_authority_identity_and_grants_bootstrap_token_persist_48d47baa
  g_rv_institutional_authority_identity_and_grants_bootstrap_token_verify_6fd32a89 -->|Initial authority verified| g_rv_institutional_authority_identity_and_grants_complete_b22cd8fd
  g_rv_institutional_authority_identity_and_grants_runtime_worker_registration_33ad4cb1 -->|Check worker.register or the capability-mapped action and exact scope| g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9
  g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9 -->|Active credential and exact grant match| g_rv_institutional_authority_identity_and_grants_runtime_grant_allowed_24a31d10
  g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9 -->|diagnostic_branch: No exact active grant| g_rv_institutional_authority_identity_and_grants_runtime_grant_denied_1e6c02a9
  g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9 -->|diagnostic_branch: Function or database unavailable| g_rv_institutional_authority_identity_and_grants_runtime_grant_unavailable_15bb3150
  g_rv_institutional_authority_identity_and_grants_runtime_grant_allowed_24a31d10 --> g_rv_institutional_authority_identity_and_grants_authorized_action_492c71b2
  g_rv_institutional_authority_identity_and_grants_runtime_grant_denied_1e6c02a9 --> g_rv_institutional_authority_identity_and_grants_deny_e8ae7e89
  g_rv_institutional_authority_identity_and_grants_runtime_grant_unavailable_15bb3150 --> g_rv_institutional_authority_identity_and_grants_unavailable_ecf79c11
  g_rv_institutional_authority_identity_and_grants_recover_dedfc857 -->|recovery_route: Revalidate the exact grant in the resumed operation| g_rv_institutional_authority_identity_and_grants_runtime_grant_check_6433bcd9
  g_rv_institutional_authority_identity_and_grants_grace_provision_request_421d027a --> g_rv_institutional_authority_identity_and_grants_grace_provision_preflight_bf691201
  g_rv_institutional_authority_identity_and_grants_grace_provision_preflight_bf691201 -->|All root-owned inputs and exact schema preconditions pass| g_rv_institutional_authority_identity_and_grants_grace_provision_registry_e56aa743
  g_rv_institutional_authority_identity_and_grants_grace_provision_preflight_bf691201 -->|diagnostic_branch: Credential, model, database or path precondition fails| g_rv_institutional_authority_identity_and_grants_grace_provision_failure_df8e07b7
  g_rv_institutional_authority_identity_and_grants_grace_provision_registry_e56aa743 -->|verification| g_rv_institutional_authority_identity_and_grants_grace_provision_verify_150fc962
  g_rv_institutional_authority_identity_and_grants_grace_provision_registry_e56aa743 -->|diagnostic_branch: Registry mutation conflicts or becomes unavailable| g_rv_institutional_authority_identity_and_grants_grace_provision_failure_df8e07b7
  g_rv_institutional_authority_identity_and_grants_grace_provision_failure_df8e07b7 -->|recovery_route: Reconcile durable registry state and protected credential file| g_rv_institutional_authority_identity_and_grants_grace_provision_recovery_5e1d3180
  g_rv_institutional_authority_identity_and_grants_grace_provision_recovery_5e1d3180 -->|Retry fixed identities idempotently; orphan bearer is revoked before replacement| g_rv_institutional_authority_identity_and_grants_grace_provision_registry_e56aa743
  g_rv_institutional_authority_identity_and_grants_grace_provision_verify_150fc962 -->|One exact office.state.write grant and matching binding verified| g_rv_institutional_authority_identity_and_grants_grace_identity_bound_a2ac060a
  g_rv_institutional_authority_identity_and_grants_model_rebind_request_030ff994 --> g_rv_institutional_authority_identity_and_grants_model_rebind_authority_000bbe96
  g_rv_institutional_authority_identity_and_grants_model_rebind_authority_000bbe96 -->|Exact office.manage grant verified| g_rv_institutional_authority_identity_and_grants_model_rebind_cas_76d5147d
  g_rv_institutional_authority_identity_and_grants_model_rebind_cas_76d5147d -->|Expected revision matches| g_rv_institutional_authority_identity_and_grants_model_rebind_update_daf5f31d
  g_rv_institutional_authority_identity_and_grants_model_rebind_cas_76d5147d -->|diagnostic_branch: Expected revision is stale| g_rv_institutional_authority_identity_and_grants_model_rebind_stale_a3a922d9
  g_rv_institutional_authority_identity_and_grants_model_rebind_update_daf5f31d -->|verification| g_rv_institutional_authority_identity_and_grants_model_rebind_verify_5bacda7d
  g_rv_institutional_authority_identity_and_grants_model_rebind_verify_5bacda7d -->|recovery_route: Rollback requested; use predecessor implementation and current revision| g_rv_institutional_authority_identity_and_grants_model_rebind_rollback_be4d1cb4
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
