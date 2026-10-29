# Riverview controlled read-only operator entry; revision 1.0.2; 2026-10-29
Clear-Host
$graceScopeReport = [System.Collections.Generic.List[string]]::new()
$graceScopeEntry = '/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-artifact-scope-diagnostic-20261029/run_grace_artifact_scope_diagnostic.sh'
$graceScopeHash = '95a34a8f82eecc5ce1ec2b2651d178966e81c0dad4445cc3e9e3a4937f4282a3'
$graceScopeSsh = @('-n','-T','-o','BatchMode=yes','-o','ConnectTimeout=15','camrui')
try {
    & {
        $graceScopeIdentity = (& whoami.exe | Out-String).Trim()
        $graceScopeReport.Add("OPERATOR_IDENTITY=$graceScopeIdentity")
        if ($graceScopeIdentity -ine 'desktop-ja3rpnq\wille') {
            $graceScopeReport.Add('BLOCKED: use the established Wille operator session.')
            return
        }
        $graceScopeOutput = @(& ssh.exe @graceScopeSsh "sha256sum '$graceScopeEntry'" 2>&1)
        $graceScopeExit = $LASTEXITCODE
        $graceScopeReport.Add("SCRIPT_HASH_SSH_EXIT_CODE=$graceScopeExit")
        foreach ($line in $graceScopeOutput) { $graceScopeReport.Add([string]$line) }
        if ($graceScopeExit -ne 0) { return }
        $graceScopeActual = (($graceScopeOutput | Out-String).Trim() -split '\s+')[0]
        if ($graceScopeActual -cne $graceScopeHash) {
            $graceScopeReport.Add('BLOCKED: diagnostic launcher hash differs from reviewed bytes.')
            return
        }
        $graceScopeOutput = @(& ssh.exe @graceScopeSsh "bash '$graceScopeEntry'" 2>&1)
        $graceScopeExit = $LASTEXITCODE
        $graceScopeReport.Add("DIAGNOSTIC_EXIT_CODE=$graceScopeExit")
        foreach ($line in $graceScopeOutput) { $graceScopeReport.Add([string]$line) }
    }
} catch {
    $graceScopeReport.Add("OPERATOR_ERROR=$($_.Exception.Message)")
} finally {
    $graceScopeText = $graceScopeReport -join [Environment]::NewLine
    Write-Host $graceScopeText
    try { Set-Clipboard -Value $graceScopeText; Write-Host 'Report copied to clipboard.' } catch { Write-Host 'Clipboard unavailable; report displayed above.' }
}
