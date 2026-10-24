#!/usr/bin/env python3
# File: scripts/ntfy_phone_test.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.0
# Purpose: Send a protected-credential ntfy iPhone acceptance notice
# Authority: Notification transport only
# Changed: 2026-10-24 UTC | RV-IPHONE-NTFY-UPSTREAM-001 | Add private-topic test CLI
"""Send one recognizable test notice through the installed private ntfy topic."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.request
from pathlib import Path


TOKEN_FILE = Path("/etc/riverview/notification/ntfy_token")
TOPIC_FILE = Path("/etc/riverview/notification/topic")
NTFY_URL = "http://127.0.0.1:2586"


def protected_value(path: Path) -> str:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
        raise RuntimeError("protected credential file permissions are invalid")
    value = path.read_text(encoding="utf-8").strip()
    if not value or "\n" in value or "\r" in value:
        raise RuntimeError("protected credential file is empty or malformed")
    return value


def main() -> int:
    if os.geteuid() != 0:
        print("Run with sudo so the existing protected notification credentials stay private.", file=sys.stderr)
        return 2
    try:
        token = protected_value(TOKEN_FILE)
        topic = protected_value(TOPIC_FILE)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", topic):
            raise RuntimeError("protected topic value is malformed")
        stamp = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        body = (
            f"Riverview NTFY test at {stamp}. Check delivery with the app in the background or closed, "
            "and note whether sound played."
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{NTFY_URL}/{topic}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Title": "Riverview iPhone notification test",
                "Priority": "4",
                "Tags": "test",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=15) as response:
            payload = json.loads(response.read())
            message_id = payload.get("id")
            if response.status != 200 or not isinstance(message_id, str) or not message_id:
                print("ntfy returned an unexpected acceptance response", file=sys.stderr)
                return 1
        print(f"Local ntfy accepted test notice (message_id={message_id}).")
        print("This confirms local publication only; confirm background display and sound on the iPhone.")
        return 0
    except urllib.error.HTTPError as exc:
        print(f"Local ntfy rejected test notice (HTTP {exc.code}); credentials and topic ACL were not changed.", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, RuntimeError) as exc:
        # Keep exception details suppressed: URL and request metadata can contain the private topic.
        print(f"Test notice failed ({type(exc).__name__}); no delivery is claimed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
