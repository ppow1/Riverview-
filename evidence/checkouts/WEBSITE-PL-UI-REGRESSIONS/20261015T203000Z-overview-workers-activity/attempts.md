<!-- Riverview~ controlled evidence
File: evidence/checkouts/WEBSITE-PL-UI-REGRESSIONS/20261015T203000Z-overview-workers-activity/attempts.md
Component: STEWARD-DASHBOARD / WEBSITE
File Revision: 1.0.0
Purpose: Retain failed fixture assertions and corrections for the dashboard browser regression
Authority: Troubleshooting history only
Changed: 2026-10-15 UTC | RV-WEBSITE-PL008/011 | Record harness assertion corrections preceding passing run
History: Git and artifacts.json checksum manifest
-->
# Browser fixture troubleshooting

- The first source assertion compared a JavaScript path regex with the wrong escape representation. The assertion was corrected to compare the actual escaped expression; the focused test then passed.
- The first worker summary draft used one counter namespace for registration and status, so an inactive row inflated the inactive registration count. Registration and heartbeat counters were separated; the final four-row fixture reconciled correctly.
- The first paging browser wait expected the raw `fixture_event_3` label, while the UI intentionally humanizes underscores. The wait now checks the rendered sequence label instead. A transient WebDriver 404 also occurred during a retry; the next isolated session completed and all checks passed.
