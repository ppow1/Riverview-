# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/Start-RiverviewControlBoard-Registry.ps1
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.1
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-CONTROL-BOARD-001 | Add dynamic Windows registry view with v4 JSON fallback and timestamp reconciliation.
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-STATUS-ACCURACY-001 | Separate terminal latest result from current assignment and session status.
# Purpose: Read-only monitoring of any registered worker, session, and work order
# Execution Model: Local PowerShell refresh loop; no session or service lifecycle changes
# Observability: Worker availability, session activity, assignment, completion, and evidence shown separately
# Authority: Observational only; registration or status does not authorize execution or commissioning
# Dependencies: PowerShell 5.1+; rv.work-registry.v1 JSON
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: tests/test_work_registry_monitor.py
# =============================================================================
param(
    [string]$RegistryPath = (Join-Path $PSScriptRoot '..\..\_control\work-registry-v1.json'),
    [string]$LegacyStatusDirectory = 'A:\AI\Riverview-Development\_control',
    [string]$CamruiMonitorTarget = 'camrui',
    [string]$CamruiMonitorDirectory = '/home/admin1/projects/Riverview-New-Core/.codex-monitor',
    [int]$RefreshSeconds = 15,
    [switch]$Detailed,
    [switch]$Once
)
$ErrorActionPreference = 'SilentlyContinue'

