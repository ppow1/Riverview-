# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_status_dashboard.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.33
# Purpose: Verify authenticated read-only projections, privacy, paging and restart-safe UI service
# Execution Model: HTTP component tests and isolated PostgreSQL integration tests
# Observability: Versioned status and request failure contracts
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL for integration class
# Authority: Creates/drops only unique rvtest_* schemas; never accesses shared Riverview data
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Verify safe component links remain functional in the consolidated guide
# Changed: 2026-10-11 UTC | RV-M4.1-DASHBOARD-COOKBOOK-ROUTE | Exercise updated authority diagnostics through the dashboard documentation route
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Enforce browser-managed persistent grant cookie and denial retry suppression UI contract
# Changed: 2026-10-11 UTC | RV-M4.1-DASHBOARD-COOKBOOK-ASSERTION | Match cookbook's documented DROP CASCADE warning text
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS | Assert expanded scheduler recovery docs render through dashboard route
# Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-EXACT-DOCS-REVISION | Match the exact docs/graph source revision in the deployment contract
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS | Assert worker recovery diagnostics render through dashboard route
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-PG-SECRET-SAFETY | Assert PostgreSQL cookbook has no password-bearing command examples
# Changed: 2026-10-13 UTC | RV-GRACE-TO-ENGINEERING | Verify workflow-session transport, exact Steward work-order gate and corrected cookie text assertion
# Changed: 2026-10-11 UTC | RV-M1.4-LIVE-DEPENDENCY-CORRECTION | Assert scheduler docs distinguish shared migration from commissioning
# Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Assert complete conversational controls, accessibility hooks, and disabled future actions
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-DASHBOARD-REPOSITORY-LINK | Preserve installed knowledge-cookbook navigation in source shell
# Changed: 2026-10-11 UTC | RV-M4.1-DB-RESTORE-COOKBOOK | Verify observed backup path incident renders safely through docs route
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-PACKAGE-ROUTE-INTEGRITY | Require every dashboard shell documentation link to resolve
# Changed: 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE-COOKBOOK-RENDER | Verify current authority recovery section renders safely with no broken evidence link
# Changed: 2026-10-11 UTC | RV-M3.3-DASHBOARD-COOKBOOK-ASSERTION-CORRECTION | Match expected HTML code-tag rendering rather than Markdown source
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: This file
# History: Git and revision/backup manifest
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Persist bounded streaming, reconnect, and terminal provenance.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL004 | Assert assignment graph/node references and restricted diagnostic link rendering.
# =============================================================================
"""Security, API, privacy and PostgreSQL integration tests for M3.1."""

import json
import os
import re
import tempfile
import sys
import threading
import time
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from pathlib import Path
from uuid import uuid4

from riverview_core.status_dashboard.projection import DashboardProjection
from riverview_core.status_dashboard.server import DashboardHTTPServer, _read_token
from riverview_core.status_dashboard.markdown import render_markdown

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]


class _FakeProjection:
    def __init__(self):
        self.last_limit = None
        self.execution_position = {"status": "unknown", "reason": "No recorded node."}

    def graph_execution_position(self, graph_id):
        return self.execution_position

    def status(self):
        return {"schema_version":"rv.dashboard.status.v1", "component_id":"STEWARD-DASHBOARD",
                "component_version":"1.0.0", "projection_status":"unavailable",
                "freshness":"unavailable", "source":{"kind":"postgresql"},
                "cme":{"status":"unavailable"}, "workers":{"status":"unknown"}}

    def assignments(self, *, after=None, limit=25):
        self.last_limit = limit
        return {"status":"available", "items":[], "next_cursor":None, "page_limit":limit}

    def events(self, *, after_seq=None, before_seq=None, limit=25):
        self.last_limit = limit
        return {"status":"available", "items":[], "next_cursor":None, "page_limit":limit}

    def workers(self, *, after=None, limit=25):
        self.last_limit = limit
        return {"status":"available", "items":[], "next_cursor":None, "page_limit":limit}

    def attention(self, *, limit=25):
        return {"status":"available", "items":[], "limit":limit}

    def snapshot(self):
        return {"schema_version":"rv.dashboard.snapshot.v1", "redaction":{"credentials":"excluded"}}

    def assignment_detail(self, assignment_id):
        return None


