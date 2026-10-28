<!-- Riverview Controlled Document
File: docs/operations/CAMRUI_GATEWAY_CODEX_COMMISSIONING.md
Component: WINDOWS-CODEX-COMMS5
File Revision: 1.0.0
Changed: 2026-10-27 | RV-CAMRUI-GATEWAY-CODEX
-->
# Camrui Codex control through the existing Comms5 Gateway

## Outcome and authority

The Steward explicitly confirmed authorization to continue the integration repair.
No renewed grant or repeated approval is requested. The change is prepared and
staged on Windows; Camrui installation and direct acceptance remain outstanding.
This extends the existing Gateway SSH key from hostname-only to bounded read-only
Codex control. It creates no key, copies no private key or login token, adds no
service, and does not replace Comms5, CME, Engineering or the operator connection.

The ordinary Windows Gateway runs as `RiverviewCmdAgent` using its own SSH key.
The account's actual Windows profile is
`C:/Users/RiverviewCmdAgent.DESKTOP-JA3RPNQ`, while effective SSH configuration
explicitly selects `C:/Users/RiverviewCmdAgent/.ssh/id_ed25519` and its pinned
known-host file. Scheduled task principal: RiverviewCmdAgent, Password logon,
Limited run level. Read-only Gateway inspection proved these values, execution
`10862a9e-4ba1-4f65-a8d3-cb1731abf954`.

The public key fingerprint was independently obtained without reading private-key
bytes: `SHA256:mqhE3Ax4u/FDvAQlVZzw9Hs5TMO+aDtUYPdiEJqMUPo` (ED25519),
execution `7a368a89-9b1a-4bc1-bdfe-0123cf4c6e47`. The installer matches only this
fingerprint and requires exactly one existing `restrict,command="hostname"`
entry (also accepts a fixed /bin or /usr/bin hostname path). It refuses ambiguous,
unrestricted, missing or unexpectedly changed entries. All other keys/options,
including host-source restrictions, remain byte-for-byte intact.

## What has and has not been proved

- ChatGPT directly executed Windows PowerShell, launched Luna, retrieved a later
  result and resumed the exact thread through Comms5: see the dual-host runbook.
- The Steward's separate operator test launched and resumed Camrui Codex under
  `admin1`, thread `01a17fd0-a4ae-73a2-9f0c-9f864cd82102`, exit 0 both times,
  recalling CEDAR-836 without repeating it in the follow-up. This is **operator**
  evidence, not proof that ChatGPT controlled Camrui directly.
- An initial operator SSH positional-prompt attempt timed out with exit 124 after
  `Reading additional input from stdin...`. Piping the prompt to SSH and using
  Codex's `-` input argument succeeded. The shared Python helper already writes
  and closes child stdin explicitly. Use that verified input discipline.
- The current forced-hostname Gateway entry cannot install its own replacement.
  One bootstrap must execute under the existing `wille` → `camrui` → `admin1`
  operator connection. Later identity/start/status/resume tests are performed
  directly by ChatGPT through the existing Camrui host grants.

## Installed boundary

Forced command becomes:

```text
/usr/bin/python3 /home/admin1/.local/lib/riverview/gateway-codex/ssh_codex_entry.py
```

The existing `restrict` option is retained. Exact `hostname` still returns the
hostname for the fixed probe. Other accepted input is `rv-codex-session` followed
by one shell-quoted JSON object; the entry parses this with shlex/JSON and never
evaluates it as shell code. Allowed requests:

| Operation | Fields | Behavior |
| --- | --- | --- |
| identity | operation | Return fixed protocol marker, host and current Unix user |
| start | operation, run_id, prompt | Existing CLI helper, fixed admin1 cwd/model, read-only sandbox |
| resume | operation, run_id, prompt, thread_id | Same, exact UUID; no `--last` |
| status | operation, run_id | Read that run's fixed local result/events; bounded messages |

No caller-selected executable, cwd, model, sandbox, arbitrary shell, key path,
credential, source installation or service operation is accepted. Prompts are
task data, passed as argv to the existing helper and then to Codex through stdin;
never include secrets. The existing account's Codex login is retained.

New Unix run directories use private permissions. Existing Comms5 host grants,
quota reservation/consumption, command SHA-256, stable keys, bounded output and
durable task status remain the authorization/audit path. The SSH entry is an
additional boundary; it neither manufactures nor substitutes institutional grants.
The helper's read-only scope deliberately does not authorize source changes.

