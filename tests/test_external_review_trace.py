# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_external_review_trace.py
# Component: EXTERNAL-REVIEW-OBSERVABILITY
# Revision: 1.0.1
# Purpose: Verify exact review correlation and redacted operator projection
# Execution Model: Isolated synthetic metadata; no network or database access
# Observability: unittest assertions over sanitized trace reports
# Dependencies: Python standard library
# Authority: Tests never contact browser, mailbox, ChatGPT, or production
# Changed: 2026-10-18 UTC | RV-P0-W1-INTEGRATION-EVIDENCE | Test C3 successor lineage and actor attribution
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================

import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from riverview_core.resident_execution.external_review_trace import (
    SCHEMA_VERSION, TraceInputError, build_report, parse_bundle,
)

_CLI_SPEC = importlib.util.spec_from_file_location(
    "report_external_review", Path(__file__).resolve().parents[1] /
    "scripts" / "report_external_review.py")
_CLI = importlib.util.module_from_spec(_CLI_SPEC)
_CLI_SPEC.loader.exec_module(_CLI)


REQUEST = "3cae4f72-7eed-4e27-8f17-32d73d8554a1"
CORRELATION = "799ec3c4-e18f-4eae-a674-b395cb28d8f3"
HASH = "a" * 64
RESPONSE_HASH = "b" * 64


def round_record(*, exchange="grace_consumed", doorbell="submitted",
                 provider="response_received", decision="accept",
                 evaluated=True, consumed=True):
    return {
        "review_subject": {"schema_version": "rv.proposal-review-subject.v1",
                    "subject_id": "proposal-review:synthetic-1", "revision": 1, "sha256": HASH,
                    "private_proposal_body": "must never appear in report"},
        "exchange": {"request_id": REQUEST, "correlation_id": CORRELATION, "state": exchange,
                     "eligible_at": "2026-10-18T14:59:59-04:00",
                     "events": [
                         {"event_type": "delivery_claimed", "occurred_at": "2026-10-18T14:59:59-04:00",
                          "actor_id": "synthetic:browser-doorbell", "payload": {"fence": 1, "private_token": "never-copy"}},
                         ({"event_type": "delivered", "occurred_at": "2026-10-18T15:00:01-04:00",
                           "actor_id": "synthetic:browser-doorbell",
                           "payload": {"state": "awaiting_external_claim", "delivery_attempt": 1}}
                          if doorbell == "submitted" else
                          {"event_type": "delivery_failed", "occurred_at": "2026-10-18T15:00:01-04:00",
                           "actor_id": "synthetic:browser-doorbell",
                           "payload": {"state": "awaiting_delivery", "error_code": "browser_timeout",
                                       "retryable": doorbell == "ambiguous"}}),
                         {"event_type": "claimed", "occurred_at": "2026-10-18T15:00:02-04:00",
                          "actor_id": "synthetic:provider", "payload": {"state": "awaiting_response"}},
                         {"event_type": "response_received", "occurred_at": "2026-10-18T15:00:03-04:00",
                          "actor_id": "synthetic:provider", "payload": {"response_sha256": RESPONSE_HASH,
                                                                            "private": "never-copy"}}]},
        "doorbell_owner_id": "synthetic:browser-doorbell",
        "provider": {"request_id": REQUEST, "correlation_id": CORRELATION,
                     "delivery_state": ("awaiting_response" if provider == "claimed" else
                                        "awaiting_external_claim" if provider == "listed" else provider),
                     "provider_id": "synthetic:chatgpt-test",
                     "review_subject_sha256": HASH,
                     "response_body": "private"},
        "grace": {"request_id": REQUEST, "correlation_id": CORRELATION,
                  "review_sha256": HASH,
                  "decision": decision if evaluated else None,
                  "evaluated_at": "2026-10-18T15:00:04-04:00" if evaluated else None,
                  "consumed_at": "2026-10-18T15:00:05-04:00" if consumed else None,
                  "access_token": "never-copy"},
    }


def bundle(*rounds, execution_kind="synthetic"):
    return {"schema_version": SCHEMA_VERSION, "execution_kind": execution_kind,
            "rounds": list(rounds)}


