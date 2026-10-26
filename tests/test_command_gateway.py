"""Focused tests for the bounded Comms5 Windows command gateway.

File Revision: 1.1.0
Component: COMMS5-WINDOWS-COMMAND-GATEWAY-TESTS
"""

import json
import io
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch

from riverview_core.comms5.command_gateway import (
    CALLER_ACTIONS,
    EXECUTION_ACTIONS,
    TASK_HOSTS,
    WindowsCommandAgentStore,
    WindowsCommandGateway,
    _run_windows_operation,
    _validate_agent_request,
    create_agent_handler,
)


class _Transaction:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _Ledger:
    def transaction(self):
        return _Transaction()

    def cursor(self):
        return _Transaction()


class _Authorizer:
    def __init__(self, grant_id="caller-grant"):
        self.db = _Ledger()
        self.grant_id = grant_id
        self.calls = []

    def require_principal(self, cursor, principal, action, scope):
        self.calls.append((principal, action, scope))
        if not self.grant_id:
            raise type("GrantDenied", (Exception,), {})()
        return {"principal_id": principal, "grant_id": self.grant_id}

    def require(self, cursor, credential, action, scope):
        self.calls.append(("credential", action, scope))
        return {"principal_id": "service:command-gateway", "grant_id": "execution-grant"}


class _AuthorityRegistry:
    def __init__(self, reservation_status="reserved"):
        self.reservation_status = reservation_status
        self.calls = []

    def reserve_delegated_grant(self, credential, grant_id, action, scope,
                                operation_ref, *, idempotency_key):
        self.calls.append(("reserve", credential, grant_id, action, scope,
                           operation_ref, idempotency_key))
        return {"reservation_id": "reservation-1", "status": self.reservation_status}

    def consume_delegated_grant(self, credential, reservation_id, result_ref):
        self.calls.append(("consume", credential, reservation_id, result_ref))

    def release_delegated_grant(self, credential, reservation_id, reason_code):
        self.calls.append(("release", credential, reservation_id, reason_code))


