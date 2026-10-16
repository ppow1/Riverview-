#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_external_reasoning_mcp.py
# Component: EXTERNAL-REASONING-MCP-TRANSPORT
# Revision: 1.0.1
# Purpose: Start the loopback authenticated MCP adapter without applying migrations
# Execution Model: systemd long-running bounded HTTP service
# Observability: Sanitized startup failure codes and private health endpoint
# Dependencies: PostgreSQL 16; Psycopg 3; systemd credentials; external reasoning package
# Authority: Provider-scoped advisory exchange only; no schema or grant changes
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Initial service launcher
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Validate the systemd provider-token credential boundary
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# Tests: tests/test_external_reasoning_mcp.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Systemd entry point for the authenticated external reasoning MCP service."""

from __future__ import annotations

import json
import os
import pwd
import sys
from pathlib import Path
import stat

from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.reasoning_escalation import ReasoningEscalationRouter
from riverview_core.resident_execution.external_reasoning import DurableExternalReasoningExchange
from riverview_core.resident_execution.external_reasoning_mcp import (
    ExternalProviderRegistration, ExternalReasoningMCPAdapter,
    MCPConfigurationError, ProviderTokenMap, create_server,
    exchange_runtime_readiness,
)
from runtime_baseline import (BaselineError, copy_systemd_credential,
                              systemd_credential_path)


SERVICE_UNIT = "riverview-external-reasoning-mcp.service"
RUNTIME_DIR = Path("/run/riverview-external-reasoning-mcp")


def _csv(name):
    value = os.environ.get(name, "")
    values = tuple(item.strip() for item in value.split(",") if item.strip())
    if len(values) > 32 or len(set(values)) != len(values):
        raise MCPConfigurationError("listener_allowlist_invalid")
    return values


def build_service(environ=None):
    """Build runtime dependencies without applying or changing database migrations."""
    environ = os.environ if environ is None else environ
    if any(environ.get(name) for name in ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
        raise MCPConfigurationError("ambient_database_override")
    credential_dir = environ.get("CREDENTIALS_DIRECTORY")
    dsn = environ.get("RIVERVIEW_PG_DSN")
    schema = environ.get("RIVERVIEW_PG_SCHEMA", "riverview_dev")
    if not credential_dir or not dsn:
        raise MCPConfigurationError("service_configuration_incomplete")
    credential_root = Path(credential_dir)
    pgpass = credential_root / "pgpass"
    token_map_path = credential_root / "provider-token-map"
    systemd_credential_path(pgpass, service_unit=SERVICE_UNIT)
    expected_credential_root = Path("/run/credentials") / SERVICE_UNIT
    try:
        root_info = credential_root.lstat()
        token_info = token_map_path.lstat()
    except OSError:
        raise MCPConfigurationError("provider_token_credential_invalid") from None
    if (credential_root != expected_credential_root or
            not stat.S_ISDIR(root_info.st_mode) or root_info.st_uid != 0 or
            stat.S_IMODE(root_info.st_mode) != 0o550 or
            not stat.S_ISREG(token_info.st_mode) or token_info.st_uid != 0 or
            stat.S_IMODE(token_info.st_mode) != 0o440 or
            token_map_path.resolve() != token_map_path.absolute()):
        raise MCPConfigurationError("provider_token_credential_invalid")
    systemd_credential_path(token_map_path, service_unit=SERVICE_UNIT)
    identity = pwd.getpwnam("riverview")
    if identity.pw_uid == 0 or os.geteuid() != identity.pw_uid:
        raise MCPConfigurationError("service_identity_mismatch")
    RUNTIME_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    copy_systemd_credential(pgpass, RUNTIME_DIR / "pgpass", identity.pw_uid)
    os.environ["PGPASSFILE"] = str(RUNTIME_DIR / "pgpass")
    token_map = ProviderTokenMap.load(token_map_path)
    registrations = {provider_id: ExternalProviderRegistration(provider_id, principal_id)
        for provider_id, principal_id in token_map.registrations.items()}
    router = ReasoningEscalationRouter(registrations)
    ledger = PostgresLedger(dsn, schema=schema)
    try:
        readiness = exchange_runtime_readiness(ledger)
        if readiness["status"] != "healthy":
            raise MCPConfigurationError(readiness["error_code"] or "exchange_runtime_unavailable")
        exchange = DurableExternalReasoningExchange(ledger, router,
            actor_id="service:external-reasoning-mcp")
        adapter = ExternalReasoningMCPAdapter(exchange, token_map)
        resource_url = environ.get("RIVERVIEW_MCP_RESOURCE_URL")
        issuer_url = environ.get("RIVERVIEW_MCP_AUTHORIZATION_SERVER_URL")
        if not resource_url or not issuer_url:
            raise MCPConfigurationError("oauth_resource_metadata_required")
        host = environ.get("RIVERVIEW_MCP_LISTEN_HOST", "127.0.0.1")
        port = int(environ.get("RIVERVIEW_MCP_LISTEN_PORT", "11827"))
        server = create_server(adapter, host=host, port=port,
            resource_url=resource_url, authorization_server_url=issuer_url,
            allowed_hosts=_csv("RIVERVIEW_MCP_ALLOWED_HOSTS"),
            allowed_origins=_csv("RIVERVIEW_MCP_ALLOWED_ORIGINS"))
        # Incoming identities are advisory-only provider principals, scoped by the
        # protected token map. They gain no Steward, resident, or Engineering grant.
        return server, ledger
    except BaseException:
        ledger.close()
        raise


def main():
    server = ledger = None
    try:
        server, ledger = build_service()
        print(json.dumps({"event": "external_reasoning_mcp_started",
            "component_id": "external-reasoning-mcp", "component_version": "1.0.0",
            "host": server.server_address[0], "port": server.server_address[1],
            "transport": "streamable-http", "database_schema": ledger.schema}), flush=True)
        server.serve_forever(poll_interval=0.5)
        return 0
    except (BaselineError, MCPConfigurationError, OSError, ValueError) as exc:
        code = getattr(exc, "code", None) or str(exc) if isinstance(exc, MCPConfigurationError) else "service_start_failed"
        print(json.dumps({"event": "external_reasoning_mcp_failed", "error_code": code}),
              file=sys.stderr, flush=True)
        return 2
    finally:
        if server is not None:
            server.server_close()
        if ledger is not None:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
