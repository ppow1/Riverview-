# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/external_reasoning_mcp.py
# Component: EXTERNAL-REASONING-MCP-TRANSPORT
# Revision: 1.2.3
# Changed: 2026-10-23 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Accept historical plan subjects without newly optional ComfyUI fields while retaining digest identity.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Preserve lifecycle criteria in provider-reviewed proposal subject digests
# Purpose: Expose the durable advisory exchange through authenticated MCP Streamable HTTP
# Execution Model: Request-driven, sessionless HTTP JSON-RPC adapter
# Observability: Sanitized request outcomes; authoritative exchange state remains PostgreSQL
# Dependencies: PyJWT with cryptography; DurableExternalReasoningExchange
# Authority: Provider-scoped advisory exchange only; no Grace consumption or execution tools
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Initial provider-scoped MCP transport
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Require expiring credential mappings and reject side-effecting JSON-RPC notifications
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Accept protocol header fallback and authenticate every MCP endpoint method
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Bound request sockets and strictly validate configured Host/Origin allowlists
# Changed: 2026-10-16 UTC | RV-EXTERNAL-MCP-ADAPTER-001 | Require both Streamable HTTP response media types in MCP client Accept
# Changed: 2026-10-17 UTC | RV-MCP-CHATGPT-OAUTH-RESOURCE-001 | Add OAuth JWT resource-server validation and OpenAI mixed-auth tool metadata
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-MCP | Expose bounded immutable review subjects and require correlated subject digest on provider replies
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-TYPED-REVIEW-SUBJECT | Validate and preserve the complete typed PlanProposal/PlanStep subject
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-EXPIRED-RESPONSE-MCP | Map durable expiration to an explicit non-success MCP result
# Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Add explicit Steward-originated Comms5 operations without constructing provider OAuth identity
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Preserve typed per-step artifact requirements in review subjects
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# Tests: tests/test_external_reasoning_mcp.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Bounded MCP Streamable HTTP adapter for Riverview's durable advisory exchange.

The transport is stateless; request, delivery, claim and response state remain in
PostgreSQL. The production launcher validates OAuth access-token signatures and
claims against a protected issuer/subject/client map. No tool argument can choose
or override an authenticated provider identity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import threading
from typing import Any, Mapping
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

import jwt
from jwt import PyJWKClient

from .external_reasoning import (
    DurableExternalReasoningExchange, ExchangeConflict, ExchangeError,
    ExchangeExpired, ExchangeNotFound, ExchangeUnauthorized,
)
from ..resident_reasoning import ArtifactRequirement, PlanProposal, PlanStep


MCP_PATH = "/mcp"
PROTECTED_RESOURCE_PATH = "/.well-known/oauth-protected-resource/mcp"
SUPPORTED_PROTOCOL_VERSIONS = frozenset({"2025-03-26", "2025-06-18", "2025-11-25"})
MAX_HTTP_BODY_BYTES = 64 * 1024
MAX_CONTEXT_RETURN_BYTES = 32 * 1024
MAX_REVIEW_SUBJECT_BYTES = 16 * 1024
MAX_TOKENS = 16
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HOSTNAME = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*\.?$")
_ALLOWED_SCOPES = {"reasoning:exchange", "reasoning:exchange:confidential"}
_ALLOWED_CLASSIFICATIONS = {"institutional", "confidential"}


class MCPConfigurationError(ValueError):
    """The protected provider identity or transport configuration is invalid."""


class MCPAuthenticationError(ValueError):
    """A bearer credential did not map to one provider principal."""


def _read_oauth_document(url: str) -> dict[str, Any]:
    """Fetch bounded HTTPS authorization metadata without following redirects."""
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise MCPConfigurationError("oauth_metadata_url_invalid")
    class _NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, _request, _fp, _code, _message, _headers, _new_url):
            return None

    request = Request(url, headers={"Accept": "application/json"})
    try:
        opener = build_opener(_NoRedirect())
        with opener.open(request, timeout=4) as response:
            if response.geturl() != url or response.status != 200:
                raise MCPConfigurationError("oauth_metadata_unavailable")
            raw = response.read(64 * 1024 + 1)
        if len(raw) > 64 * 1024:
            raise MCPConfigurationError("oauth_metadata_invalid")
        document = json.loads(raw.decode("utf-8"))
    except MCPConfigurationError:
        raise
    except Exception:
        raise MCPConfigurationError("oauth_metadata_unavailable") from None
    if not isinstance(document, dict):
        raise MCPConfigurationError("oauth_metadata_invalid")
    return document


