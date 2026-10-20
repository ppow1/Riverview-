# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_snapshot_archive.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.1
# Purpose: Verify private Release uploads, failure cleanup, credential isolation, redaction and archive integrity.
# Execution Model: Local in-memory ZIP fixtures and a fake GitHub REST transport; no network credentials or real repository.
# Observability: Exact safe outcomes, request sequence and checksums.
# Dependencies: Python standard library; riverview_core.status_dashboard.snapshot_archive
# Authority: Synthetic only; never creates a real GitHub Release.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Add fake-transport success, failure, auth-material and privacy/integrity coverage.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Verify unsafe repository path configuration is rejected.
# Tests: This file
# History: Git and revision/backup manifest
"""Synthetic unit tests for dashboard GitHub snapshot archival."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from http.client import HTTPResponse
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
import zipfile

from riverview_core.status_dashboard.snapshot_archive import (
    GitHubReleaseArchive, SnapshotArchiveError)


def package(*, privacy=None, bad_hash=False):
    members = {"diagnostics/operational-snapshot.json": b'{"status":"healthy"}',
               "diagnostics/browser-history.json": b'{"redaction":{"cookies":false}}'}
    files = [{"path": name, "size_bytes": len(data),
              "sha256": "0" * 64 if bad_hash and name.startswith("diagnostics/operational") else sha256(data).hexdigest()}
             for name, data in members.items()]
    manifest = {"schema_version": "rv.website.diagnostic-snapshot.v1", "capture_id": "capture-test-1",
                "captured_at": "2026-10-20T15:00:00Z", "source_commit": "a" * 40,
                "deployment_id": "synthetic", "files": files,
                "privacy": privacy or {"authentication_material": "excluded", "cookies": "excluded",
                    "authorization_headers": "excluded", "passwords_and_form_values": "redacted",
                    "conversation_and_request_bodies": "excluded", "account_detail_rows": "redacted"}}
    output = BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as bundle:
        for name, data in members.items():
            bundle.writestr(name, data)
        bundle.writestr("manifest.json", json.dumps(manifest).encode())
    return output.getvalue()


class _Response:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def read(self, _limit=-1):
        return json.dumps(self.value).encode() if self.value else b""


class _GitHub:
    def __init__(self, *, fail_upload=False, private=True):
        self.calls = []
        self.fail_upload = fail_upload
        self.private = private
        self.release_tag = None
    def open(self, request, timeout):
        body = request.data or b""
        self.calls.append((request.method, request.full_url, request.headers, body))
        if request.method == "GET":
            return _Response({"private": self.private})
        if request.method == "POST" and "/releases" in request.full_url and "assets" not in request.full_url:
            self.release_tag=json.loads(body)["tag_name"]
            return _Response({"id": 71, "draft": True, "tag_name": self.release_tag})
        if request.method == "POST" and "assets?name=" in request.full_url:
            if self.fail_upload:
                raise HTTPError(request.full_url, 500, "synthetic", {}, BytesIO(b"private error details"))
            name = request.full_url.split("name=", 1)[1]
            from urllib.parse import unquote
            return _Response({"name": unquote(name), "size": len(body)})
        if request.method == "PATCH":
            return _Response({"draft": False, "tag_name": self.release_tag})
        if request.method == "DELETE":
            return _Response({})
        raise AssertionError((request.method, request.full_url))


def archive(transport, token="github_pat_test_token_abcdefghijklmnopqrstuvwxyz", *, private=True):
    return GitHubReleaseArchive("owner/private-riverview-diagnostics", token, opener=transport,
        now=lambda: datetime(2026, 10, 20, 15, 0, 0, tzinfo=timezone.utc),
        id_factory=lambda: type("Id", (), {"hex": "0123456789abcdef0123456789abcdef"})())


class SnapshotArchiveTests(unittest.TestCase):
    def test_repository_configuration_rejects_path_segments(self):
        for repository in ("../private", "owner/../private", "owner/."):
            with self.subTest(repository=repository), self.assertRaises(ValueError):
                GitHubReleaseArchive(repository, "github_pat_test_token_abcdefghijklmnopqrstuvwxyz")

    def test_success_creates_draft_uploads_asset_and_publishes_with_locatable_metadata(self):
        github = _GitHub()
        result = archive(github).archive(package())
        self.assertEqual(result["status"], "archived")
        self.assertEqual(result["snapshot_id"], "rvdiag-20261020T150000Z-0123456789abcdef0123456789abcdef")
        self.assertEqual(result["retention"], "permanent")
        self.assertEqual(result["archive_sha256"], sha256(package()).hexdigest())
        self.assertIn("/releases/tag/" + result["snapshot_id"], result["release_url"])
        self.assertEqual([call[0] for call in github.calls], ["GET", "POST", "POST", "PATCH"])
        release_metadata = json.loads(json.loads(github.calls[1][3])["body"])
        self.assertEqual(release_metadata["capture_id"], "capture-test-1")
        self.assertEqual(release_metadata["archive_sha256"], result["archive_sha256"])
        self.assertEqual(github.calls[2][2]["Content-type"], "application/zip")
        self.assertTrue(all(call[2]["Authorization"] == "Bearer github_pat_test_token_abcdefghijklmnopqrstuvwxyz" for call in github.calls))
        self.assertNotIn("github_pat_test_token", json.dumps(result))

    def test_failed_asset_upload_returns_safe_error_and_removes_exact_draft_and_tag(self):
        github = _GitHub(fail_upload=True)
        with self.assertRaises(SnapshotArchiveError) as raised:
            archive(github).archive(package())
        self.assertEqual(raised.exception.code, "snapshot_archive_github_rejected")
        self.assertNotIn("private error details", str(raised.exception))
        self.assertEqual([call[0] for call in github.calls], ["GET", "POST", "POST", "DELETE", "DELETE"])
        self.assertTrue(github.calls[-1][1].endswith("/git/refs/tags/rvdiag-20261020T150000Z-0123456789abcdef0123456789abcdef"))

    def test_public_repository_is_rejected_before_any_release_or_upload(self):
        github = _GitHub(private=False)
        with self.assertRaises(SnapshotArchiveError) as raised:
            archive(github).archive(package())
        self.assertEqual(raised.exception.code, "snapshot_archive_repository_not_private")
        self.assertEqual([call[0] for call in github.calls], ["GET"])

    def test_redaction_declaration_and_manifest_hashes_are_enforced_before_network_access(self):
        github = _GitHub()
        unsafe = {"authentication_material": "included"}
        for payload in (package(privacy=unsafe), package(bad_hash=True), b"not a zip"):
            with self.subTest(payload=payload[:10]), self.assertRaises(SnapshotArchiveError):
                archive(github).archive(payload)
        self.assertEqual(github.calls, [])

    def test_loadcredential_configuration_is_read_only_server_side_and_optional(self):
        self.assertIsNone(GitHubReleaseArchive.from_environment({}))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot-github-token"
            path.write_text("github_pat_test_token_abcdefghijklmnopqrstuvwxyz", encoding="ascii")
            path.chmod(0o400)
            value = GitHubReleaseArchive.from_environment({
                "RIVERVIEW_SNAPSHOT_GITHUB_REPOSITORY": "owner/private-repo",
                "CREDENTIALS_DIRECTORY": temp,
            })
            self.assertIsInstance(value, GitHubReleaseArchive)
            self.assertNotIn("github_pat_test_token", Path(__file__).resolve().parents[1]
                             .joinpath("src/riverview_core/status_dashboard/static/diagnostic-snapshot.js")
                             .read_text(encoding="utf-8"))
            path.chmod(0o622)
            with self.assertRaises(ValueError):
                GitHubReleaseArchive.from_environment({
                    "RIVERVIEW_SNAPSHOT_GITHUB_REPOSITORY": "owner/private-repo",
                    "CREDENTIALS_DIRECTORY": temp,
                })


if __name__ == "__main__":
    unittest.main()
