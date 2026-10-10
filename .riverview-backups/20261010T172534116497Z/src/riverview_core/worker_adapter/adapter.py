# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/adapter.py
# Component: WORKER-ADAPTER
# Revision: 1.0.3
# Purpose: Authenticate a scoped local worker and persist deterministic attempts/results
# Execution Model: Request-driven local task execution with PostgreSQL durability
# Observability: Worker identity, capability, attempt outcome, and result digest
# Dependencies: Python 3.10+; Psycopg 3; M1.2 ledger and M1.4 assignment lease
# Authority: No arbitrary commands, shell execution, or external effects
# Changed: 2026-10-10 UTC | RV-M1.3-CONTINUOUS-KNOWLEDGE | Persist grounding and preflight provenance
# Contracts: docs/components/WORKER_ADAPTER.md; docs/architecture/CORE_CONTRACT.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Capability-scoped worker registration and a safe deterministic local task."""

import hashlib
import hmac
import json
import secrets
from uuid import uuid4

from psycopg.rows import dict_row

from ..postgres_ledger import PostgresLedger
from ..assignment_scheduler import PostgresAssignmentScheduler


class WorkerAdapterError(RuntimeError):
    """Worker attempt or persistence contract failure."""


class WorkerAuthorizationError(WorkerAdapterError):
    """Worker credential, capability, or assignment scope was rejected."""


class WorkerLeaseLost(WorkerAdapterError):
    """The worker lease expired or was fenced before its result committed."""


