#!/usr/bin/env bash
# Riverview~ controlled operator helper
# File: owner-release-update.sh
# Revision: 1.0.2 | 2026-10-28
# Scope: Clone exact Grace owner-session predecessor, overlay two reviewed runtime files, switch/rollback its pointer.
set -Eeuo pipefail

readonly UNIT='riverview-grace-execution-owner-session.service'
readonly UNIT_FILE='/etc/systemd/system/riverview-grace-execution-owner-session.service'
readonly UNIT_SHA256='a206fe7f9bc1fc3c04acd2a7f16d376073dd7ef79eae65747bfcd4bbc43f84ca'
readonly KNOWLEDGE_DROPIN='/etc/systemd/system/riverview-grace-execution-owner-session.service.d/40-knowledge-source-root.conf'
readonly KNOWLEDGE_SHA256='c8b8a50756b8fd2a0a60008da674a0c69d94b13e5156b7fc9e749054c628ed00'
readonly SOURCE_WORKER_DROPIN='/etc/systemd/system/riverview-grace-execution-owner-session.service.d/~~~~~~~~~~~~~~~~rv-source-worker.conf'
readonly SOURCE_WORKER_SHA256='832d11c8c9ac7c759e8a4c0ed603a36988ee500a24fff82857650065db347749'
readonly CURRENT='/opt/riverview-grace-execution/current'
readonly RELEASES='/opt/riverview-grace-execution/releases'
readonly BASE_ID='9f56cb72f3bd2961babf2527a26bd843526e18ce'
readonly BASE="$RELEASES/$BASE_ID"
readonly CANDIDATE_ID='9f56cb72f3bd2961babf2527a26bd843526e18ce-grace-publication-fence-20261028-r1'
readonly CANDIDATE="$RELEASES/$CANDIDATE_ID"
readonly PIPELINE='src/riverview_core/resident_execution/pipeline.py'
readonly SERVICE='src/riverview_core/resident_execution/service.py'
readonly BASE_PIPELINE_SHA256='0d32ef4439890e37b32d0f186cda73c39d6ec171e4bb246dd298e02e7a9a0873'
readonly BASE_SERVICE_SHA256='3a31111efe3bea0910be6571cef97076dc1a9562fbc57cdff526ca2507394c2d'
readonly NEXT_PIPELINE_SHA256='dfab86a2b7dd91f9b16d444bea6b79210e3d0e3318f9f3496075617b5b27ff64'
readonly NEXT_SERVICE_SHA256='ec382d9775dc5f116f684db22ca06fa260bdcff405c640948d8f24c3bdb4d772'
readonly STAGE='/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-accepted-forward-stage/repo'
readonly IDLE_GUARD='/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-accepted-forward-stage/owner_release_guard.py'
readonly PYTHON='/opt/riverview-core/.venv/bin/python'