## Bootstrap staged on Windows

Only public source code is in this bundle:
`C:\Users\Public\Documents\Riverview\GatewayCodexCommissioning\camrui-codex-commissioning.zip`.
SHA-256: `369cf70ac891dd167c29d37c80bc380eecb2a20ad8730d821098486d4a15c776`.
Remote Windows read-back verified that checksum, execution
`db13c52b-4624-4841-8dfd-4fcecbbb0ed0`.

Run once from the established **wille** PowerShell window. Extraction is to the
operator's temporary directory; no Git fetch or copied credential is required:

```powershell
Clear-Host
$zip = 'C:\Users\Public\Documents\Riverview\GatewayCodexCommissioning\camrui-codex-commissioning.zip'
$expected = '369cf70ac891dd167c29d37c80bc380eecb2a20ad8730d821098486d4a15c776'
if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { Write-Output 'Package checksum mismatch; stopped.'; return }
$destination = Join-Path $env:TEMP ('rv-camrui-commission-' + (Get-Date -Format 'yyyyMMddHHmmss'))
Expand-Archive -LiteralPath $zip -DestinationPath $destination
& (Join-Path $destination 'scripts\Install-RiverviewCamruiCodexEntry.ps1')
```

The bootstrap verifies wille, uses strict/pinned SSH through the existing alias,
copies only the three public Python sources to an admin1-owned staging directory,
runs installer dry-run checks and then applies the already-approved change.
It captures the report and copies it to the clipboard. It does not change the
Windows Gateway task identity or read/copy the operator's private SSH key.

Installer safeguards: current account must be admin1 with /home/admin1 HOME;
private owned non-symlink SSH directory/file; exactly one matching restricted key;
compile source before mutation; refuse an existing installation; verified original
authorized_keys backup and hash; refuse concurrent file changes; atomic replacement
with the same mode; read-back verification. Failure leaves an explicit diagnostic,
and a pre-key-change failure may leave inert installed sources for inspection.
Never rerun by deleting an unexpected existing installation without reviewing it.

## Direct acceptance after bootstrap

Use `comms5_command_task_submit` with host_id camrui, standard privilege, and the
existing exact executor grant. Each command below is its entire command body:

```text
rv-codex-session '{"operation":"identity"}'
```

Require RV_GATEWAY_CODEX_ENTRY_OK, user admin1, expected host. Then submit a
bounded marker task (a fresh run ID and stable Comms5 key):

```text
rv-codex-session '{"operation":"start","run_id":"camrui-direct-start-1","prompt":"Remember MAPLE-731. Do not use tools or modify anything. Reply with the marker."}'
```

Return after the initial Comms5 receipt; poll the original host/key/digest for
terminal execution. Retrieve the exact thread UUID and independently request:

```text
rv-codex-session '{"operation":"status","run_id":"camrui-direct-start-1"}'
```

Resume with a new run ID, exact returned thread UUID and a prompt that does not
repeat the marker. Poll/retrieve again, require same UUID, correct recalled marker,
exit 0 and durable Comms5 audit identifiers. Do not use the operator-reported
session as a substitute for this new Gateway-initiated acceptance.

## Rollback and limitations

Installer prints a private backup directory under
`/home/admin1/.local/state/riverview/gateway-codex-commissioning/<UTC timestamp>`.
Its manifest records the exact target, original/candidate SHA-256 and backup path.
Under the existing operator account, verify the predecessor hash, atomically
restore those authorized_keys bytes with their original owner/mode, and verify
the hash again. This restores hostname-only key behavior; operator keys are never
changed. The inert Python sources can remain for inspection. No sshd restart is
needed because authorized_keys is read for new connections.

The bootstrap has native Windows parser validation PASS (execution
`ca229d8c-7762-44b2-894c-03c0b627d7a3`). Twelve offline tests PASS for CLI process
handling, exact resume, idempotency and failure propagation, restricted command
parsing, traversal/duplicate-field rejection, fixed result path, exact key matching
and preservation of other key/options. Tests do not call real Codex or mutate
production authorized_keys. Camrui installation and direct acceptance are not
claimed until their actual results arrive.

The broader Grace direct Engineering objective/assignment/verifier path remains
separate from this minimal existing-Gateway Codex connection. No persistent PTY
or general-purpose Bash permission is implied by successful read-only session
control. The existing read-only sandbox policy remains enforced.