class ExternalReviewTraceTests(unittest.TestCase):
    def test_exact_correlated_acceptance_is_complete_and_redacted(self):
        report = build_report(bundle(round_record()))
        encoded = json.dumps(report)
        self.assertEqual(report["outcome"], "complete")
        self.assertTrue(report["complete"])
        self.assertEqual(report["rounds"][0]["request_id"], REQUEST)
        self.assertEqual(report["rounds"][0]["correlation_id"], CORRELATION)
        self.assertEqual(report["rounds"][0]["review_sha256"], HASH)
        self.assertTrue(report["rounds"][0]["mailbox_eligible"])
        self.assertEqual(report["evidence_level"], "synthetic_metadata_only")
        self.assertFalse(report["execution_kind_verified"])
        for private in ("private_proposal_body", "must never appear", "response_body", "access_token", "cookie"):
            self.assertNotIn(private, encoded)

    def test_wake_submission_receipt_alone_is_not_completion(self):
        record = round_record(exchange="awaiting_response", doorbell="submitted",
                              provider="not_seen", decision=None, evaluated=False, consumed=False)
        report = build_report(bundle(record, execution_kind="external"))
        self.assertEqual(report["outcome"], "in_progress")
        self.assertEqual(report["evidence_level"], "external_metadata_unverified")
        self.assertFalse(report["execution_kind_verified"])
        self.assertFalse(report["complete"])
        self.assertEqual(report["rounds"][0]["state"], "wake_submitted")

    def test_expiry_and_failed_delivery_are_blocked(self):
        report = build_report(bundle(round_record(exchange="expired", decision=None,
                                                  evaluated=False, consumed=False)))
        self.assertEqual(report["outcome"], "blocked")
        self.assertIn("expired", report["rounds"][0]["blockers"])

    def test_retryable_delivery_failure_remains_retryable_not_complete(self):
        record = round_record(exchange="awaiting_delivery", doorbell="ambiguous",
                              provider="not_seen", decision=None, evaluated=False, consumed=False)
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "in_progress")
        self.assertEqual(report["rounds"][0]["state"], "delivery_retry_pending")
        self.assertEqual(report["rounds"][0]["doorbell_error_code"], "browser_timeout")

    def test_delivery_lease_is_not_reported_as_browser_attempt(self):
        record = round_record(exchange="awaiting_delivery", doorbell="not_attempted",
                              provider="not_seen", decision=None, evaluated=False, consumed=False)
        record["exchange"]["events"] = [
            {"event_type": "delivery_claimed", "occurred_at": "2026-10-18T15:00:00-04:00",
             "actor_id": "synthetic:browser-doorbell",
             "payload": {"fence": 2}}
        ]
        report = build_report(bundle(record))
        round_report = report["rounds"][0]
        self.assertEqual(round_report["state"], "doorbell_claimed")
        self.assertEqual(round_report["next_action"], "await_or_reconcile_durable_wake_receipt")
        self.assertIsNone(round_report["doorbell_attempted_at"])
        self.assertTrue(round_report["mailbox_eligible"])

    def test_mcp_mark_delivered_event_is_not_misreported_as_browser_wake(self):
        record = round_record()
        record["exchange"]["events"][1]["actor_id"] = "mcp:chatgpt-test"
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertIn("acceptance_not_durably_consumed", report["rounds"][0]["blockers"])
        self.assertIn("doorbell_owner_mismatch", report["rounds"][0]["blockers"])
        self.assertEqual(report["rounds"][0]["doorbell_outcome"], "not_attempted")

        record["exchange"]["events"][1]["actor_id"] = "synthetic:browser-doorbell"
        record["exchange"]["events"].append({
            "event_type": "delivered", "occurred_at": "2026-10-18T15:00:02-04:00",
            "actor_id": "mcp:chatgpt-test", "payload": {"state": "awaiting_external_claim"},
        })
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "complete")
        self.assertFalse(report["rounds"][0]["doorbell_source_mismatch"])

    def test_c3_doorbell_receipt_event_supports_ambiguous_and_submitted(self):
        record = round_record()
        record["exchange"]["events"][1] = {
            "event_type": "doorbell_receipt", "occurred_at": "2026-10-18T15:00:01-04:00",
            "actor_id": "synthetic:browser-doorbell",
            "payload": {"outcome": "ambiguous", "attempt_id": "attempt-1",
                        "safe_error_code": "RIV-PLY-0003"},
        }
        report = build_report(bundle(record))
        self.assertEqual(report["rounds"][0]["doorbell_outcome"], "ambiguous")
        self.assertEqual(report["outcome"], "blocked")

        record["exchange"]["events"][1]["payload"]["outcome"] = "submitted"
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "complete")

    def test_c3_delivery_acknowledgement_is_attributed_wake_receipt(self):
        record = round_record()
        record["exchange"]["events"][1] = {
            "event_type": "delivery_acknowledged", "occurred_at": "2026-10-18T15:00:01-04:00",
            "actor_id": "synthetic:browser-doorbell",
            "payload": {"attempt_id": "attempt-1"},
        }
        report = build_report(bundle(record))
        self.assertEqual(report["rounds"][0]["doorbell_outcome"], "submitted")
        self.assertEqual(report["rounds"][0]["doorbell_attempt_id"], "attempt-1")
        self.assertEqual(report["outcome"], "complete")

    def test_c3_grace_events_supply_evaluation_and_consumption_metadata(self):
        record = round_record()
        record["grace"] = {"events": [{
            "event_type": "resident.reasoning.external_proposal_reviewed",
            "actor_id": "office:synthetic-grace",
            "occurred_at": "2026-10-18T15:00:04-04:00",
            "payload": {"request_id": REQUEST, "correlation_id": CORRELATION,
                        "subject_id": "proposal-review:synthetic-1", "revision": 1,
                        "subject_sha256": HASH, "response_sha256": RESPONSE_HASH,
                        "decision": "finish"},
        }]}
        record["exchange"]["events"].append({
            "event_type": "grace_consumed", "occurred_at": "2026-10-18T15:00:05-04:00",
            "request_id": REQUEST, "correlation_id": CORRELATION, "payload": {},
        })
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "complete")
        self.assertEqual(report["rounds"][0]["grace_reviewed_revision"], 1)

    def test_c3_review_blocked_event_cannot_be_reported_complete(self):
        record = round_record()
        record["grace"] = {"events": [{
            "event_type": "resident.reasoning.external_proposal_review_blocked",
            "actor_id": "office:synthetic-grace",
            "occurred_at": "2026-10-18T15:00:04-04:00",
            "payload": {"request_id": REQUEST, "correlation_id": CORRELATION,
                        "subject_id": "proposal-review:synthetic-1", "revision": 1,
                        "subject_sha256": HASH,
                        "decision": "accept"},
        }]}
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertIn("grace_blocked", report["rounds"][0]["blockers"])

    def test_c3_revision_event_maps_result_digest_and_successor_ids(self):
        record = round_record(decision="revise")
        record["grace"] = {"events": [{
            "event_type": "resident.reasoning.external_proposal_revised",
            "actor_id": "office:synthetic-grace",
            "occurred_at": "2026-10-18T15:00:04-04:00",
            "payload": {"request_id": REQUEST, "correlation_id": CORRELATION,
                        "subject_id": "proposal-review:synthetic-2", "revision": 2,
                        "subject_sha256": "c" * 64, "response_sha256": RESPONSE_HASH,
                        "proposal_sha256": "d" * 64, "decision": "revise",
                        "successor_request_id": "c44d68af-1d9c-458f-829d-9e2fced39894",
                        "successor_correlation_id": "99339a0a-bc79-463d-abd8-c8b2e0f8fe91"},
        }]}
        record["exchange"]["events"].append({
            "event_type": "grace_consumed", "occurred_at": "2026-10-18T15:00:05-04:00",
            "request_id": REQUEST, "correlation_id": CORRELATION, "payload": {},
        })
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "review_required")
        self.assertEqual(report["rounds"][0]["revised_version"], 2)
        self.assertEqual(report["rounds"][0]["revised_sha256"], "c" * 64)
        self.assertEqual(report["rounds"][0]["successor_request_id"],
                         "c44d68af-1d9c-458f-829d-9e2fced39894")
        successor = copy.deepcopy(round_record())
        successor["review_subject"].update(subject_id="proposal-review:synthetic-2",
                                             revision=2, sha256="c" * 64)
        successor["exchange"].update(request_id="c44d68af-1d9c-458f-829d-9e2fced39894",
                                      correlation_id="99339a0a-bc79-463d-abd8-c8b2e0f8fe91")
        successor["provider"].update(request_id=successor["exchange"]["request_id"],
                                      correlation_id=successor["exchange"]["correlation_id"],
                                      review_subject_sha256="c" * 64)
        successor["grace"].update(request_id=successor["exchange"]["request_id"],
                                   correlation_id=successor["exchange"]["correlation_id"],
                                   review_sha256="c" * 64)
        report = build_report(bundle(record, successor))
        self.assertEqual(report["outcome"], "complete")

        wrong_successor = copy.deepcopy(successor)
        wrong_successor["exchange"]["request_id"] = "d44d68af-1d9c-458f-829d-9e2fced39894"
        wrong_successor["provider"]["request_id"] = wrong_successor["exchange"]["request_id"]
        wrong_successor["grace"]["request_id"] = wrong_successor["exchange"]["request_id"]
        with self.assertRaisesRegex(TraceInputError, "revision_successor_identity_mismatch"):
            build_report(bundle(record, wrong_successor))

    def test_c3_grace_event_requires_office_actor(self):
        record = round_record()
        record["grace"] = {"events": [{
            "event_type": "resident.reasoning.external_proposal_reviewed",
            "actor_id": "mcp:synthetic-provider",
            "occurred_at": "2026-10-18T15:00:04-04:00",
            "payload": {"request_id": REQUEST, "correlation_id": CORRELATION,
                        "subject_id": "proposal-review:synthetic-1", "revision": 1,
                        "subject_sha256": HASH, "decision": "finish"},
        }]}
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertIn("grace_event_actor_unverified", report["rounds"][0]["blockers"])

    def test_request_or_correlation_mismatch_fails_closed(self):
        record = round_record()
        record["provider"]["correlation_id"] = "7a9c8530-e56e-41d4-9782-cdb7ab39a8ae"
        with self.assertRaisesRegex(TraceInputError, "provider_correlation_mismatch"):
            build_report(bundle(record))

    def test_provider_or_grace_wrong_review_hash_blocks(self):
        record = round_record()
        record["provider"]["review_subject_sha256"] = "c" * 64
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertIn("provider_review_subject_mismatch", report["rounds"][0]["blockers"])

    def test_acceptance_without_evaluation_or_consumption_cannot_complete(self):
        record = round_record(consumed=False)
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertFalse(report["complete"])
        self.assertIn("acceptance_not_durably_consumed", report["rounds"][0]["blockers"])

    def test_grace_consumption_without_matching_evaluation_is_blocked(self):
        record = round_record(decision=None, evaluated=False, consumed=True)
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertIn("grace_consumed_without_evaluation", report["rounds"][0]["blockers"])

    def test_acceptance_without_provider_response_or_wake_receipt_cannot_complete(self):
        record = round_record(provider="claimed", doorbell="ambiguous")
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertFalse(report["complete"])
        self.assertIn("acceptance_not_durably_consumed", report["rounds"][0]["blockers"])

    def test_revision_requires_new_round_for_completion(self):
        first = round_record(decision="revise", consumed=True)
        first["grace"]["revised_version"] = 2
        first["grace"]["revised_sha256"] = "c" * 64
        first["grace"]["successor_request_id"] = "c44d68af-1d9c-458f-829d-9e2fced39894"
        first["grace"]["successor_correlation_id"] = "99339a0a-bc79-463d-abd8-c8b2e0f8fe91"
        second = copy.deepcopy(round_record())
        second["review_subject"].update(subject_id="proposal-review:synthetic-2", revision=2, sha256="c" * 64)
        second["exchange"].update(request_id="c44d68af-1d9c-458f-829d-9e2fced39894",
                                  correlation_id="99339a0a-bc79-463d-abd8-c8b2e0f8fe91")
        second["provider"].update(request_id=second["exchange"]["request_id"],
                                   correlation_id=second["exchange"]["correlation_id"],
                                   review_subject_sha256="c" * 64)
        second["grace"].update(request_id=second["exchange"]["request_id"],
                               correlation_id=second["exchange"]["correlation_id"],
                               review_sha256="c" * 64)
        report = build_report(bundle(first, second))
        self.assertEqual(report["outcome"], "complete")
        self.assertEqual(report["round_count"], 2)

        second["review_subject"]["sha256"] = "d" * 64
        second["provider"]["review_subject_sha256"] = "d" * 64
        second["grace"]["review_sha256"] = "d" * 64
        with self.assertRaisesRegex(TraceInputError, "revision_successor_subject_mismatch"):
            build_report(bundle(first, second))

    def test_revision_without_revised_subject_requires_re_review(self):
        record = round_record(decision="revise")
        report = build_report(bundle(record))
        self.assertEqual(report["outcome"], "blocked")
        self.assertIn("revision_not_recorded", report["rounds"][0]["blockers"])

    def test_parse_bundle_enforces_size_and_schema(self):
        valid = json.dumps(bundle(round_record())).encode()
        report = parse_bundle(valid)
        self.assertEqual(report["outcome"], "complete")
        with self.assertRaisesRegex(TraceInputError, "input_too_large"):
            parse_bundle(b" " * (256 * 1024 + 1))
        with self.assertRaisesRegex(TraceInputError, "unsupported_schema_version"):
            build_report({"schema_version": "other", "rounds": []})

    def test_unsafe_error_code_is_rejected_without_echoing_value(self):
        record = round_record(exchange="awaiting_delivery", doorbell="ambiguous",
                              provider="not_seen", decision=None, evaluated=False, consumed=False)
        record["exchange"]["events"][1]["payload"]["error_code"] = "private token value"
        with self.assertRaisesRegex(TraceInputError, "invalid_safe_error_code"):
            build_report(bundle(record))

    def test_cli_emits_only_redacted_report_and_distinguishes_exit_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "trace.json"
            snapshot.write_text(json.dumps(bundle(round_record())), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                code = _CLI.main([str(snapshot)])
            self.assertEqual(code, 0)
            self.assertNotIn("private", output.getvalue())
            self.assertIn('"outcome":"complete"', output.getvalue())

            snapshot.write_text(json.dumps(bundle(round_record(exchange="expired",
                decision=None, evaluated=False, consumed=False))), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                code = _CLI.main([str(snapshot)])
            self.assertEqual(code, 1)

            snapshot.write_text("not json", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                code = _CLI.main([str(snapshot)])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
