<!--
Riverview~ Controlled Document
File: docs/development/RV-OCTO1-PHASE2_TRACE_REVISION_RECORD.md
Component: RESIDENT-CONVERSATION / OCTO1 TELEMETRY
File Revision: 1.0.0
Task: RV-OCTO1-PHASE2-TRACE-001
Purpose: Record read-only OCTO1 discovery and Grace inference tracing implementation evidence
Authority: Source and isolated testing only; no production deployment or hardware writes
Changed: 2026-10-21 UTC | RV-OCTO1-PHASE2-TRACE-001 | Record verified live telemetry and client-observed Grace model-response tracing
Contracts: docs/components/RESIDENT_CONVERSATION.md; docs/components/STATUS_DASHBOARD.md
Verification: focused tests 108 passed / 30 skipped; full suite 548 passed / 240 skipped; graph 22/598 PASS; controlled revision audit PASS
History: Git and .riverview-backups/manifest.jsonl
-->
# OCTO1 Phase 2 — Controller telemetry and Grace request trace

## Baseline and read-only inspection

The backend worktree is based on deployed Dashboard source `26c71277f45338239a707f09e118eb70bcd449c4`; the accepted V2 digital-twin merge `9847c80762e252503c6b06cabbd93f1f6e05e719` remains unchanged in its own worktree. OCTO1 data was gathered by invoking the already-installed `DashboardResourceTelemetry` from the deployed Dashboard release under its existing systemd credential directory. Its host key validation remains strict and the SSH identity is restricted to the fixed `resource-telemetry` command. No key material or conversation bodies were accessed.

The sample at `2026-10-21T22:45:35.121Z` showed six OCTO1 GPUs, live NVIDIA utilization, VRAM, temperature, power, and GPU-fan percentage where supported. The per-device values and loaded model/slot status are recorded in `evidence/checkouts/RV-OCTO1-PHASE2-TRACE-001/20261021T224535Z/octo1-live-telemetry.json`. `nvidia-smi` GPU fan percentage is distinct from chassis controller RPM/PWM. The collector has no OCTO1 fan-controller, environmental sensor, control target/mode, PSU, watchdog or physical riser fields. It discards PID/UUID and does not claim a per-request GPU mapping.

The configured `octo1` SSH alias exists only in the documented Windows operator context. This Camrui Linux session has no Windows SSH aliases or general-purpose OCTO1 identity. The service's installed telemetry key is forced to the bounded collector command, so arbitrary controller/PCI inspection cannot be performed through it. No other trusted host-inspection route was found in this session. Controller presence, device identity, and controller readings therefore remain **unverified**, not asserted absent.

## Grace model trace implementation

The existing conversation UUID is now forwarded as `X-Riverview-Request-ID` through the existing local provider and readiness router, including streamed turns and deferred resumption. The local provider accepts only a canonical UUID and captures only bounded response provenance: a safe opaque response ID when returned, the client-observed response-header time, first streamed text time when streaming, and client-observed response-body completion. These fields are stored in existing sanitized provider attempt metadata; no schema migration or prompt/response capture was added. Proposal drafting and durable result-review calls use deterministic or existing durable request IDs and retain provider-attempt provenance where their existing records already persist it.

No claim is made that custom request headers are logged by the currently running llama.cpp services. The model server does not expose a correlated receive timestamp, prompt-processing event, or token-generation event through its current API. `/slots` reports only aggregate slot occupancy, and `/metrics` is not available. Thus the trace can show durable request creation, router/provider call start, response ID/headers observed by the client, first streamed text if present, response-body completion observed by the client, and the assistant persistence event. Server receipt and internal inference phases remain explicitly unavailable. GPU utilization is never used as proof of a request.

## Verification and change boundary

The V2-only follow-up worktree is based on accepted release `9847c807...`. It adds a distinct Grace-request lane to the existing five-second browser timeline; it reads the current authenticated conversation through the existing endpoint and never combines GPU samples with a request. Browser fixture captures are explicitly synthetic and are not production acceptance.

No production credentials, services, databases, inference servers, controller settings, migrations, or release pointers were changed. No merge, deployment, or service restart was performed.

Focused backend verification: `PYTHONPATH=src python3 -m unittest tests.test_local_reasoning_provider tests.test_resident_model_router tests.test_resident_conversation -q` — **108 passed, 30 skipped, 0 failed**. Full canonical backend suite: `PYTHONPATH=src python3 -m unittest discover -s tests -q` — **788 tests run, 548 passed, 240 skipped, 0 failed**; skipped cases require optional integration services/configuration. `python3 scripts/process_graph.py check` — **22 graphs / 598 nodes PASS**. `python3 scripts/revision_control.py check --baseline /tmp/rv-octo1-phase2-backend-baseline.json` — **PASS, zero findings**. `git diff --check` passed for changed files; the CRLF revision manifest is checked with `core.whitespace=cr-at-eol` because repository convention stores it with CRLF.

The independent V2 worktree passed JavaScript syntax checks, `node scripts/verify_v2_resource_monitor.cjs`, and `node scripts/verify_v2_octo1_browser.cjs --evidence-dir evidence/checkouts/RV-OCTO1-PHASE2-TRACE-UI-001/20261021T-browser-final`. The latter used an isolated local HTTPS fixture and Chrome 155: all five visual/interactive screenshot states passed, no browser errors, six-device/model mapping and trace timeline assertions passed, and 375px layout had no horizontal overflow. All values in those browser captures are **synthetic fixtures**, explicitly labeled as such. They are not a live production browser acceptance.
