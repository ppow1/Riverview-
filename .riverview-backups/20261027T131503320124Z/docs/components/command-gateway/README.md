<!-- Document Revision: 1.1.2 -->

# Riverview Command Gateway

The Gateway exposes fixed diagnostic probes and two task-specific command tools
through the existing authenticated Comms5 and Windows agent path. The fixed
diagnostic operations remain:

| Operation | Fixed target | Privilege | Effect |
| --- | --- | --- | --- |
| `powershell_identity` | `DESKTOP-JA3RPNQ` | Standard user | Returns the computer name and PowerShell version. |
| `ssh_camrui_hostname` | `camrui` | Standard user | Runs the fixed remote `hostname` probe using Windows OpenSSH. |

Task commands are accepted only by `comms5_command_task_submit`; the host ID
selects a fixed PowerShell or SSH transport. The Gateway never accepts caller
selected addresses, usernames, executable paths, or credentials. Host-scoped
grants separately authorize standard or elevated execution. Windows elevated
execution is not implemented until its OS privilege boundary is commissioned.

## Authorization and audit

The authenticated Comms5 transport supplies the caller identity. Before an
execution, the dashboard checks the caller's active exact grant through the
existing `ExactGrantAuthorizer` and AuthorityRegistry. It then reserves one use
from the existing delegated-grant lifecycle for the `service:command-gateway`
principal. The reservation binds the exact operation, host scope, expiry, and
execution allowance. A denied or unavailable authority check prevents dispatch.

Required grant pairs are:

| Caller action | Execution action | Scope |
| --- | --- | --- |
| `comms5.command.submit.powershell_identity` | `comms5.command.execute.readonly.powershell_identity.standard` | `host:desktop-ja3rpnq` |
| `comms5.command.submit.ssh_camrui_hostname` | `comms5.command.execute.readonly.ssh_camrui_hostname.standard` | `host:camrui` |

The caller grant is issued to the authenticated Steward principal. The delegated
execution grant is issued to `service:command-gateway` and must have a finite use
limit, an expiry, or both. The tool call supplies its grant ID; the gateway
credential that reserves the grant is loaded only by systemd as a credential.
Do not create or approve grants from a ChatGPT tool call. Use the existing
Steward-controlled AuthorityRegistry grant process.

The execution grant is checked when its use is reserved and again directly
before HTTPS dispatch. Revocation or expiry before dispatch releases the
reservation and denies the call. Once the agent accepts the durable task, the
grant use is consumed. Later revocation does not rewrite that audit record or
silently terminate dispatched work; an authorized caller may request task
cancellation while it is queued or running.

Each result includes the caller and execution grant IDs, reservation ID,
execution ID, agent audit event ID, operation, host, privilege level, bounded
stdout/stderr, exit code, and lifecycle status. The Windows agent keeps a local
SQLite execution ledger and append-only event rows. That file contains execution
records, not authority data; AuthorityRegistry remains the sole authorization
source. Agent restart marks an unfinished execution `interrupted`.

The idempotency key is bound to caller, host, privilege class, and request
digest. Reusing an accepted key returns the same task and does not reserve or
consume another delegated use; changing the command or scope conflicts. A
connection failure after reservation is treated as an unknown dispatch
outcome; the reservation is not silently released.

## Comms5 examples

Submit the Windows identity probe:

```json
{
  "operation": "powershell_identity",
  "execution_grant_id": "<active delegated execution grant ID>",
  "idempotency_key": "acceptance-desktop-2026-10-26"
}
```

Submit the Camrui SSH hostname probe:

```json
{
  "operation": "ssh_camrui_hostname",
  "execution_grant_id": "<active delegated execution grant ID>",
  "idempotency_key": "acceptance-camrui-2026-10-26"
}
```

Read a result, including after a transport retry:

```json
{
  "operation": "powershell_identity",
  "idempotency_key": "acceptance-desktop-2026-10-26"
}
```

