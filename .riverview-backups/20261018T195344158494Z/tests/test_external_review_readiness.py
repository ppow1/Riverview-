# =============================================================================
# RIVERVIEW~ CONTROLLED TEST SOURCE
# File: tests/test_external_review_readiness.py
# Component: EXTERNAL-REVIEW-READINESS
# Revision: 1.0.0
# Purpose: Verify privacy, expiry, stale evidence, and fail-closed readiness projection
# Execution Model: Isolated unit tests; no network, browser, database, or provider access
# Observability: unittest assertions over bounded projection schema
# Dependencies: Python standard library; riverview_core.external_review_readiness
# Authority: Synthetic metadata only; no external action is performed
# Changed: 2026-10-18 UTC | RV-C1-EXTERNAL-REVIEW-READINESS-001 | Initial redacted fixtures
# Contracts: docs/components/EXTERNAL_REVIEW_READINESS.md
# History: Git
# =============================================================================

from datetime import datetime, timedelta, timezone
import unittest

from riverview_core.external_review_readiness import (
    DOORBELL_SCHEMA_VERSION,
    SCHEMA_VERSION,
    project_external_review_readiness,
)


NOW = datetime(2026, 10, 18, 20, 0, tzinfo=timezone.utc)


def exchange(state="awaiting_delivery", **updates):
    result = {
        "request_id": "7e2184c6-48f4-42fd-8ba2-d5a17732a96a",
        "correlation_id": "8b99f4b5-7837-4106-b0f5-284c6fd407c2",
        "delivery_state": state,
        "deadline_at": (NOW + timedelta(minutes=10)).isoformat(),
        "last_error_code": None,
        # This must never escape into an operator status projection.
        "request_payload": {"secret_proposal_body": "private proposal fixture"},
    }
    result.update(updates)
    return result


def doorbell(**updates):
    result = {
        "schema_version": DOORBELL_SCHEMA_VERSION,
        "component_id": "CHATGPT-DOORBELL",
        "component_version": "1.0.2",
        "observed_at": NOW.isoformat(),
        "status": "healthy",
        "ready": False,
        "browser_health": "healthy",
        "local_browser_ready": True,
        "freshness": {"state": "fresh", "stale_after_seconds": 60},
        "cdp": {"status": "connected", "address": "127.0.0.1", "port": 9225},
        "browser_runtime": True,
        "browser_session": "running",
        "authentication_status": "composer_ready",
        "target_resolution": "exact_match",
        "fixed_action_available": True,
        "last_trigger": None,
        "last_error": None,
        "blockers": [],
        "external_dependencies": {
            "comms5_mailbox": {"owner": "Codex1", "state": "available", "contract_reference": "issue:120"},
            "grace_result_consumer": {"owner": "Codex2", "state": "available", "contract_reference": "issue:120"},
        },
        "workflow_position": None,
        "workflow_position_reason": "No fixture workflow position.",
        "browser_process": {"state": "running", "started_at": NOW.isoformat()},
        "profile_lock_present": False,
    }
    result.update(updates)
    return result


