<!--
Riverview Controlled Document
File: docs/operations/RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md
Component: COMMS5-OAUTH-IONOGE
File Revision: 1.0.3
Status: Verified machine connection and recovery runbook
Date: 2026-10-17
Purpose: Record nonsecret Camrui/Ionoge Comms5 connectivity, health checks, and recovery evidence.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Record byte-level equality between deployed Comms5 Caddy block and source template.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-001 | Document credential purpose, consumers, provenance limitation and safe rotation.
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

## What the OAuth page means by “Steward credential”

The authorization form validates the submitted string against `RIVERVIEW_COMMS5_CLIENT_SECRET`. The OAuth service reads this from `/etc/riverview/comms5-oauth.env`; Caddy reads the same-named value from `/etc/caddy/riverview-comms5.env` as its legacy Comms5 bearer. For the OAuth form, Caddy forwards the request to the loopback OAuth service with the separate `RIVERVIEW_COMMS5_OAUTH_PROXY_KEY`. The OAuth code compares the submitted value in constant time. A successful check issues an OAuth authorization code and maps the resulting OAuth subject to `steward`; the page is not asking for the dashboard login credential, a PostgreSQL password, an OAuth client secret, or an SSH key. Historical source `ppow1/Riverview` at `08c1162c4ad04a21df71ed7814a3e22bd9ba41a2` describes this variable as the Steward-controlled Comms5 connector bearer in `config/riverview-comms5-ingress.Caddyfile.example` and `docs/operations/RIVERVIEW_COMMS5_DEPLOYMENT.md`. This proves the intended credential owner predates the current OAuth page, but it does not prove that the live secret bytes were carried forward from that earlier installation.

The same value is accepted as the legacy static bearer on Caddy’s `/comms5/mcp` route, which Caddy forwards as principal `steward`. Consequently, replacing it affects new OAuth logins and any direct Comms5 client still configured with the legacy bearer. Existing OAuth tokens are stored separately in OAuth state and are not the same value; no claim is made that every external static-bearer consumer has been inventoried. The separate `RIVERVIEW_COMMS5_OAUTH_PROXY_KEY` authenticates the trusted Caddy-to-OAuth authorization hop. `RIVERVIEW_COMMS5_UPSTREAM_AUTH` is the distinct Caddy-to-Camrui backend credential.

Read-only live inspection on 2026-10-17 confirmed both client-secret environment entries exist, are equal, and are in root-owned mode-0600 files. Filesystem birth times are 2026-10-17 04:16 UTC, during the current OAuth commissioning window. The available deployment records do not contain an issuance record, entropy-generation record, or confirmation that the secret was delivered to the Steward. Therefore the live value was installed during OAuth commissioning, but whether it was newly generated or copied from an earlier Steward-held Comms5 bearer, and whether the operator received it, are **unverified**. Treat it as not yet explicitly provisioned to the operator. The inspection did not read the value into output, logs, or this record.

### Establish or replace the operator-held credential

The guarded utility `scripts/rotate_comms5_steward_credential.py` is the supported procedure. It has a read-only `--check` mode and an explicit `--install-from-stdin` mode. It accepts only a 43–128 character base64url value through stdin (never an argument or environment variable); the documented operator command generates 48 cryptographically random bytes. It requires the two existing entries to match, confirms the service environment-file wiring and protected file modes, creates a root-only predecessor backup, atomically updates only the two Comms5 client-secret entries, then restarts only `riverview-comms5-oauth.service` and `caddy.service`. It checks OAuth health/discovery and confirms anonymous MCP remains HTTP 401. A failure restores the predecessor files and attempts to restore service health. It never emits the replacement value. Unit coverage is in `tests/test_comms5_steward_credential.py`.

After this utility is merged, install it from the reviewed checkout with Windows PowerShell 5.1. This copies only the public utility source, not a credential, and runs its read-only preflight:

