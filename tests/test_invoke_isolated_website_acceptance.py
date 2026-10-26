"""Regression tests for the deployed isolated acceptance asset resolver."""
# Revision: 1.0.0

import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from scripts.invoke_isolated_website_acceptance import resolve_served_assets


class ServedAssetResolutionTests(unittest.TestCase):
    def test_legacy_alias_requires_full_content_match(self):
        index = b'<link href="assets/site.css?rev=1"><script src="assets/site.js?rev=2"></script>'
        files = {"/v2/": index, "/v2/assets/site.css": b"body{}",
                 "/v2/assets/site.js": b"start();"}

        def fetch(url, limit=2_000_000):
            path = url.removeprefix("https://test")
            if path == "/v2/release.json":
                raise HTTPError(url, 404, "not found", {}, None)
            return files[path]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "releases"
            release = root / "RV-WEB-V2-TEST"
            (release / "assets").mkdir(parents=True)
            (release / "index.html").write_bytes(index)
            (release / "assets/site.css").write_bytes(files["/v2/assets/site.css"])
            (release / "assets/site.js").write_bytes(files["/v2/assets/site.js"])
            self.assertEqual(resolve_served_assets("https://test", root, fetch), release)

    def test_legacy_alias_rejects_one_changed_declared_asset(self):
        index = b'<script src="assets/site.js"></script>'

        def fetch(url, limit=2_000_000):
            if url.endswith("release.json"):
                raise HTTPError(url, 404, "not found", {}, None)
            return index if url.endswith("/v2/") else b"different"

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "releases"
            root.mkdir()
            release = root / "RV-WEB-V2-TEST"
            (release / "assets").mkdir(parents=True)
            (release / "index.html").write_bytes(index)
            (release / "assets/site.js").write_bytes(b"expected")
            with self.assertRaisesRegex(ValueError, "do_not_match"):
                resolve_served_assets("https://test", root, fetch)

    def test_release_manifest_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "releases"
            root.mkdir()

            def fetch(url, limit):
                return b'{"release_id":"../outside"}'

            with self.assertRaisesRegex(ValueError, "release_invalid"):
                resolve_served_assets("https://test", root, fetch)


if __name__ == "__main__":
    unittest.main()