class DashboardDeploymentContractTests(unittest.TestCase):
    def test_overview_explains_authoritative_projection_and_component_health_boundaries(self):
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        guidance = html[html.index('id="overview-guidance"'):html.index('</div>', html.index('id="overview-guidance"'))]
        for phrase in ("last observed institution event sequence", "read-only ledger response",
                       "separate heartbeat signals", "separate from chat availability"):
            self.assertIn(phrase, guidance)

    def test_worker_inventory_separates_registration_health_and_loaded_page_counts(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        css = (ROOT / "src/riverview_core/status_dashboard/static/app.css").read_text(encoding="utf-8")
        self.assertIn('w.active === true ? "Registered · active"', app)
        self.assertIn('w.active === false ? "Registered · inactive"', app)
        self.assertIn('w.status === "inactive" ? "Registry inactive"', app)
        self.assertIn('const health = w.status === "inactive" ? "Registry inactive"', app)
        self.assertIn("registered · ${counts.active} active · ${counts.inactive} inactive", app)
        self.assertIn("counts.heartbeat.healthy", app)
        self.assertIn("more records available", app)
        self.assertIn('id="worker-inventory-summary"', html)
        self.assertIn("Counts cover loaded 25-record pages", html)
        self.assertIn(".worker-row{grid-template-columns:minmax(0,1fr) minmax(0,1fr)", css)

    def test_assignment_detail_exposes_persisted_graph_identity_and_safe_diagnostic_reference(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        self.assertIn('item("Canonical graph ID", a.process_graph_id || "No graph ID recorded")', app)
        self.assertIn('item("Canonical node ID", a.process_node_id || "No process node ID recorded")', app)
        self.assertIn(r'^docs\/components\/([A-Za-z0-9_-]+\.md)$', app)
        self.assertIn('href="/docs/components/${esc(match[1])}"', app)
        self.assertIn("persisted assignment references", app)
        self.assertIn("Missing IDs are not inferred", app)

    def test_workflow_registry_client_supports_account_cookie_sessions(self):
        static = Path(__file__).resolve().parents[1] / "src/riverview_core/status_dashboard/static"
        js = (static / "workflow.js").read_text(encoding="utf-8")
        self.assertIn('credentials:"same-origin"', js)
        self.assertIn('if (token()) headers.Authorization', js)
        self.assertNotIn('if(!token()) return;', js)
        app = (static / "app.js").read_text(encoding="utf-8")
        html = (static / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-message-work-order', app)
        self.assertIn('/work-orders', app)
        self.assertIn('id="work-order-criteria"', html)
        self.assertIn('objective.submit on work-order:engineering', app)

    def test_grace_conversation_workspace_controls_and_complete_rendering_contract(self):
        static = Path(__file__).resolve().parents[1] / "src/riverview_core/status_dashboard/static"
        html = (static / "index.html").read_text(encoding="utf-8")
        js = (static / "app.js").read_text(encoding="utf-8")
        css = (static / "app.css").read_text(encoding="utf-8")
        self.assertIn('id="chat-history" class="conversation-timeline"', html)
        self.assertIn('id="chat-message" rows="2"', html)
        self.assertIn('id="chat-auth-form"', html)
        self.assertIn('autocomplete="current-password"', html)
        self.assertIn("HttpOnly same-origin cookie", html)
        self.assertIn('id="chat-disconnect"', html)
        self.assertIn("Shift+Enter adds a line", html)
        self.assertLess(html.index('class="chat-more"'), html.index('id="chat-send"'))
        self.assertIn('data-chat-option="details"', html)
        self.assertIn("Image generation — coming later", html)
        self.assertIn("disabled", html[html.index("Image generation — coming later")-80:html.index("Image generation — coming later")])
        self.assertIn("white-space:pre-wrap", css)
        self.assertIn("overflow-wrap:anywhere", css)
        self.assertIn("<div class=\"message-content\">${esc(body)}</div>", js)
        self.assertNotIn("textContent.slice", js[js.index("function renderConversation"):js.index("async function loadGraceConversation")])
        self.assertIn("chat-details-dialog", html)
        self.assertIn("message-details-dialog", html)
        self.assertIn('credentials: "same-origin"', js)
        self.assertIn("state.chatAuthRejected || state.chatLoading", js)
        self.assertIn('resident_conversation_not_authorized', js)
        self.assertIn('/api/v1/resident/conversations/stream', js)
        self.assertIn('text/event-stream', (ROOT / "src/riverview_core/status_dashboard/server.py").read_text())
        self.assertIn('watchPendingResponses', js)
        self.assertIn('after=${cursor}', js)
        self.assertIn('rv_grace_authority', (ROOT / "src/riverview_core/status_dashboard/server.py").read_text())

    def test_unit_uses_private_runtime_pgpass_delivery(self):
        unit = (ROOT / "deploy/riverview-status-dashboard.service").read_text()
        launcher = (ROOT / "scripts/run_status_dashboard.py").read_text()
        self.assertIn("RuntimeDirectory=riverview-status-dashboard", unit)
        self.assertIn("LoadCredential=pgpass:/etc/riverview/pgpass", unit)
        self.assertIn("Environment=RIVERVIEW_SOURCE_COMMIT=8556598b19a7da4aa191a600c767d79d24432afe", unit)
        self.assertIn("Environment=RIVERVIEW_DEPLOYMENT_ID=m3.1-camrui-docs-d2c145c", unit)
        self.assertIn("scripts/run_status_dashboard.py", unit)
        self.assertIn("copy_systemd_credential(source, PASSFILE, identity.pw_uid)", launcher)
        self.assertNotIn("Environment=PGPASSFILE=%d/pgpass", unit)

    def test_launcher_validates_service_credential_and_runtime_identity(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import run_status_dashboard
        from types import SimpleNamespace
        credential_dir = "/run/credentials/riverview-status-dashboard.service"
        with mock.patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": credential_dir}, clear=False):
            for name in ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
                os.environ.pop(name, None)
            with mock.patch.object(run_status_dashboard, "systemd_credential_path") as validate:
                with mock.patch.object(run_status_dashboard, "copy_systemd_credential") as copy:
                    with mock.patch.object(run_status_dashboard.pwd, "getpwnam",
                                            return_value=SimpleNamespace(pw_uid=1234)):
                        with mock.patch.object(run_status_dashboard.os, "geteuid", return_value=1234):
                            run_status_dashboard.prepare_runtime_credential()
            validate.assert_called_once_with(Path(credential_dir) / "pgpass",
                                             service_unit="riverview-status-dashboard.service")
            copy.assert_called_once_with(Path(credential_dir) / "pgpass",
                                         run_status_dashboard.PASSFILE, 1234)
            self.assertEqual(os.environ["PGPASSFILE"], str(run_status_dashboard.PASSFILE))


class DashboardHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temp.name) / "token"
        self.token = "A" * 43
        self.token_path.write_text(self.token)
        self.token_path.chmod(0o600)
        self.projection = _FakeProjection()
        self.server = None
        for port in range(8799, 8699, -1):
            try:
                self.server = DashboardHTTPServer("127.0.0.1", port, self.token_path,
                    self.projection, ROOT / "src/riverview_core/status_dashboard/static")
                break
            except OSError:
                continue
        if self.server is None:
            self.fail("no free dashboard test port in the reserved 8700-8799 range")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, *, token=None, host=None, cookie=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if host:
            headers["Host"] = host
        if cookie:
            headers["Cookie"] = cookie
        conn.request(method, path, headers=headers)
        response = conn.getresponse()
        body = response.read()
        result = (response.status, response.getheaders(), body)
        conn.close()
        return result

    def test_public_shell_is_local_but_projection_requires_bearer(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Riverview", body)
        self.assertIn(b"/docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md", body)
        doc_names = set(re.findall(rb'href="/docs/components/([A-Za-z0-9_-]+\.md)"', body))
        self.assertGreater(len(doc_names), 1)
        for name in sorted(doc_names):
            doc_status, _, _ = self.request(
                "GET", "/docs/components/" + name.decode("ascii"))
            self.assertEqual(doc_status, 200, name.decode("ascii"))
        header_map = dict(headers)
        self.assertEqual(header_map["Cache-Control"], "no-store")
        self.assertIn("default-src 'none'", header_map["Content-Security-Policy"])
        status, _, _ = self.request("GET", "/api/v1/status")
        self.assertEqual(status, 401)
        status, _, body = self.request("GET", "/api/v1/status", token="B" * 43)
        self.assertEqual(status, 401)
        self.assertNotIn(self.token.encode(), body)

    def test_conversation_work_order_requires_account_steward_not_recovery_token(self):
        path = "/api/v1/resident/conversations/00000000-0000-4000-8000-000000000001/work-orders"
        status, _, body = self.request("POST", path)
        self.assertEqual(status, 401)
        status, _, body = self.request("POST", path, token=self.token)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "steward_account_session_required")

    def test_conversation_stream_requires_authentication_and_existing_service(self):
        path="/api/v1/resident/conversations/00000000-0000-4000-8000-000000000001/responses/00000000-0000-4000-8000-000000000002/stream?after=0"
        status,_,_=self.request("GET",path)
        self.assertEqual(status,401)
        status,_,body=self.request("GET",path,token=self.token)
        self.assertEqual(status,503)
        self.assertEqual(json.loads(body)["error"],"resident_conversation_unavailable")
        status,_,body=self.request("POST","/api/v1/resident/conversations/stream",token=self.token)
        self.assertEqual(status,503)

    def test_authenticated_sse_replays_durable_response_events(self):
        class StreamService:
            def stream_snapshot(self,credential,conversation_id,response_id,*,after_sequence):
                self_credential=credential
                self.asserted = self_credential
                events=[
                    {"sequence":1,"event_type":"generating","generation":1},
                    {"sequence":2,"event_type":"delta","text":"first chunk"},
                    {"sequence":3,"event_type":"completed","metadata":{"model_id":"test"}},
                ]
                return {"status":"completed","events":[e for e in events if e["sequence"]>after_sequence]}
        service=StreamService()
        self.server._conversation_service=service
        conversation_id="00000000-0000-4000-8000-000000000001"
        request_id="00000000-0000-4000-8000-000000000002"
        path=f"/api/v1/resident/conversations/{conversation_id}/responses/{request_id}/stream?after=0"
        status,headers,body=self.request("GET",path,token=self.token,
            cookie="rv_grace_authority="+"C"*43)
        self.assertEqual(status,200)
        header_map=dict(headers)
        self.assertEqual(header_map["Content-Type"],"text/event-stream; charset=utf-8")
        self.assertEqual(header_map["X-Accel-Buffering"],"no")
        self.assertIn(b"event: delta",body)
        self.assertIn(b'"text":"first chunk"',body)
        self.assertIn(b"event: completed",body)
        resumed_path=path.replace("after=0","after=2")
        status,_,resumed=self.request("GET",resumed_path,token=self.token,
            cookie="rv_grace_authority="+"C"*43)
        self.assertEqual(status,200)
        self.assertNotIn(b'"text":"first chunk"',resumed)
        self.assertIn(b"event: completed",resumed)
    def test_api_is_read_only_host_checked_and_never_claims_healthy_without_source(self):
        status, _, body = self.request("GET", "/api/v1/status", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["projection_status"], "unavailable")
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            status, _, body = self.request(method, "/api/v1/status", token=self.token)
            self.assertEqual(status, 405, method)
            self.assertEqual(json.loads(body)["error"], "read_only_method")
        status, _, body = self.request("GET", "/api/v1/status", token=self.token, host="attacker.invalid")
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_host")

    def test_pages_are_bounded_and_unknown_routes_do_not_reveal_server(self):
        status, _, body = self.request("GET", "/api/v1/events?limit=9000", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(self.projection.last_limit, 100)
        status, _, body = self.request("GET", "/api/v1/workers?limit=9000", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(self.projection.last_limit, 100)
        status, _, body = self.request("GET", "/not-an-api", token=self.token)
        self.assertEqual(status, 404)
        self.assertNotIn(b"BaseHTTPRequestHandler", body)

    def test_component_cookbook_is_rendered_as_readable_safe_html(self):
        status, headers, body = self.request("GET", "/docs/components/CME_MONITOR_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b"<h1", body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"Riverview~ Controlled Document", body)
        self.assertNotIn(b"<!--", body)
        status, _, operations = self.request("GET", "/docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn(b"Observed PostgreSQL backup path permission failure", operations)
        self.assertIn(b"Permission denied", operations)
        self.assertIn(b"sudo -n -u postgres test -x", operations)
        self.assertIn(b"378a1a4cba4605a673d8cf22b8bfcbb4277bce272158cae6e79c7d6ecfd0720b", operations)
        self.assertIn(b"<pre><code", operations)
        self.assertNotIn(b"Riverview~ Controlled Document", operations)
        self.assertNotIn(b"<!--", operations)
        status, headers, body = self.request(
            "GET", "/docs/components/ASSIGNMENT_SCHEDULER_COOKBOOK.md")
        self.assertEqual(status, 200)
        for evidence in (b"dependency of the later worker and monitoring migration chain",
                         b"ce29c2994904f54706db883f61127bf05ee195ecbdce90e7242886e86711b717",
                         b"no standalone M1.4 scheduler service"):
            self.assertIn(evidence, body)
        status, headers, body = self.request("GET", "/docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b'id="riverview-operations-and-recovery-guide"', body)
        for heading in (b"PostgreSQL and ledger", b"Migrations, backups, and restoration",
                        b"CME progress monitor", b"Event processor and durable cursor",
                        b"Worker registration, scheduling, leases, assignments, verification"):
            self.assertIn(heading, body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"Riverview~ Controlled Document", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/POSTGRES_LEDGER_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        for heading in (b"Connection and schema inspection", b"Run tests safely",
                        b"Recovery discipline"):
            self.assertIn(heading, body)
        self.assertIn(b"sudo -n -u postgres psql", body)
        self.assertIn(b"RIVERVIEW_TEST_PG_DSN", body)
        self.assertNotIn(b"PGPASSWORD=", body)
        self.assertNotIn(b"postgresql://", body)
        self.assertIn(b"BEGIN READ ONLY", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/ASSIGNMENT_SCHEDULER_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        for heading in (b"Read-only claim and lease inspection",
                        b"Isolated failure and recovery verification",
                        b"StaleLeaseError"):
            self.assertIn(heading, body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/WORKER_ADAPTER_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        for heading in (b"Worker registration and persisted execution diagnosis",
                        b"Independent outcome verification",
                        b"Failure and restart recovery"):
            self.assertIn(heading, body)
        self.assertIn(b"credential digests", body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b'id="versioned-privilege-boundary-provisioner-isolated-controlled-use"', body)
        self.assertIn(b"DROP ... CASCADE", body)
        self.assertIn(b"NOLOGIN", body)
        self.assertIn(b"protected full backup", body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/INSTITUTIONAL_AUTHORITY.md")
        self.assertEqual(status, 200)
        self.assertIn(b'INSTITUTIONAL_AUTHORITY_COOKBOOK.md', body)
        self.assertIn(b"<h1", body)
        status, _, body = self.request("GET", "/docs/components/../../README.md")
        self.assertEqual(status, 404)
        self.assertNotIn(b"README", body)

    def test_canonical_graph_api_uses_only_persisted_live_position(self):
        from urllib.parse import quote
        status, _, _ = self.request("GET", "/api/v1/graphs")
        self.assertEqual(status, 401)
        status, _, body = self.request("GET", "/api/v1/graphs", token=self.token)
        self.assertEqual(status, 200)
        listing = json.loads(body)
        self.assertEqual(listing["status"], "available")
        from jsonschema import Draft202012Validator
        contract = json.loads((ROOT / "docs/components/STATUS_DASHBOARD_API.schema.json").read_text())
        Draft202012Validator(contract).validate(listing)
        self.assertTrue(any(item["graph_id"] == "rv:worker-adapter:deterministic-attempt"
                            for item in listing["items"]))
        graph_id = quote("rv:worker-adapter:deterministic-attempt", safe="")
        status, _, body = self.request("GET", "/api/v1/graphs/" + graph_id, token=self.token)
        self.assertEqual(status, 200)
        result = json.loads(body)
        Draft202012Validator(contract).validate(result)
        graph = result["graph"]
        self.assertTrue(any(item["type"] == "decision" for item in graph["nodes"]))
        self.assertTrue(any(item["type"] == "runtime_transition" for item in graph["edges"]))
        self.assertEqual(graph["execution_position"]["status"], "unknown")
        self.assertEqual(graph["execution_position"]["reason"], "No recorded node.")
        self.projection.execution_position = {"status": "current",
            "assignment_id": "assignment:recorded", "state": "running",
            "node_id": "rv:postgres-ledger:assignment-lifecycle:running",
            "recorded_at": "2026-10-13T00:00:00+00:00"}
        status, _, body = self.request("GET", "/api/v1/graphs/" + graph_id, token=self.token)
        self.assertEqual(status, 200)
        graph = json.loads(body)["graph"]
        self.assertEqual(graph["execution_position"]["node_id"],
                         "rv:postgres-ledger:assignment-lifecycle:running")
        status, _, body = self.request("GET", "/api/v1/graphs/rv%3Anot-registered%3Anone", token=self.token)
        self.assertEqual(status, 404)

    def test_assignment_intake_cookbook_renders_without_broken_evidence_link(self):
        status, headers, body = self.request(
            "GET", "/docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b"Assignment-create authorization boundary", body)
        self.assertIn(b"<pre><code class=\"language-bash\">", body)
        self.assertIn(b"exact <code>assignment.create</code>", body)
        self.assertIn(b"evidence/checkouts/M3.3-ASSIGNMENT-INTAKE/acceptance.json", body)
        self.assertNotIn(b"href=\"/evidence/", body)
        self.assertNotIn(b"<!--", body)

    def test_markdown_renderer_escapes_html_and_rejects_unsafe_link_schemes(self):
        html = render_markdown("# Title\n\n<script>alert(1)</script>\n\n[bad](javascript:alert(1))\n\n[component](CME_MONITOR_COOKBOOK.md)\n\n| A | B |\n|---|---|\n| x | y |\n\n```sh\necho safe\n```",
                               document="docs/components/STATUS_DASHBOARD_COOKBOOK.md",
                               title="Cookbook")
        self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn(b"<script>", html)
        self.assertNotIn(b"href=\"javascript:", html)
        self.assertIn(b"href=\"/docs/components/CME_MONITOR_COOKBOOK.md\"", html)
        self.assertIn(b"<table>", html)
        self.assertIn(b"<pre><code class=\"language-sh\">", html)

    def test_not_initialized_attention_is_domain_state_not_repeated_http_503(self):
        self.projection.attention = lambda *, limit=25: {
            "status":"not_initialized", "items":[], "limit":limit}
        status, _, body = self.request("GET", "/api/v1/attention?limit=10", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "not_initialized")

    def test_attention_query_failure_remains_http_503(self):
        from riverview_core.status_dashboard.projection import ProjectionUnavailable
        self.projection.attention = mock.Mock(side_effect=ProjectionUnavailable("OperationalError"))
        status, _, body = self.request("GET", "/api/v1/attention?limit=10", token=self.token)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["error"], "projection_unavailable")

    def test_not_initialized_worker_and_ledger_pages_remain_explicit_http_200(self):
        self.projection.workers = lambda *, after=None, limit=25: {
            "status":"not_initialized", "items":[], "next_cursor":None, "page_limit":limit}
        self.projection.events = lambda *, after_seq=None, before_seq=None, limit=25: {
            "status":"not_initialized", "items":[], "next_cursor":None, "page_limit":limit}
        for route in ("/api/v1/workers", "/api/v1/events"):
            status, _, body = self.request("GET", route, token=self.token)
            self.assertEqual(status, 200, route)
            self.assertEqual(json.loads(body)["status"], "not_initialized")

    def test_token_file_requires_owner_only_permissions_and_loopback_bind(self):
        with self.assertRaisesRegex(RuntimeError, "owner-only"):
            self.token_path.chmod(0o644)
            _read_token(self.token_path)
        self.token_path.chmod(0o600)
        self.assertEqual(_read_token(self.token_path), self.token)
        credential_dir = Path(self.temp.name) / "credentials"
        credential_dir.mkdir()
        credential = credential_dir / "dashboard-token"
        credential.write_text(self.token)
        credential.chmod(0o440)
        with mock.patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(credential_dir)}):
            self.assertEqual(_read_token(credential), self.token)
            credential.chmod(0o460)
            with self.assertRaisesRegex(RuntimeError, "non-writable protected"):
                _read_token(credential)
        linked = Path(self.temp.name) / "token-link"
        linked.symlink_to(self.token_path)
        with self.assertRaisesRegex(RuntimeError, "symbolic link"):
            _read_token(linked)
        with self.assertRaisesRegex(ValueError, "loopback"):
            DashboardHTTPServer("0.0.0.0", 8766, self.token_path, self.projection)

    def test_slow_database_request_does_not_block_local_tab_navigation(self):
        start = time.perf_counter()
        # Tab navigation only changes already-rendered local DOM; the API request runs independently.
        simulated_navigation_ms = (time.perf_counter() - start) * 1000
        self.assertLess(simulated_navigation_ms, 20)
        status, _, _ = self.request("GET", "/api/v1/status", token=self.token)
        self.assertEqual(status, 200)


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class DashboardPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from riverview_core.cme import CMEPostgresMonitor
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.core = ROOT / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema, migrations_dir=self.core / "assignment_scheduler/migrations")
        apply_migrations(DSN, schema=self.schema, migrations_dir=self.core / "worker_adapter/migrations")
        apply_migrations(DSN, schema=self.schema, migrations_dir=self.core / "cme/migrations")
        self.admin.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.monitor = CMEPostgresMonitor(DSN, schema=self.schema, stall_after_seconds=2,
                                          worker_freshness_seconds=30)
        self.projection = DashboardProjection(DSN, schema=self.schema,
            source_commit="a" * 40, deployment_id="test-m31")

    def tearDown(self):
        from psycopg import sql
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create(self, label, *, private=False):
        assignment_id = f"m31-{label}-{uuid4().hex}"
        self.ledger.create(assignment_id, "engineering", f"create:{assignment_id}",
            authority_ref="grant:test-secret", objective_ref="objective:private-body",
            actor_id="resident:test", correlation_id=f"corr:{assignment_id}")
        self.ledger.transition(assignment_id, "ready", "dispatch", f"ready:{assignment_id}", actor_id="processor")
        self.ledger.transition(assignment_id, "running", "execute", f"run:{assignment_id}", actor_id="worker")
        if private:
            with self.admin.cursor() as cur:
                cur.execute("UPDATE events SET privacy_domain='undercurrent' WHERE assignment_id=%s",
                            (assignment_id,))
        return assignment_id

    def test_actual_postgres_assignment_events_cme_stall_unrelated_progress_and_status(self):
        stalled = self.create("stalled")
        progressing = self.create("progressing")
        with self.admin.cursor() as cur:
            cur.execute("UPDATE events SET recorded_at=clock_timestamp()-interval '20 seconds' WHERE assignment_id=%s",
                        (stalled,))
            cur.execute("UPDATE assignments SET updated_at=clock_timestamp()-interval '20 seconds' WHERE id=%s",
                        (stalled,))
        observed = self.monitor.scan_once()
        self.assertEqual(observed["stalled"], 1)
        assignments = self.projection.assignments(limit=10)["items"]
        by_id = {row["assignment_id"]: row for row in assignments}
        self.assertEqual(by_id[stalled]["state"], "running")
        self.assertEqual(by_id[progressing]["state"], "running")
        self.assertNotEqual(by_id[stalled]["last_meaningful_progress"]["recorded_at"],
                            by_id[progressing]["last_meaningful_progress"]["recorded_at"])
        status = self.projection.status()
        self.assertEqual(status["projection_status"], "healthy")
        self.assertEqual(status["cme"]["status"], "healthy")
        self.assertEqual(status["cme"]["service_id"], "cme.monitor.v1")
        attention = self.projection.attention(limit=10)["items"]
        self.assertTrue(any(item["event_type"] == "assignment_stalled" and
                            item["assignment_id"] == stalled for item in attention))
        events = self.projection.events(limit=100)["items"]
        self.assertTrue(any(event["correlation_id"] == f"corr:{progressing}" for event in events))

    def test_stale_and_future_cme_heartbeat_are_never_healthy(self):
        self.create("stale")
        self.monitor.scan_once()
        with self.admin.cursor() as cur:
            cur.execute("UPDATE cme_monitor_health SET last_heartbeat_at=clock_timestamp()-interval '2 minutes' "
                        "WHERE service_id='cme.monitor.v1'")
        self.assertEqual(self.projection.status()["cme"]["status"], "stale")
        with self.admin.cursor() as cur:
            cur.execute("UPDATE cme_monitor_health SET last_heartbeat_at=clock_timestamp()+interval '2 minutes' "
                        "WHERE service_id='cme.monitor.v1'")
        self.assertEqual(self.projection.status()["cme"]["status"], "unverified")

    def test_workers_have_individual_bounded_health_and_summary_counts(self):
        from psycopg import sql
        from uuid import uuid4
        workers = {"healthy": "dash-healthy", "stale": "dash-stale",
                   "future": "dash-future", "unknown": "dash-unknown"}
        assignments = {name: self.create("worker-" + name) for name in workers if name != "unknown"}
        now = datetime.now(timezone.utc)
        heartbeats = {"healthy": now-timedelta(seconds=2),
                      "stale": now-timedelta(minutes=2),
                      "future": now+timedelta(minutes=2)}
        with self.admin.cursor() as cur:
            for name, worker_id in workers.items():
                cur.execute("INSERT INTO worker_registry(worker_id,credential_sha256,capabilities,scope_ref) "
                            "VALUES (%s,%s,'[]','dashboard-test')", (worker_id,bytes(name[0].encode())*32))
                if name == "unknown":
                    continue
                assignment_id=assignments[name]
                heartbeat=heartbeats[name]
                expires=now+timedelta(seconds=60) if name != "stale" else now-timedelta(seconds=5)
                acquired=now-timedelta(seconds=10)
                cur.execute("INSERT INTO assignment_leases(assignment_id,worker_id,generation,acquired_at,"
                            "heartbeat_at,expires_at) VALUES (%s,%s,1,%s,%s,%s)",
                            (assignment_id,worker_id,acquired,heartbeat,expires))
        pages=[]; page=self.projection.workers(limit=2); pages.append(page)
        self.assertEqual(len(page["items"]),2); self.assertTrue(page["truncated"])
        while page["next_cursor"]:
            page=self.projection.workers(after=page["next_cursor"],limit=2); pages.append(page)
        observed={w["worker_id"]:w["status"] for p in pages for w in p["items"]}
        self.assertEqual(observed, {"dash-healthy":"healthy","dash-stale":"stale",
                                    "dash-future":"unverified","dash-unknown":"unknown"})
        summary=self.projection.status()["workers"]
        self.assertEqual(summary["active_workers"],4)
        self.assertEqual(summary["healthy_workers"],1)
        self.assertEqual(summary["stale_workers"],1)
        self.assertEqual(summary["unverified_workers"],1)
        self.assertEqual(summary["unknown_workers"],1)
        self.assertEqual(summary["status"],"unverified")
        self.assertEqual(sum(w["active_leases"] for p in pages for w in p["items"]),2)
        self.assertEqual(len(self.projection.snapshot()["workers"]["items"]),4)

    def test_unavailable_and_not_initialized_sources_are_distinct(self):
        missing = DashboardProjection(DSN, schema="rvtest_missing_dashboard")
        self.assertEqual(missing.status()["projection_status"], "not_initialized")
        unavailable = DashboardProjection("host=127.0.0.1 port=1 dbname=missing connect_timeout=1",
                                          schema=self.schema)
        self.assertEqual(unavailable.status()["projection_status"], "unavailable")
        self.assertFalse(unavailable.snapshot()["observed_state"])

    def test_restricted_riverview_core_role_can_read_only_grace_health_after_migration(self):
        import psycopg
        from psycopg import sql
        from riverview_core.status_dashboard.projection import ProjectionUnavailable

        role = "riverview_core"
        with self.admin.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s) AS present", (role,))
            if not cur.fetchone()["present"]:
                self.skipTest("isolated PostgreSQL instance does not define the dashboard runtime role")
            cur.execute("SELECT rolsuper AS is_superuser FROM pg_roles WHERE rolname=current_user")
            is_superuser = cur.fetchone()["is_superuser"]
            cur.execute("SELECT pg_has_role(current_user,%s,'MEMBER') AS member", (role,))
            if not is_superuser and not cur.fetchone()["member"]:
                self.skipTest("test database identity cannot exercise the dashboard runtime role")
            cur.execute(sql.SQL("""CREATE TABLE {}.grace_execution_health (
                service_id TEXT PRIMARY KEY, instance_id UUID NOT NULL, status TEXT NOT NULL,
                last_heartbeat_at TIMESTAMPTZ NOT NULL, last_cycle_at TIMESTAMPTZ,
                last_error_type TEXT, cycles_completed BIGINT NOT NULL)""").format(
                    sql.Identifier(self.schema)))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(self.schema), sql.Identifier(role)))
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s AND tablename<>%s",
                        (self.schema, "grace_execution_health"))
            for row in cur.fetchall():
                cur.execute(sql.SQL("GRANT SELECT ON {}.{} TO {}").format(
                    sql.Identifier(self.schema), sql.Identifier(row["tablename"]), sql.Identifier(role)))
            cur.execute(sql.SQL("REVOKE ALL ON {}.grace_execution_health FROM {}, PUBLIC").format(
                sql.Identifier(self.schema), sql.Identifier(role)))
            cur.execute("SELECT has_table_privilege(%s,%s,'SELECT') AS allowed", (role,
                f"{self.schema}.grace_execution_health"))
            self.assertFalse(cur.fetchone()["allowed"])

        original_connect = psycopg.connect
        def restricted_connect(*args, **kwargs):
            connection = original_connect(*args, **kwargs)
            connection.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
            connection.commit()
            return connection

        with mock.patch("riverview_core.status_dashboard.projection.psycopg.connect",
                        side_effect=restricted_connect):
            before = self.projection.status()
        self.assertEqual(before["projection_status"], "unavailable")
        self.assertEqual(before["unavailable_reason"], "InsufficientPrivilege")

        migration = (self.core / "resident_execution/migrations/0005_dashboard_grace_health_read.sql").read_text()
        self.assertIn("GRANT SELECT ON %I.grace_execution_health TO riverview_core", migration)
        self.assertNotIn("schema_migrations", migration)
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            cur.execute(migration)
            cur.execute("SELECT has_table_privilege(%s,%s,'SELECT') AS allowed", (role,
                f"{self.schema}.grace_execution_health"))
            self.assertTrue(cur.fetchone()["allowed"])

        with mock.patch("riverview_core.status_dashboard.projection.psycopg.connect",
                        side_effect=restricted_connect):
            status = self.projection.status()
        self.assertEqual(status["projection_status"], "healthy")
        self.assertEqual(status["grace_execution"]["status"], "not_initialized")

    def test_private_assignments_events_and_payload_are_filtered_from_snapshot(self):
        public = self.create("public")
        private = self.create("private", private=True)
        listed = self.projection.assignments(limit=100)["items"]
        ids = {row["assignment_id"] for row in listed}
        self.assertIn(public, ids)
        self.assertNotIn(private, ids)
        self.assertIsNone(self.projection.assignment_detail(private))
        snapshot = json.dumps(self.projection.snapshot())
        for secret in ("grant:test-secret", "objective:private-body", private, "undercurrent", "secret://private"):
            self.assertNotIn(secret, snapshot)
        payload_keys = []
        def find_payload(value):
            if isinstance(value, dict):
                payload_keys.extend(key for key in value if key in {"payload", "evidence_references", "authority_ref"})
                for child in value.values(): find_payload(child)
            elif isinstance(value, list):
                for child in value: find_payload(child)
        find_payload(json.loads(snapshot))
        self.assertEqual(payload_keys, [])
        self.assertIn("credentials", snapshot)
        self.assertLess(len(snapshot.encode()), 128 * 1024)

    def test_event_keyset_page_and_assignment_cursor_are_stable_and_bounded(self):
        ids = [self.create(f"page-{i}") for i in range(3)]
        first = self.projection.assignments(limit=2)
        self.assertEqual(len(first["items"]), 2)
        self.assertTrue(first["truncated"])
        second = self.projection.assignments(after=first["next_cursor"], limit=2)
        self.assertEqual(len(second["items"]), 1)
        self.assertFalse(set(a["assignment_id"] for a in first["items"]) &
                         set(a["assignment_id"] for a in second["items"]))
        first_events = self.projection.events(after_seq=0, limit=2)
        self.assertEqual(len(first_events["items"]), 2)
        next_events = self.projection.events(after_seq=first_events["items"][-1]["seq"], limit=1000)
        self.assertLessEqual(len(next_events["items"]), 100)
        self.assertTrue(any(a in {row["assignment_id"] for row in second["items"]} for a in ids))

    def test_assignment_attempt_and_independent_verification_detail_is_redacted(self):
        import psycopg
        from uuid import uuid4
        assignment_id = self.create("verified")
        attempt_id = uuid4()
        now = datetime.now(timezone.utc)
        with psycopg.connect(DSN) as db:
            db.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
            db.execute("INSERT INTO worker_registry(worker_id,credential_sha256,capabilities,scope_ref) "
                       "VALUES ('executor',%s,'[]','scope'),('verifier',%s,'[]','scope')",
                       (b"e"*32,b"v"*32))
            db.execute("""INSERT INTO worker_attempts(attempt_id,assignment_id,worker_id,lease_generation,
                         capability,idempotency_key,input_sha256,status,started_at,finished_at)
                         VALUES (%s,%s,'executor',1,'engineering','attempt-key',%s,'succeeded',%s,%s)""",
                       (attempt_id,assignment_id,"a"*64,now-timedelta(seconds=2),now))
            db.execute("INSERT INTO verification_records(attempt_id,assignment_id,executor_id,verifier_id,"
                       "verifier_revision,decision,criteria,evidence_references,summary,idempotency_key) "
                       "VALUES (%s,%s,'executor','verifier','rev-1','ACCEPTED','{}','[\"secret://private\"]',"
                       "'accepted','verify-key')", (attempt_id,assignment_id))
        detail = self.projection.assignment_detail(assignment_id)
        self.assertEqual(detail["attempts"][0]["status"], "succeeded")
        self.assertEqual(detail["verifications"][0]["decision"], "ACCEPTED")
        self.assertEqual(detail["verifications"][0]["evidence_count"], 1)
        self.assertNotIn("secret://private", json.dumps(detail))

