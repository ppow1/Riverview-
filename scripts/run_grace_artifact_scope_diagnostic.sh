#!/usr/bin/env bash
# Riverview controlled read-only operator launcher; transient one-shot only.
set -euo pipefail
umask 077

[[ "$(id -un)" == "admin1" ]] || { printf '%s\n' 'BLOCKED: run as admin1.' >&2; exit 2; }
script=/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-artifact-scope-diagnostic-20261029/diagnose_grace_artifact_scope.py
expected_sha=ee8625ac13248cbc4a273dc8abdfbc222e6e5b19d8de6ea791668a9d420c8f0c
actual_sha=$(sha256sum "$script" | cut -d ' ' -f1)
[[ "$actual_sha" == "$expected_sha" ]] || { printf '%s\n' 'BLOCKED: diagnostic script hash mismatch.' >&2; exit 2; }

# Reuses the owner unit's existing identity, protected environment file, and only
# its existing resident-token/pgpass credentials. This does not start/restart the
# owner unit, create authority, or write objective/state data.
sudo systemd-run --system --pipe --wait --collect \
  --unit=riverview-grace-artifact-scope-diagnostic \
  --property=Type=oneshot \
  --property=User=admin1 \
  --property=Group=admin1 \
  --property=WorkingDirectory=/opt/riverview-grace-execution/current \
  --property=Environment=PYTHONPATH=/opt/riverview-grace-execution/current/src:/opt/riverview-grace-execution/current/scripts \
  --property=EnvironmentFile=/etc/riverview/grace-execution.env \
  --property=LoadCredential=resident-token:/etc/riverview/grace/resident.credential \
  --property=LoadCredential=pgpass:/etc/riverview/pgpass \
  --property=BindReadOnlyPaths="$script" \
  --property=NoNewPrivileges=yes \
  --property=ProtectSystem=strict \
  --property=ProtectHome=tmpfs \
  --property=PrivateTmp=yes \
  --property=ReadOnlyPaths=/tmp \
  --property=PrivateDevices=yes \
  --property=ProtectKernelTunables=yes \
  --property=ProtectKernelModules=yes \
  --property=ProtectControlGroups=yes \
  --property=RestrictSUIDSGID=yes \
  --property=LockPersonality=yes \
  --property=MemoryDenyWriteExecute=no \
  --property='RestrictAddressFamilies=AF_INET AF_UNIX' \
  --property=CapabilityBoundingSet= \
  --property=UMask=0077 \
  --property=RuntimeMaxSec=45 \
  /opt/riverview-core/.venv/bin/python "$script"
