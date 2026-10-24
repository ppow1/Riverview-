"""One exact authenticated standing authorization for the Grace/Luna r2 experiment."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
from uuid import NAMESPACE_URL, uuid5


OBJECTIVE_ID = "objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2"
OBJECTIVE_REVISION = 2
SOURCE_EVENT_ID = "c7558b01-8004-4a44-8344-4bf0fe0ae27e"
EXPERIMENT_KEY = "grace-autonomy-luna-r2"
ACTION = "grace.experiment.execute"
TOTAL_BUDGET_USD = 5.0
PRIOR_SPEND_USD = 0.04104010
MAX_RECOVERY_ATTEMPTS = 5
MAX_LUNA_REQUESTS = 2
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
            luna_grant = self.pipeline.authorizer.require_principal(
                cur, "resident:grace", "resident.reasoning.escalate", "provider:gpt-6-luna")
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
