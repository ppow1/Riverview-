#!/usr/bin/env bash
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/start-riverview-codex-session.sh
# Component: UNIVERSAL-WORK-REGISTRY
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Add Linux Codex registration/startup wrapper with explicit pass-through controls.
# Purpose: Register one Linux Codex worker/session and keep a bounded heartbeat
# Execution Model: Interactive Bash wrapper around the Codex CLI
# Observability: Shared rv.work-registry.v1 JSON file
# Dependencies: Bash; Python 3.10+; Codex CLI
# Authority: Start is explicit; full-permission flags are opt-in and confer no Riverview authority
# Contracts: docs/components/WORK_REGISTRY.md; docs/components/WORK_REGISTRY.schema.json
# Tests: scripts/test_work_registry_startup.py
# =============================================================================
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "$script_dir/.." && pwd)"
export PYTHONPATH="$repository_root/src${PYTHONPATH:+:$PYTHONPATH}"

args=("$script_dir/start_riverview_codex.py")
if [[ -n "${RIVERVIEW_WORKER_ID:-}" ]]; then args+=(--worker-id "$RIVERVIEW_WORKER_ID"); fi
if [[ -n "${RIVERVIEW_SESSION_ID:-}" ]]; then args+=(--session-id "$RIVERVIEW_SESSION_ID"); fi
if [[ -n "${RIVERVIEW_WORK_TITLE:-}" ]]; then args+=(--work-title "$RIVERVIEW_WORK_TITLE"); fi
if [[ -n "${RIVERVIEW_WORK_ORDER_ID:-}" ]]; then args+=(--work-order-id "$RIVERVIEW_WORK_ORDER_ID"); fi
if [[ -n "${RIVERVIEW_CODEX_MODEL:-}" ]]; then args+=(--model "$RIVERVIEW_CODEX_MODEL"); fi
if [[ -n "${RIVERVIEW_CODEX_REASONING_EFFORT:-}" ]]; then
  args+=(--reasoning-effort "$RIVERVIEW_CODEX_REASONING_EFFORT")
fi
if [[ "${RIVERVIEW_CODEX_FULL_PERMISSIONS:-}" == "1" ]]; then
  args+=(--full-permissions)
fi
if [[ -n "${RIVERVIEW_WORK_REGISTRY_PATH:-}" ]]; then
  args+=(--registry "$RIVERVIEW_WORK_REGISTRY_PATH")
fi
args+=(-- "$@")
exec python3 "${args[@]}"
