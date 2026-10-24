"""One exact authenticated standing authorization for the Grace/Luna r2 experiment."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import re
from uuid import NAMESPACE_URL, UUID, uuid5


OBJECTIVE_ID = "objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2"
OBJECTIVE_REVISION = 2
SOURCE_EVENT_ID = "c7558b01-8004-4a44-8344-4bf0fe0ae27e"
EXPERIMENT_KEY = "grace-autonomy-luna-r2"
ACTION = "grace.experiment.execute"
TOTAL_BUDGET_USD = 5.0
PRIOR_SPEND_USD = 0.04104010
MAX_RECOVERY_ATTEMPTS = 5
MAX_LUNA_REQUESTS = 2
AMENDED_MAX_LUNA_REQUESTS = 4
AMENDED_REQUEST_ALLOCATIONS = {
    "cme_diagnostic_recovery": 1,
    "performance_evaluation": 1,
}
DURATION = timedelta(hours=24)


class GraceExperimentAuthorization:
    def __init__(self, pipeline, authority_registry):
        self.pipeline = pipeline
        self.ledger = pipeline.ledger
        self.authority_registry = authority_registry

    @staticmethod
    def scope_ref(objective_id=OBJECTIVE_ID, revision=OBJECTIVE_REVISION):
        return f"grace-autonomy:{objective_id}"

    def activate(self, *, actor_id, objective_id, revision, idempotency_key):
        if (actor_id != "steward:camrui" or objective_id != OBJECTIVE_ID or
                revision != OBJECTIVE_REVISION or not isinstance(idempotency_key, str) or
                not re.fullmatch(r"[A-Za-z0-9._:-]{8,200}", idempotency_key)):
            raise ValueError("experiment_authorization_scope_invalid")
        objective = self.pipeline.get_objective(objective_id)
        if (objective is None or objective["revision"] != revision or
                objective["status"] != "GROUNDED"):
            raise ValueError("experiment_objective_not_eligible")
        criterion = "An eligible disposable diagnostic objective is promoted only following explicit Steward approval of the exact proposal revision and digest."
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            if not self.pipeline.proposal_promotion_evidence(cur, objective_id, criterion):
                raise PermissionError("exact_approved_proposal_evidence_required")
            cur.execute("""SELECT 1 FROM cme_monitor_events
                WHERE event_id=%s AND event_type='grace_objective_blocked'
                  AND details->>'objective_id'=%s
                  AND (details->>'objective_revision')::integer=%s""",
                (SOURCE_EVENT_ID, objective_id, revision))
            if cur.fetchone() is None:
                raise PermissionError("exact_block_escalation_evidence_required")
        try:
            luna_grant = self.authority_registry.active_grace_luna_escalation_grant()
        except Exception as exc:
            from ..institutional_authority import AuthorityDenied
            if isinstance(exc, AuthorityDenied):
                raise PermissionError("active_grace_luna_escalation_grant_required") from None
            raise
        now = datetime.now(timezone.utc)
        requested_expiry = now + DURATION
        authorization_id = uuid5(NAMESPACE_URL, "riverview:grace-experiment:" + idempotency_key)
        grant_id = "grant:grace-autonomy:" + str(authorization_id)
        scope_ref = self.scope_ref(objective_id, revision)
        with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""INSERT INTO grace_experiment_authorizations
                (authorization_id,experiment_key,objective_id,objective_revision,source_event_id,
                 authority_grant_id,luna_authority_grant_id,authorized_by,authority_reference,idempotency_key,
                 total_budget_usd,prior_spend_usd,max_recovery_attempts,max_luna_requests,
                 expires_at,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
                ON CONFLICT (idempotency_key) DO NOTHING""",
                (authorization_id, EXPERIMENT_KEY, objective_id, revision, SOURCE_EVENT_ID,
                 grant_id, luna_grant["grant_id"], actor_id,
                 "authenticated-comms5-steward", idempotency_key, TOTAL_BUDGET_USD,
                 PRIOR_SPEND_USD, MAX_RECOVERY_ATTEMPTS, MAX_LUNA_REQUESTS, requested_expiry))
            cur.execute("""SELECT * FROM grace_experiment_authorizations
                WHERE idempotency_key=%s FOR UPDATE""", (idempotency_key,))
            auth = cur.fetchone()
            if (auth is None or auth["authorization_id"] != authorization_id or
                    auth["objective_id"] != objective_id or auth["objective_revision"] != revision or
                    auth["authority_grant_id"] != grant_id or auth["authorized_by"] != actor_id or
                    auth["luna_authority_grant_id"] != luna_grant["grant_id"] or
                    auth["total_budget_usd"] != TOTAL_BUDGET_USD or
                    auth["prior_spend_usd"] != PRIOR_SPEND_USD or
                    auth["max_recovery_attempts"] != MAX_RECOVERY_ATTEMPTS or
                    auth["max_luna_requests"] != MAX_LUNA_REQUESTS):
                raise ValueError("experiment_authorization_idempotency_conflict")
            if auth["status"] in {"revoked", "expired"}:
                raise ValueError("experiment_authorization_not_active")
            idempotent_replay = auth["status"] == "active"
            expires_at = auth["expires_at"]
        try:
            grant_id = self.authority_registry.issue_grace_autonomy_experiment_grant(
                actor_id=actor_id, grant_id=grant_id, scope_ref=scope_ref,
                valid_until=expires_at)
        except Exception as exc:
            from ..institutional_authority import AuthorityDenied
            if isinstance(exc, AuthorityDenied):
                raise PermissionError("authority_registry_rejected_steward_grant") from None
            raise
        with self.ledger.db.transaction(), self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""UPDATE grace_experiment_authorizations SET status='active'
                WHERE authorization_id=%s AND status='pending' AND expires_at>clock_timestamp()""",
                (authorization_id,))
            cur.execute("""INSERT INTO grace_experiment_authorization_events
                (authorization_id,event_type,idempotency_key,objective_id,payload)
                VALUES (%s,'activated',%s,%s,%s::jsonb)
                ON CONFLICT (idempotency_key) DO NOTHING""",
                (authorization_id, "grace-experiment-activated:" + str(authorization_id),
                 objective_id, json.dumps({"grant_id": grant_id, "revision": revision,
                    "total_budget_usd": TOTAL_BUDGET_USD, "prior_spend_usd": PRIOR_SPEND_USD,
                    "max_recovery_attempts": MAX_RECOVERY_ATTEMPTS,
                    "max_luna_requests": MAX_LUNA_REQUESTS,
                    "expires_at": expires_at.isoformat()}, sort_keys=True)))
            cur.execute("""SELECT status FROM grace_experiment_authorizations
                WHERE authorization_id=%s""", (authorization_id,))
            if cur.fetchone()["status"] != "active":
                raise ValueError("experiment_authorization_activation_failed")
        return {"status": "active", "authorization_id": str(authorization_id),
            "authority_grant_id": grant_id, "objective_id": objective_id,
            "objective_revision": revision, "scope_ref": scope_ref,
            "total_budget_usd": TOTAL_BUDGET_USD, "prior_spend_usd": PRIOR_SPEND_USD,
            "max_recovery_attempts": MAX_RECOVERY_ATTEMPTS,
            "max_luna_requests": MAX_LUNA_REQUESTS, "expires_at": expires_at.isoformat(),
            "idempotent_replay": idempotent_replay}

    def amend_luna_request_limit(self, *, actor_id, authorization_id, objective_id,
            revision, expected_max_luna_requests, new_max_luna_requests,
            expected_used_luna_requests, expected_used_recoveries,
            expected_cumulative_spend_usd, total_budget_usd, expires_at,
            explicit_steward_confirmation, idempotency_key):
        """Append one authenticated, exact-scope request-limit amendment."""
        if (actor_id != "steward:camrui" or explicit_steward_confirmation is not True or
                objective_id != OBJECTIVE_ID or revision != OBJECTIVE_REVISION or
                expected_max_luna_requests != MAX_LUNA_REQUESTS or
                new_max_luna_requests != AMENDED_MAX_LUNA_REQUESTS or
                expected_used_luna_requests != 2 or expected_used_recoveries != 4 or
                Decimal(str(total_budget_usd)) != Decimal("5.00000000") or
                Decimal(str(expected_cumulative_spend_usd)) != Decimal("0.04183460") or
                not isinstance(idempotency_key, str) or
                not re.fullmatch(r"grace-autonomy-luna-r2-amend-20261024", idempotency_key)):
            raise ValueError("experiment_amendment_scope_invalid")
        try:
            authorization_uuid = UUID(str(authorization_id))
            expected_expiry = datetime.fromisoformat(expires_at)
        except (ValueError, TypeError, AttributeError):
            raise ValueError("experiment_amendment_identity_invalid") from None
        if expected_expiry.tzinfo is None:
            raise ValueError("experiment_amendment_expiry_invalid")
        from psycopg import sql
        scope_ref = self.scope_ref(objective_id, revision)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT * FROM grace_experiment_authorizations
                    WHERE authorization_id=%s FOR UPDATE""", (authorization_uuid,))
                auth = cur.fetchone()
                if (auth is None or auth["objective_id"] != objective_id or
                        auth["objective_revision"] != revision or auth["status"] != "active" or
                        auth["total_budget_usd"] != Decimal("5.00000000") or
                        auth["prior_spend_usd"] != Decimal("0.04104010") or
                        auth["max_recovery_attempts"] != 5 or auth["expires_at"] != expected_expiry or
                        auth["expires_at"] <= datetime.now(timezone.utc)):
                    raise PermissionError("active_experiment_authorization_mismatch")

                cur.execute("""SELECT
                    count(*) FILTER (WHERE event_type='luna_reserved') AS reserved,
                    count(*) FILTER (WHERE event_type='luna_settled') AS settled,
                    count(*) FILTER (WHERE event_type='recovery_claimed') AS recoveries,
                    COALESCE(sum((payload->>'cost_usd')::numeric)
                        FILTER (WHERE event_type='luna_settled'),0) AS luna_spend,
                    COALESCE((SELECT sum((reserved.payload->>'reserved_cost_usd')::numeric)
                        FROM grace_experiment_authorization_events reserved
                        WHERE reserved.authorization_id=%s AND reserved.event_type='luna_reserved'
                          AND NOT EXISTS (SELECT 1 FROM grace_experiment_authorization_events paid
                            WHERE paid.authorization_id=reserved.authorization_id
                              AND paid.event_type='luna_settled' AND paid.request_id=reserved.request_id)),0)
                        AS outstanding
                    FROM grace_experiment_authorization_events
                    WHERE authorization_id=%s""", (authorization_uuid, authorization_uuid))
                usage = cur.fetchone()
                cumulative = auth["prior_spend_usd"] + usage["luna_spend"]

                cur.execute(sql.SQL("SELECT {}.active_grace_autonomy_experiment_grant(%s,%s) AS grant_id").format(
                    sql.Identifier(self.authority_registry.schema)),
                    (auth["authority_grant_id"], scope_ref))
                active_grant = cur.fetchone()
                if not active_grant or active_grant["grant_id"] != auth["authority_grant_id"]:
                    raise PermissionError("active_experiment_authority_grant_required")
                cur.execute(sql.SQL("SELECT {}.active_grace_luna_escalation_grant() AS grant_id").format(
                    sql.Identifier(self.authority_registry.schema)))
                active_luna = cur.fetchone()
                if (not active_luna or
                        active_luna["grant_id"] != auth["luna_authority_grant_id"]):
                    raise PermissionError("active_grace_luna_escalation_grant_required")

                cur.execute("""SELECT event_id,payload FROM grace_experiment_authorization_events
                    WHERE authorization_id=%s AND event_type='amended' AND idempotency_key=%s""",
                    (authorization_uuid, idempotency_key))
                prior = cur.fetchone()
                if prior:
                    payload = prior["payload"]
                    if (auth["max_luna_requests"] != AMENDED_MAX_LUNA_REQUESTS or
                            payload.get("new_max_luna_requests") != AMENDED_MAX_LUNA_REQUESTS or
                            payload.get("additional_request_allocations") != AMENDED_REQUEST_ALLOCATIONS or
                            payload.get("objective_id") != objective_id or
                            payload.get("objective_revision") != revision or
                            int(usage["reserved"]) > AMENDED_MAX_LUNA_REQUESTS or
                            int(usage["recoveries"]) > 5 or
                            cumulative + usage["outstanding"] > auth["total_budget_usd"]):
                        raise ValueError("experiment_amendment_idempotency_conflict")
                    return {"status": "active", "authorization_id": str(authorization_uuid),
                        "amendment_event_id": str(prior["event_id"]),
                        "objective_id": objective_id, "objective_revision": revision,
                        "max_luna_requests": AMENDED_MAX_LUNA_REQUESTS,
                        "used_luna_requests": int(usage["reserved"]),
                        "remaining_luna_requests": AMENDED_MAX_LUNA_REQUESTS - int(usage["reserved"]),
                        "max_recovery_attempts": 5, "used_recoveries": int(usage["recoveries"]),
                        "total_budget_usd": float(auth["total_budget_usd"]),
                        "cumulative_spend_usd": float(cumulative),
                        "expires_at": auth["expires_at"].isoformat(), "idempotent_replay": True}
                if (auth["max_luna_requests"] != MAX_LUNA_REQUESTS or
                        int(usage["reserved"]) != expected_used_luna_requests or
                        int(usage["settled"]) != expected_used_luna_requests or
                        int(usage["recoveries"]) != expected_used_recoveries or
                        cumulative != Decimal(str(expected_cumulative_spend_usd)) or
                        usage["outstanding"] != 0):
                    raise PermissionError("experiment_amendment_usage_precondition_failed")

                payload = {"authorization_id": str(authorization_uuid),
                    "objective_id": objective_id, "objective_revision": revision,
                    "authorized_by": actor_id,
                    "authority_reference": "authenticated-comms5-steward-amendment",
                    "previous_max_luna_requests": MAX_LUNA_REQUESTS,
                    "new_max_luna_requests": AMENDED_MAX_LUNA_REQUESTS,
                    "additional_request_allocations": AMENDED_REQUEST_ALLOCATIONS,
                    "used_luna_requests": int(usage["reserved"]),
                    "remaining_luna_requests": AMENDED_MAX_LUNA_REQUESTS - int(usage["reserved"]),
                    "max_recovery_attempts": 5, "used_recoveries": int(usage["recoveries"]),
                    "total_budget_usd": float(auth["total_budget_usd"]),
                    "prior_spend_usd": float(auth["prior_spend_usd"]),
                    "luna_spend_usd": float(usage["luna_spend"]),
                    "cumulative_spend_usd": float(cumulative),
                    "expires_at": auth["expires_at"].isoformat(),
                    "explicit_steward_confirmation": True}
                cur.execute("""UPDATE grace_experiment_authorizations
                    SET max_luna_requests=%s WHERE authorization_id=%s
                      AND status='active' AND max_luna_requests=%s
                    RETURNING authorization_id""",
                    (AMENDED_MAX_LUNA_REQUESTS, authorization_uuid, MAX_LUNA_REQUESTS))
                if cur.fetchone() is None:
                    raise PermissionError("experiment_amendment_concurrent_change")
                cur.execute("""INSERT INTO grace_experiment_authorization_events
                    (authorization_id,event_type,idempotency_key,objective_id,payload)
                    VALUES (%s,'amended',%s,%s,%s::jsonb)""",
                    (authorization_uuid, idempotency_key, objective_id,
                     json.dumps(payload, sort_keys=True)))
                cur.execute("""SELECT event_id FROM grace_experiment_authorization_events
                    WHERE authorization_id=%s AND event_type='amended' AND idempotency_key=%s""",
                    (authorization_uuid, idempotency_key))
                amendment_event_id = cur.fetchone()["event_id"]
        return {"status": "active", "authorization_id": str(authorization_uuid),
            "amendment_event_id": str(amendment_event_id),
            "objective_id": objective_id, "objective_revision": revision,
            "max_luna_requests": AMENDED_MAX_LUNA_REQUESTS,
            "used_luna_requests": expected_used_luna_requests,
            "remaining_luna_requests": AMENDED_MAX_LUNA_REQUESTS - expected_used_luna_requests,
            "max_recovery_attempts": 5, "used_recoveries": expected_used_recoveries,
            "total_budget_usd": 5.0, "cumulative_spend_usd": 0.04183460,
            "expires_at": expected_expiry.isoformat(), "idempotent_replay": False}
