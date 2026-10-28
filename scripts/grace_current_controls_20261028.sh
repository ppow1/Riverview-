#!/usr/bin/env bash
# Grace cancellation + bounded verifier metadata release entry point.
# Revision: 1.0.1 | 2026-10-28 | Correct observed Dashboard port; check baseline health before writes.
# Default/--dry-run is read-only. --apply and --rollback require root on the service host.
set -Eeuo pipefail

readonly COMM_ID=b6b5ce715508590cc8e56051c00bf7ed17fdbf79
readonly DASH_ID=8325d3ffe8e53f3deaab4c9e14e471467454a08b
readonly COMM_HASH_NEXT=ed027c30449b028b191e72c816880802b8cb4c5421d3c0b1aba00669494b1c52
readonly COMM_BACKEND_NEXT=1e1368e8e8c7174273db6179cca7e8a26e2ecbbaf934b8c73578eda664bf94c8
readonly OPS_NEXT=91dff1171bd3fe631c07363665b0b045c539e69cebfb86b5035563dcc1b6ac50
readonly PIPE_NEXT=62a993f41b6536be5e8e844269d0aee9e3856361f2af251cf3205dd5ec808fd3
readonly COMM_SERVER_BASE=f857399c71489b8b58f96770d4f5b7d19b6ae5f6fbed766e743aa72d743fa0ac
readonly COMM_BACKEND_BASE=d902c6a443283b6663f4e00e7bb7b50682b4085723b2f767887c1292bdd8e550
readonly COMM_CATALOG_BASE=4d7cf965217af0ba9ab088f2f95368bfdc3286dcc5aa74ec81644b62b8f8e4b6
readonly DASH_SERVER_BASE=5675de8d75c62a86c7e3e714bdec3c88778e0f1405c14508cc5684aad865f3de
readonly OPS_BASE=997711eb1eb9cd4a69f585d0ff9ae3b632de4cb9b51e79eeb4ab38f7c1ce1d37
readonly PIPE_BASE=0d32ef4439890e37b32d0f186cda73c39d6ec171e4bb246dd298e02e7a9a0873
COMM_ROOT=/opt/riverview-comms5-camrui
DASH_ROOT=/opt/riverview-status-dashboard
readonly STAGE=/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-current-source-8325d3-stage/candidate/src