class OAuthProviderTokenMap:
    """Validate OAuth access JWTs and map allowed subjects to fixed provider principals.

    This is a resource-server verifier only. OAuth authorization, login, consent,
    PKCE, token issuance and refresh remain responsibilities of the configured
    standards-compliant authorization server.
    """

    SCHEMA = "rv.external-reasoning.oauth-provider-auth.v1"

    def __init__(self, *, issuer: str, audience: str, entries: tuple,
                 jwks_client, client_id_metadata_document_supported: bool):
        self.issuer = issuer
        self.audience = audience
        self._entries = entries
        self._jwks_client = jwks_client
        self.client_id_metadata_document_supported = client_id_metadata_document_supported
        registrations = {}
        for entry, _subjects, _client_ids in entries:
            old = registrations.setdefault(entry.provider_id, entry.principal_id)
            if old != entry.principal_id:
                raise MCPConfigurationError("provider_principal_mapping_conflict")
        self.registrations = registrations

    @classmethod
    def load(cls, path: str | os.PathLike[str], *, issuer: str, audience: str):
        candidate = Path(path)
        try:
            if candidate.is_symlink():
                raise MCPConfigurationError("provider_auth_credential_invalid")
            info = candidate.stat()
            if (not stat.S_ISREG(info.st_mode)
                    or stat.S_IMODE(info.st_mode) not in {0o400, 0o440, 0o600}
                    or info.st_uid not in {0, os.geteuid()} or info.st_size > 16 * 1024):
                raise MCPConfigurationError("provider_auth_credential_invalid")
            document = json.loads(candidate.read_text(encoding="utf-8"))
        except MCPConfigurationError:
            raise
        except Exception:
            raise MCPConfigurationError("provider_auth_credential_invalid") from None
        return cls.from_document(document, issuer=issuer, audience=audience)

    @classmethod
    def from_document(cls, document: Any, *, issuer: str, audience: str,
                      metadata: Mapping[str, Any] | None = None, jwks_client=None):
        issuer = _https_url(issuer)
        audience = _https_url(audience)
        if (not isinstance(document, dict)
                or set(document) != {"schema_version", "providers"}
                or document.get("schema_version") != cls.SCHEMA
                or not isinstance(document.get("providers"), list)
                or not document["providers"]):
            raise MCPConfigurationError("provider_auth_map_invalid")
        if metadata is None:
            base = issuer.rstrip("/") + "/.well-known/"
            try:
                metadata = _read_oauth_document(base + "openid-configuration")
            except MCPConfigurationError as exc:
                if str(exc) != "oauth_metadata_unavailable":
                    raise
                issuer_parts = urlsplit(issuer)
                path = "/.well-known/oauth-authorization-server" + issuer_parts.path.rstrip("/")
                metadata = _read_oauth_document(
                    issuer_parts.scheme + "://" + issuer_parts.netloc + path)
        if (not isinstance(metadata, Mapping) or metadata.get("issuer") != issuer
                or not isinstance(metadata.get("authorization_endpoint"), str)
                or not isinstance(metadata.get("token_endpoint"), str)
                or not isinstance(metadata.get("jwks_uri"), str)
                or not isinstance(metadata.get("code_challenge_methods_supported"), list)
                or "S256" not in metadata["code_challenge_methods_supported"]
                or not isinstance(metadata.get("response_types_supported"), list)
                or "code" not in metadata["response_types_supported"]
                or not isinstance(metadata.get("token_endpoint_auth_methods_supported"), list)
                or not metadata["token_endpoint_auth_methods_supported"]
                or any(not isinstance(method, str)
                       for method in metadata["token_endpoint_auth_methods_supported"])
                or not set(metadata["token_endpoint_auth_methods_supported"])
                       & {"none", "private_key_jwt"}
                or not (metadata.get("client_id_metadata_document_supported") is True
                        or isinstance(metadata.get("registration_endpoint"), str))):
            raise MCPConfigurationError("oauth_authorization_server_incompatible")
        for field in ("authorization_endpoint", "token_endpoint"):
            try:
                _oauth_endpoint(metadata[field])
            except MCPConfigurationError:
                raise MCPConfigurationError("oauth_authorization_server_incompatible") from None
        if metadata.get("registration_endpoint") is not None:
            try:
                _oauth_endpoint(metadata["registration_endpoint"])
            except MCPConfigurationError:
                raise MCPConfigurationError("oauth_authorization_server_incompatible") from None
        jwks_uri = metadata["jwks_uri"]
        jwks_parts = urlsplit(jwks_uri)
        issuer_parts = urlsplit(issuer)
        if (jwks_parts.scheme != "https" or jwks_parts.hostname != issuer_parts.hostname
                or jwks_parts.port != issuer_parts.port or jwks_parts.username
                or jwks_parts.password):
            raise MCPConfigurationError("oauth_jwks_origin_invalid")
        if jwks_client is None:
            jwks_client = PyJWKClient(jwks_uri, cache_jwk_set=True,
                                      lifespan=300, timeout=4)
        entries = []
        pairs = set()
        for item in document["providers"]:
            if (not isinstance(item, dict) or set(item) != {
                    "provider_id", "principal_id", "subjects", "client_ids", "scopes"}):
                raise MCPConfigurationError("provider_auth_entry_invalid")
            provider_id, principal_id = item["provider_id"], item["principal_id"]
            subjects, client_ids, scopes = item["subjects"], item["client_ids"], item["scopes"]
            if (not isinstance(provider_id, str) or not _IDENTITY.fullmatch(provider_id)
                    or not isinstance(principal_id, str) or not _IDENTITY.fullmatch(principal_id)
                    or not isinstance(subjects, list) or not subjects
                    or any(not isinstance(value, str) or not value or len(value) > 256 for value in subjects)
                    or not isinstance(client_ids, list) or not client_ids
                    or any(not isinstance(value, str) or not value or len(value) > 512 for value in client_ids)
                    or not isinstance(scopes, list) or not scopes
                    or any(value not in _ALLOWED_SCOPES for value in scopes)
                    or "reasoning:exchange" not in scopes):
                raise MCPConfigurationError("provider_auth_entry_invalid")
            for subject in subjects:
                for client_id in client_ids:
                    pair = (subject, client_id)
                    if pair in pairs:
                        raise MCPConfigurationError("provider_auth_mapping_ambiguous")
                    pairs.add(pair)
            entries.append(ProviderPrincipal(provider_id, principal_id,
                frozenset(scopes), "", datetime.max.replace(tzinfo=timezone.utc)))
            entries[-1] = (entries[-1], frozenset(subjects), frozenset(client_ids))
        return cls(issuer=issuer, audience=audience, entries=tuple(entries),
                   jwks_client=jwks_client,
                   client_id_metadata_document_supported=(
                       metadata.get("client_id_metadata_document_supported") is True))

    @property
    def provider_entries(self):
        return self._entries

    def resolve(self, token: str) -> ProviderPrincipal:
        if not isinstance(token, str) or not 32 <= len(token) <= 8192 or any(c.isspace() for c in token):
            raise MCPAuthenticationError("invalid_token")
        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token).key
            claims = jwt.decode(token, signing_key, algorithms=["RS256", "ES256"],
                audience=self.audience, issuer=self.issuer,
                options={"require": ["exp", "iss", "sub", "aud"]})
            if claims.get("aud") != self.audience:
                raise MCPAuthenticationError("invalid_token")
            subject = claims.get("sub")
            client_id = claims.get("client_id", claims.get("azp"))
            azp = claims.get("azp")
            if (not isinstance(subject, str) or not isinstance(client_id, str)
                    or (azp is not None and azp != client_id)):
                raise MCPAuthenticationError("invalid_token")
            raw_scopes = claims.get("scope", "")
            if not isinstance(raw_scopes, str):
                raise MCPAuthenticationError("invalid_token")
            token_scopes = frozenset(raw_scopes.split())
            matched = [entry for entry, subjects, clients in self._entries
                       if subject in subjects and client_id in clients]
            if len(matched) != 1:
                raise MCPAuthenticationError("invalid_token")
            entry = matched[0]
            scopes = entry.scopes & token_scopes
            return ProviderPrincipal(entry.provider_id, entry.principal_id, scopes,
                hashlib.sha256(token.encode("utf-8")).hexdigest(),
                datetime.fromtimestamp(claims["exp"], timezone.utc))
        except MCPAuthenticationError:
            raise
        except Exception:
            raise MCPAuthenticationError("invalid_token") from None