class ExternalReviewReadinessTests(unittest.TestCase):
    def project(self, exchange_status=None, browser=None, **kwargs):
        kwargs.setdefault("trigger_status", "ready")
        return project_external_review_readiness(
            exchange_status if exchange_status is not None else exchange(),
            browser if browser is not None else doorbell(),
            now=NOW,
            **kwargs,
        )

    def test_ready_for_doorbell_is_coarse_and_redacted(self):
        result = self.project()
        self.assertEqual(result["schema_version"], SCHEMA_VERSION)
        self.assertEqual(result["readiness"], "ready")
        self.assertEqual(result["state"], "ready_for_doorbell")
        self.assertEqual(result["next_action"], "doorbell_owner_may_wake")
        self.assertEqual(result["deadline_seconds_remaining"], 600)
        serialized = repr(result)
        for secret in ("7e2184c6-48f4-42fd-8ba2-d5a17732a96a",
                       "8b99f4b5-7837-4106-b0f5-284c6fd407c2",
                       "private proposal fixture"):
            self.assertNotIn(secret, serialized)

    def test_unverified_or_unconfigured_trigger_never_looks_ready(self):
        unverified = self.project(trigger_status=None)
        self.assertEqual(unverified["state"], "doorbell_trigger_unverified")
        self.assertEqual(unverified["readiness"], "degraded")
        missing = self.project(trigger_status="not_configured")
        self.assertEqual(missing["state"], "doorbell_not_configured")
        self.assertNotEqual(missing["readiness"], "ready")

    def test_missing_exchange_is_reported_without_identifiers(self):
        result = self.project(exchange_status=None)
        self.assertEqual(result["state"], "ready_for_doorbell")
        unavailable = project_external_review_readiness(None, doorbell(), now=NOW)
        self.assertEqual(unavailable["state"], "mailbox_unavailable")
        self.assertEqual(unavailable["failure_code"], "mailbox_unavailable")
        self.assertNotIn("request_id", unavailable)

    def test_missing_or_unknown_browser_auth_and_target_fail_closed(self):
        missing = project_external_review_readiness(exchange(), None, now=NOW)
        self.assertEqual(missing["state"], "doorbell_status_unavailable")
        unknown_auth = self.project(browser=doorbell(authentication_status="unknown"))
        self.assertEqual(unknown_auth["state"], "browser_authentication_unknown")
        unknown_target = self.project(browser=doorbell(target_resolution="unknown"))
        self.assertEqual(unknown_target["state"], "browser_target_unresolved")

    def test_stale_and_malformed_browser_status_fail_closed(self):
        stale = doorbell(observed_at=(NOW - timedelta(minutes=6)).isoformat())
        result = self.project(browser=stale)
        self.assertEqual(result["readiness"], "stale")
        malformed = self.project(browser=doorbell(schema_version="unknown"))
        self.assertEqual(malformed["failure_code"], "malformed_doorbell_status")
        bad_health = self.project(browser=doorbell(cdp={"status": "healthy but private detail"}))
        self.assertEqual(bad_health["failure_code"], "malformed_doorbell_status")

    def test_exchange_expiry_and_terminal_states(self):
        past = exchange(deadline_at=(NOW - timedelta(seconds=1)).isoformat())
        self.assertEqual(self.project(exchange_status=past)["state"], "review_expired")
        expired = self.project(exchange_status=exchange("expired"))
        self.assertEqual(expired["next_action"], "record_expiry")
        self.assertEqual(expired["deadline_seconds_remaining"], 0)
        consumed = self.project(exchange_status=exchange("grace_consumed"))
        self.assertEqual(consumed["state"], "grace_evaluated")
        self.assertEqual(consumed["next_action"], "continue_objective")

    def test_response_ready_for_grace_consumption(self):
        late_but_durable = exchange("response_received",
            deadline_at=(NOW - timedelta(seconds=1)).isoformat())
        result = self.project(exchange_status=late_but_durable)
        self.assertEqual(result["state"], "response_received")
        self.assertEqual(result["next_action"], "grace_consume_and_evaluate")
        self.assertIsNone(result["deadline_seconds_remaining"])
        self.assertNotIn("request_payload", result)

    def test_provider_rejection_is_visible_only_as_stable_code(self):
        result = self.project(
            exchange_status=exchange("response_received"),
            provider_submission={"outcome": "rejected", "error": "secret provider detail"},
        )
        self.assertEqual(result["state"], "response_rejected")
        self.assertNotIn("secret provider detail", repr(result))

    def test_wake_retry_and_correlation_mismatch(self):
        retry = self.project(wake_receipt={
            "request_id": "7e2184c6-48f4-42fd-8ba2-d5a17732a96a",
            "correlation_id": "8b99f4b5-7837-4106-b0f5-284c6fd407c2",
            "outcome": "ambiguous", "safe_error_code": "RIV-PLY-0009",
        })
        self.assertEqual(retry["state"], "retry_recovery")
        self.assertTrue(retry["retryable"])
        mismatch = self.project(wake_receipt={
            "request_id": "d462ce45-c387-4cda-838d-97f2a102ade7",
            "correlation_id": "8b99f4b5-7837-4106-b0f5-284c6fd407c2",
            "outcome": "submitted",
        })
        self.assertEqual(mismatch["failure_code"], "correlation_mismatch")
        self.assertNotIn("d462ce45-c387-4cda-838d-97f2a102ade7", repr(mismatch))

    def test_doorbell_last_trigger_reports_failure_and_verified_wake(self):
        failed = doorbell(last_trigger={
            "attempt_id": "attempt-private", "request_id": "7e2184c6-48f4-42fd-8ba2-d5a17732a96a",
            "correlation_id": "8b99f4b5-7837-4106-b0f5-284c6fd407c2", "occurred_at": NOW.isoformat(),
            "status": "failed", "failure_class": "RIV-PLY-0009", "submit_verified": False,
        })
        result = self.project(browser=failed)
        self.assertEqual(result["state"], "retry_recovery")
        self.assertNotIn("attempt-private", repr(result))
        succeeded = doorbell(last_trigger={
            "attempt_id": "attempt-private", "request_id": "7e2184c6-48f4-42fd-8ba2-d5a17732a96a",
            "correlation_id": "8b99f4b5-7837-4106-b0f5-284c6fd407c2", "occurred_at": NOW.isoformat(),
            "status": "succeeded", "failure_class": None, "submit_verified": True,
        })
        result = self.project(browser=succeeded)
        self.assertEqual(result["state"], "wake_submitted_waiting_for_claim")
        self.assertNotEqual(result["state"], "response_received")

    def test_malformed_exchange_fails_closed(self):
        result = self.project(exchange_status={"delivery_state": "surprise", "deadline_at": "bad"})
        self.assertEqual(result["state"], "invalid_exchange_status")
        self.assertFalse(result["retryable"])

    def test_bad_clock_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            project_external_review_readiness(exchange(), doorbell(), now=datetime(2026, 10, 18))
        with self.assertRaises(ValueError):
            project_external_review_readiness(exchange(), doorbell(), now=NOW,
                                              max_status_age=timedelta(days=2))


if __name__ == "__main__":
    unittest.main()
