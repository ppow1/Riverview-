Clear-Host
$graceReport = & {
  $graceIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
  "OPERATOR_IDENTITY=$graceIdentity"
  if ($graceIdentity -ine 'desktop-ja3rpnq\wille') { 'BLOCKED: Run this in your existing Wille PowerShell session.'; return }
  $graceEntry = '/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-verification-contract-diagnostic-20261029/run_grace_verification_contract_diagnostic.sh'
  $graceExpected = '0aad41762098a01d1ebdfbed7f427bf12a55fa4864879bf7952e3ba57305a426'
  $graceHashOutput = @(& ssh.exe -n -T -o BatchMode=yes camrui "sha256sum '$graceEntry'" 2>&1)
  $graceHashExit = $LASTEXITCODE
  "SCRIPT_HASH_SSH_EXIT_CODE=$graceHashExit"
  $graceHashOutput
  if ($graceHashExit -ne 0) { return }
  $graceHashText = ($graceHashOutput | Out-String).Trim()
  if (-not $graceHashText.StartsWith($graceExpected + ' ')) { 'BLOCKED: diagnostic launcher hash mismatch.'; return }
  & ssh.exe -n -T -o BatchMode=yes camrui "bash '$graceEntry'" 2>&1
  "DIAGNOSTIC_EXIT_CODE=$LASTEXITCODE"
} | Out-String
$graceReport
Set-Clipboard -Value $graceReport
'Report copied to clipboard.'
