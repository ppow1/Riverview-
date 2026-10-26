from types import SimpleNamespace
# Revision: 1.0.0
from unittest.mock import patch
from urllib.parse import urlsplit
from contextlib import contextmanager
import re
import unittest
import tempfile
from pathlib import Path

from scripts import rv_gpu_workload_control as gpu
from riverview_core.status_dashboard.gpu_workload_routes import GpuWorkloadRemote, OP_ACTION, dispatch, is_route
from scripts.apply_gpu_workload_dashboard_overlay import apply as apply_dashboard_overlay
from scripts.apply_gpu_workload_ui_overlay import apply as apply_ui_overlay


@contextmanager
def _raises(expected, match):
    try:
        yield
    except expected as exc:
        if not re.search(match, str(exc)):
            raise AssertionError(f"{exc!r} did not match {match!r}") from exc
    else:
        raise AssertionError(f"expected {expected.__name__}")


def unit(active, name):
    return {"unit": gpu.UNITS[name], "active": active, "active_state": "active" if active else "inactive",
            "sub_state": "running" if active else "dead", "main_pid": 123 if active else 0,
            "control_group": f"/system.slice/{gpu.UNITS[name]}"}


def job(op):
    return {"job_id":"4e131dde-0794-4847-9f32-a10c52c8e047", "actor_id":"steward:camrui",
            "operation":op, "state":"queued"}


class Telemetry:
    def __init__(self, hosts=None, registrations=None):
        actions=("read","start","stop","switch")
        self.hosts=hosts or [
            {"host_id":"octominer1","display_name":"OCTOMINER1","identity_state":"verified",
             "workload_control":{"state":"registered","controller_id":"ctrl-1"}},
            {"host_id":"octominer2","display_name":"OctoMiner2","identity_state":"documented_unverified",
             "workload_control":{"state":"not_registered"}},
        ]
        caps=[{"capability_id":f"hardware.gpu.workload.{x}","action":f"hardware.gpu.workload.{x}"} for x in actions]
        self.registrations=registrations or {"octominer1":{"controller_id":"ctrl-1",
            "transport_host":"192.0.2.10","transport_port":22,"transport_user":"root",
            "private_key_path":"/tmp/test-gpu-key","known_hosts_credential":"resource-telemetry-known-hosts",
            "services":[{"service_id":"vision","display_name":"Vision","controller_service":"vision"},
                        {"service_id":"comfyui","display_name":"ComfyUI","controller_service":"comfyui"}],
            "capabilities":caps}}
    def read(self): return {"hosts":self.hosts}
    def workload_controller_registrations(self): return self.registrations


def test_only_fixed_api_routes_and_ssh_commands_are_supported():
    assert is_route("GET", "/api/v1/hardware/workloads")
    assert is_route("GET", "/api/v1/hardware/workloads/jobs/4e131dde-0794-4847-9f32-a10c52c8e047")
    assert not is_route("GET", "/api/v1/hardware/workloads/jobs/not-a-uuid")
    assert is_route("POST", "/api/v1/hardware/workloads/switch")
    assert not is_route("POST", "/api/v1/hardware/workloads/exec")
    remote = GpuWorkloadRemote.__new__(GpuWorkloadRemote)
    with _raises(ValueError, "allowlisted"):
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
        body = {"host_id":"octominer1","service":"vision"}
        def __init__(self, registry): self.server=SimpleNamespace(_authority_registry=registry,
            _comms5_operations=None,_resource_telemetry=Telemetry())
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
        assert registry.calls == [("protected-test-token", "hardware.gpu.workload.start", "host:octominer1")]
        assert controller.return_value.call.call_args.args == (f"submit:start_vision:{job_id}:steward:camrui",)

        denied=Registry(denied="hardware.gpu.workload.start")
        handler=Handler(denied)
        with patch.dict("os.environ", {"CREDENTIALS_DIRECTORY":root}), \
             patch("riverview_core.status_dashboard.gpu_workload_routes._controller") as controller:
            dispatch(handler, urlsplit("/api/v1/hardware/workloads/start"), "request")
        assert handler.result == (403, {"error":"steward_gpu_workload_authority_required"})
        controller.assert_not_called()