```powershell
Clear-Host
$RepoRoot = 'A:\Riverview-New-Core'
scp "$RepoRoot\scripts\rotate_comms5_steward_credential.py" ionoge-control-01:/tmp/rotate_comms5_steward_credential.py
$CopyExit = $LASTEXITCODE
if ($CopyExit -eq 0) {
    ssh -T ionoge-control-01 'install -o root -g root -m 0755 /tmp/rotate_comms5_steward_credential.py /usr/local/sbin/rotate_comms5_steward_credential.py && rm -f /tmp/rotate_comms5_steward_credential.py && python3 /usr/local/sbin/rotate_comms5_steward_credential.py --check'
    $CheckExit = $LASTEXITCODE
}
if ($CopyExit -ne 0) {
    $Report = 'Utility transfer failed; no production credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
}
if (($CopyExit -eq 0) -and ($CheckExit -eq 0)) {
    $Report = 'Read-only credential preflight passed. The utility is installed; no production credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
}
if (($CopyExit -eq 0) -and ($CheckExit -ne 0)) {
    $Report = 'Credential preflight failed; no production credential was changed. Keep the result sanitized and diagnose before rotation.'
    $Report | Set-Clipboard
    Write-Host $Report
}
```

After preflight, the operator can generate a fresh value locally, stream it to Ionoge over that trusted SSH connection, and retain it only in the local PowerShell variable/clipboard for the browser form. The following does not print the value:

```powershell
Clear-Host
$Bytes = New-Object byte[] 48
$Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$Rng.GetBytes($Bytes)
$Credential = [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
$Credential | ssh -T ionoge-control-01 'python3 /usr/local/sbin/rotate_comms5_steward_credential.py --install-from-stdin'
$InstallExit = $LASTEXITCODE
if ($InstallExit -eq 0) {
    $Credential | Set-Clipboard
    $Report = "Comms5 credential installed. Paste the clipboard value into the HTTPS Steward credential field, complete OAuth, then clear the clipboard with Set-Clipboard -Value ''. The value was not printed."
    Write-Host $Report
}
if ($InstallExit -ne 0) {
    $Report = "Credential rotation failed or rolled back. Do not retry blindly; inspect the sanitized utility result and service health. The value was not printed."
    Write-Host $Report
}
$Credential = $null
$Bytes = $null
$Rng.Dispose()
```

Run the command only after installing the reviewed utility. The program’s JSON result reports a protected backup path and whether predecessor recovery succeeded, never the secret. The operator should complete the browser login, then clear the clipboard. If any direct static-bearer Comms5 consumer exists, update that client through its own protected credential procedure; do not silently preserve the old value in another service. This is a credential rotation and causes a brief restart of Caddy and the OAuth unit. It does not alter Comms4, the tunnel, Camrui, or OAuth token state.

For a no-change inspection, run `sudo python3 /usr/local/sbin/rotate_comms5_steward_credential.py --check`. Do not use `systemctl show -p Environment`, `cat` the environment files, pass the credential on a command line, place it in shell history, or send it in chat/email.

## 2026-10-17 commissioning record

- Camrui tunnel was verified active/running/enabled before this session. Ionoge's `127.0.0.1:11826/healthz` returned HTTP 200 and identified `riverview-comms5-camrui`.
- Ionoge OAuth was active on `127.0.0.1:11827`; public OAuth authorization-server and protected-resource metadata returned 200. Public health returned 200. The live OAuth route requires authentication for MCP.
- Caddy predecessor backup: `/var/backups/riverview/comms5-oauth-marker-fix-20261017T114013Z/Caddyfile`, SHA-256 `da1490f09427831aca79329d365a09f1c610e9792ba112a8929a7ca31202d97c`. The full candidate validated before activation. Active Caddyfile SHA-256 after route correction: `281697476349885c7e075c5d2effe045a7d129ac08e973c6a2265fd5406f2d69`. After aligning the embedded fragment revision comment with the checked-in source, the final active Caddyfile SHA-256 is `e0440931f4be47d35e6bb51ee4c4940efc896c7f6cb1fc57d150e7382006873f`. The metadata-only update backup is `/var/backups/riverview/comms5-oauth-source-revision-20261017T114645Z/Caddyfile`. Caddy active after reload with `NRestarts=0`. The active Comms5 block body byte-matches the checked-in fragment after its metadata header; both SHA-256 values are `f0cbd327e5feda7d65833fded3cdf1a3f8bf8cecd0552ce588085b45e9985867`.
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
