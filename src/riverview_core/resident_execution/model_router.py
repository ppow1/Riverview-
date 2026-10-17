# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/model_router.py
# Component: RESIDENT-MODEL-ROUTER
# Revision: 1.2.3
# Changed: 2026-10-17 UTC | RV-GRACE-PERSISTENT-AUTONOMY-001 | Require tool-backed current-status answers.
# Purpose: Prefer 80B for substantive turns, bound context and autonomic acknowledgments, and persist diagnostics
# Execution Model: Request-driven; persisted deferred turns are resumed by the conversation owner
# Observability: Selected stage and served model are returned as completion provenance
# Dependencies: LocalReasoningProvider; pinned AuthorityRegistry implementation binding
# Authority: Selects inference resources only; grants no conversation or execution authority
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# Tests: tests/test_resident_model_router.py
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-CAPABILITY-001 | Pin deferred resumption to its persisted capability and log readiness attempts
# Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Route persistent typed proposals through the authorized 80B stage
# Changed: 2026-10-15 UTC | RV-GRACE-DEMO-BASE-INTEGRATION | Reconcile router contract with integrated deferred-budget release
# Changed: 2026-10-14 UTC | RV-GRACE-80B-COMPLETION-BUDGET-001 | Include sanitized completion-limit diagnostics for non-stop provider outcomes
# Changed: 2026-10-15 UTC | RV-GRACE-SINGLE-RESIDENT-IDENTITY-001 | Identify each model stage as a capability of the one Grace resident
# Changed: 2026-10-15 UTC | RV-GRACE-CHAT-CONTEXT-BOUND-001 | Preserve required system context and latest user turn within provider message limits
# Changed: 2026-10-15 UTC | RV-GRACE-AUTONOMIC-CONTEXT-BOUND-001 | Keep 0.6B acknowledgment prompts minimal while retaining full institutional context for substantive stages
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Route validated text deltas through the same capability and fallback policy
# Changed: 2026-10-17 UTC | RV-GRACE-COMMS5-INTERNAL-TOOLS-001 | Execute one bounded internal read tool and consume its structured result
# =============================================================================
"""Small readiness-aware router for Grace's three existing model resources."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
import re
from time import monotonic

from ..local_reasoning_provider import LocalReasoningProvider, LocalReasoningUnavailable


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
    TIMEOUTS = {"autonomic": 60, "interim_30b": 15, "reasoning": 60}
    TOKEN_LIMITS = {"autonomic": 32}
    OPERATIONAL_CONTEXT_PREFIX = "Read-only Riverview operational context follows as JSON data."
    # LocalReasoningProvider accepts at most 18 messages. One is reserved for the
    # stage instruction added below; preserve all supplied system context and fit
    # the newest conversation messages into the remaining slots.
    PROVIDER_MAX_MESSAGES = LocalReasoningProvider.MAX_CHAT_MESSAGES
    STAGE_INSTRUCTIONS = {
        "autonomic": (
            "You are Grace, Riverview's Director of Operations. This is your 0.6B "
            "autonomic capability, not a separate resident, office, or agent. "
            "Give only one brief "
            "acknowledgment of at most 20 words. Do not answer substantive questions, "
            "claim an action, or imply this role grants authority."),
        "interim_30b": (
            "You are Grace, Riverview's continuing resident and Director of Operations. "
            "This response uses your 30B vision/interim capability; it is not a separate "
            "resident, office, or agent. Answer only simple questions grounded in supplied "
            "evidence. If evidence is absent or uncertainty is material, say you do not know "
            "and defer substantive reasoning to your 80B reasoning capability."),
        "reasoning": (
            "You are Grace, Riverview's continuing resident and Director of Operations. "
            "This response uses your 80B reasoning capability; it is not a separate "
            "resident, office, or agent. Preserve uncertainty, distinguish supplied facts "
            "from inference, and do not claim actions or authority that were not performed."),
    }
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

    def __init__(self, *, autonomic, vision, reasoning, internal_tools=None):
        self.providers = {"autonomic": autonomic, "vision": vision,
                          "reasoning": reasoning}
        self.internal_tools = internal_tools
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

    def propose(self, request):
        """Produce a typed Engineering proposal only through the bound 80B provider.

        ResidentReasoner binds its request to this router revision. The underlying
        adapter still verifies its own model digest, so both identities are checked
        and the returned proposal records the actual served model.
        """
        if request.implementation_revision != self.model_sha256:
            return None
        provider = self.providers["reasoning"]
        readiness = provider.readiness()
        if readiness.state != "READY":
            detail = getattr(readiness, "detail_code", "endpoint_unavailable")
            code = detail if detail in self._SAFE_ERRORS else "endpoint_unavailable"
            raise LocalReasoningUnavailable(code)
        proposal = provider.propose(replace(
            request, implementation_revision=provider.model_sha256))
        if proposal is None:
            return None
        if (proposal.provider_id != provider.provider_id
                or proposal.served_model != provider.model
                or proposal.model_revision != provider.model_sha256
                or proposal.reasoning_stage != "reasoning"):
            return None
        return proposal

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
        system = self.STAGE_INSTRUCTIONS[stage]
        stage_max_tokens = self._stage_token_limit(stage, max_tokens)
        provider_context = self._bound_provider_context(messages, stage=stage)
        if stage == "reasoning" and self.internal_tools is not None:
            while len(provider_context) > 13:
                newest_user = max((i for i, item in enumerate(provider_context)
                                   if item.get("role") == "user"), default=-1)
                removable = next((i for i, item in enumerate(provider_context)
                                  if item.get("role") != "system" and i != newest_user), None)
                if removable is None:
                    break
                provider_context.pop(removable)
        routed = [{"role": "system", "content": system},
                  *provider_context]
        if stage == "reasoning" and self.internal_tools is not None:
            catalog = json.dumps(self.internal_tools.catalog(), sort_keys=True,
                                 separators=(",", ":"), ensure_ascii=False)
            routed[0]["content"] += "\n\n" + (
                "For any user request that asks for current Riverview status, records, "
                "inventory, or recent operations covered by an available tool, you MUST "
                "call the matching tool before answering. Do not answer from memory or "
                "from operational context when a tool covers the request. Emit exactly "
                "<rv-tool-call>{\"name\":\"...\",\"arguments\":{...}}</rv-tool-call> "
                "as your entire first response. The tool result will be supplied for you "
                "to consume in a follow-up. Available internal tools: " + catalog + ". "
                "Do not invent tool names or arguments, and do not provide a status answer "
                "until the matching tool result is available.")
        attempts = []
        try:
            started_at = datetime.now(UTC)
            started = monotonic()
            completion = provider.complete_chat(routed, max_tokens=stage_max_tokens,
                expected_revision=provider.model_sha256,
                timeout_seconds=min(timeout_seconds, self.TIMEOUTS[stage]))
            attempts.append(self._attempt(stage, provider, started_at, started,
                outcome="succeeded", finish_reason=completion.finish_reason,
                completion_tokens=completion.completion_tokens,
                completion_token_limit=stage_max_tokens))
        except LocalReasoningUnavailable as exc:
            attempts.append(self._attempt(stage, provider, started_at, started,
                outcome="failed", error_code=self._safe_error(exc),
                finish_reason=getattr(exc, "finish_reason", None),
                completion_tokens=getattr(exc, "completion_tokens", None),
                completion_token_limit=getattr(exc, "completion_token_limit", None)))
            if stage == "reasoning":
                code = getattr(exc, "code", "endpoint_unavailable")
                state = "MODEL_BUSY" if code == "endpoint_busy" else (
                    "MODEL_BUSY" if code == "endpoint_http_503" else "UNAVAILABLE")
                raise ReasoningDeferred(state, attempts=attempts) from None
            if stage == "interim_30b":
                attempts[-1]["fallback_reason"] = "interim_30b_provider_failure"
                autonomic = self.providers["autonomic"]
                if autonomic.readiness().state == "READY":
                    routed[0] = {"role": "system", "content": self.STAGE_INSTRUCTIONS["autonomic"]}
                    fallback_max_tokens = self._stage_token_limit("autonomic", max_tokens)
                    fallback_started_at = datetime.now(UTC)
                    fallback_started = monotonic()
                    try:
                        completion = autonomic.complete_chat(routed,
                        max_tokens=fallback_max_tokens, expected_revision=autonomic.model_sha256,
                        timeout_seconds=self.TIMEOUTS["autonomic"])
                        attempts.append(self._attempt("autonomic", autonomic,
                            fallback_started_at, fallback_started, outcome="succeeded",
                            fallback_reason="interim_30b_provider_failure",
                            completion_token_limit=fallback_max_tokens,
                            completion_tokens=completion.completion_tokens,
                            finish_reason=completion.finish_reason))
                    except LocalReasoningUnavailable as fallback_exc:
                        attempts.append(self._attempt("autonomic", autonomic,
                            fallback_started_at, fallback_started, outcome="failed",
                            error_code=self._safe_error(fallback_exc),
                            fallback_reason="interim_30b_provider_failure",
                            finish_reason=getattr(fallback_exc, "finish_reason", None),
                            completion_tokens=getattr(fallback_exc, "completion_tokens", None),
                            completion_token_limit=getattr(fallback_exc, "completion_token_limit",
                                                           fallback_max_tokens)))
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
        tool_results = ()
        if stage == "reasoning" and self.internal_tools is not None:
            call = self._internal_tool_call(completion.content)
            if call is not None:
                tool_name, arguments = call
                tool_result = self.internal_tools.call(tool_name, arguments)
                tool_results = (tool_result,)
                followup = [*routed,
                    {"role": "assistant", "content": completion.content},
                    {"role": "user", "content": "Internal tool result (JSON data): " +
                     json.dumps(tool_result, sort_keys=True,
                                separators=(",", ":"), ensure_ascii=False)},
                    {"role": "system", "content": (
                        "Use the structured tool result as evidence for the user's question. "
                        "Describe errors clearly. Do not claim a successful action. "
                        "Do not request or emit another tool call.")}]
                final = provider.complete_chat(followup,
                    max_tokens=self._stage_token_limit(stage, max_tokens),
                    expected_revision=provider.model_sha256,
                    timeout_seconds=self.TIMEOUTS[stage])
                if self._internal_tool_call(final.content) is not None:
                    final = replace(final, content=(
                        "I could not complete the requested internal lookup because the "
                        "response requested an additional tool call."))
                completion = final
        return replace(completion, reasoning_stage=stage,
                       provisional=(stage != "reasoning"), provider_attempts=tuple(attempts),
                       internal_tool_results=tool_results)

    @staticmethod
    def _internal_tool_call(content):
        """Accept exactly one explicit, bounded model-originated tool directive."""
        match = re.fullmatch(r"\s*<rv-tool-call>(\{.{1,2048}\})</rv-tool-call>\s*",
                             content or "", flags=re.DOTALL)
        if match is None:
            return None
        try:
            value = json.loads(match.group(1))
        except (TypeError, json.JSONDecodeError):
            return None
        if (not isinstance(value, dict) or set(value) != {"name", "arguments"}
                or not isinstance(value["name"], str)
                or not isinstance(value["arguments"], dict)):
            return None
        return value["name"], value["arguments"]

    def stream_chat(self, messages, *, max_tokens, expected_revision, on_delta,
                    on_reset=lambda: None, timeout_seconds=120,
                    required_capability=None, selected_route=None):
        """Stream one routed answer while preserving the non-streaming route policy."""
        if expected_revision != self.model_sha256 or not callable(on_delta) or not callable(on_reset):
            raise LocalReasoningUnavailable("router_binding_mismatch")
        stage, provider = (selected_route if selected_route is not None else
                           self.select(messages, required_capability=required_capability))
        provider_key = "vision" if stage == "interim_30b" else stage
        if (provider_key not in self.providers or self.providers[provider_key] is not provider
                or (required_capability is not None and stage != "reasoning")):
            raise LocalReasoningUnavailable("required_capability_not_satisfied")
        stage_limit = self._stage_token_limit(stage, max_tokens)
        routed = [{"role": "system", "content": self.STAGE_INSTRUCTIONS[stage]},
                  *self._bound_provider_context(messages, stage=stage)]
        attempts = []
        emitted = False

        def emit(text):
            nonlocal emitted
            emitted = True
            on_delta(text)

        def invoke(selected_stage, selected_provider, selected_messages, selected_limit,
                   *, fallback_reason=None):
            started_at = datetime.now(UTC)
            started = monotonic()
            try:
                result = selected_provider.stream_chat(selected_messages,
                    max_tokens=selected_limit,
                    expected_revision=selected_provider.model_sha256,
                    on_delta=emit,
                    timeout_seconds=min(timeout_seconds, self.TIMEOUTS[selected_stage]))
                attempts.append(self._attempt(selected_stage, selected_provider,
                    started_at, started, outcome="succeeded", fallback_reason=fallback_reason,
                    finish_reason=result.finish_reason, completion_tokens=result.completion_tokens,
                    completion_token_limit=selected_limit))
                return result
            except LocalReasoningUnavailable as exc:
                attempts.append(self._attempt(selected_stage, selected_provider,
                    started_at, started, outcome="failed", fallback_reason=fallback_reason,
                    error_code=self._safe_error(exc),
                    finish_reason=exc.finish_reason,
                    completion_tokens=exc.completion_tokens,
                    completion_token_limit=exc.completion_token_limit or selected_limit))
                raise

        try:
            completion = invoke(stage, provider, routed, stage_limit)
        except LocalReasoningUnavailable as exc:
            if stage == "reasoning":
                raise ReasoningDeferred(
                    "MODEL_BUSY" if self._safe_error(exc) in {"endpoint_busy", "endpoint_http_503"}
                    else "UNAVAILABLE", attempts=attempts) from None
            if stage != "interim_30b":
                raise LocalReasoningUnavailable(self._safe_error(exc), attempts=attempts) from None
            attempts[-1]["fallback_reason"] = "interim_30b_provider_failure"
            fallback = self.providers["autonomic"]
            if fallback.readiness().state != "READY":
                raise ReasoningDeferred("UNAVAILABLE", attempts=attempts) from None
            if emitted:
                on_reset()
                emitted = False
            routed[0] = {"role": "system", "content": self.STAGE_INSTRUCTIONS["autonomic"]}
            fallback_messages = self._bound_provider_context(messages, stage="autonomic")
            routed = [routed[0], *fallback_messages]
            try:
                completion = invoke("autonomic", fallback, routed,
                    self._stage_token_limit("autonomic", max_tokens),
                    fallback_reason="interim_30b_provider_failure")
                stage = "autonomic"
            except LocalReasoningUnavailable as fallback_exc:
                raise LocalReasoningUnavailable("all_models_unavailable",
                    attempts=attempts) from None
        if required_capability is not None and (stage != "reasoning" or completion.provisional):
            raise LocalReasoningUnavailable("required_capability_not_satisfied", attempts=attempts)
        final_provider = getattr(self.providers["vision" if stage == "interim_30b" else stage],
                                 "provider_id", stage)
        attempts = [dict(item, final_served_provider=final_provider,
                         final_served_model=completion.served_model) for item in attempts]
        return replace(completion, reasoning_stage=stage,
                       provisional=(stage != "reasoning"),
                       provider_id=final_provider, provider_attempts=tuple(attempts))

    @classmethod
    def _stage_token_limit(cls, stage, requested):
        """Keep a model stage's generation bound below the caller's maximum."""
        limit = cls.TOKEN_LIMITS.get(stage)
        return min(requested, limit) if type(requested) is int and limit else requested

    @classmethod
    def _bound_provider_context(cls, messages, *, stage=None):
        """Bound history while preserving system context and the latest user turn.

        The router adds one stage-specific system message. Keep all caller-provided
        system messages and retain the newest chronological conversational messages
        that fit the provider's 18-message contract. This makes old history a
        bounded context window; it never alters durable conversation events.
        """
        if (not isinstance(messages, list)
                or any(not isinstance(message, dict)
                       or set(message) != {"role", "content"}
                       or message.get("role") not in {"system", "user", "assistant"}
                       or not isinstance(message.get("content"), str)
                       for message in messages)):
            raise LocalReasoningUnavailable("request_contract_invalid")
        system_messages = [message for message in messages
                           if message["role"] == "system"]
        conversation_messages = [message for message in messages
                                 if message["role"] in {"user", "assistant"}]
        if stage == "autonomic":
            # Acknowledgments need only the concise, identity-bearing stage
            # instruction and current user turn, not the large canonical role
            # block, operational snapshot, or old conversation.
            # Both remain durably stored and are available to substantive stages.
            system_messages = []
            conversation_messages = [message for message in conversation_messages
                if message["role"] == "user"][-1:]
        retained_system_ids = {id(message) for message in system_messages}
        context_limit = cls.PROVIDER_MAX_MESSAGES - 1 - len(system_messages)
        if (context_limit < 1 or not conversation_messages
                or conversation_messages[-1]["role"] != "user"):
            raise LocalReasoningUnavailable("request_contract_invalid")
        if len(conversation_messages) > context_limit:
            conversation_messages = conversation_messages[-context_limit:]
        # Keep the original order of system and conversational context. System
        # observations may occur after older messages, so select by identity from
        # the original list rather than moving them to the front.
        retained_conversation_ids = {id(message) for message in conversation_messages}
        return [message for message in messages
                if id(message) in retained_system_ids
                or id(message) in retained_conversation_ids]

    @classmethod
    def _safe_error(cls, exc):
        code = getattr(exc, "code", "")
        return code if code in cls._SAFE_ERRORS else "provider_error"

    @staticmethod
    def _attempt(stage, provider, started_at, started, *, outcome,
                 error_code=None, fallback_reason=None, finish_reason=None,
                 completion_tokens=None, completion_token_limit=None):
        ended_at = datetime.now(UTC)
        return {"selected_provider": getattr(provider, "provider_id", stage),
            "selected_model": getattr(provider, "model", stage),
            "reasoning_stage": stage, "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "elapsed_ms": round(max(0.0, monotonic() - started) * 1000, 3),
            "outcome": outcome, "error_code": error_code,
            "fallback_reason": fallback_reason,
            "finish_reason": finish_reason,
            "completion_tokens": completion_tokens,
            "completion_token_limit": completion_token_limit}
