"""Single-call GPT-6 Luna transport over Grace's existing durable exchange."""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
import urllib.error

PROVIDER_ID = "gpt-6-luna"
MODEL_ID = "gpt-6-luna"
PROVIDER_PRINCIPAL = "service:provider-gpt-6-luna"
BASELINE_TOTAL = 0.04104010
TOTAL_CREDIT = 5.0
ADDITIONAL_LIMIT = round(TOTAL_CREDIT - BASELINE_TOTAL, 8)
RESERVED_CALL_COST = 0.01
MAX_OUTPUT_TOKENS = 512
LOG = logging.getLogger("riverview.grace_execution")


def _response_ids(row):
    """Normalize database UUID objects at the JSON and string-key boundary."""
    return str(row["request_id"]), str(row["correlation_id"])


def _safe_failure_detail(exc):
    """Keep a short exception diagnosis while stripping credentials and controls."""
    detail = str(exc)
    detail = re.sub(r"(?i)bearer\s+[^\s,;]+", "Bearer [REDACTED]", detail)
    detail = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[REDACTED]", detail)
    detail = re.sub(r"(?i)(api[_ -]?key|authorization|password|token)\s*[:=]\s*[^\s,;]+",
                    r"\1=[REDACTED]", detail)
    detail = re.sub(r"[\r\n\t]+", " ", detail)
    detail = re.sub(r"[^A-Za-z0-9 .,:()'/_=+\-\[\]]", "?", detail)
    return f"{type(exc).__name__}: {detail[:200]}"


def _api_key():
    path = os.path.join(os.environ.get("CREDENTIALS_DIRECTORY", ""), "luna-openai-env")
    if not os.path.isabs(path) or not os.path.isfile(path):
        raise RuntimeError("luna_credential_unavailable")
    for line in open(path, encoding="utf-8"):
        key, sep, value = line.strip().partition("=")
        if sep and key == "OPENAI_API_KEY" and value:
            return value.strip().strip("\"'")
    raise RuntimeError("luna_credential_unavailable")


