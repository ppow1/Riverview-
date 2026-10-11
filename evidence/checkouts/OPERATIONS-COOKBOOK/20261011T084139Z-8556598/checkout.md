<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/OPERATIONS-COOKBOOK/20261011T084139Z-8556598/checkout.md
Component: RIVERVIEW-OPERATIONS / STEWARD-DASHBOARD
File Revision: 1.0.0
Purpose: Verify exact-source dashboard cookbook deployment and browser rendering
Authority: Dashboard-only non-destructive release; no database mutation
Source: 8556598b19a7da4aa191a600c767d79d24432afe; PR #19 CI run 38125561042
History: artifacts.json SHA-256 manifest
-->
# Operations guide release 8556598

The latest PR #19 head passed full controlled-checkout CI before deployment. A package built from the exact committed blobs passed package-manifest and shell-compatibility verification. Its archive checksum and all 1,304 extracted manifest checksums are recorded in this bundle. It was installed into a new immutable root-owned release; the prior `a8f0d62` release and protected archive were preserved.

Only `riverview-status-dashboard.service` was restarted. The initial readiness request raced listener bind, then HTTP 200 arrived within ten seconds; no retrying restart was needed. The dashboard stayed on loopback 8766, zero restarts, exit code 0. The other five operational services remained active; the unit checksum did not change.

Firefox 156.0.1 verified healthy/current projection, healthy CME, six durable attention records, the existing completed M3.1 assignment and one independent verification. The operations guide rendered 18 headings, 2 tables and 18 code blocks; all 21 document links returned 200, with no raw Markdown, unsafe links, scripts or browser errors. The workflow graph presented 12 nodes, 11 edges and one decision; live execution position remained unknown because the ledger has no authoritative graph-node ID. Navigation-call values were 59, 65, 91 and 102 ms; these do not measure full paint or sustained performance.

This is docs/browser deployment evidence only. No database migration/data, credential, worker, assignment or non-dashboard unit changed. M3.3 and M4.1 remain unaccepted; the application worker path does not consume authority grants and live knowledge/worker commissioning is still absent.
