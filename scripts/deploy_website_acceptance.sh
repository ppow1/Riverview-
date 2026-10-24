#!/usr/bin/env bash
# Revision: 1.0.0
set -euo pipefail

repo=${1:-$(pwd)}
release=${2:-}
if [[ $(id -u) -ne 0 ]]; then echo 'FAIL: run through passwordless sudo' >&2; exit 2; fi
if [[ ! "$release" =~ ^RV-WEB-V2-ACCEPTANCE-[A-Za-z0-9._-]{4,64}$ ]]; then
  echo 'FAIL: release ID must be RV-WEB-V2-ACCEPTANCE-<commit>' >&2; exit 2
fi

python3 "$repo/scripts/verify_v2_acceptance_candidate.py" "$repo/website/v2/deployed"
PYTHONPATH="$repo/src" python3 -m unittest tests.test_website_acceptance
[[ -f /etc/riverview/website-acceptance/personas.json && ! -L /etc/riverview/website-acceptance/personas.json ]] || { echo 'FAIL: protected persona credential is missing'; exit 2; }
[[ $(stat -c '%a' /etc/riverview/website-acceptance/personas.json) == 600 ]] || { echo 'FAIL: persona credential permissions must be 0600'; exit 2; }

stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup="/var/backups/riverview-website-acceptance/$stamp"
mkdir -p "$backup" /opt/riverview-website-acceptance/releases
chmod 0700 "$backup"
site=/etc/nginx/sites-enabled/riverview-lan
v2=/etc/nginx/snippets/riverview-v2.conf
include=/etc/nginx/snippets/riverview-website-acceptance.location.conf
install -m 0640 "$site" "$backup/riverview-lan"
install -m 0640 "$v2" "$backup/riverview-v2.conf"
install -m 0644 "$repo/deploy/nginx/riverview-website-acceptance.location.conf" "$include"

python3 - "$site" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); s=p.read_text(); line='    include /etc/nginx/snippets/riverview-website-acceptance.location.conf;\n'
marker='    include /etc/nginx/snippets/riverview-v2.conf;'
if line.strip() not in s:
    if s.count(marker)!=1: raise SystemExit('FAIL: expected unique V2 include in LAN server config')
    p.write_text(s.replace(marker,line+marker,1))
PY

target="/var/www/riverview-v2-preview/releases/$release"
if [[ -e "$target" ]]; then echo 'FAIL: immutable release path already exists'; exit 2; fi
install -d -m 0755 "$target"
cp -a "$repo/website/v2/deployed/." "$target/"
git -C "$repo" rev-parse HEAD > "$target/SOURCE_COMMIT"
python3 - "$target/release.json" "$release" "$(git -C "$repo" rev-parse HEAD)" <<'PY'
import json,sys
with open(sys.argv[1],"w",encoding="utf-8") as f:
    json.dump({"schema_version":"rv.website-release.v1","release_id":sys.argv[2],"source_commit":sys.argv[3]},f)
    f.write("\n")
PY

newv2="$backup/riverview-v2.conf.new"
python3 - "$v2" "$newv2" "$target" <<'PY'
from pathlib import Path
import re,sys
source,dest,target=sys.argv[1:]
s=Path(source).read_text()
s,n=re.subn(r'(?m)^(\s*alias )/var/www/riverview-v2-preview/releases/[^/]+/(;)$',
            lambda m:m.group(1)+target+'/'+m.group(2),s)
if n!=1: raise SystemExit('FAIL: expected one existing V2 release alias')
Path(dest).write_text(s)
PY
release_root="/opt/riverview-website-acceptance/releases/$(git -C "$repo" rev-parse --short=12 HEAD)"
if [[ -e "$release_root" ]]; then echo 'FAIL: acceptance release path already exists'; exit 2; fi
install -d -m 0755 "$release_root/scripts" "$release_root/src/riverview_core"
install -m 0755 "$repo/scripts/run_website_acceptance.py" "$repo/scripts/seed_website_test_personas.py" "$release_root/scripts/"
cp -a "$repo/src/riverview_core/account_auth" "$release_root/src/riverview_core/"
install -m 0644 "$repo/src/riverview_core/__init__.py" "$release_root/src/riverview_core/__init__.py"
install -m 0644 "$repo/deploy/systemd/riverview-website-acceptance@.service" /etc/systemd/system/
install -m 0644 "$repo/deploy/systemd/riverview-website-acceptance-light.timer" "$repo/deploy/systemd/riverview-website-acceptance-full.timer" /etc/systemd/system/
tmp_link=/opt/riverview-website-acceptance/current.new
ln -s "$release_root" "$tmp_link"
mv -Tf "$tmp_link" /opt/riverview-website-acceptance/current
install -d -m 0750 -o admin1 -g www-data /var/lib/riverview-website-acceptance
chgrp www-data /var/lib/riverview-website-acceptance/latest.json 2>/dev/null || true
chmod 0640 /var/lib/riverview-website-acceptance/latest.json 2>/dev/null || true
systemctl daemon-reload

if ! nginx -t; then
  install -m 0640 "$backup/riverview-lan" "$site"
  install -m 0640 "$backup/riverview-v2.conf" "$v2"
  exit 1
fi
systemctl reload nginx

set +e
systemctl start riverview-website-acceptance@full.service
baseline_status=$?
set -e
baseline=$(python3 -c 'import json;print(json.load(open("/var/lib/riverview-website-acceptance/latest.json"))["overall"])' 2>/dev/null || echo MISSING)
if [[ "$baseline" == FAIL || "$baseline" == MISSING || $baseline_status -ne 0 ]]; then
  install -m 0640 "$backup/riverview-lan" "$site"
  install -m 0640 "$backup/riverview-v2.conf" "$v2"
  rm -f "$include"
  nginx -t && systemctl reload nginx
  echo "BLOCKED: production baseline acceptance=$baseline; backup=$backup" >&2
  exit 1
fi

install -m 0640 "$newv2" "$v2"
if ! nginx -t; then
  install -m 0640 "$backup/riverview-v2.conf" "$v2"
  install -m 0640 "$backup/riverview-lan" "$site"
  rm -f "$include"
  exit 1
fi
systemctl reload nginx
systemctl enable --now riverview-website-acceptance-light.timer riverview-website-acceptance-full.timer

set +e
systemctl start riverview-website-acceptance@full.service
run_status=$?
set -e
overall=$(python3 -c 'import json;print(json.load(open("/var/lib/riverview-website-acceptance/latest.json"))["overall"])' 2>/dev/null || echo MISSING)
if [[ "$overall" == FAIL || "$overall" == MISSING || $run_status -ne 0 ]]; then
  install -m 0640 "$backup/riverview-lan" "$site"
  install -m 0640 "$backup/riverview-v2.conf" "$v2"
  rm -f "$include"
  nginx -t && systemctl reload nginx
  echo "ROLLED_BACK: post-deployment acceptance=$overall; backup=$backup" >&2
  exit 1
fi
echo "DEPLOYED: static_release=$release acceptance_release=$release_root pre_deployment=$baseline post_deployment=$overall backup=$backup"
