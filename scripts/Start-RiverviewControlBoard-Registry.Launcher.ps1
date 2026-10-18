# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/Start-RiverviewControlBoard-Registry.Launcher.ps1
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-CONTROL-BOARD-001 | Add side-by-side development launcher; preserve v4 fallback.
# Purpose: Launch the dynamic registry board from the development control directory
# Execution Model: Read-only local monitor delegation
# Observability: Delegates current registry snapshot and legacy fallback to the dynamic monitor
# Authority: No execution, commissioning, service, or session lifecycle changes
# Dependencies: Work-Registry/scripts/Start-RiverviewControlBoard-Registry.ps1
# Contracts: docs/components/WORK_REGISTRY.md
# Tests: tests/test_work_registry_monitor.py
# =============================================================================
param(
    [int]$RefreshSeconds = 15,
    [switch]$Detailed,
    [switch]$Once
)
$ErrorActionPreference = 'Stop'
$DevelopmentRoot = $PSScriptRoot
$Board = Join-Path $PSScriptRoot 'Work-Registry\scripts\Start-RiverviewControlBoard-Registry.ps1'
if (-not (Test-Path -LiteralPath $Board -PathType Leaf)) {
    $Board = Join-Path $PSScriptRoot 'Start-RiverviewControlBoard-Registry.ps1'
    $DevelopmentRoot = Split-Path -Parent $PSScriptRoot
}
if (-not (Test-Path -LiteralPath $Board -PathType Leaf)) {
    throw 'Dynamic registry board source is unavailable.'
}
& $Board -RegistryPath (Join-Path $DevelopmentRoot '_control\work-registry-v1.json') `
    -LegacyStatusDirectory (Join-Path $DevelopmentRoot '_control') `
    -RefreshSeconds ([Math]::Max(1, $RefreshSeconds)) -Detailed:$Detailed -Once:$Once
