<!--
Riverview~ Checkout Evidence
File: evidence/checkouts/OPERATIONS-COOKBOOK/20261011T082220Z-4b7c23d/checkout.md
Component: RIVERVIEW-OPERATIONS / STEWARD-DASHBOARD
Document Revision: 1.0.0
Purpose: Record read-only live Firefox validation of cookbook rendering and operational projections
Source Commit: 4b7c23d4be505cd211fedcd37fafa58a49a13d3d
Deployed Commit: 8dcec2ada7d811a78f6cb28a1b81e6f8f59b1a9b
Host: Camrui / Ubuntu 24.04.3
Timestamp: 2026-10-11T08:22:20Z
Task: RV-OVERNIGHT-20261011-DASHBOARD-DOCS-CHECK
History: Evidence manifest and Git
-->
# Live dashboard and cookbook verification

- **Result:** PASS for the observed read-only browser checks; this does not commission an uninstalled checkout or accept a roadmap milestone.
- **Tool:** `scripts/verify_status_dashboard_browser.py`, headless Firefox 156.0.1, local dashboard `http://127.0.0.1:8766`.
- **Exact command:** `python3 scripts/verify_status_dashboard_browser.py --assignment-id m31-real-worker-2533f1c7dd1c433c95bd2cfa8a314d7c --output /tmp/rv-dashboard-overnight-check-20261011T0823Z`.
- **Observed deployed release:** `8dcec2ada7d811a78f6cb28a1b81e6f8f59b1a9b`; dashboard service active. PostgreSQL, event processor, CME monitor, notification dispatcher and SSH services were also active.
- **Projection:** completed assignment; healthy/current dashboard projection; healthy CME; six attention records; one persisted independent verification; no failed checks or browser errors.
- **Cookbook rendering:** operations guide displayed 17 headings, 2 tables, 17 code blocks; raw Markdown/frontmatter absent; no scripts or unsafe links. All 21 linked component documents returned HTTP 200.
- **Graph:** 12 nodes, 11 canonical edges (10 in-graph plus one cross-workflow jump), one decision; selected graph node was navigable. Live execution position correctly remained unknown because the ledger has no persisted graph-node identity.
- **Navigation handler timings (single run):** Assignments 84 ms, Activity 332 ms, Overview 90 ms, Workflows 242 ms. These are handler timings only, not paint latency or a sustained performance benchmark.
- **Boundaries:** read-only dashboard/browser validation; no assignment, database, credential, service, or deployed package changes.
- **Artifacts:** `browser-acceptance.json` and screenshots. See adjacent `artifacts.json` for SHA-256 and sizes.
