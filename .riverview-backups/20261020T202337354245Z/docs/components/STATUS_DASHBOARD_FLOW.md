<!-- Riverview~ Controlled Document
**Document Revision:** 1.0.16
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
    g_rv_steward_dashboard_status_objective_scope_db1133cf{"Steward global view or exact account-owned conversation progress?"}
    g_rv_steward_dashboard_status_read_ledger_6f000d0e["Read bounded PostgreSQL projection"]
    g_rv_steward_dashboard_status_source_health_3cc042e8["Observe source and CME freshness"]
    g_rv_steward_dashboard_status_source_available_1fba9227{"Ledger available and initialized?"}
    g_rv_steward_dashboard_status_source_failure_7a84936b[["Show unavailable or not-initialized state as explicit domain status"]]
    g_rv_steward_dashboard_status_privacy_filter_7710f632["Filter private rows and payloads"]
    g_rv_steward_dashboard_status_render_cached_529d8c25["Render shell and current local view"]
    g_rv_steward_dashboard_status_navigate_9ce45297["Switch tabs without inference or full reconstruction"]
    g_rv_steward_dashboard_status_page_events_3087075e["Fetch bounded event and assignment pages"]
    g_rv_steward_dashboard_status_inspect_detail_fa591a4b["Lazy-load assignment attempts and verifier evidence"]
    g_rv_steward_dashboard_status_export_snapshot_5d8d925e["Generate one bounded privacy-filtered snapshot, archive it, and download the same ZIP"]
    g_rv_steward_dashboard_status_database_failure_fa21a93b[["Database request failed or exceeded timeout"]]
    g_rv_steward_dashboard_status_reconnect_71d9d56c["Retry read after service or database recovery"]
    g_rv_steward_dashboard_status_jump_ledger_c6cfb39d["Authoritative assignment and event ledger"]
    g_rv_steward_dashboard_status_jump_cme_36e2d25f["CME monitoring, health and attention source"]
    g_rv_steward_dashboard_status_service_start_ebd3f698(["systemd starts the dashboard service"])
    g_rv_steward_dashboard_status_prepare_passfile_2eebe68e["Validate systemd pgpass and copy to private runtime storage"]
    g_rv_steward_dashboard_status_credential_failure_69b3e373[["Reject unsafe or unavailable runtime credential"]]
    g_rv_steward_dashboard_status_list_workers_fe34c745["Page worker lease-heartbeat freshness and active leases; process liveness is not reported"]
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
    g_rv_steward_dashboard_status_select_cross_workflow_jump_34868639{"Steward selects a registered cross-workflow destination?"}
    g_rv_steward_dashboard_status_navigate_to_jump_target_3b9bb3fe["Load destination workflow and focus the exact target node"]
    g_rv_steward_dashboard_status_jump_target_unavailable_a040d015[["Show target unavailable and retain the source return path"]]
    g_rv_steward_dashboard_status_return_to_source_jump_c0627ef6["Return to the source workflow and focus its originating jump node"]
    g_rv_steward_dashboard_status_snapshot_raster_budget_1f5b4643{"Will the next PNG preview fit within the 76 MiB raster and 96 MiB package limits?"}
    g_rv_steward_dashboard_status_snapshot_preserve_vector_data_525eaf5f["Omit only over-budget raster previews and retain diagnostic records and vector representations"]
    g_rv_steward_dashboard_status_snapshot_write_manifest_be90d60d["Record component sizes, omitted paths, and truthful capture completeness"]
    g_rv_steward_dashboard_status_snapshot_verify_archive_9ea35dfa["Verify ZIP integrity, manifest hashes, and canonical offline references"]
    g_rv_steward_dashboard_status_snapshot_required_member_bound_6fff171f[["Mandatory non-raster member exceeds the hard uncompressed package limit"]]
    g_rv_steward_dashboard_status_snapshot_diagnose_and_retry_3507664e["Use the reported member path and byte counts to diagnose authorized source growth, then retry"]
    g_rv_steward_dashboard_status_archive_steward_gate_1124d9b0{"Does the request have a CSRF-valid Steward account session and configured private repository credential?"}
    g_rv_steward_dashboard_status_archive_validate_package_c0f9e9d1["Validate stored ZIP integrity, 96 MiB uncompressed bound, manifest hashes, and redaction declaration"]
    g_rv_steward_dashboard_status_archive_private_release_58971cd1["Create a unique draft Release, upload the ZIP asset, publish it, and store lookup metadata"]
    g_rv_steward_dashboard_status_archive_release_receipt_f2a487fd["Return timestamped Release URL, asset name, SHA-256, and size to the dashboard"]
    g_rv_steward_dashboard_status_archive_local_fallback_576863f0["Report safe archive failure and request browser download while retaining a local ZIP retry link"]
    g_rv_steward_dashboard_status_archive_verify_local_digest_029c5e29{"Does the confirmed GitHub receipt SHA-256 and byte count match the generated ZIP Blob?"}
    g_rv_steward_dashboard_status_snapshot_download_same_blob_9a677a5f["Request browser download from the same ZIP Blob and retain a visible Download ZIP retry link"]
    g_rv_steward_dashboard_status_snapshot_archive_link_actions_dd928218["Show the confirmed private Release URL and Copy GitHub Link action"]
    g_rv_steward_dashboard_status_snapshot_download_start_failure_fc3a6df3[["Browser did not start the ZIP download; retain archive URL and local retry link"]]
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
  g_rv_steward_dashboard_status_render_process_graph_d97ae980 -->|Steward selects a jump destination| g_rv_steward_dashboard_status_select_cross_workflow_jump_34868639
  g_rv_steward_dashboard_status_select_cross_workflow_jump_34868639 -->|Registered target selected| g_rv_steward_dashboard_status_navigate_to_jump_target_3b9bb3fe
  g_rv_steward_dashboard_status_navigate_to_jump_target_3b9bb3fe -->|diagnostic_branch: Destination graph or exact node unavailable| g_rv_steward_dashboard_status_jump_target_unavailable_a040d015
  g_rv_steward_dashboard_status_navigate_to_jump_target_3b9bb3fe -->|Return to source requested| g_rv_steward_dashboard_status_return_to_source_jump_c0627ef6
  g_rv_steward_dashboard_status_jump_target_unavailable_a040d015 -->|recovery_route: Use the preserved return control| g_rv_steward_dashboard_status_return_to_source_jump_c0627ef6
  g_rv_steward_dashboard_status_return_to_source_jump_c0627ef6 -->|Source graph and jump node restored| g_rv_steward_dashboard_status_render_process_graph_d97ae980
  g_rv_steward_dashboard_status_select_cross_workflow_jump_34868639 -->|No jump selected; continue viewing this workflow| g_rv_steward_dashboard_status_render_process_graph_d97ae980
  g_rv_steward_dashboard_status_authenticate_64fc5881 -->|Objective projection request| g_rv_steward_dashboard_status_objective_scope_db1133cf
  g_rv_steward_dashboard_status_objective_scope_db1133cf -->|Steward global access or owner and exact read grant verified| g_rv_steward_dashboard_status_read_ledger_6f000d0e
  g_rv_steward_dashboard_status_objective_scope_db1133cf -->|diagnostic_branch: Missing Steward role, account principal, owner match, or read grant| g_rv_steward_dashboard_status_deny_request_776de47b
  g_rv_steward_dashboard_status_export_snapshot_5d8d925e -->|Assemble bounded archive members| g_rv_steward_dashboard_status_snapshot_raster_budget_1f5b4643
  g_rv_steward_dashboard_status_snapshot_raster_budget_1f5b4643 -->|Raster members fit or visual pass is complete| g_rv_steward_dashboard_status_snapshot_write_manifest_be90d60d
  g_rv_steward_dashboard_status_snapshot_preserve_vector_data_525eaf5f -->|Retain HTML, JSON, SVG, and diagnostics; record omitted raster paths| g_rv_steward_dashboard_status_snapshot_write_manifest_be90d60d
  g_rv_steward_dashboard_status_snapshot_write_manifest_be90d60d -->|verification: Finalize self-describing ZIP| g_rv_steward_dashboard_status_snapshot_verify_archive_9ea35dfa
  g_rv_steward_dashboard_status_export_snapshot_5d8d925e -->|diagnostic_branch: A mandatory non-raster member would exceed the hard limit| g_rv_steward_dashboard_status_snapshot_required_member_bound_6fff171f
  g_rv_steward_dashboard_status_snapshot_required_member_bound_6fff171f -->|recovery_route: Inspect reported member and byte counts| g_rv_steward_dashboard_status_snapshot_diagnose_and_retry_3507664e
  g_rv_steward_dashboard_status_snapshot_diagnose_and_retry_3507664e -->|Retry after source correction| g_rv_steward_dashboard_status_export_snapshot_5d8d925e
  g_rv_steward_dashboard_status_snapshot_raster_budget_1f5b4643 -->|diagnostic_branch: Next raster would exceed the 76 MiB raster ceiling or reserved package space| g_rv_steward_dashboard_status_snapshot_preserve_vector_data_525eaf5f
  g_rv_steward_dashboard_status_export_snapshot_5d8d925e -->|ZIP finalized; attempt primary archive| g_rv_steward_dashboard_status_archive_steward_gate_1124d9b0
  g_rv_steward_dashboard_status_archive_steward_gate_1124d9b0 -->|Steward session, CSRF, private repo and systemd credential available| g_rv_steward_dashboard_status_archive_validate_package_c0f9e9d1
  g_rv_steward_dashboard_status_archive_steward_gate_1124d9b0 -->|diagnostic_branch: Missing authority or archive configuration| g_rv_steward_dashboard_status_archive_local_fallback_576863f0
  g_rv_steward_dashboard_status_archive_validate_package_c0f9e9d1 -->|ZIP, manifest and privacy checks pass| g_rv_steward_dashboard_status_archive_private_release_58971cd1
  g_rv_steward_dashboard_status_archive_validate_package_c0f9e9d1 -->|diagnostic_branch: Invalid, oversized or privacy contract failure| g_rv_steward_dashboard_status_archive_local_fallback_576863f0
  g_rv_steward_dashboard_status_archive_private_release_58971cd1 -->|verification: Asset upload and Release publication verified| g_rv_steward_dashboard_status_archive_release_receipt_f2a487fd
  g_rv_steward_dashboard_status_archive_private_release_58971cd1 -->|recovery_route: GitHub upload or publication failed; clean draft/tag best effort| g_rv_steward_dashboard_status_archive_local_fallback_576863f0
  g_rv_steward_dashboard_status_archive_release_receipt_f2a487fd -->|verification: Verify receipt digest and size against the exact uploaded ZIP| g_rv_steward_dashboard_status_archive_verify_local_digest_029c5e29
  g_rv_steward_dashboard_status_archive_verify_local_digest_029c5e29 -->|Confirmed matching receipt| g_rv_steward_dashboard_status_snapshot_download_same_blob_9a677a5f
  g_rv_steward_dashboard_status_archive_verify_local_digest_029c5e29 -->|diagnostic_branch: Missing or mismatched receipt; do not claim archival success| g_rv_steward_dashboard_status_archive_local_fallback_576863f0
  g_rv_steward_dashboard_status_snapshot_download_same_blob_9a677a5f -->|Keep the ZIP retry action and confirmed archive link visible| g_rv_steward_dashboard_status_snapshot_archive_link_actions_dd928218
  g_rv_steward_dashboard_status_archive_local_fallback_576863f0 -->|recovery_route: Archive failed; request local browser download from the original Blob| g_rv_steward_dashboard_status_snapshot_download_same_blob_9a677a5f
  g_rv_steward_dashboard_status_snapshot_download_same_blob_9a677a5f -->|diagnostic_branch: Browser failed to start the download; keep verified archive and local retry available| g_rv_steward_dashboard_status_snapshot_download_start_failure_fc3a6df3
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```

The service authenticates read requests, reads PostgreSQL in a bounded
read-only transaction, filters private records, and exposes paged projections.
Unavailable sources remain visible as unavailable. UI navigation renders from
the current browser cache and does not wait for a provider or database request.
See the [troubleshooting cookbook](STATUS_DASHBOARD_COOKBOOK.md).

The explicit snapshot branch captures each authorized registered page and
control, including long-page visuals split into readable overlapping tiles. It
exports each canonical workflow JSON and viewport-independent visual with the
cross-workflow index. Isolated Firefox verification used the actual dashboard
DOM and scripts with synthetic read-only APIs; production account acceptance
remains unverified. See the dashboard cookbook and PL-NEW-041 evidence.
