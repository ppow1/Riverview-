/* Riverview~ Controlled Document | File: website/v2/assets/fixtures.js | Component: RIVERVIEW-V2-WORKSPACE-SHELL | File Revision: 1.0.0 | Purpose: Synthetic, non-production preview content | Authority: Fixture data only | Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Initial preview fixtures */
window.RIVERVIEW_V2_FIXTURES = Object.freeze({
  residents: Object.freeze([
    Object.freeze({ id: "grace-preview", name: "Grace", role: "Verified identity · preview", initials: "G", status: "Workspace shell only", realIdentity: true }),
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
