<!-- Riverview Controlled Document
File: docs/operations/CAMRUI_GATEWAY_CODEX_COMMISSIONING.md
Component: WINDOWS-CODEX-COMMS5
File Revision: 1.0.1
Changed: 2026-10-27 | RV-CAMRUI-GATEWAY-CODEX
-->
# Camrui Codex control through the existing Comms5 Gateway

## Outcome and authority

The Steward explicitly confirmed authorization to continue the integration repair.
No renewed grant or repeated approval is requested. The change was installed through the established operator bootstrap; ChatGPT
subsequently completed direct Camrui identity/start/result/exact-thread-resume
acceptance through Comms5 on October 27, 2026 at 20:18–20:19 EDT.
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
and preservation of other key/options. Offline tests do not call real Codex or mutate production authorized_keys.
The separate live installation and direct acceptance evidence is recorded below.

The broader Grace direct Engineering objective/assignment/verifier path remains
separate from this minimal existing-Gateway Codex connection. No persistent PTY
or general-purpose Bash permission is implied by successful read-only session
control. The existing read-only sandbox policy remains enforced.


## Installed release and direct ChatGPT acceptance — PASS

The Steward's bootstrap report returned INSTALL_EXIT_CODE=0 and status installed.
Only the fingerprint-matched line 3 forced command changed; restrict remained.
Predecessor authorized_keys SHA-256:
`3a93308f5162d7c6071064008c8ac176c904ae05c7c9530ae5dd8cc614d28ebb`.
Installed candidate SHA-256:
`a0114ae1b0cf0ea134d820cffa9262e6fa0125ddec11779301e82d6144d97dfc`.
Verified rollback directory reported by installer:
`/home/admin1/.local/state/riverview/gateway-codex-commissioning/20261028T001757837228Z`.
Installed source hashes in that report:
- entry: `ac91f7474a0916e0d3d8529f91353b8eb72421eb7e69202abb954b7efd55db90`
- CLI helper: `9eee1d0dce6916ff8f85b8b693f7de078013112ea6a68b5a81f36a64effc6231`

After bootstrap, ChatGPT itself made each of the following Comms5 calls. The
Steward did not relay any session-control command or result in this acceptance.

| Step | Durable execution | Actual result |
| --- | --- | --- |
| Identity | `d4ffb532-f625-4e55-b125-ee04dc2ca09d` | RV_GATEWAY_CODEX_ENTRY_OK, admin1-Default-string, admin1, /home/admin1, exit 0 |
| Start | `be116efe-189e-4992-b2de-0c72794082cd` | Initial RUNNING; later durable status COMPLETED, exit 0 |
| Retrieve start result | `9e15fec6-95e6-45ff-ac27-d19e49060c6a` | Fixed run artifact returned WILLOW-947 |
| Resume | `1da817a9-9927-459e-b22d-21204a50ce09` | Initial RUNNING; later durable status COMPLETED, exit 0 |
| Retrieve resume result | `852faa4f-865e-4536-a477-d39963da7104` | Same exact thread; WILLOW-947 recalled without repeating it in follow-up |
| Reject unsupported caller-selected cwd | `641f9c75-f9ea-4850-aac1-ffd6c60c49df` | denied, exit 2, no arbitrary target accepted |
| Retain hostname probe | `de1ee334-adc7-441d-ba21-5267d58e2688` | admin1-Default-string, exit 0 |

Directly created and resumed Codex thread:
`01a17fdf-6d58-7050-92cc-1762ac986518`.
Start run ID: `camrui-direct-start-20261028-01`.
Resume run ID: `camrui-direct-resume-20261028-01`.
Their fixed result/events artifacts live under
`/home/admin1/.local/state/riverview/gateway-codex/<run_id>/`.

Start final audit: `a64b6f06-a3d8-4ccd-972b-122311873a71`.
Resume final audit: `277c524b-edfe-4509-8dec-b2ab69cffef8`.
Resumed artifact retrieval audit: `ff376a58-9223-4f32-baa2-6051ed08a370`.
Full sanitized receipts/command digests and the exact resume prompt are retained in
`evidence/checkouts/WINDOWS-CODEX-COMMS5/20261028T0019Z/direct-camrui.md`.

Quota observation after these checks: executor grant
`grant:5a2dadaf2c204632a8682e5831fd892d` is active, 14 of 20 uses consumed,
6 remaining, expires November 3, 2026 at 16:53:07 EST. Status-only Comms5 polling
needs no new executor use; the typed SSH result operation is itself a new host
command and does consume a use. Do not confuse seven-day duration with unlimited
count. No grant extension or new approval was requested for this acceptance.

This closes the minimal direct read-only Codex start/return-for-result/resume
proof for Camrui, alongside the earlier direct Windows proof. It does not claim
generic Bash access, Codex-internal tool execution, source-changing Engineering,
persistent PTY attachment, or full Grace/CME objective verification. Issue #359
retains those separate integration concerns; do not label the whole institution
complete from this session-continuity test.

Revision 1.0.0 is preserved byte-for-byte in
`docs/history/CAMRUI_GATEWAY_CODEX_COMMISSIONING_rev1.0.0.md`, original Git blob
`ef96b698604cc9ab79dc34afbeb3573532f5f635`. Restore those bytes to the original
path to restore the preceding documentation revision; this is distinct from the
production authorized_keys rollback described above.
