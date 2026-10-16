# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/proposals.py
# Component: INSTITUTIONAL-PROPOSALS
# Revision: 1.0.0
# Purpose: Persist searchable, revisioned institutional proposals and review evidence
# Execution Model: Request-driven PostgreSQL repository
# Observability: Append-only proposal events with revision, actor and provenance references
# Dependencies: PostgreSQL 16; Psycopg 3; resident conversation provider contract
# Authority: Proposal records never authorize work; callers enforce Steward and resident grants
# Changed: 2026-10-16 UTC | RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001 | Initial durable proposal registry
# Contracts: docs/components/INSTITUTIONAL_PROPOSALS.md
# Tests: tests/test_institutional_proposals.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Durable, searchable proposal records, revision history and review evidence.

The registry intentionally has no execution or work-order creation method. A
proposal is planning material. Existing objective intake and exact-grant checks
remain the only path to executable Engineering work.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row


_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
_PROPOSAL_ID = re.compile(r"^proposal:[0-9a-f-]{36}$")
_TAG = re.compile(r"^[\w][\w .:/+-]{0,63}$", re.UNICODE)
_LIFECYCLE = {
    "DRAFT", "READY_FOR_REVIEW", "UNDER_REVIEW", "CHANGES_REQUIRED",
    "READY_FOR_STEWARD_DECISION", "APPROVED", "DEFERRED", "REJECTED",
    "SUPERSEDED", "ARCHIVED",
}
_TRANSITIONS = {
    "DRAFT": {"READY_FOR_REVIEW", "ARCHIVED"},
    "READY_FOR_REVIEW": {"UNDER_REVIEW", "CHANGES_REQUIRED", "READY_FOR_STEWARD_DECISION", "ARCHIVED"},
    "UNDER_REVIEW": {"CHANGES_REQUIRED", "READY_FOR_STEWARD_DECISION", "DEFERRED", "ARCHIVED"},
    "CHANGES_REQUIRED": {"DRAFT", "READY_FOR_REVIEW", "ARCHIVED"},
    "READY_FOR_STEWARD_DECISION": {"APPROVED", "DEFERRED", "REJECTED", "CHANGES_REQUIRED", "ARCHIVED"},
    "APPROVED": {"SUPERSEDED", "ARCHIVED"},
    "DEFERRED": {"READY_FOR_REVIEW", "ARCHIVED"},
    "REJECTED": {"ARCHIVED"},
    "SUPERSEDED": {"ARCHIVED"},
    "ARCHIVED": set(),
}
_REVIEW_OUTCOMES = {
    "NO_OBJECTION", "APPROVED_WITH_CONDITIONS", "CHANGES_REQUIRED",
    "BLOCKED", "INSUFFICIENT_EVIDENCE",
}
_PRIVACY = {"institutional", "confidential", "restricted", "local_only"}
_RETENTION = {"standard", "minimum_required", "ephemeral"}


class ProposalError(RuntimeError):
    """Base class for proposal validation, lookup and lifecycle failures."""


class ProposalNotFound(ProposalError):
    """The proposal or requested revision does not exist."""


class ProposalConflict(ProposalError):
    """A revision, transition, or idempotency precondition no longer holds."""


class ProposalValidationError(ProposalError, ValueError):
    """A proposal payload is outside the bounded institutional contract."""


def _text(value, name, maximum, *, required=True):
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > maximum:
        raise ProposalValidationError(f"invalid {name}")
    return value.strip()


def _string_list(value, name, maximum_items, maximum_item_length):
    if not isinstance(value, (list, tuple)) or len(value) > maximum_items:
        raise ProposalValidationError(f"invalid {name}")
    result = []
    for item in value:
        text = _text(item, name, maximum_item_length)
        if text not in result:
            result.append(text)
    return result


