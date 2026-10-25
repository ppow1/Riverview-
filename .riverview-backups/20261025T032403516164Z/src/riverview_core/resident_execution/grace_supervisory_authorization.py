"""Steward-approved financial envelope for Luna supervisory requests."""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime
import json
import re
from uuid import NAMESPACE_URL, uuid5


SCOPE = {"functions": ["cme_diagnostic_recovery", "performance_evaluation"],
         "provider_id": "gpt-6-luna"}
TOTAL_BUDGET = Decimal("5.00000000")
PER_REQUEST_LIMIT = Decimal("0.05000000")


class GraceSupervisoryAuthorization:
    def __init__(self, pipeline, authority_registry):
        self.pipeline = pipeline
        self.ledger = pipeline.ledger
        self.authority_registry = authority_registry

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
