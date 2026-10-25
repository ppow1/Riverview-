# Revision: 1.0.0
"""Focused precedence and freshness tests for the objective status projection."""
from datetime import datetime, timedelta, timezone
import unittest

from riverview_core.status_dashboard.operational_status import derive_operational_status


NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
REVISION = 4


def event(kind, seconds_ago=1, **extra):
    return {"event_type": kind, "event_id": "event-test",
            "occurred_at": NOW - timedelta(seconds=seconds_ago), **extra}


class ObjectiveOperationalStatusTests(unittest.TestCase):
    def derive(self, **values):
        defaults = {"lifecycle_status": "GROUNDED", "revision": REVISION,
                    "assignment_state": None, "latest_event": event("objective.grounded", 60),
                    "now": NOW}
        defaults.update(values)
        return derive_operational_status(**defaults)

    def test_genuinely_waiting_for_authorization(self):
        self.assertEqual(self.derive()["label"], "Awaiting authorization")

    def test_fresh_unresolved_reasoning_and_stale_attempt(self):
        fresh = self.derive(latest_event=event("execution.reasoning_attempted", 4))
        stale = self.derive(latest_event=event("execution.reasoning_attempted", 90))
        self.assertEqual(fresh["label"], "Reasoning in progress")
        self.assertEqual(stale["label"], "Unknown")

    def test_criteria_binding_failure_only_for_current_revision(self):
        failure = {**event("execution.reasoning_failed", 2),
                   "detail_code": "PROPOSAL_CRITERIA_BINDING_REJECTED",
                   "status": "BLOCKED", "objective_revision": REVISION}
        self.assertEqual(self.derive(latest_event=failure, criteria_failure=failure)["label"],
                         "Blocked — proposal criteria binding")
        old = {**failure, "objective_revision": REVISION - 1}
        self.assertNotEqual(self.derive(latest_event=old, criteria_failure=old)["label"],
                            "Blocked — proposal criteria binding")

    def test_pending_approval_and_autonomous_recovery(self):
        pending = {"status": "pending", "objective_revision": REVISION,
                   "occurred_at": NOW - timedelta(seconds=8),
                   "expires_at": NOW + timedelta(minutes=5)}
        recovery = {"occurred_at": NOW - timedelta(seconds=2),
                    "event_type": "luna_reserved", "source": "grace_supervisory_authorization_events"}
        self.assertEqual(self.derive(recovery_approval=pending)["label"],
                         "Recovery approval pending")
        self.assertEqual(self.derive(recovery_approval=pending, supervisor_recovery=recovery)["label"],
                         "Recovery in progress")
        pending["expires_at"] = NOW - timedelta(seconds=1)
        self.assertNotEqual(self.derive(recovery_approval=pending)["label"],
                            "Recovery approval pending")

    def test_engineering_and_terminal_state_dominate_old_activity(self):
        self.assertEqual(self.derive(assignment_state="running")["label"],
                         "Engineering executing")
        self.assertEqual(self.derive(lifecycle_status="COMPLETED",
                                     latest_event=event("execution.reasoning_attempted", 1))["label"],
                         "Completed")
        self.assertEqual(self.derive(assignment_state="ready")["label"], "Unknown")

    def test_newer_execution_supersedes_old_reasoning_and_equal_conflict_is_unknown(self):
        current = {"occurred_at": NOW - timedelta(seconds=1),
                   "event_type": "luna_reserved", "source": "supervisor"}
        old = {"occurred_at": NOW - timedelta(seconds=20),
               "status": "pending", "objective_revision": REVISION,
               "expires_at": NOW + timedelta(minutes=5)}
        self.assertEqual(self.derive(recovery_approval=old, supervisor_recovery=current)["label"],
                         "Recovery in progress")
        conflicting = {**current, "occurred_at": old["occurred_at"]}
        self.assertEqual(self.derive(recovery_approval=old, supervisor_recovery=conflicting)["label"],
                         "Unknown")

    def test_multiple_objectives_are_independent(self):
        first = self.derive()
        second = self.derive(latest_event=event("execution.reasoning_attempted", 2))
        self.assertEqual(first["label"], "Awaiting authorization")
        self.assertEqual(second["label"], "Reasoning in progress")


if __name__ == "__main__":
    unittest.main()
