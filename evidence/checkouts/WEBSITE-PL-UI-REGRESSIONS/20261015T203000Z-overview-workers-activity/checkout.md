<!-- Riverview~ controlled evidence
File: evidence/checkouts/WEBSITE-PL-UI-REGRESSIONS/20261015T203000Z-overview-workers-activity/checkout.md
Component: STEWARD-DASHBOARD / WEBSITE
File Revision: 1.0.0
Purpose: Record isolated browser verification of overview, worker inventory and activity paging
Authority: Synthetic browser fixture only; no production data or service access
Changed: 2026-10-15 UTC | RV-WEBSITE-PL006/008/011 | Verify status explanations, paged worker states and bidirectional event cursors
History: Git and artifacts.json checksum manifest
-->
# PL-NEW-006 / 008 / 011 isolated Firefox verification

Firefox 156.0.1 loaded the checked-out dashboard shell, CSS and JavaScript in a synthetic same-origin account-cookie fixture. Protected API requests included the fixture cookie and no bearer header. Four fixture workers across two pages reconciled as 2 active, 1 inactive and 1 unknown registration; healthy, stale, and unknown heartbeat states stayed distinct, the final cursor hid the pager, and a 390px viewport had no worker-row overflow. The overview guidance described event cursor, projection/freshness, independent CME/worker heartbeat state, and Grace execution versus chat availability.

The Activity view started with event sequences 2–3, prepended sequence 1 using `before_seq=2`, then appended sequence 4 using `after_seq=3`; order was ascending with no duplicates. All reported checks passed and the browser error list was empty.

The fixture is synthetic. It does not establish live registry contents, production heartbeat thresholds, or deployed acceptance.

Tested branch parent: `a459cadb7cc203297949b2c3e2042f66fe468637`. The post-parent source candidate is bound by the checksums of the listed browser source/test files in the checkout; its commit is created with this evidence package.