def test_steward_status_uses_dashboard_authority_registry_without_comms5_facade():
    class Registry:
        def __init__(self): self.calls=[]
        def authorize(self, token, action, scope):
            self.calls.append((action, scope))
            return {"principal_id":"steward:camrui", "principal_kind":"steward"}

    class Handler:
        command = "GET"
        _account_cookie_authenticated = True
        _account_identity = {"roles":["steward"], "authority_principal_id":"steward:camrui"}
        def __init__(self, registry): self.server=SimpleNamespace(_authority_registry=registry,
            _comms5_operations=None,_resource_telemetry=Telemetry())
        def _json(self, status, payload, request_id): self.result=(status,payload)
        def _error(self, status, code, request_id): self.result=(status,{"error":code})

    with tempfile.TemporaryDirectory() as root:
        Path(root, "authority-steward-token").write_text("protected-test-token\n")
        registry=Registry()
        handler=Handler(registry)
        status={"services":{"vision":{"active":False},"comfyui":{"active":True}},
                "queues":{"vision":{"state":"inactive"},"comfyui":{"state":"available","running":0,"pending":0}},
                "gpu":{"state":"available","used_mib":4096,"total_mib":24564}}
        with patch.dict("os.environ", {"CREDENTIALS_DIRECTORY":root}), \
             patch("riverview_core.status_dashboard.gpu_workload_routes._controller") as controller:
            controller.return_value.call.return_value=status
            dispatch(handler, urlsplit("/api/v1/hardware/workloads"), "request")
        assert handler.result[0] == 200
        host=next(row for row in handler.result[1]["hosts"] if row["host_id"]=="octominer1")
        assert host["permissions"] == {"read":True,"start":True,"stop":True,"switch":True}
        assert registry.calls == [(action,"host:octominer1") for action in OP_ACTION.values()]
        controller.return_value.call.assert_called_once_with("status")


def test_six_workload_buttons_map_to_the_four_exact_capabilities():
    root=Path(__file__).resolve().parents[1]
    html=(root/"website/v2/deployed/index.html").read_text()
    script=(root/"website/v2/deployed/assets/gpu-workload-controls.js").read_text()
    assert 'id="gpu-workload-host"' in html
    assert 'data-gpu-action="${action}"' in script
    assert 'host_id:host.host_id' in script
    assert "host:octominer1" not in script
    assert all(f'"{action}": "hardware.gpu.workload.{action}"' in
               (root/"src/riverview_core/status_dashboard/gpu_workload_routes.py").read_text()
               for action in ("read","start","stop","switch"))


def test_registered_host_mapping_accepts_distinct_simulated_octominer2_service_and_transport():
    from riverview_core.status_dashboard.gpu_workload_routes import _registration, _service
    telemetry=Telemetry()
    telemetry.hosts[1]={"host_id":"octominer2","display_name":"OctoMiner2","identity_state":"verified"}
    telemetry.registrations["octominer2"]={"controller_id":"ctrl-2","transport_host":"198.51.100.27",
        "transport_port":2222,"transport_user":"controller","private_key_path":"/tmp/octo2-key",
        "known_hosts_credential":"octo2-known-hosts","gpu_resource_ids":["gpu:test-device"],
        "services":[{"service_id":"vision-service-two","display_name":"Host two vision",
                      "controller_service":"vision"}],"capabilities":[]}
    class Handler:
        command="GET";_account_cookie_authenticated=True
        _account_identity={"roles":["steward"],"authority_principal_id":"steward:camrui"}
        def __init__(self,registry=None): self.server=SimpleNamespace(_resource_telemetry=telemetry,
            _authority_registry=registry,_comms5_operations=None)
        def _json(self,status,payload,request_id): self.result=(status,payload)
        def _error(self,status,code,request_id): self.result=(status,{"error":code})
    registration=_registration(Handler(),"octominer2")
    assert registration["transport_host"]=="198.51.100.27"
    assert registration["transport_port"]==2222
    assert _service(registration,"vision-service-two")["service_id"]=="vision-service-two"
    class Registry:
        def __init__(self):self.calls=[]
        def authorize(self,token,action,scope):
            self.calls.append((action,scope));return {"principal_id":"steward:camrui","principal_kind":"steward"}
    registry=Registry();handler=Handler(registry)
    with tempfile.TemporaryDirectory() as root:
        Path(root,"authority-steward-token").write_text("t"*64)
        with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}), \
             patch("riverview_core.status_dashboard.gpu_workload_routes._controller") as controller:
            controller.return_value.call.return_value={"services":{"vision":{"active":True}},
                "queues":{"vision":{"state":"available","active_requests":0}},
                "gpu":{"state":"available","name":"Host two GPU","used_mib":1,"total_mib":2},
                "observed_at":"now"}
            dispatch(handler,urlsplit("/api/v1/hardware/workloads?host_id=octominer2"),"r")
    assert handler.result[0]==200
    assert registry.calls[0]==("hardware.gpu.workload.read","host:octominer2")
    assert controller.call_args.args[0]["transport_host"]=="198.51.100.27"
    telemetry.hosts[1]["identity_state"]="documented_unverified"
    with _raises(LookupError,"unverified"):
        _registration(Handler(),"octominer2")


