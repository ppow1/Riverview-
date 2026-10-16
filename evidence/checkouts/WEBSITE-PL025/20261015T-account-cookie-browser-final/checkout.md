<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/WEBSITE-PL025/20261015T-account-cookie-browser-final/checkout.md
File Revision: 1.0.0
Task: RV-WEBSITE-PL025
Result: PASS for isolated cookie-only workflow registry and detail loading; deployed acceptance pending
-->
# Account-cookie workflow browser verification

**Branch:** `codex/website-improvements` at resumed worktree baseline `2578626`.
**Environment:** Firefox headless and geckodriver against an isolated loopback fixture serving the checked-out `workflow.js` and `app.css`. Synthetic fixture login issued an HttpOnly same-origin cookie; only test graph data was served.

The browser loaded the workflow index and graph detail with the account cookie and without an Authorization header, selected the graph node, and rendered its stable ID and detail. Browser errors: none. Machine-readable details and screenshot are listed in `artifacts.json`.

This verifies browser cookie transport and the workflow client in isolation. It does not validate production account authentication, the live deployment, or production graph data. Read-only SSH to `admin1@192.168.1.155` failed with `Permission denied (publickey,password)`, so deployed acceptance remains pending. No production service or database was contacted.

Two earlier harness attempts are preserved in sibling directories: `20261015T-account-cookie-browser/` timed out because the harness incorrectly expected a default node selection; `20261015T-account-cookie-browser-rerun/` hit an SVG click error. The final retry corrected node selection to dispatch the viewer's click event.
