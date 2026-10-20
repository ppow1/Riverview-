/*
Riverview~ Controlled Source
File: website/v2/assets/fixtures.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.2
Purpose: Provide synthetic non-production preview content
Execution Model: Interactive browser data module
Observability: Fixture labels rendered by the owning shell; no runtime service
Dependencies: Browser JavaScript; loaded before workspace.js
Inputs/Outputs: Fixed fixture objects exported on window.RIVERVIEW_V2_FIXTURES
Authority: Fixture data only; no API, credential, storage, or production authority
Changed: 2026-10-20 UTC | RV-WEB-V2-GRACE-WORKSPACE-003 | Identify Grace as authenticated chat, with synthetic fixture status retained
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: tests/test_v2_workspace_shell.py, scripts/verify_v2_workspace_browser.py, scripts/verify_v2_workspace_mobile.cjs
History: Git and revision/backup manifest
*/
window.RIVERVIEW_V2_FIXTURES = Object.freeze({
  residents: Object.freeze([
    Object.freeze({ id: "grace-preview", name: "Grace", role: "Verified identity · preview", initials: "G", status: "Authenticated chat · sign-in required", realIdentity: true }),
    Object.freeze({ id: "fixture-resident-02", name: "Resident fixture 02", role: "Synthetic preview record", initials: "02", status: "Example workspace", realIdentity: false }),
    Object.freeze({ id: "fixture-resident-03", name: "Resident fixture 03", role: "Synthetic preview record", initials: "03", status: "Example workspace", realIdentity: false })
  ]),
  work: Object.freeze([
    Object.freeze({ title: "Review the weekly brief", owner: "Grace", state: "In progress", detail: "Preview item · no assignment record" }),
    Object.freeze({ title: "Prepare a resource note", owner: "Steward", state: "Ready to review", detail: "Preview item · no dispatch" }),
    Object.freeze({ title: "Check workspace references", owner: "Grace", state: "Waiting", detail: "Preview item · no production evidence" })
  ]),
  resources: Object.freeze([
    Object.freeze({ title: "Workspace guide", kind: "Reference", detail: "Fixture card" }),
    Object.freeze({ title: "Shared reading list", kind: "Collection", detail: "Fixture card" })
  ]),
  knowledge: Object.freeze([
    Object.freeze({ title: "How this preview works", kind: "Preview note", detail: "Local static fixtures; no external data is loaded." }),
    Object.freeze({ title: "Production integrations", kind: "Not connected", detail: "A separate governed API and authorization design is required." })
  ])
});