The response has `status`, `execution_id`, `stdout`, `stderr`, `exit_code`,
`authorization_evidence`, and `audit_evidence`. Command output is limited to
32 KiB per stream. Fixed diagnostic probes retain their 12-second process
deadline. Command tasks have a separate execution deadline: one hour by
default, configurable on the agent with
`RIVERVIEW_COMMAND_JOB_TIMEOUT_SECONDS` from 1 to 86,400 seconds. The agent
waits at most 2 seconds for an immediate result; if the task is still active,
submission returns `queued` or `running` with its durable `execution_id` and
`task_id`. The Dashboard gives `comms5_command_task_submit` a 25-second response
window, which exceeds the fixed probe deadline; all other Comms5 operations keep
their ordinary 3-second Dashboard timeout. The agent HTTPS timeout remains 20
seconds.

## Windows agent setup

C2 develops on Camrui/Linux. Install and commission the agent separately on
`DESKTOP-JA3RPNQ`:

1. Install Python 3.10 or newer and place the checked-out
   `src/riverview_core/comms5/command_gateway.py` plus
   `scripts/run_windows_command_agent.py` in a protected installation folder.
2. Run it as a dedicated, non-administrative Windows account. That account must
   have access to `powershell.exe`, the existing Windows OpenSSH configuration,
   and its pinned `known_hosts` entry for `camrui`. It must not receive local
   administrator rights.
3. Create `%ProgramData%\Riverview\CommandGateway` and grant access only to the
   agent account and local administrators. Put a random 32-byte-or-longer
   base64url agent bearer in `agent.token`; install a TLS certificate whose SAN
   is `desktop-ja3rpnq` and protect its private key with the same ACL.
4. Bind the HTTPS listener to the desktop's private LAN address on TCP 8443.
   Permit inbound traffic only from Camrui's private address. Do not expose the
   listener to the public network. Set `RIVERVIEW_COMMAND_AGENT_BIND` to that
   private address before starting the agent.
5. In the dashboard systemd credential directory, install the matching agent
   token, the issuing CA certificate, and the AuthorityRegistry credential for
   `service:command-gateway`. Install the optional systemd drop-in shown below.
   Configure `RIVERVIEW_COMMAND_AGENT_URL=https://desktop-ja3rpnq:8443`.
6. Provision the exact caller and finite execution grants through the existing
   Steward-authorized AuthorityRegistry process. Verify the grants are active,
   correctly scoped, and not expired before the first request.

The Windows agent's HTTPS bearer, server private key, SSH key, and known-hosts
file remain on their respective hosts. Comms5 inputs and outputs never contain
those credentials. Do not use `ssh.exe` with disabled host-key checking.

Optional Dashboard systemd drop-in (install only after all credential files
exist):

```ini
[Service]
LoadCredential=command-gateway-grantee:/etc/riverview/command-gateway/grantee.credential
LoadCredential=command-agent-token:/etc/riverview/command-gateway/agent.token
LoadCredential=command-agent-ca.pem:/etc/riverview/command-gateway/agent-ca.pem
Environment=RIVERVIEW_COMMAND_AGENT_URL=https://desktop-ja3rpnq:8443
```

Copy this example to
`/etc/systemd/system/riverview-status-dashboard.service.d/command-gateway.conf`,
then follow the existing authorized Dashboard deployment procedure. Do not
install the drop-in while any credential path is absent.

## Verification limits

Unit tests exercise schema validation, authorization ordering, exact target and
privilege derivation, use reservation/consumption, idempotency, output bounds,
timeouts, audit records, and caller-scoped result retrieval. They do not prove
that the Windows agent is installed, that the desktop certificate/network path
is ready, that grants exist in production, or that ChatGPT can complete a live
round trip. Record both live Comms5-to-agent results and the returned authority
and audit identifiers before claiming acceptance.

## Windows commissioning commands