def process_one(exchange):
    """Claim and answer at most one eligible escalation; no retries."""
    eligible = exchange.eligible_requests(PROVIDER_ID,
        principal_id=PROVIDER_PRINCIPAL, limit=1)
    if not eligible:
        return None
    row = eligible[0]
    if row["delivery_state"] == "awaiting_delivery":
        delivery = exchange.begin_delivery(row["request_id"], PROVIDER_ID,
            owner_id=PROVIDER_PRINCIPAL, lease_seconds=20)
        if delivery is None:
            return {"status": "DELIVERY_CLAIM_UNAVAILABLE"}
        exchange.mark_delivered(row["request_id"], row["correlation_id"], PROVIDER_ID,
            owner_id=PROVIDER_PRINCIPAL, delivery_token=delivery.claim_token,
            fence=delivery.fence)
    claim = exchange.claim(row["request_id"], row["correlation_id"],
        provider_id=PROVIDER_ID, principal_id=PROVIDER_PRINCIPAL, lease_seconds=120)
    if claim is None:
        return None
    if claim.duplicate:
        if exchange.provider_attempt_is_settled(row["request_id"]):
            exchange.fail_provider_response_submission(row["request_id"], row["correlation_id"],
                provider_id=PROVIDER_ID, principal_id=PROVIDER_PRINCIPAL,
                claim_token=claim.claim_token, fence=claim.fence)
            return {"status": "PAID_RESPONSE_SUBMISSION_FENCED"}
        return None
    if not exchange.begin_provider_attempt(row["request_id"], row["correlation_id"],
            principal_id=PROVIDER_PRINCIPAL, reserved_cost=RESERVED_CALL_COST,
            additional_limit=ADDITIONAL_LIMIT, baseline_total=BASELINE_TOTAL,
            total_credit=TOTAL_CREDIT):
        return {"status": "BUDGET_OR_REPEAT_BLOCKED"}
    payload = row["request_payload"]
    request_type = payload.get("request_type", "objective_reasoning")
    max_output_tokens = payload.get("max_tokens", MAX_OUTPUT_TOKENS)
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
        exchange.finish_provider_attempt(row["request_id"], row["correlation_id"],
            status="failed", failure_type="request_token_budget_invalid")
        return {"status": "REQUEST_TOKEN_BUDGET_INVALID"}
    instructions = (
        "Diagnose this CME-reported Grace stall from the supplied evidence. Return one JSON object "
        "with schema rv.grace.cme-recovery-advice.v1, assessment (short string), recovery_action "
        "(REWORK_PROPOSED or STEWARD_AUTHORIZATION_REQUIRED), rationale (short string), "
        "correction_instruction (string or null), and criteria_to_address (array of exact supplied criteria). "
        "Recommend only a bounded same-assignment correction supported by the evidence. Never claim "
        "that this response grants authority, approves work, or bypasses independent verification.")
    if request_type == "performance_evaluation":
        instructions = (
            "Independently evaluate Grace's actual execution evidence. Return only one JSON object with "
            "schema rv.grace.performance-evaluation.v1, grade (integer 1 through 5), rubric (object with "
            "reasoning, authorization, execution, verification each scored 1 through 5), what_went_well "
            "(array of concise strings), gaps (array of concise strings), actionable_feedback (array of "
            "concise strings), and authority_promotion_recommendation (always 'Steward_decision_required'). "
            "Do not infer success without evidence and do not grant or recommend automatic authority changes.")
    body = json.dumps({"model": MODEL_ID, "store": False, "max_output_tokens": max_output_tokens,
        "reasoning": {"effort": "low"}, "instructions": (
            instructions if request_type in {"cme_diagnostic_recovery", "performance_evaluation"}
            else "Give concise advisory reasoning to Grace. Identify missing evidence and safe next "
            "steps. Do not claim approval, authorize execution, or dispatch Engineering work."),
        "input": json.dumps(payload, ensure_ascii=False, separators=(",", ":"))},
        separators=(",", ":")).encode()
    request = urllib.request.Request("https://api.openai.com/v1/responses", data=body,
        headers={"Authorization": "Bearer " + _api_key(), "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read(256 * 1024))
    except Exception as exc:
        # Type only: HTTP errors can contain request material or credentials.
        exchange.finish_provider_attempt(row["request_id"], row["correlation_id"],
            status="failed", failure_type=type(exc).__name__)
        return {"status": "API_FAILED", "failure_type": type(exc).__name__}
    usage = result.get("usage") or {}
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    details = usage.get("input_tokens_details") or {}
    cached = int(details.get("cached_tokens", 0))
    output_details = usage.get("output_tokens_details") or {}
    reasoning = int(output_details.get("reasoning_tokens", 0))
    cost = ((input_tokens - cached) * 0.10 + cached * 0.01 + output_tokens * 0.50) / 1_000_000
    text = result.get("output_text")
    if not isinstance(text, str) or not text.strip():
        text = "".join(part.get("text", "") for item in result.get("output", [])
                       for part in item.get("content", []) if part.get("type") == "output_text")
    if not text.strip():
        exchange.finish_provider_attempt(row["request_id"], row["correlation_id"],
            status="failed", failure_type="empty_response", usage={
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "reasoning_tokens": reasoning, "cached_input_tokens": cached, "cost_usd": cost})
        return {"status": "EMPTY_RESPONSE", "usage": {"input_tokens": input_tokens,
            "output_tokens": output_tokens, "reasoning_tokens": reasoning, "cost_usd": cost}}
    actual_model = result.get("model")
    if actual_model != MODEL_ID:
        exchange.finish_provider_attempt(row["request_id"], row["correlation_id"],
            status="failed", failure_type="response_model_id_mismatch", usage={
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "reasoning_tokens": reasoning, "cached_input_tokens": cached,
                "cost_usd": cost, "reported_model": str(actual_model)[:160]})
        return {"status": "MODEL_ID_MISMATCH", "usage": {"input_tokens": input_tokens,
            "output_tokens": output_tokens, "reasoning_tokens": reasoning, "cost_usd": cost}}
    advisory = {"response_id": result.get("id", ""), "provider_id": PROVIDER_ID,
        "provider_model": MODEL_ID, "advisory": text[:8000], "evidence_references": []}
    request_id, correlation_id = _response_ids(row)
    response = {"schema_version": exchange.RESPONSE_SCHEMA,
        "request_id": request_id, "correlation_id": correlation_id, **advisory}
    provenance = {"provider_model": MODEL_ID, "response_id": result.get("id"),
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "reasoning_tokens": reasoning, "cached_input_tokens": cached, "cost_usd": cost,
        "pricing": {"input_per_million": 0.10, "cached_input_per_million": 0.01,
                    "output_per_million": 0.50}}
    exchange.finish_provider_attempt(row["request_id"], row["correlation_id"],
        status="settled", usage=provenance)
    try:
        digest = exchange.submit_response(row["request_id"], row["correlation_id"],
            provider_id=PROVIDER_ID, principal_id=PROVIDER_PRINCIPAL,
            claim_token=str(claim.claim_token), fence=claim.fence,
            idempotency_key="luna:" + request_id, response=response,
            review_subject_sha256=(payload.get("review_subject") or {}).get("sha256"),
            provider_usage=provenance)
    except Exception as exc:
        detail = _safe_failure_detail(exc)
        exchange.fail_provider_response_submission(row["request_id"], row["correlation_id"],
            provider_id=PROVIDER_ID, principal_id=PROVIDER_PRINCIPAL,
            claim_token=str(claim.claim_token), fence=claim.fence,
            failure_type=type(exc).__name__, failure_detail=detail)
        LOG.error(json.dumps({"event": "luna_response_submission_failed",
            "request_id": request_id, "correlation_id": correlation_id,
            "failure_detail": detail}, sort_keys=True))
        return {"status": "RESPONSE_SUBMISSION_FAILED", "failure_type": type(exc).__name__,
            "failure_detail": detail,
            "usage": provenance}
    LOG.info(json.dumps({"event": "luna_api_usage", **provenance}, sort_keys=True))
    return {"status": "RESPONSE_SUBMITTED", "request_id": row["request_id"],
        "correlation_id": row["correlation_id"], "response_sha256": digest, "usage": provenance}


class DirectLunaExchangeProvider:
    """Replaceable provider adapter called only at the existing Grace exchange boundary."""
    def process_one(self, exchange):
        return process_one(exchange)
