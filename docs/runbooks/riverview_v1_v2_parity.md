<!-- Document Revision: 1.0.0 -->
# Riverview deployed V1/V2 parity inventory

Observed 2026-10-24 against the live LAN website. V1 is the root operations portal (`/`); V2 is `/v2/`, whose deployed manifest identifies `RV-WEB-V2-ACCEPTANCE-ebd53a84` at commit `ebd53a84ae6e016353083ffe40f15048512ac6c6`. This is a UI and route inventory, not a claim that every protected operation was exercised. Unauthenticated probes of protected `/api/v1/...` paths returned 401, confirming the authentication boundary. Each endpoint continues to enforce its own authorization.

| V1 feature/function | V2 counterpart | Status | Backend/API availability and authorization | Suggested migration priority |
|---|---|---|---|---|
| Operations overview | Workspace overview and Website verification card | Working | Live V2 shell/release/report routes returned 200; report view is read-only. | Maintain |
| Assignments and objective/work-order progress | Work: Objectives, assignment progress, Engineering Progress; cancellation controls | Partial | Both bundles use authenticated objective/work APIs. Cancellation remains subject to existing lifecycle rules and Steward authorization; production mutation is skipped without disposable work. | P1: complete parity and safe test fixtures |
| Institutional proposal registry/details | No equivalent V2 registry/detail workflow | Missing | V1 bundle references `/api/v1/institutional-proposals`; operation requires existing institutional authorization. | P1: high; preserve lifecycle and audit behavior |
| Grace conversation | Grace chat in V2 | Working for authorized sessions; test persona blocked | V2 uses conversation-session, conversation, and stream APIs. Requires authenticated identity plus institutional conversation grants. | Maintain; enable isolated test authority separately |
| Resident directory | Residents view | Working for directory | V2 view is present; protected server APIs remain authenticated. | Maintain |
| Resident permission/profile administration | No V2 permission administration view | Missing | V1 bundle references `/api/v1/resident-permissions`; existing API authorization applies. | P1: high for operator administration |
| Activity/event ledger | Communications activity ledger | Partial | V1 references `/api/v1/events`; V2 Communications presents scoped activity, not the full V1 activity view. Authenticated backend. | P2: compare event coverage |
| Notification inbox/attention delivery | Notification Settings page | Partial | V1 references `/api/v1/notifications` and `/api/v1/attention`; V2 settings uses authenticated `/api/v1/notification-settings`. Settings persist; V2 navigation has no equivalent notification inbox/history. | P1: decide on inbox/history parity |
| Registered workflows and cross-workflow destinations | Image Generation workflow selector | Partial | V2 workflow UI covers image generation, not the full V1 workflow/destination view. Authenticated operations. | P2: retain general workflow discoverability |
| Documentation and diagnostics | Knowledge, Resources, Hardware & AI, Snapshot views | Partial | V2 exposes these views, but not all V1 documentation/diagnostic links. Protected APIs require authentication. | P2: add operational docs links where needed |
| Account/session administration and enrollment | No V2 account administration view; normal V2 login remains | Missing | V1 bundle references account users/enrollments, auth/session, and email settings APIs; V2 enforces login and role checks. | P1: high, Steward administration |
| Hardware & AI monitoring | No dedicated V1 counterpart | V2-only | Dedicated V2 hardware/resource panels backed by protected server APIs. | Maintain |
| Snapshot capture/archive | No dedicated V1 counterpart | V2-only | V2 uses `/api/v1/snapshot`, `/api/v1/snapshot/workflow-index`, and `/api/v1/snapshot/archive`; archive write was skipped to avoid durable production data. | Maintain |
| Website acceptance status | No V1 counterpart | V2-only | `/v2/verification/latest.json` is live and read-only; V2 panel displays categorized results. | Maintain |

## Evidence and limits

- Live V1 HTML title is “Riverview — Operations”; navigation includes Overview, Assignments, Objectives, Institutional proposals, Grace chat, Resident permissions, Activity, Workflows, Notifications, Documentation, and Account.
- Live V2 HTML title is “Riverview V2 Workspace”; navigation includes Overview, Residents, Work, Image Generation, Resources, Knowledge, Communications, and Notification Settings. Work contains objective/assignment progress and Engineering Progress; Overview contains Website verification.
- V1 bundles reference `/api/v1/account/*`, `/api/v1/notifications`, `/api/v1/events`, `/api/v1/objectives`, `/api/v1/resident-permissions`, and `/api/v1/institutional-proposals`. V2 bundles reference notification settings, snapshot, resident conversation, objective, graph, and status APIs.
- Unauthenticated protected API probes returned 401. This confirms protected routing, not operation-specific authorization or successful authenticated execution for every listed API. The full acceptance runner separately verifies its listed authenticated scenarios.
- No production feature was changed for this inventory.
