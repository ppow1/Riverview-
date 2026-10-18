# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/assignment_scheduler/scheduler.py
# Component: ASSIGNMENT-SCHEDULER
# Revision: 1.0.14
# Purpose: Claim ready assignments fairly and fence stale lease holders
# Execution Model: PostgreSQL transactional request interface
# Observability: Durable lease generations and causally linked ledger events
# Dependencies: Python 3.10+; Psycopg 3; POSTGRES-LEDGER schema and lease migration
# Authority: Does not validate grants or independently verify worker results
# Changed: 2026-10-10 UTC | RV-M2.1-001 | Add scope-filtered lease claim integration
# Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Allow a claim to be pinned to one assignment ID
# Contracts: docs/development/M1.4-001_REVISION_RECORD.md
# Changed: 2026-10-13 UTC | RV-LEDGER-GRAPH-POSITION | Persist canonical assignment lifecycle node on lease-bound transitions
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Fence Grace work-order claims to the capability persisted in the approved proposal step
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Preserve standalone scheduler operation before resident schema migration and map legacy bounded artifact worker to the Codex artifact plan capability
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Restrict the optional proposal capability filter to the currently selected schema contract
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Resolve persisted plan capability through the durable step-to-assignment link, not the mutable ledger status label
# Changed: 2026-10-18 UTC | RV-COMMS5-COMPLETION-20261017 | Enforce persisted Engineering worker-selection policy during transactional lease claims
# Changed: 2026-10-16 UTC | RV-GRACE-SCHEDULER-PROBE-COMPAT | Pass an explicit empty parameter tuple to the optional schema capability probe
# Changed: 2026-10-16 UTC | RV-GRACE-SCHEDULER-PROBE-COMPAT | Normalize assignment query parameters to the DB-API tuple contract
# Tests: tests/test_assignment_scheduler.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Fair PostgreSQL assignment claims with monotonically fenced lease generations."""

from datetime import timedelta

from psycopg.rows import dict_row

from ..ledger import TRANSITIONS
from ..postgres_ledger import PostgresLedger, assignment_process_position


class SchedulerError(RuntimeError):
    """Scheduler operation failed its durable contract."""


class StaleLeaseError(SchedulerError):
    """Lease owner, generation, or expiry no longer authorizes this operation."""