def test_delegated_host_grant_is_visible_and_reserved_for_operation_not_status_polling():
    class Registry:
        def __init__(self): self.reserved=[]; self.consumed=[]; self.released=[]
        def authorize(self,token,action,scope):
            from riverview_core.institutional_authority.registry import AuthorityDenied
            raise AuthorityDenied("no direct grant")
        def list_active_delegated_grants(self,token,action,scope):
            return [{"grant_id":"grant:gpu-test","policy_ref":"policy:delegation.v1"}]
        def reserve_delegated_grant(self,token,grant_id,action,scope,operation_ref,*,idempotency_key):
            value={"reservation_id":"resv-gpu-test","status":"reserved"}
            self.reserved.append((grant_id,action,scope,operation_ref,idempotency_key));return value
        def consume_delegated_grant(self,token,reservation_id,result_ref):
            self.consumed.append((reservation_id,result_ref));return {"status":"consumed"}
        def release_delegated_grant(self,*args): self.released.append(args)
    class Handler:
        _account_cookie_authenticated=True
        _account_identity={"roles":["steward"],"authority_principal_id":"steward:camrui"}
        def __init__(self,registry,command,body=None):
            self.command=command;self.body=body or {};self.server=SimpleNamespace(
                _authority_registry=registry,_comms5_operations=None,_resource_telemetry=Telemetry())
        def _json_body(self,maximum):return self.body
        def _json(self,status,payload,request_id):self.result=(status,payload)
        def _error(self,status,code,request_id):self.result=(status,{"error":code})
    registry=Registry();job_id="4e131dde-0794-4847-9f32-a10c52c8e047"
    with tempfile.TemporaryDirectory() as root:
        Path(root,"authority-steward-token").write_text("t"*64)
        with patch.dict("os.environ",{"CREDENTIALS_DIRECTORY":root}), \
             patch("riverview_core.status_dashboard.gpu_workload_routes._controller") as controller:
            controller.return_value.call.return_value={"job_id":job_id,"state":"queued"}
            submitted=Handler(registry,"POST",{"host_id":"octominer1","service":"vision"})
            dispatch(submitted,urlsplit("/api/v1/hardware/workloads/start"),"r")
            assert submitted.result[0]==202
            expected=("grant:gpu-test","hardware.gpu.workload.start","host:octominer1",
                f"gpu-workload:octominer1:{job_id}",job_id)
            assert registry.reserved==[expected]
            controller.return_value.call.return_value={"job_id":job_id,"operation":"start_vision","state":"succeeded"}
            completed=Handler(registry,"GET")
            dispatch(completed,urlsplit(f"/api/v1/hardware/workloads/jobs/{job_id}?host_id=octominer1"),"r")
            assert completed.result[0]==200
            assert registry.reserved==[expected,expected]
            assert registry.consumed==[("resv-gpu-test",f"gpu-workload-job:{job_id}:succeeded")]
    from riverview_core.institutional_authority.registry import AuthorityRegistry
    AuthorityRegistry._validate_delegation_scope("host:octominer1")
    with _raises(ValueError,"scope"):
        AuthorityRegistry._validate_delegation_scope("host:OCTOMINER1")


def test_stop_refuses_active_comfyui_work_without_stopping_unit():
    calls = []
    with patch.object(gpu, "LOCK", gpu.Path("/tmp/rv-gpu-control-test.lock")), \
         patch.object(gpu, "_update"), \
         patch.object(gpu, "_unit", side_effect=lambda u: unit(u == gpu.COMFY_UNIT, "comfyui" if u == gpu.COMFY_UNIT else "vision")), \
         patch.object(gpu, "_gpu_identity", return_value=("RTX 4090", '{"used_mib":7000,"total_mib":24564}')), \
         patch.object(gpu, "_queue_state", return_value={"running":1,"pending":0,"active":True}), \
         patch.object(gpu, "_run", side_effect=lambda *args, **kwargs: calls.append(args[0])):
        with _raises(gpu.ControlError, "active_requests_or_jobs"):
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
        with _raises(gpu.ControlError, "target_gpu_memory_not_released"):
            gpu._perform(job("switch_to_vision"))
    assert not any(c[:2] == ["/usr/bin/systemctl", "start"] for c in commands)


def test_start_refuses_a_conflicting_active_unit():
    calls = []
    with patch.object(gpu, "LOCK", gpu.Path("/tmp/rv-gpu-control-conflict.lock")), \
         patch.object(gpu, "_update"), \
         patch.object(gpu, "_unit", side_effect=lambda u: unit(True, "comfyui") if u == gpu.COMFY_UNIT else unit(False, "vision")), \
         patch.object(gpu, "_gpu_identity", return_value=("RTX 4090", '{"used_mib":7000,"total_mib":24564}')), \
         patch.object(gpu, "_run", side_effect=lambda *args, **kwargs: calls.append(args[0])):
        with _raises(gpu.ControlError, "conflicting_service_active"):
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


