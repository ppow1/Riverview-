<!-- Riverview~ Controlled Evidence
File: evidence/checkouts/RV-V2-BAMBU-READONLY-230/README.md
Component: RIVERVIEW-V2-HARDWARE-AI-RESOURCE-MONITOR
Revision: 1.0.0
Purpose: Record isolated Bambu P2S/AMS browser-fixture acceptance without implying live printer telemetry
Execution Model: Local Chrome against synthetic same-origin API fixtures
Observability: Browser report, screenshot, and SHA-256 artifact manifest
Authority: Isolated test only; no production calls, printer controls, or service changes
History: Git and artifacts.json
-->
# Issue #230 V2 browser-fixture evidence

The Chrome acceptance rendered a connected Bambu P2S, progress and temperatures,
remaining time/layer, and four AMS slots. It also exercised offline, stale, and
unavailable source states. No printer-control action is present. The browser
fixture uses synthetic values, prominently labels them as synthetic, and is not
evidence of live OCTO1 data or production visual acceptance.

The authenticated production Dashboard resource API currently returns no Bambu
projection. The backend PR supplies that field; live measurements remain
unavailable until the backend is reviewed and commissioned separately. This
assignment did not modify production.
