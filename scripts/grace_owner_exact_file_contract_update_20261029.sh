#!/usr/bin/env bash
# Riverview~ controlled operator helper
# File: owner-release-update-exact-file-contract.sh
# Revision: 1.0.0 | 2026-10-29
# Scope: clone exact artifact-formation-r2 release and overlay only codex_workflow.py.
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
readonly BASE_ID='9f56cb72f3bd2961babf2527a26bd843526e18ce-grace-artifact-formation-20261029-r2'
readonly BASE="$RELEASES/$BASE_ID"
readonly CANDIDATE_ID='9f56cb72f3bd2961babf2527a26bd843526e18ce-grace-exact-file-contract-20261029-r1'
readonly CANDIDATE="$RELEASES/$CANDIDATE_ID"
readonly WORKFLOW='src/riverview_core/resident_execution/codex_workflow.py'
readonly VERIFIER='src/riverview_core/resident_execution/verifier.py'
readonly PROVIDER='src/riverview_core/local_reasoning_provider.py'
readonly REASONING='src/riverview_core/resident_reasoning.py'
readonly SERVICE='src/riverview_core/resident_execution/service.py'
readonly BASE_WORKFLOW_SHA256='62aa0b6316d6f5d97d749d5bacedf2ec28f2793efa70f62a93b42ed5fd377d09'
readonly NEXT_WORKFLOW_SHA256='6c5c87e5031727de4d72455f9f8ac6d315bf73278510bb029c2429fdfbbb5571'
readonly BASE_VERIFIER_SHA256='35860d0c7e1e007a5bb0b0b9f46aa23df58aeb3ad9a01e1a0c6a9d02a8f68f63'
readonly BASE_PROVIDER_SHA256='1811b1fc57c050e12817f703c9393a8b7b2b8484fdef12fa183bd33a52c4b440'
readonly BASE_REASONING_SHA256='aa8fbd39c18d413ff814d89cb63cbdcbe8680b92bdc42d637f166e1f025cd56c'
readonly BASE_SERVICE_SHA256='73b5085d53645b1e9be20a12590e02071c0cc3fe75c51cbdf00dcf18045ad2be'
readonly STAGE='/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-artifact-exact-verifier-20261029/candidate'
readonly IDLE_GUARD='/home/admin1/.local/share/riverview/engineering/Riverview/.riverview-write-acceptance/grace-accepted-forward-stage/owner_release_guard.py'
readonly IDLE_GUARD_SHA256='d6f14337de0c5adee8e093a32075f07717b7f12b092b39b120744a8d3d0a68f1'
readonly SOURCE_UPDATER='/home/admin1/.local/share/riverview/engineering/Riverview/scripts/update_grace_source_worker_20261028.py'
readonly SOURCE_UPDATER_SHA256='dfd631baa181b57aeca91bc157d633f3a1a72fe73bae18453656713bafabecc7'
readonly PYTHON='/opt/riverview-core/.venv/bin/python'

