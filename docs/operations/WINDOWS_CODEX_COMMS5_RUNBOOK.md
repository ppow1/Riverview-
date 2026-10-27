<!--
Riverview Controlled Document
File: docs/operations/WINDOWS_CODEX_COMMS5_RUNBOOK.md
Component: WINDOWS-CODEX-COMMS5
File Revision: 1.0.0
Changed: 2026-10-27 | Live Comms5 / Windows Codex launch and session-resume verification
-->
# Windows development machine — Codex via Riverview Comms 1.1

**Status:** Verified for remote read-only execution and persisted-session resume on 2026-10-27. This is an operator runbook, not proof that autonomous background orchestration or SSH target verification is commissioned.

## Verified environment

- Windows host: `desktop-ja3rpnq`; Gateway process identity: `DESKTOP-JA3RPNQ\RiverviewCmdAgent`.
- Comms 1.1 command operation: `comms5_command_task_submit`, with `comms5_command_task_status` for asynchronous polling. The command gateway accepts an authorized **standard** execution grant. Do not paste specific grant identifiers into permanent scripts: verify current caller/executor grants, action scope, host, and expiration before submission.
- Installed Codex: v0.163.0, Node entry point `C:\Users\wille\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js`. Invoke it with `node.exe` explicitly; `codex` is not on the Gateway account's PATH.
- **Required model:** `gpt-6-luna` (explicit `--model`). Do not rely on Codex's default `gpt-6.1-sol`. The plain `gpt-6` model returned HTTP 400 unsupported for the Gateway's ChatGPT-authenticated Codex session.
- Gateway account's independent `codex login --device-auth` was completed; `codex login status` returned `Logged in using ChatGPT`. Never copy the interactive user's `auth.json`, dump credentials, or weaken ACLs.
- Working directory observed: `C:\Program Files\Riverview\CommandGateway`. Non-repository tasks require `--skip-git-repo-check`; retain read-only sandbox for diagnostics. A code-editing task requires a deliberately selected repository working directory and separately authorized write scope.

## Remote execution procedure

1. Use Comms 1.1 to submit a standard command on `desktop-ja3rpnq`, with the **currently authorized** execution grant. Record the returned task ID, command hash, and idempotency key.
2. If status is `queued` or `running`, poll `comms5_command_task_status` with the same host, command hash, privilege level, and idempotency key. Do not treat an accepted submission as completed work.
3. Launch Codex explicitly with Luna. Redirect diagnostic stderr separately, because PowerShell can otherwise classify normal Codex stderr output as a native-command error and falsely return Gateway exit code 1.
4. Check both the Codex exit code and the expected stdout; do not claim success from text alone.
5. For later continuation, persist the **Codex session ID** from its diagnostic header. Resume by exact ID with `codex exec resume --skip-git-repo-check <session-id> <prompt>` (add repository context when applicable). This starts a new CLI process against the persisted session; it is **not** reattaching to an indefinitely running terminal.

### Read-only launch smoke test (PowerShell command body submitted through Comms5)

```powershell
Clear-Host
$node = (Get-Command node.exe -ErrorAction Stop).Source
$cli = 'C:\Users\wille\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js'
$log = Join-Path $env:TEMP 'riverview-codex-smoke.stderr.txt'
$output = & $node $cli exec --skip-git-repo-check --model gpt-6-luna 'Reply with exactly CODEX_GATEWAY_TASK_OK and nothing else.' 2> $log
$code = $LASTEXITCODE
Write-Output "CODEX_EXIT_CODE=$code"
$output | Write-Output
if ($code -ne 0) { Get-Content $log -Tail 25 }
exit $code
```

### Resume an existing persisted session

```powershell
Clear-Host
$node = (Get-Command node.exe -ErrorAction Stop).Source
$cli = 'C:\Users\wille\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js'
$sessionId = '<previously captured Codex session ID>'
$log = Join-Path $env:TEMP 'riverview-codex-resume.stderr.txt'
$output = & $node $cli exec resume --skip-git-repo-check $sessionId 'Continue the previous task; report current progress.' 2> $log
$code = $LASTEXITCODE
Write-Output "RESUME_EXIT_CODE=$code"
$output | Write-Output
if ($code -ne 0) { Get-Content $log -Tail 25 }
exit $code
```

For long-running or detached launches, write stdout and stderr to a dedicated file and read them through a later Comms5 command. When using PowerShell `Start-Process -ArgumentList`, quote or use redirected stdin for multiword prompts: an unquoted prompt was split into CLI arguments and produced `unrecognized subcommand`. A verified method was `Start-Process` with `-RedirectStandardInput` and a prompt file, plus separate stdout/stderr files.

## Live acceptance evidence — 2026-10-27

| Test | Observed outcome |
| --- | --- |
| Gateway account login | `Logged in using ChatGPT` |
| Explicit Luna model | `--model gpt-6-luna` returned `CODEX_GATEWAY_TASK_OK`, exit code 0 |
| Separate Codex process launch | Detached first stage returned `FIRST_STAGE_OK` |
| Persisted-session continuity | Session `01a17f83-f243-7962-83ba-d5844dfc7496` resumed in a separate Comms5 execution, recalled `BLUEPRINT` without the word being repeated in the follow-up prompt, exit code 0 |
| Comms5 result handling | Successful `completed` status, stdout captured, exit code 0 |

## Troubleshooting and boundaries

- **`codex` not recognized:** Gateway PATH differs from interactive user; use Node and the explicit CLI path.
- **`Not logged in` / HTTP 401:** Check `codex login status` under `RiverviewCmdAgent`; authorize its own device login. An earlier attempt failed with HTTP 504 during device authorization; retry succeeded.
- **HTTP 400 unsupported model:** Use `gpt-6-luna` explicitly, not `gpt-6`.
- **Resume reports untrusted directory:** Include `--skip-git-repo-check` after `exec resume` for non-repository smoke tests; do not use this flag to conceal an unintended code-editing directory.
- **Gateway reports failed despite correct stdout:** Capture Codex stderr separately and inspect `$LASTEXITCODE`.
- **Queued/running Comms5 task:** Poll task status; do not resubmit blindly with a new idempotency key.
- **Authorization or SSH blockers:** Do not alter grants, credentials, SSH settings, or claim unrelated live target verification. See [Issue #359](https://github.com/ppow1/Riverview-/issues/359), including [the earlier blocker record](https://github.com/ppow1/Riverview-/issues/359#issuecomment-6451969750). This runbook only supersedes the narrower *Codex-on-Windows launch/authentication/session-resume* uncertainty, not all Issue #359 work.

**Scope limit:** Tests establish request/response and persisted-session continuity. They do not establish a continuously attached interactive PTY, a durable unattended scheduler, permission to change production systems, or end-to-end SSH access to another host.
