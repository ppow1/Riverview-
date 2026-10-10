#!/bin/sh
# RIVERVIEW~ CONTROLLED SOURCE
# File: deploy/rollback_event_processor.sh
# Component: EVENT-PROCESSOR
# Revision: 1.0.0
# Purpose: Restore the prior M1.3 release pointer and exact unit
# Execution Model: Explicit root recovery; database cursor data remains durable
# Observability: Validated root-only rollback bundle and systemd result
# Dependencies: systemd, flock, recorded M1.3 deployment backup
# Authority: Never reverses migrations, removes data, or changes M1.1 deployment
# Changed: 2026-10-10 UTC | RV-M1.3-002 | Initial M1.3 service recovery path
# Contracts: docs/components/EVENT_PROCESSOR_COOKBOOK.md
# Tests: POSIX shell parse; isolated recovery acceptance; Camrui commissioning
# History: New file; Git
set -eu
[ "$(id -u)" = 0 ] || exit 2
backup=${1:?Supply the root-only event processor deployment backup}
case "$backup" in /var/backups/riverview-event-processor.*) ;; *) exit 2 ;; esac
[ -d "$backup" ] && [ ! -L "$backup" ] || exit 2
[ "$(stat -c '%u:%a' "$backup")" = '0:700' ] || exit 2
exec 9>/run/riverview-event-processor-install.lock
flock -n 9 || exit 2
if [ -f "$backup/SHA256SUMS" ]; then
    (cd "$backup" && sha256sum --check --strict SHA256SUMS)
fi
if [ -e "$backup/previous.release" ]; then
    previous=$(cat "$backup/previous.release")
    case "$previous" in /opt/riverview/releases/[0-9a-f][0-9a-f]*) ;; *) exit 2 ;; esac
    printf '%s\n' "$previous" | grep -Eq '^/opt/riverview/releases/[0-9a-f]{40}$' || exit 2
    [ -d "$previous" ] && [ ! -L "$previous" ] || exit 2
    [ "$(stat -c '%u' "$previous")" = 0 ] || exit 2
fi
systemctl stop riverview-event-processor.service 2>/dev/null || true
if [ -e "$backup/previous.release" ]; then
    ln -s "$previous" "$backup/restore-link"
    mv -Tf "$backup/restore-link" /opt/riverview-event-processor
else
    rm -f /opt/riverview-event-processor
fi
if [ -f "$backup/previous.service" ]; then
    cp -p "$backup/previous.service" /etc/systemd/system/riverview-event-processor.service
else
    rm -f /etc/systemd/system/riverview-event-processor.service
fi
systemctl daemon-reload
if [ "$(cat "$backup/was_enabled")" = yes ] && [ -f "$backup/previous.service" ]; then
    systemctl enable riverview-event-processor.service
else
    systemctl disable riverview-event-processor.service 2>/dev/null || true
fi
if [ "$(cat "$backup/was_active")" = yes ] && [ -f "$backup/previous.service" ]; then
    systemctl start riverview-event-processor.service
fi
echo 'Restored prior M1.3 runtime configuration; PostgreSQL migration and cursor remain preserved.'
