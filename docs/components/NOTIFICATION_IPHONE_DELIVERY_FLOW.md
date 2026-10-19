<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_IPHONE_DELIVERY_FLOW.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.6
Purpose: Show the durable provider push-delivery workflow
Authority: Documentation only
Changed: 2026-10-18 UTC | RV-IPHONE-NOTIFICATIONS-001 | Initial canonical flow projection
Changed: 2026-10-18 UTC | RV-NOTIFICATION-GRAPH-EVIDENCE-20261018 | Add selected-provider startup validation, failure, recovery, and evidence paths
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
    g_rv_notification_delivery_iphone_push_provider_send_a734e941["Send bounded fixed-summary authenticated HTTPS or loopback HTTP provider request"]
    g_rv_notification_delivery_iphone_push_accepted_state_3e20fd81{"Provider accepted request; handset delivery remains unverified"}
    g_rv_notification_delivery_iphone_push_bounded_retry_95c8a30f["Schedule bounded retry or record terminal failure"]
    g_rv_notification_delivery_iphone_push_pushover_receipt_553c4667["Poll eligible Pushover emergency receipt at a bounded interval"]
    g_rv_notification_delivery_iphone_push_ack_expire_83898705{"Persist provider-reported acknowledgment or expiry"}
    g_rv_notification_delivery_iphone_push_worker_restart_2f8ef297["Resume expired sending leases after worker restart"]
    g_rv_notification_delivery_iphone_push_service_start_5b68bfaa(["Start worker with PostgreSQL and provider credential namespace available"])
    g_rv_notification_delivery_iphone_push_credential_preflight_1c68cfda["Validate credentials for configured provider routes only"]
    g_rv_notification_delivery_iphone_push_startup_blocked_e0a84c62[["Selected provider credential is missing or invalid; launcher exits before manager construction"]]
    g_rv_notification_delivery_iphone_push_credential_repaired_e350166f["Provision only the selected provider credential, clear systemd start limit, then retry in authorized commissioning"]
    g_rv_notification_delivery_iphone_push_ntfy_endpoint_gate_a272d370["Commissioning gate: loopback ntfy, topic ACL, and LAN HTTPS path verified"]
    g_rv_notification_delivery_iphone_push_iphone_foreground_acceptance_bbedefb8["Operator confirms one info notice appears in the open iOS app"]
    g_rv_notification_delivery_iphone_push_iphone_acceptance_blocked_946f678a[["Phone app cannot connect or display notice; preserve first event and diagnose"]]
    g_rv_notification_delivery_iphone_push_iphone_path_recovered_1dc56c8d["Correct CA, path, WebSocket, or ACL issue and resume read-only checks before retry authorization"]
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
  g_rv_notification_delivery_iphone_push_service_start_5b68bfaa --> g_rv_notification_delivery_iphone_push_credential_preflight_1c68cfda
  g_rv_notification_delivery_iphone_push_credential_preflight_1c68cfda -->|selected credentials available; worker begins reconciliation| g_rv_notification_delivery_iphone_push_attention_source_adb77d27
  g_rv_notification_delivery_iphone_push_credential_preflight_1c68cfda -->|diagnostic_branch: selected credential missing, unreadable, empty, or symlinked| g_rv_notification_delivery_iphone_push_startup_blocked_e0a84c62
  g_rv_notification_delivery_iphone_push_startup_blocked_e0a84c62 -->|recovery_route| g_rv_notification_delivery_iphone_push_credential_repaired_e350166f
  g_rv_notification_delivery_iphone_push_credential_repaired_e350166f -->|recovery_route: operator retries after authorized correction| g_rv_notification_delivery_iphone_push_service_start_5b68bfaa
  g_rv_notification_delivery_iphone_push_ntfy_endpoint_gate_a272d370 -->|prerequisite: only after endpoint, TLS path, and topic ACL checks pass| g_rv_notification_delivery_iphone_push_provider_send_a734e941
  g_rv_notification_delivery_iphone_push_accepted_state_3e20fd81 -->|verification: provider acceptance does not prove phone display| g_rv_notification_delivery_iphone_push_iphone_foreground_acceptance_bbedefb8
  g_rv_notification_delivery_iphone_push_iphone_foreground_acceptance_bbedefb8 -->|diagnostic_branch: connection or display check fails| g_rv_notification_delivery_iphone_push_iphone_acceptance_blocked_946f678a
  g_rv_notification_delivery_iphone_push_iphone_acceptance_blocked_946f678a -->|recovery_route| g_rv_notification_delivery_iphone_push_iphone_path_recovered_1dc56c8d
  g_rv_notification_delivery_iphone_push_iphone_path_recovered_1dc56c8d -->|recovery_route: recheck app path before separately authorized event retry| g_rv_notification_delivery_iphone_push_iphone_foreground_acceptance_bbedefb8
  classDef failure fill:#fee,stroke:#b00,stroke-width:2px
```
