<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/RV-OCTO1-PHASE2-TRACE-UI-001/checkout.md
File Revision: 1.0.0
Task: RV-OCTO1-PHASE2-TRACE-UI-001
Purpose: Record V2 Grace request lane and isolated browser fixture verification
Authority: Source and isolated browser testing only; no production deployment
Changed: 2026-10-21 UTC | RV-OCTO1-PHASE2-TRACE-UI-001 | Record UI integration and test evidence
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
History: Git and artifacts.json
-->
# V2 request trace lane — browser evidence

Branch `codex/octo1-phase2-v2-trace-20261021` is based on the accepted digital-twin merge `9847c80762e252503c6b06cabbd93f1f6e05e719`. This work adds a Grace request-event lane beside (not joined to) the existing five-second hardware sampling timeline.

Verification:

- `node --check website/v2/assets/resource-monitor.js` — PASS.
- `node --check website/v2/assets/grace-chat.js` — PASS.
- `node scripts/verify_v2_resource_monitor.cjs` — PASS; request and telemetry lanes remain separate, labels reflect only available evidence, polling starts/stops with view.
- `node scripts/verify_v2_octo1_browser.cjs --evidence-dir evidence/checkouts/RV-OCTO1-PHASE2-TRACE-UI-001/20261021T-browser-final` — PASS in isolated HTTPS fixture with Chrome 155. No browser errors; front/open chassis, fan detail, 80B allocation and RTX 4090 detail captured; narrow viewport 375px has no horizontal overflow.

Every value in the browser capture is **synthetic fixture data** and is labeled in the report/screenshots. This does not establish live V2 deployment, live browser acceptance, controller telemetry, model-server receipt, or GPU-to-request attribution.