class CommandGatewayTests(unittest.TestCase):
    def test_submit_authorizes_caller_and_reserves_exact_host_execution_grant(self):
        authority, authorizer, agent = _AuthorityRegistry(), _Authorizer(), Mock()
        agent.submit.return_value = {
            "execution_id": "00000000-0000-4000-8000-000000000001",
            "execution_status": "completed", "stdout": "desktop\n", "stderr": "",
            "exit_code": 0, "audit_event_id": "audit-1", "idempotency_key": "cmd-id",
            "started_at": "2026-10-26T00:00:00+00:00", "completed_at": "2026-10-26T00:00:01+00:00",
        }
        gateway = WindowsCommandGateway(authority_registry=authority, authorizer=authorizer,
            ledger_db=_Ledger(), grantee_credential="g" * 48, agent_client=agent)
        result = gateway.submit("steward:camrui", {
            "operation": "powershell_identity", "execution_grant_id": "execution-grant",
            "idempotency_key": "acceptance-a"})
        self.assertEqual(authorizer.calls, [("steward:camrui",
            CALLER_ACTIONS["powershell_identity"], "host:desktop-ja3rpnq"),
            ("credential", EXECUTION_ACTIONS["powershell_identity"],
             "host:desktop-ja3rpnq")])
        reserve = authority.calls[0]
        self.assertEqual(reserve[:5], ("reserve", "g" * 48, "execution-grant",
            EXECUTION_ACTIONS["powershell_identity"], "host:desktop-ja3rpnq"))
        self.assertEqual(authority.calls[1], ("consume", "g" * 48, "reservation-1",
            "00000000-0000-4000-8000-000000000001"))
        self.assertEqual(result["stdout"], "desktop\n")
        self.assertEqual(result["authorization_evidence"]["caller_grant_id"], "caller-grant")
        self.assertEqual(result["audit_evidence"]["audit_event_id"], "audit-1")
        agent.submit.assert_called_once()
        payload = agent.submit.call_args.args[0]
        self.assertEqual(payload["target_host"], "desktop-ja3rpnq")
        self.assertEqual(payload["privilege_level"], "standard")
        self.assertNotIn("command", payload)

    def test_denied_caller_never_reserves_or_dispatches(self):
        authority, authorizer, agent = _AuthorityRegistry(), _Authorizer(None), Mock()
        gateway = WindowsCommandGateway(authority_registry=authority, authorizer=authorizer,
            ledger_db=_Ledger(), grantee_credential="g" * 48, agent_client=agent)
        with self.assertRaises(PermissionError):
            gateway.submit("steward:camrui", {
                "operation": "ssh_camrui_hostname", "execution_grant_id": "execution-grant",
                "idempotency_key": "denied"})
        self.assertEqual(authority.calls, [])
        agent.submit.assert_not_called()

    def test_task_submission_requires_distinct_host_and_privilege_grants(self):
        authority, authorizer, agent = _AuthorityRegistry(), _Authorizer(), Mock()
        command = "Get-Service | Select-Object -First 1 Name"
        digest = __import__("hashlib").sha256(command.encode()).hexdigest()
        agent.submit.return_value = {
            "execution_id": "00000000-0000-4000-8000-000000000002",
            "execution_status": "completed", "stdout": "Spooler\n", "stderr": "",
            "exit_code": 0, "audit_event_id": "audit-task", "idempotency_key": "cmd-id",
            "started_at": "2026-10-26T00:00:00+00:00", "completed_at": "2026-10-26T00:00:01+00:00",
            "host_id": "desktop-ja3rpnq", "command_sha256": digest,
        }
        gateway = WindowsCommandGateway(authority_registry=authority, authorizer=authorizer,
            ledger_db=_Ledger(), grantee_credential="g" * 48, agent_client=agent)
        result = gateway.submit_task("steward:camrui", {
            "host_id": "desktop-ja3rpnq", "command": command,
            "privilege_level": "standard", "execution_grant_id": "execution-grant",
            "idempotency_key": "task-1"})
        action = "comms5.command.submit.task.desktop-ja3rpnq.standard"
        execution = "comms5.command.execute.task.desktop-ja3rpnq.standard"
        self.assertEqual(authorizer.calls, [("steward:camrui", action, "host:desktop-ja3rpnq"),
                                            ("credential", execution, "host:desktop-ja3rpnq")])
        self.assertEqual(authority.calls[0][3:5], (execution, "host:desktop-ja3rpnq"))
        sent = agent.submit.call_args.args[0]
        self.assertEqual(sent["command"], command)
        self.assertEqual(sent["operation"], "command_task_standard")
        self.assertEqual(sent["command_sha256"], digest) if "command_sha256" in sent else None
        self.assertEqual(result["command_sha256"], digest)
        self.assertEqual(result["authorization_evidence"]["action"], execution)

    def test_task_target_and_elevated_authority_are_exact_and_distinct(self):
        authority, authorizer, agent = _AuthorityRegistry(), _Authorizer(), Mock()
        agent.submit.return_value = {"execution_id": "exec", "execution_status": "failed",
            "stdout": "", "stderr": "", "exit_code": 1, "audit_event_id": "audit",
            "idempotency_key": "key", "host_id": "octominer1",
            "command_sha256": "a" * 64}
        gateway = WindowsCommandGateway(authority_registry=authority, authorizer=authorizer,
            ledger_db=_Ledger(), grantee_credential="g" * 48, agent_client=agent)
        gateway.submit_task("steward:camrui", {"host_id": "octominer1", "command": "id",
            "privilege_level": "elevated", "execution_grant_id": "execution-grant",
            "idempotency_key": "task-elevated"})
        self.assertIn(("steward:camrui", "comms5.command.submit.task.octominer1.elevated",
                       "host:octominer1"), authorizer.calls)
        self.assertIn(("credential", "comms5.command.execute.task.octominer1.elevated",
                       "host:octominer1"), authorizer.calls)
        with self.assertRaisesRegex(ValueError, "command_host_not_registered"):
            gateway.submit_task("steward:camrui", {"host_id": "unknown", "command": "id",
                "privilege_level": "standard", "execution_grant_id": "execution-grant",
                "idempotency_key": "task-unknown"})
        self.assertEqual(TASK_HOSTS["octominer1"][1], "host:octominer1")

    def test_task_status_requires_same_host_grant_and_command_digest(self):
        agent = Mock()
        agent.status.return_value = {"execution_id": "exec-task", "execution_status": "completed",
            "stdout": "ok", "stderr": "", "exit_code": 0, "audit_event_id": "audit-task",
            "idempotency_key": "cmd-key", "host_id": "camrui", "command_sha256": "c" * 64,
            "execution_grant_id": "executor", "reservation_id": "reservation"}
        authorizer = _Authorizer()
        gateway = WindowsCommandGateway(authority_registry=_AuthorityRegistry(), authorizer=authorizer,
            ledger_db=_Ledger(), grantee_credential="g" * 48, agent_client=agent)
        value = gateway.task_status("steward:camrui", {"host_id": "camrui",
            "command_sha256": "c" * 64, "privilege_level": "standard",
            "idempotency_key": "key-status"})
        self.assertEqual(value["status"], "completed")
        self.assertEqual(value["command_sha256"], "c" * 64)
        self.assertEqual(authorizer.calls, [("steward:camrui",
            "comms5.command.submit.task.camrui.standard", "host:camrui")])
        self.assertEqual(agent.status.call_args.args[1:], ("steward:camrui", "command_task_standard"))

    def test_task_store_persists_only_digest_and_rejects_changed_idempotent_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def runner(request, timeout):
                calls.append((request["command"], timeout))
                return "done\n", "", 0
            store = WindowsCommandAgentStore(Path(directory) / "exec.sqlite3", runner=runner)
            request = self._task_request()
            result = store.submit(request)
            replay = store.submit(request)
            self.assertEqual(result["execution_id"], replay["execution_id"])
            self.assertEqual(result["command_sha256"], __import__("hashlib").sha256(
                request["command"].encode()).hexdigest())
            self.assertEqual(calls, [(request["command"], 12)])
            with store._connect() as db:
                columns = {row[1] for row in db.execute("PRAGMA table_info(command_executions)")}
                self.assertNotIn("command", columns)
                row = db.execute("SELECT command_sha256 FROM command_executions").fetchone()
                self.assertEqual(row[0], result["command_sha256"])
            with self.assertRaisesRegex(ValueError, "idempotency_key_conflict"):
                store.submit({**request, "command": "different command"})

    def test_task_agent_rejects_host_mapping_and_command_bounds(self):
        request = self._task_request()
        with self.assertRaisesRegex(ValueError, "agent_request_not_authorized_shape"):
            _validate_agent_request({**request,
                "target_host": "octominer2"})
        with self.assertRaisesRegex(ValueError, "agent_request_not_authorized_shape"):
            _validate_agent_request({**request, "command": "x" * 9000})

    def test_runner_uses_fixed_powershell_and_pinned_ssh_invocations(self):
        class Process:
            def __init__(self):
                self.stdout, self.stderr = io.BytesIO(b"ok\\n"), io.BytesIO(b"")
            def wait(self, timeout):
                return 0
        with patch("riverview_core.comms5.command_gateway.subprocess.Popen", return_value=Process()) as popen:
            _run_windows_operation({"operation": "command_task_standard", "transport": "powershell", "privilege_level": "standard",
                "command": "Get-Date"}, 12)
            args, kwargs = popen.call_args
            self.assertEqual(args[0][-2:], ["-Command", "Get-Date"])
            self.assertIs(kwargs["shell"], False)
            popen.reset_mock()
            _run_windows_operation({"operation": "command_task_elevated", "transport": "ssh", "host_id": "octominer1",
                "privilege_level": "elevated", "command": "systemctl restart example"}, 12)
            argv = popen.call_args.args[0]
            self.assertIn("StrictHostKeyChecking=yes", argv)
            self.assertIn("ForwardAgent=no", argv)
            self.assertIn("octominer1", argv)
            self.assertTrue(argv[-1].startswith("sudo -n -- sh -lc "))
            self.assertIs(popen.call_args.kwargs["shell"], False)

    def test_agent_store_enforces_fixed_operations_idempotency_and_output_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def runner(operation, timeout):
                calls.append((operation, timeout))
                return "x" * 2000, "", 0
            store = WindowsCommandAgentStore(Path(directory) / "exec.sqlite3",
                runner=runner, output_limit=512)
            request = self._request()
            first = store.submit(request)
            replay = store.submit(request)
            self.assertEqual(first["execution_id"], replay["execution_id"])
            self.assertEqual(len(first["stdout"].encode()), 512)
            self.assertEqual(first["execution_status"], "completed")
            self.assertEqual(len(calls), 1)
            with self.assertRaisesRegex(ValueError, "idempotency_key_conflict"):
                store.submit({**request, "operation": "ssh_camrui_hostname",
                              "target_host": "camrui"})
            with self.assertRaisesRegex(ValueError, "command_operation_not_allowlisted"):
                store.submit({**request, "operation": "arbitrary_shell"})

    def test_agent_store_records_timeouts_as_terminal_audited_results(self):
        with tempfile.TemporaryDirectory() as directory:
            def runner(operation, timeout):
                raise subprocess.TimeoutExpired("fixed-probe", timeout, output=b"partial")
            store = WindowsCommandAgentStore(Path(directory) / "exec.sqlite3", runner=runner)
            result = store.submit(self._request())
            self.assertEqual(result["execution_status"], "timed_out")
            self.assertEqual(result["stdout"], "partial")
            self.assertIsNone(result["exit_code"])
            self.assertIsNotNone(result["audit_event_id"])

    def test_agent_status_is_scoped_to_original_caller_and_operation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WindowsCommandAgentStore(Path(directory) / "exec.sqlite3",
                runner=lambda op, timeout: ("host\n", "", 0))
            request = self._request()
            stored = store.submit(request)
            self.assertEqual(store.get_by_idempotency(request["idempotency_key"],
                "steward:camrui", "powershell_identity")["execution_id"], stored["execution_id"])
            self.assertEqual(store.get_by_idempotency(request["idempotency_key"],
                "steward:other", "powershell_identity")["execution_status"], "not_found")
            self.assertEqual(store.get_by_idempotency(request["idempotency_key"],
                "steward:camrui", "ssh_camrui_hostname")["execution_status"], "not_found")

    def test_agent_http_requires_bearer_and_returns_scoped_durable_result(self):
        with tempfile.TemporaryDirectory() as directory:
            store = WindowsCommandAgentStore(Path(directory) / "exec.sqlite3",
                runner=lambda op, timeout: ("desktop\n", "", 0))
            server = ThreadingHTTPServer(("127.0.0.1", 0),
                create_agent_handler(store, "a" * 48))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            body = json.dumps(self._request()).encode()
            try:
                unauthenticated = Request(base + "/v1/commands", data=body,
                    headers={"Content-Type": "application/json"})
                with self.assertRaises(HTTPError) as denied:
                    urlopen(unauthenticated, timeout=2)
                self.assertEqual(denied.exception.code, 401)
                submit = Request(base + "/v1/commands", data=body,
                    headers={"Authorization": "Bearer " + "a" * 48,
                             "Content-Type": "application/json"})
                with urlopen(submit, timeout=2) as response:
                    result = json.loads(response.read())
                self.assertEqual(result["execution_status"], "completed")
                lookup = Request(base + "/v1/commands/by-key/" + self._request()["idempotency_key"]
                    + "?principal=steward%3Acamrui&operation=powershell_identity",
                    headers={"Authorization": "Bearer " + "a" * 48})
                with urlopen(lookup, timeout=2) as response:
                    status = json.loads(response.read())
                self.assertEqual(status["execution_id"], result["execution_id"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    @staticmethod
    def _request():
        return {"operation": "powershell_identity", "target_host": "desktop-ja3rpnq",
            "privilege_level": "standard", "caller_principal": "steward:camrui",
            "caller_grant_id": "caller-grant", "execution_grant_id": "execution-grant",
            "reservation_id": "reservation-1", "idempotency_key": "cmd-" + "a" * 64}

    @staticmethod
    def _task_request():
        return {"operation": "command_task_standard", "target_host": "desktop-ja3rpnq",
            "host_id": "desktop-ja3rpnq", "transport": "powershell", "command": "Write-Output done",
            "privilege_level": "standard", "caller_principal": "steward:camrui",
            "caller_grant_id": "caller-grant", "execution_grant_id": "execution-grant",
            "reservation_id": "reservation-task", "idempotency_key": "cmd-" + "b" * 64}


if __name__ == "__main__":
    unittest.main()
