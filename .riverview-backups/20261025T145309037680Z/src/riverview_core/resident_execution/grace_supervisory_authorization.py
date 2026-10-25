# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/grace_supervisory_authorization.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.0.6
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REPLAY-CORRELATION-20261025 | Bind the one-use S4 exception to the locked live revision and current assignment pointer instead of historical constants.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REWORK-EXCEPTION-20261025 | Require the exact replayed S4 evaluation and durable feedback consumption before issuing the one-use attempt.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-REWORK-EXCEPTION-20261025 | Add one expiring exact-verification S4 rework exception using append-only single-use objective events.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Require all authorization tuple fields to match on idempotent replay.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Validate the approved parent assignment alongside the current S3 child pointer.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Require exact revision and root-assignment scope in retry availability checks.
# Purpose: Bind Luna supervisory calls and event-scoped retry exceptions to Steward authority
# Execution Model: Request-driven PostgreSQL authorization
# Observability: Append-only supervisory authorization events
# Dependencies: PostgreSQL ledger; AuthorityRegistry active-grant function
# Authority: Existing $5/$0.05 Luna grant; a diagnostic exception is exact-event, expiring, and single-use
# Changed: 2026-10-25 UTC | RV-GRACE-S3-EVENT-RETRY-20261025 | Record one approved retry for the exact S3 stall.
# Contracts: docs/components/EXTERNAL_REASONING_EXCHANGE.md
# Tests: tests/test_external_reasoning_exchange.py
# History: Git and .riverview-backups/manifest.jsonl
"""Steward-approved financial envelope for Luna supervisory requests."""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta, timezone
import json
import re
from uuid import NAMESPACE_URL, UUID, uuid5


SCOPE = {"functions": ["cme_diagnostic_recovery", "performance_evaluation"],
         "provider_id": "gpt-6-luna"}
TOTAL_BUDGET = Decimal("5.00000000")
PER_REQUEST_LIMIT = Decimal("0.05000000")

S3_RETRY_OBJECTIVE_ID = "objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2"
S3_RETRY_OBJECTIVE_REVISION = 8
S3_RETRY_OBJECTIVE_ASSIGNMENT_ID = (
    "assignment:grace:de19cd78b86f1889d32cdf02c6d3fe51d4658834")
S3_RETRY_STALL_EVENT_ID = "8671a141-da3c-47c5-960d-324e3c51eeef"
S3_RETRY_PROGRESS_SEQUENCE = 223
S3_RETRY_EVENT_ASSIGNMENT_ID = (
    S3_RETRY_OBJECTIVE_ASSIGNMENT_ID + ":step:41242b9fae56fad4")
S3_RETRY_GRANT_KEY = "grace-supervision:cme-retry-authorized:" + S3_RETRY_STALL_EVENT_ID
S3_RETRY_GRANT_LIFETIME = timedelta(minutes=30)

S4_REWORK_OBJECTIVE_ID = S3_RETRY_OBJECTIVE_ID
S4_REWORK_ROOT_ASSIGNMENT_ID = S3_RETRY_OBJECTIVE_ASSIGNMENT_ID
S4_REWORK_ASSIGNMENT_ID = (
    S4_REWORK_ROOT_ASSIGNMENT_ID + ":step:5b840157e7e86aef")
S4_REWORK_VERIFICATION_ID = "54d1fb2f-411e-4771-a137-785d2b620de7"
S4_REWORK_EVALUATION_REQUEST_ID = "98ca464e-23b8-5511-8ca0-cd8c528cdffa"
S4_REWORK_EXCEPTION_IDEMPOTENCY_KEY = (
    "grace-s4-rework-authorized:" + S4_REWORK_VERIFICATION_ID)


