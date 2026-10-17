<!--
Riverview Controlled Document
File: docs/operations/RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md
Component: COMMS5-OAUTH-IONOGE
File Revision: 1.0.6
Status: Verified machine connection and recovery runbook
Date: 2026-10-17
Purpose: Record nonsecret Camrui/Ionoge Comms5 connectivity, health checks, and recovery evidence.
Changed: 2026-10-17 UTC | RV-COMMS5-OAUTH-FORWARD-HEADERS-001 | Record byte-level equality between deployed Comms5 Caddy block and source template.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-001 | Document credential purpose, consumers, provenance limitation and safe rotation.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-CREDENTIAL-002 | Record direct-bearer inventory limits, live utility preflight and guarded operator command.
Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-ROTATION-HEALTH-REPAIR | Document bounded post-restart readiness and corrected Windows launcher paths/target.
Changed: 2026-10-17 UTC | RV-CAMRUI-EXECUTION-ENVIRONMENT-001 | Confirm Windows alias operation and distinguish it from local Camrui Linux execution.
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

## Verified Windows SSH and Linux execution context — 2026-10-17

The Windows development workstation's existing OpenSSH alias and identity were verified headlessly:

```powershell
ssh.exe -o BatchMode=yes camrui "hostname; whoami; pwd"
```

It returned hostname `admin1-Default-string`, account `admin1`, directory `/home/admin1`, and exit code `0`. The Windows alias and its configured key remain the working Windows access path; the private key is not copied into this Linux environment.

The Codex Linux execution shell for this campaign is itself Camrui (`admin1-Default-string`, `admin1`, `/home/admin1`, local address `192.168.1.155`). Local systemd, loopback services, and checkouts are therefore accessed directly from that shell. The attempted `ssh camrui` from Linux failed at alias/name resolution because this Linux environment does not contain the Windows-only alias configuration; that was not an SSH authentication failure or a Camrui server fault. Run `ssh.exe -G camrui` in Windows PowerShell to inspect effective Windows mapping without exposing private-key contents. See the historical repository's `docs/operations/network/RIVERVIEW_SSH_STANDARD.md` for the client-side standard and diagnosis sequence.

## What the OAuth page means by “Steward credential”

The authorization form validates the submitted string against `RIVERVIEW_COMMS5_CLIENT_SECRET`. The OAuth service reads this from `/etc/riverview/comms5-oauth.env`; Caddy reads the same-named value from `/etc/caddy/riverview-comms5.env` as its legacy Comms5 bearer. For the OAuth form, Caddy forwards the request to the loopback OAuth service with the separate `RIVERVIEW_COMMS5_OAUTH_PROXY_KEY`. The OAuth code compares the submitted value in constant time. A successful check issues an OAuth authorization code and maps the resulting OAuth subject to `steward`; the page is not asking for the dashboard login credential, a PostgreSQL password, an OAuth client secret, or an SSH key. Historical source `ppow1/Riverview` at `08c1162c4ad04a21df71ed7814a3e22bd9ba41a2` describes this variable as the Steward-controlled Comms5 connector bearer in `config/riverview-comms5-ingress.Caddyfile.example` and `docs/operations/RIVERVIEW_COMMS5_DEPLOYMENT.md`. This proves the intended credential owner predates the current OAuth page, but it does not prove that the live secret bytes were carried forward from that earlier installation.

The same value is accepted as the legacy static bearer on Caddy’s `/comms5/mcp` route, which Caddy forwards as principal `steward`. Consequently, replacing it affects new OAuth logins and any direct Comms5 client still configured with the legacy bearer. Existing OAuth tokens are stored separately in OAuth state and are not the same value. The separate `RIVERVIEW_COMMS5_OAUTH_PROXY_KEY` authenticates the trusted Caddy-to-OAuth authorization hop. `RIVERVIEW_COMMS5_UPSTREAM_AUTH` is the distinct Caddy-to-Camrui backend credential.

### Direct-bearer client inventory before rotation

The live ingress has one shared static-bearer matcher on `/comms5/mcp`; Caddy has no access-log directive for this route, and the MCP backend does not maintain a named direct-bearer client registry. Read-only inspection of the OAuth SQLite state found 11 dynamic OAuth client registrations: one named `ChatGPT` and ten commissioning/diagnostic clients. These are OAuth client registrations, not evidence of callers using the Steward static bearer. The stored OAuth token records are separate and do not identify static-bearer callers. Therefore, server-side evidence cannot enumerate all existing direct-bearer clients. Before rotation, the Steward should confirm whether any independently configured client uses the old static bearer and arrange its update; otherwise that client will lose access. No access log or credential value was inspected or disclosed for this inventory.

