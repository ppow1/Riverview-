# File Revision: 1.0.0
import io
import json
import logging
import time
import unittest

from riverview_core.diagnostics import (
    _ObjectiveRequestFilter, backend_pid, configure_component_logging, emit,
    safe_sqlstate,
)


class DiagnosticSafetyTests(unittest.TestCase):
    def test_exception_diagnostic_keeps_only_sqlstate_and_backend_pid(self):
        class Diag:
            server_process_id = 321

        class DatabaseError(Exception):
            sqlstate = "42501"
            diag = Diag()

        exc = DatabaseError("private prompt, password=supersecret")
        output = io.StringIO()
        logger = logging.getLogger("test.grace.diagnostics")
        handler = logging.StreamHandler(output)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            emit(logger, logging.ERROR, "grace_work_order_intake_failed",
                 request_id="request-safe", conversation_id="conversation-safe",
                 source_sequence=4, objective_id="objective:sample",
                 failure_stage="event_history", exception_type=type(exc).__name__,
                 sqlstate=safe_sqlstate(exc), backend_pid=backend_pid(exc),
                 private_content=str(exc), password="supersecret")
        finally:
            logger.removeHandler(handler)
            handler.close()
        rendered = output.getvalue()
        record = json.loads(rendered)
        self.assertEqual(record["sqlstate"], "42501")
        self.assertEqual(record["backend_pid"], 321)
        self.assertEqual(record["request_id"], "request-safe")
        self.assertNotIn("private prompt", rendered)
        self.assertNotIn("supersecret", rendered)
        self.assertNotIn("private_content", record)

    def test_sqlstate_and_backend_pid_reject_untrusted_values(self):
        class UnsafeError(Exception):
            sqlstate = "42501 password=secret"
            diag = type("Diag", (), {"server_process_id": "321"})()

        self.assertIsNone(safe_sqlstate(UnsafeError("sensitive")))
        self.assertIsNone(backend_pid(UnsafeError("sensitive")))

    def test_debug_requires_expiry_and_correlation_and_reverts_to_normal(self):
        original = logging.getLogger().level
        try:
            valid = {"RIVERVIEW_DIAGNOSTICS_MODE": "DEBUG",
                     "RIVERVIEW_DIAGNOSTICS_EXPIRES_AT": "1100",
                     "RIVERVIEW_DIAGNOSTICS_OBJECTIVE_ID": "objective:test"}
            self.assertEqual(configure_component_logging(environ=valid, now=1000), "DEBUG")
            self.assertEqual(logging.getLogger().level, logging.DEBUG)
            self.assertEqual(configure_component_logging(environ=valid, now=1200), "NORMAL")
            self.assertEqual(logging.getLogger().level, logging.INFO)
            uncorrelated = dict(valid)
            uncorrelated.pop("RIVERVIEW_DIAGNOSTICS_OBJECTIVE_ID")
            self.assertEqual(configure_component_logging(environ=uncorrelated, now=1000), "NORMAL")
        finally:
            logging.getLogger().setLevel(original)

    def test_debug_timer_returns_root_logger_to_normal(self):
        original = logging.getLogger().level
        settings = {"RIVERVIEW_DIAGNOSTICS_MODE": "DEBUG",
                    "RIVERVIEW_DIAGNOSTICS_EXPIRES_AT": str(time.time() + 0.15),
                    "RIVERVIEW_DIAGNOSTICS_REQUEST_ID": "request-target"}
        try:
            self.assertEqual(configure_component_logging(environ=settings), "DEBUG")
            deadline = time.monotonic() + 1
            while logging.getLogger().level == logging.DEBUG and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertEqual(logging.getLogger().level, logging.INFO)
        finally:
            configure_component_logging(environ={"RIVERVIEW_DIAGNOSTICS_MODE": "NORMAL"})
            logging.getLogger().setLevel(original)

    def test_debug_filter_only_passes_matching_objective_or_request(self):
        filter_ = _ObjectiveRequestFilter("objective:target", "request-target")
        matching = logging.makeLogRecord({"levelno": logging.DEBUG,
                                           "objective_id": "objective:target"})
        unrelated = logging.makeLogRecord({"levelno": logging.DEBUG,
                                            "objective_id": "objective:other"})
        info = logging.makeLogRecord({"levelno": logging.INFO})
        self.assertTrue(filter_.filter(matching))
        self.assertFalse(filter_.filter(unrelated))
        self.assertTrue(filter_.filter(info))

    def test_debug_filter_drops_records_missing_a_single_configured_correlation(self):
        no_correlation = logging.makeLogRecord({"levelno": logging.DEBUG})
        objective_only = _ObjectiveRequestFilter("objective:target", None)
        request_only = _ObjectiveRequestFilter(None, "request-target")
        self.assertFalse(objective_only.filter(no_correlation))
        self.assertFalse(request_only.filter(no_correlation))
        objective_record = logging.makeLogRecord({"levelno": logging.DEBUG,
                                                   "objective_id": "objective:target"})
        request_record = logging.makeLogRecord({"levelno": logging.DEBUG,
                                                 "request_id": "request-target"})
        self.assertTrue(objective_only.filter(objective_record))
        self.assertTrue(request_only.filter(request_record))

    def test_authenticated_outcome_event_has_only_request_and_safe_reason(self):
        output = io.StringIO()
        logger = logging.getLogger("test.grace.auth-outcome")
        handler = logging.StreamHandler(output)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        try:
            emit(logger, logging.INFO, "grace_work_order_auth_accepted",
                 request_id="request-safe", reason_code="steward_source_owned",
                 conversation_id="must-not-be-logged", cookie="secret")
        finally:
            logger.removeHandler(handler)
            handler.close()
        record = json.loads(output.getvalue())
        self.assertEqual(set(record), {"event", "request_id", "reason_code"})


if __name__ == "__main__":
    unittest.main()