class GraceSupervisoryAuthorization:
    def __init__(self, pipeline, authority_registry):
        self.pipeline = pipeline
        self.ledger = pipeline.ledger
        self.authority_registry = authority_registry

    def authorize_one_s3_cme_retry(self, *, actor_id, authorization_id,
            objective_id, objective_revision, objective_assignment_id,
            stall_event_id, progress_sequence, explicit_steward_confirmation):
        """Append the approved one-use exception for the fixed S3 stall only."""
        if (actor_id != "steward:camrui" or explicit_steward_confirmation is not True or
                objective_id != S3_RETRY_OBJECTIVE_ID or
                objective_revision != S3_RETRY_OBJECTIVE_REVISION or
                objective_assignment_id != S3_RETRY_OBJECTIVE_ASSIGNMENT_ID or
                stall_event_id != S3_RETRY_STALL_EVENT_ID or
                progress_sequence != S3_RETRY_PROGRESS_SEQUENCE):
            raise PermissionError("cme_retry_exception_scope_mismatch")
        try:
            authorization_uuid = UUID(str(authorization_id))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("grace_supervisory_authorization_identity_invalid") from None
        from psycopg import sql

        with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT * FROM grace_supervisory_authorizations
                WHERE authorization_id=%s FOR UPDATE""", (authorization_uuid,))
            auth = cur.fetchone()
            if (auth is None or auth["status"] != "active" or
                    auth["total_budget_usd"] != TOTAL_BUDGET or
                    auth["per_request_limit_usd"] != PER_REQUEST_LIMIT or
                    auth["scope"] != SCOPE or
                    (auth["valid_until"] is not None and
                     auth["valid_until"] <= datetime.now(timezone.utc))):
                raise PermissionError("active_grace_supervisory_authorization_required")
            cur.execute(sql.SQL("SELECT {}.active_grace_supervisory_luna_grant(%s) AS grant_id").format(
                sql.Identifier(self.authority_registry.schema)), (auth["authority_grant_id"],))
            linked = cur.fetchone()
            if not linked or linked["grant_id"] != auth["authority_grant_id"]:
                raise PermissionError("active_grace_supervisory_authority_grant_required")
            cur.execute("""SELECT e.assignment_id,s.step_id,s.status AS step_status,
                    a.state AS assignment_state,o.status AS objective_status,
                    o.revision AS objective_revision,o.assignment_id AS objective_assignment_id
                FROM cme_monitor_events e
                JOIN assignments a ON a.id=e.assignment_id
                JOIN grace_objective_steps s ON s.assignment_id=a.id
                JOIN grace_objectives o ON o.objective_id=s.objective_id
                JOIN assignments root ON root.id=%s
                    AND root.objective_ref=o.objective_id
                WHERE e.event_id=%s AND e.event_type='assignment_stalled'
                  AND s.objective_id=%s AND s.step_id='s3'
                  AND e.assignment_id=%s AND e.details->>'state'='rework_required'
                  AND (e.details->>'progress_seq')::integer=%s
                  AND a.objective_ref=o.objective_id
                  AND o.assignment_id=a.id
                  AND a.state='rework_required' AND s.status='assigned'
                  AND o.status='WORK_ORDER_CREATED' AND o.revision=%s
                """, (objective_assignment_id, UUID(stall_event_id), objective_id,
                    S3_RETRY_EVENT_ASSIGNMENT_ID, progress_sequence, objective_revision))
            facts = cur.fetchone()
            if facts is None:
                raise PermissionError("current_s3_stall_facts_do_not_match_approval")
            now = datetime.now(timezone.utc)
            expires_at = now + S3_RETRY_GRANT_LIFETIME
            event_payload = {
                "schema": "rv.grace.cme-retry-exception.v1",
                "authorized_by": actor_id,
                "approval_reference": "Steward-directed Codex instruction",
                "objective_id": objective_id,
                "objective_revision": objective_revision,
                "objective_assignment_id": objective_assignment_id,
                "assignment_id": S3_RETRY_EVENT_ASSIGNMENT_ID,
                "step_id": "s3",
                "stall_event_id": stall_event_id,
                "progress_sequence": progress_sequence,
                "request_type": "cme_diagnostic_recovery",
                "max_attempts": 1,
                "per_request_limit_usd": format(PER_REQUEST_LIMIT, ".8f"),
                "expires_at": expires_at.isoformat(),
            }
            cur.execute("""INSERT INTO grace_supervisory_authorization_events
                (authorization_id,event_type,idempotency_key,objective_id,payload)
                VALUES (%s,'cme_retry_authorized',%s,%s,%s::jsonb)
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING event_id""",
                (authorization_uuid, S3_RETRY_GRANT_KEY, objective_id,
                 json.dumps(event_payload, sort_keys=True)))
            event = cur.fetchone()
            if event is None:
                cur.execute("""SELECT event_id,objective_id,payload FROM grace_supervisory_authorization_events
                    WHERE authorization_id=%s AND event_type='cme_retry_authorized'
                      AND idempotency_key=%s""", (authorization_uuid, S3_RETRY_GRANT_KEY))
                existing = cur.fetchone()
                existing_payload = existing["payload"] if existing else {}
                if (existing is None or existing["objective_id"] != objective_id or
                        existing_payload.get("authorized_by") != actor_id or
                        existing_payload.get("objective_id") != objective_id or
                        existing_payload.get("objective_revision") != objective_revision or
                        existing_payload.get("objective_assignment_id") != objective_assignment_id or
                        existing_payload.get("assignment_id") != S3_RETRY_EVENT_ASSIGNMENT_ID or
                        existing_payload.get("step_id") != "s3" or
                        existing_payload.get("stall_event_id") != stall_event_id or
                        existing_payload.get("progress_sequence") != progress_sequence or
                        existing_payload.get("request_type") != "cme_diagnostic_recovery" or
                        existing_payload.get("max_attempts") != 1 or
                        existing_payload.get("per_request_limit_usd") != format(PER_REQUEST_LIMIT, ".8f")):
                    raise PermissionError("cme_retry_exception_idempotency_conflict")
                return {"status": "already_recorded", "event_id": str(existing["event_id"]),
                    "expires_at": existing_payload.get("expires_at")}
            return {"status": "authorized", "event_id": str(event["event_id"]),
                "authorization_id": str(authorization_uuid), "objective_id": objective_id,
                "assignment_id": S3_RETRY_EVENT_ASSIGNMENT_ID,
                "stall_event_id": stall_event_id, "progress_sequence": progress_sequence,
                "max_attempts": 1, "per_request_limit_usd": format(PER_REQUEST_LIMIT, ".8f"),
                "expires_at": expires_at.isoformat()}

    def authorize_one_s4_rework_attempt(self, *, actor_id, objective_id,
            objective_revision, objective_assignment_id, assignment_id,
            verification_id, assignment_credential, explicit_steward_confirmation):
        """Record one exact S4 rework authorization without changing normal retry limits."""
        if (actor_id != "steward:camrui" or explicit_steward_confirmation is not True or
                objective_id != S4_REWORK_OBJECTIVE_ID or
                type(objective_revision) is not int or objective_revision < 1 or
                not isinstance(objective_assignment_id, str) or not objective_assignment_id or
                assignment_id != S4_REWORK_ASSIGNMENT_ID or
                verification_id != S4_REWORK_VERIFICATION_ID):
            raise PermissionError("s4_rework_exception_scope_mismatch")
        evidence_reader = getattr(self.pipeline,
            "performance_evaluation_runtime_evidence_for_assignment", None)
        evidence = evidence_reader(objective_id, assignment_id) if callable(evidence_reader) else None
        if (not isinstance(evidence, dict) or
                evidence.get("schema") !=
                    "rv.grace.performance-evaluation-runtime-evidence.v1" or
                evidence.get("objective_id") != objective_id or
                evidence.get("assignment_id") != assignment_id or
                not isinstance(evidence.get("exchange"), dict) or
                evidence["exchange"].get("request_id") !=
                    S4_REWORK_EVALUATION_REQUEST_ID or
                evidence["exchange"].get("delivery_state") != "grace_consumed" or
                not isinstance(evidence.get("evaluation"), dict) or
                evidence["evaluation"].get("feedback_consumed") is not True or
                evidence["evaluation"].get("authority_granted") is not False):
            raise PermissionError("s4_durable_performance_evaluation_required")
        with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT o.status,o.revision,o.assignment_id AS objective_assignment_id,
                    a.id AS assignment_id,a.state AS assignment_state,a.objective_ref,
                    s.step_id,s.status AS step_status
                FROM grace_objectives o JOIN assignments a ON a.id=%s
                    AND a.objective_ref=o.objective_id
                JOIN grace_objective_steps s ON s.objective_id=o.objective_id
                    AND s.assignment_id=a.id
                WHERE o.objective_id=%s AND s.step_id='s4'
                FOR UPDATE OF o,a,s""", (assignment_id, objective_id))
            state = cur.fetchone()
            if (state is None or state["revision"] != objective_revision or
                    state["objective_assignment_id"] != objective_assignment_id or
                    state["assignment_id"] != assignment_id or
                    state["objective_ref"] != objective_id):
                raise PermissionError("active_exact_assignment_create_grant_required")
            cur.execute("SELECT authority_ref FROM assignments WHERE id=%s",
                (assignment_id,))
            assignment_scope = cur.fetchone()
            if (assignment_scope is None or not self.pipeline.assignment_intake.authorizer.require(
                    cur, assignment_credential, self.pipeline.assignment_intake.ACTION,
                    assignment_scope["authority_ref"])):
                raise PermissionError("active_exact_assignment_create_grant_required")
            cur.execute("""SELECT verification_id::text AS verification_id,decision
                FROM verification_records WHERE assignment_id=%s
                ORDER BY recorded_at DESC,verification_id DESC LIMIT 1""",
                (assignment_id,))
            latest = cur.fetchone()
            cur.execute("""SELECT count(*) AS attempts FROM grace_objective_events
                WHERE objective_id=%s AND event_type='engineering.rework_decided'
                  AND payload->>'assignment_id'=%s
                  AND payload->>'decision'='REWORK_PROPOSED'""",
                (objective_id, assignment_id))
            attempt_count = cur.fetchone()["attempts"]
            cur.execute("""SELECT 1 FROM grace_objective_events
                WHERE objective_id=%s AND event_type='engineering.rework_escalation_pending'
                  AND payload->>'assignment_id'=%s AND payload->>'verification_id'=%s
                  AND payload->>'reason_code'='retry_limit_exhausted' LIMIT 1""",
                (objective_id, assignment_id, verification_id))
            exhausted_hold = cur.fetchone() is not None
            if (not state or state["status"] != "WORK_ORDER_CREATED" or
                    state["revision"] != objective_revision or
                    state["assignment_id"] != objective_assignment_id or
                    state["objective_ref"] != objective_id or
                    state["assignment_state"] != "rework_required" or
                    state["step_status"] != "assigned" or not latest or
                    latest["verification_id"] != verification_id or
                    latest["decision"] != "REJECTED" or
                    attempt_count != 3 or not exhausted_hold):
                raise PermissionError("current_exhausted_s4_rejection_does_not_match_approval")
            expires_at = datetime.now(timezone.utc) + S3_RETRY_GRANT_LIFETIME
            payload = {"schema": "rv.grace.rework-retry-exception.v1",
                "authorized_by": actor_id,
                "approval_reference": "Steward-directed Codex instruction",
                "objective_id": objective_id,
                "objective_revision": objective_revision,
                "objective_assignment_id": objective_assignment_id,
                "assignment_id": assignment_id, "step_id": "s4",
                "verification_id": verification_id,
                "prior_rework_attempts": attempt_count,
                "additional_attempts": 1,
                "expires_at": expires_at.isoformat(),
                "independent_verification_required": True}
            cur.execute("""INSERT INTO grace_objective_events
                (objective_id,event_type,idempotency_key,actor_id,payload)
                VALUES (%s,'engineering.rework_retry_authorized',%s,%s,%s::jsonb)
                ON CONFLICT (idempotency_key) DO NOTHING RETURNING event_id""",
                (objective_id, S4_REWORK_EXCEPTION_IDEMPOTENCY_KEY, actor_id,
                 json.dumps(payload, sort_keys=True)))
            event = cur.fetchone()
            if event is None:
                cur.execute("""SELECT event_id::text AS event_id,payload
                    FROM grace_objective_events WHERE objective_id=%s
                      AND idempotency_key=%s""",
                    (objective_id, S4_REWORK_EXCEPTION_IDEMPOTENCY_KEY))
                existing = cur.fetchone()
                if not existing or dict(existing["payload"]) != payload:
                    raise PermissionError("s4_rework_exception_idempotency_conflict")
                return {"status": "already_recorded", "event_id": existing["event_id"],
                    "expires_at": payload["expires_at"]}
            return {"status": "authorized", "event_id": str(event["event_id"]),
                "objective_id": objective_id, "assignment_id": assignment_id,
                "verification_id": verification_id, "prior_rework_attempts": 3,
                "additional_attempts": 1, "expires_at": expires_at.isoformat()}

    def cme_retry_exception_available(self, *, authorization_id, objective_id,
            objective_revision, assignment_id, stall_event_id, progress_sequence):
        """Read whether the exact one-use event authorization remains unconsumed."""
        cur = self.ledger.db.cursor()
        try:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT 1 FROM grace_supervisory_authorization_events g
                WHERE g.authorization_id=%s AND g.event_type='cme_retry_authorized'
                  AND g.objective_id=%s AND g.payload->>'assignment_id'=%s
                  AND g.payload->>'objective_assignment_id'=%s
                  AND g.payload->>'step_id'='s3'
                  AND g.payload->>'stall_event_id'=%s
                  AND (g.payload->>'objective_revision')::integer=%s
                  AND (g.payload->>'progress_sequence')::integer=%s
                  AND (g.payload->>'expires_at')::timestamptz>clock_timestamp()
                  AND NOT EXISTS (SELECT 1 FROM grace_supervisory_authorization_events c
                    WHERE c.authorization_id=g.authorization_id
                      AND c.event_type='cme_retry_consumed'
                      AND c.payload->>'grant_event_id'=g.event_id::text)""",
                (UUID(str(authorization_id)), objective_id, assignment_id,
                 S3_RETRY_OBJECTIVE_ASSIGNMENT_ID,
                 stall_event_id, objective_revision, progress_sequence))
            return cur.fetchone() is not None
        finally:
            cur.close()

    def authorize(self, *, actor_id, total_budget_usd, per_request_limit_usd,
                  explicit_steward_confirmation, idempotency_key, expires_at=None):
        if (not isinstance(actor_id, str) or not actor_id.startswith("steward:") or
                explicit_steward_confirmation is not True or
                Decimal(str(total_budget_usd)) != TOTAL_BUDGET or
                Decimal(str(per_request_limit_usd)) != PER_REQUEST_LIMIT or
                not isinstance(idempotency_key, str) or
                not re.fullmatch(r"[A-Za-z0-9._:-]{8,200}", idempotency_key)):
            raise ValueError("grace_supervisory_authorization_scope_invalid")
        if expires_at is not None:
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except (ValueError, TypeError):
                raise ValueError("grace_supervisory_expiry_invalid") from None
            if expires_at.tzinfo is None:
                raise ValueError("grace_supervisory_expiry_invalid")
        auth_id = uuid5(NAMESPACE_URL, "riverview:grace-supervision:" + idempotency_key)
        grant_id = "grant:grace-supervision:" + str(auth_id)
        with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""INSERT INTO grace_supervisory_authorizations
                (authorization_id,authority_grant_id,authorized_by,idempotency_key,
                 total_budget_usd,per_request_limit_usd,scope,valid_until,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,'pending')
                ON CONFLICT (idempotency_key) DO NOTHING""",
                (auth_id, grant_id, actor_id, idempotency_key, TOTAL_BUDGET,
                 PER_REQUEST_LIMIT, json.dumps(SCOPE, sort_keys=True), expires_at))
            cur.execute("SELECT * FROM grace_supervisory_authorizations WHERE idempotency_key=%s FOR UPDATE",
                        (idempotency_key,))
            row = cur.fetchone()
            if (row is None or row["authorization_id"] != auth_id or
                    row["authority_grant_id"] != grant_id or row["authorized_by"] != actor_id or
                    row["total_budget_usd"] != TOTAL_BUDGET or
                    row["per_request_limit_usd"] != PER_REQUEST_LIMIT or row["scope"] != SCOPE):
                raise ValueError("grace_supervisory_authorization_idempotency_conflict")
            if row["valid_until"] != expires_at:
                raise ValueError("grace_supervisory_authorization_idempotency_conflict")
            if row["status"] == "revoked":
                raise PermissionError("grace_supervisory_authorization_revoked")
        grant_id = self.authority_registry.issue_grace_supervisory_luna_grant(
            actor_id=actor_id, grant_id=grant_id, valid_until=None)
        with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""UPDATE grace_supervisory_authorizations SET status='active',
                    activated_at=COALESCE(activated_at,clock_timestamp())
                WHERE authorization_id=%s AND status IN ('pending','active')""", (auth_id,))
            cur.execute("""INSERT INTO grace_supervisory_authorization_events
                (authorization_id,event_type,idempotency_key,payload)
                VALUES (%s,'activated',%s,%s::jsonb) ON CONFLICT (idempotency_key) DO NOTHING""",
                (auth_id, "grace-supervision-activated:" + str(auth_id),
                 json.dumps({"authority_grant_id": grant_id, "scope": SCOPE,
                    "total_budget_usd": str(TOTAL_BUDGET),
                    "per_request_limit_usd": str(PER_REQUEST_LIMIT),
                    "expires_at": None}, sort_keys=True)))
            cur.execute("SELECT status,activated_at FROM grace_supervisory_authorizations WHERE authorization_id=%s",
                        (auth_id,))
            state = cur.fetchone()
            if not state or state["status"] != "active":
                raise ValueError("grace_supervisory_authorization_activation_failed")
        return {"status": "active", "authorization_id": str(auth_id),
            "authority_grant_id": grant_id, "scope": SCOPE,
            "total_budget_usd": format(TOTAL_BUDGET, ".8f"),
            "per_request_limit_usd": format(PER_REQUEST_LIMIT, ".8f"),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "idempotent_replay": row["status"] == "active"}

    def status(self):
        from psycopg import sql
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT a.authorization_id,a.authority_grant_id,a.authorized_by,
                    a.total_budget_usd,a.per_request_limit_usd,a.scope,a.status,a.activated_at,a.valid_until,
                    COALESCE(sum((e.payload->>'cost_usd')::numeric)
                        FILTER (WHERE e.event_type='luna_settled'
                          AND COALESCE((e.payload->>'cost_is_reserved_estimate')::boolean,false)=false),0) AS spent,
                    COALESCE(sum((e.payload->>'cost_usd')::numeric)
                        FILTER (WHERE e.event_type='luna_settled'
                          AND COALESCE((e.payload->>'cost_is_reserved_estimate')::boolean,false)=true),0) AS unresolved,
                    COALESCE(sum((e.payload->>'reserved_cost_usd')::numeric)
                        FILTER (WHERE e.event_type='luna_reserved' AND NOT EXISTS (
                            SELECT 1 FROM grace_supervisory_authorization_events s
                            WHERE s.authorization_id=e.authorization_id AND s.event_type='luna_settled'
                              AND s.request_id=e.request_id)),0) AS outstanding,
                    count(*) FILTER (WHERE e.event_type='luna_reserved') AS requests
                FROM grace_supervisory_authorizations a
                LEFT JOIN grace_supervisory_authorization_events e USING (authorization_id)
                GROUP BY a.authorization_id ORDER BY a.created_at DESC LIMIT 1""")
            row = cur.fetchone()
            if row is not None:
                cur.execute(sql.SQL("SELECT {}.active_grace_supervisory_luna_grant(%s) AS grant_id").format(
                    sql.Identifier(self.authority_registry.schema)), (row["authority_grant_id"],))
                linked_grant_active = cur.fetchone()["grant_id"] == row["authority_grant_id"]
        if row is None:
            return {"status": "not_authorized"}
        spent = row["spent"]
        unresolved = row["unresolved"]
        outstanding = row["outstanding"]
        state = row["status"]
        if state == "active" and not linked_grant_active:
            state = "revoked_or_inactive"
        if state == "active" and row["valid_until"] is not None and row["valid_until"] <= datetime.now().astimezone():
            state = "expired"
        return {"authorization_id": str(row["authorization_id"]),
            "authority_grant_id": row["authority_grant_id"], "status": state,
            "authority_grant_active": linked_grant_active,
            "scope": row["scope"], "total_budget_usd": format(row["total_budget_usd"], ".8f"),
            "per_request_limit_usd": format(row["per_request_limit_usd"], ".8f"),
            "spent_usd": format(spent, ".8f"),
            "unresolved_cost_usd": format(unresolved, ".8f"),
            "reserved_usd": format(outstanding, ".8f"),
            "available_usd": format(row["total_budget_usd"] - spent - unresolved - outstanding, ".8f"),
            "request_count": int(row["requests"]), "expires_at": row["valid_until"].isoformat()
                if row["valid_until"] else None}

    def revoke(self, *, actor_id, authorization_id, explicit_steward_confirmation,
               idempotency_key):
        if (not isinstance(actor_id, str) or not actor_id.startswith("steward:") or
                explicit_steward_confirmation is not True or
                not re.fullmatch(r"[A-Za-z0-9._:-]{8,200}", str(idempotency_key))):
            raise ValueError("grace_supervisory_revocation_scope_invalid")
        from psycopg import sql
        schema = self.authority_registry.schema
        with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("SELECT authority_grant_id,status FROM grace_supervisory_authorizations WHERE authorization_id=%s FOR UPDATE",
                        (authorization_id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError("grace_supervisory_authorization_not_found")
            cur.execute(sql.SQL("SELECT {}.revoke_grace_supervisory_luna_grant(%s,%s)").format(
                sql.Identifier(schema)), (actor_id, row["authority_grant_id"]))
            cur.execute("UPDATE grace_supervisory_authorizations SET status='revoked' WHERE authorization_id=%s",
                        (authorization_id,))
            cur.execute("""INSERT INTO grace_supervisory_authorization_events
                (authorization_id,event_type,idempotency_key,payload)
                VALUES (%s,'revoked',%s,%s::jsonb) ON CONFLICT (idempotency_key) DO NOTHING""",
                (authorization_id, idempotency_key,
                 json.dumps({"authorized_by": actor_id}, sort_keys=True)))
        return {"status": "revoked", "authorization_id": str(authorization_id)}