Read-only live inspection on 2026-10-17 confirmed both client-secret environment entries exist, are equal, and are in root-owned mode-0600 files. Filesystem birth times are 2026-10-17 04:16 UTC, during the current OAuth commissioning window. The available deployment records do not contain an issuance record, entropy-generation record, or confirmation that the secret was delivered to the Steward. Therefore the live value was installed during OAuth commissioning, but whether it was newly generated or copied from an earlier Steward-held Comms5 bearer, and whether the operator received it, are **unverified**. Treat it as not yet explicitly provisioned to the operator. The inspection did not read the value into output, logs, or this record.

### Establish or replace the operator-held credential

The guarded utility `scripts/rotate_comms5_steward_credential.py` is the supported procedure. It has a read-only `--check` mode and an explicit `--install-from-stdin` mode. It accepts only a 43–128 character base64url value through stdin (never an argument or environment variable); the documented operator command generates 48 cryptographically random bytes. It requires the two existing entries to match, confirms the service environment-file wiring and protected file modes, creates a root-only predecessor backup, atomically updates only the two Comms5 client-secret entries, then restarts only `riverview-comms5-oauth.service` and `caddy.service`. After restart it retries service-active and endpoint checks within one shared 15-second readiness deadline. Expected responses remain 200 for OAuth health and authorization-server discovery, and 401 for anonymous MCP. Deadline errors identify the check with a sanitized stable ID; raw command output is not emitted. A failure restores both protected predecessor files atomically and retries service recovery within the same bounded window. It never emits the replacement value. Unit coverage is in `tests/test_comms5_steward_credential.py`.

The utility was merged in PR #86 at `a094297b67a9bd5e4ea3c74c284382c3e75845be`, then installed on Ionoge at `/usr/local/sbin/rotate_comms5_steward_credential.py` as `root:root` mode `0755`. Its SHA-256 is `9910a03d74c538466d36888950a3186d77e6362ced45125fc26dac77b0458224`. The live read-only `--check` passed. The Caddy and OAuth services were active; loopback Comms5 and OAuth health plus both public OAuth metadata URLs returned HTTP 200; anonymous public MCP returned HTTP 401. No service was restarted and no credential was changed.

Use this single Windows PowerShell 5.1 command only after the Steward has approved the credential rotation. The script resolves the checkout root as the parent of its `scripts` directory, verifies the local utility hash, installs the exact helper only if absent (and refuses to replace a different installed version), runs read-only preflight and service checks, then pauses for the exact text `ROTATE`. Typing anything else ends without changing the credential. SSH and SCP target the verified `root@64.227.21.54` address directly with strict host-key checking, using the already trusted `64.227.21.54` known-host entry rather than relying on an alias. On approval, it generates 48 random bytes locally, streams the base64url value through SSH stdin, leaves the value only on the Windows clipboard, and prints no secret. Successful rotation restarts only the Comms5 OAuth and Caddy services. Complete the OAuth browser login and then clear the clipboard with `Set-Clipboard -Value ''`.

```powershell
& 'A:\Riverview-New-Core\scripts\Invoke-RiverviewComms5StewardCredentialRotation.ps1'
```

The helper’s sanitized JSON includes the protected backup directory and recovery disposition; it never emits the new value. If utility rollback reports that predecessor files were restored but service recovery is unverified, inspect its reported state and perform the recovery below. Never restore from an unverified or unrelated backup.

Manual recovery, only if the utility explicitly reports that automatic service recovery is unverified:

