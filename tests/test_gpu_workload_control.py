from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit
import tempfile
from pathlib import Path

import pytest

from scripts import rv_gpu_workload_control as gpu
from riverview_core.status_dashboard.gpu_workload_routes import GpuWorkloadRemote, OP_ACTION, dispatch, is_route


def unit(active, name):
    return {"unit": gpu.UNITS[name], "active": active, "active_state": "active" if active else "inactive",
            "sub_state": "running" if active else "dead", "main_pid": 123 if active else 0,
            "control_group": f"/system.slice/{gpu.UNITS[name]}"}


def job(op):
    return {"job_id":"4e131dde-0794-4847-9f32-a10c52c8e047", "actor_id":"steward:camrui",
            "operation":op, "state":"queued"}


def test_only_fixed_api_routes_and_ssh_commands_are_supported():
    assert is_route("GET", "/api/v1/hardware/workloads")
    assert is_route("GET", "/api/v1/hardware/workloads/jobs/4e131dde-0794-4847-9f32-a10c52c8e047")
    assert not is_route("GET", "/api/v1/hardware/workloads/jobs/not-a-uuid")
    assert is_route("POST", "/api/v1/hardware/workloads/switch")
    assert not is_route("POST", "/api/v1/hardware/workloads/exec")
    remote = GpuWorkloadRemote.__new__(GpuWorkloadRemote)
    with pytest.raises(ValueError, match="allowlisted"):
        remote.call("submit:systemctl:4e131dde-0794-4847-9f32-a10c52c8e047:steward:camrui")


def test_dashboard_bearer_without_steward_cookie_cannot_reach_remote_controller():
    class Handler:
        command = "POST"
        _account_cookie_authenticated = False
        _account_identity = None
        server = SimpleNamespace()
        def _error(self, status, code, request_id):
            self.result = (status, code)

    handler = Handler()
    assert dispatch(handler, urlsplit("/api/v1/hardware/workloads/start"), "request")
    assert handler.result == (403, "steward_gpu_workload_authority_required")


def test_steward_submission_requires_exact_registered_authority_and_uses_fixed_operation():
    class Registry:
        def __init__(self, denied=None): self.calls, self.denied = [], denied
        def authorize(self, token, action, scope):
            self.calls.append((token, action, scope))
            if action == self.denied:
                from riverview_core.institutional_authority.registry import AuthorityDenied
                raise AuthorityDenied("not authorized")
            return {"principal_id":"steward:camrui", "principal_kind":"steward"}

    class Handler:
        command = "POST"
        _account_cookie_authenticated = True
        _account_identity = {"roles":["steward"], "authority_principal_id":"steward:camrui"}
        body = {"service":"vision"}
        def __init__(self, registry): self.server=SimpleNamespace(_comms5_operations=SimpleNamespace(authority_registry=registry))
        def _json_body(self, maximum): return self.body
        def _json(self, status, payload, request_id): self.result=(status,payload)
        def _error(self, status, code, request_id): self.result=(status,{"error":code})

    with tempfile.TemporaryDirectory() as root:
        Path(root, "authority-steward-token").write_text("protected-test-token\n")
        registry=Registry()
        handler=Handler(registry)
        with patch.dict("os.environ", {"CREDENTIALS_DIRECTORY":root}), \
             patch("riverview_core.status_dashboard.gpu_workload_routes._controller") as controller:
            def accepted(command):
                return {"job_id":command.split(":")[2],"state":"queued"}
            controller.return_value.call.side_effect=accepted
            dispatch(handler, urlsplit("/api/v1/hardware/workloads/start"), "request")
        assert handler.result[0] == 202
        assert handler.result[1]["state"] == "queued"
        assert handler.result[1]["operation"] == "start_vision"
        job_id=handler.result[1]["job_id"]
        assert registry.calls == [("protected-test-token", action, "host:octominer1") for action in OP_ACTION.values()]
        assert controller.return_value.call.call_args.args == (f"submit:start_vision:{job_id}:steward:camrui",)

        denied=Registry(denied="hardware.gpu.workload.start")
        handler=Handler(denied)
        with patch.dict("os.environ", {"CREDENTIALS_DIRECTORY":root}), \
             patch("riverview_core.status_dashboard.gpu_workload_routes._controller") as controller:
            dispatch(handler, urlsplit("/api/v1/hardware/workloads/start"), "request")
        assert handler.result == (403, {"error":"steward_gpu_workload_authority_required"})
        controller.assert_not_called()


def test_stop_refuses_active_comfyui_work_without_stopping_unit():
    calls = []
    with patch.object(gpu, "LOCK", gpu.Path("/tmp/rv-gpu-control-test.lock")), \
         patch.object(gpu, "_update"), \
         patch.object(gpu, "_unit", side_effect=lambda u: unit(u == gpu.COMFY_UNIT, "comfyui" if u == gpu.COMFY_UNIT else "vision")), \
         patch.object(gpu, "_gpu_identity", return_value=("RTX 4090", '{"used_mib":7000,"total_mib":24564}')), \
         patch.object(gpu, "_queue_state", return_value={"running":1,"pending":0,"active":True}), \
         patch.object(gpu, "_run", side_effect=lambda *args, **kwargs: calls.append(args[0])):
        with pytest.raises(gpu.ControlError, match="active_requests_or_jobs"):
            gpu._perform(job("stop_comfyui"))
    assert calls == []


