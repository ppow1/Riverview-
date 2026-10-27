Clear-Host
# Riverview Controlled Source
# File: scripts/Test-RiverviewCamruiCodexContinuity.ps1
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: Verify the established operator SSH path and exact Codex thread resume.
# Execution Model: Interactive operator command, two separate SSH/Codex invocations.
# Observability: Captured report, clipboard, temporary stdout/stderr artifacts.
# Dependencies: Existing wille SSH alias camrui, admin1 Codex login, PowerShell.
# Authority: Existing operator identity only; no key, grant, ACL or service changes.
# Changed: 2026-10-27 | RV-CODEX-DUAL-HOST-RUNBOOK | Operator acceptance runner.
# Contracts: docs/operations/CODEX_DUAL_HOST_CONTROL_RUNBOOK.md
# Tests: PowerShell parser validation; live operator acceptance remains outstanding.
# History: New file; no predecessor.

$identity = (& whoami).Trim().ToLowerInvariant()
if ($identity -ne 'desktop-ja3rpnq\wille') {
    $report = "Wrong execution identity: $identity. Run this script in the established wille operator PowerShell window."
    $report
    try { $report | Set-Clipboard -ErrorAction Stop } catch { Write-Output 'CLIPBOARD_UNAVAILABLE' }
    return
}
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$logs = Join-Path $env:TEMP "rv359-camrui-continuity-$stamp"
New-Item -ItemType Directory -Path $logs -ErrorAction Stop | Out-Null
$lines = New-Object 'System.Collections.Generic.List[string]'
$lines.Add("WINDOWS_IDENTITY=$identity")
$lines.Add("LOG_DIRECTORY=$logs")
$exitStatus = 0
try {
    $effective = & ssh.exe -G camrui 2> (Join-Path $logs 'ssh-config.stderr.txt')
    $effective | Where-Object { $_ -match '^(hostname|user|identitiesonly|identityfile) ' } | ForEach-Object { $lines.Add($_) }
    $probe = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes camrui 'printf "RV_OPERATOR_EXEC_OK\n"; hostname; id -un; pwd' 2> (Join-Path $logs 'probe.stderr.txt')
    $probeCode = $LASTEXITCODE
    $lines.Add("SSH_PROBE_EXIT_CODE=$probeCode")
    $probe | ForEach-Object { $lines.Add($_) }
    if ($probeCode -ne 0 -or $probe -notcontains 'RV_OPERATOR_EXEC_OK' -or $probe -notcontains 'admin1') {
        $exitStatus = 2
        $lines.Add('FAILED: expected operator identity/marker absent; no Codex invocation attempted.')
    }
    if ($exitStatus -eq 0) {
        $startCommand = "/home/admin1/.local/bin/codex --sandbox read-only exec --json --model gpt-6-luna --skip-git-repo-check -C /home/admin1 'Remember the continuity marker CEDAR-836. Do not use tools or modify anything. Reply with the marker.'"
        $start = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes camrui $startCommand 2> (Join-Path $logs 'start.stderr.txt')
        $startCode = $LASTEXITCODE
        $start | Set-Content -Encoding UTF8 (Join-Path $logs 'start.events.jsonl')
        $lines.Add("CODEX_START_EXIT_CODE=$startCode")
        $start | ForEach-Object { $lines.Add($_) }
        $startEvents = @($start | ForEach-Object { try { $_ | ConvertFrom-Json -ErrorAction Stop } catch {} })
        $thread = ($startEvents | Where-Object { $_.type -eq 'thread.started' } | Select-Object -First 1).thread_id
        if ($startCode -ne 0 -or $thread -notmatch '^[0-9a-f-]{36}$') {
            $exitStatus = 2
            $lines.Add('FAILED: start did not return a successful exact thread UUID; no resume attempted.')
        }
    }
    if ($exitStatus -eq 0) {
        $lines.Add("RESUMING_EXACT_THREAD=$thread")
        $resumeCommand = "/home/admin1/.local/bin/codex --sandbox read-only exec resume --json --model gpt-6-luna --skip-git-repo-check '$thread' 'Report the exact continuity marker from the previous turn. Do not use tools or modify anything. Reply only with the marker.'"
        $resume = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes camrui $resumeCommand 2> (Join-Path $logs 'resume.stderr.txt')
        $resumeCode = $LASTEXITCODE
        $resume | Set-Content -Encoding UTF8 (Join-Path $logs 'resume.events.jsonl')
        $lines.Add("CODEX_RESUME_EXIT_CODE=$resumeCode")
        $resume | ForEach-Object { $lines.Add($_) }
        $resumeEvents = @($resume | ForEach-Object { try { $_ | ConvertFrom-Json -ErrorAction Stop } catch {} })
        $resumedThread = ($resumeEvents | Where-Object { $_.type -eq 'thread.started' } | Select-Object -First 1).thread_id
        $message = @($resumeEvents | Where-Object { $_.type -eq 'item.completed' -and $_.item.type -eq 'agent_message' } | ForEach-Object { $_.item.text.Trim() })
        if ($resumeCode -ne 0 -or $resumedThread -ne $thread -or $message -notcontains 'CEDAR-836') {
            $exitStatus = 2
            $lines.Add('FAILED: resume identity, exit status or remembered marker did not match.')
        }
        if ($exitStatus -eq 0) { $lines.Add('PASS: operator SSH and separate-process exact-session Codex continuity verified.') }
    }
} catch {
    $exitStatus = 2
    $lines.Add('FAILED: ' + $_.Exception.Message)
}
$lines.Add("VERIFICATION_EXIT_CODE=$exitStatus")
$lines.Add('This verifies operator SSH/Codex only; it does not commission the Gateway SSH identity or a persistent PTY.')
$report = $lines -join [Environment]::NewLine
$report | Set-Content -Encoding UTF8 (Join-Path $logs 'report.txt')
$report
try { $report | Set-Clipboard -ErrorAction Stop } catch { Write-Output 'CLIPBOARD_UNAVAILABLE: report.txt retained.' }
