"""Offline tests for current-release Grace cancellation and verifier projection."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from riverview_core.institutional_authority.grants import GrantDenied, InstitutionalPrincipal
from riverview_core.resident_execution.comms5_operations import Comms5Operations
from riverview_core.resident_execution.pipeline import GraceExecutionPipeline, ObjectiveNotAuthorized


class _Cursor:
    def __init__(self, state, events):
        self.state, self.events, self.sql = state, events, ""
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params=None):
        self.sql = str(query)
        if self.sql.startswith("UPDATE grace_objectives SET status='CANCELLED'"):
            self.state["status"] = "CANCELLED"
            self.state["revision"] += 1
    def fetchone(self):
        if "FOR UPDATE" in self.sql:
            return {"status": self.state["status"], "scope_ref": "work-order:test",
                    "assignment_id": None, "revision": self.state["revision"]}
        if "SELECT\n                            EXISTS" in self.sql:
            return {"has_assignment": False, "has_dispatch": False, "has_step_activity": False}
        if "RETURNING revision,updated_at" in self.sql:
            return {"revision": self.state["revision"], "updated_at": datetime.now(timezone.utc)}
        if "idempotency_key IN" in self.sql:
            return next(({"event_type": e["event_type"], "payload": e["payload"]}
                         for e in reversed(self.events)), None)
        return None


class _Harness:
    def __init__(self, authorize=True):
        self.state = {"status": "GROUNDED", "revision": 1}
        self.events = []
        self.authorizer = MagicMock()
        if authorize:
            self.authorizer.require_principal.return_value = {"principal_id": "steward:test"}
        else:
            self.authorizer.require_principal.side_effect = GrantDenied("no exact grant")
        cursor = _Cursor(self.state, self.events)
        db = SimpleNamespace(transaction=lambda: _nullcontext(), cursor=lambda: cursor)
        self.pipeline = GraceExecutionPipeline.__new__(GraceExecutionPipeline)
        self.pipeline.ledger = SimpleNamespace(db=db, _set_search_path=lambda cur: None)
        self.pipeline.authorizer = self.authorizer
        self.pipeline.get_objective = lambda _id: {"objective_id": "objective:test",
            "status": self.state["status"], "scope_ref": "work-order:test",
            "revision": self.state["revision"], "assignment_id": None}
        self.pipeline._event = lambda cur, oid, event, idem, actor, payload: self.events.append(
            {"objective_id": oid, "event_type": event, "idempotency_key": idem,
             "actor_id": actor, "payload": payload})


def _nullcontext():
    from contextlib import nullcontext
    return nullcontext()


class GraceCurrentCancellationTests(unittest.TestCase):
    def call(self, harness):
        return harness.pipeline.cancel_work_order("objective:test",
            credential=InstitutionalPrincipal("steward:test"),
            authority_ref="work-order:test", reason="bounded test reason")

    def test_exact_principal_grant_allows_and_repeated_cancel_is_idempotent(self):
        h = _Harness()
        first = self.call(h)
        repeated = self.call(h)
        self.assertEqual(first["status"], "CANCELLED")
        self.assertEqual(repeated["revision"], first["revision"])
        self.assertEqual(len(h.events), 1)
        self.assertEqual(h.authorizer.require_principal.call_args.args[1:],
                         ("steward:test", "assignment.cancel", "work-order:test"))

    def test_exact_principal_grant_denial_does_not_cancel(self):
        h = _Harness(authorize=False)
        with self.assertRaises(ObjectiveNotAuthorized):
            self.call(h)
        self.assertEqual(h.state["status"], "GROUNDED")
        self.assertEqual(h.events, [])

    def test_comms5_route_requires_confirmation_and_uses_authenticated_principal(self):
        from riverview_core.comms5 import dashboard_backend
        pipeline = MagicMock()
        pipeline.get_objective.return_value = {"scope_ref": "work-order:test"}
        pipeline.cancel_work_order.return_value = {"status": "CANCELLED", "revision": 2}
        operations = Comms5Operations(None, None, objective_pipeline=pipeline)
        args = {"objective_id": "objective:test", "reason": "bounded reason",
                "explicit_steward_confirmation": True}
        result = operations.execute("comms5_cancel_objective", args,
                                    principal_id="steward:test")
        self.assertEqual(result["status"], "CANCELLED")
        self.assertIsInstance(pipeline.cancel_work_order.call_args.kwargs["credential"],
                              InstitutionalPrincipal)
        self.assertIn("comms5_cancel_objective", Comms5Operations.SUPPORTED)
        self.assertIn("comms5_cancel_objective", dashboard_backend._INTERNAL_TOOLS)
        with self.assertRaises(PermissionError):
            operations.execute("comms5_cancel_objective",
                {**args, "explicit_steward_confirmation": False}, principal_id="steward:test")
        self.assertEqual(pipeline.cancel_work_order.call_count, 1)


if __name__ == "__main__":
    unittest.main()
