#!/usr/bin/env python3
#!/usr/bin/env python3
# =============================================================================
# Riverview~ Controlled Source
# File: scripts/serve_v2_workspace_preview.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.1
# Purpose: Serve only the static V2 preview on loopback
# Execution Model: Request-driven local preview; foreground process
# Observability: Sanitized request path/status log and startup URL; no health API
# Dependencies: Python 3.10+ standard library; website/v2 static files
# Inputs/Outputs: HTTP GET/HEAD static assets; mutating methods rejected
# Authority: Local preview only; no production API or deployment integration
# Changed: 2026-10-20 UTC | RV-WEB-V2-SHELL-001 | Add standard source contract header
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: tests/test_v2_workspace_shell.py
# History: Git and revision/backup manifest
# =============================================================================
"""Serve the fixture-only V2 shell on loopback; no service installation required."""
from __future__ import annotations

import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / "website" / "v2"


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        self.send_error(405, "preview is read-only")

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST

    def translate_path(self, path):
        request_path = unquote(urlsplit(path).path)
        parts = [part for part in request_path.split("/") if part not in ("", ".")]
        if any(part == ".." for part in parts):
            return str(ROOT / "__rejected_path__")
        if not parts:
            parts = ["index.html"]
        target = ROOT.joinpath(*parts)
        try:
            resolved = target.resolve(strict=False)
            if resolved != ROOT and ROOT not in resolved.parents:
                return str(ROOT / "__rejected_path__")
            return str(resolved)
        except (OSError, RuntimeError):
            return str(ROOT / "__rejected_path__")

    def log_message(self, fmt, *args):
        # Preview server logs only request path/status; no headers or user data.
        super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Must remain a loopback address")
    parser.add_argument("--port", type=int, default=8877)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"}:
        parser.error("preview server may bind only to loopback")
    server = ThreadingHTTPServer((args.host, args.port), PreviewHandler)
    server.daemon_threads = True
    print(f"V2 fixture preview: http://{args.host}:{server.server_port}/ (loopback only)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
