#!/bin/sh
# RIVERVIEW~ CONTROLLED SOURCE
# File: deploy/install_event_processor.sh
# Component: EVENT-PROCESSOR
# Revision: 1.0.0
# Purpose: Stage an immutable M1.3 release and isolated systemd unit
# Execution Model: Explicit root commissioning; stops only the M1.3 service
# Observability: Checksums and root-only rollback bundle under /var/backups
# Dependencies: Ubuntu systemd, Python venv/pip, riverview OS and DB accounts
# Authority: Does not change M1.1 link/unit, DB schema, credentials or enable service
# Changed: 2026-10-10 UTC | RV-M1.3-002 | Initial recoverable processor deployment
# Contracts: docs/components/EVENT_PROCESSOR_COOKBOOK.md
# Tests: POSIX shell parse; isolated acceptance; Camrui commissioning
# History: New file; Git
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run as root on Camrui' >&2; exit 2; }
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
cd "$source_dir"
sha256sum --check --strict PACKAGE_SHA256SUMS
revision=$(cat SOURCE_COMMIT)
printf '%s\n' "$revision" | grep -Eq '^[0-9a-f]{40}$' || exit 2
getent passwd riverview >/dev/null || { echo 'Missing riverview runtime account' >&2; exit 2; }
[ "$(id -u riverview)" != 0 ] || exit 2
[ -f /etc/riverview/pgpass ] && [ ! -L /etc/riverview/pgpass ] || exit 2
[ "$(stat -c '%u:%a' /etc/riverview/pgpass)" = '0:600' ] || exit 2
[ -d /opt/riverview/releases ] && [ ! -L /opt/riverview/releases ] || exit 2
[ "$(stat -c '%u' /opt/riverview/releases)" = 0 ] || exit 2
release="/opt/riverview/releases/$revision"
link=/opt/riverview-event-processor
unit=/etc/systemd/system/riverview-event-processor.service
command -v flock >/dev/null
exec 9>/run/riverview-event-processor-install.lock
flock -n 9 || { echo 'Another M1.3 deployment is active' >&2; exit 2; }

if [ -e "$release" ]; then
    [ -d "$release" ] && [ ! -L "$release" ] || exit 2
    [ "$(stat -c '%u' "$release")" = 0 ] || exit 2
    (cd "$release" && sha256sum --check --strict PACKAGE_SHA256SUMS)
    [ "$(cat "$release/SOURCE_COMMIT")" = "$revision" ] || exit 2
else
    install -d -o root -g root -m 0755 "$release"
    cp -a "$source_dir/." "$release/"
    chown -R root:root "$release"
    chmod -R a+rX "$release"
    chmod -R go-w "$release"
fi

if [ ! -x "$release/.venv/bin/python" ]; then
    python3 -m venv "$release/.venv"
fi
"$release/.venv/bin/python" -m pip install 'psycopg[binary]==3.2.10'

backup=$(mktemp -d /var/backups/riverview-event-processor.XXXXXXXX)
chmod 0700 "$backup"
if [ -e "$unit" ] || [ -L "$unit" ]; then
    [ -f "$unit" ] && [ ! -L "$unit" ] || exit 2
    cp -p "$unit" "$backup/previous.service"
fi
if [ -L "$link" ]; then
    readlink "$link" > "$backup/previous.release"
elif [ -e "$link" ]; then
    echo 'Refuse non-symlink M1.3 deployment path' >&2
    exit 2
fi
if systemctl is-enabled --quiet riverview-event-processor.service; then
    printf 'yes\n' > "$backup/was_enabled"
else
    printf 'no\n' > "$backup/was_enabled"
fi
if systemctl is-active --quiet riverview-event-processor.service; then
    printf 'yes\n' > "$backup/was_active"
    systemctl stop riverview-event-processor.service
else
    printf 'no\n' > "$backup/was_active"
fi
printf '%s\n' "$revision" > "$backup/installed.commit"
printf '%s\n' "$release" > "$backup/new.release"
for saved in previous.service previous.release was_active was_enabled installed.commit new.release; do
    if [ -f "$backup/$saved" ]; then
        (cd "$backup" && sha256sum "$saved" >> SHA256SUMS)
    fi
done
install -o root -g root -m 0644 deploy/systemd/riverview-event-processor.service "$unit"
ln -s "$release" "$backup/new-link"
mv -Tf "$backup/new-link" "$link"
systemctl daemon-reload
echo "Staged M1.3 release $revision"
echo "Rollback record: $backup"
echo 'Service remains stopped and disabled until migration verification is complete.'
