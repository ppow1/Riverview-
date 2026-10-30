# Riverview controlled operator entry; revision 1.0.0; 2026-10-29
Clear-Host
$graceAdmissionReport = [System.Collections.Generic.List[string]]::new()
$graceAdmissionEntry = '/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-artifact-formation-20261029/owner-release-update-artifact-formation.sh'
$graceAdmissionExpectedHash = '5fb725a600b3966356185f482a92d9901719384527cdd3ebaaf5ae725a715ba7'
$graceAdmissionSshArgs = @('-n', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', 'camrui')
try {
    & {
        $graceAdmissionIdentity = (& whoami.exe | Out-String).Trim()
        $graceAdmissionReport.Add("OPERATOR_IDENTITY=$graceAdmissionIdentity")
        if ($graceAdmissionIdentity -ine 'desktop-ja3rpnq\wille') {
            $graceAdmissionReport.Add('BLOCKED: use the established Wille operator session.')
            return
        }
        $graceAdmissionHashOutput = @(& ssh.exe @graceAdmissionSshArgs "sha256sum '$graceAdmissionEntry'" 2>&1)
        $graceAdmissionHashExit = $LASTEXITCODE
        $graceAdmissionReport.Add("SCRIPT_HASH_SSH_EXIT_CODE=$graceAdmissionHashExit")
        foreach ($line in $graceAdmissionHashOutput) { $graceAdmissionReport.Add([string]$line) }
        if ($graceAdmissionHashExit -ne 0) { return }
        $graceAdmissionActualHash = (($graceAdmissionHashOutput | Out-String).Trim() -split '\s+')[0]
        if ($graceAdmissionActualHash -cne $graceAdmissionExpectedHash) {
            $graceAdmissionReport.Add('BLOCKED: prepared helper hash differs from reviewed bytes.')
            return
        }
        foreach ($graceAdmissionMode in @('--dry-run', '--apply')) {
            $graceAdmissionOutput = @(& ssh.exe @graceAdmissionSshArgs "sudo -n bash '$graceAdmissionEntry' $graceAdmissionMode" 2>&1)
            $graceAdmissionExit = $LASTEXITCODE
            $graceAdmissionLabel = $graceAdmissionMode.TrimStart('-').Replace('-', '_').ToUpperInvariant()
            $graceAdmissionReport.Add("${graceAdmissionLabel}_EXIT_CODE=$graceAdmissionExit")
            foreach ($line in $graceAdmissionOutput) { $graceAdmissionReport.Add([string]$line) }
            if ($graceAdmissionExit -ne 0) { return }
        }
    }
} catch {
    $graceAdmissionReport.Add("OPERATOR_ERROR=$($_.Exception.Message)")
} finally {
    $graceAdmissionText = $graceAdmissionReport -join [Environment]::NewLine
    Write-Host $graceAdmissionText
    try { Set-Clipboard -Value $graceAdmissionText; Write-Host 'Report copied to clipboard.' } catch { Write-Host 'Clipboard unavailable; report displayed above.' }
}
