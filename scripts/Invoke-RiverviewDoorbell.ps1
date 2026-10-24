# Revision: 1.0.0
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $CamruiHost,

    [ValidateSet('Status', 'Recover', 'Login')]
    [string] $Action = 'Status',

    [string] $User = 'admin1'
)

$ErrorActionPreference = 'Stop'
$target = "$User@$CamruiHost"
$browserService = 'riverview-chatgpt-doorbell-browser.service'
$runtime = '/opt/riverview-grace-execution/current/tools/riverview_browser_runtime.cjs'

switch ($Action) {
    'Status' {
        $remote = "node $runtime --status; node /opt/riverview-grace-execution/current/tools/riverview_doorbell_bridge.cjs --preflight; systemctl --user --no-pager status $browserService"
        & ssh $target $remote
    }
    'Recover' {
        $remote = "systemctl --user restart $browserService && node $runtime --status && systemctl --user --no-pager status $browserService"
        & ssh $target $remote
    }
    'Login' {
        Write-Host 'Start VcXsrv or another Windows X server before continuing.'
        Write-Host 'The SSH X11 tunnel uses the persistent Doorbell profile. Keep this window open.'
        $remote = "systemctl --user stop $browserService && node $runtime --start && read -r -p 'Complete ChatGPT login/MFA, close the Chrome window, then press Enter to return control to the Doorbell service: ' _ && systemctl --user start $browserService && node $runtime --status"
        & ssh -Y -t $target $remote
    }
}

if ($LASTEXITCODE -ne 0) {
    throw "Riverview Doorbell $Action failed over SSH (exit $LASTEXITCODE)."
}
