Clear-Host
# Riverview Controlled Operator Script
# File: scripts/Invoke-RiverviewComms5StewardCredentialRotation.ps1
# Component: COMMS5-OAUTH-IONOGE
# File Revision: 1.0.1
# Purpose: Stage and preflight the approved Comms5 credential utility, then rotate only after explicit operator confirmation.
# Execution Model: Interactive Windows PowerShell 5.1
# Observability: Sanitized result; successful credential is copied to clipboard and never printed.
# Dependencies: OpenSSH scp/ssh, verified Ionoge host key for 64.227.21.54, Set-Clipboard.
# Authority: Explicitly asks for exact ROTATE confirmation before changing the shared Comms5 login/direct-bearer credential.
# Changed: 2026-10-17 UTC | RV-COMMS5-STEWARD-ROTATION-HEALTH-REPAIR | Fix checkout root and pin target to verified Ionoge address.
# Contracts: docs/operations/RIVERVIEW_MACHINE_CONNECTIONS_AND_COMMS5_RECOVERY_2026-10-17.md
# History: Git + revision/backup manifest.

$ErrorActionPreference = 'Stop'
$SshTarget = 'root@64.227.21.54'
$ExpectedUtilitySha256 = 'ede7a8a12ec0baa03ff2af48529298950c30ef2586c1f7951423c8bc6c0eaeea'
$RemoteUtility = '/usr/local/sbin/rotate_comms5_steward_credential.py'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$UtilityPath = Join-Path $RepoRoot 'scripts\rotate_comms5_steward_credential.py'

if (-not (Test-Path -LiteralPath $UtilityPath -PathType Leaf)) {
    $Report = 'Credential utility source is missing from this checkout; no production credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
    return
}

