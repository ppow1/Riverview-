# Riverview~ Controlled Source
# File: tests/test_ntfy_publisher.py
# Component: NOTIFICATION-DELIVERY
# Revision: 1.0.0
# Purpose: Verify safe ntfy titles, priorities, deep links and view-only actions
# Execution Model: Local unittest with a fake transport; no live notification
# Observability: unittest case names, counts and exit status
# Dependencies: Python standard library and Riverview notification publisher
# Authority: Synthetic IDs and fake network transport only
# Changed: 2026-10-26 UTC | RV-V2-NTFY-RICH-LINKS-20261026 | Add focused tests for validated links and actions.
# Contracts: docs/components/NOTIFICATION_DELIVERY.md
# History: Initial controlled source
import json
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from riverview_core.notifications.ntfy_publisher import NtfyPhonePublisher


class _Response:
    status = 200
    def read(self, _limit):
        return json.dumps({"id": "safe-message-id"}).encode()
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False


class _Opener:
    def __init__(self):
        self.request = None
    def open(self, request, timeout):
        self.request = request
        self.timeout = timeout
        return _Response()


class NtfyPublisherTests(unittest.TestCase):
    def test_assignment_notification_has_safe_deep_link_and_view_only_action(self):
        opener = _Opener()
        with patch("riverview_core.notifications.ntfy_publisher.urllib.request.build_opener",
                   return_value=opener):
            publisher = NtfyPhonePublisher(
                "https://ntfy.example", topic="protected", token="test-secret",
                web_base_url="https://riverview.example/v2/")
            message_id = publisher.publish(
                "assignment_stalled", notification_id="e8c47c3d-17e8-4b61-93e3-2706bcb0f8a2",
                assignment_id="assignment:42")
        self.assertEqual(message_id, "safe-message-id")
        headers = dict(opener.request.header_items())
        target = headers["Click"]
        parsed = urlsplit(target)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "riverview.example")
        self.assertEqual(parsed.path, "/v2/")
        self.assertEqual(parse_qs(parsed.query), {
            "view": ["work"], "assignment_id": ["assignment:42"],
            "notification_id": ["e8c47c3d-17e8-4b61-93e3-2706bcb0f8a2"]})
        self.assertEqual(headers["Actions"], f"view,Open in Riverview,{target}")
        self.assertEqual(headers["Title"], "Assignment stalled")
        self.assertEqual(headers["Priority"], "4")
        self.assertNotIn("test-secret", target + headers["Actions"])

    def test_notification_only_link_targets_existing_inbox_detail_view(self):
        publisher = NtfyPhonePublisher(
            "https://ntfy.example", topic="protected", token="test-secret",
            web_base_url="https://riverview.example/v2")
        target = publisher._dashboard_link("e8c47c3d-17e8-4b61-93e3-2706bcb0f8a2", None)
        self.assertEqual(parse_qs(urlsplit(target).query), {
            "view": ["communications"],
            "notification_id": ["e8c47c3d-17e8-4b61-93e3-2706bcb0f8a2"]})

    def test_bad_web_origins_and_record_references_are_rejected(self):
        for value in ("http://riverview.example/v2", "https://user:pass@riverview.example/v2",
                      "https://riverview.example/v2?redirect=evil"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                NtfyPhonePublisher("https://ntfy.example", topic="protected", token="test",
                                   web_base_url=value)
        publisher = NtfyPhonePublisher(
            "https://ntfy.example", topic="protected", token="test",
            web_base_url="https://riverview.example/v2")
        with self.assertRaises(ValueError):
            publisher._dashboard_link("not-a-uuid", None)
        with self.assertRaises(ValueError):
            publisher._dashboard_link(None, "../outside")

    def test_without_configured_dashboard_origin_existing_text_transport_stays_unlinked(self):
        opener = _Opener()
        with patch("riverview_core.notifications.ntfy_publisher.urllib.request.build_opener",
                   return_value=opener):
            publisher = NtfyPhonePublisher("https://ntfy.example", topic="protected", token="test")
            self.assertEqual(publisher.publish("monitor_failed"), "safe-message-id")
        headers = dict(opener.request.header_items())
        self.assertNotIn("Click", headers)
        self.assertNotIn("Actions", headers)
        self.assertEqual(headers["Title"], "Notification monitor issue")


if __name__ == "__main__":
    unittest.main()
