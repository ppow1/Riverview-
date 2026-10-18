# Riverview aggregate process graph

**Document Revision:** 1.0.24
**Generated from:** canonical workflow JSON; do not edit this projection by hand.  
**Source:** `python3 scripts/process_graph.py generate`  

The graph is complete across registered workflows. Use focused component flow documents for detailed reading. Unimplemented roadmap integration points are explicitly labeled planned.

```mermaid
flowchart LR
  g_rv_website_account_auth_account_lifecycle_68396cbf[["WEBSITE-ACCOUNT-AUTH<br/>website.account-auth.v1<br/>rv:website-account-auth:account-lifecycle"]]
  g_rv_assignment_intake_governed_request_226f3420[["ASSIGNMENT-INTAKE<br/>governed-request.v1<br/>rv:assignment-intake:governed-request"]]
  g_rv_assignment_scheduler_independent_claims_88bd80c4[["ASSIGNMENT-SCHEDULER<br/>independent-assignment-claims.v1<br/>rv:assignment-scheduler:independent-claims"]]
  g_rv_cme_progress_and_recovery_402efffa[["CME<br/>progress-and-recovery.v1<br/>rv:cme:progress-and-recovery"]]
  g_rv_comms5_camrui_adapter_00856725[["COMMS5-CAMRUI-ADAPTER<br/>comms5.camrui.compatibility.v1<br/>rv:comms5:camrui-adapter"]]
  g_rv_event_processor_assignment_progression_fa10db2d[["EVENT-PROCESSOR<br/>assignment-progression.v1<br/>rv:event-processor:assignment-progression"]]
  g_rv_grace_institutional_proposal_lifecycle_0d2c6d4e[["INSTITUTIONAL-PROPOSALS<br/>institutional-proposal.v1<br/>rv:grace:institutional-proposal-lifecycle"]]
  g_rv_grace_operational_integration_9989f0be[["RESIDENT-ORCHESTRATION<br/>grace-engineering-objective.v1<br/>rv:grace:operational-integration"]]
  g_rv_institutional_authority_identity_and_grants_05fdf0c5[["INSTITUTIONAL-AUTHORITY<br/>identity-and-grants.v1<br/>rv:institutional-authority:identity-and-grants"]]
  g_rv_institutional_authority_resident_permission_profiles_2f442d86[["RESIDENT-PERMISSION-PROFILES<br/>resident-permission-profiles.v1<br/>rv:institutional-authority:resident-permission-profiles"]]
  g_rv_repository_knowledge_provider_pinned_worker_contracts_0269c370[["REPOSITORY-KNOWLEDGE-PROVIDER<br/>pinned-worker-contracts.v1<br/>rv:repository-knowledge-provider:pinned-worker-contracts"]]
  g_rv_notification_delivery_visual_attention_3f4f84d2[["NOTIFICATION-DELIVERY<br/>visual-attention.v1<br/>rv:notification-delivery:visual-attention"]]
  g_rv_outcome_verifier_independent_result_1d5c0875[["OUTCOME-VERIFIER<br/>deterministic-result-verification.v1<br/>rv:outcome-verifier:independent-result"]]
  g_rv_postgres_ledger_assignment_lifecycle_a9a01b67[["POSTGRES-LEDGER<br/>assignment-lifecycle.v1<br/>rv:postgres-ledger:assignment-lifecycle"]]
  g_rv_postgres_ledger_migration_4c89ef23[["POSTGRES-LEDGER<br/>postgres-migration.v1<br/>rv:postgres-ledger:migration"]]
  g_rv_resident_conversation_browser_chat_533a6831[["RESIDENT-CONVERSATION<br/>resident.conversation.v1<br/>rv:resident-conversation:browser-chat"]]
  g_rv_resident_reasoning_runtime_49854a10[["RESIDENT-REASONING<br/>resident.reasoning.v1<br/>rv:resident-reasoning:runtime"]]
  g_rv_runtime_baseline_commissioning_46ff1ccf[["RUNTIME-BASELINE<br/>runtime-baseline.v1<br/>rv:runtime-baseline:commissioning"]]
  g_rv_steward_dashboard_status_75f7c259[["STEWARD-DASHBOARD<br/>status-projection.v1<br/>rv:steward-dashboard:status"]]
  g_rv_work_registry_observational_registry_21b6727a[["UNIVERSAL-WORK-REGISTRY<br/>observational-registry.v1<br/>rv:work-registry:observational-registry"]]
  g_rv_worker_adapter_deterministic_attempt_15d59b6f[["WORKER-ADAPTER<br/>deterministic-attempt.v1<br/>rv:worker-adapter:deterministic-attempt"]]
  g_rv_worker_adapter_registration_retirement_6a7a90c3[["WORKER-ADAPTER<br/>registration-retirement.v1<br/>rv:worker-adapter:registration-retirement"]]
  g_rv_worker_adapter_supervised_services_d9ea8d99[["WORKER-ADAPTER<br/>supervised-services.v1<br/>rv:worker-adapter:supervised-services"]]
  g_rv_assignment_intake_governed_request_226f3420 -->|jump| g_rv_institutional_authority_identity_and_grants_05fdf0c5
  g_rv_assignment_scheduler_independent_claims_88bd80c4 -->|jump: Open the M1.3 ready-state producer workflow| g_rv_event_processor_assignment_progression_fa10db2d
  g_rv_cme_progress_and_recovery_402efffa -->|jump| g_rv_grace_operational_integration_9989f0be
  g_rv_event_processor_assignment_progression_fa10db2d -->|prerequisite: M1.2 migrated ledger schema; not a runtime call| g_rv_postgres_ledger_migration_4c89ef23
  g_rv_event_processor_assignment_progression_fa10db2d -->|jump| g_rv_runtime_baseline_commissioning_46ff1ccf
  g_rv_grace_operational_integration_9989f0be -->|jump| g_rv_worker_adapter_deterministic_attempt_15d59b6f
  g_rv_grace_operational_integration_9989f0be -->|jump| g_rv_cme_progress_and_recovery_402efffa
  g_rv_grace_operational_integration_9989f0be -->|jump| g_rv_outcome_verifier_independent_result_1d5c0875
  g_rv_institutional_authority_resident_permission_profiles_2f442d86 -->|jump: Revalidate institutional grant authority| g_rv_institutional_authority_identity_and_grants_05fdf0c5
  g_rv_repository_knowledge_provider_pinned_worker_contracts_0269c370 -->|jump| g_rv_worker_adapter_deterministic_attempt_15d59b6f
  g_rv_notification_delivery_visual_attention_3f4f84d2 -->|jump| g_rv_cme_progress_and_recovery_402efffa
  g_rv_notification_delivery_visual_attention_3f4f84d2 -->|jump| g_rv_steward_dashboard_status_75f7c259
  g_rv_outcome_verifier_independent_result_1d5c0875 -->|jump| g_rv_worker_adapter_deterministic_attempt_15d59b6f
  g_rv_postgres_ledger_migration_4c89ef23 -->|jump| g_rv_steward_dashboard_status_75f7c259
  g_rv_resident_conversation_browser_chat_533a6831 -->|jump: Separate explicit objective path; no conversation-triggered call| g_rv_grace_operational_integration_9989f0be
  g_rv_resident_reasoning_runtime_49854a10 -->|jump| g_rv_worker_adapter_deterministic_attempt_15d59b6f
  g_rv_resident_reasoning_runtime_49854a10 -->|jump| g_rv_institutional_authority_identity_and_grants_05fdf0c5
  g_rv_runtime_baseline_commissioning_46ff1ccf -->|jump| g_rv_postgres_ledger_migration_4c89ef23
  g_rv_steward_dashboard_status_75f7c259 -->|jump| g_rv_postgres_ledger_assignment_lifecycle_a9a01b67
  g_rv_steward_dashboard_status_75f7c259 -->|jump| g_rv_cme_progress_and_recovery_402efffa
  g_rv_steward_dashboard_status_75f7c259 -->|jump: Account enrollment or sign-in| g_rv_website_account_auth_account_lifecycle_68396cbf
  g_rv_work_registry_observational_registry_21b6727a -->|jump| g_rv_grace_operational_integration_9989f0be
  g_rv_worker_adapter_deterministic_attempt_15d59b6f -->|jump: Follow current M1.4 lease validation| g_rv_assignment_scheduler_independent_claims_88bd80c4
  g_rv_worker_adapter_deterministic_attempt_15d59b6f -->|prerequisite: M1.4 lease table/token contract; not a runtime call| g_rv_assignment_scheduler_independent_claims_88bd80c4
  g_rv_worker_adapter_deterministic_attempt_15d59b6f -->|jump: independent evidence gate| g_rv_outcome_verifier_independent_result_1d5c0875
  g_rv_worker_adapter_supervised_services_d9ea8d99 -->|jump: independent verifier contract| g_rv_outcome_verifier_independent_result_1d5c0875
  g_rv_worker_adapter_supervised_services_d9ea8d99 -->|jump: durable assignment.created event| g_rv_event_processor_assignment_progression_fa10db2d
```