$LocalHash = (Get-FileHash -LiteralPath $UtilityPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($LocalHash -ne $ExpectedUtilitySha256) {
    $Report = 'Credential utility source hash does not match the reviewed merge; no production credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
    return
}

$InspectCommand = "if test -f $RemoteUtility; then sha256sum $RemoteUtility; stat -c '%U:%G %a' $RemoteUtility; else printf ABSENT; fi"
$RemoteState = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes $SshTarget $InspectCommand 2>&1
$RemoteStateExit = $LASTEXITCODE
$RemoteStateText = (($RemoteState | Out-String).Trim() -replace "`r", '')
if ($RemoteStateExit -ne 0) {
    $Report = 'Ionoge SSH preflight failed; verify the trusted ionoge-control-01 connection. No credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
    return
}

if ($RemoteStateText -eq 'ABSENT') {
    $TemporaryRemote = "/tmp/rotate_comms5_steward_credential_$PID.py"
    $CopyResult = & scp.exe -o BatchMode=yes -o StrictHostKeyChecking=yes $UtilityPath ("{0}:{1}" -f $SshTarget, $TemporaryRemote) 2>&1
    $CopyExit = $LASTEXITCODE
    if ($CopyExit -ne 0) {
        $Report = 'Credential utility transfer failed; no production credential was changed.'
        $Report | Set-Clipboard
        Write-Host $Report
        return
    }
    $InstallCommand = "set -eu; test `$(sha256sum $TemporaryRemote | cut -d' ' -f1) = $ExpectedUtilitySha256; test ! -e $RemoteUtility; install -o root -g root -m 0755 $TemporaryRemote $RemoteUtility; rm -f $TemporaryRemote; sha256sum $RemoteUtility | cut -d' ' -f1; stat -c '%U:%G %a' $RemoteUtility"
    $InstallResult = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes $SshTarget $InstallCommand 2>&1
    $InstallExit = $LASTEXITCODE
    $InstalledHash = ($InstallResult | Out-String).Trim()
    $InstalledHash = $InstalledHash -replace "`r", ''
    $ExpectedInstalledState = "$ExpectedUtilitySha256`nroot:root 755"
    if (($InstallExit -ne 0) -or ($InstalledHash -ne $ExpectedInstalledState)) {
        $Report = 'Credential utility install or checksum verification failed; no production credential was changed.'
        $Report | Set-Clipboard
        Write-Host $Report
        return
    }
}
if (($RemoteStateText -ne 'ABSENT') -and ($RemoteStateText -ne "$ExpectedUtilitySha256 $RemoteUtility`nroot:root 755")) {
    $Report = 'A different credential utility is installed on Ionoge; it was preserved and no credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
    return
}

$CheckResult = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes $SshTarget "python3 $RemoteUtility --check" 2>&1
$CheckExit = $LASTEXITCODE
if ($CheckExit -ne 0) {
    $Report = 'Read-only credential preflight failed. Review the sanitized result below; no production credential was changed.'
    Write-Host $Report
    Write-Host ($CheckResult | Out-String).Trim()
    $Report | Set-Clipboard
    return
}

$HealthCommand = @'
set -eu
test "$(systemctl is-active caddy.service)" = active
test "$(systemctl is-active riverview-comms5-oauth.service)" = active
check() { actual=$(curl --silent --show-error --max-time 8 -o /dev/null -w '%{http_code}' "$1"); test "$actual" = "$2"; }
check http://127.0.0.1:11826/healthz 200
check http://127.0.0.1:11827/healthz 200
check https://riverview-comms.ionoge.com/.well-known/oauth-authorization-server 200
check https://riverview-comms.ionoge.com/.well-known/oauth-protected-resource 200
check https://riverview-comms.ionoge.com/comms5/mcp 401
printf 'PASS caddy=active oauth=active backend=200 oauth_health=200 discovery=200 protected_resource=200 anonymous_mcp=401'
'@
$PreRotationHealth = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes $SshTarget $HealthCommand 2>&1
$PreRotationHealthExit = $LASTEXITCODE
if ($PreRotationHealthExit -ne 0) {
    $Report = 'OAuth/Comms5 service preflight failed. No credential was changed.'
    Write-Host $Report
    Write-Host ($PreRotationHealth | Out-String).Trim()
    $Report | Set-Clipboard
    return
}

Write-Host 'Read-only preflight passed:'
Write-Host ($CheckResult | Out-String).Trim()
Write-Host ($PreRotationHealth | Out-String).Trim()
$Confirmation = Read-Host 'Rotation restarts Comms5 OAuth and Caddy and invalidates direct clients using the old bearer. Confirm those clients are accounted for; type ROTATE only after Steward approval'
if ($Confirmation -cne 'ROTATE') {
    $Report = 'Preflight passed; rotation was not authorized and no production credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
    return
}

$Bytes = New-Object byte[] 48
$Rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$Credential = $null
try {
    $Rng.GetBytes($Bytes)
    $Credential = [Convert]::ToBase64String($Bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    Set-Clipboard -Value $Credential
}
catch {
    $Report = 'Local secure credential generation or clipboard setup failed; no production credential was changed.'
    $Report | Set-Clipboard
    Write-Host $Report
    $Rng.Dispose()
    $Bytes = $null
    return
}
$Rng.Dispose()

$InstallResult = $Credential | & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes $SshTarget "python3 $RemoteUtility --install-from-stdin" 2>&1
$InstallExit = $LASTEXITCODE
if ($InstallExit -ne 0) {
    Set-Clipboard -Value ''
    $Report = 'Credential rotation failed or rolled back. The clipboard was cleared. Review the sanitized utility result; do not retry blindly.'
    Write-Host $Report
    Write-Host ($InstallResult | Out-String).Trim()
    $Report | Set-Clipboard
    $Credential = $null
    $Bytes = $null
    return
}

$PostRotationHealth = & ssh.exe -T -o BatchMode=yes -o StrictHostKeyChecking=yes $SshTarget $HealthCommand 2>&1
$PostRotationHealthExit = $LASTEXITCODE
Write-Host ($InstallResult | Out-String).Trim()
if ($PostRotationHealthExit -eq 0) {
    $Report = "Credential installed; OAuth and Comms5 checks passed. The new value is on the clipboard and was not printed. Complete the OAuth login, then clear the clipboard with Set-Clipboard -Value ''."
    Write-Host ($PostRotationHealth | Out-String).Trim()
    Write-Host $Report
}
if ($PostRotationHealthExit -ne 0) {
    $Report = 'Credential rotation reported success, but a post-rotation service check failed. The credential remains on the clipboard; do not retry. Use the protected predecessor path printed above and the runbook recovery procedure.'
    Write-Host $Report
    Write-Host ($PostRotationHealth | Out-String).Trim()
}
$Credential = $null
$Bytes = $null