class PostgresAssignmentScheduler:
    """Claim ready work in age order and reject stale worker generations.

    The caller must explicitly apply this component's migration before use.
    Claims do not execute work, validate authority grants, or assert verification.
    """

    def __init__(self, dsn, *, schema="public"):
        self.ledger = PostgresLedger(dsn, schema=schema)
        self.schema = schema

    def close(self):
        self.ledger.close()

    @staticmethod
    def _validate_lease(worker_id, lease_seconds):
        if not worker_id or not worker_id.strip():
            raise ValueError("worker_id is required")
        if not isinstance(lease_seconds, (int, float)) or lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")

    @staticmethod
    def _policy_selected_worker(cur, scope_ref, required_capability):
        """Return the worker selected by an installed durable policy, if any."""
        if scope_ref != "work-order:engineering":
            return None
        cur.execute("SELECT to_regclass(current_schema() || '.resource_selection_policies') AS table_name", ())
        if not cur.fetchone()["table_name"]:
            return None
        cur.execute("""SELECT mode,parameters,last_selected_worker FROM
            resource_selection_policies WHERE policy_key='engineering'""")
        policy = cur.fetchone()
        if not policy or policy["mode"] == "automatic":
            return None
        cur.execute("""SELECT worker_id FROM worker_registry
            WHERE active=TRUE AND scope_ref='work-order:engineering'
              AND (%s::text IS NULL OR capabilities @> jsonb_build_array(%s::text))
            ORDER BY worker_id""", (required_capability, required_capability))
        eligible = [row["worker_id"] for row in cur.fetchall()]
        if not eligible:
            return ""  # Explicit policy with no eligible registered resource fails closed.
        params = policy["parameters"] or {}
        fallback = params.get("fallback", True)
        if policy["mode"] == "target":
            target = params.get("target_seat", "")
            if target in eligible:
                return target
            return eligible[0] if fallback else ""
        if policy["mode"] == "priority":
            ranked = [worker for worker in params.get("priority_order", [])
                      if worker in eligible]
            return ranked[0] if ranked else (eligible[0] if fallback else "")
        if policy["mode"] == "balanced":
            cur.execute("""SELECT wr.worker_id,count(l.assignment_id)::bigint AS active_leases
                FROM worker_registry wr LEFT JOIN assignment_leases l
                  ON l.worker_id=wr.worker_id AND l.expires_at>clock_timestamp()
                WHERE wr.worker_id=ANY(%s) GROUP BY wr.worker_id
                ORDER BY active_leases,wr.worker_id""", (eligible,))
            return cur.fetchone()["worker_id"]
        raise RuntimeError("resource_policy_mode_inconsistent")

    @staticmethod
    def _claim_candidate(cur, worker_id, lease_seconds, *, scope_ref=None,
                         assignment_id=None, required_capability=None):
        """Claim one eligible assignment in the caller's active transaction."""
        selected_worker = PostgresAssignmentScheduler._policy_selected_worker(
            cur, scope_ref, required_capability)
        if selected_worker is not None and selected_worker != worker_id:
            return None
        # The scheduler is also used by installations that have not enabled the
        # resident-objective schema. Only add proposal-scope fencing when that
        # existing contract is installed; an absent table cannot contain a
        # Grace objective assignment.
        cur.execute("SELECT to_regclass(current_schema() || '.grace_objectives') IS NOT NULL AS available", ())
        objective_contract = bool(cur.fetchone()["available"])
        capability_clause = ""
        parameters = [scope_ref, scope_ref, assignment_id, assignment_id]
        if objective_contract:
            capability_clause = """
                 AND (%s::text IS NULL OR a.workflow_id<>'grace.objective-work-order.v1'
                   OR EXISTS (
                     SELECT 1 FROM grace_objectives o
                     JOIN grace_objective_steps assigned_step
                       ON assigned_step.objective_id=o.objective_id
                     JOIN LATERAL jsonb_array_elements(o.proposal->'steps') AS step(value)
                       ON step.value->>'step_id'=assigned_step.step_id
                     WHERE o.objective_id=a.objective_ref
                       AND assigned_step.assignment_id=a.id
                       AND (COALESCE(step.value->>'execution_capability',
                               'engineering.codex-cli-artifact.v1')=%s
                            OR (%s='engineering.bounded-artifact.v1'
                                AND COALESCE(step.value->>'execution_capability',
                                    'engineering.codex-cli-artifact.v1')=
                                    'engineering.codex-cli-artifact.v1'))))"""
            parameters.extend((required_capability, required_capability, required_capability))
        cur.execute(
            """SELECT a.id,l.generation
               FROM assignments AS a
               LEFT JOIN assignment_leases AS l ON l.assignment_id=a.id
               WHERE a.state='ready'
                 AND (l.assignment_id IS NULL OR l.expires_at<=clock_timestamp())
                 AND (%s::text IS NULL OR a.authority_ref=%s)
                 AND (%s::text IS NULL OR a.id=%s)""" + capability_clause + """
               ORDER BY a.updated_at,a.id
               FOR UPDATE OF a SKIP LOCKED LIMIT 1""", tuple(parameters))
        assignment = cur.fetchone()
        if assignment is None:
            return None
        generation = (assignment["generation"] or 0) + 1
        cur.execute(
            """INSERT INTO assignment_leases
                   (assignment_id,worker_id,generation,acquired_at,heartbeat_at,expires_at)
               VALUES (%s,%s,%s,clock_timestamp(),clock_timestamp(),
                       clock_timestamp()+(%s * interval '1 second'))
               ON CONFLICT (assignment_id) DO UPDATE SET
                   worker_id=EXCLUDED.worker_id,
                   generation=EXCLUDED.generation,
                   acquired_at=EXCLUDED.acquired_at,
                   heartbeat_at=EXCLUDED.heartbeat_at,
                   expires_at=EXCLUDED.expires_at
               RETURNING assignment_id,worker_id,generation,acquired_at,heartbeat_at,expires_at""",
            (assignment["id"], worker_id, generation, lease_seconds))
        lease = cur.fetchone()
        if lease is not None and selected_worker is not None:
            cur.execute("""UPDATE resource_selection_policies SET
                last_selected_worker=%s,updated_at=clock_timestamp()
                WHERE policy_key='engineering'""", (worker_id,))
            cur.execute("""INSERT INTO resource_selection_policy_events
                (policy_key,revision,event_type,idempotency_key,actor_id,payload)
                SELECT 'engineering',revision,'worker_selected',%s,'service:assignment-scheduler',%s::jsonb
                FROM resource_selection_policies WHERE policy_key='engineering'
                ON CONFLICT(idempotency_key) DO NOTHING""",
                (f"resource-policy-select:{lease['assignment_id']}:{lease['generation']}",
                 __import__("json").dumps({"worker_id": worker_id,
                    "assignment_id": lease["assignment_id"],
                    "generation": lease["generation"]}, sort_keys=True)))
        return lease

    def claim_next(self, worker_id, *, lease_seconds=30, scope_ref=None,
                   assignment_id=None, required_capability=None):
        """Claim oldest eligible ready work, optionally within an exact authority scope."""
        self._validate_lease(worker_id, lease_seconds)
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                return self._claim_candidate(cur, worker_id, lease_seconds,
                                             scope_ref=scope_ref,
                                             assignment_id=assignment_id,
                                             required_capability=required_capability)

    def heartbeat(self, assignment_id, worker_id, generation, *, lease_seconds=30):
        """Extend only a currently active exact worker/generation lease.

        Lock the assignment first, matching claim/reclaim lock order, so a
        successful heartbeat cannot race with replacement by a newer generation.
        """
        self._validate_lease(worker_id, lease_seconds)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT id FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                if cur.fetchone() is None:
                    raise StaleLeaseError("assignment no longer exists")
                cur.execute(
                    """UPDATE assignment_leases
                       SET heartbeat_at=clock_timestamp(),
                           expires_at=clock_timestamp()+(%s * interval '1 second')
                       WHERE assignment_id=%s AND worker_id=%s AND generation=%s
                         AND expires_at>clock_timestamp()
                       RETURNING expires_at""",
                    (lease_seconds, assignment_id, worker_id, generation))
                row = cur.fetchone()
                if row is None:
                    raise StaleLeaseError("lease is absent, expired, or fenced by a newer generation")
                return row["expires_at"]

    def transition_with_lease(self, assignment_id, to_state, step, idempotency_key,
                              worker_id, generation, *, verified=False,
                              privacy_domain="institution"):
        """Apply any legal assignment transition only under the current lease token."""
        if not idempotency_key or not step or not worker_id:
            raise ValueError("idempotency key, step, and worker_id are required")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                assignment = cur.fetchone()
                if assignment is None:
                    raise SchedulerError("unknown assignment")
                cur.execute("SELECT worker_id,generation,expires_at FROM assignment_leases WHERE assignment_id=%s FOR UPDATE",
                            (assignment_id,))
                lease = cur.fetchone()
                cur.execute("SELECT clock_timestamp() AS now")
                now = cur.fetchone()["now"]
                if (lease is None or lease["worker_id"] != worker_id or
                        lease["generation"] != generation or lease["expires_at"] <= now):
                    raise StaleLeaseError("lease is absent, expired, or fenced by a newer generation")
                cur.execute("SELECT assignment_id,event_type,payload FROM events WHERE idempotency_key=%s",
                            (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    prior = existing["payload"]
                    graph_id, node_id = assignment_process_position(to_state)
                    if (existing["assignment_id"] != assignment_id or
                            existing["event_type"] != "assignment.transitioned" or
                            prior.get("to") != to_state or prior.get("step") != step or
                            prior.get("actor_id") != worker_id or
                            prior.get("verified_claim") is not bool(verified) or
                            prior.get("privacy_domain") != privacy_domain or
                            (("process_graph_id" in prior or "process_node_id" in prior) and
                             (prior.get("process_graph_id") != graph_id or
                              prior.get("process_node_id") != node_id))):
                        raise SchedulerError("idempotency key collision")
                    return self.ledger.get(assignment_id)
                payload = {"from": assignment["state"], "to": to_state, "step": step,
                           "actor_id": worker_id, "verified_claim": bool(verified),
                           "privacy_domain": privacy_domain}
                graph_id, node_id = assignment_process_position(to_state)
                payload.update({"process_graph_id": graph_id, "process_node_id": node_id})
                if to_state not in TRANSITIONS[assignment["state"]]:
                    raise SchedulerError(f"invalid transition: {assignment['state']} -> {to_state}")
                if to_state == "completed" and not verified:
                    raise SchedulerError("completion requires independently verified evidence")
                cur.execute("SELECT event_id FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                            (assignment_id,))
                cause = cur.fetchone()["event_id"]
                cur.execute("""UPDATE assignments SET state=%s,workflow_step=%s,
                    process_graph_id=%s,process_node_id=%s,updated_at=clock_timestamp(),
                    version=version+1 WHERE id=%s""",
                    (to_state, step, graph_id, node_id, assignment_id))
                self.ledger._append_event(
                    cur, assignment_id=assignment_id, event_type="assignment.transitioned",
                    idempotency_key=idempotency_key, actor_id=worker_id,
                    authority_ref=assignment["authority_ref"],
                    correlation_id=assignment["correlation_id"], causation_id=cause,
                    payload_schema="rv.assignment.transitioned.v1", payload=payload,
                    privacy_domain=privacy_domain)
        return self.ledger.get(assignment_id)

    def start_assignment(self, assignment_id, worker_id, generation):
        """Start work with a current token, emitting one causal ledger event."""
        return self.transition_with_lease(
            assignment_id, "running", f"worker:{worker_id}:execution",
            f"scheduler:start:{assignment_id}:{generation}", worker_id, generation)
