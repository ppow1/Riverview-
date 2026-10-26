"""Focused tests for the bounded Comms5 Windows command gateway.

File Revision: 1.0.0
Component: COMMS5-WINDOWS-COMMAND-GATEWAY-TESTS
"""

import json
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock

from riverview_core.comms5.command_gateway import (
    CALLER_ACTIONS,
    EXECUTION_ACTIONS,
    WindowsCommandAgentStore,
    WindowsCommandGateway,
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


if __name__ == "__main__":
    unittest.main()