function Read-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
    try { return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop }
    catch { return $null }
}
function Age([object]$Value) {
    if (-not $Value) { return 'unknown' }
    try {
        $seconds = [Math]::Max(0, ([DateTimeOffset]::Now - [DateTimeOffset]::Parse([string]$Value)).TotalSeconds)
        if ($seconds -lt 60) { return ('{0}s' -f [int]$seconds) }
        if ($seconds -lt 3600) { return ('{0}m' -f [int]($seconds / 60)) }
        return ('{0}h' -f [int]($seconds / 3600))
    } catch { return 'unknown' }
}
function Clip([object]$Value, [int]$Limit) {
    $text = [string]$Value
    if ($text.Length -le $Limit) { return $text }
    return $text.Substring(0, [Math]::Max(0, $Limit - 3)) + '...'
}
function Record-Array([object]$Value) {
    if ($null -eq $Value) { return @() }
    if ($Value -is [System.Collections.IDictionary]) { return @($Value.Values) }
    if ($Value.PSObject.Properties.Count -gt 0 -and $Value -isnot [array]) {
        return @($Value.PSObject.Properties | ForEach-Object { $_.Value })
    }
    return @($Value)
}
function Is-SourceReconciled([object[]]$Orders, [string]$Reference, [object]$SourceTime) {
    if (-not $SourceTime) { return $false }
    $latest = $null
    foreach ($order in $Orders) {
        if (@($order.evidence) -contains $Reference -and $order.updated_at) {
            try {
                $candidate = [DateTimeOffset]::Parse([string]$order.updated_at)
                if ($null -eq $latest -or $candidate -gt $latest) { $latest = $candidate }
            } catch { }
        }
    }
    if ($null -eq $latest) { return $false }
    try { return [DateTimeOffset]::Parse([string]$SourceTime) -le $latest }
    catch { return $false }
}
function Read-CamruiLegacy([object[]]$Orders) {
    $ssh = Get-Command ssh -ErrorAction SilentlyContinue
    if (-not $ssh -or $CamruiMonitorTarget -notmatch '^[A-Za-z0-9._-]+$' -or $CamruiMonitorDirectory -notmatch '^(/[A-Za-z0-9._-]+)+$') {
        return @()
    }
    $names = & $ssh.Source -o BatchMode=yes -o ConnectTimeout=3 $CamruiMonitorTarget `
        "find '$CamruiMonitorDirectory' -maxdepth 1 -type f -name '*.json' -printf '%f\n'" 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }
    $result = @()
    foreach ($name in $names) {
        if ([string]$name -notmatch '^[A-Za-z0-9._-]+\.json$') { continue }
        $remotePath = "$CamruiMonitorDirectory/$name"
        $raw = & $ssh.Source -o BatchMode=yes -o ConnectTimeout=3 $CamruiMonitorTarget "cat -- '$remotePath'" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $raw) { continue }
        try { $state = ($raw -join "`n") | ConvertFrom-Json -ErrorAction Stop }
        catch { continue }
        if (-not $state.task -or -not $state.status -or -not $state.updated_at) { continue }
        $reference = 'Camrui v4 monitoring source: ' + $name
        if (Is-SourceReconciled $Orders $reference $state.updated_at) { continue }
        $result += [pscustomobject]@{ Worker='UNVERIFIED'; Host='Camrui'; Session='UNVERIFIED'; Identity='UNVERIFIED'; Availability='unknown'; Activity='unknown'; Assignment=(Clip $state.task 30); AssignmentState='legacy report'; Completion=$state.status; Milestone=('{0}/{1}' -f $state.milestone,$state.milestones_total); Heartbeat=(Age $state.updated_at); Blocker=(Clip $state.blocker 36); Deliverable=$state.pr_url; Source=$reference; Detail=$state.detail; Next=$state.next_action; Evidence=$state.evidence }
    }
    return $result
}
function Show-Board {
    $snapshot = $null
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and (Test-Path -LiteralPath $RegistryPath -PathType Leaf)) {
        $json = & $python.Source (Join-Path $PSScriptRoot 'register_work.py') --registry $RegistryPath snapshot --json-file 2>$null
        if ($LASTEXITCODE -eq 0 -and $json) {
            try { $snapshot = ($json -join "`n") | ConvertFrom-Json -ErrorAction Stop }
            catch { $snapshot = $null }
        }
    }
    if (-not $snapshot) { $snapshot = Read-Json $RegistryPath }
    if ($snapshot -and $snapshot.schema_version -ne 'rv.work-registry.v1') { $snapshot = $null }
    $workers = @(); $sessions = @(); $orders = @()
    if ($snapshot) {
        $workers = Record-Array $snapshot.workers
        $sessions = Record-Array $snapshot.sessions
        $orders = Record-Array $snapshot.work_orders
    }

    Clear-Host
    Write-Host ('RIVERVIEW WORK REGISTRY BOARD   {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) -ForegroundColor Cyan
    Write-Host 'Observational inventory | identity, availability, activity, assignment, completion, and commissioning are separate' -ForegroundColor DarkGray
    Write-Host ('Registry: {0} | workers={1} sessions={2} work orders={3}' -f $RegistryPath,$workers.Count,$sessions.Count,$orders.Count)
    Write-Host 'A heartbeat or live process does not prove model reasoning; registration does not grant execution authority.' -ForegroundColor DarkGray

    $rows = @()
    foreach ($worker in $workers) {
        $workerSessions = @($sessions | Where-Object { $_.worker_id -eq $worker.worker_id })
        if (-not $workerSessions.Count) {
            $rows += [pscustomobject]@{ Worker=$worker.worker_id; Type=$worker.worker_type; Model=$worker.model_identity; Host=$worker.hostname; Session='-'; Identity='-'; Availability=$worker.status; Activity='-'; Assignment='-'; AssignmentState='-'; LatestResult='-'; Milestone='-'; Heartbeat='-'; Blocker=''; Deliverable='' }
            continue
        }
        foreach ($session in $workerSessions) {
            $linked = @($orders | Where-Object { $_.session_id -eq $session.session_id -or ($null -eq $_.session_id -and $_.worker_id -eq $worker.worker_id) })
            $latestResult = $null
            if ($linked.Count) { $latestResult = $linked | Sort-Object updated_at -Descending | Select-Object -First 1 }
            $current = $null
            if ($session.current_work_order_id) { $current = $orders | Where-Object { $_.work_order_id -eq $session.current_work_order_id } | Select-Object -First 1 }
            if ($current -and @('completed','failed','cancelled') -contains ([string]$current.status).ToLowerInvariant()) { $current = $null }
            if (-not $current -and $linked.Count) {
                $current = $linked | Where-Object { @('queued','active','blocked') -contains ([string]$_.status).ToLowerInvariant() } |
                    Sort-Object updated_at -Descending | Select-Object -First 1
            }
            $step = '-'
            if ($current -and $null -ne $current.milestone -and $null -ne $current.milestones_total) { $step = '{0}/{1}' -f $current.milestone,$current.milestones_total }
            $age = if ($session.last_heartbeat_at) { Age $session.last_heartbeat_at } else { 'unknown' }
            $latestLabel = if ($latestResult) { '{0}: {1}' -f $latestResult.status,(Clip $latestResult.title 26) } else { 'none' }
            $rows += [pscustomobject]@{
                Worker=$worker.worker_id; Type=$worker.worker_type; Model=$session.model_identity; Host=$worker.hostname; Session=$session.session_id
                Identity=$(if ($session.identity_state -eq 'unverified') { 'UNVERIFIED' } else { 'verified' })
                Availability=$session.status; Activity=$session.activity_state
                Assignment=$(if ($current) { Clip $current.title 30 } else { 'unassigned' })
                AssignmentState=$(if ($current) { $current.ownership_state } else { 'unassigned' })
                LatestResult=$latestLabel; Milestone=$step
                Heartbeat=$age; Blocker=$(if ($current) { Clip $current.blocker 36 } else { '' })
                Deliverable=$(if ($current) { $current.pull_request } elseif ($latestResult) { $latestResult.pull_request } else { '' })
            }
        }
    }
    foreach ($row in $rows) {
        Write-Host ('{0,-3} {1,-12} {2,-22} {3,-12} identity={4,-11} availability={5,-10} activity={6,-7} assignment={7} owner_state={8} latest_result={9} step={10} beat={11} model={12}' -f `
            $row.Worker,$row.Type,$row.Host,$row.Session,$row.Identity,$row.Availability,$row.Activity,
            (Clip $row.Assignment 24),$row.AssignmentState,(Clip $row.LatestResult 36),$row.Milestone,$row.Heartbeat,(Clip $row.Model 24))
        if ($row.Blocker) { Write-Host ('    BLOCKER: ' + $row.Blocker) -ForegroundColor Yellow }
        if ($row.Deliverable) { Write-Host ('    PR/DELIVERABLE: ' + $row.Deliverable) -ForegroundColor DarkGray }
    }
    $unlinked = @($orders | Where-Object { -not $_.session_id })
    if ($unlinked.Count) {
        Write-Host 'PROPOSED / UNLINKED WORK ORDERS' -ForegroundColor Cyan
        foreach ($order in $unlinked) {
            $step = '-'
            if ($null -ne $order.milestone -and $null -ne $order.milestones_total) { $step = '{0}/{1}' -f $order.milestone,$order.milestones_total }
            Write-Host ('{0} | owner={1} | assignment={2} | ownership={3} | state={4} | step={5}' -f `
                $order.work_order_id,(Clip $order.owner_label 30),(Clip $order.title 34),
                $order.ownership_state,$order.status,$step)
            if ($order.blocker) { Write-Host ('    BLOCKER: ' + (Clip $order.blocker 140)) -ForegroundColor Yellow }
            if ($order.pull_request) { Write-Host ('    PR/DELIVERABLE: ' + $order.pull_request) -ForegroundColor DarkGray }
        }
    }

    $legacy = @()
    if (Test-Path -LiteralPath $LegacyStatusDirectory -PathType Container) {
        foreach ($file in (Get-ChildItem -LiteralPath $LegacyStatusDirectory -Filter '*.json' -File)) {
            if ($file.FullName -eq $RegistryPath -or $file.Name -eq 'work-registry.json' -or $file.Name -eq 'work-registry-v1.json') { continue }
            $state = Read-Json $file.FullName
            if (-not $state -or -not $state.task -or -not $state.status) { continue }
            $reference = 'legacy v4 source: ' + $file.Name
            if (Is-SourceReconciled $orders $reference $state.updated_at) { continue }
            $legacy += [pscustomobject]@{ Worker='UNVERIFIED'; Host='Windows'; Session='UNVERIFIED'; Identity='UNVERIFIED'; Availability='unknown'; Activity='unknown'; Assignment=(Clip $state.task 30); AssignmentState='legacy report'; Completion=$state.status; Milestone=('{0}/{1}' -f $state.milestone,$state.milestones_total); Heartbeat=(Age $state.updated_at); Blocker=(Clip $state.blocker 36); Deliverable=$state.pr_url; Source=$reference; Detail=$state.detail; Next=$state.next_action; Evidence=$state.evidence }
        }
    }
    $legacy += Read-CamruiLegacy $orders
    if ($legacy.Count) {
        Write-Host 'LEGACY V4 REPORTS (unreconciled; shown for transition compatibility)' -ForegroundColor Yellow
        foreach ($item in $legacy) {
            Write-Host ('{0} {1} assignment={2} state={3} step={4} report-age={5}' -f `
                $item.Source,$item.Host,(Clip $item.Assignment 24),$item.Completion,$item.Milestone,$item.Heartbeat)
            if ($item.Blocker) { Write-Host ('    BLOCKER: ' + $item.Blocker) -ForegroundColor Yellow }
            if ($item.Deliverable) { Write-Host ('    PR/DELIVERABLE: ' + $item.Deliverable) -ForegroundColor DarkGray }
        }
    }

    Write-Host 'PRODUCTION CAPABILITY / COMMISSIONING: NOT ESTABLISHED BY THIS OBSERVATIONAL REGISTRY.' -ForegroundColor Yellow
    Write-Host 'Refresh: {0}s | Ctrl+C to stop | existing v4 board remains available as fallback.' -f $RefreshSeconds -ForegroundColor DarkGray
    if ($Detailed) {
        Write-Host 'DETAIL / EVIDENCE' -ForegroundColor Cyan
        foreach ($order in $orders) {
            Write-Host ('[{0}] {1} | owner={2} | assignment={3}' -f $order.work_order_id,$order.title,$order.owner_label,$order.ownership_state)
            if ($order.detail) { Write-Host ('  DETAIL: ' + $order.detail) }
            if ($order.blocker) { Write-Host ('  BLOCKER: ' + $order.blocker) -ForegroundColor Yellow }
            if ($order.next_action) { Write-Host ('  NEXT: ' + $order.next_action) }
            foreach ($evidence in $order.evidence) { Write-Host ('  EVIDENCE: ' + $evidence) -ForegroundColor DarkGray }
            if ($order.outcome) { Write-Host ('  OUTCOME: ' + $order.outcome) }
            if ($order.local_ai_job) {
                $job = $order.local_ai_job
                Write-Host ('  INFERENCE: model={0} endpoint-ref={1} slot={2} queue={3} correlation={4} started={5} completed={6}' -f `
                    $job.model_identity,$job.endpoint_ref,$job.slot,$job.queue_status,$job.task_correlation_id,$job.started_at,$job.completed_at)
            }
        }
        foreach ($item in $legacy) {
            Write-Host ('[LEGACY {0}] {1} | {2}' -f $item.Source,$item.Assignment,$item.Completion)
            if ($item.Detail) { Write-Host ('  DETAIL: ' + $item.Detail) }
            if ($item.Blocker) { Write-Host ('  BLOCKER: ' + $item.Blocker) -ForegroundColor Yellow }
            if ($item.Next) { Write-Host ('  NEXT: ' + $item.Next) }
            if ($item.Evidence) { Write-Host ('  EVIDENCE: ' + $item.Evidence) -ForegroundColor DarkGray }
        }
    }
}

do {
    Show-Board
    if (-not $Once) { Start-Sleep -Seconds ([Math]::Max(1, $RefreshSeconds)) }
} while (-not $Once)