mode=${1:---dry-run}
[[ $# -le 1 ]] || { echo "usage: $0 [--dry-run|--apply|--rollback]" >&2; exit 2; }
[[ "$mode" == --dry-run || "$mode" == --apply || "$mode" == --rollback ]] || { echo "invalid_mode" >&2; exit 2; }

# A test-only root can exercise read-only guards offline. It is rejected for writes.
if [[ -n "${RIVERVIEW_CONTROLS_TEST_ROOT:-}" ]]; then
  [[ "$mode" == --dry-run ]] || { echo "test_root_is_dry_run_only" >&2; exit 2; }
  COMM_ROOT="$RIVERVIEW_CONTROLS_TEST_ROOT/comms5"
  DASH_ROOT="$RIVERVIEW_CONTROLS_TEST_ROOT/dashboard"
fi
readonly COMM_ROOT DASH_ROOT
readonly COMM_BASE="$COMM_ROOT/releases/$COMM_ID"
readonly DASH_BASE="$DASH_ROOT/releases/$DASH_ID"
readonly COMM_NEXT="$COMM_ROOT/releases/${COMM_ID}-grace-controls-20261028-r2"
readonly DASH_NEXT="$DASH_ROOT/releases/${DASH_ID}-grace-controls-20261028-r2"

fail() { echo "release_guard_failed:$1" >&2; exit 2; }
sha() { sha256sum "$1" | awk '{print $1}'; }
check_hash() { [[ -f "$1" ]] || fail "missing:$1"; [[ "$(sha "$1")" == "$2" ]] || fail "sha256:$1"; }
current_target() { readlink -f "$1/current" 2>/dev/null || fail "current_pointer_unavailable:$1"; }
set_link() {
  local root="$1" target="$2" temp="$1/.current.grace-controls.$$"
  ln -s "$target" "$temp"
  mv -Tf "$temp" "$root/current"
}
check_inputs() {
  [[ "$(current_target "$COMM_ROOT")" == "$COMM_BASE" ]] || fail "comms5_current_pointer_changed"
  [[ "$(current_target "$DASH_ROOT")" == "$DASH_BASE" ]] || fail "dashboard_current_pointer_changed"
  check_hash "$COMM_BASE/src/riverview_core/comms5/server.py" "$COMM_SERVER_BASE"
  check_hash "$COMM_BASE/src/riverview_core/comms5/dashboard_backend.py" "$COMM_BACKEND_BASE"
  check_hash "$COMM_BASE/src/riverview_core/comms5/tool_catalog.json" "$COMM_CATALOG_BASE"
  check_hash "$DASH_BASE/src/riverview_core/status_dashboard/server.py" "$DASH_SERVER_BASE"
  check_hash "$DASH_BASE/src/riverview_core/resident_execution/comms5_operations.py" "$OPS_BASE"
  check_hash "$DASH_BASE/src/riverview_core/resident_execution/pipeline.py" "$PIPE_BASE"
  check_hash "$STAGE/riverview_core/comms5/dashboard_backend.py" "$COMM_BACKEND_NEXT"
  check_hash "$STAGE/riverview_core/comms5/tool_catalog.json" "$COMM_HASH_NEXT"
  check_hash "$STAGE/riverview_core/resident_execution/comms5_operations.py" "$OPS_NEXT"
  check_hash "$STAGE/riverview_core/resident_execution/pipeline.py" "$PIPE_NEXT"
  python3 - "$STAGE" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
files=("riverview_core/comms5/dashboard_backend.py",
       "riverview_core/resident_execution/comms5_operations.py",
       "riverview_core/resident_execution/pipeline.py")
for name in files:
    path=root/name
    compile(path.read_bytes(), str(path), "exec")
json.loads((root/"riverview_core/comms5/tool_catalog.json").read_text(encoding="utf-8"))
PY
}
health() {
  local attempt http_code=unavailable phase=${1:-post_restart}
  for attempt in $(seq 1 15); do
    if systemctl is-active --quiet riverview-comms5-camrui.service &&
       systemctl is-active --quiet riverview-status-dashboard.service &&
       curl -fsS --max-time 4 http://127.0.0.1:11826/healthz -o /dev/null 2>/dev/null; then
      # Dashboard status requires its existing bearer. Do not read credentials here;
      # a 401/403 confirms the loopback HTTP handler and protected route respond.
      http_code=$(curl -sS --max-time 4 -o /dev/null -w "%{http_code}" http://127.0.0.1:8767/api/v1/status 2>/dev/null || true)
      if [[ "$http_code" == 401 || "$http_code" == 403 ]]; then return 0; fi
    fi
    sleep 2
  done
  echo "health_phase=$phase dashboard_port=8767 dashboard_http=$http_code" >&2
  echo "comms5_state=$(systemctl is-active riverview-comms5-camrui.service 2>/dev/null || true)" >&2
  echo "dashboard_state=$(systemctl is-active riverview-status-dashboard.service 2>/dev/null || true)" >&2
  fail "${phase}_health_timeout"
}

if [[ "$mode" == --dry-run ]]; then
  check_inputs
  [[ ! -e "$COMM_NEXT" && ! -e "$DASH_NEXT" ]] || fail "candidate_release_name_already_exists"
  echo "DRY_RUN_OK: exact current pointers, predecessor hashes, candidate hashes, and in-memory compile verified; no writes performed"
  echo "apply: $0 --apply"
  exit 0
fi

[[ -z "${RIVERVIEW_CONTROLS_TEST_ROOT:-}" ]] || fail "test_root_write_refused"
[[ $EUID -eq 0 ]] || fail "root_required_for_release_or_rollback"

if [[ "$mode" == --apply ]]; then
  check_inputs
  [[ ! -e "$COMM_NEXT" && ! -e "$DASH_NEXT" ]] || fail "candidate_release_name_already_exists"
  health baseline
  activated=0
  rollback_on_error() {
    local rc=$?
    trap - EXIT
    if (( rc != 0 && activated )); then
      set_link "$COMM_ROOT" "$COMM_BASE" || true
      set_link "$DASH_ROOT" "$DASH_BASE" || true
      systemctl restart riverview-comms5-camrui.service || true
      systemctl restart riverview-status-dashboard.service || true
    fi
    exit "$rc"
  }
  trap rollback_on_error EXIT
  cp -a -- "$COMM_BASE" "$COMM_NEXT"
  cp -a -- "$DASH_BASE" "$DASH_NEXT"
  install -m 0644 "$STAGE/riverview_core/comms5/dashboard_backend.py" "$COMM_NEXT/src/riverview_core/comms5/dashboard_backend.py"
  install -m 0644 "$STAGE/riverview_core/comms5/tool_catalog.json" "$COMM_NEXT/src/riverview_core/comms5/tool_catalog.json"
  install -m 0644 "$STAGE/riverview_core/resident_execution/comms5_operations.py" "$DASH_NEXT/src/riverview_core/resident_execution/comms5_operations.py"
  install -m 0644 "$STAGE/riverview_core/resident_execution/pipeline.py" "$DASH_NEXT/src/riverview_core/resident_execution/pipeline.py"
  check_hash "$COMM_NEXT/src/riverview_core/comms5/server.py" "$COMM_SERVER_BASE"
  check_hash "$COMM_NEXT/src/riverview_core/comms5/dashboard_backend.py" "$COMM_BACKEND_NEXT"
  check_hash "$COMM_NEXT/src/riverview_core/comms5/tool_catalog.json" "$COMM_HASH_NEXT"
  check_hash "$DASH_NEXT/src/riverview_core/status_dashboard/server.py" "$DASH_SERVER_BASE"
  check_hash "$DASH_NEXT/src/riverview_core/resident_execution/comms5_operations.py" "$OPS_NEXT"
  check_hash "$DASH_NEXT/src/riverview_core/resident_execution/pipeline.py" "$PIPE_NEXT"
  python3 - "$COMM_NEXT" "$DASH_NEXT" <<'PY'
import json, sys
from pathlib import Path
for root, paths in ((Path(sys.argv[1]), ("src/riverview_core/comms5/dashboard_backend.py",)),
                    (Path(sys.argv[2]), ("src/riverview_core/resident_execution/comms5_operations.py",
                                         "src/riverview_core/resident_execution/pipeline.py"))):
    for name in paths:
        path=root/name
        compile(path.read_bytes(), str(path), "exec")
json.loads((Path(sys.argv[1])/"src/riverview_core/comms5/tool_catalog.json").read_text())
PY
  set_link "$COMM_ROOT" "$COMM_NEXT"
  activated=1
  set_link "$DASH_ROOT" "$DASH_NEXT"
  systemctl restart riverview-comms5-camrui.service
  systemctl restart riverview-status-dashboard.service
  health candidate
  activated=0
  trap - EXIT
  echo "APPLY_OK: only Comms5 and Dashboard releases were switched and checked"
else
  [[ "$(current_target "$COMM_ROOT")" == "$COMM_NEXT" ]] || fail "comms5_not_on_expected_candidate"
  [[ "$(current_target "$DASH_ROOT")" == "$DASH_NEXT" ]] || fail "dashboard_not_on_expected_candidate"
  check_hash "$COMM_BASE/src/riverview_core/comms5/server.py" "$COMM_SERVER_BASE"
  check_hash "$COMM_BASE/src/riverview_core/comms5/dashboard_backend.py" "$COMM_BACKEND_BASE"
  check_hash "$COMM_BASE/src/riverview_core/comms5/tool_catalog.json" "$COMM_CATALOG_BASE"
  check_hash "$DASH_BASE/src/riverview_core/status_dashboard/server.py" "$DASH_SERVER_BASE"
  check_hash "$DASH_BASE/src/riverview_core/resident_execution/comms5_operations.py" "$OPS_BASE"
  check_hash "$DASH_BASE/src/riverview_core/resident_execution/pipeline.py" "$PIPE_BASE"
  set_link "$COMM_ROOT" "$COMM_BASE"
  set_link "$DASH_ROOT" "$DASH_BASE"
  systemctl restart riverview-comms5-camrui.service
  systemctl restart riverview-status-dashboard.service
  health rollback
  echo "ROLLBACK_OK: both exact predecessor pointers restored and checked"
fi
