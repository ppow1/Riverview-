# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/resident_learning.py
# Component: RESIDENT-LEARNING-GOVERNANCE
# Revision: 1.0.0
# Purpose: Persist evidence-backed resident learning candidates behind an injected authorization boundary
# Execution Model: Request-driven library; no startup or background registration
# Observability: Immutable evidence revisions and append-only lifecycle events
# Dependencies: Python 3.10+; Psycopg 3; resident_execution migration 0014
# Authority: No default grants; each operation requires an injected fail-closed authorization port
# Changed: 2026-10-18 UTC | RV-RESIDENT-LEARNING-IMPLEMENTATION-001 | Add dormant common learning lifecycle service
# Contracts: docs/architecture/RESIDENT_LEARNING_GOVERNANCE.md
# Tests: tests/test_resident_learning.py; tests/test_resident_learning_postgres.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Dormant resident learning lifecycle; no runtime caller is registered."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
_RESIDENT = re.compile(r"^resident:[A-Za-z0-9._:-]{1,220}$")
_STEWARD = re.compile(r"^steward:[A-Za-z0-9._:-]{1,220}$")
_RECORD = re.compile(r"^learning:([0-9a-f-]{36})$")
_SHA = re.compile(r"^[0-9a-f]{64}$")
INSTITUTION_SCOPE = "institution:riverview"


class LearningError(RuntimeError): pass
class LearningNotFound(LearningError): pass
class LearningConflict(LearningError): pass
class LearningValidationError(LearningError, ValueError): pass
class AuthorizationDenied(LearningError, PermissionError): pass


class AuthorizationPort(Protocol):
    """Adapter to existing owner-approved exact-grant checks; no mappings are supplied here."""
    def require(self, principal_id: str, operation: str, scope_ref: str) -> dict[str, Any]: ...


