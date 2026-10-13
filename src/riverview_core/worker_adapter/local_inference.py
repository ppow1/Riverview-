# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/local_inference.py
# Component: LOCAL-INFERENCE-WORKER
# Revision: 1.0.1
# Purpose: Call a loopback OpenAI-compatible local inference endpoint as a worker action
# Execution Model: Request-driven HTTP call bounded by timeout and response size
# Observability: Sanitized error class; model identity and output are durable worker artifacts
# Dependencies: Python 3.10+; standard library; configured local inference runtime
# Authority: Loopback only; worker adapter still requires exact grants and verified knowledge
# Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Preserve model-serving identity in durable artifact
# Contracts: docs/components/WORKER_ADAPTER.md
# Tests: tests/test_local_inference.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Small loopback-only adapter for local OpenAI-compatible inference workers."""

from __future__ import annotations

import ipaddress
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class LocalInferenceError(RuntimeError):
    """Sanitized local inference failure; messages never include prompt or response."""


class LocalInferenceAction:
    """Run one grounded prompt against an explicitly configured loopback endpoint.

    Network calls are limited to a literal loopback IP address. The adapter does
    not add a credential, accept arbitrary URLs, or treat an endpoint failure as
    evidence. Callers must already have verified knowledge and action preflight.
    """

    CAPABILITY = "local.inference.v1"
    _SECRET_PATTERNS = (
        re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*\S+"),
        re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}={0,2}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    )

    def __init__(self, endpoint: str, model: str, *, model_revision: str | None = None,
                 model_sha256: str | None = None, timeout_seconds: float = 90,
                 max_prompt_bytes: int = 4096, max_output_bytes: int = 8192,
                 max_tokens: int = 128):
        parsed = urlsplit(endpoint)
        try:
            address = ipaddress.ip_address(parsed.hostname or "")
        except ValueError:
            address = None
        if (parsed.scheme != "http" or address is None or not address.is_loopback
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or not parsed.path.rstrip("/").endswith("/v1")):
            raise ValueError("endpoint must be an unauthenticated loopback HTTP /v1 URL")
        if (not isinstance(model, str) or not model or len(model) > 160
                or timeout_seconds <= 0 or max_prompt_bytes <= 0
                or max_output_bytes <= 0 or max_tokens <= 0):
            raise ValueError("model and positive bounded inference limits are required")
        if model_revision is not None and (not isinstance(model_revision, str)
                                           or not model_revision or len(model_revision) > 160):
            raise ValueError("model_revision must be a bounded non-empty string")
        if model_sha256 is not None and (not isinstance(model_sha256, str)
                                         or len(model_sha256) != 64
                                         or any(char not in "0123456789abcdef"
                                                for char in model_sha256)):
            raise ValueError("model_sha256 must be lowercase hexadecimal SHA-256")
        self.endpoint = endpoint.rstrip("/") + "/chat/completions"
        self.model = model
        self.model_revision = model_revision
        self.model_sha256 = model_sha256
        self.timeout_seconds = timeout_seconds
        self.max_prompt_bytes = max_prompt_bytes
        self.max_output_bytes = max_output_bytes
        self.max_tokens = max_tokens

    def __call__(self, assignment, grounded):
        value = grounded.value
        prompt = value if isinstance(value, str) else json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        prompt_bytes = prompt.encode("utf-8")
        if not prompt_bytes or len(prompt_bytes) > self.max_prompt_bytes:
            raise LocalInferenceError("prompt_size_invalid")
        if any(pattern.search(prompt) for pattern in self._SECRET_PATTERNS):
            raise LocalInferenceError("prompt_sensitive_content")
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "stream": False,
        }, ensure_ascii=False).encode("utf-8")
        request = Request(self.endpoint, data=body,
                          headers={"Content-Type": "application/json",
                                   "Accept": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise LocalInferenceError("endpoint_status_invalid")
                payload = response.read(self.max_output_bytes + 1)
        except HTTPError as exc:
            raise LocalInferenceError(f"endpoint_http_{exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise LocalInferenceError("endpoint_unavailable") from None
        if len(payload) > self.max_output_bytes:
            raise LocalInferenceError("response_size_invalid")
        try:
            document = json.loads(payload)
            choice = document["choices"][0]
            output = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            served_model = document["model"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LocalInferenceError("response_schema_invalid") from None
        if (not isinstance(served_model, str) or not served_model
                or not isinstance(output, str) or not output.strip()
                or len(output.encode("utf-8")) > self.max_output_bytes
                or finish_reason != "stop"):
            raise LocalInferenceError("response_incomplete")
        # Store only the useful artifact and non-sensitive provenance; the prompt
        # stays represented by the attempt's SHA-256 input digest.
        return {"provider": "llama.cpp-compatible",
                "requested_model": self.model,
                "served_model": served_model,
                "model_revision": self.model_revision,
                "model_sha256": self.model_sha256,
                "output": output.strip(),
                "finish_reason": finish_reason}
