<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/WEBSITE-PL027/20261015T193400Z-workflow-navigation/checkout.md
File Revision: 1.0.0
Task: RV-WEBSITE-PL027
Result: PASS for isolated cross-workflow target navigation and return
-->
# Website workflow navigation browser verification

**Branch:** `codex/website-improvements`  
**Integration baseline:** PR #41 merge `218cb58491bcb939466a1eebb51bd666fd97005e`; PR #40 stream implementation is included.  
**Environment:** Firefox headless through geckodriver; loopback-only fixture serving the working-tree `workflow.js`, `app.css`, and canonical process graph JSON. No production service, account, database, or external network endpoint was used.

The browser loaded 19 canonical workflows. From `rv:assignment-intake:governed-request`, it followed `rv:assignment-intake:governed-request:exact-grant-jump` to `rv:institutional-authority:identity-and-grants:runtime-grant-check`. The exact destination node was focused and its details showed the stable ID. **Back to source node** restored the originating graph, source jump-node focus, and details. The machine-readable result and screenshots are in `browser-report.json`, `workflow-target.png`, and `workflow-return.png`.

The isolated fixture used a test-only bearer token in `sessionStorage`. It verifies interaction against real canonical graph content, but does not exercise production account-cookie authorization or live service transport. Browser console error collection was not part of this harness. The earlier fixture setup timeout is preserved in sibling evidence and was resolved by setting the fixture token.
