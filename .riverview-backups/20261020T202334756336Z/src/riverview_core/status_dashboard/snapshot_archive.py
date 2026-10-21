# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/status_dashboard/snapshot_archive.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.2
# Purpose: Archive validated redacted dashboard snapshots as private GitHub Release assets.
# Execution Model: Synchronous request-driven upload from the dashboard backend; no background worker or disk staging.
# Observability: Safe error codes and release metadata; credentials and response bodies are never logged.
# Dependencies: Python standard library; GitHub REST API; private dashboard credential.
# Authority: Steward-triggered snapshot archive only; does not grant repository administration.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Initial private Release asset archival with ZIP, manifest and redaction validation.
# Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Reject repository path traversal and require exact generated release tags.
# Contracts: docs/components/STATUS_DASHBOARD.md; docs/components/STATUS_DASHBOARD_COOKBOOK.md
# Tests: tests/test_snapshot_archive.py
# History: Git and revision/backup manifest
"""Bounded, private GitHub Release archival for generated dashboard snapshots."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import stat
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from uuid import uuid4
import zipfile

MAX_PACKAGE_BYTES = 96 * 1024 * 1024
MAX_UPLOAD_BYTES = MAX_PACKAGE_BYTES + 1024 * 1024
_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_.-]{20,256}$")
_REQUIRED_PRIVACY = {
    "authentication_material": "excluded", "cookies": "excluded",
    "authorization_headers": "excluded", "passwords_and_form_values": "redacted",
    "conversation_and_request_bodies": "excluded", "account_detail_rows": "redacted",
}


class SnapshotArchiveError(Exception):
    """Failure with a stable safe code suitable for an HTTP response."""
    def __init__(self, code: str, status: int = 502):
        super().__init__(code)
        self.code = code
        self.status = status


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubReleaseArchive:
    """Create a private draft release, upload the ZIP asset, then publish it."""
    def __init__(self, repository: str, token: str, *, opener=None, now=None, id_factory=None):
        if (not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository)
                or any(part in {".", ".."} for part in repository.split("/"))):
            raise ValueError("invalid_snapshot_archive_repository")
        if not isinstance(token, str) or not _TOKEN.fullmatch(token):
            raise ValueError("invalid_snapshot_archive_credential")
        self.repository = repository
        self._token = token
        self._opener = opener or build_opener(_NoRedirect())
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory or uuid4

    @classmethod
    def from_environment(cls, environ=None):
        environ = os.environ if environ is None else environ
        repository = environ.get("RIVERVIEW_SNAPSHOT_GITHUB_REPOSITORY", "").strip()
        credential_dir = environ.get("CREDENTIALS_DIRECTORY", "")
        if not repository:
            return None
        if not credential_dir:
            raise ValueError("snapshot_archive_configuration_incomplete")
        path = Path(credential_dir) / "snapshot-github-token"
        descriptor = None
        try:
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags)
            info = os.fstat(descriptor)
            if (not stat.S_ISREG(info.st_mode) or not info.st_mode & stat.S_IRUSR
                    or info.st_mode & 0o027 or info.st_size > 256):
                raise ValueError("snapshot_archive_credential_invalid")
            raw = os.read(descriptor, 257)
            if len(raw) > 256:
                raise ValueError("snapshot_archive_credential_invalid")
            token = raw.decode("ascii").strip()
        except (OSError, UnicodeError) as exc:
            raise ValueError("snapshot_archive_credential_unavailable") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
        return cls(repository, token)

    @staticmethod
    def inspect_package(data: bytes):
        if not isinstance(data, bytes) or not data or len(data) > MAX_UPLOAD_BYTES:
            raise SnapshotArchiveError("snapshot_archive_invalid_package", 413)
        try:
            with zipfile.ZipFile(BytesIO(data), "r") as bundle:
                infos = bundle.infolist()
                names = [item.filename for item in infos]
                if (not infos or len(names) != len(set(names)) or "manifest.json" not in names
                        or any(name.startswith(("/", "\\")) or ".." in name.split("/")
                               or "\\" in name for name in names)
                        or any(item.flag_bits & 1 or item.compress_type != zipfile.ZIP_STORED
                               for item in infos)
                or len(infos) > 20000
                        or sum(item.file_size for item in infos) > MAX_PACKAGE_BYTES
                        or bundle.testzip() is not None):
                    raise SnapshotArchiveError("snapshot_archive_invalid_package", 400)
                manifest = json.loads(bundle.read("manifest.json"))
                if manifest.get("schema_version") != "rv.website.diagnostic-snapshot.v1":
                    raise SnapshotArchiveError("snapshot_archive_invalid_manifest", 400)
                privacy = manifest.get("privacy")
                if not isinstance(privacy, dict) or any(privacy.get(key) != value
                                                        for key, value in _REQUIRED_PRIVACY.items()):
                    raise SnapshotArchiveError("snapshot_archive_privacy_contract_missing", 400)
                listed = manifest.get("files")
                if not isinstance(listed, list) or len(listed) != len(names) - 1:
                    raise SnapshotArchiveError("snapshot_archive_manifest_mismatch", 400)
                listed_paths = set()
                for entry in listed:
                    if not isinstance(entry, dict) or entry.get("path") not in names or entry["path"] == "manifest.json":
                        raise SnapshotArchiveError("snapshot_archive_manifest_mismatch", 400)
                    if entry["path"] in listed_paths:
                        raise SnapshotArchiveError("snapshot_archive_manifest_mismatch", 400)
                    listed_paths.add(entry["path"])
                    payload = bundle.read(entry["path"])
                    if (entry.get("size_bytes") != len(payload)
                            or entry.get("sha256") != sha256(payload).hexdigest()):
                        raise SnapshotArchiveError("snapshot_archive_manifest_mismatch", 400)
                if listed_paths != set(names) - {"manifest.json"}:
                    raise SnapshotArchiveError("snapshot_archive_manifest_mismatch", 400)
                capture_id = manifest.get("capture_id")
                if not isinstance(capture_id, str) or not 1 <= len(capture_id) <= 80:
                    raise SnapshotArchiveError("snapshot_archive_invalid_manifest", 400)
                for key, maximum in (("captured_at", 64), ("source_commit", 128), ("deployment_id", 128)):
                    value = manifest.get(key)
                    if (not isinstance(value, str) or not value or len(value) > maximum
                            or any(ord(character) < 32 for character in value)):
                        raise SnapshotArchiveError("snapshot_archive_invalid_manifest", 400)
                return {key: manifest.get(key) for key in
                        ("capture_id", "captured_at", "source_commit", "deployment_id", "schema_version")}
        except SnapshotArchiveError:
            raise
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, zipfile.BadZipFile):
            raise SnapshotArchiveError("snapshot_archive_invalid_package", 400) from None

    def _request(self, method, url, *, data=None, content_type="application/vnd.github+json"):
        request = Request(url, data=data, method=method, headers={
            "Accept": "application/vnd.github+json", "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Riverview-Diagnostic-Archive",
            "Content-Type": content_type,
        })
        try:
            with self._opener.open(request, timeout=120) as response:
                raw = response.read(64 * 1024)
                if not raw:
                    return {}
                return json.loads(raw.decode("utf-8"))
        except HTTPError as exc:
            # Do not expose GitHub's response body, which can contain private metadata.
            raise SnapshotArchiveError("snapshot_archive_github_rejected", 502) from None
        except (URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
            raise SnapshotArchiveError("snapshot_archive_github_unavailable", 502) from None

    def archive(self, data: bytes):
        manifest = self.inspect_package(data)
        api = "https://api.github.com/repos/" + self.repository
        repository = self._request("GET", api)
        if repository.get("private") is not True:
            raise SnapshotArchiveError("snapshot_archive_repository_not_private", 503)

        timestamp = self._now().astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        snapshot_id = f"rvdiag-{timestamp}-{self._id_factory().hex}"
        tag = snapshot_id
        asset_name = snapshot_id + ".zip"
        metadata = {"schema_version": "rv.website.snapshot-archive.v1", "snapshot_id": snapshot_id,
                    "capture_id": manifest["capture_id"], "captured_at": manifest.get("captured_at"),
                    "source_commit": manifest.get("source_commit"), "deployment_id": manifest.get("deployment_id"),
                    "archive_sha256": sha256(data).hexdigest(), "archive_size_bytes": len(data),
                    "package_schema": manifest["schema_version"], "retention": "permanent"}
        release = None
        base = "https://api.github.com/repos/" + self.repository
        try:
            release = self._request("POST", base + "/releases", data=json.dumps({
                "tag_name": tag, "name": "Riverview diagnostic snapshot " + timestamp,
                "body": json.dumps(metadata, sort_keys=True), "draft": True, "prerelease": False,
            }, separators=(",", ":")).encode())
            release_id = release.get("id")
            if (not isinstance(release_id, int) or release_id <= 0
                    or release.get("tag_name") != tag or release.get("draft") is not True):
                raise SnapshotArchiveError("snapshot_archive_release_creation_failed", 502)
            upload = ("https://uploads.github.com/repos/" + self.repository +
                      f"/releases/{release_id}/assets?name={quote(asset_name, safe='')}")
            asset = self._request("POST", upload, data=data, content_type="application/zip")
            if asset.get("name") != asset_name or asset.get("size") != len(data):
                raise SnapshotArchiveError("snapshot_archive_upload_failed", 502)
            published = self._request("PATCH", base + f"/releases/{release_id}",
                                      data=b'{"draft":false}')
            if published.get("draft") is not False or published.get("tag_name") != tag:
                raise SnapshotArchiveError("snapshot_archive_publish_failed", 502)
        except SnapshotArchiveError:
            if release and isinstance(release.get("id"), int):
                self._cleanup_draft(base, release["id"], tag)
            raise
        return {"status": "archived", "snapshot_id": snapshot_id,
                "release_url": f"https://github.com/{self.repository}/releases/tag/{tag}",
                "asset_name": asset_name, "archive_sha256": metadata["archive_sha256"],
                "archive_size_bytes": len(data), "retention": "permanent"}

    def _cleanup_draft(self, base, release_id, tag):
        try:
            self._request("DELETE", base + f"/releases/{release_id}")
            self._request("DELETE", base + "/git/refs/tags/" + quote(tag, safe=""))
        except SnapshotArchiveError:
            pass


class UnavailableSnapshotArchive:
    """Safe fail-closed endpoint when deployment configuration is incomplete."""
    def __init__(self, code="snapshot_archive_not_configured"):
        self.code = code

    def archive(self, data):
        raise SnapshotArchiveError(self.code, 503)
