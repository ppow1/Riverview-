Clear-Host
# Riverview Controlled Source
# File: scripts/Update-RiverviewCamruiCodexWorkspace.ps1
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: Apply the approved source-editing correction through the established operator SSH alias.
# Execution Model: Operator bootstrap only; subsequent Codex work uses Comms5 directly.
# Observability: Complete stdout report and clipboard, remote verified backup manifest.
# Authority: Existing wille to admin1 connection; no copied key or changed grant.
# Changed: 2026-10-28 | RV-CODEX-ENGINEERING-WRITE
$identity = (& whoami).Trim().ToLowerInvariant()
if ($identity -ne 'desktop-ja3rpnq\wille') {
    $report = "Use the established wille PowerShell window. Actual identity: $identity"
    $report
    try { $report | Set-Clipboard -ErrorAction Stop } catch { Write-Output 'CLIPBOARD_UNAVAILABLE' }
    return
}
$report = & {
    Write-Output "OPERATOR_IDENTITY=$identity"
    $remote = '/home/admin1/.cache/riverview/codex-workspace-update-' + (Get-Date -Format 'yyyyMMddHHmmss')
    & ssh.exe -n -T -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes camrui "umask 077; mkdir -p '$remote'"
    Write-Output "STAGING_EXIT_CODE=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) { return }
    foreach ($name in @('ssh_codex_entry.py','riverview_codex_session.py','upgrade_camrui_codex_workspace.py')) {
        & scp.exe -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes (Join-Path $PSScriptRoot $name) ("camrui:" + $remote + '/' + $name)
        Write-Output "COPY_${name}_EXIT_CODE=$LASTEXITCODE"
        if ($LASTEXITCODE -ne 0) { return }
    }
    & ssh.exe -n -T -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes camrui "timeout 30s python3 '$remote/upgrade_camrui_codex_workspace.py'"
    Write-Output "DRY_RUN_EXIT_CODE=$LASTEXITCODE"
    if ($LASTEXITCODE -ne 0) { return }
    & ssh.exe -n -T -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes camrui "timeout 180s python3 '$remote/upgrade_camrui_codex_workspace.py' --apply"
    Write-Output "INSTALL_EXIT_CODE=$LASTEXITCODE"
    if ($LASTEXITCODE -eq 0) { Write-Output 'WORKSPACE_WRITE_INSTALLED: ChatGPT can now independently verify file editing, tests and exact-session resume.' }
} 2>&1 | Out-String
$report
try { $report | Set-Clipboard -ErrorAction Stop } catch { Write-Output 'CLIPBOARD_UNAVAILABLE' }