This is a prepared runbook, not authorization to run it. The account, ACL,
firewall, certificate, and SSH-key steps change Windows or host security and
require their respective approvals. Fill the placeholders from approved
records. Do not put passwords, bearer tokens, SSH keys, or private-key contents
in command arguments or ChatGPT.

Run the installation shell as Administrator. Install Python from the approved
Windows package source (this command uses WinGet's Python 3.12 package):

```powershell
$ErrorActionPreference = 'Stop'
winget install --exact --id Python.Python.3.12 --scope machine --silent `
  --accept-package-agreements --accept-source-agreements
$Python = Join-Path $env:ProgramFiles 'Python312\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Python312 installation missing' }
& $Python --version
```

Verify and copy the approved source revision. `$ExpectedCommit` must name the
commit approved for commissioning; do not install from a moving branch.

```powershell
$SourceRoot = 'C:\Staging\Riverview'
$ExpectedCommit = '<approved-release-commit>'
$ActualCommit = (git -C $SourceRoot rev-parse HEAD).Trim()
if ($ActualCommit -ne $ExpectedCommit) { throw "Unexpected source revision: $ActualCommit" }
if ((Get-CimInstance Win32_ComputerSystem).Name -ne 'DESKTOP-JA3RPNQ') {
  throw 'This setup is only for DESKTOP-JA3RPNQ'
}
$InstallRoot = Join-Path $env:ProgramFiles 'Riverview\CommandGateway'
$PackageRoot = Join-Path $InstallRoot 'src\riverview_core'
$CommsRoot = Join-Path $PackageRoot 'comms5'
$ScriptsRoot = Join-Path $InstallRoot 'scripts'
New-Item -ItemType Directory -Force -Path $CommsRoot, $ScriptsRoot | Out-Null
Copy-Item "$SourceRoot\src\riverview_core\__init__.py" $PackageRoot -Force
Copy-Item "$SourceRoot\src\riverview_core\ledger.py" $PackageRoot -Force
Copy-Item "$SourceRoot\src\riverview_core\comms5\command_gateway.py" $CommsRoot -Force
Copy-Item "$SourceRoot\scripts\run_windows_command_agent.py" $ScriptsRoot -Force
```

Create a local standard account. This command does not add it to
Administrators. Keep its password in the Windows credential manager.

```powershell
$AgentUserName = 'RiverviewCommandAgent'
$AgentAccount = "$env:COMPUTERNAME\$AgentUserName"
$AgentPassword = Read-Host 'Set the local agent account password' -AsSecureString
New-LocalUser -Name $AgentUserName -Password $AgentPassword `
  -Description 'Least-privilege Riverview read-only command agent' `
  -PasswordNeverExpires -AccountNeverExpires
$AgentPassword = $null
```

Create separate secret and data directories. The approved internal CA must
provide a PEM certificate chain and private key; the certificate SAN must be
`DNS:desktop-ja3rpnq`. Install the issuing CA certificate on Camrui as
`agent-ca.pem`. The issuer and LAN addresses are environment-specific and must
come from the authorized administrators.

```powershell
$Base = Join-Path $env:ProgramData 'Riverview\CommandGateway'
$Secrets = Join-Path $Base 'secrets'
$Data = Join-Path $Base 'data'
New-Item -ItemType Directory -Force -Path $Secrets, $Data | Out-Null
Copy-Item 'C:\Staging\Approved\agent.crt' (Join-Path $Secrets 'agent.crt') -Force
Copy-Item 'C:\Staging\Approved\agent.key' (Join-Path $Secrets 'agent.key') -Force
certutil.exe -dump (Join-Path $Secrets 'agent.crt')
icacls.exe $InstallRoot /inheritance:r /grant:r `
  '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "${AgentAccount}:(OI)(CI)RX" /T
icacls.exe $Secrets /inheritance:r /grant:r `
  '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "${AgentAccount}:(OI)(CI)RX" /T
