#!/bin/sh
# RIVERVIEW~ CONTROLLED SOURCE
# File: deploy/install_baseline.sh
# Component: RUNTIME-BASELINE
# Revision: 1.0.1
# Purpose: Commission versioned code, isolated qualification, and systemd credential delivery
# Execution Model: Explicit one-time operational installation; repeatable
# Observability: Checksums, retained root-only rollback records and baseline JSON
# Dependencies: Root, systemd 250+, Python 3/venv/pip, runuser, sha256sum, packaged release
# Authority: OS commissioning only; no DB writes/password reset/public-schema change
# Changed: 2026-10-10 UTC | RV-M1.1-007 | Recover partial releases and normalize read access
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
command -v runuser >/dev/null
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
fi
[ -d "$release" ] && [ ! -L "$release" ] || { echo 'Refuse a non-directory or symlink release' >&2; exit 2; }
[ "$(stat -c '%u' "$release")" = 0 ] || { echo 'Refuse a non-root-owned release' >&2; exit 2; }
if find "$release" ! -user root -print -quit | grep -q .; then
    echo 'Refuse release content not owned by root' >&2
    exit 2
fi
cd "$release"
sha256sum --check --strict PACKAGE_SHA256SUMS
# cp -a of a mode-0700 staging root also applies that mode to the release root.
# After validating package bytes, make files readable and directories traversable
# by the service, then remove group/other write access. This also repairs the same
# safe partial release on rerun without changing package bytes or ownership.
chmod -R a+rX "$release"
chmod -R go-w "$release"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install 'psycopg[binary]==3.2.10'
unset RIVERVIEW_TEST_PG_DSN RIVERVIEW_PG_DSN PGPASSWORD PGSERVICE PGSERVICEFILE PGOPTIONS
install -d -o root -g root -m 0755 /opt/riverview/qualification
[ ! -L /opt/riverview/qualification ] && [ "$(stat -c '%u:%a' /opt/riverview/qualification)" = '0:755' ] || exit 2
qualification_root=$(mktemp -d "/opt/riverview/qualification/$revision.XXXXXXXX")
chmod 0755 "$qualification_root"
python3 -m venv "$qualification_root/venv"
"$qualification_root/venv/bin/python" -m pip install --disable-pip-version-check --upgrade 'pip==24.3.1'
"$qualification_root/venv/bin/python" -m pip install --disable-pip-version-check --no-deps --only-binary=:all: -r deploy/qualification-requirements.txt
chmod -R a+rX "$qualification_root"
runuser -u riverview -- env HOME=/var/lib/riverview TMPDIR=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src \
    "$qualification_root/venv/bin/pytest" -p no:cacheprovider -q tests
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
