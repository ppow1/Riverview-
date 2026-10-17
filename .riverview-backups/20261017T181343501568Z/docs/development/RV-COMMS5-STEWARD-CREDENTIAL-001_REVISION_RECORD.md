<!--
Riverview Controlled Record
File: docs/development/RV-COMMS5-STEWARD-CREDENTIAL-001_REVISION_RECORD.md
Component: COMMS5-OAUTH-IONOGE
File Revision: 1.0.1
Purpose: Preserve evidence and change record for the Steward credential investigation and safe rotation procedure.
Authority: No live credential, grant, or service change was made.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-001 | Record credential mapping, custody evidence, procedure, and tests.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-002 | Record the merged helper deployment, direct-client inventory limit, and authorization-gated operator flow.
History: Git.
-->

# RV-COMMS5-STEWARD-CREDENTIAL-001 — OAuth page credential ownership

## Findings

- The public OAuth form label is backed by `RIVERVIEW_COMMS5_CLIENT_SECRET`. The deployed OAuth code reads it from `/etc/riverview/comms5-oauth.env` and compares the submitted form value in constant time.
- Caddy reads the same setting from `/etc/caddy/riverview-comms5.env`. The two deployed values matched in a read-only comparison. Both files are root-owned, mode `0600`; their filesystem birth times were 2026-10-17 04:16 UTC.
- Caddy also accepts this same value as a direct legacy bearer on `/comms5/mcp` and attests that request as `steward`. A rotation therefore changes both browser login proof and legacy direct-bearer access. OAuth access/refresh tokens are separately stored; they are not this credential.
- `RIVERVIEW_COMMS5_OAUTH_PROXY_KEY` is a separate matching Caddy/OAuth internal trust secret. `RIVERVIEW_COMMS5_UPSTREAM_AUTH` is separately held by Caddy for the backend hop and is absent from the OAuth environment file.
- Historical repository `ppow1/Riverview` at commit `08c1162c4ad04a21df71ed7814a3e22bd9ba41a2` describes the same variable as the Steward-controlled connector bearer in `config/riverview-comms5-ingress.Caddyfile.example` and `docs/operations/RIVERVIEW_COMMS5_DEPLOYMENT.md`. That proves intended ownership predates the OAuth page, but does not prove continuity of the live secret bytes.
- Deployment artifacts do not record issuance, generation, reuse, or operator delivery. The live value was installed with OAuth commissioning, but the record cannot establish if it was newly generated or reused. Operator custody is unverified.

## Changes

- Added `scripts/rotate_comms5_steward_credential.py`: read-only preflight and explicit stdin-based rotation, guarded service wiring and root-only file checks, protected predecessor copy, atomic dual-file update, restarts limited to OAuth and Caddy, health/authentication checks, and automatic predecessor restoration on failure. The secret is not accepted in argv/environment or emitted.
- Added isolated tests for matching/mismatched values, duplicate entries, private predecessor storage, malformed input, restart/health rollback, and exact service environment-file checks.
- Updated the machine-connection runbook and OAuth troubleshooting guide; added a credential lifecycle step to the canonical Comms5 graph.
- PR #86 merged at `a094297b67a9bd5e4ea3c74c284382c3e75845be`; exact-head controlled-checkout passed. Review was performed against the code and tests; no GitHub review approval was fabricated or required by branch policy.
- Installed the exact merged helper to Ionoge `/usr/local/sbin/rotate_comms5_steward_credential.py` with owner/mode `root:root/0755`, SHA-256 `9910a03d74c538466d36888950a3186d77e6362ced45125fc26dac77b0458224`. The read-only `--check` returned PASS. The helper refuses configuration mismatches and only the two Comms5 client-secret entries are in its write set.
- Live readiness check: Caddy and OAuth units active; Ionoge backend health `/healthz` HTTP 200; OAuth loopback `/healthz` HTTP 200; public authorization-server and protected-resource metadata HTTP 200; unauthenticated MCP HTTP 401. No service restart, credential rotation, OAuth database update, or Caddy configuration change occurred.
- Client inventory: OAuth state contains 11 DCR client records, including the named ChatGPT registration and commissioning/diagnostic clients. These do not enumerate direct static-bearer callers. Caddy has no Comms5 access-log directive and the service has no direct-bearer client registry, so external static-bearer consumers remain unknown. This remains the material rotation risk.
- Added `scripts/Invoke-RiverviewComms5StewardCredentialRotation.ps1`, a one-command Windows PowerShell 5.1 workflow. It checks the exact reviewed helper hash, performs read-only configuration/service checks, requires explicit typed `ROTATE`, generates 48 RNG bytes locally, sends the value only on SSH stdin, places it on clipboard without printing, and validates the same public/loopback health gates after rotation. Manual restore commands use the protected predecessor path.

## Verification

- Live read-only Ionoge checks: both `caddy.service` and `riverview-comms5-oauth.service` active; the two relevant environment files have mode `0600`; client secret and proxy-key entries match between Caddy and OAuth; backend-hop credential exists only in Caddy; Caddy and OAuth units reference the intended files. No environment values were printed.
- `python3 -m unittest tests.test_comms5_steward_credential -v`: 8 passed.
- `PYTHONPATH=src python3 -m unittest tests.test_comms5_mcp tests.test_comms5_deployment -v`: 9 passed.
- `python3 scripts/process_graph.py validate`: 22 graphs, PASS.
- `python3 scripts/process_graph.py check`: 22 graphs, 539 nodes, PASS.
- `python3 scripts/revision_control.py --root . check --baseline /tmp/rv-comms5-credential-baseline.json`: PASS, zero issues.
- `python3 -m py_compile scripts/rotate_comms5_steward_credential.py`: PASS.

No production environment file, OAuth/Caddy service, database, token store, grant, or credential was changed. The helper was installed and its read-only preflight passed. No credential rotation was performed; the script will stop before rotation unless the operator enters `ROTATE` after explicit Steward approval. The operator must confirm any direct static-bearer client use before proceeding.