@dataclass(frozen=True)
class ProposalContent:
    """One immutable proposal revision's human-reviewable content."""

    title: str
    summary: str
    objective: str
    scope: str
    proposed_approach: str
    constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    tags: tuple[str, ...]

    @classmethod
    def parse(cls, value):
        expected = {"title", "summary", "objective", "scope", "proposed_approach",
                    "constraints", "acceptance_criteria", "tags"}
        if not isinstance(value, dict) or set(value) != expected:
            raise ProposalValidationError("proposal fields do not match the revision contract")
        tags = [tag.casefold() for tag in _string_list(value["tags"], "tags", 24, 64)]
        if any(not _TAG.fullmatch(tag) for tag in tags):
            raise ProposalValidationError("invalid proposal tag")
        return cls(
            _text(value["title"], "title", 200),
            _text(value["summary"], "summary", 1000),
            _text(value["objective"], "objective", 4000),
            _text(value["scope"], "scope", 4000),
            _text(value["proposed_approach"], "proposed approach", 6000),
            tuple(_string_list(value["constraints"], "constraints", 24, 1000)),
            tuple(_string_list(value["acceptance_criteria"], "acceptance criteria", 24, 1000)),
            tuple(tags),
        )

    def document(self):
        return asdict(self)


def _bounded_references(value, name, *, maximum=64, entry_keys=None):
    if not isinstance(value, (list, tuple)) or len(value) > maximum:
        raise ProposalValidationError(f"invalid {name}")
    result = []
    for item in value:
        if not isinstance(item, dict) or (entry_keys is not None and set(item) != entry_keys):
            raise ProposalValidationError(f"invalid {name} entry")
        packed = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if len(packed.encode("utf-8")) > 1024:
            raise ProposalValidationError(f"oversized {name} entry")
        result.append(item)
    return result


