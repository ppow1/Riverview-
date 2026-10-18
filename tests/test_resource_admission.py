# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_resource_admission.py
# Component: RESOURCE-ADMISSION
# Revision: 1.0.0
# Purpose: Verify fresh context, concurrency, suitability, and queue admission outcomes
# Execution Model: Deterministic observations; no endpoint, database, or model
# Observability: Assert selected resource and safe decision reason
# Authority: Admission planning does not grant authority
# Contracts: src/riverview_core/resource_admission.py
# =============================================================================
"""Focused tests for explicit-observation resource admission."""

import unittest
from datetime import datetime, timedelta, timezone

from riverview_core.resource_admission import (
    AdmissionRequest, ResourcePlanner, SlotObservation,
)


class ResourcePlannerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.planner = ResourcePlanner()

    def slot(self, resource_id="80b", **updates):
        values = dict(resource_id=resource_id,
            capabilities=frozenset({"reasoning"}),
            supported_tasks=frozenset({"reasoning"}),
            max_context_tokens=100_000, available_context_tokens=4096,
            active_requests=0, max_concurrency=1, observed_at=self.now)
        values.update(updates)
        return SlotObservation(**values)

    def request(self, **updates):
        values = dict(task="reasoning", required_capability="reasoning",
            input_tokens=3000, output_tokens=512)
        values.update(updates)
        return AdmissionRequest(**values)

    def test_uses_current_free_context_not_model_maximum(self):
        result = self.planner.plan(self.request(),
            [self.slot(available_context_tokens=3500)], now=self.now)
        self.assertEqual((result.status, result.reason, result.queue_position),
                         ("queue", "capacity_unavailable", 1))
        zero = self.planner.plan(self.request(),
            [self.slot(available_context_tokens=0)], now=self.now)
        self.assertEqual((zero.status, zero.reason), ("queue", "capacity_unavailable"))

    def test_admits_only_if_context_budget_and_concurrency_both_fit(self):
        result = self.planner.plan(self.request(), [self.slot(
            available_context_tokens=4096)], now=self.now)
        self.assertEqual((result.status, result.resource_id), ("admit", "80b"))
        full = self.planner.plan(self.request(input_tokens=3000, output_tokens=512),
            [self.slot(active_requests=1, available_context_tokens=10000)], now=self.now)
        self.assertEqual((full.status, full.reason), ("queue", "capacity_unavailable"))

    def test_stale_or_future_observations_never_admit(self):
        for observed_at in (self.now - timedelta(seconds=16),
                            self.now + timedelta(seconds=1)):
            result = self.planner.plan(self.request(),
                [self.slot(observed_at=observed_at)], now=self.now)
            self.assertEqual((result.status, result.reason), ("defer", "observation_stale"))

    def test_idle_30b_is_not_selected_for_unsuitable_text_task(self):
        vision = self.slot("30b", capabilities=frozenset({"vision"}),
            supported_tasks=frozenset({"vision_question"}))
        result = self.planner.plan(self.request(), [vision], now=self.now)
        self.assertEqual((result.status, result.reason), ("defer", "no_suitable_resource"))

    def test_vision_requirement_needs_vision_capability(self):
        result = self.planner.plan(self.request(task="vision_question",
            vision_required=True), [self.slot(supported_tasks=frozenset({"vision_question"}))],
            now=self.now)
        self.assertEqual((result.status, result.reason), ("defer", "no_suitable_resource"))

    def test_vision_slot_admits_explicit_vision_work(self):
        vision = self.slot("30b", capabilities=frozenset({"vision"}),
            supported_tasks=frozenset({"vision_question"}))
        result = self.planner.plan(self.request(task="vision_question",
            required_capability="vision", vision_required=True), [vision], now=self.now)
        self.assertEqual((result.status, result.resource_id), ("admit", "30b"))

    def test_external_advisory_is_separate_from_local_reasoning(self):
        local = self.slot("80b", resource_kind="local")
        external = self.slot("chatgpt", capabilities=frozenset({"advisory"}),
            supported_tasks=frozenset({"advisory"}), resource_kind="external_advisory")
        local_request = self.request(required_capability="reasoning")
        advisory_request = self.request(task="advisory", required_capability="advisory",
            external_advisory=True)
        self.assertEqual(self.planner.plan(local_request, [external], now=self.now).reason,
                         "no_suitable_resource")
        result = self.planner.plan(advisory_request, [local, external], now=self.now)
        self.assertEqual((result.status, result.resource_id), ("admit", "chatgpt"))

    def test_queue_position_accounts_for_existing_queue(self):
        result = self.planner.plan(self.request(), [self.slot(active_requests=1)],
            now=self.now, queue_depth=4)
        self.assertEqual(result.queue_position, 5)

    def test_invalid_free_context_and_counts_rejected(self):
        with self.assertRaises(ValueError):
            self.slot(available_context_tokens=100001)
        with self.assertRaises(ValueError):
            self.slot(active_requests=2)


if __name__ == "__main__":
    unittest.main()
