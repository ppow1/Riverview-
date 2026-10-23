# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_manual_image_generation_http.py
# Component: V2-MANUAL-IMAGE-GENERATION
# Revision: 1.0.3
# Purpose: Verify manual image routes preserve Dashboard account, role and CSRF boundaries
# Changed: 2026-10-23 UTC | RV-ISSUE-250 | Assert cross-account artifact verification remains forbidden.
# =============================================================================
"""HTTP route authorization and artifact delivery checks for V2 manual images."""
import hashlib
import json
from http.client import HTTPConnection
import tempfile
from pathlib import Path
import threading
import unittest
from uuid import uuid4

from riverview_core.account_auth import AuthDenied
from riverview_core.status_dashboard.server import DashboardHTTPServer

ROOT = Path(__file__).resolve().parents[1]
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000b49444154789c636000020000050001a5f645400000000049454e44ae426082")
REQUEST_ID = "a0365478-bafa-4f6a-a539-c942bc6fc1bd"


class Projection:
    def status(self): return {"status": "available"}


class Auth:
    def authenticate(self, credential, *, csrf_token, state_changing):
        if credential not in {"operator-session", "other-session", "viewer-session"}:
            raise AuthDenied("denied")
        if state_changing and csrf_token != "csrf-valid":
            raise AuthDenied("csrf")
        account = {"operator-session": ("operator-1", ["operator"]),
                   "other-session": ("operator-2", ["operator"]),
                   "viewer-session": ("viewer-1", ["viewer"])}[credential]
        return {"account_id": account[0], "roles": account[1], "email": "user@example.test"}

    @staticmethod
    def require_role(identity, *roles):
        if not set(identity.get("roles", ())) & set(roles):
            raise ValueError("role denied")


class Service:
    def __init__(self): self.records = {}
    def catalog(self): return {"schema_version": "rv.manual-image.catalog.v1", "workflows": [],
                               "gpu_selection_supported": False, "worker": {"status": "ready"}}
    def submit(self, **kwargs):
        record = {"request_id": kwargs["request_id"], "actor_id": kwargs["actor_id"],
                  "status": "queued", "workflow_id": kwargs["workflow_id"]}
        self.records[record["request_id"]] = record
        return record
    def history(self, actor_id=None, *, limit=100):
        return [value for value in self.records.values()
                if actor_id is None or value["actor_id"] == actor_id][:limit]
    def get(self, request_id): return self.records.get(request_id)
    def image_bytes(self, request_id):
        record = self.records.get(request_id)
        if not record: return None
        record["status"] = "complete"
        record["artifact"] = {"sha256": hashlib.sha256(PNG).hexdigest()}
        return record, PNG


class ManualImageHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        token_path = Path(self.temp.name) / "dashboard-token"
        token_path.write_text("A" * 43, encoding="ascii")
        token_path.chmod(0o600)
        self.service = Service()
        self.server = None
        for port in range(8799, 8699, -1):
            try:
                self.server = DashboardHTTPServer("127.0.0.1", port, token_path,
                    Projection(), ROOT / "src/riverview_core/status_dashboard/static",
                    account_auth_service=Auth(), manual_image_generation=self.service)
                break
            except OSError:
                continue
        if self.server is None: self.fail("no reserved Dashboard test port available")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, *, session=None, csrf=None, token=False, body=None,
                content_type="application/json"):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {}
        if session: headers["Cookie"] = "rv_account_session=" + session
        if csrf: headers["X-Riverview-CSRF"] = csrf
        if token: headers["Authorization"] = "Bearer " + "A" * 43
        if body is not None: headers["Content-Type"] = content_type
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse(); payload = response.read()
        result = response.status, dict(response.getheaders()), payload
        conn.close(); return result

    def test_catalog_requires_account_role_not_internal_bearer(self):
        status, _, _ = self.request("GET", "/api/v1/manual-image-generations/catalog", token=True)
        self.assertEqual(status, 403)
        status, _, _ = self.request("GET", "/api/v1/manual-image-generations/catalog", session="viewer-session")
        self.assertEqual(status, 403)
        status, _, body = self.request("GET", "/api/v1/manual-image-generations/catalog", session="operator-session")
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["gpu_selection_supported"])

    def test_generation_requires_session_role_and_csrf(self):
        payload = json.dumps({"request_id": REQUEST_ID, "workflow_id": "registered-workflow.v1",
                              "parameters": {"prompt": "red cube"}})
        status, _, _ = self.request("POST", "/api/v1/manual-image-generations", token=True,
                                     body=payload)
        self.assertEqual(status, 403)
        status, _, _ = self.request("POST", "/api/v1/manual-image-generations",
            session="operator-session", body=payload)
        self.assertEqual(status, 403)
        status, _, _ = self.request("POST", "/api/v1/manual-image-generations",
            session="viewer-session", csrf="csrf-valid", body=payload)
        self.assertEqual(status, 403)
        status, _, body = self.request("POST", "/api/v1/manual-image-generations",
            session="operator-session", csrf="csrf-valid", body=payload)
        self.assertEqual(status, 202)
        self.assertEqual(json.loads(body)["actor_id"], "operator-1")

    def test_history_is_owner_scoped_and_image_is_authenticated(self):
        self.service.records[REQUEST_ID] = {"request_id": REQUEST_ID, "actor_id": "operator-1",
                                            "status": "complete"}
        status, _, body = self.request("GET", "/api/v1/manual-image-generations?limit=20",
                                       session="other-session")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["items"], [])
        status, _, _ = self.request("GET", f"/api/v1/manual-image-generations/{REQUEST_ID}/image",
                                    token=True)
        self.assertEqual(status, 403)
        status, _, _ = self.request("GET", f"/api/v1/manual-image-generations/{REQUEST_ID}/image?download=1",
                                    session="other-session")
        self.assertEqual(status, 403)
        status, _, _ = self.request("GET", f"/api/v1/manual-image-generations/{REQUEST_ID}",
                                    session="other-session")
        self.assertEqual(status, 403)
        status, headers, image = self.request("GET", f"/api/v1/manual-image-generations/{REQUEST_ID}/image?download=1",
                                              session="operator-session")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "image/png")
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(headers["X-Content-SHA256"], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(image, PNG)

    def test_manual_javascript_is_served_from_the_authenticated_dashboard_asset_allowlist(self):
        status, headers, body = self.request("GET", "/v2/assets/manual-image-generation.js", token=True)
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertIn(b"rv_account_csrf", body)

    def test_deployed_v2_bundle_has_native_manual_view_and_preserves_live_integrations(self):
        page = (ROOT / "website/v2/deployed/index.html").read_text(encoding="utf-8")
        workspace = (ROOT / "website/v2/deployed/assets/workspace.js").read_text(encoding="utf-8")
        generator = (ROOT / "website/v2/deployed/assets/manual-image-generation.js").read_text(encoding="utf-8")
        self.assertIn('data-view="image-generation"', page)
        self.assertIn('id="manual-image-form"', page)
        self.assertIn('id="manual-image-preview"', page)
        self.assertIn('id="manual-image-history-list"', page)
        self.assertIn('"image-generation"', workspace)
        self.assertIn('const api = "/api/v1/manual-image-generations"', generator)
        self.assertIn("${api}/catalog", generator)
        self.assertNotIn("sd-turbo-text-to-image.v1", generator)
        self.assertIn("rv-v2-snapshot-mode", page)
        self.assertIn('id="grace-workspace"', page)
        self.assertIn('id="communications-workspace"', page)
        self.assertIn('id="resource-monitor-workspace"', page)


if __name__ == "__main__":
    unittest.main()