@dataclass(frozen=True)
class ProviderPrincipal:
    provider_id: str
    principal_id: str
    scopes: frozenset[str]
    token_sha256: str
    expires_at: datetime

    def permits(self, classification: str) -> bool:
        if classification == "institutional":
            return "reasoning:exchange" in self.scopes
        if classification == "confidential":
            return "reasoning:exchange:confidential" in self.scopes
        return False


class ProviderTokenMap:
    """Resolve opaque high-entropy bearer tokens to fixed provider identities."""

    SCHEMA = "rv.external-reasoning.provider-auth.v1"

    def __init__(self, entries):
        if not isinstance(entries, tuple) or not 1 <= len(entries) <= MAX_TOKENS:
            raise MCPConfigurationError("provider_token_map_invalid")
        digests = [entry.token_sha256 for entry in entries]
        if len(set(digests)) != len(digests):
            raise MCPConfigurationError("provider_token_map_duplicate")
        self._entries = entries

    @classmethod
    def from_document(cls, document: Any):
        if (not isinstance(document, dict) or set(document) != {"schema_version", "tokens"}
                or document.get("schema_version") != cls.SCHEMA
                or not isinstance(document.get("tokens"), list)):
            raise MCPConfigurationError("provider_token_map_invalid")
        entries = []
        for item in document["tokens"]:
            if not isinstance(item, dict) or set(item) != {
                    "token_sha256", "provider_id", "principal_id", "scopes", "expires_at"}:
                raise MCPConfigurationError("provider_token_entry_invalid")
            digest, provider_id, principal_id, scopes = (
                item.get("token_sha256"), item.get("provider_id"),
                item.get("principal_id"), item.get("scopes"))
            expires_at = item.get("expires_at")
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if expiry.tzinfo is None:
                    raise ValueError
                expiry = expiry.astimezone(timezone.utc)
            except (AttributeError, TypeError, ValueError):
                raise MCPConfigurationError("provider_token_entry_invalid") from None
            if (not isinstance(digest, str) or not _SHA256.fullmatch(digest)
                    or not isinstance(provider_id, str) or not _IDENTITY.fullmatch(provider_id)
                    or not isinstance(principal_id, str) or not _IDENTITY.fullmatch(principal_id)
                    or not isinstance(scopes, list) or not scopes
                    or any(not isinstance(scope, str) or scope not in _ALLOWED_SCOPES
                           for scope in scopes)
                    or len(set(scopes)) != len(scopes)
                    or "reasoning:exchange" not in scopes):
                raise MCPConfigurationError("provider_token_entry_invalid")
            entries.append(ProviderPrincipal(provider_id, principal_id,
                frozenset(scopes), digest, expiry))
        return cls(tuple(entries))

    @classmethod
    def load(cls, path: str | os.PathLike[str]):
        """Load a systemd credential; reject symlinks and group/world-readable files."""
        candidate = Path(path)
        try:
            if candidate.is_symlink():
                raise MCPConfigurationError("provider_token_credential_invalid")
            info = candidate.stat()
            if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) not in {0o400, 0o440, 0o600}
                    or info.st_uid not in {0, os.geteuid()} or info.st_size > 16 * 1024):
                raise MCPConfigurationError("provider_token_credential_invalid")
            raw = candidate.read_bytes()
            document = json.loads(raw.decode("utf-8"))
        except MCPConfigurationError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError):
            raise MCPConfigurationError("provider_token_credential_invalid") from None
        return cls.from_document(document)

    def resolve(self, token: str) -> ProviderPrincipal:
        if not isinstance(token, str) or not 32 <= len(token) <= 4096 or any(c.isspace() for c in token):
            raise MCPAuthenticationError("invalid_token")
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        matched = None
        # Compare every configured digest to avoid disclosing which provider entry matched.
        for entry in self._entries:
            if hmac.compare_digest(digest, entry.token_sha256):
                matched = entry
        if matched is None or matched.expires_at <= datetime.now(timezone.utc):
            raise MCPAuthenticationError("invalid_token")
        return matched

    @property
    def registrations(self):
        """Return one immutable provider/principal registration per provider."""
        registrations = {}
        for entry in self._entries:
            prior = registrations.setdefault(entry.provider_id, entry.principal_id)
            if prior != entry.principal_id:
                raise MCPConfigurationError("provider_principal_mapping_conflict")
        return dict(registrations)


class ExternalProviderRegistration:
    """Identity-only marker; this MCP surface cannot invoke external inference."""

    def __init__(self, provider_id: str, principal_id: str):
        if (not isinstance(provider_id, str) or not _IDENTITY.fullmatch(provider_id)
                or not isinstance(principal_id, str) or not _IDENTITY.fullmatch(principal_id)):
            raise MCPConfigurationError("provider_registration_invalid")
        self.provider_id = provider_id
        self.exchange_principal_id = principal_id

    def propose(self, _request):
        raise RuntimeError("external_provider_is_mcp_only")


def exchange_runtime_readiness(ledger):
    """Read-only startup check for migration presence and the required narrow ACL."""
    schema = ledger.schema
    exchange = f"{schema}.external_reasoning_exchanges"
    events = f"{schema}.external_reasoning_exchange_events"
    sequence = f"{schema}.external_reasoning_exchange_events_sequence_seq"
    with ledger.db.cursor() as cursor:
        cursor.execute("""SELECT to_regclass(%s) AS exchanges,
            to_regclass(%s) AS events,
            has_table_privilege(current_user,%s,'SELECT') AS exchange_select,
            has_table_privilege(current_user,%s,'INSERT') AS exchange_insert,
            has_column_privilege(current_user,%s,'delivery_state','UPDATE') AS delivery_update,
            has_column_privilege(current_user,%s,'response_payload','UPDATE') AS response_update,
            has_table_privilege(current_user,%s,'SELECT') AS event_select,
            has_table_privilege(current_user,%s,'INSERT') AS event_insert,
            has_sequence_privilege(current_user,%s,'USAGE') AS event_sequence_usage""",
            (exchange, events, exchange, exchange, exchange, exchange,
             events, events, sequence))
        row = cursor.fetchone()
    if not row or not row["exchanges"] or not row["events"]:
        return {"status": "not_initialized", "error_code": "exchange_migration_missing"}
    required = ("exchange_select", "exchange_insert", "delivery_update", "response_update",
                "event_select", "event_insert", "event_sequence_usage")
    if not all(row[name] for name in required):
        return {"status": "blocked", "error_code": "exchange_runtime_privilege_missing"}
    return {"status": "healthy", "error_code": None}


