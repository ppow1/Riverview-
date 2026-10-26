#!/usr/bin/env python3
# Revision: 1.0.0
"""Allowlisted root-side controller for the OCTOMINER1 RTX 4090 workloads.

SSH access is intended to be restricted to this forced command. This program
does not accept command paths, unit names, ports, shell fragments, or GPU IDs
from the caller.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from uuid import UUID, uuid4


ROOT = Path("/var/lib/riverview-gpu-control")
JOBS = ROOT / "jobs"
AUDIT = ROOT / "audit.jsonl"
LOCK = ROOT / "transition.lock"
HOST_IP = "192.168.1.160"
CAMRUI_IP = "192.168.1.155"
COMFY_UNIT = "riverview-comfyui.service"
VISION_UNIT = "grace-vision.service"
UNITS = {"comfyui": COMFY_UNIT, "vision": VISION_UNIT}
OPS = {
    "start_comfyui": ("start", "comfyui"), "stop_comfyui": ("stop", "comfyui"),
    "switch_to_comfyui": ("switch", "comfyui"),
    "start_vision": ("start", "vision"), "stop_vision": ("stop", "vision"),
    "switch_to_vision": ("switch", "vision"),
}
MAX_JOB_BYTES = 8192
SAFE_ACTOR = re.compile(r"^steward:camrui$")
SAFE_JOB = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


class ControlError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _run(argv: list[str], timeout: float = 4) -> str:
    try:
        result = subprocess.run(argv, check=True, capture_output=True, text=True,
                                timeout=timeout, env={"LC_ALL": "C", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
    except subprocess.TimeoutExpired:
        raise ControlError("host_command_timeout") from None
    except subprocess.CalledProcessError:
        raise ControlError("host_command_failed") from None
    if len(result.stdout.encode()) > MAX_JOB_BYTES:
        raise ControlError("host_output_too_large")
    return result.stdout.strip()


def _http_json(path: str, timeout: float = 2):
    if path not in {"/queue", "/system_stats", "/slots", "/health"}:
        raise ControlError("endpoint_not_allowlisted")
    port = 8188 if path in {"/queue", "/system_stats"} else 18080
    request = __import__("urllib.request", fromlist=["Request"]).Request(
        f"http://{HOST_IP}:{port}{path}", headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_JOB_BYTES + 1)
            if response.status != 200 or len(raw) > MAX_JOB_BYTES:
                raise ControlError("service_response_invalid")
        if path == "/health":
            return {"healthy": True}
        return json.loads(raw)
    except ControlError:
        raise
    except (OSError, ValueError, URLError, HTTPError, json.JSONDecodeError):
        raise ControlError("service_probe_unavailable") from None


def _unit(unit: str) -> dict:
    if unit not in UNITS.values():
        raise ControlError("unit_not_allowlisted")
    values = {}
    for name in ("LoadState", "ActiveState", "SubState", "MainPID", "ControlGroup"):
        values[name] = _run(["/usr/bin/systemctl", "show", f"--property={name}", "--value", unit])
    if values["LoadState"] != "loaded":
        raise ControlError("service_unit_unavailable")
    try:
        pid = int(values["MainPID"] or "0")
    except ValueError:
        raise ControlError("service_state_invalid") from None
    return {"unit": unit, "active": values["ActiveState"] == "active",
            "active_state": values["ActiveState"], "sub_state": values["SubState"],
            "main_pid": pid, "control_group": values["ControlGroup"]}


def _gpu_identity() -> tuple[str, str]:
    vision = Path("/usr/local/bin/grace-vision-fast").read_text(encoding="utf-8")
    env = Path("/etc/riverview/comfyui.env").read_text(encoding="utf-8")
    v = re.search(r"^export CUDA_VISIBLE_DEVICES=(GPU-[0-9A-Fa-f-]{36})$", vision, re.M)
    c = re.search(r"^CUDA_VISIBLE_DEVICES=(GPU-[0-9A-Fa-f-]{36})$", env, re.M)
    if not v or not c or v.group(1) != c.group(1):
        raise ControlError("workloads_do_not_share_verified_gpu")
    rows = _run(["/usr/bin/nvidia-smi", "--query-gpu=uuid,name,memory.used,memory.total",
                 "--format=csv,noheader,nounits"], timeout=3).splitlines()
    for row in rows:
        parts = [p.strip() for p in row.split(",", 3)]
        if len(parts) == 4 and parts[0] == v.group(1):
            if "4090" not in parts[1]:
                raise ControlError("target_gpu_identity_mismatch")
            try:
                used, total = int(parts[2]), int(parts[3])
            except ValueError:
                raise ControlError("gpu_memory_unavailable") from None
            return parts[1], json.dumps({"used_mib": used, "total_mib": total})
    raise ControlError("target_gpu_unavailable")


def _gpu_clients() -> list[int]:
    raw = _run(["/usr/bin/nvidia-smi", "--query-compute-apps=gpu_uuid,pid",
                "--format=csv,noheader,nounits"], timeout=3)
    target, _ = _gpu_identity()
    # Resolve the configured UUID from service configuration, never a caller value.
    script = Path("/usr/local/bin/grace-vision-fast").read_text(encoding="utf-8")
    uuid = re.search(r"^export CUDA_VISIBLE_DEVICES=(GPU-[0-9A-Fa-f-]{36})$", script, re.M).group(1)
    clients = []
    for line in raw.splitlines():
        fields = [part.strip() for part in line.split(",", 1)]
        if len(fields) == 2 and fields[0] == uuid:
            try:
                clients.append(int(fields[1]))
            except ValueError:
                raise ControlError("gpu_process_inventory_invalid") from None
    return clients


def _cgroup_pids(unit_state: dict) -> set[int]:
    group = unit_state.get("control_group", "")
    if not group.startswith("/system.slice/") or ".." in group:
        raise ControlError("service_cgroup_unavailable")
    path = Path("/sys/fs/cgroup") / group.lstrip("/") / "cgroup.procs"
    try:
        values = path.read_text().split()
        return {int(value) for value in values}
    except (OSError, ValueError):
        if unit_state["active"]:
            raise ControlError("service_process_inventory_unavailable") from None
        return set()


def _queue_state(service: str) -> dict:
    if service == "comfyui":
        queue = _http_json("/queue")
        running, pending = queue.get("queue_running"), queue.get("queue_pending")
        if not isinstance(running, list) or not isinstance(pending, list):
            raise ControlError("comfyui_queue_schema_invalid")
        return {"running": len(running), "pending": len(pending), "active": bool(running or pending)}
    slots = _http_json("/slots")
    if isinstance(slots, dict):
        slots = slots.get("slots")
    if not isinstance(slots, list):
        raise ControlError("vision_slot_schema_invalid")
    active = 0
    for slot in slots:
        if not isinstance(slot, dict) or slot.get("state") not in {"idle", "processing"}:
            raise ControlError("vision_slot_schema_invalid")
        active += slot["state"] == "processing"
    return {"active_requests": active, "active": active > 0}


def status() -> dict:
    units = {name: _unit(unit) for name, unit in UNITS.items()}
    try:
        gpu_name, memory_json = _gpu_identity()
        memory = json.loads(memory_json)
        gpu = {"state": "available", "name": gpu_name, **memory}
    except (OSError, ControlError, ValueError):
        gpu = {"state": "unavailable", "reason": "verified_target_gpu_unavailable"}
    queues = {}
    for name, state in units.items():
        if state["active"]:
            try:
                _ready(name)
                queues[name] = {"state": "available", "readiness": "ready", **_queue_state(name)}
            except ControlError as exc:
                queues[name] = {"state": "unavailable", "readiness": "unavailable",
                                "reason": exc.code, "active": None}
        else:
            queues[name] = {"state": "inactive", "readiness": "not_running", "active": False}
    active_job = None
    try:
        candidates = sorted((p for p in JOBS.glob("*.json") if p.is_file() and not p.is_symlink()),
                           key=lambda p: p.stat().st_mtime, reverse=True)[:128]
        for path in candidates:
            try:
                item = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if item.get("state") in {"queued", "checking_state", "stopping_service",
                    "stopping_conflicting_service", "verifying_vram_release",
                    "verifying_vram_before_start", "starting_service", "waiting_for_readiness"}:
                active_job = {key:item.get(key) for key in ("job_id", "operation", "state", "updated_at")}
                break
    except OSError:
        pass
    return {"schema_version": "rv.gpu-workload-control.v1", "services": {
        "comfyui": {k: v for k, v in units["comfyui"].items() if k != "control_group"},
        "vision": {k: v for k, v in units["vision"].items() if k != "control_group"}},
        "queues": queues, "gpu": gpu, "active_job": active_job,
        "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def _write(path: Path, item: dict):
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(item, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temp, 0o640)
    os.replace(temp, path)


def _audit(job: dict, event: str, result: str):
    item = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "job_id": job["job_id"], "actor_id": job["actor_id"],
            "operation": job["operation"], "event": event, "result": result}
    JOBS.mkdir(mode=0o750, parents=True, exist_ok=True)
    fd = os.open(AUDIT, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o640)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        record = (json.dumps(item, sort_keys=True) + "\n").encode()
        if os.write(fd, record) != len(record):
            raise ControlError("audit_record_write_failed")
        os.fsync(fd)
    finally:
        os.close(fd)


def _update(job: dict, state: str, code: str | None = None):
    job["state"] = state
    job["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if code:
        job["error_code"] = code
    _write(JOBS / f"{job['job_id']}.json", job)
    _audit(job, state, code or "none")


def _check_safe_to_stop(service: str):
    own = _unit(UNITS[service])
    if not own["active"]:
        return own
    queue = _queue_state(service)
    if queue["active"]:
        raise ControlError("active_requests_or_jobs")
    clients = _gpu_clients()
    allowed = _cgroup_pids(own) | _cgroup_pids(_unit(UNITS["vision" if service == "comfyui" else "comfyui"]))
    if any(pid not in allowed for pid in clients):
        raise ControlError("unrelated_gpu_process_active")
    return own


def _wait_inactive(service: str, seconds: int = 45):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        unit = _unit(UNITS[service])
        if (unit["active_state"] == "inactive" and unit["main_pid"] == 0
                and not _cgroup_pids(unit)):
            return
        time.sleep(1)
    raise ControlError("service_stop_timeout")


def _verify_vram_release():
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if _gpu_clients():
            time.sleep(1)
            continue
        _, memory_json = _gpu_identity()
        memory = json.loads(memory_json)
        if memory["used_mib"] <= 1024:
            return
        time.sleep(1)
    raise ControlError("target_gpu_memory_not_released_or_unrelated_process_active")


def _ready(service: str):
    if service == "comfyui":
        _http_json("/system_stats")
        _http_json("/queue")
    else:
        _http_json("/health")
        _queue_state("vision")


def _wait_ready(service: str, seconds: int):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        unit = _unit(UNITS[service])
        if unit["active"]:
            try:
                _ready(service)
                return
            except ControlError:
                pass
        time.sleep(2)
    raise ControlError("service_readiness_timeout")


def _perform(job: dict):
    mode, target = OPS[job["operation"]]
    opposite = "vision" if target == "comfyui" else "comfyui"
    lock_fd = os.open(LOCK, os.O_CREAT | os.O_RDWR, 0o640)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ControlError("another_transition_is_in_progress") from None
        _update(job, "checking_state")
        current = {name: _unit(unit) for name, unit in UNITS.items()}
        vram_verified = False
        if current["comfyui"]["active"] and current["vision"]["active"]:
            raise ControlError("both_gpu_services_active")
        _gpu_identity()  # Verify both existing unit mappings target the same RTX 4090.
        if mode == "stop":
            if current[target]["active"]:
                _check_safe_to_stop(target)
                _update(job, "stopping_service")
                _run(["/usr/bin/systemctl", "stop", "--no-block", UNITS[target]])
                _wait_inactive(target)
                _update(job, "verifying_vram_release")
                _verify_vram_release()
                vram_verified = True
            _update(job, "succeeded")
            return
        if mode == "start" and current[opposite]["active"]:
            raise ControlError("conflicting_service_active_use_switch")
        if mode == "switch" and current[opposite]["active"]:
            _check_safe_to_stop(opposite)
            _update(job, "stopping_conflicting_service")
            _run(["/usr/bin/systemctl", "stop", "--no-block", UNITS[opposite]])
            _wait_inactive(opposite)
            _update(job, "verifying_vram_release")
            _verify_vram_release()
            vram_verified = True
        if not _unit(UNITS[target])["active"]:
            if not vram_verified:
                _update(job, "verifying_vram_before_start")
                _verify_vram_release()
            _update(job, "starting_service")
            _run(["/usr/bin/systemctl", "start", "--no-block", UNITS[target]])
        _update(job, "waiting_for_readiness")
        _wait_ready(target, 600 if target == "vision" else 180)
        _update(job, "succeeded")
    finally:
        os.close(lock_fd)


def _worker(job_id: str) -> int:
    if os.geteuid() != 0 or not SAFE_JOB.fullmatch(job_id):
        return 2
    path = JOBS / f"{job_id}.json"
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
        if job.get("job_id") != job_id or job.get("operation") not in OPS:
            return 2
        _perform(job)
    except ControlError as exc:
        job = locals().get("job", {"job_id": job_id, "actor_id": "unknown", "operation": "unknown"})
        _update(job, "failed", exc.code)
    except Exception:
        job = locals().get("job", {"job_id": job_id, "actor_id": "unknown", "operation": "unknown"})
        _update(job, "failed", "controller_internal_error")
    return 0


def serve(original: str, stdin=None) -> int:
    if os.geteuid() != 0:
        return 2
    if original == "status":
        result = status()
    elif original.startswith("job:"):
        job_id = original[4:]
        if not SAFE_JOB.fullmatch(job_id):
            result = {"error": "job_id_invalid"}
            print(json.dumps(result, sort_keys=True))
            return 2
        path = JOBS / f"{job_id}.json"
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except OSError:
            result = {"error": "job_not_found"}
    elif original.startswith("submit:"):
        _, operation, job_id, actor = (original.split(":", 3) + [""])[:4]
        # Canonical actor and UUID checks keep the SSH command grammar bounded.
        if operation not in OPS or not SAFE_JOB.fullmatch(job_id) or not SAFE_ACTOR.fullmatch(actor):
            print(json.dumps({"error": "operation_not_allowlisted"}, sort_keys=True))
            return 2
        JOBS.mkdir(mode=0o750, parents=True, exist_ok=True)
        path = JOBS / f"{job_id}.json"
        if path.exists():
            print(json.dumps({"error": "job_id_conflict"}, sort_keys=True))
            return 2
        job = {"job_id": job_id, "actor_id": actor, "operation": operation,
               "state": "queued", "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _write(path, job)
        _audit(job, "queued", "none")
        env = {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C", "HOME": "/root"}
        try:
            subprocess.Popen(["/usr/bin/python3", "/usr/local/sbin/riverview-gpu-workload-control", "_worker", job_id],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True, env=env)
        except OSError:
            _update(job, "failed", "worker_launch_failed")
            print(json.dumps({"error": "worker_launch_failed"}, sort_keys=True))
            return 1
        result = {"job_id": job_id, "state": "queued"}
    else:
        result = {"error": "operation_not_allowlisted"}
        print(json.dumps(result, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "_worker" and len(argv) == 2 and not os.environ.get("SSH_ORIGINAL_COMMAND"):
        return _worker(argv[1])
    if argv or not os.environ.get("SSH_ORIGINAL_COMMAND"):
        return 2
    try:
        return serve(os.environ["SSH_ORIGINAL_COMMAND"])
    except ControlError as exc:
        print(json.dumps({"error": exc.code}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
