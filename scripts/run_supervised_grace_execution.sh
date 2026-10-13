#!/usr/bin/env bash
# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/run_supervised_grace_execution.sh
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.1
# Purpose: Run one selected Grace Engineering objective with the owner's ChatGPT CLI session
# Execution Model: Interactive transient systemd unit with protected Riverview credentials
# Observability: Objective ID and sanitized runner result; no auth data or prompt logging
# Dependencies: Camrui systemd, installed Grace release, exact pre-provisioned credentials/grants
# Authority: Does not create grants; existing dispatch, execution, and verification checks remain required
# Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Add a no-copy, TTY-bound subscription execution command
# Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Pin the installed Codex binary and source checkout
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md; process_graphs/grace/operational-integration.json
# Tests: bash -n scripts/run_supervised_grace_execution.sh
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
set -euo pipefail
umask 077

if [[ "$(id -un)" != "admin1" || ! -t 0 ]]; then
  printf '%s\n' 'This command must be started by admin1 from an interactive terminal.' >&2
  exit 2
fi

if [[ $# -ne 1 ]]; then
  printf '%s\n' 'Usage: scripts/run_supervised_grace_execution.sh objective:<id>' >&2
  exit 2
fi

objective_id=$1
if [[ ! "$objective_id" =~ ^objective:[A-Za-z0-9._:-]{1,120}$ ]]; then
  printf '%s\n' 'Invalid objective identity.' >&2
  exit 2
fi

state_root=/home/admin1/.local/share/riverview-grace
install -d -m 0700 "$state_root" "$state_root/workspaces" "$state_root/artifacts"
for state_dir in "$state_root" "$state_root/workspaces" "$state_root/artifacts"; do
  if [[ "$(stat -c '%u:%a' "$state_dir")" != "$(id -u):700" ]]; then
    printf '%s\n' 'Supervised state directory must be owned by admin1 with mode 0700.' >&2
    exit 2
  fi
done

unit_suffix=$(printf '%s' "$objective_id" | sha256sum | cut -c1-12)
unit_name="riverview-grace-supervised-${unit_suffix}"

sudo systemd-run --system --pty --wait --collect \
  --unit="$unit_name" \
  --property=Type=oneshot \
  --property=User=admin1 \
  --property=Group=admin1 \
  --property=WorkingDirectory=/opt/riverview-grace-execution/current \
  --property=Environment=PYTHONPATH=/opt/riverview-grace-execution/current/src:/opt/riverview-grace-execution/current/scripts \
  --property='Environment=RIVERVIEW_PG_DSN=host=127.0.0.1 port=5432 dbname=riverview user=riverview_core application_name=riverview-grace-supervised' \
  --property=Environment=RIVERVIEW_PG_SCHEMA=riverview_dev \
  --property=Environment=RIVERVIEW_AUTHORITY_SCHEMA=riverview_authority \
  --property=Environment=RIVERVIEW_KNOWLEDGE_ROOT=/opt/riverview-grace-execution/current \
  --property=Environment=RIVERVIEW_ARTIFACT_DIR="$state_root/artifacts" \
  --property=Environment=RIVERVIEW_ENGINEERING_ADAPTER=codex-cli \
  --property=Environment=RIVERVIEW_CODEX_AUTH_MODE=supervised-chatgpt \
  --property=Environment=RIVERVIEW_CODEX_EXECUTABLE=/opt/riverview-codex/bin/codex \
  --property=Environment=RIVERVIEW_CODEX_REPOSITORY_PATH=/opt/riverview-engineering-source \
  --property=Environment=RIVERVIEW_CODEX_REPOSITORY_REF=repo://riverview/engineering-source \
  --property=Environment=RIVERVIEW_CODEX_TIMEOUT_SECONDS=180 \
  --property="Environment=RIVERVIEW_SUPERVISED_OBJECTIVE_ID=$objective_id" \
  --property=EnvironmentFile=/etc/riverview/grace-execution.env \
  --property=LoadCredential=pgpass:/etc/riverview/pgpass \
  --property=LoadCredential=dispatch-token:/etc/riverview/worker/grace-dispatch.credential \
  --property=LoadCredential=worker-token:/etc/riverview/worker/grace-executor.credential \
  --property=LoadCredential=verifier-token:/etc/riverview/worker/grace-verifier.credential \
  --property=LoadCredential=resident-token:/etc/riverview/residents/grace-office.credential \
  --property=NoNewPrivileges=yes \
  --property=ProtectSystem=strict \
  --property=ProtectHome=tmpfs \
  --property=BindReadOnlyPaths=/home/admin1/.codex \
  --property="ReadWritePaths=$state_root" \
  --property=PrivateTmp=yes \
  --property=PrivateDevices=yes \
  --property=ProtectKernelTunables=yes \
  --property=ProtectKernelModules=yes \
  --property=ProtectControlGroups=yes \
  --property=RestrictSUIDSGID=yes \
  --property=LockPersonality=yes \
  --property=MemoryDenyWriteExecute=yes \
  --property='RestrictAddressFamilies=AF_INET AF_UNIX' \
  --property=CapabilityBoundingSet= \
  --property=UMask=0077 \
  --property=RuntimeMaxSec=300 \
  /opt/riverview-core/.venv/bin/python \
  /opt/riverview-grace-execution/current/scripts/run_grace_execution_service.py
