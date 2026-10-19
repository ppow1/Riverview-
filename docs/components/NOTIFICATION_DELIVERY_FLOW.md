<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_DELIVERY_FLOW.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.1
Purpose: Focused notification lifecycle flow generated from canonical JSON
Authority: Documentation only
Changed: 2026-10-11 UTC | RV-M3.2-001 | Register visual attention flow
History: Git and revision/backup manifest
-->
# Notification delivery flow

Canonical source: `process_graphs/notification-delivery/visual-attention.json`.
Generate this diagram with `python3 scripts/process_graph.py generate`; do not
edit the Mermaid source independently.

```mermaid
flowchart LR
  subgraph g_rv_notification_delivery_visual_attention["NOTIFICATION-DELIVERY / visual-attention.v1"]
    g_rv_notification_delivery_visual_attention_cme_event_b6871406(["CME attention is durably observed"])
    g_rv_notification_delivery_visual_attention_filter_8cabce4e{"Institution privacy and event allowlist pass?"}
    g_rv_notification_delivery_visual_attention_skip_private_fff6a63d[["Skip private or unsupported source event"]]
    g_rv_notification_delivery_visual_attention_queue_notice_42899637["Idempotently queue fixed-summary notice"]
    g_rv_notification_delivery_visual_attention_pending_request_06218c28["Create pending review request for awaiting-steward assignment"]
    g_rv_notification_delivery_visual_attention_render_6a316d15["Render bounded notice in visible dashboard view"]
    g_rv_notification_delivery_visual_attention_delivery_receipt_59f94d15["Persist browser rendering receipt"]
    g_rv_notification_delivery_visual_attention_ack_receipt_d87641bb["Persist explicit receipt acknowledgment"]
    g_rv_notification_delivery_visual_attention_no_authority_effect_a01aa4b9(["Decision request stays pending; no authority effect"])
    g_rv_notification_delivery_visual_attention_unavailable_b203f8cf[["Keep queued and show unavailable without success claim"]]
    g_rv_notification_delivery_visual_attention_retry_635d6b92["Re-scan durable CME source after recovery"]
    g_rv_notification_delivery_visual_attention_jump_cme_68ab309e["CME source workflow"]
    g_rv_notification_delivery_visual_attention_jump_dashboard_f63d918e["Dashboard authenticated receipt client"]
    g_rv_notification_delivery_visual_attention_push_status_request_57ca7560(["Authenticated caller requests the bounded notification API page"])
    g_rv_notification_delivery_visual_attention_push_status_project_d3631ea2["Read aggregate provider queue and health without notice content"]
    g_rv_notification_delivery_visual_attention_push_status_classify_e6305a9b{"Classify provider health, freshness, and durable recovery state"}
    g_rv_notification_delivery_visual_attention_push_status_response_039784d9(["Return redacted push status alongside visual notices"])
    g_rv_notification_delivery_visual_attention_push_status_unavailable_6976d5d5[["Report unavailable provider status without claiming delivery"]]
    g_rv_notification_delivery_visual_attention_push_status_retry_d1d87b38["Refresh the read-only status after the source dependency recovers"]
  end
  g_rv_cme_progress_and_recovery_monitor_start_3c5b8496["Registered target<br/>rv:cme:progress-and-recovery"]
  g_rv_steward_dashboard_status_ingest_66a3387a["Registered target<br/>rv:steward-dashboard:status"]
  g_rv_notification_delivery_visual_attention_cme_event_b6871406 --> g_rv_notification_delivery_visual_attention_filter_8cabce4e
  g_rv_notification_delivery_visual_attention_filter_8cabce4e -->|institutional and allowlisted| g_rv_notification_delivery_visual_attention_queue_notice_42899637
  g_rv_notification_delivery_visual_attention_filter_8cabce4e -->|diagnostic_branch: private or unsupported| g_rv_notification_delivery_visual_attention_skip_private_fff6a63d
  g_rv_notification_delivery_visual_attention_queue_notice_42899637 -->|assignment is awaiting_steward| g_rv_notification_delivery_visual_attention_pending_request_06218c28
  g_rv_notification_delivery_visual_attention_pending_request_06218c28 --> g_rv_notification_delivery_visual_attention_render_6a316d15
  g_rv_notification_delivery_visual_attention_queue_notice_42899637 -->|no decision request required| g_rv_notification_delivery_visual_attention_render_6a316d15
  g_rv_notification_delivery_visual_attention_render_6a316d15 -->|visible client render confirmed| g_rv_notification_delivery_visual_attention_delivery_receipt_59f94d15
  g_rv_notification_delivery_visual_attention_delivery_receipt_59f94d15 -->|explicit receipt action| g_rv_notification_delivery_visual_attention_ack_receipt_d87641bb
  g_rv_notification_delivery_visual_attention_ack_receipt_d87641bb --> g_rv_notification_delivery_visual_attention_no_authority_effect_a01aa4b9
  g_rv_notification_delivery_visual_attention_queue_notice_42899637 -->|diagnostic_branch: projection or database unavailable| g_rv_notification_delivery_visual_attention_unavailable_b203f8cf
  g_rv_notification_delivery_visual_attention_unavailable_b203f8cf -->|recovery_route| g_rv_notification_delivery_visual_attention_retry_635d6b92
  g_rv_notification_delivery_visual_attention_retry_635d6b92 --> g_rv_notification_delivery_visual_attention_queue_notice_42899637
  g_rv_notification_delivery_visual_attention_cme_event_b6871406 -->|documentation| g_rv_notification_delivery_visual_attention_jump_cme_68ab309e
  g_rv_notification_delivery_visual_attention_render_6a316d15 -->|documentation| g_rv_notification_delivery_visual_attention_jump_dashboard_f63d918e
  g_rv_notification_delivery_visual_attention_jump_cme_68ab309e -->|jump| g_rv_cme_progress_and_recovery_monitor_start_3c5b8496
  g_rv_notification_delivery_visual_attention_jump_dashboard_f63d918e -->|jump| g_rv_steward_dashboard_status_ingest_66a3387a
  g_rv_notification_delivery_visual_attention_push_status_request_57ca7560 --> g_rv_notification_delivery_visual_attention_push_status_project_d3631ea2
  g_rv_notification_delivery_visual_attention_push_status_project_d3631ea2 --> g_rv_notification_delivery_visual_attention_push_status_classify_e6305a9b
  g_rv_notification_delivery_visual_attention_push_status_classify_e6305a9b -->|health and queue projection available| g_rv_notification_delivery_visual_attention_push_status_response_039784d9
  g_rv_notification_delivery_visual_attention_push_status_classify_e6305a9b -->|diagnostic_branch: incomplete schema or status query unavailable| g_rv_notification_delivery_visual_attention_push_status_unavailable_6976d5d5
  g_rv_notification_delivery_visual_attention_push_status_unavailable_6976d5d5 -->|recovery_route| g_rv_notification_delivery_visual_attention_push_status_retry_d1d87b38
  g_rv_notification_delivery_visual_attention_push_status_retry_d1d87b38 -->|subsequent authenticated read| g_rv_notification_delivery_visual_attention_push_status_request_57ca7560
  g_rv_notification_delivery_visual_attention_push_status_response_039784d9 -->|documentation: API consumer integration seam; dashboard rendering not included| g_rv_notification_delivery_visual_attention_jump_dashboard_f63d918e
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