icacls.exe $Data /inheritance:r /grant:r `
  '*S-1-5-18:(OI)(CI)F' '*S-1-5-32-544:(OI)(CI)F' "${AgentAccount}:(OI)(CI)M" /T
```

Generate the 32-byte bearer without printing it. Transfer it to Camrui only
through the approved secret-transfer channel and install the same value there
as systemd credential `command-agent-token`.

```powershell
$Random = [Security.Cryptography.RandomNumberGenerator]::Create()
$Bytes = New-Object byte[] 32
$Random.GetBytes($Bytes)
$AgentToken = [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
[IO.File]::WriteAllText((Join-Path $Secrets 'agent.token'), $AgentToken, [Text.Encoding]::ASCII)
[Array]::Clear($Bytes, 0, $Bytes.Length)
$AgentToken = $null
$Random.Dispose()
icacls.exe (Join-Path $Secrets 'agent.token') /inheritance:r /grant:r `
  '*S-1-5-18:F' '*S-1-5-32-544:F' "${AgentAccount}:R"
```

The authentication direction is Dashboard-to-agent: the Dashboard connects to
`https://desktop-ja3rpnq:8443`, validates the agent certificate against its
systemd-loaded CA, then sends the bearer over TLS. The agent validates that
bearer with constant-time comparison. This is server-authenticated TLS plus a
bearer, not mutual TLS. The Comms5 caller identity and grants are checked on
Camrui before dispatch; they are not agent credentials.

Provision the SSH key for the agent account through the existing SSH
authorization process. Prefer a key restricted on Camrui to `hostname`, with
PTY and forwarding disabled. Keep the private key in this Windows account's
`.ssh` directory. Fetch a candidate host key, compare the fingerprint with the
independently supplied Camrui fingerprint, and only then install it:

```powershell
$SshDir = Join-Path $env:USERPROFILE '.ssh'
New-Item -ItemType Directory -Force -Path $SshDir | Out-Null
$Candidate = Join-Path $SshDir 'camrui.known_hosts.candidate'
$KnownHosts = Join-Path $SshDir 'known_hosts'
$ExpectedCamruiFingerprint = 'SHA256:<independently-confirmed-fingerprint>'
$Scan = & ssh-keyscan.exe -T 5 -t ed25519 camrui 2>$null
if (-not $Scan) { throw 'No Camrui Ed25519 host key received' }
$Scan | Set-Content -Encoding ascii $Candidate
$ObservedFingerprint = ((& ssh-keygen.exe -lf $Candidate -E sha256) -split '\s+')[1]
if ($ObservedFingerprint -ne $ExpectedCamruiFingerprint) {
  throw "Camrui host-key fingerprint mismatch: $ObservedFingerprint"
}
$Scan | Set-Content -Encoding ascii $KnownHosts
```

The agent uses the Windows OpenSSH `camrui` alias with `BatchMode=yes` and
`StrictHostKeyChecking=yes`. The firewall rule must be limited to the desktop
private address and Camrui private source address:

```powershell
$AgentBind = '<DESKTOP-JA3RPNQ-private-IPv4>'
$CamruiAddress = '<Camrui-private-IPv4>'
New-NetFirewallRule -Name 'RiverviewCommandGateway8443' `
  -DisplayName 'Riverview command gateway from Camrui' `
  -Direction Inbound -Action Allow -Protocol TCP -LocalAddress $AgentBind `
  -LocalPort 8443 -RemoteAddress $CamruiAddress -Profile Domain,Private
Get-NetFirewallRule -Name 'RiverviewCommandGateway8443' |
  Get-NetFirewallAddressFilter
