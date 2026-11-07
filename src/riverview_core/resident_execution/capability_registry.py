# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/capability_registry.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.2
# Changed: 2026-10-25 UTC | C3-AUTOMATIC-CAPABILITY-REGISTRATION | Expose declaration metadata and keep unsupported capabilities non-invocable
# Purpose: Project the existing institutional capability catalog into Grace's typed tool route
# Execution Model: Read-only catalog projection; exact-grant-checked typed invocation
# Observability: Structured discovery, authorization, execution and result envelopes
# Dependencies: Institutional authority migration 0013; existing AuthorityRegistry and pipeline
# Authority: Discovery grants no authority; invocation uses Grace's resident credential
# Tests: tests/test_grace_capability_registry.py
# =============================================================================
"""A narrow bridge from the institutional catalog to Grace's existing tool router."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg import sql
from ..institutional_authority.grants import GrantCheckUnavailable, GrantDenied


_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
_CAPABILITY_ID = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
_MAX_SCHEMA_BYTES = 16 * 1024
_MAX_CALL_BYTES = 32 * 1024
_HEALTH_TTL_SECONDS = 60


class CapabilityRegistryUnavailable(RuntimeError):
    """The protected capability projection could not provide a trustworthy result."""


def _schema_valid(schema, value):
    """Validate the bounded JSON-schema subset used by registered capability tools."""
    if not isinstance(schema, dict):
        return False
    kind = schema.get("type")
    if "enum" in schema and value not in schema["enum"]:
        return False
    if isinstance(value, str) and (len(value) < schema.get("minLength", 0)
                                   or len(value) > schema.get("maxLength", 1_000_000)):
        return False
    if kind == "object":
        if not isinstance(value, dict):
            return False
        properties = schema.get("properties", {})
        if any(key not in value for key in schema.get("required", ())):
            return False
        for key, item in value.items():
            if key in properties:
                if not _schema_valid(properties[key], item):
                    return False
            elif schema.get("additionalProperties") is False:
                return False
            elif isinstance(schema.get("additionalProperties"), dict) and not _schema_valid(
                    schema["additionalProperties"], item):
                return False
        return True
    if kind == "array":
        return (isinstance(value, list) and
                len(value) >= schema.get("minItems", 0) and
                len(value) <= schema.get("maxItems", 1_000_000) and
                all(_schema_valid(schema.get("items", {}), item) for item in value))
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        return (isinstance(value, int) and not isinstance(value, bool)
                and value >= schema.get("minimum", value)
                and value <= schema.get("maximum", value))
    if kind == "number":
        return (isinstance(value, (int, float)) and not isinstance(value, bool)
                and value >= schema.get("minimum", value)
                and value <= schema.get("maximum", value))
    if kind == "boolean":
        return isinstance(value, bool)
    return kind is None


class GraceCapabilityRegistry:
    """Read current authority metadata and invoke only explicitly wired adapters."""

    def __init__(self, *, dsn, resident_credential, authorizer,
                 authority_registry, pipeline=None, dashboard_projection=None,
                 proposal_registry=None, executors=None, authority_schema="riverview_authority",
                 runtime_schema="riverview_dev", connect=None, clock=None):
        if not isinstance(dsn, str) or not dsn:
            raise ValueError("capability registry database connection is required")
        if not isinstance(resident_credential, str) or len(resident_credential) < 32:
            raise ValueError("resident credential is required")
        if not callable(getattr(authorizer, "require", None)):
            raise TypeError("an exact-grant authorizer is required")
        if not callable(getattr(authority_registry, "set_office_state", None)):
            raise TypeError("the existing AuthorityRegistry is required")
        for name, value in (("authority schema", authority_schema),
                            ("runtime schema", runtime_schema)):
            if not isinstance(value, str) or not _SCHEMA.fullmatch(value):
                raise ValueError(f"invalid {name}")
        self.dsn = dsn
        self.credential = resident_credential
        self.authorizer = authorizer
        self.authority_registry = authority_registry
        self.pipeline = pipeline
        self.dashboard_projection = dashboard_projection
        self.proposal_registry = proposal_registry
        self.authority_schema = authority_schema
        self.runtime_schema = runtime_schema
        self.connect = connect or (lambda: psycopg.connect(self.dsn, connect_timeout=2))
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.executors = dict(executors or {})
        # These are existing, typed Riverview APIs. An entry is callable only when its
        # implementation_ref has an adapter supplied by the existing runtime.
        self.executors.setdefault("AuthorityRegistry.set_office_state.v1",
            self._set_office_state)
        if dashboard_projection is not None and callable(
                getattr(dashboard_projection, "status", None)):
            self.executors.setdefault("dashboard.projection.v1",
                self._read_dashboard_projection)
        if pipeline is not None and callable(getattr(pipeline, "submit_objective", None)):
            self.executors.setdefault("grace.execution-pipeline.v1", self._submit_work_order)
        if proposal_registry is not None and callable(getattr(proposal_registry, "create_draft", None)):
            self.executors.setdefault("institutional.proposal-registry.v1", self._create_proposal_draft)
        if proposal_registry is not None and callable(getattr(proposal_registry, "get", None)):
            self.executors.setdefault("institutional.proposal-registry-status.v1",
                                      self._read_proposal_status)

    def _catalog(self):
        try:
            with self.connect() as connection, connection.cursor() as cur:
                cur.execute(sql.SQL("SELECT {}.list_capability_registry() AS result").format(
                    sql.Identifier(self.authority_schema)))
                row = cur.fetchone()
        except (psycopg.Error, OSError):
            raise CapabilityRegistryUnavailable("capability_registry_unavailable") from None
        result = row[0] if row is not None else None
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (TypeError, ValueError):
                result = None
        if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
            raise CapabilityRegistryUnavailable("capability_registry_response_invalid")
        return result

    def _authorized_scopes(self):
        scopes = {}
        try:
            with self.connect() as connection, connection.cursor() as cur:
                cur.execute(sql.SQL(
                    "SELECT principal_id,action,scope_ref FROM {}.list_capability_grants(%s)"
                ).format(sql.Identifier(self.authority_schema)),
                    (hashlib.sha256(self.credential.encode("utf-8")).digest(),))
                rows = cur.fetchall()
                for row in rows:
                    principal_id, action, scope_ref = row[0], row[1], row[2]
                    try:
                        decision = self.authorizer.require(cur, self.credential, action, scope_ref)
                    except GrantDenied:
                        continue
                    except GrantCheckUnavailable:
                        raise CapabilityRegistryUnavailable(
                            "capability_authorization_unavailable") from None
                    if decision.get("principal_id") != principal_id:
                        continue
                    scopes.setdefault(action, set()).add(scope_ref)
        except (psycopg.Error, OSError):
            raise CapabilityRegistryUnavailable("capability_authorization_unavailable") from None
        return scopes

    def _runtime(self):
        worker = sql.Identifier(self.runtime_schema, "worker_registry")
        health = sql.Identifier(self.runtime_schema, "grace_execution_health")
        try:
            with self.connect() as connection, connection.cursor() as cur:
                cur.execute(sql.SQL("SELECT worker_id,capabilities,active,scope_ref FROM {} WHERE active")
                            .format(worker))
                workers = cur.fetchall()
                cur.execute(sql.SQL("SELECT status,worker_capabilities,last_heartbeat_at,service_id "
                                    "FROM {} WHERE service_id='grace.execution.v1'").format(health))
                heartbeat = cur.fetchone()
        except (psycopg.Error, OSError):
            raise CapabilityRegistryUnavailable("capability_runtime_status_unavailable") from None
        declared = {}
        for worker_id, capabilities, _active, scope_ref in workers:
            if isinstance(capabilities, str):
                try:
                    capabilities = json.loads(capabilities)
                except ValueError:
                    capabilities = []
            for capability in capabilities if isinstance(capabilities, list) else ():
                if isinstance(capability, str):
                    declared.setdefault(capability, []).append({
                        "worker_id": worker_id, "scope_ref": scope_ref})
        status = "unknown"
        observed_at = None
        healthy_caps = set()
        if heartbeat:
            status, raw_caps, observed_at, _service_id = heartbeat
            if isinstance(raw_caps, str):
                try:
                    raw_caps = json.loads(raw_caps)
                except ValueError:
                    raw_caps = []
            age = (self.clock() - observed_at).total_seconds() if observed_at else None
            if status == "healthy" and age is not None and 0 <= age <= _HEALTH_TTL_SECONDS:
                for item in raw_caps if isinstance(raw_caps, list) else ():
                    if isinstance(item, dict) and isinstance(item.get("capability"), str):
                        healthy_caps.add(item["capability"])
            else:
                status = "stale" if age is None or age > _HEALTH_TTL_SECONDS else status
        return declared, healthy_caps, status, observed_at

    def snapshot(self, *, scope_ref=None, capability_id=None):
        if scope_ref is not None and (not isinstance(scope_ref, str) or not 1 <= len(scope_ref) <= 512):
            raise ValueError("scope_ref is invalid")
        if capability_id is not None and (not isinstance(capability_id, str)
                                          or not _CAPABILITY_ID.fullmatch(capability_id)):
            raise ValueError("capability_id is invalid")
        rows = self._catalog()
        if capability_id is not None:
            rows = [row for row in rows if row.get("capability_id") == capability_id]
        scopes = self._authorized_scopes()
        declared, healthy, service_status, observed_at = self._runtime()
        output = []
        for row in rows:
            action = row.get("authority_action")
            authorized = sorted(scopes.get(action, ()))
            if scope_ref is not None:
                authorized_for_scope = scope_ref in authorized
                auth_status = "authorized" if authorized_for_scope else "denied"
            else:
                authorized_for_scope = bool(authorized)
                auth_status = "authorized" if authorized else "not_authorized"
            cap_id = row.get("capability_id")
            workers = declared.get(cap_id, [])
            adapter_present = row.get("implementation_ref") in self.executors
            if workers:
                availability = "available" if any(
                    item["worker_id"] and cap_id in healthy for item in workers) else "degraded"
                health_status = service_status if cap_id in healthy else "not_healthy"
            elif adapter_present:
                availability, health_status = "available", "unknown"
            else:
                availability, health_status = "unknown", "unknown"
            schema = row.get("input_schema")
            authorization_contract = row.get("authorization_contract")
            registration_blocker = row.get("registration_blocker")
            auth_mode = (authorization_contract.get("mode")
                         if isinstance(authorization_contract, dict) else None)
            invocable = bool(row.get("enabled") and not registration_blocker
                             and auth_mode == "exact_grant" and authorized_for_scope and schema
                             and row.get("implementation_ref") in self.executors)
            output.append({
                "capability_id": cap_id,
                "registered": True,
                "description": row.get("description"),
                "enabled": bool(row.get("enabled")),
                "authority_action": action,
                "owner_office": row.get("owner_office"),
                "implementation_ref": row.get("implementation_ref"),
                "dependencies": row.get("dependencies", []),
                "resources": row.get("resources", []),
                "input_schema": schema,
                "authorization_contract": authorization_contract,
                "availability_policy": row.get("availability_policy"),
                "registration_blocker": registration_blocker,
                "declaration_source": row.get("declaration_source"),
                "declaration_source_commit": row.get("declaration_source_commit"),
                "availability": availability,
                "health": health_status,
                "health_observed_at": observed_at.isoformat() if observed_at else None,
                "worker_bindings": workers,
                "authorized_scopes": authorized,
                "authorization_status": auth_status,
                "scope_ref_checked": scope_ref,
                "invocable": invocable,
                "invocation_blocker": (None if invocable else
                    registration_blocker if registration_blocker else
                    "authorization_contract_missing_or_unsupported" if auth_mode != "exact_grant" else
                    "disabled" if not row.get("enabled") else
                    "input_schema_not_registered" if not schema else
                    "no_exact_grant_for_scope" if not authorized else
                    "execution_adapter_unavailable" if row.get("implementation_ref") not in self.executors
                    else "unavailable"),
            })
        return {"schema_version": "rv.capability-registry.snapshot.v1",
                "status": "available", "source": "riverview_authority.capability_catalog",
                "observed_at": self.clock().isoformat(), "capabilities": output}

    def tool_specs(self):
        snapshot = self.snapshot()
        specs = []
        for capability in snapshot["capabilities"]:
            schema = capability["input_schema"]
            scopes = capability["authorized_scopes"]
            if (not capability["enabled"] or not scopes or not schema
                    or capability["registration_blocker"]
                    or not isinstance(capability["authorization_contract"], dict)
                    or capability["authorization_contract"].get("mode") != "exact_grant"
                    or capability["implementation_ref"] not in self.executors):
                continue
            if len(json.dumps(schema, separators=(",", ":")).encode()) > _MAX_SCHEMA_BYTES:
                continue
            specs.append({
                "name": capability["capability_id"],
                "description": (capability["description"] or "Registered Riverview capability") +
                    " Exact active Grace authorization is required. " +
                    "Implementation: " + str(capability["implementation_ref"]),
                "inputSchema": {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "scope_ref": {"type": "string", "enum": scopes},
                        "input": schema,
                    }, "required": ["scope_ref", "input"],
                },
            })
        return specs

    def invoke(self, capability_id, arguments):
        try:
            encoded_call = json.dumps(arguments, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError):
            return self._error(capability_id, "tool_arguments_invalid")
        if len(encoded_call) > _MAX_CALL_BYTES:
            return self._error(capability_id, "tool_arguments_too_large",
                call={"capability_id": capability_id,
                      "input_sha256": hashlib.sha256(encoded_call).hexdigest(),
                      "input_bytes": len(encoded_call)})
        call_record = {"call_id": str(uuid4()), "capability_id": capability_id,
                       "arguments": arguments,
                       "input_sha256": hashlib.sha256(encoded_call).hexdigest()}
        if not isinstance(arguments, dict) or set(arguments) != {"scope_ref", "input"}:
            return self._error(capability_id, "tool_arguments_invalid", call=call_record)
        scope_ref, inputs = arguments["scope_ref"], arguments["input"]
        snapshot = self.snapshot(scope_ref=scope_ref, capability_id=capability_id)
        cap = next(iter(snapshot["capabilities"]), None)
        if cap is None:
            return self._error(capability_id, "capability_not_registered", call=call_record)
        if cap["authorization_status"] != "authorized":
            return self._error(capability_id, "capability_not_authorized", call=call_record)
        if cap.get("registration_blocker"):
            return self._error(capability_id, "capability_registration_blocked", call=call_record)
        contract = cap.get("authorization_contract")
        if not isinstance(contract, dict) or contract.get("mode") != "exact_grant":
            return self._error(capability_id, "capability_authorization_contract_unsupported",
                               call=call_record)
        if not cap["enabled"]:
            return self._error(capability_id, "capability_disabled", call=call_record)
        schema = cap["input_schema"]
        if not schema or not _schema_valid(schema, inputs):
            return self._error(capability_id, "tool_arguments_invalid", call=call_record)
        executor = self.executors.get(cap["implementation_ref"])
        if executor is None:
            return self._error(capability_id, "execution_adapter_unavailable", call=call_record)
        try:
            with self.connect() as connection, connection.cursor() as cur:
                grant = self.authorizer.require(cur, self.credential,
                    cap["authority_action"], scope_ref)
            result = executor(scope_ref=scope_ref, inputs=inputs,
                              credential=self.credential, grant=grant)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if isinstance(exc, GrantCheckUnavailable):
                return self._error(capability_id, "capability_authorization_unavailable",
                                   call=call_record)
            if (isinstance(exc, (GrantDenied, PermissionError)) or
                    type(exc).__name__ == "AuthorityDenied"):
                return self._error(capability_id, "capability_not_authorized", call=call_record)
            if code:
                code = code if re.fullmatch(r"[a-z][a-z0-9_]{0,63}", str(code)) else "capability_execution_failed"
            else:
                code = "capability_execution_failed"
            return self._error(capability_id, code, call=call_record)
        return {"schema_version": "rv.grace.tool-result.v1", "status": "ok",
                "tool": capability_id, "call": call_record,
                "authorization": {"status": "authorized", "principal_id": grant["principal_id"],
                                  "action": cap["authority_action"], "scope_ref": scope_ref,
                                  "grant_id": grant["grant_id"]},
                "result": result}

    def _set_office_state(self, *, scope_ref, inputs, credential, grant):
        prefix = "office:"
        if not scope_ref.startswith(prefix):
            raise PermissionError("office_scope_required")
        office_id = scope_ref[len(prefix):]
        revision = self.authority_registry.set_office_state(
            credential, office_id, inputs["state"],
            expected_revision=inputs["expected_revision"])
        return {"office_id": office_id, "revision": revision, "status": "updated"}

    def _read_dashboard_projection(self, *, scope_ref, inputs, credential, grant):
        if scope_ref != "institution:riverview" or inputs:
            raise PermissionError("institution_status_scope_required")
        return self.dashboard_projection.status()

    def _submit_work_order(self, *, scope_ref, inputs, credential, grant):
        objective = self.pipeline.submit_objective(
            inputs["objective_id"], inputs["request"], inputs["acceptance_criteria"],
            scope_ref=scope_ref, credential=credential,
            criteria_source="steward_supplied")
        return {"objective": objective,
                "verification": {"status": "pending",
                    "source": "existing_assignment_controller_and_independent_verifier"}}

    def _create_proposal_draft(self, *, scope_ref, inputs, credential, grant):
        """Persist a Grace draft in the authoritative registry; never approve or promote."""
        if scope_ref != "institution:proposal-drafts":
            raise PermissionError("proposal_draft_scope_required")
        correlation_id = inputs["correlation_id"]
        idempotency_key = inputs["idempotency_key"]
        content = inputs["content"]
        author = grant.get("principal_id")
        if not isinstance(author, str) or not author:
            raise PermissionError("authenticated_resident_identity_required")
        # A draft writer must also be permitted to retrieve the authoritative receipt.
        with self.connect() as connection, connection.cursor() as cur:
            read_grant = self.authorizer.require(cur, credential,
                "proposal.status.read", "institution:proposal-drafts")
        if read_grant.get("principal_id") != author:
            raise PermissionError("proposal_read_identity_mismatch")
        record = self.proposal_registry.create_draft(content, created_by=author,
            origin_kind="grace_conversation",
            source_references=[{"kind": "resident_correlation", "id": correlation_id}],
            provenance={"actor_principal_id": author,
                "draft_grant_id": grant.get("grant_id"),
                "read_grant_id": read_grant.get("grant_id"),
                "correlation_id": correlation_id,
                "submission_path": "resident_capability_registry"},
            idempotency_key=idempotency_key)
        proposal = record["proposal"]
        revision = record["revision"]
        if proposal.get("created_by") != author or revision.get("content_sha256") is None:
            raise RuntimeError("proposal_persistence_receipt_invalid")
        readback = self.proposal_registry.get(proposal["proposal_id"])
        if (readback["proposal"]["created_by"] != author or
                readback["revision"]["revision"] != revision["revision"] or
                readback["revision"]["content_sha256"] != revision["content_sha256"]):
            raise RuntimeError("proposal_persistence_readback_mismatch")
        return {"proposal_id": proposal["proposal_id"],
            "revision": revision["revision"],
            "content_sha256": revision["content_sha256"],
            "author_principal_id": author,
            "correlation_id": correlation_id,
            "lifecycle_status": proposal["lifecycle_status"],
            "persistence": "durably_persisted",
            "approval": "awaiting_steward_decision",
            "readback_verified": True}

    def _read_proposal_status(self, *, scope_ref, inputs, credential, grant):
        """Return a bounded receipt for a proposal authored by this principal."""
        if scope_ref != "institution:proposal-drafts":
            raise PermissionError("proposal_draft_scope_required")
        principal = grant.get("principal_id")
        if not isinstance(principal, str) or not principal:
            raise PermissionError("authenticated_resident_identity_required")
        record = self.proposal_registry.get(inputs["proposal_id"])
        proposal = record.get("proposal", {})
        revision = record.get("revision", {})
        if proposal.get("created_by") != principal:
            # Do not disclose whether a non-owned proposal exists.
            raise PermissionError("proposal_not_found")
        return {"proposal_id": proposal["proposal_id"],
                "revision": revision["revision"],
                "content_sha256": revision["content_sha256"],
                "author_principal_id": principal,
                "lifecycle_status": proposal["lifecycle_status"],
                "approval": ("awaiting_steward_decision"
                             if proposal["lifecycle_status"] == "DRAFT" else "not_pending"),
                "readback_verified": True}

    @staticmethod
    def _error(capability_id, code, *, call=None):
        return {"schema_version": "rv.grace.tool-result.v1", "status": "error",
                "tool": capability_id if isinstance(capability_id, str) else None,
                **({"call": call} if call is not None else {}),
                "error": {"code": code}}