class PostgresWorkerAdapter:
    """Register scoped workers and execute only approved deterministic tasks.

    The registration credential is returned once and stored only as a SHA-256
    digest. Provisioning/registration remains a trusted control-plane operation.
    """

    SHA256_CAPABILITY = "deterministic.sha256.v1"

    def __init__(self, dsn, *, schema="public"):
        self.ledger = PostgresLedger(dsn, schema=schema)
        self.scheduler = PostgresAssignmentScheduler(dsn, schema=schema)
        self.schema = schema

    def close(self):
        self.scheduler.close()
        self.ledger.close()

    def register_worker(self, worker_id, capabilities, scope_ref):
        """Create a scoped worker and return its one-time bearer credential."""
        if not worker_id or not scope_ref:
            raise ValueError("worker_id and scope_ref are required")
        caps = sorted(set(capabilities or []))
        if not caps or any(not isinstance(cap, str) or not cap.strip() for cap in caps):
            raise ValueError("at least one non-empty capability is required")
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO worker_registry
                    (worker_id,credential_sha256,capabilities,scope_ref)
                    VALUES (%s,%s,%s,%s)""",
                    (worker_id, digest, json.dumps(caps), scope_ref))
        return token

    def _authenticated_worker(self, cur, worker_id, credential, capability):
        if not isinstance(credential, str) or not credential:
            raise WorkerAuthorizationError("worker authentication failed")
        cur.execute("SELECT credential_sha256,capabilities,scope_ref,active FROM worker_registry WHERE worker_id=%s FOR SHARE",
                    (worker_id,))
        row = cur.fetchone()
        candidate = hashlib.sha256(credential.encode("utf-8")).digest()
        if row is None or not hmac.compare_digest(bytes(row["credential_sha256"]), candidate):
            raise WorkerAuthorizationError("worker authentication failed")
        if not row["active"]:
            raise WorkerAuthorizationError("worker is inactive")
        if capability not in row["capabilities"]:
            raise WorkerAuthorizationError("worker capability is not registered")
        return row["scope_ref"]

    def _authorized_worker(self, cur, worker_id, credential, capability, authority_ref):
        scope_ref = self._authenticated_worker(cur, worker_id, credential, capability)
        if scope_ref != authority_ref:
            raise WorkerAuthorizationError("worker scope does not match assignment authority")

    def claim_next(self, worker_id, credential, *, capability=None, lease_seconds=30):
        """Authenticate and claim only ready work inside the worker's scope."""
        capability = capability or self.SHA256_CAPABILITY
        self.scheduler._validate_lease(worker_id, lease_seconds)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                scope_ref = self._authenticated_worker(cur, worker_id, credential, capability)
                lease = self.scheduler._claim_candidate(
                    cur, worker_id, lease_seconds, scope_ref=scope_ref)
                if lease is None:
                    return None
                cur.execute("SELECT * FROM assignments WHERE id=%s", (lease["assignment_id"],))
                return {"lease": lease, "assignment": cur.fetchone()}

    def start_assignment(self, assignment_id, worker_id, credential, generation,
                         *, capability=None):
        """Authenticate scope before using the M1.4 fenced start transition."""
        capability = capability or self.SHA256_CAPABILITY
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT authority_ref FROM assignments WHERE id=%s", (assignment_id,))
                row = cur.fetchone()
                if row is None:
                    raise WorkerAdapterError("unknown assignment")
                self._authorized_worker(cur, worker_id, credential, capability,
                                        row["authority_ref"])
        return self.scheduler.start_assignment(assignment_id, worker_id, generation)

    def record_knowledge_observation(self, assignment_id, worker_id, operation,
                                     result, *, action=None):
        """Persist knowledge status and provenance, never provider payload/secrets."""
        from .knowledge import KnowledgeResult
        if not isinstance(result, KnowledgeResult):
            raise TypeError("result must be a KnowledgeResult")
        if operation not in {"ground_assignment", "preflight_action",
                             "reground_assignment", "record_learning"}:
            raise ValueError("unknown knowledge operation")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""INSERT INTO knowledge_observations
                    (assignment_id,worker_id,operation,status,action,source_references,
                     source_revision,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING observation_id""",
                    (assignment_id, worker_id, operation, result.status.value, action,
                     json.dumps(list(result.source_references)), result.source_revision,
                     result.source_sha256))
                return cur.fetchone()["observation_id"]

    def execute_sha256(self, assignment_id, worker_id, credential, generation,
                       idempotency_key, data):
        """Hash explicit UTF-8 input, retaining attempt/result provenance.

        Input text is not stored. The attempt stores only its digest. The task has
        no subprocess, shell, network, filesystem, or hardware side effects.
        """
        if not isinstance(data, str) or not idempotency_key:
            raise ValueError("text data and idempotency_key are required")
        raw = data.encode("utf-8")
        input_digest = hashlib.sha256(raw).hexdigest()
        capability = self.SHA256_CAPABILITY
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                assignment = cur.fetchone()
                if assignment is None:
                    raise WorkerAdapterError("unknown assignment")
                self._authorized_worker(cur, worker_id, credential, capability,
                                        assignment["authority_ref"])
                cur.execute("SELECT worker_id,generation,expires_at FROM assignment_leases WHERE assignment_id=%s FOR UPDATE",
                            (assignment_id,))
                lease = cur.fetchone()
                cur.execute("SELECT clock_timestamp() AS now")
                now = cur.fetchone()["now"]
                if (assignment["state"] != "running" or lease is None or
                        lease["worker_id"] != worker_id or lease["generation"] != generation or
                        lease["expires_at"] <= now):
                    raise WorkerLeaseLost("active assignment lease is required")
                cur.execute("""SELECT attempt_id,status,assignment_id,worker_id,
                                      lease_generation,capability,input_sha256
                               FROM worker_attempts WHERE idempotency_key=%s""",
                            (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    if (existing["assignment_id"] != assignment_id or
                            existing["worker_id"] != worker_id or
                            existing["lease_generation"] != generation or
                            existing["capability"] != capability or
                            existing["input_sha256"].strip() != input_digest):
                        raise WorkerAdapterError("idempotency key collision")
                    if existing["status"] != "succeeded":
                        raise WorkerAdapterError("idempotent attempt is still incomplete")
                    cur.execute("SELECT result,result_sha256 FROM worker_results WHERE attempt_id=%s",
                                (existing["attempt_id"],))
                    saved = cur.fetchone()
                    return {"attempt_id": existing["attempt_id"], "status": "succeeded",
                            "result": saved["result"], "result_sha256": saved["result_sha256"]}
                attempt_id = uuid4()
                cur.execute("""INSERT INTO worker_attempts
                    (attempt_id,assignment_id,worker_id,lease_generation,capability,
                     idempotency_key,input_sha256,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'running')""",
                    (attempt_id, assignment_id, worker_id, generation, capability,
                     idempotency_key, input_digest))

        # This deterministic local computation intentionally runs outside the DB
        # transaction; lease ownership is checked again before durable result commit.
        result = {"sha256": input_digest, "utf8_bytes": len(raw)}
        result_digest = hashlib.sha256(json.dumps(result, sort_keys=True,
                                                  separators=(",", ":")).encode()).hexdigest()
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT id FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                cur.execute("SELECT worker_id,generation,expires_at FROM assignment_leases WHERE assignment_id=%s FOR UPDATE",
                            (assignment_id,))
                lease = cur.fetchone()
                cur.execute("SELECT clock_timestamp() AS now")
                now = cur.fetchone()["now"]
                if (lease is None or lease["worker_id"] != worker_id or
                        lease["generation"] != generation or lease["expires_at"] <= now):
                    cur.execute("UPDATE worker_attempts SET status='lease_lost',finished_at=clock_timestamp(),failure_class='WorkerLeaseLost' WHERE attempt_id=%s AND status='running'",
                                (attempt_id,))
                    lost = True
                else:
                    cur.execute("INSERT INTO worker_results(attempt_id,result,result_sha256) VALUES (%s,%s,%s)",
                                (attempt_id, json.dumps(result, sort_keys=True), result_digest))
                    cur.execute("UPDATE worker_attempts SET status='succeeded',finished_at=clock_timestamp() WHERE attempt_id=%s AND status='running'",
                                (attempt_id,))
                    lost = False
        if lost:
            raise WorkerLeaseLost("lease was fenced before result commit")
        return {"attempt_id": attempt_id, "status": "succeeded",
                "result": result, "result_sha256": result_digest}

    def incomplete_attempts(self):
        """List durable unfinished work for worker-loss detection and reconciliation."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT attempt_id,assignment_id,worker_id,lease_generation,
                                  capability,started_at
                           FROM worker_attempts WHERE status='running'
                           ORDER BY started_at,attempt_id""")
            return cur.fetchall()