blocked() { printf '{"status":"BLOCKED","reason":"%s"}\n' "$1"; exit 2; }
root_required() { [[ "$EUID" -eq 0 ]] || blocked root_required; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
check_hash() { [[ -f "$1" ]] || return 1; [[ "$(sha "$1")" == "$2" ]]; }
current_target() { readlink -f "$CURRENT" 2>/dev/null || return 1; }
atomic_pointer() {
  local target="$1" temp="$CURRENT.pending.$$"
  ln -s "$target" "$temp"
  mv -Tf "$temp" "$CURRENT"
}
check_environment() {
  [[ -f "$UNIT_FILE" ]] && check_hash "$UNIT_FILE" "$UNIT_SHA256" || return 1
  [[ -f "$KNOWLEDGE_DROPIN" ]] && check_hash "$KNOWLEDGE_DROPIN" "$KNOWLEDGE_SHA256" || return 1
  [[ -f "$SOURCE_WORKER_DROPIN" ]] && check_hash "$SOURCE_WORKER_DROPIN" "$SOURCE_WORKER_SHA256" || return 1
}
check_base() {
  [[ -d "$BASE" && ! -L "$BASE" ]] || return 1
  [[ "$(cat "$BASE/SOURCE_COMMIT" 2>/dev/null || true)" == "$BASE_ID" ]] || return 1
  check_hash "$BASE/$PIPELINE" "$BASE_PIPELINE_SHA256" || return 1
  check_hash "$BASE/$SERVICE" "$BASE_SERVICE_SHA256" || return 1
}
check_stage() {
  check_hash "$IDLE_GUARD" "d6f14337de0c5adee8e093a32075f07717b7f12b092b39b120744a8d3d0a68f1" || return 1
  check_hash "/home/admin1/.local/share/riverview/engineering/Riverview/scripts/update_grace_source_worker_20261028.py" "dfd631baa181b57aeca91bc157d633f3a1a72fe73bae18453656713bafabecc7" || return 1
  check_hash "$STAGE/$PIPELINE" "$NEXT_PIPELINE_SHA256" || return 1
  check_hash "$STAGE/$SERVICE" "$NEXT_SERVICE_SHA256" || return 1
  /opt/riverview-core/.venv/bin/python - "$STAGE/$PIPELINE" "$STAGE/$SERVICE" <<'PY' >/dev/null 2>&1 || return 1
import sys
from pathlib import Path
for name in sys.argv[1:]:
    compile(Path(name).read_bytes(), name, "exec")
PY
}
check_candidate() {
  [[ -d "$CANDIDATE" && ! -L "$CANDIDATE" ]] || return 1
  check_hash "$CANDIDATE/$PIPELINE" "$NEXT_PIPELINE_SHA256" || return 1
  check_hash "$CANDIDATE/$SERVICE" "$NEXT_SERVICE_SHA256" || return 1
  # All other release files remain byte-identical to the exact predecessor.
  [[ "$(cat "$CANDIDATE/SOURCE_COMMIT" 2>/dev/null || true)" == "$BASE_ID" ]] || return 1
  /usr/bin/python3 - "$BASE" "$CANDIDATE" "$PIPELINE" "$SERVICE" <<'PY' >/dev/null 2>&1 || return 1
import hashlib, sys
from pathlib import Path
base, candidate = map(Path, sys.argv[1:3])
changed = set(sys.argv[3:])
base_paths = {p.relative_to(base).as_posix() for p in base.rglob("*")}
candidate_paths = {p.relative_to(candidate).as_posix() for p in candidate.rglob("*")}
if candidate_paths != base_paths:
    raise SystemExit(1)
for path in base.rglob("*"):
    rel = path.relative_to(base)
    target = candidate / rel
    if rel.as_posix() in changed:
        continue
    if path.is_symlink():
        if not target.is_symlink() or target.readlink() != path.readlink(): raise SystemExit(1)
    elif path.is_file():
        if not target.is_file() or hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(target.read_bytes()).digest(): raise SystemExit(1)
    elif path.is_dir() and not target.is_dir(): raise SystemExit(1)
PY
}
idle_state() {
  local allow_stopped="${1:-}"
  local output rc=0
  if [[ "$allow_stopped" == allow-stopped ]]; then
    output="$("$PYTHON" "$IDLE_GUARD" --allow-stopped 2>/dev/null)" || rc=$?
  else
    output="$("$PYTHON" "$IDLE_GUARD" 2>/dev/null)" || rc=$?
  fi
  if (( rc != 0 )); then
    [[ "$output" == BLOCKED:* ]] && printf '%s\n' "${output#BLOCKED:}" >&2 || printf '%s\n' owner_session_idle_guard_failed >&2
    return 2
  fi
  [[ "$output" == ACTIVE || "$output" == STOPPED ]] || { printf '%s\n' owner_session_idle_guard_invalid_result >&2; return 2; }
  printf '%s\n' "$output"
}
unit_ready() {
  local previous_pid='' pid state started events stable=0 n
  for n in $(seq 1 40); do
    state="$(systemctl show "$UNIT" --property=ActiveState --value 2>/dev/null || true)"
    pid="$(systemctl show "$UNIT" --property=MainPID --value 2>/dev/null || true)"
    started="$(systemctl show "$UNIT" --property=ExecMainStartTimestamp --value 2>/dev/null || true)"
    if [[ "$state" == active && "$pid" =~ ^[0-9]+$ && "$pid" -gt 1 && -n "$started" ]]; then
      events="$(journalctl --unit "$UNIT" --since "$started" --output=cat --no-pager 2>/dev/null || true)"
      if [[ "$events" == *'"event": "grace_execution_service_started"'* &&
            "$events" != *'"event": "source_change_worker_unavailable"'* ]]; then
        if [[ "$previous_pid" == "$pid" ]]; then stable=$((stable+1)); else stable=1; fi
        previous_pid="$pid"
        [[ "$stable" -ge 5 ]] && return 0
      else
        previous_pid=''; stable=0
      fi
    else
      previous_pid=''; stable=0
    fi
    sleep 1
  done
  return 1
}
usage() { printf 'Usage: %s --dry-run|--apply|--rollback\n' "$0"; }
[[ "$#" -eq 1 ]] || { usage >&2; exit 64; }
mode="$1"
[[ "$mode" == --dry-run || "$mode" == --apply || "$mode" == --rollback ]] || { usage >&2; exit 64; }

[[ -L "$CURRENT" ]] || blocked current_pointer_not_symlink
current="$(current_target)" || blocked current_pointer_unavailable
check_environment || blocked owner_unit_or_dropin_hash_mismatch
check_base || blocked predecessor_hash_mismatch
check_stage || blocked staged_candidate_hash_or_compile_mismatch

case "$mode" in
  --dry-run)
    [[ "$current" == "$BASE" ]] || blocked current_pointer_mismatch
    [[ ! -e "$CANDIDATE" && ! -L "$CANDIDATE" ]] || blocked candidate_already_exists
    idle="$(idle_state)" || blocked owner_session_idle_guard_failed
    [[ "$idle" == ACTIVE ]] || blocked owner_session_must_be_active_for_apply
    unit_ready || blocked owner_session_baseline_health_unavailable
    printf '{"status":"DRY_RUN_OK","unit":"%s","predecessor":"%s","candidate":"%s","overlay_files":["%s","%s"]}\n' "$UNIT" "$BASE" "$CANDIDATE" "$PIPELINE" "$SERVICE"
    ;;
  --apply)
    [[ "$current" == "$BASE" ]] || blocked current_pointer_mismatch
    [[ ! -e "$CANDIDATE" && ! -L "$CANDIDATE" ]] || blocked candidate_already_exists
    idle="$(idle_state)" || blocked owner_session_idle_guard_failed
    [[ "$idle" == ACTIVE ]] || blocked owner_session_must_be_active_for_apply
    root_required
    unit_ready || blocked owner_session_baseline_health_unavailable
    cp -a -- "$BASE" "$CANDIDATE"
    for rel in "$PIPELINE" "$SERVICE"; do
      owner="$(stat -c %u "$CANDIDATE/$rel")"
      group="$(stat -c %g "$CANDIDATE/$rel")"
      mode_bits="$(stat -c %a "$CANDIDATE/$rel")"
      install -o "$owner" -g "$group" -m "$mode_bits" "$STAGE/$rel" "$CANDIDATE/$rel"
    done
    check_candidate || blocked candidate_overlay_validation_failed
    check_environment || blocked owner_unit_or_dropin_changed_before_switch
    [[ "$(current_target)" == "$BASE" ]] || blocked current_pointer_changed_before_switch
    idle="$(idle_state)" || blocked owner_session_not_idle_before_switch
    [[ "$idle" == ACTIVE ]] || blocked owner_session_not_idle_before_switch
    unit_ready || blocked owner_session_baseline_health_unavailable_after_staging
    atomic_pointer "$CANDIDATE"
    if systemctl restart "$UNIT" >/dev/null 2>&1 && unit_ready; then
      printf '{"status":"UPDATED","unit":"%s","predecessor":"%s","candidate":"%s"}\n' "$UNIT" "$BASE" "$CANDIDATE"
      exit 0
    fi
    rollback_state="$(idle_state allow-stopped)" || blocked owner_session_idle_guard_failed
    atomic_pointer "$BASE"
    if systemctl restart "$UNIT" >/dev/null 2>&1 && unit_ready; then blocked candidate_health_failed_rolled_back; fi
    blocked candidate_and_rollback_health_failed
    ;;
  --rollback)
    [[ "$current" == "$CANDIDATE" ]] || blocked current_pointer_mismatch
    check_candidate || blocked candidate_hash_mismatch
    check_base || blocked predecessor_hash_mismatch
    rollback_state="$(idle_state allow-stopped)" || blocked owner_session_idle_guard_failed
    root_required
    atomic_pointer "$BASE"
    if [[ "$rollback_state" == STOPPED ]]; then
      printf '{"status":"ROLLED_BACK_STOPPED","unit":"%s","restored":"%s"}\n' "$UNIT" "$BASE"
      exit 0
    fi
    if systemctl restart "$UNIT" >/dev/null 2>&1 && unit_ready; then
      printf '{"status":"ROLLED_BACK","unit":"%s","restored":"%s"}\n' "$UNIT" "$BASE"
      exit 0
    fi
    atomic_pointer "$CANDIDATE"
    systemctl restart "$UNIT" >/dev/null 2>&1 || true
    blocked rollback_health_failed_candidate_pointer_restored
    ;;
esac
