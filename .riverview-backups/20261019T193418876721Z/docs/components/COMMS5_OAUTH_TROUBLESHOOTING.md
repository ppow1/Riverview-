<!--
Riverview Controlled Document
File: docs/components/COMMS5_OAUTH_TROUBLESHOOTING.md
Component: COMMS5-OAUTH-IONOGE
File Revision: 1.0.4
Status: Operational troubleshooting record
Date: 2026-10-17
Purpose: Diagnose and recover Comms5 OAuth-to-Camrui authenticated MCP forwarding.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Record verified principal/marker defect, recovery, and acceptance evidence.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-001 | Explain authorization credential dependencies and guarded rotation.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-002 | Record direct-bearer inventory limits and verified helper preflight.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-ROTATION-HEALTH-REPAIR | Record bounded readiness retries, sanitized failure IDs, and incident-cause limitation.
History: New file; no predecessor existed.
Authority: Existing OAuth and Steward authority boundaries; no grant changes.
-->

# Comms5 OAuth and authenticated forwarding troubleshooting

## Symptom and cause

OAuth discovery, login, PKCE exchange, and `/oauth/verify` succeeded, but `POST /comms5/mcp` with the issued access token returned HTTP 401 from the Camrui adapter. A successful OAuth verification returned `X-Riverview-Comms5-Principal: steward`. The backend requires that principal, `X-Riverview-Comms5: 1`, and the protected hop bearer.

The Caddy OAuth fallback contained both `header_up -X-Riverview-Comms5` and `header_up X-Riverview-Comms5 1`. The installed Caddy adaptation retained the delete and dropped the marker before proxying, so the backend rejected the request. A loopback-only isolated Caddy/HTTP fixture reproduced this: OAuth principal arrived as `steward`, Authorization was present, and the deleted/set marker arrived absent. Removing only the delete directive made the marker arrive as `1`.

## Corrective procedure

1. Back up the live `/etc/caddy/Caddyfile`, record SHA-256, and verify the backup before editing.
2. Remove only the OAuth fallback's marker deletion. Keep `header_up X-Riverview-Comms5 1`; it overwrites client-supplied values. Keep `copy_headers X-Riverview-Comms5-Principal` under successful `forward_auth`. Keep the legacy static-bearer route unchanged.
3. Preserve Caddyfile ownership/mode when installing a candidate. The file was accidentally staged at `0640`, which prevented the unprivileged Caddy reload process from reading it. Caddy remained active and `NRestarts=0`; restore metadata from the preserved predecessor (this host: `root:root 0644`).
4. Validate the complete Caddyfile with the same protected `EnvironmentFile` set used by `caddy.service`, then reload Caddy. Never print environment values.
5. Poll OAuth loopback `/healthz` after an OAuth service restart before probing the public path. A request during the brief listener startup gap can return 502; verify recovery by health/discovery rather than treating systemd `active` alone as readiness.
6. Run DCR, authorization-code + PKCE S256, resource-bound token exchange, MCP initialize, `tools/list`, and one implemented read-only tool call. Revoke the issued refresh token and confirm unauthenticated and revoked access return 401.

## 2026-10-17 verification record

- Candidate and full live Caddy configuration validated. Caddyfile predecessor backup: `/var/backups/riverview/comms5-oauth-marker-fix-20261017T114013Z/Caddyfile`; predecessor SHA-256 `da1490f09427831aca79329d365a09f1c610e9792ba112a8929a7ca31202d97c`. Final live Caddyfile SHA-256 is recorded in the dated machine-connection runbook.
- Caddy reload succeeded after restoring original file mode. Caddy active; no restart (`NRestarts=0`). Public health/discovery/resource metadata returned 200; unauthenticated `/mcp` and `/comms5/mcp` returned 401.
- Real HTTPS PKCE harness: DCR 201; authorization page 200; credential submission 302 with verified state; token exchange 200 bound to the exact MCP resource. MCP initialize 200 (`2025-11-25`); initialized notification 202; tools/list 200 with 21 tools; `comms5_contract_info` returned `riverview-comms-contract:5.0`; token family revoked 200; revoked and unauthenticated calls returned 401. The test did not log credentials, codes, or tokens.
- OAuth unit restart preserved a DCR client created before restart. The first public discovery probe immediately after `systemctl restart` saw 502 before the new loopback listener was ready; loopback `/healthz` then returned 200, and the persisted-client authorization and full MCP tool test passed.
- Controlled reverse SSH disconnect/reconnect: terminated only the sshd process owning Ionoge's `127.0.0.1:11826` forward; the listener and Camrui `/healthz` recovered in 6 seconds. No inference/model services were touched.
- Comms4 `/mcp` route is unchanged and unauthenticated access returns 401. An authenticated `ping` returned 502 because no process currently listens on Ionoge `127.0.0.1:11825`. This is an unresolved upstream availability issue, not changed by the Comms5 route correction.
- ChatGPT account-side connector sign-in/invocation remains unverified; the protocol acceptance used a test client against the actual public HTTPS services.

## Fast read-only checks

