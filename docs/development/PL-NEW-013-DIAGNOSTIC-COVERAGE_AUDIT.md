<!--
Riverview~ Controlled Document
File: docs/development/PL-NEW-013-DIAGNOSTIC-COVERAGE_AUDIT.md
Component: STEWARD-DASHBOARD / WEBSITE
File Revision: 1.0.0
Task: RV-WEBSITE-PL013
Purpose: Record a bounded code-to-workflow, cookbook and diagnostic-catalog coverage audit
Authority: Audit findings only; no new product requirement
Changed: 2026-10-15 UTC | RV-WEBSITE-PL013 | Audit dashboard error-code and documentation traceability
History: Git
-->
# PL-NEW-013 dashboard diagnostic coverage audit

## Scope and method

Audited literal HTTP error identifiers in `src/riverview_core/status_dashboard/server.py` against exact string references in `docs/components/STATUS_DASHBOARD.md`, `docs/components/STATUS_DASHBOARD_COOKBOOK.md`, and the canonical dashboard workflow `process_graphs/steward-dashboard/status.json`. Searched the dashboard component for a diagnostic catalog route or named catalog artifact. Exact-name matching is a bounded traceability check; a missing exact match is not proof that no semantically relevant guidance exists.

The extraction pattern was `_error(<numeric status>, "<lowercase_identifier>")`. It found 59 distinct literal identifiers and one dynamic `exc.code` call site whose possible values are outside this extraction.

## Findings

| Trace | Result |
|---|---|
| Literal server error identifiers | 59 distinct; one dynamic `exc.code` call site is not enumerated |
| Exact identifier appears in dashboard contract or cookbook | 5 of 59 |
| Exact identifier appears in canonical dashboard workflow JSON | 0 of 59 |
| Semantic failure/recovery paths | Present for request denial, source/database/worker unavailability, credential failure, documentation unavailable, graph unavailable, and jump-target unavailable; the nodes reference cookbooks but do not enumerate server error codes |
| Dedicated dashboard diagnostic catalog | None found in dashboard component files or routes searched |
| Cookbook coverage | 15 component cookbooks exist repository-wide; dashboard troubleshooting contains process-first and area-specific guidance, but no complete error-code index |

Five exact dashboard contract/cookbook matches:

- `email_delivery_unavailable`
- `not_found`
- `process_graph_not_found`
- `projection_unavailable`
- `read_only_method`

The full literal server identifier set:

- `account_auth_unavailable`
- `asset_unavailable`
- `assignment_not_found`
- `authentication_required`
- `authority_unavailable`
- `challenge_invalid_or_expired`
- `conversation_message_not_found`
- `conversation_request_length_required`
- `conversation_request_too_large`
- `conversation_session_body_not_allowed`
- `cross_origin_request_denied`
- `csrf_or_session_check_failed`
- `diagnostic_reference_unavailable`
- `email_delivery_unavailable`
- `engineering_work_order_submission_not_authorized`
- `institutional_principal_required`
- `invalid_account_request`
- `invalid_conversation_request`
- `invalid_host`
- `invalid_objective`
- `invalid_objective_json`
- `invalid_objective_shape`
- `invalid_query`
- `invalid_work_order_request`
- `not_authorized`
- `not_found`
- `notification_not_found`
- `notification_receipt_body_not_allowed`
- `notification_receipt_conflict`
- `notifications_not_initialized`
- `notifications_unavailable`
- `objective_action_not_authorized`
- `objective_grounding_unavailable`
- `objective_intake_not_initialized`
- `objective_not_found`
- `objective_operation_unavailable`
- `objective_request_length_required`
- `objective_request_too_large`
- `objective_submission_conflict`
- `objective_submission_not_authorized`
- `objective_submission_unavailable`
- `process_graph_not_found`
- `projection_failed`
- `projection_unavailable`
- `read_only_method`
- `request_too_large`
- `resident_context_too_large`
- `resident_conversation_failed`
- `resident_conversation_not_authorized`
- `resident_conversation_not_found`
- `resident_conversation_unavailable`
- `resident_permission_change_not_authorized`
- `resident_permission_registry_unavailable`
- `resident_permission_revision_conflict`
- `steward_account_required`
- `steward_account_session_required`
- `ui_unavailable`
- `work_order_conflict`
- `work_order_intake_unavailable`

## Assessment

The audit confirms a traceability gap: dashboard workflow nodes describe broad failure and recovery states, but none names a literal server error code; only a small subset of literal codes appears verbatim in the dashboard contract/cookbook; and no dedicated diagnostic catalog is present. Existing area-level troubleshooting still provides useful recovery guidance, so this does not establish that every uncovered code lacks user-facing explanation or requires an individual workflow node.

This completes the requested audit portion of PL-NEW-013. The audit records coverage status; it does not create a new acceptance requirement to add one node or cookbook section per error code. A searchable, indexed diagnostic catalog remains a separately captured PL-NEW-038 proposal. Any catalog implementation should begin with an approved mapping/data source and avoid duplicating backend error semantics.

## Boundary

Read-only source and documentation inspection only. No backend, authorization, CME, production service, schema, or workflow-map changes were made. The existing canonical workflow already represents generic failure and recovery routing and required no semantic update for this audit.
