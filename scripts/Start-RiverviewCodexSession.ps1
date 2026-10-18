# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/Start-RiverviewCodexSession.ps1
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Add PowerShell Codex registration/startup wrapper with explicit pass-through controls.
# Purpose: Register one Windows Codex worker/session and keep a bounded heartbeat
# Execution Model: Interactive PowerShell wrapper around the Codex CLI
# Observability: Shared rv.work-registry.v1 JSON file
# Dependencies: PowerShell 7; Python 3.10+; Codex CLI
# Authority: Start is explicit; full-permission flags are opt-in and confer no Riverview authority
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: scripts/test_work_registry_startup.py
# =============================================================================
param(
    [string]$RegistryPath = $env:RIVERVIEW_WORK_REGISTRY_PATH,
    [string]$WorkerId,
    [string]$SessionId,
    [string]$WorkTitle,
    [string]$WorkOrderId,
    [string]$Model,
    [ValidateSet('low','medium','high','xhigh','max')]
    [string]$ReasoningEffort,
    [switch]$FullPermissions,
    [string[]]$CodexArgument
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $PSScriptRoot 'start_riverview_codex.py'
$pythonPath = Join-Path $repositoryRoot 'src'
if ($env:PYTHONPATH) { $pythonPath = $pythonPath + [IO.Path]::PathSeparator + $env:PYTHONPATH }
$env:PYTHONPATH = $pythonPath
$arguments = @($runner)
if ($RegistryPath) { $arguments += @('--registry', $RegistryPath) }
if ($WorkerId) { $arguments += @('--worker-id', $WorkerId) }
if ($SessionId) { $arguments += @('--session-id', $SessionId) }
if ($WorkTitle) { $arguments += @('--work-title', $WorkTitle) }
if ($WorkOrderId) { $arguments += @('--work-order-id', $WorkOrderId) }
if ($Model) { $arguments += @('--model', $Model) }
if ($ReasoningEffort) { $arguments += @('--reasoning-effort', $ReasoningEffort) }
if ($FullPermissions) { $arguments += '--full-permissions' }
$arguments += '--'
$arguments += $CodexArgument
& python @arguments
exit $LASTEXITCODE
