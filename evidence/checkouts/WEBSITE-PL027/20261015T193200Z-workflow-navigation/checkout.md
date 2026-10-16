<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/WEBSITE-PL027/20261015T193200Z-workflow-navigation/checkout.md
File Revision: 1.0.0
Task: RV-WEBSITE-PL027
Result: Initial harness attempt; no product failure established
-->
# Initial isolated browser attempt

The first Firefox harness opened the dashboard workflow view without setting the test-only session token. The existing viewer correctly declined to load the authenticated graph registry, so the harness timed out while waiting for graph options. The application was not changed in response. The next harness set a local fixture token and passed the intended destination-focus and return checks; see the sibling `20261015T193400Z-workflow-navigation` evidence.
