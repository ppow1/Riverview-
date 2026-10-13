# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/model_router.py
# Component: RESIDENT-MODEL-ROUTER
# Revision: 1.0.3
# Purpose: Select Grace's reasoning stage by request complexity and readiness
# Execution Model: Request-driven; persisted deferred turns are resumed by the conversation owner
# Observability: Selected stage and served model are returned as completion provenance
# Dependencies: LocalReasoningProvider; pinned AuthorityRegistry implementation binding
# Authority: Selects inference resources only; grants no conversation or execution authority
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: tests/test_resident_model_router.py
# =============================================================================
"""Small readiness-aware router for Grace's three existing model resources."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import re

from ..local_reasoning_provider import LocalReasoningUnavailable


class ReasoningDeferred(RuntimeError):
    """The request requires a higher-capability model that is not ready."""


class GraceModelRouter:
    """Route substantive requests to 80B, simple turns to 30B/0.6B, fail closed."""

    provider_id = "grace.readiness_router.v1"
    _COMPLEX = re.compile(
        r"\b(analy[sz](?:e|is)?|plan|design|compare|evaluate|recommend|troubleshoot|"
        r"engineering|investigat|reason|trade[- ]?off|decide|strategy|review|audit|"
        r"assess|research|forecast|estimate|debug|repair|implement|build|create|"
        r"work ?order|why|how to|should|could|would|impact|risk|security|"
        r"architecture|requirements)\b", re.IGNORECASE)
    _AUTONOMIC = re.compile(
        r"^\s*(hi|hello|hey|good morning|good afternoon|good evening|"
        r"are you there|status\??|thanks|thank you)[.!?\s]*$", re.IGNORECASE)

    def __init__(self, *, autonomic, vision, reasoning):
        self.providers = {"autonomic": autonomic, "vision": vision,
                          "reasoning": reasoning}
        if any(provider is None for provider in self.providers.values()):
            raise ValueError("all three Grace reasoning providers must be configured")
        self.model = "grace-readiness-router"
        manifest = {stage: {"model": provider.model,
                            "model_sha256": provider.model_sha256}
                    for stage, provider in self.providers.items()}
        serialized = json.dumps({"router_revision": "1.0.3", "models": manifest},
                                sort_keys=True, separators=(",", ":"))
        self.model_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def requires_reasoning(cls, messages):
        latest_user = next((message for message in reversed(messages)
                            if message.get("role") == "user"), {})
        text = str(latest_user.get("content", ""))
        return len(text.encode("utf-8")) > 700 or bool(cls._COMPLEX.search(text))

    def readiness(self):
        return {stage: provider.readiness() for stage, provider in self.providers.items()}

    def select(self, messages):
        states = self.readiness()
        if self.requires_reasoning(messages):
            state = states["reasoning"]
            if state.state != "READY":
                raise ReasoningDeferred(state.state)
            return "reasoning", self.providers["reasoning"]
        # 30B may provide a short provisional turn; the small CPU model is the
        # autonomic fallback. Both prompts explicitly require evidence and candor.
        if states["vision"].state == "READY":
            return "interim_30b", self.providers["vision"]
        latest_user = next((message for message in reversed(messages)
                            if message.get("role") == "user"), {})
        text = str(latest_user.get("content", ""))
        if self._AUTONOMIC.fullmatch(text) and states["autonomic"].state == "READY":
            return "autonomic", self.providers["autonomic"]
        if states["reasoning"].state == "READY":
            return "reasoning", self.providers["reasoning"]
        if not self.requires_reasoning(messages):
            raise ReasoningDeferred(states["reasoning"].state)
        raise LocalReasoningUnavailable("all_models_unavailable")

    def complete_chat(self, messages, *, max_tokens, expected_revision,
                      timeout_seconds=120):
        if expected_revision != self.model_sha256:
            raise LocalReasoningUnavailable("router_binding_mismatch")
        stage, provider = self.select(messages)
        system = {
            "autonomic": "You are Grace's autonomic layer. Give only a brief status or acknowledgment. Do not answer substantive or factual questions; say that the request is being deferred.",
            "interim_30b": "You are Grace's provisional interim reasoning layer. Answer only simple questions grounded in supplied evidence. If evidence is absent or uncertainty is material, say you do not know and defer substantive reasoning to Grace's 80B layer.",
            "reasoning": "You are Grace's substantive reasoning layer. Preserve uncertainty, distinguish supplied facts from inference, and do not claim actions or authority that were not performed.",
        }[stage]
        routed = [{"role": "system", "content": system}, *messages]
        try:
            completion = provider.complete_chat(routed, max_tokens=max_tokens,
                expected_revision=provider.model_sha256, timeout_seconds=timeout_seconds)
        except LocalReasoningUnavailable as exc:
            if stage == "reasoning":
                code = getattr(exc, "code", "endpoint_unavailable")
                state = "MODEL_BUSY" if code == "endpoint_busy" else (
                    "MODEL_BUSY" if code == "endpoint_http_503" else "UNAVAILABLE")
                raise ReasoningDeferred(state) from None
            if stage == "interim_30b":
                autonomic = self.providers["autonomic"]
                if autonomic.readiness().state == "READY":
                    routed[0] = {"role": "system", "content": (
                        "You are Grace's autonomic layer. Give only a brief status or "
                        "acknowledgment. Do not answer substantive or factual questions; "
                        "say that the request is being deferred.")}
                    completion = autonomic.complete_chat(routed,
                        max_tokens=max_tokens, expected_revision=autonomic.model_sha256,
                        timeout_seconds=timeout_seconds)
                    stage = "autonomic"
                else:
                    raise LocalReasoningUnavailable("all_models_unavailable") from None
            else:
                raise
        return replace(completion, reasoning_stage=stage,
                       provisional=(stage != "reasoning"))
