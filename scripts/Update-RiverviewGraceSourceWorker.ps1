# Riverview Controlled Source
# File: scripts/Update-RiverviewGraceSourceWorker.ps1
# Revision: 1.0.0 | 2026-10-28
# Apply the explicitly approved source-worker update through the existing operator SSH alias.
Clear-Host
$ErrorActionPreference = 'Continue'
$workerReport = New-Object 'System.Collections.Generic.List[string]'
function Add-WorkerReport([string]$Line) { [void]$workerReport.Add($Line) }
function Finish-WorkerReport {
    $workerText = $workerReport -join [Environment]::NewLine
    Write-Output $workerText
    try { Set-Clipboard -Value $workerText -ErrorAction Stop; Write-Host 'Report copied to clipboard.' }
    catch { Write-Host 'Clipboard unavailable; the complete report is displayed above.' }
}
$workerIdentity = (& whoami).Trim()
Add-WorkerReport "OPERATOR_IDENTITY=$workerIdentity"
if ($workerIdentity -ne 'desktop-ja3rpnq\wille') {
    Add-WorkerReport 'STOP: Run in the established desktop-ja3rpnq\wille operator session.'
    Finish-WorkerReport
    return
}
$workerEntry = '/home/admin1/.local/share/riverview/engineering/Riverview/scripts/update_grace_source_worker_20261028.py'
$workerExpectedHash = 'dfd631baa181b57aeca91bc157d633f3a1a72fe73bae18453656713bafabecc7'
$workerSshArgs = @('-n', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
    '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=2', 'camrui')
Write-Host 'Checking the prepared source-worker update...'
$workerHashResult = @(& ssh.exe @workerSshArgs "sha256sum '$workerEntry'" 2>&1)
$workerHashExit = $LASTEXITCODE
$workerHashText = ($workerHashResult | Out-String).Trim()
Add-WorkerReport "SCRIPT_HASH_SSH_EXIT_CODE=$workerHashExit"
Add-WorkerReport $workerHashText
if ($workerHashExit -ne 0 -or $workerHashText -notmatch ('^' + $workerExpectedHash + '\s')) {
    Add-WorkerReport 'STOP: prepared script is missing or differs from the reviewed hash.'
    Finish-WorkerReport
    return
}
Write-Host 'Checking the loaded worker configuration and approved scope...'
$workerDryResult = @(& ssh.exe @workerSshArgs "sudo -n /usr/bin/python3 '$workerEntry' --dry-run" 2>&1)
$workerDryExit = $LASTEXITCODE
Add-WorkerReport "DRY_RUN_EXIT_CODE=$workerDryExit"
Add-WorkerReport (($workerDryResult | Out-String).Trim())
if ($workerDryExit -ne 0) {
    Add-WorkerReport 'STOP: preflight failed; no apply command was sent.'
    Finish-WorkerReport
    return
}
Write-Host 'Applying the approved source-worker update...'
$workerApplyResult = @(& ssh.exe @workerSshArgs "sudo -n /usr/bin/python3 '$workerEntry' --apply" 2>&1)
$workerApplyExit = $LASTEXITCODE
Add-WorkerReport "APPLY_EXIT_CODE=$workerApplyExit"
Add-WorkerReport (($workerApplyResult | Out-String).Trim())
Finish-WorkerReport