```

After approval, open a PowerShell session as the agent account and start the
agent in the foreground for commissioning. No Python packages are required.

```powershell
$Base = Join-Path $env:ProgramData 'Riverview\CommandGateway'
$env:RIVERVIEW_COMMAND_AGENT_BIND = '<DESKTOP-JA3RPNQ-private-IPv4>'
$env:RIVERVIEW_COMMAND_AGENT_DB = Join-Path $Base 'data\executions.sqlite3'
$env:RIVERVIEW_COMMAND_AGENT_TOKEN_FILE = Join-Path $Base 'secrets\agent.token'
$env:RIVERVIEW_COMMAND_AGENT_CERT_FILE = Join-Path $Base 'secrets\agent.crt'
$env:RIVERVIEW_COMMAND_AGENT_KEY_FILE = Join-Path $Base 'secrets\agent.key'
$env:RIVERVIEW_COMMAND_JOB_TIMEOUT_SECONDS = '3600'
$env:RIVERVIEW_COMMAND_RETENTION_DAYS = '30'
& "$env:ProgramFiles\Python312\python.exe" `
  "$env:ProgramFiles\Riverview\CommandGateway\scripts\run_windows_command_agent.py"
```

## Acceptance commissioning

After approved Comms5 deployment, agent startup, and verification of both grant
pairs, submit the following through ChatGPT's Comms5 tools. Substitute only
the execution grant IDs from the approved Registry records.

```json
{
  "operation": "powershell_identity",
  "execution_grant_id": "<desktop-execution-grant-id>",
  "idempotency_key": "commission-desktop-identity-001"
}
```

Expect stdout JSON with `hostname: DESKTOP-JA3RPNQ` and `powershell_version`.
Then submit:

```json
{
  "operation": "ssh_camrui_hostname",
  "execution_grant_id": "<camrui-execution-grant-id>",
  "idempotency_key": "commission-camrui-hostname-001"
}
```

Expect stdout `camrui`. Save both complete Comms5 results, including status,
stdout, stderr, exit code, execution ID, caller/execution grant IDs, action,
scope, reservation ID, audit event ID, and idempotency key. Verify matching
reservation/consumption audit events in the canonical AuthorityRegistry. Do
not claim acceptance until both responses and both Registry audit records are
captured. Installing the Dashboard credential drop-in and restarting its
service remains subject to the normal authorized deployment procedure.


## Task-specific PowerShell and SSH commands

The task interface uses the same Gateway, Windows HTTPS agent, AuthorityRegistry
reservation/consumption, and SQLite audit ledger as the fixed probes. Host IDs
are a closed server-side mapping: `desktop-ja3rpnq` uses
PowerShell; `camrui`, `octominer1`, and `octominer2` use administrator-configured
OpenSSH aliases. A caller cannot supply a network address, username, executable,
credential, or alternate transport. SSH must use strict pinned host keys, batch
mode, no forwarding, and no TTY.

A command is at most 8,000 UTF-8 bytes. The agent persists the host, transport,
privilege class, caller/grant/reservation identifiers, command SHA-256, task
deadline, status, bounded result, timestamps, cancellation state, and
append-only audit events. Command text is held only in worker memory and is not
stored in SQLite. The durable queue row is committed before the agent starts
the worker. A single bounded worker and a 100-task outstanding queue prevent
unbounded execution fan-out. Completed records and their audit rows are
retained for 30 days by default (`RIVERVIEW_COMMAND_RETENTION_DAYS`, 1–365).

Example submit arguments (the Comms5 route supplies the authenticated caller):

```json
{
  "host_id": "desktop-ja3rpnq",
  "command": "Get-Date -Format o",
  "privilege_level": "standard",
  "execution_grant_id": "<active exact execution grant>",
  "idempotency_key": "task-2026-10-26-001"
}
```

Poll using the returned command digest and the same caller-supplied idempotency
key. Status and cancellation both recheck the same host-scoped caller grant.

```json
{
  "host_id": "desktop-ja3rpnq",
  "command_sha256": "<sha256 returned by submit>",
  "privilege_level": "standard",
  "idempotency_key": "task-2026-10-26-001"
}
```

