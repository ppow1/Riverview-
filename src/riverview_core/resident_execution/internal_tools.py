# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/internal_tools.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.1
# Changed: 2026-10-24 UTC | RV-GRACE-CAPABILITY-REGISTRY-BRIDGE-20261024 | Add dynamic institution-registry discovery and exact-authorized typed capability calls.
# Purpose: Expose implemented Comms5 tools as Grace's internal callable surface
# Execution Model: In-process Comms5 application dispatch from Grace's persistent conversation route
# Observability: Structured operation results and sanitized error envelopes are persisted with turns
# Dependencies: Comms5Application; DashboardReadBackend; GraceCapabilityRegistry
# Authority: Authenticated Grace conversation plus Grace's exact resident credential grants
# Contracts: src/riverview_core/comms5/server.py; src/riverview_core/comms5/dashboard_backend.py
# Tests: tests/test_grace_internal_tools.py
# History: Git and revision/backup manifest
# =============================================================================
"""Internal dispatch into the same Comms5 schema, validation and backend."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from ..comms5.dashboard_backend import DashboardReadBackend
from ..comms5.server import Comms5Application
from .capability_registry import GraceCapabilityRegistry


_DISCOVER_TOOL = {
    "name": "riverview_capability_discover",
    "description": ("Read the current institutional capability registry, including schemas, "
                    "resource bindings, worker availability, health and Grace's exact grants."),
    "inputSchema": {"type": "object", "additionalProperties": False,
        "properties": {"capability_id": {"type": "string"},
                       "scope_ref": {"type": "string"}}},
}


class GraceInternalTools:
    """Call the existing Comms5 application and backend without a second tool API."""

    def __init__(self, backend=None, *, capability_registry=None):
        self.backend = DashboardReadBackend() if backend is None else backend
        # The app is used only after ResidentConversationService has authenticated Grace's
        # conversation request. Its backend separately authenticates fixed dashboard reads.
        self.application = Comms5Application("grace-internal-" + uuid4().hex, backend=self.backend)
        self.capability_registry = capability_registry

    def catalog(self):
        response = self.application.handle({"jsonrpc": "2.0", "id": "catalog",
                                            "method": "tools/list", "params": {}})
        available = self.application.implemented_tools
        tools = [tool for tool in response["result"]["tools"] if tool["name"] in available]
        if self.capability_registry is not None:
            try:
                capability_tools = self.capability_registry.tool_specs()
            except Exception:
                # Ordinary chat remains available; an explicit discovery call will
                # return the registry outage as a structured, persisted tool error.
                capability_tools = []
            tools.extend([_DISCOVER_TOOL, *capability_tools])
        return tools

    def call(self, name, arguments):
        """Return the existing Comms5 structured result in Grace's durable result envelope."""
        if self.capability_registry is not None:
            if name == "riverview_capability_discover":
                call_record = {"call_id": str(uuid4()), "tool": name,
                               "arguments": arguments}
                try:
                    encoded = json.dumps(arguments, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False, allow_nan=False).encode("utf-8")
                    call_record["input_sha256"] = hashlib.sha256(encoded).hexdigest()
                    if len(encoded) > 4096:
                        return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                                "tool": name, "call": {"call_id": call_record["call_id"],
                                    "tool": name, "input_sha256": call_record["input_sha256"],
                                    "input_bytes": len(encoded)},
                                "error": {"code": "tool_arguments_too_large"}}
                except (TypeError, ValueError):
                    return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                            "tool": name, "error": {"code": "tool_arguments_invalid"}}
                if not isinstance(arguments, dict) or set(arguments) - {"capability_id", "scope_ref"}:
                    return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                            "tool": name, "call": call_record,
                            "error": {"code": "tool_arguments_invalid"}}
                try:
                    result = self.capability_registry.snapshot(**arguments)
                except (ValueError, RuntimeError):
                    return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                            "tool": name, "call": call_record,
                            "error": {"code": "capability_registry_unavailable"}}
                return {"schema_version": "rv.grace.tool-result.v1", "status": "ok",
                        "tool": name, "call": call_record, "result": result}
            try:
                dynamic_names = {item["name"] for item in self.capability_registry.tool_specs()}
            except Exception:
                return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                        "tool": name if isinstance(name, str) else None,
                        "error": {"code": "capability_registry_unavailable"}}
            if name in dynamic_names:
                try:
                    return self.capability_registry.invoke(name, arguments)
                except Exception:
                    return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                            "tool": name, "error": {"code": "capability_execution_failed"}}
        if name not in self.application.implemented_tools:
            return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                    "tool": name if isinstance(name, str) else None,
                    "error": {"code": "tool_not_available"}}
        response = self.application.handle({"jsonrpc": "2.0", "id": "grace-internal",
            "method": "tools/call", "params": {"name": name, "arguments": arguments}})
        if "error" in response:
            code = "tool_arguments_invalid" if response["error"].get("code") == -32602 else "tool_call_failed"
            return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                    "tool": name if isinstance(name, str) else None,
                    "error": {"code": code}}
        outcome = response.get("result", {})
        value = outcome.get("structuredContent")
        if not isinstance(value, dict):
            return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                    "tool": name if isinstance(name, str) else None,
                    "error": {"code": "tool_result_invalid"}}
        return {"schema_version": "rv.grace.tool-result.v1",
                "status": "error" if outcome.get("isError") else "ok",
                "tool": name, "result": value}