class ExternalReasoningMCPAdapter:
    """Expose only provider-scoped list, claim, submit and body-free status tools."""

    COMPONENT_ID = "external-reasoning-mcp"
    VERSION = "1.2.0"

    def __init__(self, exchange: DurableExternalReasoningExchange,
                 token_map: ProviderTokenMap | OAuthProviderTokenMap):
        if not isinstance(exchange, DurableExternalReasoningExchange):
            raise TypeError("DurableExternalReasoningExchange is required")
        if not isinstance(token_map, (ProviderTokenMap, OAuthProviderTokenMap)):
            raise TypeError("a provider token resolver is required")
        for provider_id, principal_id in token_map.registrations.items():
            provider = exchange.router.providers.get(provider_id)
            if (provider is None or getattr(provider, "provider_id", None) != provider_id
                    or getattr(provider, "exchange_principal_id", provider_id) != principal_id):
                raise MCPConfigurationError("provider_not_registered")
        self.exchange = exchange
        self.token_map = token_map

    @staticmethod
    def tools() -> list[dict[str, Any]]:
        auth = [{"type": "oauth2", "scopes": ["reasoning:exchange",
            "reasoning:exchange:confidential"]}]
        return [
            {"name": "reasoning_exchange_list_requests",
             "description": "List bounded advisory requests assigned to this authenticated provider. For exact-proposal review requests, the immutable review subject and digest are visible only to its selected provider.",
             "securitySchemes": auth,
             "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "additionalProperties": False}},
            {"name": "reasoning_exchange_claim_request",
             "description": "Claim one assigned request with a finite lease and fencing identity.",
             "securitySchemes": auth,
             "inputSchema": {"type": "object", "required": ["request_id", "correlation_id"], "properties": {"request_id": {"type": "string", "format": "uuid"}, "correlation_id": {"type": "string", "format": "uuid"}, "lease_seconds": {"type": "integer", "minimum": 1, "maximum": 300}}, "additionalProperties": False}},
            {"name": "reasoning_exchange_submit_response",
             "description": "Submit one bounded structured advisory for the active correlated claim. Advice grants no approval or execution authority.",
             "securitySchemes": auth,
             "inputSchema": {"type": "object", "required": ["request_id", "correlation_id", "claim_token", "fence", "idempotency_key", "response"], "properties": {"request_id": {"type": "string", "format": "uuid"}, "correlation_id": {"type": "string", "format": "uuid"}, "claim_token": {"type": "string", "minLength": 36, "maxLength": 36}, "fence": {"type": "integer", "minimum": 1}, "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 240}, "review_subject_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}, "response": {"type": "object"}}, "additionalProperties": False}},
            {"name": "reasoning_exchange_status",
             "description": "Read state, sanitized diagnostics, provenance and digests for this provider's exchange; response contents are never returned.",
             "securitySchemes": auth,
             "inputSchema": {"type": "object", "required": ["request_id", "correlation_id"], "properties": {"request_id": {"type": "string", "format": "uuid"}, "correlation_id": {"type": "string", "format": "uuid"}}, "additionalProperties": False}},
        ]

    @staticmethod
    def _require_scope(principal: ProviderPrincipal, classification="institutional"):
        if not principal.permits(classification):
            raise ExchangeUnauthorized("provider_scope_denied")

    @staticmethod
    def _json(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)

    def _owned_status(self, principal, request_id, correlation_id):
        status = self.exchange.provider_status(request_id, correlation_id,
            provider_id=principal.provider_id, principal_id=principal.principal_id)
        self._require_scope(principal, status.get("classification", "institutional"))
        return status

    @classmethod
    def _review_subject(cls, row, payload):
        """Validate and return the exact bounded subject reserved for an MCP provider."""
        from_payload = payload.get("review_subject") if isinstance(payload, Mapping) else None
        from_row = row.get("review_subject")
        if from_row is not None and from_payload is not None and from_row != from_payload:
            raise ValueError("review_subject_conflict")
        subject = from_row if from_row is not None else from_payload
        if subject is None:
            return None
        if (not isinstance(subject, Mapping) or set(subject) != {
                "schema_version", "subject_id", "revision", "sha256", "proposal"}):
            raise ValueError("review_subject_invalid")
        proposal = subject["proposal"]
        if (subject["schema_version"] != "rv.grace.proposal-review-subject.v1"
                or not isinstance(subject["subject_id"], str)
                or type(subject["revision"]) is not int or not 1 <= subject["revision"] <= 3
                or not isinstance(subject["sha256"], str)
                or not _SHA256.fullmatch(subject["sha256"])
                or not isinstance(proposal, Mapping)
                or set(proposal) not in ({"summary", "steps"},
                    {"summary", "steps", "system_owned_criteria"})
                or not isinstance(proposal["summary"], str)
                or not proposal["summary"].strip() or len(proposal["summary"]) > 4000
                or not isinstance(proposal["steps"], (list, tuple))
                or not 1 <= len(proposal["steps"]) <= 20):
            raise ValueError("review_subject_invalid")
        try:
            UUID(subject["subject_id"])
            subject_id = str(subject["subject_id"])
            allowed_step_keys = set(PlanStep.__dataclass_fields__)
            required_step_keys = {"step_id", "objective", "acceptance_criteria"}
            normalized_steps = []
            for step in proposal["steps"]:
                if (not isinstance(step, Mapping) or
                        not required_step_keys <= set(step) or
                        not set(step) <= allowed_step_keys):
                    raise ValueError
                step_data = dict(step)
                fields = ["acceptance_criteria", "depends_on", "authorized_paths", "test_targets"]
                fields.append("artifact_requirements")
                for field in fields:
                    if field not in step_data:
                        continue
                    values = step_data[field]
                    if not isinstance(values, (list, tuple)):
                        raise ValueError
                    if field == "artifact_requirements":
                        step_data[field] = tuple(ArtifactRequirement(
                            item["name"], item["path"], item["media_type"],
                            tuple(item["acceptance_criteria"]), item.get("max_bytes", 32768))
                            if isinstance(item, Mapping) else item for item in values)
                    else:
                        step_data[field] = tuple(values)
                normalized_steps.append(PlanStep(**step_data))
            system_owned = proposal.get("system_owned_criteria", [])
            if not isinstance(system_owned, (list, tuple)):
                raise ValueError
            validated_proposal = PlanProposal(proposal["summary"], tuple(normalized_steps), 0,
                system_owned_criteria=tuple(system_owned))
            normalized_steps_data = []
            for original, step in zip(proposal["steps"], validated_proposal.steps):
                record = asdict(step)
                for field in allowed_step_keys - set(original):
                    record.pop(field, None)
                normalized_steps_data.append(record)
            normalized_proposal = {"summary": validated_proposal.summary,
                "steps": normalized_steps_data}
            if "system_owned_criteria" in proposal:
                normalized_proposal["system_owned_criteria"] = list(
                    validated_proposal.system_owned_criteria)
        except (TypeError, ValueError, KeyError):
            raise ValueError("review_subject_invalid") from None
        digest_input = {"subject_id": subject_id, "revision": subject["revision"],
                        "proposal": normalized_proposal}
        digest = hashlib.sha256(cls._json(digest_input).encode("utf-8")).hexdigest()
        normalized = {"schema_version": subject["schema_version"],
            "subject_id": subject_id, "revision": subject["revision"],
            "sha256": subject["sha256"], "proposal": normalized_proposal}
        encoded = cls._json(subject).encode("utf-8")
        if digest != subject["sha256"] or len(encoded) > MAX_REVIEW_SUBJECT_BYTES:
            raise ValueError("review_subject_digest_or_size_invalid")
        return normalized

    def call_tool(self, principal: ProviderPrincipal, name: str,
                  arguments: Mapping[str, Any]) -> dict[str, Any]:
        self._require_scope(principal, "institutional")
        if not isinstance(arguments, Mapping):
            raise ValueError("tool_arguments_invalid")
        if name == "reasoning_exchange_list_requests":
            if set(arguments) - {"limit"}:
                raise ValueError("tool_arguments_invalid")
            limit = arguments.get("limit", 10)
            if type(limit) is not int or not 1 <= limit <= 10:
                raise ValueError("tool_arguments_invalid")
            rows = self.exchange.eligible_requests(principal.provider_id,
                principal_id=principal.principal_id, limit=limit)
            result = []
            for row in rows:
                classification = row.get("classification")
                if not principal.permits(classification):
                    continue
                if row.get("delivery_state") == "awaiting_delivery":
                    owner_id = "mcp:" + principal.principal_id
                    lease = self.exchange.begin_delivery(row["request_id"],
                        principal.provider_id, owner_id=owner_id, lease_seconds=30)
                    if lease is None:
                        continue
                    self.exchange.mark_delivered(row["request_id"], row["correlation_id"],
                        principal.provider_id, owner_id=owner_id,
                        delivery_token=lease.claim_token, fence=lease.fence)
                payload = row["request_payload"]
                encoded = self._json(payload)
                if len(encoded.encode("utf-8")) > MAX_CONTEXT_RETURN_BYTES:
                    continue
                review_subject = self._review_subject(row, payload)
                request_result = {"request_id": str(row["request_id"]),
                    "correlation_id": str(row["correlation_id"]),
                    "objective_id": row["objective_id"],
                    "conversation_id": str(row["conversation_id"]),
                    "message_sequence": row["message_sequence"],
                    "proposal_id": row["proposal_id"],
                    "proposal_revision": row["proposal_revision"],
                    "schema_version": row["request_schema"],
                    "classification": classification,
                    "context_sha256": row["context_sha256"],
                    "deadline_at": row["deadline_at"].isoformat(),
                    "delivery_state": ("awaiting_external_claim"
                        if row.get("delivery_state") == "awaiting_delivery"
                        else row["delivery_state"]),
                    "request": payload}
                if review_subject is not None:
                    request_result["review_subject"] = review_subject
                    request_result["review_subject_sha256"] = review_subject["sha256"]
                if len(self._json(request_result).encode("utf-8")) > MAX_CONTEXT_RETURN_BYTES:
                    continue
                result.append(request_result)
            return {"requests": result, "count": len(result)}
        if name == "reasoning_exchange_claim_request":
            self._exact_keys(arguments, {"request_id", "correlation_id"},
                             {"lease_seconds"})
            lease_seconds = arguments.get("lease_seconds", 120)
            if type(lease_seconds) is not int or not 1 <= lease_seconds <= 300:
                raise ValueError("tool_arguments_invalid")
            status = self._owned_status(principal, arguments["request_id"],
                                        arguments["correlation_id"])
            claim = self.exchange.claim(arguments["request_id"], arguments["correlation_id"],
                provider_id=principal.provider_id, principal_id=principal.principal_id,
                lease_seconds=lease_seconds)
            if claim is None:
                return {"state": status["delivery_state"], "claimed": False}
            return {"request_id": claim.request_id, "correlation_id": claim.correlation_id,
                "claim_token": claim.claim_token, "fence": claim.fence,
                "lease_until": claim.lease_until.isoformat(), "duplicate": claim.duplicate}
        if name == "reasoning_exchange_submit_response":
            self._exact_keys(arguments,
                {"request_id", "correlation_id", "claim_token", "fence", "idempotency_key", "response"},
                {"review_subject_sha256"})
            if type(arguments["fence"]) is not int or arguments["fence"] < 1:
                raise ValueError("tool_arguments_invalid")
            status = self._owned_status(principal, arguments["request_id"],
                                        arguments["correlation_id"])
            expected_subject_digest = status.get("review_subject_sha256")
            supplied_subject_digest = arguments.get("review_subject_sha256")
            if expected_subject_digest is not None:
                if (not isinstance(expected_subject_digest, str)
                        or not _SHA256.fullmatch(expected_subject_digest)
                        or supplied_subject_digest != expected_subject_digest):
                    raise ValueError("review_subject_digest_mismatch")
            elif supplied_subject_digest is not None and (
                    not isinstance(supplied_subject_digest, str)
                    or not _SHA256.fullmatch(supplied_subject_digest)):
                raise ValueError("tool_arguments_invalid")
            submit_kwargs = {}
            if supplied_subject_digest is not None:
                submit_kwargs["review_subject_sha256"] = supplied_subject_digest
            digest = self.exchange.submit_response(arguments["request_id"],
                arguments["correlation_id"], provider_id=principal.provider_id,
                principal_id=principal.principal_id, claim_token=arguments["claim_token"],
                fence=arguments["fence"], idempotency_key=arguments["idempotency_key"],
                response=arguments["response"], **submit_kwargs)
            if digest == "expired":
                return {"state": "expired", "accepted": False}
            return {"response_sha256": digest, "state": "response_received"}
        if name == "reasoning_exchange_status":
            self._exact_keys(arguments, {"request_id", "correlation_id"})
            return self._owned_status(principal, arguments["request_id"],
                                      arguments["correlation_id"])
        raise KeyError("tool_not_found")

    @staticmethod
    def _exact_keys(arguments, required, optional=frozenset()):
        keys = set(arguments)
        if not required <= keys or keys - required - set(optional):
            raise ValueError("tool_arguments_invalid")

    def handle_rpc(self, principal: ProviderPrincipal | None, message: Any,
                   protocol_version: str | None = None, *,
                   auth_challenge: str | None = None):
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return self._rpc_error(message.get("id") if isinstance(message, dict) else None,
                                   -32600, "Invalid Request")
        method = message.get("method")
        request_id = message.get("id")
        is_notification = "id" not in message
        if not isinstance(method, str) or (not is_notification and
                (isinstance(request_id, bool) or not isinstance(request_id, (str, int)))):
            return self._rpc_error(request_id, -32600, "Invalid Request")
        if is_notification:
            # Never execute a tool or other request method from a JSON-RPC
            # notification; only the two protocol notifications are accepted.
            return None
        if method == "initialize":
            params = message.get("params")
            client_info = params.get("clientInfo") if isinstance(params, dict) else None
            capabilities = params.get("capabilities") if isinstance(params, dict) else None
            if (not isinstance(params, dict) or set(params) - {"protocolVersion", "capabilities", "clientInfo", "_meta"}
                    or not isinstance(params.get("protocolVersion"), str)
                    or not isinstance(capabilities, dict)
                    or not isinstance(client_info, dict)
                    or not isinstance(client_info.get("name"), str)
                    or not isinstance(client_info.get("version"), str)):
                return self._rpc_error(request_id, -32602, "Invalid params")
            requested = params["protocolVersion"]
            if requested not in SUPPORTED_PROTOCOL_VERSIONS:
                return self._rpc_error(request_id, -32602, "Unsupported protocol version")
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "protocolVersion": requested,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "Riverview External Reasoning Exchange", "version": self.VERSION},
                "instructions": "Advisory reasoning only. Responses do not authorize or execute institutional work."}}
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if protocol_version not in SUPPORTED_PROTOCOL_VERSIONS:
            return self._rpc_error(request_id, -32600, "Protocol version required")
        if method == "tools/list":
            params = message.get("params", {})
            if (not isinstance(params, dict) or set(params) - {"cursor"}
                    or params.get("cursor") not in (None, "")):
                return self._rpc_error(request_id, -32602, "Invalid params")
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"tools": self.tools()}}
        if method == "tools/call":
            params = message.get("params")
            if (not isinstance(params, dict) or set(params) - {"name", "arguments", "_meta"}
                    or not isinstance(params.get("name"), str)
                    or not isinstance(params.get("arguments", {}), dict)):
                return self._rpc_error(request_id, -32602, "Invalid params")
            if principal is None:
                return self._auth_tool_error(request_id, auth_challenge,
                                             "invalid_token", "A valid OAuth access token is required")
            try:
                result = self.call_tool(principal, params["name"], params.get("arguments", {}))
                content = [{"type": "text", "text": self._json(result)}]
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": content, "isError": False}}
            except KeyError:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "tool_not_found"}], "isError": True}}
            except ExchangeUnauthorized:
                return self._auth_tool_error(request_id, auth_challenge,
                    "insufficient_scope", "The access token lacks the required exchange scope")
            except ExchangeNotFound:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_not_found"}], "isError": True}}
            except ExchangeExpired:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_expired"}], "isError": True}}
            except ExchangeConflict:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_conflict"}], "isError": True}}
            except (ValueError, TypeError):
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "tool_arguments_invalid"}], "isError": True}}
            except ExchangeError:
                return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"content": [{"type": "text", "text": "exchange_unavailable"}], "isError": True}}
        if is_notification:
            return None
        return self._rpc_error(request_id, -32601, "Method not found")

    @staticmethod
    def _rpc_error(request_id, code, message):
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": code, "message": message}}

    @staticmethod
    def _auth_tool_error(request_id, challenge, error, description):
        result = {"content": [{"type": "text", "text": "authentication_required"}],
                  "isError": True}
        if challenge:
            result["_meta"] = {"mcp/www_authenticate": [
                challenge + ', error="' + error + '", error_description="' + description + '"']}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}



