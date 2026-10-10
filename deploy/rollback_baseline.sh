#!/bin/sh
# RIVERVIEW~ CONTROLLED SOURCE
# File: deploy/rollback_baseline.sh
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Restore preserved deployment symlink and exact systemd predecessor
# Execution Model: Explicit authorized operational recovery
# Observability: Verified predecessor checksum and systemd result
# Dependencies: Root, systemd, protected installer rollback directory
# Authority: No DB or credential mutation; keeps code and backups
# Changed: 2026-10-10 UTC | RV-M1.1-001 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE_COOKBOOK.md
# Tests: Camrui rollback NOT VERIFIED
# History: New file; no predecessor; Git
set -eu
[ "$(id -u)" = 0 ] || exit 2
backup=${1:?Supply the installer rollback directory}
case "$backup" in /var/backups/riverview-baseline.*) ;; *) exit 2 ;; esac
[ ! -L "$backup" ] && [ -d "$backup" ] || exit 2
[ "$(stat -c '%u:%a' "$backup")" = '0:700' ] || exit 2
exec 9>/run/riverview-baseline-install.lock
flock -n 9 || exit 2
if [ -f "$backup/previous.service" ]; then
    (cd "$backup" && sha256sum --check --strict SHA256SUMS)
fi
systemctl stop riverview-baseline.service
if [ -f "$backup/previous.release" ]; then
    previous=$(cat "$backup/previous.release")
    [ -d "$previous" ] || exit 2
    ln -s "$previous" "$backup/restore-link"
    mv -Tf "$backup/restore-link" /opt/riverview-core
fi
if [ -f "$backup/previous.service" ]; then
    cp -p "$backup/previous.service" /etc/systemd/system/riverview-baseline.service
fi
if [ ! -f "$backup/previous.service" ]; then
    rm -f /etc/systemd/system/riverview-baseline.service
fi
if [ ! -f "$backup/previous.release" ]; then
    rm -f /opt/riverview-core
fi
systemctl daemon-reload
echo 'Restored deployment configuration; identity, credentials, releases and backups retained'
