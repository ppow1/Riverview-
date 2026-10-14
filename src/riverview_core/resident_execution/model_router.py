# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/model_router.py
# Component: RESIDENT-MODEL-ROUTER
# Revision: 1.0.6
# Purpose: Prefer 80B for substantive turns and persist bounded routing diagnostics
# Execution Model: Request-driven; persisted deferred turns are resumed by the conversation owner
# Observability: Selected stage and served model are returned as completion provenance
# Dependencies: LocalReasoningProvider; pinned AuthorityRegistry implementation binding
# Authority: Selects inference resources only; grants no conversation or execution authority
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: tests/test_resident_model_router.py
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-CAPABILITY-001 | Pin deferred resumption to its persisted capability and log readiness attempts
# =============================================================================
"""Small readiness-aware router for Grace's three existing model resources."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
import re
from time import monotonic

from ..local_reasoning_provider import LocalReasoningUnavailable


class ReasoningDeferred(RuntimeError):
    """The request requires a higher-capability model that is not ready."""

    def __init__(self, state, *, attempts=()):
        self.state = state
        self.attempts = tuple(attempts)
        super().__init__(state)


class GraceModelRouter:
    """Route substantive requests to 80B, with bounded interim/autonomic stages."""

    provider_id = "grace.readiness_router.v1"
    _AUTONOMIC = re.compile(
        r"^\s*(hi|hello|hey|good morning|good afternoon|good evening|"
        r"are you there|status\??|thanks|thank you)[.!?\s]*$", re.IGNORECASE)
    _INTERIM = re.compile(
        r"^\s*(?:define\s+.{1,100}|what does\s+.{1,100}\s+mean\??|"
        r"what is\s+.{1,100}|who is\s+.{1,100}|where is\s+.{1,100}|"
        r"when is\s+.{1,100}|how many\s+.{1,100})[.!?\s]*$", re.IGNORECASE)
    TIMEOUTS = {"autonomic": 35, "interim_30b": 15, "reasoning": 60}
    _SAFE_ERRORS = frozenset({"endpoint_busy", "endpoint_timeout", "endpoint_unavailable",
        "endpoint_loading", "endpoint_http_503", "endpoint_http_502", "endpoint_http_504",
        "endpoint_http_500", "endpoint_http_400", "endpoint_http_404",
        "endpoint_http_408", "endpoint_http_413", "endpoint_http_422",
        "endpoint_http_429", "response_incomplete", "response_contract_invalid",
        "response_too_large", "request_contract_invalid", "endpoint_status_invalid",
        "all_models_unavailable", "required_capability_not_satisfied",
        "readiness_timeout", "health_status_invalid", "model_list_invalid",
        "configured_model_missing", "provider_slot_occupied",
        "endpoint_http_503", "endpoint_http_502", "endpoint_http_504"})

    def __init__(self, *, autonomic, vision, reasoning):
        self.providers = {"autonomic": autonomic, "vision": vision,
                          "reasoning": reasoning}
        if any(provider is None for provider in self.providers.values()):
            raise ValueError("all three Grace reasoning providers must be configured")
        self.model = "grace-readiness-router"
        manifest = {stage: {"model": provider.model,
                            "model_sha256": provider.model_sha256}
                    for stage, provider in self.providers.items()}
        serialized = json.dumps({"router_revision": "1.0.4", "models": manifest},
                                sort_keys=True, separators=(",", ":"))
        self.model_sha256 = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def requires_reasoning(cls, messages):
        latest_user = next((message for message in reversed(messages)
                            if message.get("role") == "user"), {})
        text = str(latest_user.get("content", ""))
        # Only a small explicit low-risk class may use the provisional 30B.
        # Every other non-autonomic request is substantive and defaults to 80B.
        return not cls._AUTONOMIC.fullmatch(text) and not (
            len(text.encode("utf-8")) <= 180 and cls._INTERIM.fullmatch(text))

    def readiness(self):
        return {stage: provider.readiness() for stage, provider in self.providers.items()}

    def supports_capability(self, capability):
        """Report the one bounded reasoning capability this router can satisfy."""
        return capability == "grace.reasoning.80b" and self.providers.get("reasoning") is not None

    def select(self, messages, *, required_capability=None):
        if required_capability is not None:
            if required_capability != "grace.reasoning.80b":
                raise ReasoningDeferred("UNSUPPORTED_CAPABILITY")
            provider = self.providers["reasoning"]
            started_at = datetime.now(UTC)
            started = monotonic()
            state = provider.readiness()
            if state.state != "READY":
                detail = getattr(state, "detail_code", "endpoint_unavailable")
                error_code = detail if detail in self._SAFE_ERRORS else "endpoint_unavailable"
                if isinstance(detail, str) and re.fullmatch(r"endpoint_http_[45][0-9]{2}", detail):
                    error_code = detail
                attempt = self._attempt("reasoning", provider, started_at, started,
                    outcome="deferred", error_code=error_code)
                raise ReasoningDeferred(state.state, attempts=(attempt,))
            return "reasoning", provider
        states = self.readiness()
        latest_user = next((message for message in reversed(messages)
                            if message.get("role") == "user"), {})
        text = str(latest_user.get("content", ""))
        if self._AUTONOMIC.fullmatch(text) and states["autonomic"].state == "READY":
            return "autonomic", self.providers["autonomic"]
        if self.requires_reasoning(messages):
            state = states["reasoning"]
            if state.state != "READY":
                raise ReasoningDeferred(state.state)
            return "reasoning", self.providers["reasoning"]
        # A narrow simple fact/definition class may receive a provisional 30B turn.
        if states["vision"].state == "READY":
            return "interim_30b", self.providers["vision"]
        raise ReasoningDeferred(states["vision"].state)

    def complete_chat(self, messages, *, max_tokens, expected_revision,
                      timeout_seconds=120, required_capability=None):
        if expected_revision != self.model_sha256:
            raise LocalReasoningUnavailable("router_binding_mismatch")
        try:
            stage, provider = self.select(messages,
                required_capability=required_capability)
        except ReasoningDeferred:
            raise
        system = {
            "autonomic": "You are Grace's autonomic layer. Give only a brief status or acknowledgment. Do not answer substantive or factual questions; say that the request is being deferred.",
            "interim_30b": "You are Grace's provisional interim reasoning layer. Answer only simple questions grounded in supplied evidence. If evidence is absent or uncertainty is material, say you do not know and defer substantive reasoning to Grace's 80B layer.",
            "reasoning": "You are Grace's substantive reasoning layer. Preserve uncertainty, distinguish supplied facts from inference, and do not claim actions or authority that were not performed.",
        }[stage]
        routed = [{"role": "system", "content": system}, *messages]
        attempts = []
        try:
            started_at = datetime.now(UTC)
            started = monotonic()
            completion = provider.complete_chat(routed, max_tokens=max_tokens,
                expected_revision=provider.model_sha256,
                timeout_seconds=min(timeout_seconds, self.TIMEOUTS[stage]))
            attempts.append(self._attempt(stage, provider, started_at, started,
                                          outcome="succeeded"))
        except LocalReasoningUnavailable as exc:
            attempts.append(self._attempt(stage, provider, started_at, started,
                outcome="failed", error_code=self._safe_error(exc)))
            if stage == "reasoning":
                code = getattr(exc, "code", "endpoint_unavailable")
                state = "MODEL_BUSY" if code == "endpoint_busy" else (
                    "MODEL_BUSY" if code == "endpoint_http_503" else "UNAVAILABLE")
                raise ReasoningDeferred(state, attempts=attempts) from None
            if stage == "interim_30b":
                attempts[-1]["fallback_reason"] = "interim_30b_provider_failure"
                autonomic = self.providers["autonomic"]
                if autonomic.readiness().state == "READY":
                    routed[0] = {"role": "system", "content": (
                        "You are Grace's autonomic layer. Give only a brief status or "
                        "acknowledgment. Do not answer substantive or factual questions; "
                        "say that the request is being deferred.")}
                    fallback_started_at = datetime.now(UTC)
                    fallback_started = monotonic()
                    try:
                        completion = autonomic.complete_chat(routed,
                        max_tokens=max_tokens, expected_revision=autonomic.model_sha256,
                        timeout_seconds=self.TIMEOUTS["autonomic"])
                        attempts.append(self._attempt("autonomic", autonomic,
                            fallback_started_at, fallback_started, outcome="succeeded",
                            fallback_reason="interim_30b_provider_failure"))
                    except LocalReasoningUnavailable as fallback_exc:
                        attempts.append(self._attempt("autonomic", autonomic,
                            fallback_started_at, fallback_started, outcome="failed",
                            error_code=self._safe_error(fallback_exc),
                            fallback_reason="interim_30b_provider_failure"))
                        raise LocalReasoningUnavailable("all_models_unavailable",
                            attempts=attempts) from None
                    stage = "autonomic"
                else:
                    raise ReasoningDeferred("UNAVAILABLE", attempts=attempts) from None
            else:
                raise LocalReasoningUnavailable(self._safe_error(exc),
                                                attempts=attempts) from None
        final_provider = getattr(provider, "provider_id", stage) if stage != "autonomic" else getattr(self.providers["autonomic"], "provider_id", "autonomic")
        if attempts and stage == "autonomic" and len(attempts) > 1:
            final_provider = getattr(self.providers["autonomic"], "provider_id", "autonomic")
        attempts = [dict(item, final_served_provider=final_provider,
                         final_served_model=completion.served_model,
                         fallback_reason=item.get("fallback_reason")) for item in attempts]
        if required_capability is not None and (
                stage != "reasoning" or completion.provisional):
            raise LocalReasoningUnavailable("required_capability_not_satisfied",
                                            attempts=attempts)
        return replace(completion, reasoning_stage=stage,
                       provisional=(stage != "reasoning"), provider_attempts=tuple(attempts))

    @classmethod
    def _safe_error(cls, exc):
        code = getattr(exc, "code", "")
        return code if code in cls._SAFE_ERRORS else "provider_error"

    @staticmethod
    def _attempt(stage, provider, started_at, started, *, outcome,
                 error_code=None, fallback_reason=None):
        ended_at = datetime.now(UTC)
        return {"selected_provider": getattr(provider, "provider_id", stage),
            "selected_model": getattr(provider, "model", stage),
            "reasoning_stage": stage, "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "elapsed_ms": round(max(0.0, monotonic() - started) * 1000, 3),
            "outcome": outcome, "error_code": error_code,
            "fallback_reason": fallback_reason}