class StewardReviewBridge:
    """Comms5-only review operations authorized by the authenticated Steward.

    This bridge never creates a ProviderPrincipal. It binds each call to the
    durable request's provider route and uses the distinct Steward methods on
    the exchange, which record the Steward as the claim/response actor.
    """

    TOOLS = frozenset({
        "reasoning_exchange_list_requests", "reasoning_exchange_claim_request",
        "reasoning_exchange_submit_response", "reasoning_exchange_status",
    })

    def __init__(self, exchange):
        if not isinstance(exchange, DurableExternalReasoningExchange):
            raise TypeError("DurableExternalReasoningExchange is required")
        self.exchange = exchange

    @staticmethod
    def _steward(principal_id):
        if (not isinstance(principal_id, str) or not principal_id.startswith("steward:")
                or len(principal_id) > 256):
            raise ExchangeUnauthorized("authenticated Steward principal required")
        return principal_id

    @staticmethod
    def _exact_keys(arguments, required, optional=frozenset()):
        keys = set(arguments)
        if not required <= keys or keys - required - set(optional):
            raise ValueError("tool_arguments_invalid")

    def call_tool(self, principal_id: str, name: str,
                  arguments: Mapping[str, Any]) -> dict[str, Any]:
        principal_id = self._steward(principal_id)
        if name not in self.TOOLS or not isinstance(arguments, Mapping):
            raise ValueError("tool_arguments_invalid")
        if name == "reasoning_exchange_list_requests":
            self._exact_keys(arguments, set(), {"limit"})
            limit = arguments.get("limit", 10)
            if type(limit) is not int or not 1 <= limit <= 10:
                raise ValueError("tool_arguments_invalid")
            rows = self.exchange.steward_eligible_requests(
                principal_id=principal_id, limit=limit)
            result = []
            for row in rows:
                provider_id = row["provider_id"]
                state = row["delivery_state"]
                if state == "awaiting_delivery":
                    lease = self.exchange.begin_delivery(row["request_id"], provider_id,
                        owner_id=principal_id, lease_seconds=30)
                    if lease is None:
                        continue
                    self.exchange.mark_delivered(row["request_id"], row["correlation_id"],
                        provider_id, owner_id=principal_id,
                        delivery_token=lease.claim_token, fence=lease.fence)
                    state = "awaiting_external_claim"
                payload = row["request_payload"]
                if len(self._json(payload).encode("utf-8")) > MAX_CONTEXT_RETURN_BYTES:
                    continue
                subject = ExternalReasoningMCPAdapter._review_subject(row, payload)
                item = {"request_id": str(row["request_id"]),
                    "correlation_id": str(row["correlation_id"]),
                    "objective_id": row["objective_id"],
                    "conversation_id": str(row["conversation_id"]),
                    "message_sequence": row["message_sequence"],
                    "proposal_id": row["proposal_id"],
                    "proposal_revision": row["proposal_revision"],
                    "schema_version": row["request_schema"],
                    "provider_id": provider_id,
                    "classification": row["classification"],
                    "context_sha256": row["context_sha256"],
                    "deadline_at": row["deadline_at"].isoformat(),
                    "delivery_state": state, "request": payload}
                if subject is not None:
                    item["review_subject"] = subject
                    item["review_subject_sha256"] = subject["sha256"]
                if len(self._json(item).encode("utf-8")) <= MAX_CONTEXT_RETURN_BYTES:
                    result.append(item)
            return {"requests": result, "count": len(result)}

        if name == "reasoning_exchange_claim_request":
            self._exact_keys(arguments, {"request_id", "correlation_id"}, {"lease_seconds"})
            lease_seconds = arguments.get("lease_seconds", 120)
            if type(lease_seconds) is not int or not 1 <= lease_seconds <= 300:
                raise ValueError("tool_arguments_invalid")
            status = self.exchange.steward_status(arguments["request_id"],
                arguments["correlation_id"], principal_id=principal_id)
            claim = self.exchange.steward_claim(arguments["request_id"],
                arguments["correlation_id"], principal_id=principal_id,
                lease_seconds=lease_seconds)
            if claim is None:
                return {"state": status["delivery_state"], "claimed": False}
            return {"request_id": claim.request_id, "correlation_id": claim.correlation_id,
                "claim_token": claim.claim_token, "fence": claim.fence,
                "lease_until": claim.lease_until.isoformat(), "duplicate": claim.duplicate}

        if name == "reasoning_exchange_submit_response":
            self._exact_keys(arguments,
                {"request_id", "correlation_id", "claim_token", "fence",
                 "idempotency_key", "response"}, {"review_subject_sha256"})
            if type(arguments["fence"]) is not int or arguments["fence"] < 1:
                raise ValueError("tool_arguments_invalid")
            status = self.exchange.steward_status(arguments["request_id"],
                arguments["correlation_id"], principal_id=principal_id)
            expected_digest = status.get("review_subject_sha256")
            supplied_digest = arguments.get("review_subject_sha256")
            if expected_digest is not None and supplied_digest != expected_digest:
                raise ValueError("review_subject_digest_mismatch")
            if expected_digest is None and supplied_digest is not None:
                raise ValueError("review_subject_not_present")
            digest = self.exchange.steward_submit_response(
                arguments["request_id"], arguments["correlation_id"],
                principal_id=principal_id, claim_token=arguments["claim_token"],
                fence=arguments["fence"], idempotency_key=arguments["idempotency_key"],
                response=arguments["response"], review_subject_sha256=supplied_digest)
            if digest == "expired":
                return {"state": "expired", "accepted": False}
            return {"response_sha256": digest, "state": "response_received",
                    "reviewer_kind": "steward"}

        self._exact_keys(arguments, {"request_id", "correlation_id"})
        return self.exchange.steward_status(arguments["request_id"],
            arguments["correlation_id"], principal_id=principal_id)

    @staticmethod
    def _json(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)



