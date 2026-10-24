# Riverview visualization and navigation roadmap

This roadmap is an extensible sequence of capability slices, not a fixed inventory of tabs. Each item should reuse an existing owner API and data source, have current-vs-historical evidence labels, and preserve the authorization boundary. The separate Grace reasoning/execution workstream remains outside this roadmap's implementation scope.

## Now — operational visibility with current services

1. **Recommended next implementation: a unified V2 Notifications and Operational Events inbox.** Reuse the existing `/api/v1/notifications`, `/api/v1/attention`, and `/api/v1/events` contracts already used by V1. Keep persisted Notification Settings as-is. Show delivery/acknowledgment state, severity, timestamp, exact related objective/service, and an evidence link. Preserve endpoint authorization and notification-policy enforcement; do not add a dispatcher or second inbox store. This closes a live V1/V2 gap and gives the institution a reliable attention entry point.
2. Add blocker/dependency drill-down to V2 Work/Engineering Progress using current objective, stage, assignment, and audit records. Keep cancellation eligibility and active-worker safety rules unchanged.
3. Improve V2 Overview with sourced/freshness-labelled summaries of existing service health, active/blocked work, resource utilization, and recent attention. Link every summary to its owning page and evidence record.
4. Keep acceptance results, API/auth boundaries, and release identity visible. Treat the 37 PASS / 0 FAIL / 3 SKIPPED browser result as WARNING, not acceptance.

## Next — reusable V2 integration and missing functionality

5. Bring Institutional Proposals into V2 through the already-existing proposal routes and review/decision records.
6. Add resident permission/account administration views by reusing existing V1 APIs and authorization; do not build a new role model.
7. Expand Communications and Documentation/Diagnostics coverage with safe projections, correlation IDs, and existing runbook/evidence links.
8. Add model/host/GPU/workload association using authoritative live telemetry and UUID-bound runtime evidence. Mark uninstalled model-assignment code as such.
9. Test V2 task flows at mobile widths and repair concrete interaction problems before proposing a separate mobile app.

## Later — advanced visualization and physical interfaces

10. Develop the panoramic Steward Command Center composition from the original artwork once the original binary is transferred and preserved. Keep all represented data bound to live APIs; concept art alone remains an illustration.
11. Validate physical display geometry, source selection, scaling, input, and recovery across the tested HDMI matrix and actual displays before designing a multi-display wall. Current evidence does not prove four independent displays over AirPlay/Linux.
12. Extend the existing Stream Deck actions to capability navigation and bounded authorized operations, with visible target/result and status feedback.
13. Recommission the historical Quest/WebXR prototype against current hardware, deployment, headset, and input behavior. Begin read-only; teleport/hand-input and production resident-model behavior were unresolved in the historical acceptance.
14. Consider a dedicated mobile app or spatial room only if responsive V2 and shared APIs cannot meet demonstrated use cases.

## Extending the roadmap

For each newly discovered capability, add a slice with: domain; repository/source path; maturity (proposed, implemented, historically tested, deployed, live); authoritative API/data owner; current V2 exposure; reusable component; required grants; concrete evidence; migration priority; dependencies. Revisit priority from Steward/operator value, safety, reuse potential, and evidence quality. Do not turn this list into permanent top-level navigation and do not create another capability database to store the roadmap.