def test_audit_record_is_appended_and_fsynced_without_credentials():
    import json
    from unittest.mock import Mock
    job={"job_id":"4e131dde-0794-4847-9f32-a10c52c8e047","actor_id":"steward:camrui",
         "operation":"switch_to_vision"}
    with tempfile.TemporaryDirectory() as root, \
         patch.object(gpu,"ROOT",Path(root)), patch.object(gpu,"JOBS",Path(root)/"jobs"), \
         patch.object(gpu,"AUDIT",Path(root)/"audit.jsonl"), patch.object(gpu.os,"fsync",Mock()) as sync:
        gpu._audit(job,"queued","none")
        row=json.loads((Path(root)/"audit.jsonl").read_text())
        assert row["actor_id"]=="steward:camrui" and row["event"]=="queued"
        assert "password" not in row and "token" not in row
        sync.assert_called_once()


def test_composite_dashboard_overlay_is_bounded_valid_and_idempotent():
    source = (
        'def handle():\n'
        '            delegation_route = (path == "/api/v1/steward")\n'
        '            allowed = (\n'
        '                    True\n'
        '                    and not delegation_revoke\n'
        '            )\n'
        '            conversation_session = (parsed.path == _CONVERSATION_SESSION\n'
        '                                     and self.command == "GET")\n'
        '            if delegation_route:\n'
        '                dispatch(self, parsed, request_id)\n'
        '                return\n'
        '            if snapshot_archive:\n'
        '                identity = getattr(self, "_account_identity", None)\n'
        '                process_snapshot()\n'
        '            v2_asset = re.fullmatch(r"/v2/assets/(favicon\\.svg|workspace\\.css|fixtures\\.js|workspace\\.js|snapshot\\.js)", parsed.path)\n')
    output = apply_dashboard_overlay(source)
    compile(output, "composite-server.py", "exec")
    assert "hardware.gpu.workload.switch" in output
    assert "gpu_workload_routes import dispatch" in output
    assert "gpu-workload-controls\\.js" in output
    assert apply_dashboard_overlay(output) == output


def test_deployed_v2_ui_overlay_preserves_existing_page_and_inserts_one_control_panel():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    feature=(root/"website/v2/deployed/index.html").read_text()
    baseline=('  <link rel="stylesheet" href="assets/delegation-approvals.css?rev=steward-delegation-refresh-76b02cfb">\n'
              '  <script defer src="assets/delegation-approvals.js?rev=steward-delegation-refresh-76b02cfb"></script>\n'
              '                    <p class="resource-footnote">Queue contents are not exposed. ComfyUI CUDA device numbers are separate from host NVIDIA indices and physical chassis bays.</p>\n'
              '<main id="existing-dashboard-features">preserve existing features</main>\n')
    result=apply_ui_overlay(baseline,feature)
    assert result.count('id="gpu-workload-controls"') == 1
    assert 'id="existing-dashboard-features">preserve existing features' in result
    assert apply_ui_overlay(result,feature) == result


class GPUWorkloadControlTests(unittest.TestCase):
    """Expose the focused cases to the repository's unittest CI runner."""
    def test_only_fixed_api_routes_and_ssh_commands_are_supported(self):
        test_only_fixed_api_routes_and_ssh_commands_are_supported()

    def test_bearer_without_steward_cookie_is_denied(self):
        test_dashboard_bearer_without_steward_cookie_cannot_reach_remote_controller()

    def test_exact_registered_authority_is_required(self):
        test_steward_submission_requires_exact_registered_authority_and_uses_fixed_operation()

    def test_status_uses_dashboard_registry_without_comms5(self):
        test_steward_status_uses_dashboard_authority_registry_without_comms5_facade()

    def test_six_controls_map_to_four_capabilities(self):
        test_six_workload_buttons_map_to_the_four_exact_capabilities()

    def test_active_comfyui_work_refuses_stop(self):
        test_stop_refuses_active_comfyui_work_without_stopping_unit()

    def test_switch_waits_for_release_and_readiness(self):
        test_switch_waits_for_release_before_start_and_readiness()

    def test_switch_refuses_unreleased_vram(self):
        test_switch_does_not_start_target_when_vram_is_not_released()

    def test_start_refuses_conflicting_unit(self):
        test_start_refuses_a_conflicting_active_unit()

    def test_stop_waits_for_exact_inactive_state(self):
        test_stop_waits_for_exact_systemd_inactive_state_before_memory_check()

    def test_audit_is_durable_and_sanitized(self):
        test_audit_record_is_appended_and_fsynced_without_credentials()

    def test_dashboard_source_overlay_is_bounded(self):
        test_composite_dashboard_overlay_is_bounded_valid_and_idempotent()

    def test_ui_overlay_preserves_existing_release(self):
        test_deployed_v2_ui_overlay_preserves_existing_page_and_inserts_one_control_panel()