class ProposalRegistry:
    """PostgreSQL persistence adapter. Authorization is always enforced by callers."""

    def __init__(self, dsn, *, schema="riverview_dev"):
        if not isinstance(schema, str) or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid proposal schema")
        self.schema = schema
        try:
            self.db = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
        except psycopg.Error as exc:
            raise ProposalError(type(exc).__name__) from None

    def close(self):
        self.db.close()

    def _path(self, cur):
        cur.execute("SELECT set_config('search_path', %s, false)", (self.schema,))

    @staticmethod
    def _json(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _digest(content):
        return hashlib.sha256(ProposalRegistry._json(content).encode("utf-8")).hexdigest()

    def create_draft(self, content, *, created_by, origin_kind, source_references,
                     provenance, privacy_classification="institutional",
                     retention_policy="standard", retention_until=None,
                     idempotency_key=None):
        content = content if isinstance(content, ProposalContent) else ProposalContent.parse(content)
        created_by = _text(created_by, "creator identity", 256)
        if origin_kind not in {"grace_conversation", "steward_authored", "authorized_import"}:
            raise ProposalValidationError("unsupported proposal origin")
        if privacy_classification not in _PRIVACY or retention_policy not in _RETENTION:
            raise ProposalValidationError("unsupported privacy or retention classification")
        if retention_policy == "standard":
            if retention_until is not None:
                raise ProposalValidationError("standard retention must not have an expiry")
        else:
            if (not isinstance(retention_until, datetime) or retention_until.tzinfo is None or
                    retention_until <= datetime.now(timezone.utc)):
                raise ProposalValidationError("bounded retention requires a future timezone-aware expiry")
        source_references = _bounded_references(source_references, "source references")
        if not isinstance(provenance, dict) or not provenance:
            raise ProposalValidationError("proposal provenance is required")
        provenance = dict(provenance)
        if len(self._json(provenance).encode("utf-8")) > 4096:
            raise ProposalValidationError("proposal provenance exceeds the contract")
        if idempotency_key is not None:
            idempotency_key = _text(idempotency_key, "idempotency key", 240)
        content_doc = content.document()
        content_digest = self._digest(content_doc)
        request_digest = self._digest({"created_by": created_by, "origin_kind": origin_kind,
            "privacy_classification": privacy_classification, "retention_policy": retention_policy,
            "retention_until": retention_until.isoformat() if retention_until else None,
            "source_references": source_references, "provenance": provenance,
            "content_sha256": content_digest}) if idempotency_key else None
        proposal_id = "proposal:" + str(uuid4())
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                if idempotency_key:
                    cur.execute("""SELECT proposal_id,created_by,idempotency_request_sha256 FROM institutional_proposals
                        WHERE idempotency_key=%s FOR UPDATE""", (idempotency_key,))
                    existing = cur.fetchone()
                    if existing:
                        if (existing["created_by"] != created_by or
                                existing["idempotency_request_sha256"] != request_digest):
                            raise ProposalConflict("idempotency key is already bound to different proposal content")
                        return self.get(existing["proposal_id"])
                cur.execute("""INSERT INTO institutional_proposals
                    (proposal_id,created_by,origin_kind,privacy_classification,retention_policy,
                     retention_until,current_revision,lifecycle_status,content_sha256,idempotency_key,
                     idempotency_request_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,1,'DRAFT',%s,%s,%s)
                    ON CONFLICT (idempotency_key) DO NOTHING RETURNING proposal_id""",
                    (proposal_id, created_by, origin_kind, privacy_classification,
                     retention_policy, retention_until, content_digest, idempotency_key, request_digest))
                inserted = cur.fetchone()
                if inserted is None:
                    cur.execute("SELECT proposal_id,created_by,idempotency_request_sha256 FROM institutional_proposals WHERE idempotency_key=%s",
                                (idempotency_key,))
                    existing = cur.fetchone()
                    if (not existing or existing["created_by"] != created_by or
                            existing["idempotency_request_sha256"] != request_digest):
                        raise ProposalConflict("proposal create raced with incompatible content")
                    proposal_id = existing["proposal_id"]
                    return self.get(proposal_id)
                self._insert_revision(cur, proposal_id, 1, content_doc,
                                      source_references, provenance, created_by)
                self._event(cur, proposal_id, 1, "proposal.created", "proposal-created:" + proposal_id,
                            created_by, {"origin_kind": origin_kind, "content_sha256": content_digest})
            return self.get(proposal_id)
        except psycopg.Error as exc:
            raise ProposalError(type(exc).__name__) from None

    def _insert_revision(self, cur, proposal_id, revision, content, source_references,
                         provenance, created_by):
        cur.execute("""INSERT INTO institutional_proposal_revisions
            (proposal_id,revision,title,summary,objective,scope,proposed_approach,
             constraints,acceptance_criteria,tags,source_references,provenance,created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s::jsonb,%s::jsonb,%s)""",
            (proposal_id, revision, content["title"], content["summary"], content["objective"],
             content["scope"], content["proposed_approach"], self._json(content["constraints"]),
             self._json(content["acceptance_criteria"]), list(content["tags"]),
             self._json(source_references), self._json(provenance), created_by))

    def _event(self, cur, proposal_id, revision, event_type, idempotency_key, actor_id, payload):
        cur.execute("""INSERT INTO institutional_proposal_events
            (proposal_id,revision,event_type,idempotency_key,actor_id,payload)
            VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
            (proposal_id, revision, event_type, idempotency_key, actor_id, self._json(payload)))

    def get(self, proposal_id, *, revision=None):
        if not isinstance(proposal_id, str) or not _PROPOSAL_ID.fullmatch(proposal_id):
            raise ProposalNotFound("proposal not found")
        with self.db.cursor() as cur:
            self._path(cur)
            cur.execute("SELECT * FROM institutional_proposals WHERE proposal_id=%s", (proposal_id,))
            proposal = cur.fetchone()
            if proposal is None:
                raise ProposalNotFound("proposal not found")
            revision = proposal["current_revision"] if revision is None else revision
            if type(revision) is not int or revision < 1:
                raise ProposalNotFound("proposal revision not found")
            cur.execute("""SELECT proposal_id,revision,title,summary,objective,scope,proposed_approach,
                constraints,acceptance_criteria,tags,source_references,provenance,created_by,created_at,lifecycle_status
                FROM institutional_proposal_revisions WHERE proposal_id=%s AND revision=%s""",
                (proposal_id, revision))
            rev = cur.fetchone()
            if rev is None:
                raise ProposalNotFound("proposal revision not found")
            cur.execute("""SELECT revision,reviewer_office,reviewer_principal,review_outcome,findings,conditions,
                evidence_references,authority_reference,created_at FROM institutional_proposal_reviews
                WHERE proposal_id=%s AND revision=%s ORDER BY created_at,review_id""",
                (proposal_id, revision))
            reviews = cur.fetchall()
            cur.execute("""SELECT event_type,actor_id,payload,occurred_at FROM institutional_proposal_events
                WHERE proposal_id=%s ORDER BY occurred_at,event_id""", (proposal_id,))
            events = cur.fetchall()
        for row in (proposal, rev, *reviews, *events):
            for key, value in tuple(row.items()):
                if isinstance(value, datetime):
                    row[key] = value.isoformat()
                elif key.endswith("_id") and value is not None and not isinstance(value, str):
                    row[key] = str(value)
        return {"proposal": proposal, "revision": rev, "reviews": reviews, "events": events}

    def get_by_idempotency_key(self, idempotency_key, *, created_by=None):
        """Return a prior creation receipt without regenerating model output."""
        idempotency_key = _text(idempotency_key, "idempotency key", 240)
        with self.db.cursor() as cur:
            self._path(cur)
            cur.execute("SELECT proposal_id,created_by FROM institutional_proposals WHERE idempotency_key=%s",
                        (idempotency_key,))
            row = cur.fetchone()
        if row is None or (created_by is not None and row["created_by"] != created_by):
            return None
        return self.get(row["proposal_id"])

    def search(self, query="", *, status=None, tag=None, limit=25):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ProposalValidationError("invalid proposal search limit")
        query = _text(query, "search query", 256, required=False)
        if status is not None and status not in _LIFECYCLE:
            raise ProposalValidationError("invalid proposal status filter")
        if tag is not None:
            tag = _text(tag, "tag filter", 64).casefold()
        with self.db.cursor() as cur:
            self._path(cur)
            cur.execute("""SELECT p.proposal_id,p.current_revision,r.title,r.summary,r.tags,
                    r.lifecycle_status,p.privacy_classification,p.retention_policy,
                    p.created_by,p.updated_at,
                    CASE WHEN %s='' THEN 0 ELSE ts_rank(r.search_document,plainto_tsquery('simple',%s)) END AS rank
                FROM institutional_proposals p JOIN institutional_proposal_revisions r
                  ON r.proposal_id=p.proposal_id AND r.revision=p.current_revision
                WHERE p.lifecycle_status<>'ARCHIVED'
                  AND (%s='' OR r.search_document @@ plainto_tsquery('simple',%s)
                    OR EXISTS (SELECT 1 FROM unnest(r.tags) tag
                        WHERE to_tsvector('simple',tag) @@ plainto_tsquery('simple',%s)))
                  AND (%s::text IS NULL OR p.lifecycle_status=%s)
                  AND (%s::text IS NULL OR %s=ANY(r.tags))
                  AND (p.retention_until IS NULL OR p.retention_until>clock_timestamp())
                ORDER BY rank DESC,p.updated_at DESC,p.proposal_id LIMIT %s""",
                (query, query, query, query, query, status, status, tag, tag, limit))
            rows = cur.fetchall()
        return {"schema_version": "rv.institutional.proposals.v1", "status": "available",
                "items": [{**row, "updated_at": row["updated_at"].isoformat()} for row in rows],
                "limit": limit}

    def revise(self, proposal_id, expected_revision, content, *, actor_id,
               source_references=None, provenance=None, idempotency_key=None):
        content = content if isinstance(content, ProposalContent) else ProposalContent.parse(content)
        actor_id = _text(actor_id, "actor identity", 256)
        provenance_supplied = provenance is not None
        if provenance is None:
            provenance = {"revision_method": "steward_edit"}
        if not isinstance(provenance, dict) or len(self._json(provenance).encode()) > 4096:
            raise ProposalValidationError("invalid revision provenance")
        content_doc = content.document()
        digest = self._digest(content_doc)
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                cur.execute("SELECT current_revision,lifecycle_status FROM institutional_proposals WHERE proposal_id=%s FOR UPDATE",
                            (proposal_id,))
                current = cur.fetchone()
                if current is None:
                    raise ProposalNotFound("proposal not found")
                if current["current_revision"] != expected_revision:
                    raise ProposalConflict("proposal revision changed")
                if source_references is None:
                    cur.execute("SELECT source_references,provenance FROM institutional_proposal_revisions WHERE proposal_id=%s AND revision=%s",
                                (proposal_id, expected_revision))
                    previous_revision = cur.fetchone()
                    refs = previous_revision["source_references"]
                    inherited = previous_revision["provenance"]
                    if not provenance_supplied:
                        provenance = {"revision_method": "steward_edit",
                                      "predecessor_provenance": inherited}
                        if len(self._json(provenance).encode("utf-8")) > 4096:
                            provenance = {"revision_method": "steward_edit",
                                          "predecessor_revision": expected_revision}
                else:
                    refs = _bounded_references(source_references, "source references")
                revision = expected_revision + 1
                if current["lifecycle_status"] not in {"ARCHIVED", "REJECTED"}:
                    cur.execute("UPDATE institutional_proposal_revisions SET lifecycle_status='SUPERSEDED' WHERE proposal_id=%s AND revision=%s",
                                (proposal_id, expected_revision))
                self._insert_revision(cur, proposal_id, revision, content_doc, refs, provenance, actor_id)
                cur.execute("""UPDATE institutional_proposals SET current_revision=%s,lifecycle_status='DRAFT',
                    content_sha256=%s,updated_at=clock_timestamp() WHERE proposal_id=%s""",
                    (revision, digest, proposal_id))
                self._event(cur, proposal_id, revision, "proposal.revised",
                    idempotency_key or f"proposal-revision:{proposal_id}:{revision}", actor_id,
                    {"previous_revision": expected_revision, "content_sha256": digest})
            return self.get(proposal_id)
        except psycopg.Error as exc:
            if "UniqueViolation" in type(exc).__name__:
                raise ProposalConflict("proposal revision event already exists") from None
            raise ProposalError(type(exc).__name__) from None

    def transition(self, proposal_id, revision, new_status, *, actor_id, reason,
                   approved_purpose=None, authority_reference=None):
        actor_id = _text(actor_id, "actor identity", 256)
        reason = _text(reason, "transition reason", 1000)
        if new_status not in _LIFECYCLE:
            raise ProposalValidationError("invalid proposal lifecycle status")
        if new_status == "APPROVED":
            approved_purpose = _text(approved_purpose, "approved purpose", 1000)
            authority_reference = _text(authority_reference, "authority reference", 256)
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                cur.execute("""SELECT p.current_revision,r.lifecycle_status FROM institutional_proposals p
                    JOIN institutional_proposal_revisions r ON r.proposal_id=p.proposal_id
                    AND r.revision=%s WHERE p.proposal_id=%s FOR UPDATE OF p,r""",
                    (revision, proposal_id))
                row = cur.fetchone()
                if row is None:
                    raise ProposalNotFound("proposal revision not found")
                if row["current_revision"] != revision:
                    raise ProposalConflict("only the current proposal revision can transition")
                old = row["lifecycle_status"]
                if new_status not in _TRANSITIONS.get(old, set()):
                    raise ProposalConflict("proposal lifecycle transition is not allowed")
                cur.execute("UPDATE institutional_proposal_revisions SET lifecycle_status=%s WHERE proposal_id=%s AND revision=%s",
                            (new_status, proposal_id, revision))
                cur.execute("UPDATE institutional_proposals SET lifecycle_status=%s,updated_at=clock_timestamp() WHERE proposal_id=%s",
                            (new_status, proposal_id))
                payload = {"from": old, "to": new_status, "reason": reason}
                if new_status == "APPROVED":
                    payload.update({"approved_purpose": approved_purpose,
                                    "authority_reference": authority_reference})
                self._event(cur, proposal_id, revision, "proposal.lifecycle_changed",
                    f"proposal-transition:{proposal_id}:{revision}:{new_status}", actor_id, payload)
            return self.get(proposal_id, revision=revision)
        except psycopg.Error as exc:
            if "UniqueViolation" in type(exc).__name__:
                raise ProposalConflict("proposal transition already recorded") from None
            raise ProposalError(type(exc).__name__) from None

    def record_review(self, proposal_id, revision, *, reviewer_office, reviewer_principal,
                      outcome, findings, conditions=(), evidence_references=(),
                      authority_reference, idempotency_key):
        reviewer_office = _text(reviewer_office, "review office", 256)
        reviewer_principal = _text(reviewer_principal, "reviewer identity", 256)
        findings = _text(findings, "review findings", 4000)
        authority_reference = _text(authority_reference, "review authority reference", 256)
        idempotency_key = _text(idempotency_key, "review idempotency key", 240)
        if outcome not in _REVIEW_OUTCOMES:
            raise ProposalValidationError("invalid review outcome")
        conditions = _string_list(conditions, "review conditions", 24, 1000)
        evidence_references = _bounded_references(evidence_references, "review evidence")
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                cur.execute("SELECT 1 FROM institutional_proposal_revisions WHERE proposal_id=%s AND revision=%s",
                            (proposal_id, revision))
                if cur.fetchone() is None:
                    raise ProposalNotFound("proposal revision not found")
                cur.execute("""INSERT INTO institutional_proposal_reviews
                    (proposal_id,revision,reviewer_office,reviewer_principal,review_outcome,
                     findings,conditions,evidence_references,authority_reference,idempotency_key)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)
                    ON CONFLICT (idempotency_key) DO NOTHING RETURNING review_id""",
                    (proposal_id, revision, reviewer_office, reviewer_principal, outcome,
                     findings, self._json(conditions), self._json(evidence_references),
                     authority_reference, idempotency_key))
                inserted = cur.fetchone()
                if inserted is None:
                    cur.execute("""SELECT proposal_id,revision,reviewer_office,reviewer_principal,
                        review_outcome,findings,conditions,evidence_references,authority_reference
                        FROM institutional_proposal_reviews WHERE idempotency_key=%s""",
                                (idempotency_key,))
                    old = cur.fetchone()
                    if not old or (old["proposal_id"], old["revision"], old["reviewer_office"],
                            old["reviewer_principal"], old["review_outcome"], old["findings"],
                            old["conditions"], old["evidence_references"], old["authority_reference"]) != (
                            proposal_id, revision, reviewer_office, reviewer_principal, outcome,
                            findings, conditions, evidence_references, authority_reference):
                        raise ProposalConflict("review idempotency key is bound to another decision")
                    return self.get(proposal_id, revision=revision)
                self._event(cur, proposal_id, revision, "proposal.review_recorded", idempotency_key,
                    reviewer_principal, {"reviewer_office": reviewer_office,
                        "review_outcome": outcome, "conditions_count": len(conditions)})
            return self.get(proposal_id, revision=revision)
        except psycopg.Error as exc:
            if "UniqueViolation" in type(exc).__name__:
                raise ProposalConflict("proposal review already recorded") from None
            raise ProposalError(type(exc).__name__) from None

    def link_work_order(self, proposal_id, revision, *, objective_id, assignment_id,
                        approved_purpose, actor_id, authority_reference):
        """Append a provenance link only after existing intake confirms authorization."""
        actor_id = _text(actor_id, "linking actor", 256)
        approved_purpose = _text(approved_purpose, "approved purpose", 1000)
        authority_reference = _text(authority_reference, "authority reference", 256)
        if not isinstance(objective_id, str) or not objective_id.startswith("objective:"):
            raise ProposalValidationError("invalid objective identity")
        if not isinstance(assignment_id, str) or not assignment_id.startswith("assignment:"):
            raise ProposalValidationError("invalid assignment identity")
        try:
            with self.db.transaction(), self.db.cursor() as cur:
                self._path(cur)
                cur.execute("""SELECT lifecycle_status FROM institutional_proposal_revisions
                    WHERE proposal_id=%s AND revision=%s""", (proposal_id, revision))
                row = cur.fetchone()
                if row is None:
                    raise ProposalNotFound("proposal revision not found")
                if row["lifecycle_status"] != "APPROVED":
                    raise ProposalConflict("only a specifically approved proposal revision can link to work")
                cur.execute("""INSERT INTO institutional_proposal_work_orders
                    (proposal_id,proposal_revision,objective_id,assignment_id,approved_purpose,
                     linked_by,authority_reference) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (proposal_id, revision, objective_id, assignment_id, approved_purpose,
                     actor_id, authority_reference))
                self._event(cur, proposal_id, revision, "proposal.work_order_linked",
                    f"proposal-work-order:{proposal_id}:{revision}:{objective_id}:{assignment_id}",
                    actor_id, {"objective_id": objective_id, "assignment_id": assignment_id,
                               "approved_purpose": approved_purpose,
                               "authority_reference": authority_reference})
            return self.get(proposal_id, revision=revision)
        except psycopg.Error as exc:
            if "UniqueViolation" in type(exc).__name__:
                raise ProposalConflict("proposal work-order link already exists") from None
            raise ProposalError(type(exc).__name__) from None