class LearningStore(Protocol):
    def create_candidate(self, record: dict, *, actor_id: str, idempotency_key: str,
                         authorization_reference: str) -> dict: ...
    def get(self, record_id: str) -> dict: ...
    def transition(self, record_id: str, revision: int, expected_status: str,
                   status_after: str, *, event_type: str, actor_id: str,
                   idempotency_key: str, payload: dict) -> dict: ...
    def correct(self, old_record_id: str, revision: int, record: dict, *,
                actor_id: str, idempotency_key: str, payload: dict) -> dict: ...
    def rollback(self, record_id: str, replacement_id: str, revision: int, *,
                 actor_id: str, idempotency_key: str, payload: dict) -> dict: ...
    def list_approved(self, scope_ref: str, limit: int) -> list[dict]: ...


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _text(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise LearningValidationError(f"invalid {name}")
    return value.strip()


def _record_uuid(record_id: str) -> str:
    match = _RECORD.fullmatch(record_id or "")
    if not match:
        raise LearningNotFound("learning record not found")
    try:
        return str(UUID(match.group(1)))
    except ValueError:
        raise LearningNotFound("learning record not found") from None


def _scope(origin: str, scope_ref: str) -> str:
    if not isinstance(origin, str) or not _RESIDENT.fullmatch(origin):
        raise LearningValidationError("active resident identity is required")
    if scope_ref == origin or scope_ref == INSTITUTION_SCOPE:
        return scope_ref
    raise LearningValidationError("scope must be the origin resident or institution:riverview")


def _actor_scope(actor: str, scope_ref: str) -> str:
    if not (_RESIDENT.fullmatch(actor or "") or _STEWARD.fullmatch(actor or "")):
        raise AuthorizationDenied("authenticated resident or Steward identity is required")
    if scope_ref == INSTITUTION_SCOPE:
        return scope_ref
    if _RESIDENT.fullmatch(scope_ref or "") and actor == scope_ref:
        return scope_ref
    raise AuthorizationDenied("private learning scope is isolated to its exact resident")


def _review_scope(actor: str, scope_ref: str) -> str:
    if not (_RESIDENT.fullmatch(actor or "") or _STEWARD.fullmatch(actor or "")):
        raise AuthorizationDenied("authenticated reviewer identity is required")
    if scope_ref != INSTITUTION_SCOPE and not _RESIDENT.fullmatch(scope_ref or ""):
        raise LearningValidationError("invalid learning scope")
    return scope_ref


def _evidence(items: Any) -> list[dict]:
    kinds = {"resident_statement", "conversation_event", "repository_source",
             "operational_observation", "external_source"}
    if not isinstance(items, (list, tuple)) or not 1 <= len(items) <= 50:
        raise LearningValidationError("at least one evidence reference is required")
    result = []
    allowed = {"source_ref", "source_kind", "captured_at", "source_revision", "source_sha256"}
    for item in items:
        if not isinstance(item, dict) or set(item) - allowed:
            raise LearningValidationError("invalid evidence reference")
        source_ref = _text(item.get("source_ref"), "evidence reference", 2048)
        kind = item.get("source_kind")
        if kind not in kinds:
            raise LearningValidationError("invalid evidence source kind")
        try:
            timestamp = datetime.fromisoformat(item["captured_at"].replace("Z", "+00:00"))
        except (AttributeError, KeyError, TypeError, ValueError):
            raise LearningValidationError("evidence timestamp must include a timezone") from None
        if timestamp.tzinfo is None:
            raise LearningValidationError("evidence timestamp must include a timezone")
        revision = item.get("source_revision")
        digest = item.get("source_sha256")
        if revision is not None and (not isinstance(revision, str) or len(revision) > 256):
            raise LearningValidationError("invalid evidence revision")
        if digest is not None and (not isinstance(digest, str) or not _SHA.fullmatch(digest)):
            raise LearningValidationError("invalid evidence digest")
        result.append({"source_ref": source_ref, "source_kind": kind,
            "captured_at": timestamp.astimezone(timezone.utc).isoformat(),
            "source_revision": revision, "source_sha256": digest})
    return result


def _provenance(value: Any) -> dict:
    fields = {"recorder_id", "method", "implementation_revision", "interpretation"}
    if not isinstance(value, dict) or set(value) != fields:
        raise LearningValidationError("complete provenance is required")
    interpretation = value["interpretation"]
    if interpretation not in {"direct_observation", "resident_assertion",
                              "imported_source", "model_interpretation"}:
        raise LearningValidationError("unsupported provenance interpretation")
    revision = value["implementation_revision"]
    if revision is not None and (not isinstance(revision, str) or len(revision) > 256):
        raise LearningValidationError("invalid implementation revision")
    return {"recorded_at": _now(), "recorder_id": _text(value["recorder_id"], "recorder", 256),
        "method": _text(value["method"], "recording method", 256),
        "implementation_revision": revision, "interpretation": interpretation}


def _assert_scope(record: dict, scope_ref: str, revision: int) -> None:
    if not isinstance(record, dict) or record.get("scope_ref") != scope_ref:
        raise LearningNotFound("learning record not found")
    if type(revision) is not int or record.get("revision") != revision:
        raise LearningConflict("learning revision is stale")


def _text_list(values: Any, name: str, maximum: int) -> list[str]:
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= maximum:
        raise LearningValidationError(f"{name} is required")
    return [_text(v, name, 2048) for v in values]


def _supported(record: dict) -> bool:
    return any(e.get("event_type") == "validated"
        and e.get("payload", {}).get("validation", {}).get("result") == "SUPPORTED"
        for e in record.get("events", []))


class ResidentLearningService:
    """Common lifecycle facade. Missing, mismatched, or unavailable auth always denies."""
    OPERATIONS = frozenset({"candidate_write", "validate", "private_confirm", "shared_approve",
        "reject", "private_read", "shared_read", "correct", "rollback"})

    def __init__(self, store: LearningStore, authorizer: AuthorizationPort):
        if store is None or authorizer is None:
            raise TypeError("learning store and fail-closed authorizer are required")
        self.store, self.authorizer = store, authorizer

    def _require(self, principal: str, operation: str, scope_ref: str) -> dict:
        if operation not in self.OPERATIONS:
            raise LearningValidationError("unknown learning operation")
        if not (_RESIDENT.fullmatch(principal or "") or _STEWARD.fullmatch(principal or "")):
            raise AuthorizationDenied("authenticated resident or Steward identity is required")
        try:
            proof = self.authorizer.require(principal, operation, scope_ref)
        except Exception:
            raise AuthorizationDenied("exact learning authorization denied or unavailable") from None
        if (not isinstance(proof, dict) or proof.get("principal_id") != principal
                or not proof.get("grant_id") or not proof.get("authority_reference")):
            raise AuthorizationDenied("authorization port returned no matching exact allow")
        return proof

    def create_candidate(self, principal_id: str, *, scope_ref: str, content: str,
                         evidence: list[dict], provenance: dict, classification: str,
                         retention: str, idempotency_key: str) -> dict:
        scope_ref = _scope(principal_id, scope_ref)
        proof = self._require(principal_id, "candidate_write", scope_ref)
        content = _text(content, "content", 12000)
        if classification not in {"internal", "confidential", "restricted", "local_only"}:
            raise LearningValidationError("unsupported classification")
        if scope_ref == INSTITUTION_SCOPE and classification == "local_only":
            raise LearningValidationError("local_only content cannot be shared institutionally")
        if retention != "bounded_durable":
            raise LearningValidationError("durable records require bounded retention")
        prov = _provenance(provenance)
        if prov["recorder_id"] != principal_id:
            raise LearningValidationError("candidate recorder must match authenticated origin resident")
        record = {"record_id": "learning:" + str(uuid4()), "revision": 1,
            "originating_resident_id": principal_id, "scope_ref": scope_ref,
            "classification": classification, "retention": retention, "status": "candidate",
            "content": content, "content_sha256": _digest(content), "evidence": _evidence(evidence),
            "provenance": prov, "created_at": _now()}
        return self.store.create_candidate(record, actor_id=principal_id,
            idempotency_key=_text(idempotency_key, "idempotency key", 240),
            authorization_reference=proof["authority_reference"])

    def validate(self, principal_id: str, record_id: str, *, scope_ref: str,
                 expected_revision: int, result: str, evidence_refs: list[str],
                 authority_event_ref: str, idempotency_key: str) -> dict:
        scope_ref = _review_scope(principal_id, scope_ref)
        proof = self._require(principal_id, "validate", scope_ref)
        record = self.store.get(record_id)
        _assert_scope(record, scope_ref, expected_revision)
        if record["status"] != "candidate" or principal_id == record["originating_resident_id"]:
            raise LearningConflict("validation requires a candidate and an independent validator")
        if result not in {"SUPPORTED", "CONTRADICTED", "INSUFFICIENT"}:
            raise LearningValidationError("invalid validation result")
        status = {"SUPPORTED": "validated", "CONTRADICTED": "rejected",
                  "INSUFFICIENT": "candidate"}[result]
        payload = {"validation": {"result": result, "validator_id": principal_id,
            "validated_at": _now(), "evidence_refs": _text_list(evidence_refs, "validation evidence", 50),
            "authority_event_ref": _text(authority_event_ref, "validation event", 256)},
            "authorization": proof}
        return self.store.transition(record_id, expected_revision, "candidate", status,
            event_type="validated" if status == "validated" else (
                "rejected" if status == "rejected" else "validation_inconclusive"),
            actor_id=principal_id, idempotency_key=_text(idempotency_key, "idempotency key", 240),
            payload=payload)

    def approve_shared(self, principal_id: str, record_id: str, *, expected_revision: int,
                       approved_purpose: str, authority_event_ref: str,
                       idempotency_key: str) -> dict:
        proof = self._require(principal_id, "shared_approve", INSTITUTION_SCOPE)
        if not _STEWARD.fullmatch(principal_id or ""):
            raise AuthorizationDenied("institutional approval requires a Steward identity")
        record = self.store.get(record_id)
        _assert_scope(record, INSTITUTION_SCOPE, expected_revision)
        if record["status"] != "validated" or not _supported(record):
            raise LearningConflict("only independently validated knowledge can be approved")
        decision = {"outcome": "STEWARD_APPROVE", "actor_id": principal_id,
            "decided_at": _now(), "scope_ref": INSTITUTION_SCOPE,
            "purpose": _text(approved_purpose, "approved purpose", 1000),
            "content_sha256": record["content_sha256"],
            "authority_event_ref": _text(authority_event_ref, "approval event", 256)}
        return self.store.transition(record_id, expected_revision, "validated", "approved",
            event_type="approved", actor_id=principal_id,
            idempotency_key=_text(idempotency_key, "idempotency key", 240),
            payload={"decision": decision, "authorization": proof})

    def confirm_private(self, principal_id: str, record_id: str, *, scope_ref: str,
                        expected_revision: int,
                        authority_event_ref: str, idempotency_key: str) -> dict:
        scope_ref = _actor_scope(principal_id, scope_ref)
        if scope_ref == INSTITUTION_SCOPE:
            raise AuthorizationDenied("resident confirmation cannot approve institutional knowledge")
        proof = self._require(principal_id, "private_confirm", scope_ref)
        record = self.store.get(record_id)
        if record.get("scope_ref") != scope_ref or record["originating_resident_id"] != principal_id:
            raise AuthorizationDenied("private retention is limited to the originating resident")
        _assert_scope(record, scope_ref, expected_revision)
        if record["status"] != "validated" or not _supported(record):
            raise LearningConflict("only validated private candidates can be confirmed")
        decision = {"outcome": "RESIDENT_CONFIRM", "actor_id": principal_id,
            "decided_at": _now(), "scope_ref": scope_ref,
            "purpose": "resident-confirmed private retention",
            "content_sha256": record["content_sha256"],
            "authority_event_ref": _text(authority_event_ref, "confirmation event", 256)}
        return self.store.transition(record_id, expected_revision, "validated", "approved",
            event_type="approved", actor_id=principal_id,
            idempotency_key=_text(idempotency_key, "idempotency key", 240),
            payload={"decision": decision, "authorization": proof})

    def reject(self, principal_id: str, record_id: str, *, scope_ref: str,
               expected_revision: int, reason: str, authority_event_ref: str,
               idempotency_key: str) -> dict:
        scope_ref = _actor_scope(principal_id, scope_ref)
        if scope_ref == INSTITUTION_SCOPE and not _STEWARD.fullmatch(principal_id or ""):
            raise AuthorizationDenied("institutional rejection requires a Steward")
        proof = self._require(principal_id, "reject", scope_ref)
        record = self.store.get(record_id)
        _assert_scope(record, scope_ref, expected_revision)
        if record["status"] not in {"candidate", "validated"}:
            raise LearningConflict("record is not eligible for rejection")
        payload = {"decision": {"outcome": "REJECT", "actor_id": principal_id,
            "decided_at": _now(), "scope_ref": scope_ref, "purpose": "candidate review",
            "content_sha256": record["content_sha256"],
            "authority_event_ref": _text(authority_event_ref, "rejection event", 256),
            "reason": _text(reason, "rejection reason", 2000)}, "authorization": proof}
        return self.store.transition(record_id, expected_revision, record["status"], "rejected",
            event_type="rejected", actor_id=principal_id,
            idempotency_key=_text(idempotency_key, "idempotency key", 240), payload=payload)

    def retrieve(self, principal_id: str, *, scope_ref: str, limit: int = 50) -> list[dict]:
        scope_ref = _actor_scope(principal_id, scope_ref)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise LearningValidationError("limit must be 1..100")
        operation = "shared_read" if scope_ref == INSTITUTION_SCOPE else "private_read"
        self._require(principal_id, operation, scope_ref)
        return self.store.list_approved(scope_ref, limit)

    def correct(self, principal_id: str, record_id: str, *, scope_ref: str,
                expected_revision: int, content: str, evidence: list[dict],
                provenance: dict, idempotency_key: str) -> dict:
        scope_ref = _actor_scope(principal_id, scope_ref)
        proof = self._require(principal_id, "correct", scope_ref)
        old = self.store.get(record_id)
        _assert_scope(old, scope_ref, expected_revision)
        if old["status"] != "approved":
            raise LearningConflict("only approved knowledge can be corrected")
        if scope_ref == INSTITUTION_SCOPE and not _STEWARD.fullmatch(principal_id or ""):
            raise AuthorizationDenied("institutional correction requires Steward authority")
        if scope_ref != INSTITUTION_SCOPE and principal_id != old["originating_resident_id"]:
            raise AuthorizationDenied("private correction is limited to the originating resident")
        new_content = _text(content, "corrected content", 12000)
        prov = _provenance(provenance)
        if prov["recorder_id"] != principal_id:
            raise LearningValidationError("correction recorder must match authenticated principal")
        new_record = {"record_id": "learning:" + str(uuid4()), "revision": 1,
            "originating_resident_id": old["originating_resident_id"], "scope_ref": scope_ref,
            "classification": old["classification"], "retention": old["retention"],
            "status": "candidate", "content": new_content, "content_sha256": _digest(new_content),
            "evidence": _evidence(evidence), "provenance": prov, "created_at": _now(),
            "supersedes": record_id}
        return self.store.correct(record_id, expected_revision, new_record, actor_id=principal_id,
            idempotency_key=_text(idempotency_key, "idempotency key", 240),
            payload={"authorization": proof, "correction_reason": "correction candidate"})

    def rollback(self, principal_id: str, record_id: str, replacement_id: str, *,
                 scope_ref: str, expected_revision: int, revalidation: dict,
                 idempotency_key: str) -> dict:
        scope_ref = _actor_scope(principal_id, scope_ref)
        if scope_ref == INSTITUTION_SCOPE and not _STEWARD.fullmatch(principal_id or ""):
            raise AuthorizationDenied("institutional rollback requires Steward authority")
        proof = self._require(principal_id, "rollback", scope_ref)
        previous, replacement = self.store.get(record_id), self.store.get(replacement_id)
        _assert_scope(previous, scope_ref, expected_revision)
        if (previous["status"] != "superseded" or replacement.get("supersedes") != record_id
                or replacement.get("scope_ref") != scope_ref
                or not any(e.get("status_after") == "approved" for e in previous.get("events", []))):
            raise LearningConflict("records are not an approved correction and its supersession")
        if not isinstance(revalidation, dict) or revalidation.get("result") != "SUPPORTED":
            raise LearningValidationError("rollback requires fresh supported validation")
        validator = _text(revalidation.get("validator_id"), "rollback validator", 256)
        if validator == previous["originating_resident_id"]:
            raise AuthorizationDenied("rollback revalidation must be independent")
        validation_proof = self._require(validator, "validate", scope_ref)
        payload = {"revalidation": {"result": "SUPPORTED", "validator_id": validator,
            "validated_at": _now(), "evidence_refs": _text_list(
                revalidation.get("evidence_refs"), "rollback evidence", 50),
            "authority_event_ref": _text(revalidation.get("authority_event_ref"),
                "rollback validation event", 256)}, "authorization": proof,
            "validation_authorization": validation_proof,
            "restored_content_sha256": previous["content_sha256"]}
        return self.store.rollback(record_id, replacement_id, expected_revision,
            actor_id=principal_id, idempotency_key=_text(idempotency_key, "idempotency key", 240),
            payload=payload)


class PostgresResidentLearningStore:
    """Append-only PostgreSQL repository. Migration 0014 grants no runtime table access."""

    def __init__(self, dsn: str, *, schema: str = "riverview_dev"):
        if not isinstance(schema, str) or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid learning schema")
        self.schema = schema
        try:
            self.db = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        except psycopg.Error as exc:
            raise LearningError(type(exc).__name__) from None

    def close(self) -> None: self.db.close()

    def _path(self, cur) -> None:
        cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))

    @staticmethod
    def _uuid(record_id: str) -> str: return _record_uuid(record_id)

    def _event(self, cur, record_id, revision, event_type, state, actor_id, key, payload):
        cur.execute("""INSERT INTO resident_learning_events
            (record_id,revision,event_type,status_after,actor_id,idempotency_key,payload)
            VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)""",
            (self._uuid(record_id), revision, event_type, state, actor_id, key,
             json.dumps(payload, sort_keys=True)))

    def create_candidate(self, record, *, actor_id, idempotency_key, authorization_reference=""):
        identity = self._uuid(record["record_id"])
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                cur.execute("""SELECT record_id,originating_resident_id,scope_ref,content_sha256
                    FROM resident_learning_records WHERE idempotency_key=%s FOR UPDATE""",
                    (idempotency_key,))
                old = cur.fetchone()
                if old:
                    if (old["originating_resident_id"] != record["originating_resident_id"]
                            or old["scope_ref"] != record["scope_ref"]
                            or old["content_sha256"] != record["content_sha256"]):
                        raise LearningConflict("idempotency key conflicts")
                    return self.get("learning:" + str(old["record_id"]))
                self._insert(cur, record, actor_id, idempotency_key, authorization_reference)
            return self.get(record["record_id"])
        except LearningError: raise
        except psycopg.Error as exc: raise LearningError(type(exc).__name__) from None

    def _insert(self, cur, record, actor_id, key, authority_ref=""):
        identity = self._uuid(record["record_id"])
        cur.execute("""INSERT INTO resident_learning_records
            (record_id,originating_resident_id,scope_ref,classification,retention,
             content_sha256,idempotency_key,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::timestamptz)""",
            (identity, record["originating_resident_id"], record["scope_ref"],
             record["classification"], record["retention"], record["content_sha256"],
             key, record["created_at"]))
        cur.execute("""INSERT INTO resident_learning_revisions
            (record_id,revision,content,content_sha256,evidence,provenance,supersedes_record_id)
            VALUES (%s,1,%s,%s,%s::jsonb,%s::jsonb,%s)""",
            (identity, record["content"], record["content_sha256"],
             json.dumps(record["evidence"], sort_keys=True),
             json.dumps(record["provenance"], sort_keys=True),
             self._uuid(record["supersedes"]) if record.get("supersedes") else None))
        self._event(cur, record["record_id"], 1, "candidate_created", "candidate",
            actor_id, key, {"content_sha256": record["content_sha256"],
                            "authorization_reference": authority_ref})

    def get(self, record_id):
        identity = self._uuid(record_id)
        with self.db.cursor() as cur:
            self._path(cur)
            cur.execute("""SELECT r.record_id,r.originating_resident_id,r.scope_ref,
                    r.classification,r.retention,r.content_sha256,r.created_at,
                    v.content,v.evidence,v.provenance,v.supersedes_record_id,
                    e.revision,e.status_after
                FROM resident_learning_records r
                JOIN resident_learning_revisions v ON v.record_id=r.record_id
                JOIN LATERAL (SELECT revision,status_after FROM resident_learning_events
                    WHERE record_id=r.record_id ORDER BY event_id DESC LIMIT 1) e ON TRUE
                WHERE r.record_id=%s""", (identity,))
            row = cur.fetchone()
            if row is None: raise LearningNotFound("learning record not found")
            cur.execute("""SELECT event_type,status_after,actor_id,idempotency_key,payload,recorded_at
                FROM resident_learning_events WHERE record_id=%s ORDER BY event_id""", (identity,))
            events = cur.fetchall()
        result = {"record_id":"learning:"+str(row["record_id"]), "revision":row["revision"],
            "originating_resident_id":row["originating_resident_id"],"scope_ref":row["scope_ref"],
            "classification":row["classification"],"retention":row["retention"],
            "status":row["status_after"],"content":row["content"],
            "content_sha256":row["content_sha256"],"evidence":row["evidence"],
            "provenance":row["provenance"],"created_at":row["created_at"].isoformat(),
            "events":[{**e,"recorded_at":e["recorded_at"].isoformat()} for e in events]}
        if row["supersedes_record_id"]:
            result["supersedes"]="learning:"+str(row["supersedes_record_id"])
        for event in events:
            for key in ("validation","decision","revalidation"):
                if key in event["payload"]: result[key]=event["payload"][key]
        return result

    def _state(self, cur, identity):
        cur.execute("SELECT record_id FROM resident_learning_records WHERE record_id=%s FOR UPDATE",
                    (identity,))
        if cur.fetchone() is None: raise LearningNotFound("learning record not found")
        cur.execute("""SELECT e.revision,e.status_after FROM resident_learning_events e
            WHERE e.record_id=%s ORDER BY e.event_id DESC LIMIT 1""", (identity,))
        row=cur.fetchone()
        if row is None: raise LearningNotFound("learning record not found")
        return row["revision"],row["status_after"]

    def transition(self, record_id, revision, expected, state, *, event_type,
                   actor_id, idempotency_key, payload):
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                current=self._state(cur,self._uuid(record_id))
                if current!=(revision,expected): raise LearningConflict("lifecycle state changed")
                self._event(cur,record_id,revision,event_type,state,actor_id,idempotency_key,payload)
            return self.get(record_id)
        except LearningError: raise
        except psycopg.Error as exc: raise LearningError(type(exc).__name__) from None

    def correct(self, old_record_id, revision, record, *, actor_id, idempotency_key, payload):
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                if self._state(cur,self._uuid(old_record_id))!=(revision,"approved"):
                    raise LearningConflict("only approved knowledge can be corrected")
                self._insert(cur,record,actor_id,idempotency_key+":candidate")
                self._event(cur,old_record_id,revision,"correction_started","superseded",
                    actor_id,idempotency_key,{**payload,"replacement_record_id":record["record_id"]})
            return self.get(record["record_id"])
        except LearningError: raise
        except psycopg.Error as exc: raise LearningError(type(exc).__name__) from None

    def rollback(self, record_id, replacement_id, revision, *, actor_id, idempotency_key, payload):
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                if self._state(cur,self._uuid(record_id))!=(revision,"superseded"):
                    raise LearningConflict("rollback target is no longer superseded")
                replacement=self._uuid(replacement_id)
                cur.execute("""SELECT 1 FROM resident_learning_revisions
                    WHERE record_id=%s AND supersedes_record_id=%s""",
                    (replacement,self._uuid(record_id)))
                if cur.fetchone() is None: raise LearningConflict("replacement lineage mismatch")
                cur.execute("""SELECT 1 FROM resident_learning_events
                    WHERE record_id=%s AND status_after='approved' LIMIT 1""",
                    (self._uuid(record_id),))
                if cur.fetchone() is None: raise LearningConflict("rollback target was never approved")
                self._event(cur,record_id,revision,"rollback_restored","approved",actor_id,
                    idempotency_key+":restore",payload)
                repl_state=self._state(cur,replacement)
                self._event(cur,replacement_id,repl_state[0],"rollback_superseded","superseded",
                    actor_id,idempotency_key+":replacement",
                    {"restored_record_id":record_id,"rollback_event":idempotency_key})
            return self.get(record_id)
        except LearningError: raise
        except psycopg.Error as exc: raise LearningError(type(exc).__name__) from None

    def list_approved(self, scope_ref, limit):
        with self.db.cursor() as cur:
            self._path(cur)
            cur.execute("""SELECT r.record_id FROM resident_learning_records r
                JOIN LATERAL (SELECT status_after FROM resident_learning_events
                    WHERE record_id=r.record_id ORDER BY event_id DESC LIMIT 1) e ON TRUE
                WHERE r.scope_ref=%s AND e.status_after='approved'
                ORDER BY r.created_at DESC,r.record_id LIMIT %s""",(scope_ref,limit))
            ids=[r["record_id"] for r in cur.fetchall()]
        return [self.get("learning:"+str(i)) for i in ids]
