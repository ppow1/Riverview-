# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/internal_tools.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.0
# Purpose: Expose implemented Comms5 tools as Grace's internal callable surface
# Execution Model: In-process Comms5 application dispatch from Grace's persistent conversation route
# Observability: Structured operation results and sanitized error envelopes are persisted with turns
# Dependencies: Comms5Application; DashboardReadBackend
# Authority: Authenticated Grace conversation plus the existing protected dashboard read credential
# Contracts: src/riverview_core/comms5/server.py; src/riverview_core/comms5/dashboard_backend.py
# Tests: tests/test_grace_internal_tools.py
# History: Git and revision/backup manifest
# =============================================================================
"""Internal dispatch into the same Comms5 schema, validation and backend."""

from __future__ import annotations

from uuid import uuid4

from ..comms5.dashboard_backend import DashboardReadBackend
from ..comms5.server import Comms5Application


class GraceInternalTools:
    """Call the existing Comms5 application and backend without a second tool API."""

    def __init__(self, backend=None):
        self.backend = DashboardReadBackend() if backend is None else backend
        # The app is used only after ResidentConversationService has authenticated Grace's
        # conversation request. Its backend separately authenticates fixed dashboard reads.
        self.application = Comms5Application("grace-internal-" + uuid4().hex, backend=self.backend)

    def catalog(self):
        response = self.application.handle({"jsonrpc": "2.0", "id": "catalog",
                                            "method": "tools/list", "params": {}})
        available = self.application.implemented_tools
        return [tool for tool in response["result"]["tools"] if tool["name"] in available]

    def call(self, name, arguments):
        """Return the existing Comms5 structured result in Grace's durable result envelope."""
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