blocked() { printf '{"status":"BLOCKED","reason":"%s"}\n' "$1"; exit 2; }
root_required() { [[ "$EUID" -eq 0 ]] || blocked root_required; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
check_hash() { [[ -f "$1" ]] && [[ "$(sha "$1")" == "$2" ]]; }
current_target() { readlink -f "$CURRENT" 2>/dev/null || return 1; }
atomic_pointer() { local tmp="$CURRENT.pending.$$"; ln -s "$1" "$tmp"; mv -Tf "$tmp" "$CURRENT"; }
check_environment() {
  check_hash "$UNIT_FILE" "$UNIT_SHA256" &&
  check_hash "$KNOWLEDGE_DROPIN" "$KNOWLEDGE_SHA256" &&
  check_hash "$SOURCE_WORKER_DROPIN" "$SOURCE_WORKER_SHA256"
}
check_base() {
  [[ -d "$BASE" && ! -L "$BASE" ]] &&
  [[ "$(cat "$BASE/SOURCE_COMMIT" 2>/dev/null || true)" == '9f56cb72f3bd2961babf2527a26bd843526e18ce' ]] &&
  check_hash "$BASE/$WORKFLOW" "$BASE_WORKFLOW_SHA256" &&
  check_hash "$BASE/$VERIFIER" "$BASE_VERIFIER_SHA256" &&
  check_hash "$BASE/$PROVIDER" "$BASE_PROVIDER_SHA256" &&
  check_hash "$BASE/$REASONING" "$BASE_REASONING_SHA256" &&
  check_hash "$BASE/$SERVICE" "$BASE_SERVICE_SHA256"
}
check_stage() {
  check_hash "$IDLE_GUARD" "$IDLE_GUARD_SHA256" &&
  check_hash "$SOURCE_UPDATER" "$SOURCE_UPDATER_SHA256" &&
  check_hash "$STAGE/$WORKFLOW" "$NEXT_WORKFLOW_SHA256" &&
  "$PYTHON" - "$STAGE/$WORKFLOW" <<'PY' >/dev/null 2>&1
import sys
from pathlib import Path
for name in sys.argv[1:]: compile(Path(name).read_bytes(), name, "exec")
PY
}
check_candidate() {
  [[ -d "$CANDIDATE" && ! -L "$CANDIDATE" ]] &&
  check_hash "$CANDIDATE/$WORKFLOW" "$NEXT_WORKFLOW_SHA256" &&
  check_hash "$CANDIDATE/$VERIFIER" "$BASE_VERIFIER_SHA256" &&
  check_hash "$CANDIDATE/$PROVIDER" "$BASE_PROVIDER_SHA256" &&
  check_hash "$CANDIDATE/$REASONING" "$BASE_REASONING_SHA256" &&
  check_hash "$CANDIDATE/$SERVICE" "$BASE_SERVICE_SHA256" &&
  [[ "$(cat "$CANDIDATE/SOURCE_COMMIT" 2>/dev/null || true)" == '9f56cb72f3bd2961babf2527a26bd843526e18ce' ]] &&
  /usr/bin/python3 - "$BASE" "$CANDIDATE" "$WORKFLOW" <<'PY' >/dev/null 2>&1
import hashlib, sys
from pathlib import Path
base, candidate = map(Path, sys.argv[1:3]); changed=set(sys.argv[3:])
base_paths={p.relative_to(base).as_posix() for p in base.rglob('*')}
candidate_paths={p.relative_to(candidate).as_posix() for p in candidate.rglob('*')}
if candidate_paths != base_paths: raise SystemExit(1)
for p in base.rglob('*'):
    rel=p.relative_to(base); q=candidate/rel
    if rel.as_posix() in changed: continue
    if p.is_symlink():
        if not q.is_symlink() or q.readlink()!=p.readlink(): raise SystemExit(1)
    elif p.is_file():
        if not q.is_file() or hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(q.read_bytes()).digest(): raise SystemExit(1)
    elif p.is_dir() and not q.is_dir(): raise SystemExit(1)
PY
}
idle_state() {
  local mode="${1:-}" output rc=0
  if [[ "$mode" == allow-stopped ]]; then output="$("$PYTHON" "$IDLE_GUARD" --allow-stopped 2>/dev/null)" || rc=$?
  else output="$("$PYTHON" "$IDLE_GUARD" 2>/dev/null)" || rc=$?; fi
  if (( rc != 0 )); then [[ "$output" == BLOCKED:* ]] && printf '%s\n' "${output#BLOCKED:}" >&2 || printf '%s\n' owner_session_idle_guard_failed >&2; return 2; fi
  [[ "$output" == ACTIVE || "$output" == STOPPED ]] || return 2
  printf '%s\n' "$output"
}
unit_ready() {
  local prev='' pid state started events stable=0 n
  for n in $(seq 1 40); do
    state="$(systemctl show "$UNIT" --property=ActiveState --value 2>/dev/null || true)"
    pid="$(systemctl show "$UNIT" --property=MainPID --value 2>/dev/null || true)"
    started="$(systemctl show "$UNIT" --property=ExecMainStartTimestamp --value 2>/dev/null || true)"
    if [[ "$state" == active && "$pid" =~ ^[0-9]+$ && "$pid" -gt 1 && -n "$started" ]]; then
      events="$(journalctl --unit "$UNIT" --since "$started" --output=cat --no-pager 2>/dev/null || true)"
      if [[ "$events" == *'"event": "grace_execution_service_started"'* && "$events" != *'"event": "source_change_worker_unavailable"'* ]]; then
        if [[ "$prev" == "$pid" ]]; then stable=$((stable+1)); else stable=1; fi
        prev="$pid"; [[ "$stable" -ge 5 ]] && return 0
      else prev=''; stable=0; fi
    else prev=''; stable=0; fi
    sleep 1
  done
  return 1
}
[[ "$#" -eq 1 && ( "$1" == --dry-run || "$1" == --apply || "$1" == --rollback ) ]] || { printf 'Usage: %s --dry-run|--apply|--rollback\n' "$0" >&2; exit 64; }
mode="$1"
[[ -L "$CURRENT" ]] || blocked current_pointer_not_symlink
current="$(current_target)" || blocked current_pointer_unavailable
check_environment || blocked owner_unit_or_dropin_hash_mismatch
check_base || blocked predecessor_hash_mismatch
check_stage || blocked staged_hash_or_compile_mismatch

case "$mode" in
  --dry-run)
    [[ "$current" == "$BASE" ]] || blocked current_pointer_mismatch
    [[ ! -e "$CANDIDATE" && ! -L "$CANDIDATE" ]] || blocked candidate_already_exists
    idle="$(idle_state)" || blocked owner_session_idle_guard_failed
    [[ "$idle" == ACTIVE ]] || blocked owner_session_must_be_active_for_apply
    unit_ready || blocked owner_session_baseline_health_unavailable
    printf '{"status":"DRY_RUN_OK","unit":"%s","predecessor":"%s","candidate":"%s","overlay_files":["%s"]}\n' "$UNIT" "$BASE" "$CANDIDATE" "$WORKFLOW"
    ;;
  --apply)
    [[ "$current" == "$BASE" ]] || blocked current_pointer_mismatch
    [[ ! -e "$CANDIDATE" && ! -L "$CANDIDATE" ]] || blocked candidate_already_exists
    idle="$(idle_state)" || blocked owner_session_idle_guard_failed
    [[ "$idle" == ACTIVE ]] || blocked owner_session_must_be_active_for_apply
    root_required
    unit_ready || blocked owner_session_baseline_health_unavailable
    cp -a -- "$BASE" "$CANDIDATE"
    for rel in "$WORKFLOW"; do
      install -o "$(stat -c %u "$CANDIDATE/$rel")" -g "$(stat -c %g "$CANDIDATE/$rel")" -m "$(stat -c %a "$CANDIDATE/$rel")" "$STAGE/$rel" "$CANDIDATE/$rel"
    done
    check_candidate || blocked candidate_overlay_validation_failed
    check_environment || blocked owner_unit_or_dropin_changed_before_switch
    [[ "$(current_target)" == "$BASE" ]] || blocked current_pointer_changed_before_switch
    idle="$(idle_state)" || blocked owner_session_not_idle_before_switch
    [[ "$idle" == ACTIVE ]] || blocked owner_session_not_idle_before_switch
    unit_ready || blocked owner_session_baseline_health_unavailable_after_staging
    atomic_pointer "$CANDIDATE"
    if systemctl restart "$UNIT" >/dev/null 2>&1 && unit_ready; then
      printf '{"status":"UPDATED","unit":"%s","predecessor":"%s","candidate":"%s"}\n' "$UNIT" "$BASE" "$CANDIDATE"; exit 0
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
    if [[ "$rollback_state" == STOPPED ]]; then printf '{"status":"ROLLED_BACK_STOPPED","unit":"%s","restored":"%s"}\n' "$UNIT" "$BASE"; exit 0; fi
    if systemctl restart "$UNIT" >/dev/null 2>&1 && unit_ready; then printf '{"status":"ROLLED_BACK","unit":"%s","restored":"%s"}\n' "$UNIT" "$BASE"; exit 0; fi
    atomic_pointer "$CANDIDATE"; systemctl restart "$UNIT" >/dev/null 2>&1 || true
    blocked rollback_health_failed_candidate_pointer_restored
    ;;
esac