class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    """Bound concurrent request threads and queue depth for the local adapter."""
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, handler, *, max_handlers=16):
        self._handler_slots = threading.BoundedSemaphore(max_handlers)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self._handler_slots.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._handler_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._handler_slots.release()


def make_handler(adapter: ExternalReasoningMCPAdapter, *, resource_url: str,
                 authorization_server_url: str, allowed_hosts=(), allowed_origins=()):
    """Create a stateless Streamable HTTP handler with per-request bearer auth."""
    resource, issuer = _https_url(resource_url), _https_url(authorization_server_url)
    hosts = frozenset(_configured_host(host) for host in
                      (allowed_hosts or ("127.0.0.1", "localhost")))
    origins = frozenset(allowed_origins)
    for origin in origins:
        parsed_origin = urlsplit(origin) if isinstance(origin, str) else None
        if (parsed_origin is None or parsed_origin.scheme not in {"https", "http"}
                or not parsed_origin.netloc or parsed_origin.path not in {"", "/"}
                or parsed_origin.query or parsed_origin.fragment
                or parsed_origin.username or parsed_origin.password):
            raise MCPConfigurationError("origin_allowlist_invalid")
    protected_resource = {"resource": resource,
        "authorization_servers": [issuer],
        "scopes_supported": sorted(_ALLOWED_SCOPES),
        "bearer_methods_supported": ["header"]}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "RiverviewMCP/1.1"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, _format, *_args):
            # BaseHTTPRequestHandler's default log includes client-supplied paths.
            return

        def _send(self, status, body=None, headers=None):
            payload = b"" if body is None else json.dumps(body, ensure_ascii=False,
                sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if body is not None:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def _host_allowed(self):
            raw_host = self.headers.get("Host", "")
            try:
                host = _canonical_host(urlsplit("//" + raw_host).hostname or "")
            except ValueError:
                host = ""
            if host not in hosts:
                self._send(403, {"error": "host_not_allowed"})
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in origins:
                self._send(403, {"error": "origin_not_allowed"})
                return False
            return True

        def do_GET(self):
            if not self._host_allowed():
                return
            if self.path == PROTECTED_RESOURCE_PATH:
                self._send(200, protected_resource)
                return
            if self.path == "/healthz":
                try:
                    ready = exchange_runtime_readiness(adapter.exchange.ledger)
                    healthy = ready["status"] == "healthy"
                    self._send(200 if healthy else 503, {"component_id": adapter.COMPONENT_ID,
                        "component_version": adapter.VERSION, **ready})
                except Exception:
                    self._send(503, {"component_id": adapter.COMPONENT_ID,
                        "component_version": adapter.VERSION, "status": "unavailable"})
                return
            if self.path == MCP_PATH:
                self._send(405, {"error": "method_not_allowed"}, {"Allow": "POST"})
                return
            self._send(404, {"error": "not_found"})

        def do_DELETE(self):
            if not self._host_allowed():
                return
            if self.path != MCP_PATH:
                self._send(404, {"error": "not_found"})
                return
            self._send(405, {"error": "method_not_allowed"}, {"Allow": "GET, POST"})

        def do_POST(self):
            if not self._host_allowed():
                return
            if self.path != MCP_PATH:
                self._send(404, {"error": "not_found"})
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            accepted = set()
            for item in self.headers.get("Accept", "").split(","):
                parts = [part.strip() for part in item.split(";")]
                quality = 1.0
                try:
                    for parameter in parts[1:]:
                        key, separator, value = parameter.partition("=")
                        if separator and key.strip().lower() == "q":
                            quality = float(value.strip())
                    if 0.0 < quality <= 1.0:
                        accepted.add(parts[0].lower())
                except ValueError:
                    continue
            if content_type != "application/json":
                self.close_connection = True
                self._send(415, {"error": "unsupported_media_type"}, {"Connection": "close"})
                return
            if not {"application/json", "text/event-stream"} <= accepted:
                self.close_connection = True
                self._send(406, {"error": "not_acceptable"}, {"Connection": "close"})
                return
            raw_length = self.headers.get("Content-Length")
            try:
                length = int(raw_length)
            except (TypeError, ValueError):
                self._send(411, {"error": "content_length_required"})
                return
            if not 0 <= length <= MAX_HTTP_BODY_BYTES:
                self.close_connection = True
                self._send(413, {"error": "request_too_large"}, {"Connection": "close"})
                return
            try:
                message = json.loads(self.rfile.read(length).decode("utf-8"),
                                     parse_constant=_reject_json_constant)
            except (UnicodeError, json.JSONDecodeError, ValueError):
                self._send(400, ExternalReasoningMCPAdapter._rpc_error(None, -32700, "Parse error"))
                return
            principal = (self._provider_token()
                if isinstance(message, dict) and message.get("method") == "tools/call"
                else None)
            protocol = self.headers.get("MCP-Protocol-Version")
            if protocol is not None and protocol not in SUPPORTED_PROTOCOL_VERSIONS:
                self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                    message.get("id") if isinstance(message, dict) else None,
                    -32600, "Unsupported protocol version"))
                return
            if isinstance(message, dict) and message.get("method") != "initialize":
                protocol = protocol or "2025-03-26"
                if protocol not in SUPPORTED_PROTOCOL_VERSIONS:
                    self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                        message.get("id"), -32600, "Protocol version required"))
                    return
                if self.headers.get("Mcp-Method") not in (None, message.get("method")):
                    self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                        message.get("id"), -32600, "MCP method header mismatch"))
                    return
                if message.get("method") == "tools/call":
                    tool_name = message.get("params", {}).get("name") if isinstance(message.get("params"), dict) else None
                    if self.headers.get("Mcp-Name") not in (None, tool_name):
                        self._send(400, ExternalReasoningMCPAdapter._rpc_error(
                            message.get("id"), -32600, "MCP name header mismatch"))
                        return
            try:
                metadata_url = resource + PROTECTED_RESOURCE_PATH
                challenge = ('Bearer resource_metadata="' + metadata_url +
                             '", scope="reasoning:exchange"')
                response = adapter.handle_rpc(principal, message, protocol,
                                              auth_challenge=challenge)
            except Exception as exc:
                # Do not log input, provider credentials, SQL text, or exception messages.
                import logging
                logging.getLogger("riverview.external_reasoning_mcp").error(
                    "request_failed error_type=%s", type(exc).__name__)
                response = ExternalReasoningMCPAdapter._rpc_error(
                    message.get("id") if isinstance(message, dict) else None,
                    -32603, "Internal error")
            if response is None:
                self._send(202)
            else:
                challenge = None
                result = response.get("result") if isinstance(response, dict) else None
                metadata = result.get("_meta") if isinstance(result, dict) else None
                challenges = metadata.get("mcp/www_authenticate") if isinstance(metadata, dict) else None
                if isinstance(challenges, list) and challenges and isinstance(challenges[0], str):
                    challenge = challenges[0]
                if challenge:
                    status = 403 if 'error="insufficient_scope"' in challenge else 401
                    self._send(status, response, {"WWW-Authenticate": challenge})
                else:
                    self._send(200, response)

        def _unauthorized(self, protected_resource_url):
            metadata_url = resource + PROTECTED_RESOURCE_PATH
            challenge = ('Bearer resource_metadata="' + metadata_url +
                         '", scope="reasoning:exchange"')
            self._send(401, {"error": "unauthorized"}, {"WWW-Authenticate": challenge})

        def _provider_token(self):
            auth = self.headers.get("Authorization", "")
            scheme, _, token = auth.partition(" ")
            if scheme.lower() != "bearer" or not token:
                return None
            try:
                return adapter.token_map.resolve(token)
            except MCPAuthenticationError:
                return None

    return Handler


