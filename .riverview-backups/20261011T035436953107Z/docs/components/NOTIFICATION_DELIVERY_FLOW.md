<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_DELIVERY_FLOW.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.0
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
  subgraph notification_delivery_visual_attention["NOTIFICATION-DELIVERY / visual-attention.v1"]
    rv_notification_delivery_visual_attention_cme_event_9f00(["CME attention is durably observed"])
    rv_notification_delivery_visual_attention_filter_2ab1{"Institution privacy and allowlist pass?"}
    rv_notification_delivery_visual_attention_skip_private_91ac[["Skip private or unsupported event"]]
    rv_notification_delivery_visual_attention_project_635c["Idempotently queue fixed-summary notice"]
    rv_notification_delivery_visual_attention_pending_8432["Create pending review request when assignment awaits Steward"]
    rv_notification_delivery_visual_attention_render_a302["Render bounded notice in visible dashboard view"]
    rv_notification_delivery_visual_attention_receipt_9220["Persist delivery receipt"]
    rv_notification_delivery_visual_attention_ack_11ef["Persist explicit receipt acknowledgment"]
    rv_notification_delivery_visual_attention_noauthority_b713(["Decision request stays pending; no authority effect"])
    rv_notification_delivery_visual_attention_sourcefailure_91e1[["Keep queued; show unavailable without success claim"]]
    rv_notification_delivery_visual_attention_retry_23d5["Re-scan durable CME source after recovery"]
    rv_notification_delivery_visual_attention_jump_cme_c23a["CME source"]
    rv_notification_delivery_visual_attention_jump_dashboard_2d67["Dashboard receipt client"]
  end
  rv_notification_delivery_visual_attention_cme_event_9f00 --> rv_notification_delivery_visual_attention_filter_2ab1
  rv_notification_delivery_visual_attention_filter_2ab1 -->|pass| rv_notification_delivery_visual_attention_project_635c
  rv_notification_delivery_visual_attention_filter_2ab1 -->|private or unsupported| rv_notification_delivery_visual_attention_skip_private_91ac
  rv_notification_delivery_visual_attention_project_635c --> rv_notification_delivery_visual_attention_pending_8432
  rv_notification_delivery_visual_attention_pending_8432 --> rv_notification_delivery_visual_attention_render_a302
  rv_notification_delivery_visual_attention_render_a302 --> rv_notification_delivery_visual_attention_receipt_9220
  rv_notification_delivery_visual_attention_receipt_9220 --> rv_notification_delivery_visual_attention_ack_11ef
  rv_notification_delivery_visual_attention_ack_11ef --> rv_notification_delivery_visual_attention_noauthority_b713
  rv_notification_delivery_visual_attention_project_635c -.->|database or service unavailable| rv_notification_delivery_visual_attention_sourcefailure_91e1
  rv_notification_delivery_visual_attention_sourcefailure_91e1 --> rv_notification_delivery_visual_attention_retry_23d5
  rv_notification_delivery_visual_attention_retry_23d5 --> rv_notification_delivery_visual_attention_project_635c
```
