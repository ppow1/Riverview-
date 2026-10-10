#!/bin/sh
# RIVERVIEW~ CONTROLLED SOURCE
# File: deploy/install_baseline.sh
# Component: RUNTIME-BASELINE
# Revision: 1.0.0
# Purpose: Commission versioned code, OS identity and systemd credential delivery
# Execution Model: Explicit one-time operational installation; repeatable
# Observability: Checksums, retained root-only rollback records and baseline JSON
# Dependencies: Root, systemd 250+, Python 3/venv/pip, sha256sum, packaged release
# Authority: OS commissioning only; no DB writes/password reset/public-schema change
# Changed: 2026-10-10 UTC | RV-M1.1-001 | Initial implementation
# Contracts: docs/components/RUNTIME_BASELINE.md
# Tests: tests/test_runtime_baseline.py; Camrui commissioning NOT VERIFIED
# History: New file; no predecessor; Git; deployed unit backups below /var/backups
set -eu
[ "$(id -u)" = 0 ] || { echo 'Run as root on Camrui' >&2; exit 2; }
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
cd "$source_dir"
sha256sum --check --strict PACKAGE_SHA256SUMS
revision=$(cat SOURCE_COMMIT)
printf '%s\n' "$revision" | grep -Eq '^[0-9a-f]{40}$' || exit 2
release="/opt/riverview/releases/$revision"
unit=/etc/systemd/system/riverview-baseline.service
link=/opt/riverview-core
[ ! -e "$link" ] || [ -L "$link" ] || { echo 'Refuse to replace a non-symlink deployment' >&2; exit 2; }
command -v flock >/dev/null
exec 9>/run/riverview-baseline-install.lock
flock -n 9 || { echo 'Another commissioning operation is active' >&2; exit 2; }
if ! getent passwd riverview >/dev/null; then
    useradd --system --user-group --home-dir /var/lib/riverview --shell /usr/sbin/nologin riverview
fi
[ "$(id -u riverview)" != 0 ] || exit 2
getent passwd riverview | cut -d: -f7 | grep -Eq '^(/usr/sbin/nologin|/sbin/nologin|/bin/false)$' || exit 2
install -d -m 0755 /opt/riverview /opt/riverview/releases
if [ ! -e "$release" ]; then
    install -d -m 0755 "$release"
    cp -a "$source_dir/." "$release/"
    chown -R root:root "$release"
    chmod -R go-w "$release"
fi
cd "$release"
sha256sum --check --strict PACKAGE_SHA256SUMS
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install 'psycopg[binary]==3.2.10'
unset RIVERVIEW_TEST_PG_DSN RIVERVIEW_PG_DSN PGPASSWORD PGSERVICE PGSERVICEFILE PGOPTIONS
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
if [ ! -e /etc/riverview ]; then
    install -d -m 0700 /etc/riverview
fi
[ ! -L /etc/riverview ] && [ "$(stat -c '%u:%a' /etc/riverview)" = '0:700' ] || exit 2
if [ ! -e /etc/riverview/pgpass ]; then
    python3 scripts/provision_pgpass.py
fi
[ ! -L /etc/riverview/pgpass ] || exit 2
[ "$(stat -c '%u:%a' /etc/riverview/pgpass)" = '0:600' ] || { echo 'Unsafe credential ownership/mode' >&2; exit 2; }
if [ ! -e /var/lib/riverview ]; then
    install -d -o riverview -g riverview -m 0700 /var/lib/riverview
fi
[ ! -L /var/lib/riverview ] && [ "$(stat -c '%u:%a' /var/lib/riverview)" = "$(id -u riverview):700" ] || exit 2
backup=$(mktemp -d /var/backups/riverview-baseline.XXXXXXXX)
chmod 0700 "$backup"
if [ -e "$unit" ] || [ -L "$unit" ]; then
    [ ! -L "$unit" ] || { echo 'Refuse existing symlink unit' >&2; exit 2; }
    cp -p "$unit" "$backup/previous.service"
    cmp "$unit" "$backup/previous.service"
    (cd "$backup" && sha256sum previous.service > SHA256SUMS)
fi
if [ -L "$link" ]; then
    readlink "$link" > "$backup/previous.release"
fi
printf '%s\n' "$revision" > "$backup/installed.commit"
install -o root -g root -m 0644 deploy/systemd/riverview-baseline.service "$unit"
ln -s "$release" "$backup/new-link"
mv -Tf "$backup/new-link" "$link"
systemctl daemon-reload
echo "Rollback record: $backup"
systemctl start riverview-baseline.service
python3 scripts/read_baseline_report.py
