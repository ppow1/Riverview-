<!-- Riverview~ Controlled Document
**Document Revision:** 1.0.7
**Component:** STEWARD-DASHBOARD · generated from canonical JSON
**Task:** RV-M3.1-001
**Authority:** Read-only process view; edit the canonical JSON graph only.
-->
# Steward dashboard status-projection flow

**Task:** RV-M3.1-001 · **Component:** STEWARD-DASHBOARD  
**Source:** canonical JSON `process_graphs/steward-dashboard/status.json`; Mermaid below is generated.

```mermaid
flowchart LR
  subgraph g_rv_steward_dashboard_status["STEWARD-DASHBOARD / status-projection.v1"]
    g_rv_steward_dashboard_status_ingest_66a3387a(["Browser shell and status request"])
    g_rv_steward_dashboard_status_authenticate_64fc5881{"Host, loopback and bearer or active account session valid?"}
    g_rv_steward_dashboard_status_deny_request_776de47b[["Reject unauthorized or mutating request"]]
    g_rv_steward_dashboard_status_read_ledger_6f000d0e["Read bounded PostgreSQL projection"]
    g_rv_steward_dashboard_status_source_health_3cc042e8["Observe source and CME freshness"]
    g_rv_steward_dashboard_status_source_available_1fba9227{"Ledger available and initialized?"}
    g_rv_steward_dashboard_status_source_failure_7a84936b[["Show unavailable or not-initialized state as explicit domain status"]]
    g_rv_steward_dashboard_status_privacy_filter_7710f632["Filter private rows and payloads"]
    g_rv_steward_dashboard_status_render_cached_529d8c25["Render shell and current local view"]
    g_rv_steward_dashboard_status_navigate_9ce45297["Switch tabs without inference or full reconstruction"]
    g_rv_steward_dashboard_status_page_events_3087075e["Fetch bounded event and assignment pages"]
    g_rv_steward_dashboard_status_inspect_detail_fa591a4b["Lazy-load assignment attempts and verifier evidence"]
    g_rv_steward_dashboard_status_export_snapshot_5d8d925e["Export bounded redacted diagnostic snapshot"]
    g_rv_steward_dashboard_status_database_failure_fa21a93b[["Database request failed or exceeded timeout"]]
    g_rv_steward_dashboard_status_reconnect_71d9d56c["Retry read after service or database recovery"]
    g_rv_steward_dashboard_status_jump_ledger_c6cfb39d["Authoritative assignment and event ledger"]
    g_rv_steward_dashboard_status_jump_cme_36e2d25f["CME monitoring, health and attention source"]
    g_rv_steward_dashboard_status_service_start_ebd3f698(["systemd starts the dashboard service"])
    g_rv_steward_dashboard_status_prepare_passfile_2eebe68e["Validate systemd pgpass and copy to private runtime storage"]
    g_rv_steward_dashboard_status_credential_failure_69b3e373[["Reject unsafe or unavailable runtime credential"]]
    g_rv_steward_dashboard_status_list_workers_fe34c745["Page individual worker lease health and active work counts"]
    g_rv_steward_dashboard_status_workers_unavailable_789b26c9[["Report missing worker relations or unreadable health as not initialized or unavailable"]]
    g_rv_steward_dashboard_status_attention_relation_check_427bbb7d{"Is the optional CME attention relation initialized?"}
    g_rv_steward_dashboard_status_attention_uninitialized_00c22bed["Render not_initialized domain state and defer attention polling"]
    g_rv_steward_dashboard_status_read_attention_0d7d5751["Fetch bounded authoritative CME attention rows when the relation exists"]
    g_rv_steward_dashboard_status_render_documentation_55221346["Render allowlisted cookbooks as safe readable HTML"]
    g_rv_steward_dashboard_status_documentation_unavailable_85960402[["Keep missing or unapproved documentation unavailable"]]
    g_rv_steward_dashboard_status_browse_process_graphs_5ccf18cc["Browse workflow index from canonical graph JSON"]
    g_rv_steward_dashboard_status_read_canonical_graph_322bcdca["Read registered focused workflow definition"]
    g_rv_steward_dashboard_status_render_process_graph_d97ae980["Render nodes, typed edges and decisions in read-only SVG"]
    g_rv_steward_dashboard_status_graph_source_unavailable_08315b7d[["Show graph source unavailable without inferred workflow state"]]
    g_rv_steward_dashboard_status_live_position_check_8718556a["Use only an exact persisted process-node identity for live highlighting"]
    g_rv_steward_dashboard_status_live_position_unknown_3fc40b10["Show unknown when the ledger has no process-node mapping"]
    g_rv_steward_dashboard_status_account_session_55b33a2d["Recheck account session, disablement, role and CSRF before protected writes"]
    g_rv_steward_dashboard_status_account_health_6a2c05c9["Project bounded account schema and email readiness without personal data"]
    g_rv_steward_dashboard_status_account_login_2b9c8452["Visitor opens account sign-in and access request"]
    g_rv_steward_dashboard_status_account_management_4dab15f2["Steward opens account approval and management"]
    g_rv_steward_dashboard_status_workflow_session_transport_d4da7bde["Fetch canonical graph index and definition with either the recovery bearer or active same-origin account session"]
  end
  g_rv_postgres_ledger_assignment_lifecycle_intake_c1d0abf1["Registered target<br/>rv:postgres-ledger:assignment-lifecycle"]
  g_rv_cme_progress_and_recovery_monitor_start_3c5b8496["Registered target<br/>rv:cme:progress-and-recovery"]
  g_rv_website_account_auth_account_lifecycle_visitor_request_c85d701b["Registered target<br/>rv:website-account-auth:account-lifecycle"]
  g_rv_website_account_auth_account_lifecycle_steward_management_756368cd["Registered target<br/>rv:website-account-auth:account-lifecycle"]
  g_rv_steward_dashboard_status_ingest_66a3387a --> g_rv_steward_dashboard_status_authenticate_64fc5881
  g_rv_steward_dashboard_status_authenticate_64fc5881 -->|diagnostic_branch: No / invalid host or bearer; write verb| g_rv_steward_dashboard_status_deny_request_776de47b
  g_rv_steward_dashboard_status_authenticate_64fc5881 -->|Authorized GET| g_rv_steward_dashboard_status_read_ledger_6f000d0e
  g_rv_steward_dashboard_status_read_ledger_6f000d0e --> g_rv_steward_dashboard_status_source_health_3cc042e8
  g_rv_steward_dashboard_status_source_health_3cc042e8 --> g_rv_steward_dashboard_status_source_available_1fba9227
  g_rv_steward_dashboard_status_source_available_1fba9227 -->|diagnostic_branch: Unavailable / stale / uninitialized| g_rv_steward_dashboard_status_source_failure_7a84936b
  g_rv_steward_dashboard_status_source_available_1fba9227 -->|Readable rows| g_rv_steward_dashboard_status_privacy_filter_7710f632
  g_rv_steward_dashboard_status_privacy_filter_7710f632 --> g_rv_steward_dashboard_status_render_cached_529d8c25
  g_rv_steward_dashboard_status_render_cached_529d8c25 -->|Local view change| g_rv_steward_dashboard_status_navigate_9ce45297
  g_rv_steward_dashboard_status_render_cached_529d8c25 -->|Bounded refresh| g_rv_steward_dashboard_status_page_events_3087075e
  g_rv_steward_dashboard_status_page_events_3087075e -->|Explicit inspect| g_rv_steward_dashboard_status_inspect_detail_fa591a4b
  g_rv_steward_dashboard_status_render_cached_529d8c25 -->|Explicit snapshot| g_rv_steward_dashboard_status_export_snapshot_5d8d925e
  g_rv_steward_dashboard_status_read_ledger_6f000d0e -->|diagnostic_branch: Connection/query failure| g_rv_steward_dashboard_status_database_failure_fa21a93b
  g_rv_steward_dashboard_status_database_failure_fa21a93b -->|recovery_route| g_rv_steward_dashboard_status_reconnect_71d9d56c
  g_rv_steward_dashboard_status_reconnect_71d9d56c --> g_rv_steward_dashboard_status_read_ledger_6f000d0e
  g_rv_steward_dashboard_status_jump_ledger_c6cfb39d -->|jump| g_rv_postgres_ledger_assignment_lifecycle_intake_c1d0abf1
  g_rv_steward_dashboard_status_jump_cme_36e2d25f -->|jump| g_rv_cme_progress_and_recovery_monitor_start_3c5b8496
  g_rv_steward_dashboard_status_read_ledger_6f000d0e -->|documentation| g_rv_steward_dashboard_status_jump_ledger_c6cfb39d
  g_rv_steward_dashboard_status_source_health_3cc042e8 -->|documentation| g_rv_steward_dashboard_status_jump_cme_36e2d25f
  g_rv_steward_dashboard_status_service_start_ebd3f698 --> g_rv_steward_dashboard_status_prepare_passfile_2eebe68e
  g_rv_steward_dashboard_status_prepare_passfile_2eebe68e -->|diagnostic_branch: Credential validation or private copy failed| g_rv_steward_dashboard_status_credential_failure_69b3e373
  g_rv_steward_dashboard_status_prepare_passfile_2eebe68e -->|prerequisite: Runtime credential available before requests| g_rv_steward_dashboard_status_ingest_66a3387a
  g_rv_steward_dashboard_status_render_cached_529d8c25 -->|Refresh bounded worker page| g_rv_steward_dashboard_status_list_workers_fe34c745
  g_rv_steward_dashboard_status_list_workers_fe34c745 -->|diagnostic_branch: Worker relation missing or source unavailable| g_rv_steward_dashboard_status_workers_unavailable_789b26c9
  g_rv_steward_dashboard_status_render_cached_529d8c25 --> g_rv_steward_dashboard_status_attention_relation_check_427bbb7d
  g_rv_steward_dashboard_status_attention_relation_check_427bbb7d -->|diagnostic_branch: Relation absent; return domain state without repeated request| g_rv_steward_dashboard_status_attention_uninitialized_00c22bed
  g_rv_steward_dashboard_status_attention_relation_check_427bbb7d -->|Relation present| g_rv_steward_dashboard_status_read_attention_0d7d5751
  g_rv_steward_dashboard_status_attention_uninitialized_00c22bed --> g_rv_steward_dashboard_status_list_workers_fe34c745
  g_rv_steward_dashboard_status_read_attention_0d7d5751 --> g_rv_steward_dashboard_status_list_workers_fe34c745
  g_rv_steward_dashboard_status_render_cached_529d8c25 -->|Steward opens workflow viewer| g_rv_steward_dashboard_status_browse_process_graphs_5ccf18cc
  g_rv_steward_dashboard_status_browse_process_graphs_5ccf18cc --> g_rv_steward_dashboard_status_read_canonical_graph_322bcdca
  g_rv_steward_dashboard_status_read_canonical_graph_322bcdca -->|Registered graph definition returned| g_rv_steward_dashboard_status_render_process_graph_d97ae980
  g_rv_steward_dashboard_status_read_canonical_graph_322bcdca -->|diagnostic_branch: Unknown ID or graph source unavailable| g_rv_steward_dashboard_status_graph_source_unavailable_08315b7d
  g_rv_steward_dashboard_status_render_process_graph_d97ae980 --> g_rv_steward_dashboard_status_live_position_check_8718556a
  g_rv_steward_dashboard_status_live_position_check_8718556a -->|diagnostic_branch: No exact durable graph-node identity is stored; render no highlight| g_rv_steward_dashboard_status_live_position_unknown_3fc40b10
  g_rv_steward_dashboard_status_render_cached_529d8c25 -->|Steward opens a diagnostic reference| g_rv_steward_dashboard_status_render_documentation_55221346
  g_rv_steward_dashboard_status_render_documentation_55221346 -->|diagnostic_branch: Missing or unapproved document| g_rv_steward_dashboard_status_documentation_unavailable_85960402
  g_rv_steward_dashboard_status_authenticate_64fc5881 -->|Account cookie presented| g_rv_steward_dashboard_status_account_session_55b33a2d
  g_rv_steward_dashboard_status_account_session_55b33a2d -->|Current session and read role valid| g_rv_steward_dashboard_status_read_ledger_6f000d0e
  g_rv_steward_dashboard_status_account_session_55b33a2d -->|diagnostic_branch: Revoked, disabled, expired or CSRF invalid| g_rv_steward_dashboard_status_deny_request_776de47b
  g_rv_steward_dashboard_status_read_ledger_6f000d0e -->|Include bounded account readiness| g_rv_steward_dashboard_status_account_health_6a2c05c9
  g_rv_steward_dashboard_status_ingest_66a3387a -->|Visitor selects account login| g_rv_steward_dashboard_status_account_login_2b9c8452
  g_rv_steward_dashboard_status_account_login_2b9c8452 -->|jump: Account enrollment or sign-in| g_rv_website_account_auth_account_lifecycle_visitor_request_c85d701b
  g_rv_steward_dashboard_status_render_cached_529d8c25 -->|Steward opens account controls| g_rv_steward_dashboard_status_account_management_4dab15f2
  g_rv_steward_dashboard_status_account_management_4dab15f2 -->|jump: Steward account management| g_rv_website_account_auth_account_lifecycle_steward_management_756368cd
  g_rv_steward_dashboard_status_browse_process_graphs_5ccf18cc -->|Open the workflow viewer| g_rv_steward_dashboard_status_workflow_session_transport_d4da7bde
  g_rv_steward_dashboard_status_workflow_session_transport_d4da7bde -->|Authenticated same-origin graph request| g_rv_steward_dashboard_status_read_canonical_graph_322bcdca
  g_rv_steward_dashboard_status_workflow_session_transport_d4da7bde -->|diagnostic_branch: Expired or absent account session; return authorization denial| g_rv_steward_dashboard_status_deny_request_776de47b
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

The service authenticates read requests, reads PostgreSQL in a bounded
read-only transaction, filters private records, and exposes paged projections.
Unavailable sources remain visible as unavailable. UI navigation renders from
the current browser cache and does not wait for a provider or database request.
See the [troubleshooting cookbook](STATUS_DASHBOARD_COOKBOOK.md).