def create_server(adapter, *, host="127.0.0.1", port=11827,
                  resource_url: str, authorization_server_url: str,
                  allowed_hosts=(), allowed_origins=(), max_handlers=16):
    """Create the loopback-only default server; TLS belongs to the approved proxy."""
    if host not in {"127.0.0.1", "::1", "localhost"}:
        raise MCPConfigurationError("listener_must_be_loopback")
    if type(port) is not int or not 1 <= port <= 65535:
        raise MCPConfigurationError("listener_port_invalid")
    return BoundedThreadingHTTPServer((host, port),
        make_handler(adapter, resource_url=resource_url,
            authorization_server_url=authorization_server_url,
            allowed_hosts=allowed_hosts, allowed_origins=allowed_origins),
        max_handlers=max_handlers)


def _https_url(value):
    if not isinstance(value, str) or len(value) > 512:
        raise MCPConfigurationError("oauth_resource_metadata_invalid")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment):
        raise MCPConfigurationError("oauth_resource_metadata_invalid")
    return value


def _oauth_endpoint(value):
    """Accept only absolute HTTPS OAuth endpoints without userinfo/fragments."""
    if not isinstance(value, str) or len(value) > 2048:
        raise MCPConfigurationError("oauth_endpoint_invalid")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.fragment):
        raise MCPConfigurationError("oauth_endpoint_invalid")
    try:
        parsed.port
    except ValueError:
        raise MCPConfigurationError("oauth_endpoint_invalid") from None
    return value


def _reject_json_constant(_value):
    raise ValueError("invalid_json_number")


def _canonical_host(value):
    if not isinstance(value, str) or not value:
        raise MCPConfigurationError("listener_allowlist_invalid")
    try:
        return ipaddress.ip_address(value).compressed.lower()
    except ValueError:
        normalized = value.lower()
        if not _HOSTNAME.fullmatch(normalized) or ".." in normalized:
            raise MCPConfigurationError("listener_allowlist_invalid") from None
        return normalized.rstrip(".")


def _configured_host(value):
    if not isinstance(value, str) or not value or value == "*":
        raise MCPConfigurationError("listener_allowlist_invalid")
    try:
        parsed = urlsplit("//" + value)
        if (parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or parsed.port is not None):
            raise MCPConfigurationError("listener_allowlist_invalid")
        return _canonical_host(parsed.hostname or "")
    except ValueError:
        raise MCPConfigurationError("listener_allowlist_invalid") from None
