# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resource_admission.py
# Component: RESOURCE-ADMISSION
# Revision: 1.0.0
# Changed: 2026-10-18 UTC | RV-RESOURCE-ADMISSION-001 | Add explicit-observation admission decisions for resident model slots.
# Purpose: Admit bounded requests only against fresh, task-suitable live slot capacity
# Execution Model: Pure deterministic planning over caller-supplied observations
# Observability: Typed decision and sanitized reason code; no prompt content retained
# Dependencies: Python standard library
# Authority: Selects a local resource only; grants no conversation, execution, or external escalation authority
# Contracts: docs/components/RESIDENT_REASONING.md
# Tests: tests/test_resource_admission.py
# =============================================================================
"""Fail-closed admission decisions for explicitly observed model slot capacity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class SlotObservation:
    """A fresh snapshot of one slot; free context is measured, never inferred."""

    resource_id: str
    capabilities: frozenset[str]
    supported_tasks: frozenset[str]
    max_context_tokens: int
    available_context_tokens: int
    active_requests: int
    max_concurrency: int
    observed_at: datetime
    status: str = "READY"
    resource_kind: str = "local"

    def __post_init__(self):
        if not isinstance(self.resource_id, str) or not self.resource_id:
            raise ValueError("resource identity is required")
        if not isinstance(self.capabilities, frozenset) or not self.capabilities:
            raise ValueError("registered capabilities are required")
        if not isinstance(self.supported_tasks, frozenset) or not self.supported_tasks:
            raise ValueError("task suitability must be explicit")
        for name in ("max_context_tokens", "max_concurrency"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (type(self.available_context_tokens) is not int
                or self.available_context_tokens < 0):
            raise ValueError("available context must be a nonnegative integer")
        if (type(self.active_requests) is not int or self.active_requests < 0
                or self.active_requests > self.max_concurrency):
            raise ValueError("active request count must be within slot concurrency")
        if self.available_context_tokens > self.max_context_tokens:
            raise ValueError("available context cannot exceed configured maximum")
        if not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None:
            raise ValueError("observation time must be timezone-aware")
        if self.status not in {"READY", "BUSY", "UNAVAILABLE", "UNKNOWN"}:
            raise ValueError("unsupported slot status")
        if self.resource_kind not in {"local", "external_advisory"}:
            raise ValueError("unsupported resource kind")


@dataclass(frozen=True)
class AdmissionRequest:
    """Bounded request requirements used for admission, not model prompting."""

    task: str
    required_capability: str
    input_tokens: int
    output_tokens: int
    vision_required: bool = False
    external_advisory: bool = False

    def __post_init__(self):
        if not isinstance(self.task, str) or not self.task:
            raise ValueError("task classification is required")
        if not isinstance(self.required_capability, str) or not self.required_capability:
            raise ValueError("required capability is required")
        for name in ("input_tokens", "output_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.input_tokens + self.output_tokens < 1:
            raise ValueError("a positive total token budget is required")
        if type(self.vision_required) is not bool or type(self.external_advisory) is not bool:
            raise ValueError("vision and advisory requirements must be booleans")


@dataclass(frozen=True)
class AdmissionDecision:
    """Result of planning one request against a single observation snapshot."""

    status: str
    resource_id: str | None
    reason: str
    queue_position: int | None = None


class ResourcePlanner:
    """Choose an eligible resource or return a truthful queue/defer outcome.

    Observations are sorted by caller order for deterministic policy. No configured
    context maximum, stale reading, or unrelated idle slot is treated as capacity.
    External advisory resources are considered only for explicitly advisory work.
    """

    def __init__(self, *, observation_ttl: timedelta = timedelta(seconds=15)):
        if not isinstance(observation_ttl, timedelta) or observation_ttl <= timedelta(0):
            raise ValueError("observation freshness window must be positive")
        self.observation_ttl = observation_ttl

    def plan(self, request: AdmissionRequest, observations, *, now: datetime,
             queue_depth: int = 0) -> AdmissionDecision:
        if not isinstance(request, AdmissionRequest):
            raise ValueError("a validated admission request is required")
        if not isinstance(now, datetime) or now.tzinfo is None:
            raise ValueError("planning time must be timezone-aware")
        if type(queue_depth) is not int or queue_depth < 0:
            raise ValueError("queue depth must be a nonnegative integer")
        slots = tuple(observations)
        if any(not isinstance(slot, SlotObservation) for slot in slots):
            raise ValueError("all slot observations must use the typed contract")

        stale_seen = False
        eligible_seen = False
        capacity_blocked = False
        needed = request.input_tokens + request.output_tokens
        expected_kind = "external_advisory" if request.external_advisory else "local"
        for slot in slots:
            if slot.resource_kind != expected_kind:
                continue
            if request.required_capability not in slot.capabilities:
                continue
            if request.task not in slot.supported_tasks:
                continue
            if request.vision_required and "vision" not in slot.capabilities:
                continue
            eligible_seen = True
            age = now - slot.observed_at
            if age < timedelta(0) or age > self.observation_ttl:
                stale_seen = True
                continue
            if slot.status != "READY":
                capacity_blocked = True
                continue
            if slot.active_requests >= slot.max_concurrency:
                capacity_blocked = True
                continue
            if slot.available_context_tokens < needed:
                capacity_blocked = True
                continue
            return AdmissionDecision("admit", slot.resource_id, "capacity_available")

        if eligible_seen and stale_seen and not capacity_blocked:
            return AdmissionDecision("defer", None, "observation_stale")
        if not eligible_seen:
            return AdmissionDecision("defer", None, "no_suitable_resource")
        return AdmissionDecision("queue", None, "capacity_unavailable", queue_depth + 1)


__all__ = ["AdmissionDecision", "AdmissionRequest", "ResourcePlanner", "SlotObservation"]
