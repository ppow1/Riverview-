#!/usr/bin/env python3
# =============================================================================
# Riverview~ Controlled Source
# File: scripts/serve_v2_workspace_preview.py
# Component: RIVERVIEW-V2-WORKSPACE-SHELL
# Revision: 1.0.4
# Purpose: Serve the fixture-only V2 preview locally or on a trusted LAN with password authentication
# Execution Model: Request-driven foreground preview; sessions and throttles are in memory
# Observability: Sanitized startup URL and HTTP status only; request data is not logged
# Dependencies: Python 3.10+ standard library; website/v2 static assets; optional protected password hash file
# Inputs/Outputs: HTTP GET/HEAD static assets; POST login; all other mutations rejected
# Authority: Preview only; non-loopback bind requires password hash and explicit narrow client subnet
# Changed: 2026-10-20 UTC | RV-WEB-V2-LAN-PREVIEW-001 | Add password sessions and LAN client restrictions
# Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
# Tests: tests/test_v2_workspace_shell.py
# History: Git and revision/backup manifest
# =============================================================================
"""Serve the fixture-only V2 shell, with optional password-protected LAN access."""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import stat
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / "website" / "v2"
DEFAULT_PBKDF2_ITERATIONS = 600_000
MIN_PBKDF2_ITERATIONS = 300_000
MAX_PBKDF2_ITERATIONS = 1_500_000
SALT_BYTES = 16
DIGEST_BYTES = 32
SESSION_SECONDS = 8 * 60 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 5
MAX_FORM_BYTES = 4096
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ValueError("invalid password hash configuration")
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_password_record(password: str, *, iterations: int = DEFAULT_PBKDF2_ITERATIONS) -> dict:
    """Create a salted password verifier; the plaintext is not returned or persisted."""
    if not isinstance(password, str) or not 12 <= len(password) <= 256:
        raise ValueError("password must contain 12 to 256 characters")
    if not MIN_PBKDF2_ITERATIONS <= iterations <= MAX_PBKDF2_ITERATIONS:
        raise ValueError("password hash work factor is outside the supported range")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=DIGEST_BYTES)
    return {
        "format": 1,
        "algorithm": "pbkdf2_hmac_sha256",
        "iterations": iterations,
        "salt": _b64encode(salt),
        "password_hash": _b64encode(digest),
    }


def verify_password(password: str, record: dict) -> bool:
    """Verify a password using constant-time digest comparison."""
    try:
        salt = _b64decode(record["salt"])
        expected = _b64decode(record["password_hash"])
        iterations = record["iterations"]
        if (record.get("format") != 1 or record.get("algorithm") != "pbkdf2_hmac_sha256" or
                not isinstance(iterations, int) or not MIN_PBKDF2_ITERATIONS <= iterations <= MAX_PBKDF2_ITERATIONS or
                len(salt) < SALT_BYTES or len(expected) != DIGEST_BYTES):
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=DIGEST_BYTES)
        return hmac.compare_digest(candidate, expected)
    except (KeyError, TypeError, ValueError, UnicodeError):
        return False


