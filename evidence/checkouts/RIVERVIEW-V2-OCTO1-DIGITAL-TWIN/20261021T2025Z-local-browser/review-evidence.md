<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/RIVERVIEW-V2-OCTO1-DIGITAL-TWIN/20261021T2025Z-local-browser/review-evidence.md
Revision: 1.0.0
Task: RV-V2-OCTO1-DIGITAL-TWIN
Authority: Isolated review evidence only; no production changes
-->
# OCTO1 V2 digital twin review evidence

Source commit tested: `7ad48dc7f4c66887ee8f1d5cca5fc6b993667e3c`.

`source-observation.json` is an actual read-only observation captured at `2026-10-21T17:35:24Z` by the restricted OCTOMINER1 GPU collector and fixed model endpoints. It shows six GPUs, the 80B model mapped to P100 devices 0, 3, 4, and 5, the 30B model mapped to RTX 4090 device 1, and RTX 3060 Ti device 2 unassigned. It also records model health and slot occupancy. It is a historical point-in-time sample, not a fresh post-change production acceptance.

The desktop screenshot and `browser-report.json` come from an isolated loopback HTTPS Chrome fixture with synthetic telemetry. The screenshot watermark says `LOCAL BROWSER FIXTURE · SYNTHETIC DATA · NOT A LIVE OCTO1 READING`. It verifies the presentation and interactions only. The test also checks a 390 px viewport has no horizontal overflow; Chrome's headless screenshot capture after viewport resize was blank, so no narrow-layout screenshot is included.

The implementation is a telemetry-driven interactive topology view, not yet a manufacturer-accurate chassis drawing. The Steward's four reference images were not present in the engineering workspace. No replacement artwork, physical GPU slot positions, fan-channel mappings, or controller locations are invented. Current OCTO1 Dashboard telemetry does not provide chassis fan RPM/PWM, controller sensors, PSU data, watchdog status, or request-correlated model generation phases. Those values remain explicitly unavailable.
