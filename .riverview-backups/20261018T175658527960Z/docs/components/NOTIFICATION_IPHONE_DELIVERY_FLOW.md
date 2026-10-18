<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_IPHONE_DELIVERY_FLOW.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.1
Purpose: Show the durable provider push-delivery workflow
Authority: Documentation only
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial canonical flow projection
History: Git and .riverview-backups/manifest.jsonl
-->
# iPhone notification delivery flow

Canonical source: `process_graphs/notification-delivery/iphone-push.json`.
Generate this diagram with `python3 scripts/process_graph.py generate`; do not
edit the Mermaid source independently.

```mermaid
flowchart LR
  subgraph g_rv_notification_delivery_iphone_push["NOTIFICATION-DELIVERY / iphone-push.v1"]
    g_rv_notification_delivery_iphone_push_attention_source_adb77d27(["Existing privacy-filtered CME notice is available"])
    g_rv_notification_delivery_iphone_push_severity_route_6c2f49c9{"Map source event to configured severity and provider route"}
    g_rv_notification_delivery_iphone_push_durable_outbox_1925b92d["Insert one deduplicated provider row in PostgreSQL outbox"]
    g_rv_notification_delivery_iphone_push_lease_claim_55ef6166["Claim due row under a bounded lease and increment attempt count"]
    g_rv_notification_delivery_iphone_push_secret_load_53b23ff9["Load provider credential from protected systemd credential directory"]
    g_rv_notification_delivery_iphone_push_provider_send_a734e941["Send bounded fixed-summary HTTPS provider request"]
    g_rv_notification_delivery_iphone_push_accepted_state_3e20fd81{"Provider accepted request; handset delivery remains unverified"}
    g_rv_notification_delivery_iphone_push_bounded_retry_95c8a30f["Schedule bounded retry or record terminal failure"]
    g_rv_notification_delivery_iphone_push_pushover_receipt_553c4667["Poll eligible Pushover emergency receipt at a bounded interval"]
    g_rv_notification_delivery_iphone_push_ack_expire_83898705{"Persist provider-reported acknowledgment or expiry"}
    g_rv_notification_delivery_iphone_push_worker_restart_2f8ef297["Resume expired sending leases after worker restart"]
  end
  g_rv_notification_delivery_iphone_push_attention_source_adb77d27 --> g_rv_notification_delivery_iphone_push_severity_route_6c2f49c9
  g_rv_notification_delivery_iphone_push_severity_route_6c2f49c9 -->|route configured| g_rv_notification_delivery_iphone_push_durable_outbox_1925b92d
  g_rv_notification_delivery_iphone_push_durable_outbox_1925b92d --> g_rv_notification_delivery_iphone_push_lease_claim_55ef6166
  g_rv_notification_delivery_iphone_push_lease_claim_55ef6166 --> g_rv_notification_delivery_iphone_push_secret_load_53b23ff9
  g_rv_notification_delivery_iphone_push_secret_load_53b23ff9 -->|credential available| g_rv_notification_delivery_iphone_push_provider_send_a734e941
  g_rv_notification_delivery_iphone_push_secret_load_53b23ff9 -->|diagnostic_branch: credential/configuration unavailable| g_rv_notification_delivery_iphone_push_bounded_retry_95c8a30f
  g_rv_notification_delivery_iphone_push_provider_send_a734e941 -->|2xx/API accepted| g_rv_notification_delivery_iphone_push_accepted_state_3e20fd81
  g_rv_notification_delivery_iphone_push_provider_send_a734e941 -->|diagnostic_branch: network or provider failure| g_rv_notification_delivery_iphone_push_bounded_retry_95c8a30f
  g_rv_notification_delivery_iphone_push_bounded_retry_95c8a30f -->|recovery_route: retry becomes due| g_rv_notification_delivery_iphone_push_lease_claim_55ef6166
  g_rv_notification_delivery_iphone_push_accepted_state_3e20fd81 -->|Pushover critical receipt exists| g_rv_notification_delivery_iphone_push_pushover_receipt_553c4667
  g_rv_notification_delivery_iphone_push_pushover_receipt_553c4667 --> g_rv_notification_delivery_iphone_push_ack_expire_83898705
  g_rv_notification_delivery_iphone_push_accepted_state_3e20fd81 -->|recovery_route: process interruption| g_rv_notification_delivery_iphone_push_worker_restart_2f8ef297
  g_rv_notification_delivery_iphone_push_worker_restart_2f8ef297 -->|lease expires| g_rv_notification_delivery_iphone_push_lease_claim_55ef6166
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
