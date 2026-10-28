<!-- Riverview Controlled Document
File: docs/development/GRACE_DEVELOPMENT_REPLACEMENT_20261028.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.0
Changed: 2026-10-28 UTC | Steward development-system direction
-->
# Fresh development request replaces stale recovery priority

Steward clarified that Riverview is not yet production and instructed the operator
to prefer cancellation and fresh bounded requests over prolonged recovery of stale
development requests. This supersedes the prior handoff's insistence on recovering
the exact old Run 2. Preserve its history; do not reset counters or fabricate state.

## Verified records

Old objective: objective:proposal:4ab91570-c31a-5420-994b-33474fe567ed:r2.
Canonical read: GROUNDED revision 2; no assignment, steps, intents or verification.
Its cancellation has NOT been performed. Existing canonical cancellation route is
POST /api/v1/objectives/{id}/cancel with exact assignment.cancel authority and
scope work-order:engineering. The Comms5 cancel_draft tool cannot cancel objectives.

Replacement: proposal:f34ed871-1779-42ff-866e-53ac1ae61551 revision 2.
State: READY_FOR_STEWARD_DECISION.
Digest: 1ca2838005ef4cb246b6bba297b4a6d331203f2ba8be813249ea7b25e501eef4.
Task: Grace coordinates a bounded existing-runbook clarification through Engineering,
GitHub publication, independent verification and normal completion. Preserve actual
Camrui workspace-write evidence and Windows sandbox limitations.

Authenticated confirm_and_promote_seed attempted with existing Steward direction:
BACKEND_UNAVAILABLE, executed:false, reason dashboard_operation_unavailable,
error_code INVALID_ARGUMENT. No new objective or execution was created.
Do not retry blindly or represent this as missing user approval.

## Current next action

Inspect and repair the bounded existing intake/control adapter gap, using canonical
lifecycle operations. No new services, authority models or credentials. Do not
continue old-request forensic debugging as a prerequisite for the replacement.

Existing exact Camrui Codex thread:
01a17fdf-6d58-7050-92cc-1762ac986518.

Control-path inspection:
run grace-development-replacement-path-20261028-01;
execution f500c27f-6eca-4746-b6cc-8afe087128c5, exit 0;
terminal audit e02ab582-0257-4b6d-9c63-e10bd19a4ab8.
Result retrieval e1a7eaa5-e951-40b1-a2a2-1632b2bda2c0;
audit 8097dae4-3af6-4276-8857-c9580b18b413.
No cancellation event was created; no authorized grant-bearing Dashboard client
was exposed to the Codex session.

Active bounded source task:
run grace-fresh-intake-control-gap-20261028-01;
execution d9c53604-df15-4bd6-a024-ae83f37ae6e0;
original key grace-fresh-intake-control-gap-20261028-01;
command SHA256 5419ab2064ff8c866f202ed8882e7f6cc02bc9b605b80009ec5a9087e594ef8e.
Inspect existing adapter and promotion endpoint, implement only demonstrated
defects with focused tests, preserve predecessors, report unavailable components.
No deployment, direct database mutation, grants or credential changes authorized
by this bounded adapter task.