```sh
BACKUP_DIR='/var/backups/riverview/comms5-steward-credential-<UTC timestamp>'
sudo python3 - "$BACKUP_DIR" <<'PY'
import hashlib, json, pathlib, sys
root=pathlib.Path(sys.argv[1])
manifest=json.loads((root/'manifest.json').read_text())
for name, original in (('caddy.env','/etc/caddy/riverview-comms5.env'),('oauth.env','/etc/riverview/comms5-oauth.env')):
    digest=hashlib.sha256((root/name).read_bytes()).hexdigest()
    assert digest == manifest['files'][original], 'predecessor checksum mismatch: '+name
print('protected predecessors verified')
PY
sudo install -o root -g root -m 0600 "$BACKUP_DIR/caddy.env" /etc/caddy/riverview-comms5.env
sudo install -o root -g root -m 0600 "$BACKUP_DIR/oauth.env" /etc/riverview/comms5-oauth.env
sudo systemctl restart riverview-comms5-oauth.service caddy.service
sudo systemctl is-active riverview-comms5-oauth.service caddy.service
curl -fsS http://127.0.0.1:11827/healthz -o /dev/null
curl -fsS http://127.0.0.1:11826/healthz -o /dev/null
curl -fsS https://riverview-comms.ionoge.com/.well-known/oauth-authorization-server -o /dev/null
test "$(curl -sS -o /dev/null -w '%{http_code}' https://riverview-comms.ionoge.com/comms5/mcp)" = 401
```

This restore returns both settings to the protected predecessor, including the previous shared login/static-bearer value. It does not alter Comms4, the tunnel, Camrui, or OAuth token state.

For a no-change inspection, run `sudo python3 /usr/local/sbin/rotate_comms5_steward_credential.py --check`. Do not use `systemctl show -p Environment`, `cat` the environment files, pass the credential on a command line, place it in shell history, or send it in chat/email.

## 2026-10-17 commissioning record

- Camrui tunnel was verified active/running/enabled before this session. Ionoge's `127.0.0.1:11826/healthz` returned HTTP 200 and identified `riverview-comms5-camrui`.
- Ionoge OAuth was active on `127.0.0.1:11827`; public OAuth authorization-server and protected-resource metadata returned 200. Public health returned 200. The live OAuth route requires authentication for MCP.
- Caddy predecessor backup: `/var/backups/riverview/comms5-oauth-marker-fix-20261017T114013Z/Caddyfile`, SHA-256 `da1490f09427831aca79329d365a09f1c610e9792ba112a8929a7ca31202d97c`. The full candidate validated before activation. Active Caddyfile SHA-256 after route correction: `281697476349885c7e075c5d2effe045a7d129ac08e973c6a2265fd5406f2d69`. After aligning the embedded fragment revision comment with the checked-in source, the final active Caddyfile SHA-256 is `e0440931f4be47d35e6bb51ee4c4940efc896c7f6cb1fc57d150e7382006873f`. The metadata-only update backup is `/var/backups/riverview/comms5-oauth-source-revision-20261017T114645Z/Caddyfile`. Caddy active after reload with `NRestarts=0`. The active Comms5 block body byte-matches the checked-in fragment after its metadata header; both SHA-256 values are `f0cbd327e5feda7d65833fded3cdf1a3f8bf8cecd0552ce588085b45e9985867`.
- OAuth acceptance through the real public HTTPS route: dynamic client registration 201; login page 200; credential authorization 302 and OAuth state matched; authorization code exchanged using PKCE S256 for a token bound to the exact resource; MCP initialize 200, initialized notification 202, tools/list 200 with 21 entries, and read-only `comms5_contract_info` returned contract `riverview-comms-contract:5.0`. Refresh-token revocation returned 200; unauthenticated and revoked requests returned 401. No credentials, authorization codes, or access/refresh tokens were logged or included here.
- OAuth unit restart preserved a previously registered test client. Once `/healthz` returned 200, that persisted client completed the same authorization/MCP exchange. A probe immediately in the startup gap returned 502; subsequent readiness-gated verification passed.
- 2026-10-17 18:07 UTC: after PR #86 merge, the exact merged helper was installed to `/usr/local/sbin/rotate_comms5_steward_credential.py`, SHA-256 verified, owner/mode `root:root/0755`. `--check` returned PASS. Caddy/OAuth units were active; Camrui backend health, OAuth loopback health, public authorization-server metadata, public protected-resource metadata returned 200; anonymous MCP returned 401. Installation created no configuration changes and restarted no service. Credential rotation remains unperformed.
- 2026-10-17 rotation health repair: a later operator rotation attempt restarted OAuth and Caddy, failed post-restart validation, and restored both credential files byte-for-byte from the protected predecessor. The exact failed probe was not preserved, so the incident cause remains unconfirmed. A separate earlier restart record demonstrated a transient public HTTP 502 before OAuth loopback health became 200; this establishes that a readiness race is possible but does not prove it caused the rotation failure. Development correction adds one shared 15-second readiness window and stable sanitized check IDs. It has not been deployed or used to rotate production credentials.
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