def load_password_record(path: str | Path) -> dict:
    """Load only a protected, owner-owned regular file; reject symlinks and weak records."""
    path = Path(path)
    if path.is_symlink():
        raise RuntimeError("password hash file must not be a symbolic link")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise RuntimeError("password hash file must be a protected regular file") from None
    with os.fdopen(descriptor, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            raise RuntimeError("password hash file must be owner-owned and mode 0600")
        payload = stream.read(8193)
    if len(payload) > 8192:
        raise RuntimeError("password hash file is too large")
    try:
        record = json.loads(payload.decode("utf-8"))
        _validate_password_record(record)
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        raise RuntimeError("password hash file is invalid") from None
    return record


def _validate_password_record(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("invalid record")
    if (record.get("format") != 1 or record.get("algorithm") != "pbkdf2_hmac_sha256" or
            not isinstance(record.get("iterations"), int) or
            not MIN_PBKDF2_ITERATIONS <= record["iterations"] <= MAX_PBKDF2_ITERATIONS):
        raise ValueError("invalid record")
    if len(_b64decode(record.get("salt"))) < SALT_BYTES or len(_b64decode(record.get("password_hash"))) != DIGEST_BYTES:
        raise ValueError("invalid record")


def trusted_client(client_ip: str, network: ipaddress.IPv4Network | None) -> bool:
    if network is None:
        return True
    try:
        address = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    return address.version == 4 and address in network


def _login_page(message: str = "") -> bytes:
    safe_message = "<p class=\"error\">Password was not accepted. Wait if access is temporarily limited.</p>" if message else ""
    return ("<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>V2 preview sign in</title>"
            "<style>body{margin:0;background:#101820;color:#e8f0f5;font:16px system-ui;display:grid;min-height:100vh;place-items:center}.card{width:min(390px,calc(100% - 36px));box-sizing:border-box;padding:28px;border:1px solid #354652;border-radius:14px;background:#17232d}h1{font-size:22px;margin:0 0 9px}.notice{color:#ffd38a;font-size:13px;line-height:1.5}label{display:block;margin:22px 0 7px;font-size:13px}input,button{box-sizing:border-box;width:100%;border-radius:8px;padding:12px;font:inherit}input{border:1px solid #526472;background:#0f171e;color:#fff}button{margin-top:12px;border:0;background:#78dce8;color:#102029;font-weight:650;cursor:pointer}.error{color:#ffaca3;font-size:13px}</style><main class=\"card\"><h1>Riverview V2 preview</h1>"
            "<p class=\"notice\">LAN-only preview over HTTP. Enter the password only on a trusted Riverview LAN. HTTP does not encrypt the password on the network.</p>"
            f"{safe_message}<form method=\"post\" action=\"/login\"><label for=\"password\">Preview password</label><input id=\"password\" name=\"password\" type=\"password\" autocomplete=\"current-password\" required maxlength=\"256\" autofocus><button type=\"submit\">Open V2 preview</button></form></main></html>").encode("utf-8")


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 32

    def __init__(self, address, handler, *, auth_record=None, trusted_network=None):
        self.auth_record = auth_record
        self.trusted_network = trusted_network
        self.session_key = secrets.token_bytes(32)
        self.login_attempts: dict[str, tuple[int, float, float]] = {}
        self.login_attempts_lock = threading.Lock()
        self.request_slots = threading.BoundedSemaphore(8)
        super().__init__(address, handler)

    def get_request(self):
        request, client_address = super().get_request()
        request.settimeout(10)
        return request, client_address

    def process_request(self, request, client_address):
        if not self.request_slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        threading.Thread(target=self._process_bounded, args=(request, client_address), daemon=True).start()

    def _process_bounded(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)
            self.request_slots.release()

    def allowed_host(self, supplied: str) -> bool:
        bind_ip, port = self.server_address[:2]
        host = supplied.strip().lower()
        candidates = {f"{bind_ip.lower()}:{port}", bind_ip.lower()}
        try:
            parsed = ipaddress.ip_address(bind_ip)
            if parsed.is_loopback:
                candidates.update({"localhost", f"localhost:{port}"})
                if parsed.version == 6:
                    candidates.update({f"[{bind_ip.lower()}]:{port}", f"[{bind_ip.lower()}]"})
        except ValueError:
            return False
        return host in candidates

    def login_locked_for(self, client_ip: str, now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        with self.login_attempts_lock:
            attempts = self.login_attempts.get(client_ip)
            if not attempts:
                return 0
            _count, _window_start, locked_until = attempts
            return max(0, int(locked_until - now + 0.999))

    def record_login_failure(self, client_ip: str, now: float | None = None) -> int:
        now = time.monotonic() if now is None else now
        with self.login_attempts_lock:
            previous = self.login_attempts.get(client_ip)
            count, window_start, locked_until = previous or (0, now, 0.0)
            if locked_until > now:
                return max(1, int(locked_until - now + 0.999))
            if now - window_start >= LOGIN_WINDOW_SECONDS:
                count, window_start = 0, now
            count += 1
            if count >= LOGIN_MAX_FAILURES:
                locked_until = now + LOGIN_WINDOW_SECONDS
                count = LOGIN_MAX_FAILURES
            self.login_attempts[client_ip] = (count, window_start, locked_until)
            if len(self.login_attempts) > 512:
                oldest = sorted(self.login_attempts, key=lambda key: self.login_attempts[key][1])[:64]
                for key in oldest:
                    self.login_attempts.pop(key, None)
            return max(0, int(locked_until - now + 0.999))

    def clear_login_failures(self, client_ip: str) -> None:
        with self.login_attempts_lock:
            self.login_attempts.pop(client_ip, None)

    def make_session_cookie(self, now: int | None = None) -> str:
        now = int(time.time()) if now is None else now
        expires = now + SESSION_SECONDS
        nonce = secrets.token_urlsafe(24)
        payload = f"{expires}.{nonce}"
        signature = _b64encode(hmac.new(self.session_key, payload.encode("ascii"), hashlib.sha256).digest())
        return f"v1.{payload}.{signature}"

    def valid_session_cookie(self, cookie_value: str | None, now: int | None = None) -> bool:
        if not cookie_value or len(cookie_value) > 256:
            return False
        parts = cookie_value.split(".")
        if len(parts) != 4 or parts[0] != "v1":
            return False
        try:
            expires = int(parts[1])
            nonce = parts[2]
            supplied = _b64decode(parts[3])
            if expires <= (int(time.time()) if now is None else now) or not 16 <= len(nonce) <= 64:
                return False
            payload = f"{parts[1]}.{nonce}"
            expected = hmac.new(self.session_key, payload.encode("ascii"), hashlib.sha256).digest()
            return hmac.compare_digest(supplied, expected)
        except (ValueError, UnicodeError):
            return False


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _preflight(self) -> bool:
        if not self.server.allowed_host(self.headers.get("Host", "")):
            self.send_error(400, "invalid Host header")
            return False
        if not trusted_client(self.client_address[0], self.server.trusted_network):
            self.send_error(403, "client is outside the trusted LAN")
            return False
        return True

    def _session(self) -> bool:
        if self.server.auth_record is None:
            return True
        cookie_header = self.headers.get("Cookie", "")
        for item in cookie_header.split(";"):
            name, separator, value = item.strip().partition("=")
            if separator and name == "rv_v2_preview":
                return self.server.valid_session_cookie(value)
        return False

    def _send_login_page(self, *, failed: bool = False):
        body = _login_page("failed" if failed else "")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _origin_matches_host(self) -> bool:
        host = self.headers.get("Host", "").strip().lower()
        origin = self.headers.get("Origin", "").strip().lower()
        return bool(host and origin == f"http://{host}")

    def do_GET(self):
        if not self._preflight():
            return
        path = urlsplit(self.path).path
        if self.server.auth_record is not None and not self._session():
            if path in {"/", "/login"}:
                self._send_login_page()
            else:
                self.send_error(401, "preview authentication required")
            return
        if path == "/login":
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        super().do_GET()

    def do_HEAD(self):
        if not self._preflight():
            return
        path = urlsplit(self.path).path
        if self.server.auth_record is not None and not self._session():
            self.send_error(401, "preview authentication required")
            return
        if path == "/login":
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self):
        if not self._preflight():
            return
        path = urlsplit(self.path).path
        if self.server.auth_record is None or path != "/login":
            self.send_error(405, "preview is read-only")
            return
        if not self._origin_matches_host():
            self.send_error(403, "login origin rejected")
            return
        retry_after = self.server.login_locked_for(self.client_address[0])
        if retry_after:
            self._send_rate_limited(retry_after)
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if (content_type != "application/x-www-form-urlencoded" or self.headers.get("Transfer-Encoding") or
                not self.headers.get("Content-Length", "").isdigit()):
            self.send_error(400, "invalid login form")
            return
        length = int(self.headers["Content-Length"])
        if length < 1 or length > MAX_FORM_BYTES:
            self.send_error(400, "invalid login form")
            return
        try:
            form = parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True, max_num_fields=2)
            values = form.get("password", [])
            password = values[0] if len(values) == 1 and len(values[0]) <= 256 else ""
        except (UnicodeError, ValueError):
            password = ""
        if not password or not verify_password(password, self.server.auth_record):
            retry_after = self.server.record_login_failure(self.client_address[0])
            if retry_after:
                self._send_rate_limited(retry_after)
                return
            self._send_login_page(failed=True)
            return
        self.server.clear_login_failures(self.client_address[0])
        self.send_response(303)
        self.send_header("Set-Cookie", f"rv_v2_preview={self.server.make_session_cookie()}; Path=/; Max-Age={SESSION_SECONDS}; HttpOnly; SameSite=Strict")
        self.send_header("Location", "/")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _send_rate_limited(self, retry_after: int):
        body = b"login temporarily limited\n"
        self.send_response(429)
        self.send_header("Retry-After", str(retry_after))
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):
        if self._preflight():
            self.send_error(405, "preview is read-only")

    do_PATCH = do_PUT
    do_DELETE = do_PUT
    do_OPTIONS = do_PUT

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
        # Avoid logging passwords, query strings, referrers, and browser request data.
        return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind to 127.0.0.1 or one explicit IPv4 address")
    parser.add_argument("--port", type=int, default=8877)
    parser.add_argument("--trusted-network", help="Narrow IPv4 client network required for LAN binding, e.g. 192.168.1.0/24")
    parser.add_argument("--auth-file", help="Owner-only PBKDF2 password hash file created by setup_v2_workspace_preview_auth.py")
    args = parser.parse_args()
    try:
        address = ipaddress.ip_address(args.host)
        if address.version != 4 or address.is_unspecified or address.is_multicast:
            parser.error("host must be 127.0.0.1 or one explicit IPv4 address")
        network = ipaddress.ip_network(args.trusted_network, strict=False) if args.trusted_network else None
        if network is not None and (network.version != 4 or network.prefixlen < 24):
            parser.error("trusted network must be an IPv4 subnet /24 or narrower")
        if address.is_loopback:
            if network is not None and address not in network:
                parser.error("trusted network must contain the bind address")
        else:
            if network is None or address not in network:
                parser.error("non-loopback binding requires a narrow trusted network containing the bind address")
            if not args.auth_file:
                parser.error("non-loopback binding requires an owner-only --auth-file")
        auth_record = load_password_record(args.auth_file) if args.auth_file else None
        server = PreviewServer((str(address), args.port), PreviewHandler,
                               auth_record=auth_record, trusted_network=network)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print(f"V2 fixture preview: http://{server.server_address[0]}:{server.server_port}/ ({'password protected' if auth_record else 'loopback only; no password configured'})", flush=True)
    if network:
        print(f"Trusted clients: {network}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