`comms5_command_task_status` returns `queued`, `running`, `completed`, `failed`,
`timed_out`, `cancelled`, or `interrupted`, with timestamps, bounded output,
exit code, execution/task ID, authorization evidence, and the latest audit event
identifier. The Gateway's `cancel_task` operation and authenticated agent
DELETE endpoint provide idempotent cancellation. Comms5 publishes task submit
and status tools; cancellation remains available through the authenticated
agent API. Queued work becomes `cancelled`;
running work receives a cancellation signal and its process is terminated.
Completed work is returned unchanged.

After an agent restart, queued and running records become `interrupted` with an
audit event. Since command text is not persisted, unfinished work is never
silently replayed; resubmission needs a new idempotency key and fresh grant.
Completed results remain pollable during retention. Fast fixed probes continue
to return their immediate result as before.

### Required exact grants

For each target host, issue two separate grants on `host:<host_id>` under
`policy:delegation.v1`: one to the authenticated Comms5 principal for the caller
action, and one to `service:command-gateway` for the execution action. Standard
and elevated classes are independent. These are exact host grants; the
`project:Riverview` `comms5.operations.non_destructive.v1` grant does not
authorize shell access.

| Host | Standard caller action | Standard executor action | Elevated caller action | Elevated executor action |
| --- | --- | --- | --- | --- |
| `desktop-ja3rpnq` | `comms5.command.submit.task.desktop-ja3rpnq.standard` | `comms5.command.execute.task.desktop-ja3rpnq.standard` | `comms5.command.submit.task.desktop-ja3rpnq.elevated` | `comms5.command.execute.task.desktop-ja3rpnq.elevated` |
| `camrui` | `comms5.command.submit.task.camrui.standard` | `comms5.command.execute.task.camrui.standard` | `comms5.command.submit.task.camrui.elevated` | `comms5.command.execute.task.camrui.elevated` |
| `octominer1` | `comms5.command.submit.task.octominer1.standard` | `comms5.command.execute.task.octominer1.standard` | `comms5.command.submit.task.octominer1.elevated` | `comms5.command.execute.task.octominer1.elevated` |
| `octominer2` | `comms5.command.submit.task.octominer2.standard` | `comms5.command.execute.task.octominer2.standard` | `comms5.command.submit.task.octominer2.elevated` | `comms5.command.execute.task.octominer2.elevated` |

Each grant must be separately approved through the current Steward workflow. The
caller action grant belongs to the actual OAuth-verified Comms5 principal. The
executor grant belongs to `service:command-gateway`. Status retrieval requires
the same active caller action grant. A finite or unlimited use count and expiry
are set through the existing grant lifecycle.

Example submit:

```json
{
  "host_id": "camrui",
  "command": "hostname && systemctl is-active riverview-status-dashboard.service",
  "privilege_level": "standard",
  "execution_grant_id": "<active service:command-gateway grant>",
  "idempotency_key": "camrui-health-check-20261026-01"
}
```

For status, supply the same `host_id`, `privilege_level`, and `idempotency_key`,
plus the SHA-256 digest returned by the submit result as `command_sha256`. The
result returns bounded output, exit code, execution ID, grant references, and
audit event ID.

### Elevated execution limits and commissioning

The `elevated` class requires separate host-specific caller and executor grants.
SSH elevated requests run `sudo -n -- sh -lc <command>` and therefore fail
closed unless the target account's approved sudo policy permits that exact
execution. Standard SSH accounts must have no sudo rights. The Windows agent
currently rejects elevated PowerShell because it has no separate OS-level
elevation executor; a Steward grant alone cannot elevate its Windows service
identity.

This source change does not commission the Windows agent, SSH keys, host aliases,
CA, credentials, or protected systemd drop-in. Do not deploy/enable task commands
until the Windows agent is running under a dedicated non-administrator service
identity, its TLS and bearer credentials are installed through the approved
credential process, SSH aliases have strict known-host entries and least-
privilege accounts, and the host-specific caller/executor grants are active.
