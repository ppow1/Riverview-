<!--
Riverview~ Controlled Document
File: docs/components/RESIDENT_REASONING_FLOW.md
Component: RESIDENT-REASONING
File Revision: 1.0.22
Purpose: Generated focused process view for resident reasoning routing
Authority: Graph-generated view; canonical source is JSON
Changed: 2026-10-11 UTC | RV-M4.2-001 | Add graph-generated resident reasoning flow
History: process_graphs/resident-reasoning/runtime.json
-->
# Resident reasoning process flow

**Document Revision:** 1.0.0
**Generated from:** `process_graphs/resident-reasoning/runtime.json`; do not edit Mermaid by hand.

```mermaid
flowchart LR
  subgraph g_rv_resident_reasoning_runtime["RESIDENT-REASONING / resident.reasoning.v1"]
    g_rv_resident_reasoning_runtime_request_7f98a7b3(["Resident reasoning request for one authoritative assignment"])
    g_rv_resident_reasoning_runtime_authorize_state_01b83150["Require exact active office.state.write grant before reading assignment context"]
    g_rv_resident_reasoning_runtime_authority_gate_f71eec68{"Is the exact resident office-state grant active?"}
    g_rv_resident_reasoning_runtime_authority_denied_24a96278[["Return AUTHORITY_DENIED without reading context or invoking provider"]]
    g_rv_resident_reasoning_runtime_load_context_d318d274["Read current office binding and assignment revision; attach the resident-engineering contract reference; reject credential fields and oversized inputs"]
    g_rv_resident_reasoning_runtime_ground_fedaa2c8["Ground the current assignment through knowledge-provider v1"]
    g_rv_resident_reasoning_runtime_reground_480fc411["Reground at the request trigger and retain source revision/hash"]
    g_rv_resident_reasoning_runtime_grounding_gate_64658003{"Are grounding and regrounding both VERIFIED and complete?"}
    g_rv_resident_reasoning_runtime_evidence_wait_5652c712[["Persist non-verified status and return WAITING_FOR_EVIDENCE"]]
    g_rv_resident_reasoning_runtime_knowledge_contract_jump_4dfc6c88["Use the existing assignment knowledge provider contract"]
    g_rv_resident_reasoning_runtime_binding_jump_a19c568e["Read the durable office binding and state revision"]
    g_rv_resident_reasoning_runtime_select_provider_46047639["Choose the provider matching the active office implementation provider_ref"]
    g_rv_resident_reasoning_runtime_route_gate_56e9828c{"Is the primary provider and every configured fallback exact, registered and bounded?"}
    g_rv_resident_reasoning_runtime_route_unavailable_854025a6[["Persist route failure and return UNAVAILABLE without inferred fallback"]]
    g_rv_resident_reasoning_runtime_provider_call_c528110c["Call the bound provider under a shared explicitly bounded deadline of at most 60 seconds and divided token budget"]
    g_rv_resident_reasoning_runtime_response_normalization_327d11e8["Preserve ordered local text blocks; reject tool calls, mixed refusal and text, and unsupported content semantics without granting authority"]
    g_rv_resident_reasoning_runtime_grace_role_context_8af6db52["For office:grace only, add the shared Director of Operations role and authority boundaries to the assignment proposal prompt"]
    g_rv_resident_reasoning_runtime_fallback_gate_7e77ebca{"Did the call time out or fail before returning a plan?"}
    g_rv_resident_reasoning_runtime_fallback_6dc058bf["Try the next explicitly configured provider only; no implicit provider selection"]
    g_rv_resident_reasoning_runtime_proposal_gate_8918a316["Validate typed plan schema, ordered dependencies, and attempt token budget"]
    g_rv_resident_reasoning_runtime_proposal_invalid_182e56de[["Reject malformed or over-budget output; do not persist a proposal"]]
    g_rv_resident_reasoning_runtime_freshness_gate_bef2dc13{"Did authorized office-state revalidation and assignment revision checks remain current?"}
    g_rv_resident_reasoning_runtime_stale_context_20ce95a2[["Discard stale result and require a new authoritative grounding cycle"]]
    g_rv_resident_reasoning_runtime_persist_plan_66486e35["Persist source references, statuses, request metadata and plan via office-state CAS"]
    g_rv_resident_reasoning_runtime_persistence_gate_d9f96702{"Did exact-grant state write succeed against the expected revision?"}
    g_rv_resident_reasoning_runtime_state_conflict_0acad65d[["Return AUTHORITY_DENIED, STATE_CONFLICT or UNAVAILABLE; never report success"]]
    g_rv_resident_reasoning_runtime_proposal_only_27f4e7fa(["Return PROPOSED; proposal is not an approved work order or executed action"])
    g_rv_resident_reasoning_runtime_budget_gate_362686a9{"Can the total budget provide at least one token to every primary/fallback attempt?"}
    g_rv_resident_reasoning_runtime_budget_insufficient_85f3e6b9[["Reject an undersized route before invoking any provider"]]
    g_rv_resident_reasoning_runtime_task_escalation_contract_dec2e604["IMPLEMENTED — explicit task escalation is durably admitted to PostgreSQL before a separate transport attempts delivery; no provider call blocks Grace or CME"]
    g_rv_resident_reasoning_runtime_task_escalation_authority_gate_efa7f87a{"Require exact resident.reasoning.escalate grant for the selected provider before exchange persistence"}
    g_rv_resident_reasoning_runtime_task_escalation_result_cd1b038d["Persist only a versioned advisory whose correlation, context fingerprint, provider identity, claim fence and response schema match"]
    g_rv_resident_reasoning_runtime_task_escalation_failure_96662c07[["Record denied, unavailable, expired, lease, retry, malformed-response and stale-context diagnostics without approving or dispatching work"]]
    g_rv_resident_reasoning_runtime_task_escalation_recovery_d0da7090["Keep the original assignment durable; retry only within the active exact grant and budget, using the provider-observed 512-token output ceiling and one idempotent bounded fallback"]
    g_rv_resident_reasoning_runtime_supervisory_luna_exchange_36f44d81["Submit only authorized CME recovery or performance evaluation to the existing durable Luna exchange with the 512-token output cap"]
    g_rv_resident_reasoning_runtime_supervisory_luna_response_invalid_94551e48[["Persist a sanitized provider or structured-response failure without treating it as a grade, recovery decision, or authorization"]]
    g_rv_resident_reasoning_runtime_supervisory_luna_bounded_retry_0bb6dc16["Apply only the durable output-limit retry allowed for the recorded failure; stop after the compact 512-token fallback or when existing grant and budget checks reject it"]
    g_rv_resident_reasoning_runtime_exchange_outbox_7bebb762["Commit authorized request, context digest, origin and finite deadline before delivery; preserve stable idempotency and correlation IDs"]
    g_rv_resident_reasoning_runtime_exchange_transport_readiness_c71cc220{"OAuth resource-server and Streamable HTTP adapter pass isolated verification; official Tunnel is suitable, but Camrui service, Platform tunnel, OAuth issuer and ChatGPT exchange are not commissioned"}
    g_rv_resident_reasoning_runtime_exchange_transport_blocked_482fc90e[["Preserve awaiting_delivery while production migration, issuer, public route or external-client verification remains incomplete; never fall through to historical Comms5."]]
    g_rv_resident_reasoning_runtime_exchange_delivery_lease_6cddd7c8["Claim a bounded delivery lease and fence; acknowledge or schedule bounded retry without blocking assignment processing"]
    g_rv_resident_reasoning_runtime_exchange_delivered_072adda5["Mark delivery acknowledged; wait for external claim without polling or holding a worker lease"]
    g_rv_resident_reasoning_runtime_exchange_external_claim_bb5aa89e["Authenticate provider identity, claim correlated request with bounded lease and monotonic fence"]
    g_rv_resident_reasoning_runtime_exchange_response_gate_87bf6800{"Does response schema, provider, request/correlation, active claim fence, size and deadline match?"}
    g_rv_resident_reasoning_runtime_exchange_response_persisted_74d2abca["Commit one structured advisory, evidence references, digest and provenance idempotently"]
    g_rv_resident_reasoning_runtime_exchange_grace_consumption_0b864d8c["IMPLEMENTED; ISOLATED POSTGRESQL VERIFIED — Grace revalidates original exact escalation grant, leases the persisted response, and passes typed advice separately from verified context to ResidentReasoner"]
    g_rv_resident_reasoning_runtime_exchange_grace_ack_4657c0a8["IMPLEMENTED; ISOLATED POSTGRESQL VERIFIED — Acknowledge only after proposal and correlated external_advisory_evaluated event commit; restart recovery checks that durable idempotency fence before repeating reasoning"]
    g_rv_resident_reasoning_runtime_exchange_expired_124bcfc4[["Expire request on finite deadline; preserve terminal event, reject late response, and return MCP expired/non-success without response digest"]]
    g_rv_resident_reasoning_runtime_exchange_recovery_4f7ee76d["Recover awaiting-delivery, expired claims or persisted response after restart with same correlation and fenced idempotency"]
    g_rv_resident_reasoning_runtime_exchange_resume_6e7253b1["IMPLEMENTED; ISOLATED POSTGRESQL VERIFIED — Grace reasons over the correlated advisory as unapproved proposal input; existing objective and authorization paths govern any next action"]
    g_rv_resident_reasoning_runtime_exchange_mcp_auth_89ac0223{"Validate OAuth JWT issuer, exact MCP audience, expiry and fixed subject/client mapping; return 401 for invalid tokens and 403 for missing scope"}
    g_rv_resident_reasoning_runtime_exchange_mcp_auth_denied_eac5aa1a[["Reject missing or invalid OAuth tokens with HTTP 401/WWW-Authenticate; reject authenticated insufficient scope with HTTP 403; preserve challenge metadata"]]
    g_rv_resident_reasoning_runtime_exchange_mcp_initialize_602c72d5["Negotiate supported MCP protocol version over sessionless Streamable HTTP JSON-RPC POST"]
    g_rv_resident_reasoning_runtime_exchange_mcp_tools_856213a4["Discover fixed provider-scoped tools; late submit after durable deadline reports expired/non-success without a response digest"]
    g_rv_resident_reasoning_runtime_exchange_mcp_pull_9d19168a["Provider pulls bounded eligible request context; transport delivery lease and acknowledgement are durable"]
    g_rv_resident_reasoning_runtime_exchange_mcp_status_6c99e3ba["Expose provider-owned body-free state, digest, provenance and sanitized diagnostic projection"]
    g_rv_resident_reasoning_runtime_external_escalation_intent_8882f798{"Did the bound model return a typed advisory intent for a configured provider?"}
    g_rv_resident_reasoning_runtime_doorbell_owner_loop_poll_2296c492["Grace owner-session cycle polls the optional fixed-wake adapter before continuing its existing exchange and Engineering work"]
    g_rv_resident_reasoning_runtime_doorbell_runtime_opt_in_dd047c1c{"Is the worker explicitly enabled and bound to an already registered provider and exact existing target?"}
    g_rv_resident_reasoning_runtime_doorbell_disabled_791a9791["Default-off or incomplete configuration leaves the durable exchange untouched and performs no browser action"]
    g_rv_resident_reasoning_runtime_doorbell_durable_claim_1e6b34cd["C3 claims one due request with existing exchange lease, owner identity and monotonic fence; claim contains metadata only"]
    g_rv_resident_reasoning_runtime_doorbell_fixed_wake_30192d7f["C2 invokes only the established browser bridge against its configured conversation target"]
    g_rv_resident_reasoning_runtime_doorbell_durable_receipt_3c9db306["C3 atomically records one fenced receipt and applies existing retry, ambiguity and state-transition rules"]
    g_rv_resident_reasoning_runtime_doorbell_worker_failure_363ede17[["Configuration, exchange, bridge or receipt failure is sanitized and isolated from the remainder of Grace cycle"]]
    g_rv_resident_reasoning_runtime_doorbell_lease_recovery_e2646f65["Keep existing durable request; recover only through lease expiry and exchange retry policy; never infer wake success"]
    g_rv_resident_reasoning_runtime_s3_retry_exception_3005a431["Append one expiring Steward retry grant bound to the exact S3 objective, assignment, stall, and progress sequence"]
    g_rv_resident_reasoning_runtime_s3_retry_admission_19d91f09{"Atomically consume the exact one-use event grant with the existing budget reservation before provider submission"}
  end
  g_rv_worker_adapter_deterministic_attempt_ground_c2193741["Registered target<br/>rv:worker-adapter:deterministic-attempt"]
  g_rv_institutional_authority_identity_and_grants_office_state_e5a8ca22["Registered target<br/>rv:institutional-authority:identity-and-grants"]
  g_rv_resident_reasoning_runtime_request_7f98a7b3 --> g_rv_resident_reasoning_runtime_authorize_state_01b83150
  g_rv_resident_reasoning_runtime_authorize_state_01b83150 --> g_rv_resident_reasoning_runtime_authority_gate_f71eec68
  g_rv_resident_reasoning_runtime_authority_gate_f71eec68 -->|exact grant active| g_rv_resident_reasoning_runtime_load_context_d318d274
  g_rv_resident_reasoning_runtime_authority_gate_f71eec68 -->|diagnostic_branch: missing or revoked grant| g_rv_resident_reasoning_runtime_authority_denied_24a96278
  g_rv_resident_reasoning_runtime_load_context_d318d274 -->|documentation| g_rv_resident_reasoning_runtime_knowledge_contract_jump_4dfc6c88
  g_rv_resident_reasoning_runtime_knowledge_contract_jump_4dfc6c88 -->|jump| g_rv_worker_adapter_deterministic_attempt_ground_c2193741
  g_rv_resident_reasoning_runtime_ground_fedaa2c8 --> g_rv_resident_reasoning_runtime_reground_480fc411
  g_rv_resident_reasoning_runtime_reground_480fc411 --> g_rv_resident_reasoning_runtime_grounding_gate_64658003
  g_rv_resident_reasoning_runtime_grounding_gate_64658003 -->|both VERIFIED and complete| g_rv_resident_reasoning_runtime_select_provider_46047639
  g_rv_resident_reasoning_runtime_grounding_gate_64658003 -->|diagnostic_branch: otherwise| g_rv_resident_reasoning_runtime_evidence_wait_5652c712
  g_rv_resident_reasoning_runtime_select_provider_46047639 -->|documentation| g_rv_resident_reasoning_runtime_binding_jump_a19c568e
  g_rv_resident_reasoning_runtime_binding_jump_a19c568e -->|jump| g_rv_institutional_authority_identity_and_grants_office_state_e5a8ca22
  g_rv_resident_reasoning_runtime_route_gate_56e9828c -->|diagnostic_branch: unknown or invalid route| g_rv_resident_reasoning_runtime_route_unavailable_854025a6
  g_rv_resident_reasoning_runtime_provider_call_c528110c -->|provider response returned for adapter-specific validation| g_rv_resident_reasoning_runtime_response_normalization_327d11e8
  g_rv_resident_reasoning_runtime_response_normalization_327d11e8 -->|response accepted as complete data or returned as a sanitized contract failure| g_rv_resident_reasoning_runtime_fallback_gate_7e77ebca
  g_rv_resident_reasoning_runtime_fallback_gate_7e77ebca -->|provider returned| g_rv_resident_reasoning_runtime_proposal_gate_8918a316
  g_rv_resident_reasoning_runtime_fallback_gate_7e77ebca -->|recovery_route: timeout/failure with configured next provider| g_rv_resident_reasoning_runtime_fallback_6dc058bf
  g_rv_resident_reasoning_runtime_fallback_6dc058bf --> g_rv_resident_reasoning_runtime_provider_call_c528110c
  g_rv_resident_reasoning_runtime_proposal_gate_8918a316 -->|schema and budget pass| g_rv_resident_reasoning_runtime_freshness_gate_bef2dc13
  g_rv_resident_reasoning_runtime_proposal_gate_8918a316 -->|diagnostic_branch: invalid schema or token budget| g_rv_resident_reasoning_runtime_proposal_invalid_182e56de
  g_rv_resident_reasoning_runtime_freshness_gate_bef2dc13 -->|binding and assignment revisions unchanged| g_rv_resident_reasoning_runtime_persist_plan_66486e35
  g_rv_resident_reasoning_runtime_freshness_gate_bef2dc13 -->|diagnostic_branch: revision changed| g_rv_resident_reasoning_runtime_stale_context_20ce95a2
  g_rv_resident_reasoning_runtime_persist_plan_66486e35 --> g_rv_resident_reasoning_runtime_persistence_gate_d9f96702
  g_rv_resident_reasoning_runtime_persistence_gate_d9f96702 -->|diagnostic_branch: denial/conflict/unavailable/size limit| g_rv_resident_reasoning_runtime_state_conflict_0acad65d
  g_rv_resident_reasoning_runtime_route_gate_56e9828c -->|route is exact, registered and bounded| g_rv_resident_reasoning_runtime_budget_gate_362686a9
  g_rv_resident_reasoning_runtime_budget_gate_362686a9 -->|Budget fits; apply office-specific canonical context before provider call| g_rv_resident_reasoning_runtime_grace_role_context_8af6db52
  g_rv_resident_reasoning_runtime_grace_role_context_8af6db52 -->|Role context is bounded and supplies no permissions| g_rv_resident_reasoning_runtime_provider_call_c528110c
  g_rv_resident_reasoning_runtime_budget_gate_362686a9 -->|diagnostic_branch: total token budget is smaller than route length| g_rv_resident_reasoning_runtime_budget_insufficient_85f3e6b9
  g_rv_resident_reasoning_runtime_select_provider_46047639 -->|prerequisite: Optional explicit task-escalation contract; distinct from provider failure fallback| g_rv_resident_reasoning_runtime_task_escalation_contract_dec2e604
  g_rv_resident_reasoning_runtime_task_escalation_contract_dec2e604 -->|prerequisite: Task escalation is a distinct authorized route, not failure fallback| g_rv_resident_reasoning_runtime_task_escalation_authority_gate_efa7f87a
  g_rv_resident_reasoning_runtime_task_escalation_authority_gate_efa7f87a -->|prerequisite: Only exact-grant authorized provider results may be considered| g_rv_resident_reasoning_runtime_task_escalation_result_cd1b038d
  g_rv_resident_reasoning_runtime_task_escalation_contract_dec2e604 -->|diagnostic_branch: Denied, unavailable, saturated, timed out, malformed, or stale context| g_rv_resident_reasoning_runtime_task_escalation_failure_96662c07
  g_rv_resident_reasoning_runtime_task_escalation_failure_96662c07 -->|recovery_route: Preserve assignment and resume after authority/resource/context regrounding| g_rv_resident_reasoning_runtime_task_escalation_recovery_d0da7090
  g_rv_resident_reasoning_runtime_task_escalation_recovery_d0da7090 -->|prerequisite: Re-establish verified facts and current assignment before another proposal| g_rv_resident_reasoning_runtime_ground_fedaa2c8
  g_rv_resident_reasoning_runtime_task_escalation_authority_gate_efa7f87a -->|exact grant and registered target passed| g_rv_resident_reasoning_runtime_exchange_outbox_7bebb762
  g_rv_resident_reasoning_runtime_exchange_outbox_7bebb762 -->|request and objective event committed| g_rv_resident_reasoning_runtime_exchange_transport_readiness_c71cc220
  g_rv_resident_reasoning_runtime_exchange_transport_readiness_c71cc220 -->|authenticated current adapter is registered and externally verified| g_rv_resident_reasoning_runtime_exchange_delivery_lease_6cddd7c8
  g_rv_resident_reasoning_runtime_exchange_transport_readiness_c71cc220 -->|diagnostic_branch: adapter absent, authentication fails, or external route is unverified| g_rv_resident_reasoning_runtime_exchange_transport_blocked_482fc90e
  g_rv_resident_reasoning_runtime_exchange_transport_blocked_482fc90e -->|recovery_route: retain durable request; resume only after current transport preflight passes| g_rv_resident_reasoning_runtime_exchange_recovery_4f7ee76d
  g_rv_resident_reasoning_runtime_exchange_delivery_lease_6cddd7c8 -->|transport acknowledges delivery| g_rv_resident_reasoning_runtime_exchange_delivered_072adda5
  g_rv_resident_reasoning_runtime_exchange_delivery_lease_6cddd7c8 -->|diagnostic_branch: deadline elapsed before delivery| g_rv_resident_reasoning_runtime_exchange_expired_124bcfc4
  g_rv_resident_reasoning_runtime_exchange_delivery_lease_6cddd7c8 -->|recovery_route: delivery process restarts or lease expires| g_rv_resident_reasoning_runtime_exchange_recovery_4f7ee76d
  g_rv_resident_reasoning_runtime_exchange_delivered_072adda5 -->|configured provider claims exact request| g_rv_resident_reasoning_runtime_exchange_external_claim_bb5aa89e
  g_rv_resident_reasoning_runtime_exchange_external_claim_bb5aa89e -->|provider submits structured response| g_rv_resident_reasoning_runtime_exchange_response_gate_87bf6800
  g_rv_resident_reasoning_runtime_exchange_response_gate_87bf6800 -->|verification: response identity and active fence valid| g_rv_resident_reasoning_runtime_exchange_response_persisted_74d2abca
  g_rv_resident_reasoning_runtime_exchange_response_gate_87bf6800 -->|diagnostic_branch: invalid schema, identity, authority, fence or deadline| g_rv_resident_reasoning_runtime_task_escalation_failure_96662c07
  g_rv_resident_reasoning_runtime_exchange_response_persisted_74d2abca -->|persisted response is available to Grace| g_rv_resident_reasoning_runtime_exchange_grace_consumption_0b864d8c
  g_rv_resident_reasoning_runtime_exchange_response_persisted_74d2abca -->|recovery_route: process restart before Grace consumption| g_rv_resident_reasoning_runtime_exchange_recovery_4f7ee76d
  g_rv_resident_reasoning_runtime_exchange_grace_consumption_0b864d8c -->|original exact grant revalidated; advisory remains non-authorizing| g_rv_resident_reasoning_runtime_exchange_resume_6e7253b1
  g_rv_resident_reasoning_runtime_exchange_resume_6e7253b1 -->|verification: existing reasoning workflow durably records its continuation result| g_rv_resident_reasoning_runtime_exchange_grace_ack_4657c0a8
  g_rv_resident_reasoning_runtime_exchange_grace_consumption_0b864d8c -->|recovery_route: consumer lease expires before durable acknowledgment| g_rv_resident_reasoning_runtime_exchange_recovery_4f7ee76d
  g_rv_resident_reasoning_runtime_exchange_transport_readiness_c71cc220 -->|prerequisite: loopback MCP adapter is configured| g_rv_resident_reasoning_runtime_exchange_mcp_auth_89ac0223
  g_rv_resident_reasoning_runtime_exchange_mcp_auth_89ac0223 -->|prerequisite: valid bearer maps to registered provider principal and scope| g_rv_resident_reasoning_runtime_exchange_mcp_initialize_602c72d5
  g_rv_resident_reasoning_runtime_exchange_mcp_auth_89ac0223 -->|diagnostic_branch: credential missing, expired, unmapped or scope denied| g_rv_resident_reasoning_runtime_exchange_mcp_auth_denied_eac5aa1a
  g_rv_resident_reasoning_runtime_exchange_mcp_auth_denied_eac5aa1a -->|recovery_route: preserve exchange state; retry only after credential correction| g_rv_resident_reasoning_runtime_exchange_transport_blocked_482fc90e
  g_rv_resident_reasoning_runtime_exchange_mcp_initialize_602c72d5 -->|MCP protocol initialization succeeds| g_rv_resident_reasoning_runtime_exchange_mcp_tools_856213a4
  g_rv_resident_reasoning_runtime_exchange_mcp_tools_856213a4 -->|client discovers and calls provider request retrieval| g_rv_resident_reasoning_runtime_exchange_mcp_pull_9d19168a
  g_rv_resident_reasoning_runtime_exchange_mcp_pull_9d19168a -->|selected provider receives bounded request through existing delivery lease| g_rv_resident_reasoning_runtime_exchange_delivery_lease_6cddd7c8
  g_rv_resident_reasoning_runtime_exchange_external_claim_bb5aa89e -->|MCP submit tool supplies structured advisory and claim fence| g_rv_resident_reasoning_runtime_exchange_response_gate_87bf6800
  g_rv_resident_reasoning_runtime_exchange_response_persisted_74d2abca -->|provider may inspect body-free persisted outcome| g_rv_resident_reasoning_runtime_exchange_mcp_status_6c99e3ba
  g_rv_resident_reasoning_runtime_exchange_mcp_status_6c99e3ba -->|status is observational; Grace consumes only through its existing authorized workflow| g_rv_resident_reasoning_runtime_exchange_grace_consumption_0b864d8c
  g_rv_resident_reasoning_runtime_persistence_gate_d9f96702 -->|durable typed plan returned| g_rv_resident_reasoning_runtime_external_escalation_intent_8882f798
  g_rv_resident_reasoning_runtime_external_escalation_intent_8882f798 -->|intent targets an explicitly configured provider| g_rv_resident_reasoning_runtime_task_escalation_contract_dec2e604
  g_rv_resident_reasoning_runtime_external_escalation_intent_8882f798 -->|no escalation intent; proposal remains unapproved| g_rv_resident_reasoning_runtime_proposal_only_27f4e7fa
  g_rv_resident_reasoning_runtime_exchange_outbox_7bebb762 -->|independent bounded owner-loop polling; no provider call in the exchange| g_rv_resident_reasoning_runtime_doorbell_owner_loop_poll_2296c492
  g_rv_resident_reasoning_runtime_doorbell_owner_loop_poll_2296c492 -->|the configured owner cycle invokes the optional adapter hook| g_rv_resident_reasoning_runtime_doorbell_runtime_opt_in_dd047c1c
  g_rv_resident_reasoning_runtime_doorbell_runtime_opt_in_dd047c1c -->|diagnostic_branch: disabled by default or required configuration is not present| g_rv_resident_reasoning_runtime_doorbell_disabled_791a9791
  g_rv_resident_reasoning_runtime_doorbell_runtime_opt_in_dd047c1c -->|explicit opt-in with provider already registered and target config valid| g_rv_resident_reasoning_runtime_doorbell_durable_claim_1e6b34cd
  g_rv_resident_reasoning_runtime_doorbell_durable_claim_1e6b34cd -->|one due metadata-only claim is returned with enough lease remaining| g_rv_resident_reasoning_runtime_doorbell_fixed_wake_30192d7f
  g_rv_resident_reasoning_runtime_doorbell_fixed_wake_30192d7f -->|verification: the fixed bridge reports bounded success, known pre-send failure or ambiguity| g_rv_resident_reasoning_runtime_doorbell_durable_receipt_3c9db306
  g_rv_resident_reasoning_runtime_doorbell_owner_loop_poll_2296c492 -->|diagnostic_branch: optional adapter reports a bounded failure without stopping the owner cycle| g_rv_resident_reasoning_runtime_doorbell_worker_failure_363ede17
  g_rv_resident_reasoning_runtime_doorbell_runtime_opt_in_dd047c1c -->|diagnostic_branch: invalid opt-in configuration fails startup closed| g_rv_resident_reasoning_runtime_doorbell_worker_failure_363ede17
  g_rv_resident_reasoning_runtime_doorbell_durable_claim_1e6b34cd -->|recovery_route: claim or receipt is unavailable; existing fenced lease remains authoritative| g_rv_resident_reasoning_runtime_doorbell_lease_recovery_e2646f65
  g_rv_resident_reasoning_runtime_doorbell_fixed_wake_30192d7f -->|recovery_route: bridge result is uncertain; do not issue an automatic second wake| g_rv_resident_reasoning_runtime_doorbell_lease_recovery_e2646f65
  g_rv_resident_reasoning_runtime_doorbell_durable_receipt_3c9db306 -->|recovery_route: receipt persistence fails; request can recover only through lease expiry| g_rv_resident_reasoning_runtime_doorbell_lease_recovery_e2646f65
  g_rv_resident_reasoning_runtime_doorbell_lease_recovery_e2646f65 -->|recovery_route: subsequent cycle observes only work eligible under durable exchange policy| g_rv_resident_reasoning_runtime_doorbell_owner_loop_poll_2296c492
  g_rv_resident_reasoning_runtime_exchange_response_gate_87bf6800 -->|diagnostic_branch: deadline elapsed before response commit; MCP returns expired/non-success without digest| g_rv_resident_reasoning_runtime_exchange_expired_124bcfc4
  g_rv_resident_reasoning_runtime_supervisory_luna_exchange_36f44d81 -->|Authorized supervisory request enters the existing durable exchange| g_rv_resident_reasoning_runtime_exchange_outbox_7bebb762
  g_rv_resident_reasoning_runtime_supervisory_luna_exchange_36f44d81 -->|diagnostic_branch: Provider submission fails or bounded structured response is invalid| g_rv_resident_reasoning_runtime_supervisory_luna_response_invalid_94551e48
  g_rv_resident_reasoning_runtime_supervisory_luna_response_invalid_94551e48 -->|recovery_route: One idempotent 512-token fallback may run inside existing authority and budget| g_rv_resident_reasoning_runtime_supervisory_luna_bounded_retry_0bb6dc16
  g_rv_resident_reasoning_runtime_supervisory_luna_bounded_retry_0bb6dc16 -->|Persist the bounded retry in the same exchange| g_rv_resident_reasoning_runtime_exchange_outbox_7bebb762
  g_rv_resident_reasoning_runtime_supervisory_luna_bounded_retry_0bb6dc16 -->|recovery_route: The bounded request was denied at admission and a matching Steward-authorized exception is recorded for this stall only| g_rv_resident_reasoning_runtime_s3_retry_exception_3005a431
  g_rv_resident_reasoning_runtime_s3_retry_exception_3005a431 -->|prerequisite: Exact objective, root and step assignments, stall event, progress, revision, expiry, and one-use limit match| g_rv_resident_reasoning_runtime_s3_retry_admission_19d91f09
  g_rv_resident_reasoning_runtime_s3_retry_admission_19d91f09 -->|One reservation and exception consumption commit atomically before the existing durable Luna exchange| g_rv_resident_reasoning_runtime_exchange_outbox_7bebb762
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
