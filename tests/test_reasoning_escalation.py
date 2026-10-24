# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_reasoning_escalation.py
# Component: RESIDENT-REASONING
# Revision: 1.0.1
# Purpose: Verify bounded, correlated, exact-grant reasoning escalation
# Execution Model: Isolated synthetic providers; no network or external model call
# Observability: Typed success/denial/failure outcomes and invocation boundaries
# Dependencies: unittest; Riverview resident reasoning contracts
# Authority: A proposal never creates or authorizes an engineering assignment
# Changed: 2026-10-13 UTC | RV-REASONING-ESCALATION-CONTRACT | Add contract regression tests
# Changed: 2026-10-13 UTC | RV-REASONING-ESCALATION-AUTHORITY-STATUS | Test denial and authority-check outage as distinct fail-closed results
# Contracts: docs/components/RESIDENT_REASONING.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Synthetic contract tests; they are not evidence of a live provider route."""

import unittest

from riverview_core.reasoning_escalation import (
    EscalationStatus, ReasoningEscalationRouter, EscalationRequest)
from riverview_core.resident_reasoning import PlanProposal, PlanStep, ReasoningRequest
from riverview_core.institutional_authority import GrantCheckUnavailable


def request():
    return ReasoningRequest(
        request_id="request-1", office_id="grace", assignment_id="objective-1",
        assignment_revision="rev-4", binding_revision=8,
        implementation_revision="model-sha256", trigger="objective_grounded",
        token_budget=64, assignment={"objective": "bounded review"},
        verified_knowledge=({"source": "repo://example", "revision": "abc"},),
        prior_plan=None)


class Provider:
    provider_id = "provider:synthetic-high"

    def __init__(self, result=None):
        self.result = result or PlanProposal("bounded result",
            (PlanStep("review", "Review verified facts", ("facts are cited",)),), 24)
        self.calls = []

    def propose(self, req):
        self.calls.append(req)
        return self.result


class EscalationContractTests(unittest.TestCase):
    def test_success_preserves_objective_context_and_requires_exact_provider_grant(self):
        original = request()
        provider = Provider()
        router = ReasoningEscalationRouter({provider.provider_id: provider})
        envelope = EscalationRequest.create(original, reason="task_complexity",
            target_provider_id=provider.provider_id, max_tokens=48, timeout_seconds=2)
        checks = []
        result = router.execute(envelope, original, principal_id="resident:grace",
            authorize=lambda principal, action, scope: checks.append(
                (principal, action, scope)) or True)
        self.assertEqual(result.status, EscalationStatus.PROPOSED)
        self.assertEqual(result.original_request_id, original.request_id)
        self.assertEqual(result.context_sha256, envelope.context_sha256)
        self.assertEqual(checks, [("resident:grace", "resident.reasoning.escalate",
                                  "provider:" + provider.provider_id)])
        self.assertEqual(provider.calls[0].assignment_revision, original.assignment_revision)
        self.assertEqual(provider.calls[0].verified_knowledge, original.verified_knowledge)
        self.assertEqual(provider.calls[0].token_budget, 48)

    def test_denial_does_not_call_provider(self):
        original = request()
        provider = Provider()
        envelope = EscalationRequest.create(original, reason="capability_gap",
            target_provider_id=provider.provider_id)
        result = ReasoningEscalationRouter({provider.provider_id: provider}).execute(
            envelope, original, principal_id="resident:grace",
            authorize=lambda *_: False)
        self.assertEqual(result.status, EscalationStatus.DENIED)
        self.assertEqual(provider.calls, [])

    def test_authority_registry_failure_is_distinct_and_does_not_call_provider(self):
        original = request()
        provider = Provider()
        envelope = EscalationRequest.create(original, reason="capability_gap",
            target_provider_id=provider.provider_id)
        def unavailable(*_):
            raise GrantCheckUnavailable("registry unavailable")
        result = ReasoningEscalationRouter({provider.provider_id: provider}).execute(
            envelope, original, principal_id="resident:grace", authorize=unavailable)
        self.assertEqual(result.status, EscalationStatus.AUTHORITY_UNAVAILABLE)
        self.assertEqual(provider.calls, [])

    def test_correlation_and_budget_are_fail_closed(self):
        original = request()
        provider = Provider(PlanProposal("too large",
            (PlanStep("review", "Review", ("result cited",)),), 50))
        envelope = EscalationRequest.create(original, reason="low_confidence",
            target_provider_id=provider.provider_id, max_tokens=10)
        result = ReasoningEscalationRouter({provider.provider_id: provider}).execute(
            envelope, original, principal_id="resident:grace", authorize=lambda *_: True)
        self.assertEqual(result.status, EscalationStatus.INVALID_RESULT)
        altered = request()
        altered = ReasoningRequest(**{**altered.__dict__, "assignment_revision":"rev-5"})
        with self.assertRaisesRegex(ValueError, "correlation"):
            ReasoningEscalationRouter({provider.provider_id: provider}).execute(
                envelope, altered, principal_id="resident:grace", authorize=lambda *_: True)

    def test_escalation_token_ceiling_accepts_four_thousand_ninety_six_only(self):
        original = request()
        envelope = EscalationRequest.create(original, reason="capability_gap",
            target_provider_id="provider:synthetic-high", max_tokens=4096)
        self.assertEqual(envelope.max_tokens, 4096)
        with self.assertRaisesRegex(ValueError, "bounded contract"):
            EscalationRequest.create(original, reason="capability_gap",
                target_provider_id="provider:synthetic-high", max_tokens=4097)

    def test_unavailable_target_and_invalid_limits_do_not_fallback(self):
        original = request()
        with self.assertRaises(ValueError):
            EscalationRequest.create(original, reason="operator_override",
                target_provider_id="provider:missing")
        envelope = EscalationRequest.create(original, reason="task_complexity",
            target_provider_id="provider:missing")
        result = ReasoningEscalationRouter({}).execute(envelope, original,
            principal_id="resident:grace", authorize=lambda *_: True)
        self.assertEqual(result.status, EscalationStatus.UNAVAILABLE)
        self.assertEqual(result.detail_code, "provider_not_registered")


if __name__ == "__main__":
    unittest.main()
