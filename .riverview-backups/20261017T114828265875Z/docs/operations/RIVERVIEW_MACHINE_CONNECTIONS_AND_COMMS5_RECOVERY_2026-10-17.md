<!--
Riverview Controlled Document
File: docs/operations/RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md
Component: COMMS5-OAUTH-IONOGE
File Revision: 1.0.1
Status: Verified machine connection and recovery runbook
Date: 2026-10-17
Purpose: Record nonsecret Camrui/Ionoge Comms5 connectivity, health checks, and recovery evidence.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Record final live Caddyfile checksum and second configuration checkpoint.
History: New file; no predecessor existed in the integration checkout.
Authority: Existing service identities and grants; this document does not issue authority.
-->

# Riverview machine connections and Comms5 recovery

## Verified topology

```text
ChatGPT MCP client
  -> https://riverview-comms.ionoge.com/comms5/mcp (Caddy/TLS)
  -> OAuth authorization service, Ionoge loopback 127.0.0.1:11827
  -> Caddy forward_auth validates the resource-bound token and copies its principal
  -> restricted reverse SSH listener, Ionoge 127.0.0.1:11826
  -> Comms5 adapter, Camrui loopback 127.0.0.1:11826
```

Ionoge is `ionoge-control-01` at `64.227.21.54`. Comms5 public issuer is `https://riverview-comms.ionoge.com`; MCP resource is `https://riverview-comms.ionoge.com/comms5/mcp`. OAuth routes are on the same HTTPS host. The adapter and OAuth listeners remain loopback-only.

Camrui units: `riverview-comms5-camrui.service` and `riverview-comms5-tunnel.service`. Ionoge units: `riverview-comms5-oauth.service` and `caddy.service`. The reverse tunnel uses the dedicated restricted key and pinned host key delivered to the Camrui service with systemd credentials; SSH uses strict host-key checking and a remote forward bound only to `127.0.0.1:11826`. Do not copy, print, or rotate credentials as routine recovery.

## 2026-10-17 commissioning record

- Camrui tunnel was verified active/running/enabled before this session. Ionoge's `127.0.0.1:11826/healthz` returned HTTP 200 and identified `riverview-comms5-camrui`.
- Ionoge OAuth was active on `127.0.0.1:11827`; public OAuth authorization-server and protected-resource metadata returned 200. Public health returned 200. The live OAuth route requires authentication for MCP.
- Caddy predecessor backup: `/var/backups/riverview/comms5-oauth-marker-fix-20261017T114013Z/Caddyfile`, SHA-256 `da1490f09427831aca79329d365a09f1c610e9792ba112a8929a7ca31202d97c`. The full candidate validated before activation. Active Caddyfile SHA-256 after route correction: `281697476349885c7e075c5d2effe045a7d129ac08e973c6a2265fd5406f2d69`. After aligning the embedded fragment revision comment with the checked-in source, the final active Caddyfile SHA-256 is `e0440931f4be47d35e6bb51ee4c4940efc896c7f6cb1fc57d150e7382006873f`. The metadata-only update backup is `/var/backups/riverview/comms5-oauth-source-revision-20261017T114645Z/Caddyfile`. Caddy active after reload with `NRestarts=0`.
- OAuth acceptance through the real public HTTPS route: dynamic client registration 201; login page 200; credential authorization 302 and OAuth state matched; authorization code exchanged using PKCE S256 for a token bound to the exact resource; MCP initialize 200, initialized notification 202, tools/list 200 with 21 entries, and read-only `comms5_contract_info` returned contract `riverview-comms-contract:5.0`. Refresh-token revocation returned 200; unauthenticated and revoked requests returned 401. No credentials, authorization codes, or access/refresh tokens were logged or included here.
- OAuth unit restart preserved a previously registered test client. Once `/healthz` returned 200, that persisted client completed the same authorization/MCP exchange. A probe immediately in the startup gap returned 502; subsequent readiness-gated verification passed.
- Controlled reverse-tunnel reconnect: only the sshd child process owning Ionoge's `127.0.0.1:11826` listener was terminated. The tunnel reconnected and backend health returned 200 in 6 seconds. The Camrui model/inference services and other services were not touched.
- Comms4 remained configuration-isolated: the `/mcp` block was not edited; unauthenticated request returns 401. An authenticated MCP `ping` returns 502 because Ionoge has no listener on its configured upstream `127.0.0.1:11825`. Comms4 backend operation is not currently healthy/verified; restore its existing upstream separately.
- ChatGPT Plus UI registration and a tool invocation inside the account remain unverified. The protocol test was an authenticated external HTTPS harness against the actual public service, not a ChatGPT session.

## Health and recovery checks

On Ionoge, run without printing environment-file contents:

```sh
systemctl is-active caddy riverview-comms5-oauth.service
curl -fsS http://127.0.0.1:11827/healthz
curl -fsS https://riverview-comms.ionoge.com/.well-known/oauth-authorization-server
curl -fsS https://riverview-comms.ionoge.com/.well-known/oauth-protected-resource
curl -fsS http://127.0.0.1:11826/healthz
ss -ltnp | grep -E '127.0.0.1:11826|127.0.0.1:11827'
```

On Camrui, verify the two unit states with `systemctl is-active riverview-comms5-camrui.service riverview-comms5-tunnel.service` and check local adapter health. If the tunnel drops, allow its systemd restart policy to reconnect, then poll Ionoge `http://127.0.0.1:11826/healthz`; do not kill/restart sshd globally. A controlled reconnect test recovered in 6 seconds on 2026-10-17.

The Comms4 health issue is different: inspect only the existing Comms4 upstream and its owner before any repair. Do not repoint Comms4 to the Comms5 service.

## Rollback

For a Caddy-only rollback, restore the preserved `Caddyfile` predecessor and its metadata, validate with the Caddy service's existing protected EnvironmentFiles, then reload Caddy. Do not restart unrelated services. The correction touched only the Comms5 OAuth fallback header. Keep OAuth SQLite state and both SSH authorized-key backups. If a future Comms5 change fails, restore only this Caddyfile and reload; the Camrui adapter and tunnel are independently managed.
