"""Single-call GPT-6 Luna transport over Grace's existing durable exchange."""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error

PROVIDER_ID = "gpt-6-luna"
MODEL_ID = "gpt-6-luna"
PROVIDER_PRINCIPAL = "service:provider-gpt-6-luna"
BASELINE_TOTAL = 0.04104010
TOTAL_CREDIT = 5.0
ADDITIONAL_LIMIT = round(TOTAL_CREDIT - BASELINE_TOTAL, 8)
RESERVED_CALL_COST = 0.01
LOG = logging.getLogger("riverview.grace_execution")


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
    if claim is None or claim.duplicate:
        return None
    if not exchange.begin_provider_attempt(row["request_id"], row["correlation_id"],
            principal_id=PROVIDER_PRINCIPAL, reserved_cost=RESERVED_CALL_COST,
            additional_limit=ADDITIONAL_LIMIT, baseline_total=BASELINE_TOTAL,
            total_credit=TOTAL_CREDIT):
        return {"status": "BUDGET_OR_REPEAT_BLOCKED"}
    payload = row["request_payload"]
    body = json.dumps({"model": MODEL_ID, "store": False, "max_output_tokens": 192,
        "reasoning": {"effort": "low"}, "instructions": (
            "Give concise advisory reasoning to Grace. Identify missing evidence and safe next "
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
    response = {"schema_version": exchange.RESPONSE_SCHEMA,
        "request_id": row["request_id"], "correlation_id": row["correlation_id"], **advisory}
    provenance = {"provider_model": MODEL_ID, "response_id": result.get("id"),
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "reasoning_tokens": reasoning, "cached_input_tokens": cached, "cost_usd": cost,
        "pricing": {"input_per_million": 0.10, "cached_input_per_million": 0.01,
                    "output_per_million": 0.50}}
    exchange.finish_provider_attempt(row["request_id"], row["correlation_id"],
        status="settled", usage=provenance)
    digest = exchange.submit_response(row["request_id"], row["correlation_id"],
        provider_id=PROVIDER_ID, principal_id=PROVIDER_PRINCIPAL,
        claim_token=str(claim.claim_token), fence=claim.fence,
        idempotency_key="luna:" + row["request_id"], response=response,
        review_subject_sha256=(payload.get("review_subject") or {}).get("sha256"),
        provider_usage=provenance)
    LOG.info(json.dumps({"event": "luna_api_usage", **provenance}, sort_keys=True))
    return {"status": "RESPONSE_SUBMITTED", "request_id": row["request_id"],
        "correlation_id": row["correlation_id"], "response_sha256": digest, "usage": provenance}


class DirectLunaExchangeProvider:
    """Replaceable provider adapter called only at the existing Grace exchange boundary."""
    def process_one(self, exchange):
        return process_one(exchange)
