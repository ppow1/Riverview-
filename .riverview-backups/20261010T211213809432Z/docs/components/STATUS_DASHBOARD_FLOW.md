<!-- Riverview~ Controlled Document; revision 1.0.0; generated graph projection; STEWARD-DASHBOARD. -->
# Steward dashboard status-projection flow

**Task:** RV-M3.1-001 · **Component:** STEWARD-DASHBOARD  
**Source:** canonical JSON `process_graphs/steward-dashboard/status.json`; Mermaid below is generated.

```mermaid
flowchart LR
  A[reserved]
```

The service authenticates read requests, reads PostgreSQL in a bounded
read-only transaction, filters private records, and exposes paged projections.
Unavailable sources remain visible as unavailable. UI navigation renders from
the current browser cache and does not wait for a provider or database request.
See the [troubleshooting cookbook](STATUS_DASHBOARD_COOKBOOK.md).