def test_switch_waits_for_release_before_start_and_readiness():
    states = {"comfyui":True, "vision":False}
    commands = []
    def mocked_run(argv, **kwargs):
        commands.append(argv)
        if argv[:3] == ["/usr/bin/systemctl", "stop", "--no-block"]:
            states["comfyui"] = False
        return ""
    with patch.object(gpu, "LOCK", gpu.Path("/tmp/rv-gpu-control-switch.lock")), \
         patch.object(gpu, "_update"), \
         patch.object(gpu, "_unit", side_effect=lambda u: unit(states["comfyui" if u == gpu.COMFY_UNIT else "vision"], "comfyui" if u == gpu.COMFY_UNIT else "vision")), \
         patch.object(gpu, "_gpu_identity", return_value=("RTX 4090", '{"used_mib":0,"total_mib":24564}')), \
         patch.object(gpu, "_queue_state", return_value={"running":0,"pending":0,"active":False}), \
         patch.object(gpu, "_gpu_clients", return_value=[]), \
         patch.object(gpu, "_cgroup_pids", return_value=set()), \
         patch.object(gpu, "_wait_inactive") as stopped, \
         patch.object(gpu, "_verify_vram_release") as released, \
         patch.object(gpu, "_wait_ready") as ready, \
         patch.object(gpu, "_run", side_effect=mocked_run):
        gpu._perform(job("switch_to_vision"))
    assert [c[1] for c in commands if c[0] == "/usr/bin/systemctl"] == ["stop", "start"]
    stopped.assert_called_once_with("comfyui")
    released.assert_called_once_with()
    ready.assert_called_once_with("vision", 600)


def test_switch_does_not_start_target_when_vram_is_not_released():
    states = {"comfyui":True, "vision":False}
    commands = []
    def mocked_run(argv, **kwargs):
        commands.append(argv)
        if argv[:3] == ["/usr/bin/systemctl", "stop", "--no-block"]:
            states["comfyui"] = False
        return ""
    with patch.object(gpu, "LOCK", gpu.Path("/tmp/rv-gpu-control-vram.lock")), \
         patch.object(gpu, "_update"), \
         patch.object(gpu, "_unit", side_effect=lambda u: unit(states["comfyui" if u == gpu.COMFY_UNIT else "vision"], "comfyui" if u == gpu.COMFY_UNIT else "vision")), \
         patch.object(gpu, "_gpu_identity", return_value=("RTX 4090", '{"used_mib":7000,"total_mib":24564}')), \
         patch.object(gpu, "_queue_state", return_value={"running":0,"pending":0,"active":False}), \
         patch.object(gpu, "_gpu_clients", return_value=[]), \
         patch.object(gpu, "_cgroup_pids", return_value=set()), \
         patch.object(gpu, "_wait_inactive"), \
         patch.object(gpu, "_verify_vram_release", side_effect=gpu.ControlError("target_gpu_memory_not_released_or_unrelated_process_active")), \
         patch.object(gpu, "_run", side_effect=mocked_run):
        with pytest.raises(gpu.ControlError, match="target_gpu_memory_not_released"):
            gpu._perform(job("switch_to_vision"))
    assert not any(c[:2] == ["/usr/bin/systemctl", "start"] for c in commands)


def test_start_refuses_a_conflicting_active_unit():
    calls = []
    with patch.object(gpu, "LOCK", gpu.Path("/tmp/rv-gpu-control-conflict.lock")), \
         patch.object(gpu, "_update"), \
         patch.object(gpu, "_unit", side_effect=lambda u: unit(True, "comfyui") if u == gpu.COMFY_UNIT else unit(False, "vision")), \
         patch.object(gpu, "_gpu_identity", return_value=("RTX 4090", '{"used_mib":7000,"total_mib":24564}')), \
         patch.object(gpu, "_run", side_effect=lambda *args, **kwargs: calls.append(args[0])):
        with pytest.raises(gpu.ControlError, match="conflicting_service_active"):
            gpu._perform(job("start_vision"))
    assert calls == []


def test_stop_waits_for_exact_systemd_inactive_state_before_memory_check():
    states = ["deactivating", "inactive"]
    snapshots = [unit(False, "comfyui") | {"active_state":state,"main_pid":0}
                 for state in states]
    with patch.object(gpu, "_unit", side_effect=snapshots), \
         patch.object(gpu, "_cgroup_pids", return_value=set()), \
         patch.object(gpu.time, "sleep") as sleep:
        gpu._wait_inactive("comfyui", seconds=1)
    sleep.assert_called_once_with(1)
