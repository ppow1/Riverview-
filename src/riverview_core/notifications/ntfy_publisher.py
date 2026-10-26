# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/notifications/ntfy_publisher.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.0
# Purpose: Publish durable dispatcher notices over the existing private NTFY transport
# Authority: May publish to the preconfigured protected phone topic only
# =============================================================================
"""Minimal authenticated NTFY publisher for already-authorized dispatcher notices."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID


_MESSAGES = {
    "assignment_stalled": "An assignment has stopped making progress.",
    "deadline_missed": "An active assignment passed its deadline.",
    "assignment_attention": "An assignment needs Steward attention.",
    "recovery_requested": "An execution lease needs recovery.",
    "monitor_failed": "The notification monitor reported a failure.",
    "grace_objective_blocked": "Grace has blocked an objective and needs Steward attention.",
    "attention_resolved": "A previous attention condition has cleared.",
}
_TITLES = {
    "assignment_stalled": "Assignment stalled",
    "deadline_missed": "Deadline missed",
    "assignment_attention": "Assignment needs attention",
    "recovery_requested": "Recovery requested",
    "monitor_failed": "Notification monitor issue",
    "grace_objective_blocked": "Grace objective blocked",
    "attention_resolved": "Attention condition cleared",
}
_PRIORITY = {"assignment_stalled": 4, "assignment_attention": 4,
             "attention_resolved": 3, "deadline_missed": 5,
             "recovery_requested": 5, "monitor_failed": 5,
             "grace_objective_blocked": 4}


class NtfyPublishError(RuntimeError):
    """Safe transport failure with no URL, topic, or credential in its message."""


class NtfyPhonePublisher:
    def __init__(self, base_url: str, *, topic: str, token: str,
                 web_base_url: str | None = None, timeout: float = 8):
        if not isinstance(base_url, str) or not re.fullmatch(r"https?://[^/]+(?::[0-9]+)?", base_url):
            raise ValueError("invalid NTFY publisher origin")
        if not isinstance(topic, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", topic):
            raise ValueError("invalid NTFY topic credential")
        if not isinstance(token, str) or not token or "\n" in token or "\r" in token:
            raise ValueError("invalid NTFY token credential")
        if not 1 <= timeout <= 30:
            raise ValueError("invalid NTFY timeout")
        self.base_url = base_url.rstrip("/")
        self._topic = topic
        self._token = token
        self.timeout = timeout
        self.web_base_url = self._validate_web_base_url(web_base_url) if web_base_url else None

    @staticmethod
    def _validate_web_base_url(value: str) -> str:
        try:
            parsed = urlsplit(value)
            valid = (parsed.scheme == "https" and parsed.hostname and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment
                     and parsed.path in {"", "/", "/v2", "/v2/"})
            if not valid:
                raise ValueError
            _ = parsed.port
            return urlunsplit(("https", parsed.netloc, parsed.path.rstrip("/"), "", ""))
        except (TypeError, ValueError):
            raise ValueError("invalid dashboard URL") from None

    def _dashboard_link(self, notification_id: str | None, assignment_id: str | None) -> str | None:
        if self.web_base_url is None:
            return None
        query = {}
        if assignment_id is not None:
            if not isinstance(assignment_id, str) or not re.fullmatch(r"[A-Za-z0-9:._-]{1,128}", assignment_id):
                raise ValueError("invalid assignment reference")
            query["view"] = "work"
            query["assignment_id"] = assignment_id
        else:
            query["view"] = "communications"
        if notification_id is not None:
            try:
                query["notification_id"] = str(UUID(notification_id))
            except (TypeError, ValueError, AttributeError):
                raise ValueError("invalid notification reference") from None
        return f"{self.web_base_url}/?{urlencode(query)}"

    def publish(self, event_type: str, *, notification_id: str | None = None,
                assignment_id: str | None = None) -> str:
        message = _MESSAGES.get(event_type)
        if message is None:
            raise ValueError("unclassified phone notification")
        dashboard_link = self._dashboard_link(notification_id, assignment_id)
        headers = {"Authorization": f"Bearer {self._token}",
                   "Title": _TITLES[event_type],
                   "Priority": str(_PRIORITY[event_type]), "Tags": "riverview",
                   "Content-Type": "text/plain; charset=utf-8"}
        if dashboard_link:
            headers["Click"] = dashboard_link
            # A view action only opens the authenticated V2 page; it cannot mutate receipts or authority.
            headers["Actions"] = f"view,Open in Riverview,{dashboard_link}"
        request = urllib.request.Request(
            f"{self.base_url}/{self._topic}", data=message.encode("utf-8"), method="POST",
            headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(request, timeout=self.timeout) as response:
                payload = json.loads(response.read(8192))
                message_id = payload.get("id") if response.status == 200 else None
                if not isinstance(message_id, str) or not message_id:
                    raise NtfyPublishError("unexpected_ntfy_response")
                return message_id
        except urllib.error.HTTPError as exc:
            raise NtfyPublishError(f"ntfy_http_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            if isinstance(exc, NtfyPublishError):
                raise
            raise NtfyPublishError(type(exc).__name__) from None