```sh
systemctl is-active caddy riverview-comms5-oauth.service
curl -fsS https://riverview-comms.ionoge.com/.well-known/oauth-authorization-server >/dev/null
curl -fsS https://riverview-comms.ionoge.com/.well-known/oauth-protected-resource >/dev/null
curl -fsS http://127.0.0.1:11826/healthz
ss -ltnp | grep -E '127.0.0.1:11826|127.0.0.1:11827'
```

For a blocked authenticated MCP call, inspect the Caddy adapted route without emitting environment values. The OAuth-to-backend proxy headers must have a set for marker `1`, no delete for that marker, and a principal copied from the successful OAuth `/oauth/verify` response. Keep OAuth `/oauth/verify` loopback-only.

## Steward credential diagnosis and rotation

The authorization page’s “Steward credential” is `RIVERVIEW_COMMS5_CLIENT_SECRET`, read by the OAuth service and compared in constant time. The same value is used by Caddy as the direct legacy Comms5 bearer, so rotation also invalidates any direct client using that bearer. It is not the internal OAuth proxy key, backend upstream credential, dashboard credential, or OAuth-issued token. Live files and service wiring were inspected without disclosing their values; their owner/mode were root:root/0600 and the two client-secret entries matched.

No deployment record identifies who generated the currently installed value, whether it reused an earlier Comms5 bearer, or whether it was handed to the Steward. Treat operator custody as unverified. The selected remediation is to establish a fresh operator-held value with the reviewed utility, rather than to expose the current secret through logs or chat.

Read-only inventory found 11 OAuth DCR records (including one named ChatGPT and commissioning/diagnostic clients), which do not identify direct static-bearer callers. The Caddy Comms5 route has no access-log directive, and no server-side registry records direct-bearer client identities. External direct-bearer usage therefore remains unenumerated; have the Steward confirm/update any such clients before rotating.

Read-only check after the utility is installed:

```sh
sudo python3 /usr/local/sbin/rotate_comms5_steward_credential.py --check
```

The helper was installed from merged PR #86 at `/usr/local/sbin/rotate_comms5_steward_credential.py` (SHA-256 `9910a03d74c538466d36888950a3186d77e6362ced45125fc26dac77b0458224`, root:root/0755). On 2026-10-17 its read-only `--check` passed against live systemd wiring and protected files; service health/discovery and unauthenticated 401 checks also passed. No credential was rotated and no service was restarted.

### Rotation post-restart readiness failure

The first rotation attempt restarted OAuth and Caddy, failed post-restart validation, and restored both credential files byte-for-byte from the protected predecessor. Available incident evidence does not identify which validation failed or establish its timestamp, so the historical failure cause remains **unconfirmed**. The prior 2026-10-17 OAuth restart record independently shows that an immediate public probe can race listener startup: it returned 502 before loopback `/healthz` became 200, after which discovery and MCP checks passed. This proves a readiness-timing failure is possible, not that it caused the rotation incident.

The corrected helper retries each post-restart readiness check within one shared 15-second monotonic deadline. It preserves expected HTTP responses: loopback OAuth health 200, public authorization-server discovery 200, and unauthenticated Comms5 MCP 401. Service-active checks are included in the same deadline. If the deadline expires, sanitized output identifies only the failed check, for example `readiness_deadline_exceeded:oauth_loopback_health_200`; raw curl/systemd output is not included. Rotation then restores both protected predecessor files atomically and performs the same bounded service recovery checks. `predecessor_restored` means those checks passed; `predecessor_files_restored_service_recovery_unverified` requires the documented operator recovery. No production rotation or service restart was performed for this code correction.

Check IDs are `oauth_service_active`, `caddy_service_active`, `oauth_loopback_health_200`, `oauth_public_discovery_200`, and `mcp_anonymous_rejected_401`. Restart command failures identify the service unit separately and do not enter the readiness retry window.

Use the single Windows PowerShell 5.1 operator script documented in the machine-connection runbook. It verifies the exact helper hash and live service readiness, then requires the exact text `ROTATE` before generation and installation. It streams the new value over strict-host-verified SSH, leaves it only on the operator clipboard, and prints no secret. The utility validates both service environment-file references, refuses mismatched/duplicated entries, writes protected predecessors, atomically updates only the shared client-secret setting, and restarts only OAuth and Caddy. Post-restart checks use the 15-second bounded readiness contract above. Complete OAuth in the browser using the clipboard and clear it. See the runbook for manual predecessor recovery if automatic service recovery is unverified.
## External reasoning review tools in the existing Comms5 connector

The Comms5 tool list should expose 25 entries after refreshing the existing connector catalog. The four `reasoning_exchange_*` tools are authorized by the established Steward Comms5 identity on the existing internal route. They are not external-provider OAuth operations. Provider OAuth tokens continue to work only against the provider-scoped four-tool MCP adapter.

If the tools are absent, refresh or re-register the existing Comms5 connector from the current catalog; do not add a second ChatGPT MCP app or public route. If listing works but an operation returns `BACKEND_UNAVAILABLE`, inspect dashboard startup logs for the sanitized `comms5_steward_review_exchange_unavailable` marker and verify that the existing exchange migrations and runtime ACLs are present. If an operation returns `NOT_AUTHORIZED`, inspect the existing ingress identity mapping; do not pass a principal in tool arguments or widen grants. Correlation, lease/fence, expiry, and exact review-subject digest errors require the caller to resume or re-read the durable request.
