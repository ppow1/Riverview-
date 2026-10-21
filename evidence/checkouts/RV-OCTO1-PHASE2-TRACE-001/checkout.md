<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/RV-OCTO1-PHASE2-TRACE-001/checkout.md
File Revision: 1.0.0
Task: RV-OCTO1-PHASE2-TRACE-001
Purpose: Record read-only OCTO1 observations and source validation
Authority: Isolated source changes and read-only telemetry only
Changed: 2026-10-21 UTC | RV-OCTO1-PHASE2-TRACE-001 | Capture observed GPU/model state and validation results
Contracts: docs/components/RESIDENT_CONVERSATION.md; docs/components/STATUS_DASHBOARD.md
History: Git and artifacts.json
-->
# OCTO1 Phase 2 source and telemetry evidence

## Production observation (read-only)

- Dashboard release used: `/opt/riverview-status-dashboard/releases/26c71277f45338239a707f09e118eb70bcd449c4`.
- Existing `DashboardResourceTelemetry` was invoked with the running Dashboard service's existing credential path, strict host-key checking, and its fixed `resource-telemetry` remote command. No credential values or conversation bodies were read or recorded.
- Observation time: `2026-10-21T22:45:35.121Z`.
- Sanitized device/model measurements: `20261021T224535Z/octo1-live-telemetry.json`.
- Confirmed: six GPUs and live NVIDIA utilization, memory, temperature, power, and GPU-fan percentage where the driver supplies it; loaded model identities/readiness and aggregate slot occupancy were also observed.
- Not exposed by the current collector: chassis controller channel RPM/PWM, fan target/control mode, controller/environment sensors, PSU telemetry, watchdog heartbeat/reset state, or GPU PCI/riser mapping. NVIDIA GPU fan percentage is not chassis-fan telemetry.
- Model server exposes readiness/loaded model and `/slots` occupancy. The inspected `/metrics` endpoint is unavailable; request-correlated server receipt, prompt processing, and token-generation timestamps are not exposed. A `/slots` occupancy or GPU sample is not evidence that a particular Grace request reached or generated on the model.
- Physical GPU-to-riser mapping remains unknown. Software model-to-GPU allocation is present in service process mapping, but device index is not a physical bay identifier.

## Source changes and verification

Backend worktree: `codex/octo1-phase2-trace-20261021`, based on deployed Dashboard source `26c71277f45338239a707f09e118eb70bcd449c4`.

- Focused backend: `PYTHONPATH=src python3 -m unittest tests.test_local_reasoning_provider tests.test_resident_model_router tests.test_resident_conversation -q` — 108 passed, 30 skipped, 0 failed.
- Full backend: `PYTHONPATH=src python3 -m unittest discover -s tests -q` — 788 run, 548 passed, 240 skipped, 0 failed.
- Process graph: `python3 scripts/process_graph.py check` — 22 graphs / 598 nodes PASS.
- Controlled revision/predecessor check: `python3 scripts/revision_control.py check --baseline /tmp/rv-octo1-phase2-backend-baseline.json` — PASS, zero findings.
- No production service, database, model server, controller, credential, or release pointer was changed. No PR merge or deployment was performed.

The browser screenshots are in the separate V2 UI worktree and use labeled synthetic fixtures. They verify rendering and layout only, not live production behavior.
