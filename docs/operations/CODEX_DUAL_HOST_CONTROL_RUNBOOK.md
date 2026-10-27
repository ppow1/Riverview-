<!-- Riverview Controlled Document
File: docs/operations/CODEX_DUAL_HOST_CONTROL_RUNBOOK.md
Component: WINDOWS-CODEX-COMMS5
File Revision: 1.0.1
Changed: 2026-10-27 | RV-CODEX-DUAL-HOST-RUNBOOK
-->
# Windows and Camrui: shell access, Codex start, result, and exact-session resume

This is the continuation index for [Issue #359](https://github.com/ppow1/Riverview-/issues/359).
Use existing identities and the existing Comms5 asynchronous command interface.
The accompanying Python helper only invokes the existing CLI and records output;
it does not create an execution service, dispatcher, credential, or authority.

## Acceptance record: distinguish the paths

| Path | Identity | Established evidence | Outstanding proof |
| --- | --- | --- | --- |
| Windows operator shell | `DESKTOP-JA3RPNQ\wille` | Operator diagnostic and SSH alias verification supplied by Steward | No new live test in this continuation |
| Windows Comms5 shell/Codex | `DESKTOP-JA3RPNQ\RiverviewCmdAgent` | Fresh 19:36 EDT real Luna start, later status read and exact UUID resume recalled ORCHARD-592; both exit 0 | Codex-internal shell attempts were blocked by its environment policy; helper itself remains offline-tested |
| Windows operator SSH → Camrui | `wille` client → `admin1@192.168.1.155` | Steward's CAMRUI_EXECUTION_OK, `admin1`, `/home/admin1`, SSH exit 0 | Do not infer Gateway account access from this success |
| Camrui local Codex | `admin1` | Issue #359 records start and resume of `01a17ee1-4a3b-7951-b26d-3f44ecda6c25`, hostname returned | New remote Comms5 acceptance not established |
| Gateway SSH → Camrui | Gateway's independently configured SSH identity | Fresh 19:30 EDT Comms5 submission and later status returned hostname only, exit 0; requested marker/user/pwd absent | Arbitrary Bash and remote Codex start/resume fail acceptance through this identity |

Windows persisted session `01a17f83-f243-7962-83ba-d5844dfc7496` is historical
acceptance evidence, not a shared default session. Create a bounded smoke session
and retain its actual UUID. Sessions belong to the OS account and Codex home that
created them; do not copy authentication or session files between users.

The 19:04 EDT Windows diagnostic records existing interactive SSH/Codex processes
and a Gateway launched by the `Riverview Command Gateway Agent` scheduled task.
Do not assume it is a Windows service merely because older notes use that term.
Two Camrui repository paths appear in real sessions: `/home/admin1/riverview-core`
and `/home/admin1/projects/Riverview-New-Core`. Verify the intended repository's
origin, HEAD and working tree before engineering edits; neither is interchangeable
with a service release under `/opt`.

## Correct SSH connection

The existing **operator** alias is `camrui`. The Steward verified its effective
mapping: user `admin1`, hostname `192.168.1.155`, IdentitiesOnly yes, identity path
`C:/Users/wille/.ssh/octominer1_nopass`. That filename does not imply an OctoMiner
destination. Keep using the documented alias in the operator account.

Run this from Windows PowerShell as `wille`:

```powershell
Clear-Host
$report = & {
    whoami
    ssh.exe -G camrui | Select-String '^(hostname|user|identitiesonly|identityfile) '
    ssh.exe -o BatchMode=yes -o StrictHostKeyChecking=yes camrui 'printf "CAMRUI_EXECUTION_OK\n"; hostname; id -un; pwd'
    Write-Output "SSH_EXIT_CODE=$LASTEXITCODE"
} | Out-String
$report
$report | Set-Clipboard
```

Expect the marker, hostname `admin1-Default-string`, user `admin1`, and exit 0.
A Gateway key forced to `hostname` can return a correct hostname while ignoring
the requested command. Require the marker, user and directory to prove execution.
Do not weaken its restriction, copy the operator private key to the Gateway, or
modify `authorized_keys` to make a failed test appear successful. An already
authorized operator path is used under the operator identity; it is not silently
substituted for the Gateway identity.

Reference: [SSH standard](https://github.com/ppow1/Riverview-/blob/codex/grace-camrui-local-recovery/docs/operations/network/RIVERVIEW_SSH_STANDARD.md)
and [Camrui local execution recovery](https://github.com/ppow1/Riverview-/blob/codex/grace-camrui-local-recovery/docs/operations/GRACE_CAMRUI_LOCAL_EXECUTION_RECOVERY_2026-10-17.md).
The latter describes a Codex runner already on Camrui; this ChatGPT Work container
must not assume it is that runner.

## Access: why seven days does not by itself identify usable execution authority

First inspect existing grants. Do not automatically create another request when
an assistant lacks an ID or sees a generic error. Check these exact bindings:

| Grantee | Action | Scope |
| --- | --- | --- |
| Authenticated caller, historically `steward:camrui` | `comms5.operations.non_destructive.v1` | `project:Riverview` |
| Same caller | `comms5.command.submit.task.desktop-ja3rpnq.standard` | `host:desktop-ja3rpnq` |
| `service:command-gateway` | `comms5.command.execute.task.desktop-ja3rpnq.standard` | `host:desktop-ja3rpnq` |
| Same caller | `comms5.command.submit.task.camrui.standard` | `host:camrui` |
| `service:command-gateway` | `comms5.command.execute.task.camrui.standard` | `host:camrui` |

A seven-day **project** grant does not authorize host shell execution. A seven-day
host grant remains reusable until expiry, revocation or quota exhaustion; changing
chat windows does not revoke it. Status requires its ID in this connector.
The currently exposed Comms5 interface has request/status operations but no active
host-grant discovery operation. The existing issue log records this as
`COMMS5-CROSS-CONVERSATION-GRANT-RESOLUTION`. A missing reference is a continuity
problem, not evidence that the Steward must approve again.

The older original Camrui request records still point to two-hour grants:
`grant:54dafa24f70d4ee296b737e867091884` and
`grant:06dad5aa461d46fd9af4924a73f4e0a5`.
The latter was independently read back as revoked at 15:56:51 EDT on October 27,
with one use consumed. It cannot establish the current seven-day grant's state.
The Steward subsequently supplied the existing seven-day successor references,
and this continuation independently verified both as active:

| Binding | Current reference | Expiry | Limit |
| --- | --- | --- | --- |
| Camrui caller | `grant:6422d222eca74cb3b328bf3a80384a59` | November 3, 2026, 16:53:06 EST | Unlimited count |
| Camrui executor | `grant:5a2dadaf2c204632a8682e5831fd892d` | November 3, 2026, 16:53:07 EST | 20 total uses; 6 used before this continuation's one test |

Caller request: `delegation-request:8a7be042c6ae42d9ba4c52eab1486f79`, hash
`1dbb87ea327ce21c70c13f97e5c60c62ce21544a4a7fb7d19efb5b2b231aa21d`.
Executor request: `delegation-request:ba2d8bf8d062498bbcfcfba5b7ecc73d`, hash
`0eb785b6c976eb21ea0f0bacb164a652ac128c9cbb609a502cf72d38fbfca5b9`.
Both supersede their corresponding older grants. A seven-day extension preserved
the executor's original 20-use ceiling and carried usage forward; it did not reset
the quota or create unlimited execution. Recheck current usage before each task.
This continuation has not renewed, replaced, surrendered or approved any grant.
Current Windows grants, supplied by Steward and independently verified active:

| Binding | Grant ID | Expiry | Usage policy |
| --- | --- | --- | --- |
| Windows caller | `grant:bc790c0beb1746b295aade230d4a56cf` | November 2, 2026, 19:55:25 EST | Unlimited |
| Windows executor | `grant:2c4cd34bcc484a61814f6f489f25c8f1` | November 2, 2026, 19:55:25 EST | Unlimited |

No further approval is needed for eligible commands while these bindings remain
active. Their identity, scope and dates were read from the canonical status tool.
Use counts below are observations, not a continuously refreshed projection.

Fresh acceptance attempt: key `issue359-handoff-camrui-shell-20261027-01`, execution
`34e1e579-3ebb-4d85-9bc9-07b2e9cb162f`, audit event
`008cddfa-e0e2-418b-9f16-48a073f83ccc`, command SHA-256
`71033602ea6564f6342c4536f4f7a772b0747a18691be219d997eb686046c700`.
The exact command requested clear, RV_CAMRUI_SHELL_OK, hostname, id -un and pwd.
Submit and independent durable status returned only `admin1-Default-string`,
exit 0. Authorization/transport succeeded; shell-command acceptance failed.
Do not spend additional uses repeating arbitrary commands through a forced key.

Inspect each known current ID through:

```json
{"grant_id":"<current granted ID>"}
```

Call `comms5_get_delegation_grant_status`; verify `status`, principal, exact action,
scope, `valid_until`, `revoked_at`, `max_uses` and `used_count`. Preserve the caller
and executor IDs, request IDs and hashes in the authorized operational handoff.
IDs are references, never substitutes for the actual authenticated caller.

### Only when an existing eligible grant is genuinely absent or needs extension

Use `comms5_request_delegation_grant` for a new exact binding. This example is a
template; do not submit it merely to recover a lost ID:

```json
{
  "principal_id":"service:command-gateway",
  "action":"comms5.command.execute.task.desktop-ja3rpnq.standard",
  "scope_ref":"host:desktop-ja3rpnq",
  "policy_ref":"policy:delegation.v1",
  "duration_spec":{"unit":"days","value":7},
  "max_uses":null,
  "request_ref":"issue:359/explicit-seven-day-host-authority",
  "idempotency_key":"<stable unique key for this exact request>"
}
```

For the caller binding use the actual authenticated principal and the submit
action. For Camrui use the corresponding Camrui action and host scope. For an
existing grant, prefer the documented `request_delegation_grant_change` extension
workflow; approval creates a successor and retains lineage. Do not silently
change an existing use cap to unlimited: that is a Steward scope decision.

Approval uses the existing signed-in Steward Dashboard at
`https://192.168.1.155/v2/`, with its account session, CSRF cookie and authority.
The existing decision route is
`POST /api/v1/steward/delegation-grant-requests/{request_id}/decision`.
After inspecting the exact request, this page-console template approves only
the supplied ID and digest; it does not request or generate authority:

```javascript
(async () => {
  const requestId = '<existing pending request ID>';
  const requestSha256 = '<exact request_sha256 returned by status>';
  if (!/^delegation-request:[0-9a-f]+$/.test(requestId) ||
      !/^[0-9a-f]{64}$/.test(requestSha256)) return console.error('Supply the inspected request ID and hash.');
  const item = document.cookie.split(';').map(s => s.trim())
    .find(s => s.startsWith('rv_account_csrf='));
  if (!item) return console.error('Sign in as the authorized Steward on this origin.');
  if (!confirm('Approve the exact previously inspected request ' + requestId + '?')) return;
  const response = await fetch('/api/v1/steward/delegation-grant-requests/' + requestId + '/decision', {
    method: 'POST', credentials: 'same-origin',
    headers: {'Content-Type':'application/json', 'Accept':'application/json',
      'X-Riverview-CSRF':decodeURIComponent(item.slice('rv_account_csrf='.length))},
    body: JSON.stringify({decision:'approve', expected_request_sha256:requestSha256,
      idempotency_key:'issue359-approve-' + requestId.split(':')[1],
      approval_ref:'Steward approval of the inspected exact Issue #359 request'})
  });
  console.log(response.status, await response.json());
})();
```

Read the returned grant back through Comms5. The earlier apparent active/denied
contradiction was traced in Issue #359 to uncommitted approval writes on a shared
manager connection; PR #361 supplied transaction isolation and was deployed.
Original uncommitted approvals rolled back during the authorized recovery, then
the original request IDs were approved durably. Do not repeat that diagnosis or
assume an old in-session success proves durable authority.

## Existing Comms5 asynchronous shell procedure

Submit `comms5_command_task_submit` with these fields:

```json
{
  "host_id":"desktop-ja3rpnq",
  "privilege_level":"standard",
  "execution_grant_id":"<current exact Windows executor grant ID>",
  "idempotency_key":"<stable key for this command>",
  "command":"Clear-Host\nWrite-Output 'RV_SHELL_OK'\nwhoami"
}
```

For the separately commissioned Linux transport, use host_id `camrui`, its exact
executor grant, and `clear; printf 'RV_BASH_OK\n'; hostname; id -un; pwd`.
That command does not turn a hostname-only SSH key into a shell-capable key.
No user-supplied login, worker or private key belongs in the tool arguments.

Retain the response, execution ID, original key and command SHA-256. Poll
`comms5_command_task_status` with host, privilege, original key and exact digest.
The digest covers the exact UTF-8 command including whitespace. Do not submit
again with a new key because the first request is still running. Default task
deadline is 3,600 seconds; maximum server-configured deadline is 86,400 seconds.
This connector has no timeout override argument. Output is bounded to 32 KiB per
stream. Completion requires the terminal result, exit code and expected output.

## Codex invocation helper and retained results

Source: [scripts/riverview_codex_session.py](../../scripts/riverview_codex_session.py).
Use an absolute helper path from a checkout visible to the executing account.
No installation or ACL change is assumed. Each invocation uses an explicit cwd,
model and stable run ID, enforces the read-only sandbox, and passes the prompt
on stdin. It records `request.json`, `events.jsonl`, `stderr.txt`, `result.json` in
an account-owned state directory. The prompt itself is not stored by the helper;
Codex's own account-local session retains its normal conversation history.
Never put credentials in prompts. Output/session artifacts can contain task data.

### Windows start, under the identity whose Codex login was verified

Codex v0.163.0 was verified via Node and
`C:\Users\wille\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js`.
The Gateway has its own completed ChatGPT device login. Use explicit
`gpt-6-luna`; the plain `gpt-6` model failed for that login.

Replace only the helper path below with its verified account-visible location:

```powershell
Clear-Host
$helper = '<absolute path to scripts\riverview_codex_session.py>'
$python = (Get-Command python.exe -ErrorAction Stop).Source
$node = (Get-Command node.exe -ErrorAction Stop).Source
$cli = 'C:\Users\wille\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js'
$state = Join-Path $env:LOCALAPPDATA 'Riverview\CodexControl'
$runId = 'windows-smoke-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$report = & $python $helper --codex $cli --node $node --cwd $env:TEMP --state-root $state --run-id $runId --host-label desktop-ja3rpnq --model gpt-6-luna --non-repository-smoke-test --prompt 'Remember the marker MAPLE-47. Run hostname and report the hostname and marker.' | Out-String
$code = $LASTEXITCODE
$report = "CODEX_EXIT_CODE=$code`n$report"
$report
$report | Set-Clipboard
exit $code
```

When submitted through Comms5, the existing async task runs independently of
the chat turn; poll the task later. Clipboard access may be unavailable in a
headless account: stdout and account-local artifacts are authoritative.
Do not interpret a clipboard error as a failed Codex execution.

### Windows return and resume

After the previous task is terminal, inspect its `result.json` and event log.
Set the variables to the exact previously returned paths/UUID, not `--last`:

```powershell
Clear-Host
$previousResult = '<absolute previous result.json path>'
$prior = Get-Content -Raw $previousResult | ConvertFrom-Json
$report = & {
    $prior | ConvertTo-Json
    Get-Content $prior.events -Tail 30
} | Out-String
$report
$report | Set-Clipboard
```

Resume in a new invocation after setting the prior result path:

```powershell
Clear-Host
$helper = '<absolute path to scripts\riverview_codex_session.py>'
$previousResult = '<absolute previous result.json path>'
$prior = Get-Content -Raw $previousResult | ConvertFrom-Json
if ($prior.status -ne 'completed') { Write-Output 'Previous run is not completed; inspect it before resume.'; return }
$python = (Get-Command python.exe -ErrorAction Stop).Source
$node = (Get-Command node.exe -ErrorAction Stop).Source
$cli = 'C:\Users\wille\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js'
$state = Join-Path $env:LOCALAPPDATA 'Riverview\CodexControl'
$runId = 'windows-resume-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
$report = & $python $helper --codex $cli --node $node --cwd $prior.cwd --state-root $state --run-id $runId --host-label desktop-ja3rpnq --model gpt-6-luna --non-repository-smoke-test --resume $prior.thread_id --prompt 'Run hostname again and report the marker remembered from the previous task.' | Out-String
$code = $LASTEXITCODE
$report = "RESUME_EXIT_CODE=$code`n$report"
$report
$report | Set-Clipboard
exit $code
```

The prompt deliberately does not repeat the marker. Require exit 0, the same
thread UUID, expected host and recalled marker. For direct CLI use, the verified
baseline is `node.exe <codex.js> exec resume --skip-git-repo-check --model gpt-6-luna <UUID> <prompt>`.

### Camrui operator SSH and local Bash start/resume

Use the established Windows operator connection to enter Camrui as `admin1`:
`ssh.exe -o BatchMode=yes -o StrictHostKeyChecking=yes camrui`.
If already on Camrui as `admin1`, use the local shell directly. Verify hostname
and user before using the existing `/home/admin1/.local/bin/codex`.
Place the helper in a checked-out or deliberately copied, account-owned path;
do not place it in a production release merely for a smoke test.

```bash
clear
helper='/home/admin1/riverview-core/scripts/riverview_codex_session.py'
run_id="camrui-smoke-$(date +%Y%m%d-%H%M%S)"
report=$(python3 "$helper" --codex /home/admin1/.local/bin/codex \
  --cwd /home/admin1 --state-root /home/admin1/.local/state/riverview/codex-control \
  --run-id "$run_id" --host-label camrui --model gpt-6-luna \
  --non-repository-smoke-test \
  --prompt 'Remember the marker CEDAR-83. Run hostname and report the hostname and marker.')
code=$?
report=$(printf '%s\nCODEX_EXIT_CODE=%s\n' "$report" "$code")
printf '%s\n' "$report"
copied=0
if command -v wl-copy >/dev/null 2>&1; then printf '%s\n' "$report" | wl-copy && copied=1; fi
if [ "$copied" -eq 0 ] && command -v xclip >/dev/null 2>&1; then printf '%s\n' "$report" | xclip -selection clipboard && copied=1; fi
if [ "$copied" -eq 0 ]; then printf 'CLIPBOARD_UNAVAILABLE: retain stdout and result.json\n'; fi
(exit "$code")
```

The helper path is an example target, not evidence the file is installed there.
For later resume, first inspect the prior result and event log, then run:

```bash
clear
helper='/home/admin1/riverview-core/scripts/riverview_codex_session.py'
thread_id='<recorded completed thread UUID>'
run_id="camrui-resume-$(date +%Y%m%d-%H%M%S)"
report=$(python3 "$helper" --codex /home/admin1/.local/bin/codex \
  --cwd /home/admin1 --state-root /home/admin1/.local/state/riverview/codex-control \
  --run-id "$run_id" --host-label camrui --model gpt-6-luna \
  --non-repository-smoke-test --resume "$thread_id" \
  --prompt 'Run hostname again and report the marker remembered from the previous task.')
code=$?
report=$(printf '%s\nRESUME_EXIT_CODE=%s\n' "$report" "$code")
printf '%s\n' "$report"
copied=0
if command -v wl-copy >/dev/null 2>&1; then printf '%s\n' "$report" | wl-copy && copied=1; fi
if [ "$copied" -eq 0 ] && command -v xclip >/dev/null 2>&1; then printf '%s\n' "$report" | xclip -selection clipboard && copied=1; fi
if [ "$copied" -eq 0 ]; then printf 'CLIPBOARD_UNAVAILABLE: retain stdout and result.json\n'; fi
(exit "$code")
```

If collecting this result from Windows, capture the `ssh.exe` stdout into
`$report` and use `Set-Clipboard` there; a headless Linux SSH session normally has
no desktop clipboard. Do not install clipboard packages as a prerequisite.

## What leaving and returning means

There are two independent IDs: the Comms5 execution ID/key identifies one shell
task; the Codex thread UUID identifies persisted conversation context. An async
Comms5 task can continue after the submit call returns. A completed Codex CLI
process is exited; `exec resume <UUID>` starts another process using the same
account's persisted context. It does not attach to a live PTY. Do not resume the
same thread concurrently with its still-running original task.

The helper marks `running` before consuming events and writes the thread ID when
observed. A host/agent interruption can leave that file stale. Compare it with
the durable Comms5 terminal status and actual process state; never blindly replay
potential external effects. A repeated helper run ID returns its prior result
instead of launching another process; changed inputs with the same ID fail.

## Failure classification and safe continuation

| Signal | First decisive check | Action |
| --- | --- | --- |
| Tool absent | Callable session tool inventory | Restore/expose the existing operation; capability advertisement alone is insufficient |
| Platform tool rejection without receipt | Exact tool result | Do not claim host execution or try to evade the rejection |
| NOT_AUTHORIZED | Existing exact caller/executor grant records and transaction visibility | Identify failing stage; do not automatically request another grant |
| SSH hostname error | Gateway account's effective target/alias | Compare installed agent with source fix; preserve host-key pinning |
| Only hostname returned | Forced-command restriction and executing identity | Use the already authorized operator path in its own account; do not weaken restricted key |
| Git operation hangs | Correct account's repository visibility and Git auth | Bound inspection; do not copy interactive credentials |
| Codex not found | Account-specific PATH | Windows uses Node plus verified CLI path; Camrui uses its verified executable |
| Codex not logged in | Login status under actual executing account | Its own device login, only if genuinely missing; SSH/grants and Codex login are separate |
| Correct output but wrapper failure | Native exit code and separated stderr | Preserve both; do not parse normal stderr as a failed task |
| Resume loses context | Exact UUID, OS account, Codex home and model | Resume under the original identity; do not copy auth/session files |

The current documentation is complete enough to reproduce the established
procedures, but **dual-host Comms5 acceptance remains incomplete**. New helper
tests are offline process/recording tests, not live Codex authentication or SSH
tests. To close acceptance, retain fresh caller/executor references and actual
start → leave/poll → result → exact-ID resume evidence for each intended path.


## Revision preservation and local validation

The preceding Windows runbook revision 1.0.0 is retained byte-for-byte at
`docs/history/WINDOWS_CODEX_COMMS5_RUNBOOK_rev1.0.0.md`, original blob
`f7ed97bf4169e42773fd68098f37a30a36528636`, SHA-256
`26b9c9785a5dfad19f3765a2de97ee01e876569dfab95d6d37f48a5dd207fb4e`.
Restore by verifying that checksum and copying those bytes to the original path.
This change updates the original file to 1.0.1; new files start at 1.0.0.
Five standard-library offline tests pass for the helper: start/event capture,
exact UUID resume, idempotent replay, changed-input conflict, and child failure
exit propagation. They use a fake CLI, never real Codex or host credentials.
The PowerShell examples have not been executed by this continuation. Use the
existing live-tested Windows baseline above until a current Windows grant
reference permits a fresh run; do not label offline helper tests live acceptance.


## Fresh Windows live acceptance — October 27, 2026, 19:35–19:38 EDT

1. Windows PowerShell probe returned RV_WINDOWS_SHELL_OK, host DESKTOP-JA3RPNQ,
   identity desktop-ja3rpnq\riverviewcmdagent, and the verified Node/CLI paths,
   exit 0. Execution: `240c8ca4-924e-48f2-bfa8-4068772f1dc0`.
2. A real read-only Luna start returned RUNNING, allowing the initiating call to
   finish; a later durable status read returned COMPLETED, exit 0, thread
   `01a17fb8-8ab0-7993-a547-7f576d8571d4`. Execution:
   `9b4d1a89-57fb-4cba-9368-d3c1e38143c6`; final audit:
   `79c7852f-8706-4c7d-b158-4b8320bfdba0`.
3. A separate Comms5 task ran `exec resume` on that exact UUID. The prompt did
   not repeat the original marker. Later status returned ORCHARD-592, the same
   UUID and exit 0. Execution: `cec27864-e8ef-4fdf-8745-ea367e05c9ea`;
   final audit: `9b32d050-9bfa-43ff-a4b6-e3a19e99a0bd`.

This proves Windows shell access plus real Codex start, return for result and
persisted-session resume through Comms5. The initial Codex request also asked
Codex to run hostname/whoami; its reply reports both tool attempts blocked by
policy, and the events do not establish those commands ran. The independent
Gateway PowerShell probe above did execute them. Do not conflate these outcomes
or weaken the sandbox to make the Codex-internal shell test pass.

### Remaining Camrui operator acceptance: one existing-account runner

`scripts/Test-RiverviewCamruiCodexContinuity.ps1` verifies wille, inspects the
existing alias without reading keys, requires a genuine SSH marker and admin1,
starts read-only Luna, closes that SSH invocation, then resumes the exact UUID in
another invocation and checks marker recall. It captures a complete report and
copies it to the Windows clipboard. It does not alter authorized_keys, ACLs,
SSH configuration, authentication, grants or services. Live Windows PowerShell
parser validation passed, execution `1f15a9f3-3935-4a12-ac2b-ae862ae67a4c`.
The runner has not been executed under wille by this ChatGPT continuation; its
Gateway tool runs as RiverviewCmdAgent, which cannot be substituted for wille.

From the established wille PowerShell window, use the existing checkout to
retrieve the script and run it. The following only fetches the documentation
branch, writes a temporary operator script, then runs that script. It does not
switch, reset, merge or edit the checkout:

```powershell
Clear-Host
$checkout = 'A:\Riverview-New-Core'
if ((& whoami).Trim().ToLowerInvariant() -ne 'desktop-ja3rpnq\wille') { Write-Output 'Use the established wille operator window.'; return }
git -C $checkout fetch --no-tags origin docs/windows-codex-comms5-runbook-20261027
if ($LASTEXITCODE -ne 0) { Write-Output 'Fetch failed; keep the existing checkout unchanged.'; return }
$scriptText = & git -C $checkout show 'FETCH_HEAD:scripts/Test-RiverviewCamruiCodexContinuity.ps1'
if ($LASTEXITCODE -ne 0) { Write-Output 'Script retrieval failed.'; return }
$scriptPath = Join-Path $env:TEMP 'Test-RiverviewCamruiCodexContinuity.ps1'
$scriptText | Set-Content -Encoding UTF8 $scriptPath
& $scriptPath
```

Paste its complete report into Issue #359 or the active continuation. This is
execution under the already-established operator account, not another grant
approval. Its result can verify the operator SSH/Codex path; it cannot turn that
path into a Gateway service-account path or prove remote Comms5 Bash access.

### Revision 1.0.1 predecessor

Prior dual-host runbook revision 1.0.0 is preserved at
`docs/history/CODEX_DUAL_HOST_CONTROL_RUNBOOK_rev1.0.0.md`. Original Git blob:
`788edbd070eccab909815b2eab51b02ce076997c`. Verify the following SHA-256 before
restoring those bytes to the original path:
`d5a67fb4e56fb0835f597833455140287a3ae388f262cc09bfc038c44815947a`.
