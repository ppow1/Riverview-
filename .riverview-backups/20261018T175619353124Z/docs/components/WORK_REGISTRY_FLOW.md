# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/WORK_REGISTRY_FLOW.md
# Component: UNIVERSAL-WORK-REGISTRY
# File Revision: 1.0.0
# Purpose: Show observed registry and explicit v4 receipt paths, failures, and recovery
# Execution Model: Documentation projection generated from the canonical registry graph
# Authority: Observational only; receipt events do not authorize execution
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-DOD-REMEDIATION-001 | Add focused registry and receipt bridge flow.
# History: New document; generated Mermaid is synchronized from process_graphs/work-registry/observational-registry.json
# =============================================================================
# Universal Work Registry workflow

This diagram describes the implemented request-driven registry, browser read projection, and explicitly invoked v4 receipt bridge. It does not show automatic GitHub polling, dispatch, or existing-session wake because those capabilities are not implemented.

```mermaid
flowchart LR
  placeholder[Generated from the canonical work registry graph]
```

## Stable step mapping

| Stable node ID | Observed operation |
| --- | --- |
| `rv:work-registry:observational-registry:register-worker` | Persist a worker identity and capability metadata. |
| `rv:work-registry:observational-registry:start-session` | Persist a session separately; heartbeat is not model reasoning. |
| `rv:work-registry:observational-registry:record-work` | Create/update a work order or inference-job observation. |
| `rv:work-registry:observational-registry:acknowledge-assignment` | Startup binds an explicitly supplied existing order to a session. |
| `rv:work-registry:observational-registry:explicit-receipt-event` | Explicit caller reports acknowledged, in-progress, blocked, or completed. |
| `rv:work-registry:observational-registry:receipt-state-conflict` | Mapping, ownership, validation, or expected-state check rejects the event. |
| `rv:work-registry:observational-registry:receipt-mirror-recovery` | After registry persistence but failed v4 mirror, diagnose and replay the same event. |
| `rv:work-registry:observational-registry:read-only-diagnostic` | Read a filtered registry snapshot and current v4 status without mutation. |
| `rv:work-registry:observational-registry:read-dashboard` | Authenticated dashboard reads the registry snapshot. |
| `rv:work-registry:observational-registry:grace-permission-boundary` | Future Grace adapter requires its existing exact institutional grant. |
| `rv:work-registry:observational-registry:retain-history` | Completed and disconnected history remains observable. |

See [`WORK_REGISTRY_COOKBOOK.md`](WORK_REGISTRY_COOKBOOK.md) for diagnostics and recovery steps for each failure path.
