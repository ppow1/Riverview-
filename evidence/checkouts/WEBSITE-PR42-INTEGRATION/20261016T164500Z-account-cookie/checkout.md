# PR #42 current integration account-cookie regression

- Date: 2026-10-16 UTC
- Source tree: website branch `codex/website-improvements` with integration through `af87c1a1b8ef4deeb8770c64da8bb4556bc85866` and local PR #42 changes.
- Tested client source: `src/riverview_core/status_dashboard/static/workflow.js` and `app.css` from this checkout.
- Browser: Mozilla Firefox 156.0.1.
- Mode: isolated same-origin HTTP fixture; synthetic account session only; no production access.
- Result: PASS, no failed checks or browser errors. Both graph registry/detail requests included the synthetic account cookie and omitted Authorization; the canonical node rendered.
- Limitation: fixture verification does not establish production account authentication, deployment state, or objective-intake behavior.
- Reproduce: `python3 scripts/verify_workflow_account_cookie_browser.py --output <new-directory>`.

`artifacts.json` checksums the browser report and screenshot.

- `workflow.js` SHA-256: `c64b9338cddedafaeddd8c997c3871f60bf7cf87c8db5c94798f946a6bb7e2af`.
- `app.css` SHA-256: `72dee659205bb9934f471b729cd541e0e062948961c7a36bf34ead943b66f686`.
