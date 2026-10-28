Clear-Host
# Riverview Controlled Source
# File: scripts/Install-RiverviewCamruiCodexEntry.ps1
# Component: WINDOWS-CODEX-COMMS5
# Revision: 1.0.0
# Purpose: One-time approved installation through the established operator SSH alias.
# Execution Model: Operator bootstrap; later control uses the existing Comms5 Gateway.
# Observability: Captured report and clipboard; remote verified rollback manifest.
# Dependencies: Existing wille SSH alias, admin1 login, adjacent public Python sources.
# Authority: Steward approved the bounded existing-key Codex commissioning in this conversation.
# Changed: 2026-10-27 | RV-CAMRUI-GATEWAY-CODEX | Prepared bootstrap; no new key or credential copy.
# History: New file; no predecessor.

$identity = (& whoami).Trim().ToLowerInvariant()
if ($identity -ne 'desktop-ja3rpnq\wille') {
    $report = "Run this one-time bootstrap from the established wille operator window. Actual identity: $identity"
    $report
    $report | Set-Clipboard
    return
}
$logs = New-Object 'System.Collections.Generic.List[string]'
$logs.Add("OPERATOR_IDENTITY=$identity")
$remoteRoot = '/home/admin1/.cache/riverview/gateway-codex-' + (Get-Date -Format 'yyyyMMddHHmmss')
$stagingOK = $true
$files = @('ssh_codex_entry.py','riverview_codex_session.py','commission_camrui_codex_entry.py')
foreach ($name in $files) {
    if (-not (Test-Path (Join-Path $PSScriptRoot $name))) {
        $stagingOK = $false
        $logs.Add("Missing source: $name")
    }
}
if ($stagingOK) {
    $output = & ssh.exe -T -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes camrui "umask 077; mkdir -p '$remoteRoot'" 2>&1 | Out-String
    $code = $LASTEXITCODE
    $logs.Add("STAGING_SSH_EXIT_CODE=$code")
    $logs.Add($output)
    if ($code -ne 0) { $stagingOK = $false }
}
if ($stagingOK) {
    foreach ($name in $files) {
        if ($stagingOK) {
            $output = & scp.exe -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes (Join-Path $PSScriptRoot $name) ("camrui:" + $remoteRoot + '/' + $name) 2>&1 | Out-String
            $code = $LASTEXITCODE
            $logs.Add("COPY_${name}_EXIT_CODE=$code")
            $logs.Add($output)
            if ($code -ne 0) { $stagingOK = $false }
        }
    }
}
if ($stagingOK) {
    $output = & ssh.exe -n -T -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes camrui "timeout 30s python3 '$remoteRoot/commission_camrui_codex_entry.py'" 2>&1 | Out-String
    $code = $LASTEXITCODE
    $logs.Add("DRY_RUN_EXIT_CODE=$code")
    $logs.Add($output)
    if ($code -ne 0) { $stagingOK = $false }
}
if ($stagingOK) {
    $output = & ssh.exe -n -T -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes camrui "timeout 30s python3 '$remoteRoot/commission_camrui_codex_entry.py' --apply --acknowledge-key-scope-change" 2>&1 | Out-String
    $code = $LASTEXITCODE
    $logs.Add("INSTALL_EXIT_CODE=$code")
    $logs.Add($output)
    if ($code -ne 0) { $stagingOK = $false }
}
if ($stagingOK) { $logs.Add('BOOTSTRAP_INSTALLED: return to ChatGPT for independent Gateway identity/start/status/resume testing.') }
if (-not $stagingOK) { $logs.Add('BOOTSTRAP_STOPPED: inspect report; do not loosen key options or change identities.') }
$report = $logs -join [Environment]::NewLine
$report
try { $report | Set-Clipboard -ErrorAction Stop } catch { Write-Output 'CLIPBOARD_UNAVAILABLE' }
