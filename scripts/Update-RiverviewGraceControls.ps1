# Riverview Controlled Source
# File: scripts/Update-RiverviewGraceControls.ps1
# Revision: 1.0.1 | 2026-10-28
# Uses the established Windows operator SSH alias; captures a clipboard report.
Clear-Host
$ErrorActionPreference = 'Continue'
$graceReport = New-Object 'System.Collections.Generic.List[string]'
function Add-GraceReport([string]$Line) { [void]$graceReport.Add($Line) }
function Finish-GraceReport {
    $graceText = $graceReport -join [Environment]::NewLine
    Write-Output $graceText
    try { Set-Clipboard -Value $graceText -ErrorAction Stop; Write-Host 'Report copied to clipboard.' }
    catch { Write-Host 'Clipboard unavailable; the complete report is displayed above.' }
}
$graceIdentity = (& whoami).Trim()
Add-GraceReport "OPERATOR_IDENTITY=$graceIdentity"
if ($graceIdentity -ne 'desktop-ja3rpnq\wille') {
    Add-GraceReport 'STOP: Run in the documented desktop-ja3rpnq\wille operator session.'
    Finish-GraceReport
    return
}
$graceEntry = '/home/admin1/.local/share/riverview/engineering/Riverview/scripts/grace_current_controls_20261028.sh'
$graceExpectedHash = 'd4526f6753e4f3ae8acd2845a447935457cd32ff48f78dc0e7d8c708cf42a14c'
$graceSshArgs = @('-n', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
    '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2', 'camrui')
Write-Host 'Checking the prepared Camrui update script...'
$graceHashResult = @(& ssh.exe @graceSshArgs "sha256sum '$graceEntry'" 2>&1)
$graceHashExit = $LASTEXITCODE
Add-GraceReport "SCRIPT_HASH_SSH_EXIT_CODE=$graceHashExit"
$graceHashText = ($graceHashResult | Out-String).Trim()
Add-GraceReport $graceHashText
if ($graceHashExit -ne 0 -or $graceHashText -notmatch ('^' + $graceExpectedHash + '\s')) {
    Add-GraceReport 'STOP: prepared script is unavailable or does not match the reviewed hash.'
    Finish-GraceReport
    return
}
Write-Host 'Validating exact service pointers and file hashes...'
$graceDryResult = @(& ssh.exe @graceSshArgs "bash '$graceEntry' --dry-run" 2>&1)
$graceDryExit = $LASTEXITCODE
Add-GraceReport "DRY_RUN_EXIT_CODE=$graceDryExit"
Add-GraceReport (($graceDryResult | Out-String).Trim())
if ($graceDryExit -ne 0) {
    Add-GraceReport 'STOP: preflight failed; inspect the displayed guard result.'
    Finish-GraceReport
    return
}
Write-Host 'Applying the approved development update; checking services and rollback...'
$graceApplyResult = @(& ssh.exe @graceSshArgs "sudo -n bash '$graceEntry' --apply" 2>&1)
$graceApplyExit = $LASTEXITCODE
Add-GraceReport "APPLY_EXIT_CODE=$graceApplyExit"
Add-GraceReport (($graceApplyResult | Out-String).Trim())
Finish-GraceReport
