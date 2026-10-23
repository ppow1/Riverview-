# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/adapter.py
# Component: WORKER-ADAPTER
# Revision: 1.0.23
# Changed: 2026-10-22 UTC | RIVERVIEW-COMFYUI-ENGINEERING-INTEGRATION | Add ComfyUI capability to an existing worker only after rechecking its exact registration grant.
# Purpose: Authenticate fixed engineering-test work under exact assignment grants
# Execution Model: Request-driven local task execution with PostgreSQL durability
# Observability: Worker identity, capability, attempt outcome, and result digest
# Dependencies: Python 3.10+; Psycopg 3; M1.2 ledger and M1.4 assignment lease
# Authority: No arbitrary commands, shell execution, or external effects
# Changed: 2026-10-10 UTC | RV-M2.3-001 | Persist execution intent before worker actions
# Changed: 2026-10-11 UTC | RV-M4.1-GRANT-ENFORCEMENT-FIX | Use one exact institutional credential at each worker action boundary
# Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Persist bounded JSON artifacts under an exact local-inference capability
# Changed: 2026-10-11 UTC | RV-M33-ENGINEERING-ARTIFACT | Map the fixed repository test capability to assignment.execute
# Changed: 2026-10-11 UTC | RV-M33-INDEPENDENT-CAPABILITY-EVIDENCE | Include execution capability in verifier evidence input
# Changed: 2026-10-11 UTC | RV-M4.4-BOUNDED-ARTIFACT-WORKER | Allow exact-grant execution for bounded file-artifact workers
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Map bounded Codex artifact work to exact assignment.execute grant
# Changed: 2026-10-13 UTC | RV-SUPERVISED-CODEX-DISPATCH-001 | Pass an exact assignment pin through the authorized claim
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-001 | Register the separate scoped Codex source-change capability under exact assignment.execute authority
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001 | Select only exact-scope, expired-lease WAITING_FOR_EVIDENCE assignments after current worker authorization
# Changed: 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Expose authenticated worker scope to recovery before side effects
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Permit an append-only new-revision verifier decision for a previously rejected immutable attempt
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Append verifier-revision decisions while retaining prior rejection and exact grant checks
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Pass exact registered worker capability into Grace proposal-step claim fencing
# Contracts: docs/components/WORKER_ADAPTER.md; docs/architecture/CORE_CONTRACT.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Capability-scoped worker registration and a safe deterministic local task."""

import hashlib
import hmac
import json
from uuid import uuid4

from psycopg.rows import dict_row

from ..postgres_ledger import PostgresLedger
from ..assignment_scheduler import PostgresAssignmentScheduler
from ..institutional_authority import (ExactGrantAuthorizer,
                                       GrantCheckUnavailable, GrantDenied)
from .verifier import VerificationResult, VerificationStatus


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
    LOCAL_INFERENCE_CAPABILITY = "local.inference.v1"
    COMFYUI_CAPABILITY = "engineering.comfyui-image.v1"
    REPOSITORY_CHECK_CAPABILITY = "engineering.repository-check.v1"
    BOUNDED_ARTIFACT_CAPABILITY = "engineering.bounded-artifact.v1"
    CODEX_CLI_CAPABILITY = "engineering.codex-cli-artifact.v1"
    CODEX_SOURCE_CHANGE_CAPABILITY = "engineering.codex-cli-source-change.v1"
    VERIFICATION_CAPABILITY = "assignment.verify.v1"

    def __init__(self, dsn, *, schema="public", authority_schema=None):
        self.dsn = dsn
        self.ledger = PostgresLedger(dsn, schema=schema)
        self.scheduler = PostgresAssignmentScheduler(dsn, schema=schema)
        self.schema = schema
        self.authorizer = ExactGrantAuthorizer(authority_schema or schema)

    def close(self):
        self.scheduler.close()
        self.ledger.close()

    def register_worker(self, worker_id, capabilities, scope_ref, *, credential=None):
        """Register a worker only with a Steward-issued exact registration grant.

        The supplied credential is returned unchanged and stored only as a
        digest. It must be issued for this institutional principal and scope.
        """
        if not worker_id or not scope_ref:
            raise ValueError("worker_id and scope_ref are required")
        caps = sorted(set(capabilities or []))
        if not caps or any(not isinstance(cap, str) or not cap.strip() for cap in caps):
            raise ValueError("at least one non-empty capability is required")
        if not isinstance(credential, str) or len(credential) < 32:
            raise WorkerAuthorizationError("a grant-bound worker credential is required")
        digest = hashlib.sha256(credential.encode("utf-8")).digest()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                self._require_grant(cur, credential, "worker.register", scope_ref)
                cur.execute("""INSERT INTO worker_registry
                    (worker_id,credential_sha256,capabilities,scope_ref)
                    VALUES (%s,%s,%s,%s)""",
                    (worker_id, digest, json.dumps(caps), scope_ref))
        return credential

    def register_comfyui_capability(self, worker_id, credential, scope_ref):
        """Add the one ComfyUI capability to an existing worker under worker.register.

        This does not create an identity, change its scope, reactivate a worker, or
        widen the operation-to-grant mapping. Assignment claims still require the
        same credential's exact ``assignment.execute`` grant.
        """
        capability = self.COMFYUI_CAPABILITY
        if not worker_id or not scope_ref or not isinstance(credential, str) or len(credential) < 32:
            raise WorkerAuthorizationError("ComfyUI worker registration input is invalid")
        candidate = hashlib.sha256(credential.encode("utf-8")).digest()
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT credential_sha256,capabilities,scope_ref,active FROM worker_registry "
                            "WHERE worker_id=%s FOR UPDATE", (worker_id,))
                row = cur.fetchone()
                if (row is None or not hmac.compare_digest(bytes(row["credential_sha256"]), candidate) or
                        not row["active"] or row["scope_ref"] != scope_ref):
                    raise WorkerAuthorizationError("worker registration identity mismatch")
                self._require_grant(cur, credential, "worker.register", scope_ref)
                capabilities = row["capabilities"]
                if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
                    raise WorkerAdapterError("worker capability registry is invalid")
                if capability not in capabilities:
                    cur.execute("UPDATE worker_registry SET capabilities=%s WHERE worker_id=%s",
                                (json.dumps(sorted(set(capabilities) | {capability})), worker_id))
        return capability in capabilities or capability == self.COMFYUI_CAPABILITY

    def _require_grant(self, cur, credential, action, scope_ref):
        try:
            return self.authorizer.require(cur, credential, action, scope_ref)
        except GrantDenied as exc:
            raise WorkerAuthorizationError(str(exc)) from None
        except GrantCheckUnavailable:
            raise WorkerAdapterError("institutional authority registry is unavailable") from None

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
        if capability == self.VERIFICATION_CAPABILITY:
            action = "assignment.verify"
        elif capability in {self.SHA256_CAPABILITY, self.LOCAL_INFERENCE_CAPABILITY,
                            self.REPOSITORY_CHECK_CAPABILITY,
                            self.BOUNDED_ARTIFACT_CAPABILITY,
                            self.CODEX_CLI_CAPABILITY,
                            self.CODEX_SOURCE_CHANGE_CAPABILITY,
                            self.COMFYUI_CAPABILITY}:
            action = "assignment.execute"
        else:
            raise WorkerAuthorizationError("capability has no authority action mapping")
        self._require_grant(cur, credential, action, row["scope_ref"])
        return row["scope_ref"]

    def _authorized_worker(self, cur, worker_id, credential, capability, authority_ref):
        scope_ref = self._authenticated_worker(cur, worker_id, credential, capability)
        if scope_ref != authority_ref:
            raise WorkerAuthorizationError("worker scope does not match assignment authority")

    def authenticated_scope(self, worker_id, credential, capability):
        """Return a worker scope only after validating its current exact grant."""
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                return self._authenticated_worker(cur, worker_id, credential, capability)

    def claim_next(self, worker_id, credential, *, capability=None, lease_seconds=30,
                   assignment_id=None):
        """Authenticate and claim only ready work inside the worker's scope."""
        capability = capability or self.SHA256_CAPABILITY
        self.scheduler._validate_lease(worker_id, lease_seconds)
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                scope_ref = self._authenticated_worker(cur, worker_id, credential, capability)
                lease = self.scheduler._claim_candidate(
                    cur, worker_id, lease_seconds, scope_ref=scope_ref,
                    assignment_id=assignment_id, required_capability=capability)
                if lease is None:
                    return None
                cur.execute("SELECT * FROM assignments WHERE id=%s", (lease["assignment_id"],))
                return {"lease": lease, "assignment": cur.fetchone()}

    def waiting_for_evidence(self, worker_id, credential, *, capability, limit=1):
        """Read bounded blocked work only after revalidating the worker's exact grant."""
        if (capability != self.CODEX_CLI_CAPABILITY or type(limit) is not int or
                not 1 <= limit <= 10):
            raise ValueError("waiting evidence recovery is limited to bounded Codex claims")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                scope_ref = self._authenticated_worker(cur, worker_id, credential, capability)
                cur.execute("""SELECT a.* FROM assignments a
                    LEFT JOIN assignment_leases l ON l.assignment_id=a.id
                    WHERE a.state='blocked' AND a.workflow_step='WAITING_FOR_EVIDENCE'
                      AND a.authority_ref=%s
                      AND (l.assignment_id IS NULL OR l.expires_at<=clock_timestamp())
                    ORDER BY a.updated_at,a.id FOR UPDATE OF a SKIP LOCKED LIMIT %s""",
                    (scope_ref, limit))
                return cur.fetchall()

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

    def begin_execution_intent(self, assignment_id, worker_id, credential, generation,
                               idempotency_key, *, effect_class, capability=None):
        """Durably classify an action before invoking its execution callback.

        ``retry_safe`` may be replayed after lease expiry. ``external_uncertain``
        is never automatically replayed after an interrupted outcome.
        """
        if effect_class not in {"retry_safe", "external_uncertain"}:
            raise ValueError("effect_class must be retry_safe or external_uncertain")
        if not idempotency_key:
            raise ValueError("idempotency_key is required")
        capability = capability or self.SHA256_CAPABILITY
        db = self.ledger.db
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                assignment = cur.fetchone()
                if assignment is None:
                    raise WorkerAdapterError("unknown assignment")
                self._authorized_worker(cur, worker_id, credential,
                                        capability, assignment["authority_ref"])
                cur.execute("SELECT worker_id,generation,expires_at FROM assignment_leases WHERE assignment_id=%s FOR UPDATE",
                            (assignment_id,))
                lease = cur.fetchone()
                cur.execute("SELECT clock_timestamp() AS now")
                now = cur.fetchone()["now"]
                if (assignment["state"] != "running" or lease is None or
                        lease["worker_id"] != worker_id or lease["generation"] != generation or
                        lease["expires_at"] <= now):
                    raise WorkerLeaseLost("active assignment lease is required")
                cur.execute("""SELECT intent_id,assignment_id,worker_id,lease_generation,
                                      capability,effect_class,status FROM worker_execution_intents
                               WHERE idempotency_key=%s FOR UPDATE""", (idempotency_key,))
                prior = cur.fetchone()
                if prior:
                    if (prior["assignment_id"] != assignment_id or
                            prior["worker_id"] != worker_id or
                            prior["lease_generation"] != generation or
                            prior["capability"] != capability or
                            prior["effect_class"] != effect_class):
                        raise WorkerAdapterError("execution intent idempotency collision")
                    return prior["intent_id"]
                cur.execute("""INSERT INTO worker_execution_intents
                    (assignment_id,worker_id,lease_generation,capability,effect_class,
                     idempotency_key,status)
                    VALUES (%s,%s,%s,%s,%s,%s,'running') RETURNING intent_id""",
                    (assignment_id, worker_id, generation, capability,
                     effect_class, idempotency_key))
                return cur.fetchone()["intent_id"]

    def execute_artifact(self, assignment_id, worker_id, credential, generation,
                         idempotency_key, input_data, result, *, capability,
                         intent_id=None):
        """Persist a bounded JSON result artifact under a registered capability.

        Input is represented only by its digest. Result JSON is canonicalized and
        stored with a separately recomputable digest. The active lease and exact
        worker grant are checked both before attempt creation and before result
        commit, so a stale worker cannot publish after revocation/fencing.
        """
        if (not isinstance(input_data, str) or not idempotency_key or
                not isinstance(capability, str) or not capability or
                not isinstance(result, dict)):
            raise ValueError("text input, capability, idempotency key, and object result are required")
        raw = input_data.encode("utf-8")
        if len(raw) > 65536:
            raise ValueError("artifact input exceeds 65536 bytes")
        input_digest = hashlib.sha256(raw).hexdigest()
        try:
            result_json = json.dumps(result, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False)
            result_bytes = result_json.encode("utf-8")
        except (TypeError, ValueError):
            raise ValueError("result must be finite JSON data") from None
        if len(result_bytes) > 65536:
            raise ValueError("result artifact exceeds 65536 bytes")
        result_digest = hashlib.sha256(result_bytes).hexdigest()
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
                    if saved is None:
                        raise WorkerAdapterError("successful attempt has no result artifact")
                    if saved["result_sha256"].strip() != result_digest:
                        raise WorkerAdapterError("idempotent result differs from saved artifact")
                    if intent_id is not None:
                        cur.execute("""UPDATE worker_execution_intents
                            SET attempt_id=%s,status='succeeded',finished_at=clock_timestamp()
                            WHERE intent_id=%s AND assignment_id=%s AND worker_id=%s
                              AND lease_generation=%s AND capability=%s AND status='running'""",
                            (existing["attempt_id"], intent_id, assignment_id,
                             worker_id, generation, capability))
                        if cur.rowcount != 1:
                            raise WorkerAdapterError("execution intent is absent or no longer current")
                    return {"attempt_id": existing["attempt_id"], "status": "succeeded",
                            "result": saved["result"], "result_sha256": saved["result_sha256"]}
                attempt_id = uuid4()
                cur.execute("""INSERT INTO worker_attempts
                    (attempt_id,assignment_id,worker_id,lease_generation,capability,
                     idempotency_key,input_sha256,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'running')""",
                    (attempt_id, assignment_id, worker_id, generation, capability,
                     idempotency_key, input_digest))
                if intent_id is not None:
                    cur.execute("""UPDATE worker_execution_intents SET attempt_id=%s
                        WHERE intent_id=%s AND assignment_id=%s AND worker_id=%s
                          AND lease_generation=%s AND capability=%s AND status='running'""",
                        (attempt_id, intent_id, assignment_id, worker_id,
                         generation, capability))
                    if cur.rowcount != 1:
                        raise WorkerAdapterError("execution intent is absent or no longer current")
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE", (assignment_id,))
                assignment = cur.fetchone()
                if assignment is None:
                    raise WorkerAdapterError("assignment disappeared before artifact commit")
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
                    cur.execute("UPDATE worker_attempts SET status='lease_lost',finished_at=clock_timestamp(),failure_class='WorkerLeaseLost' WHERE attempt_id=%s AND status='running'",
                                (attempt_id,))
                    lost = True
                else:
                    cur.execute("INSERT INTO worker_results(attempt_id,result,result_sha256) VALUES (%s,%s,%s)",
                                (attempt_id, result_json, result_digest))
                    cur.execute("UPDATE worker_attempts SET status='succeeded',finished_at=clock_timestamp() WHERE attempt_id=%s AND status='running'",
                                (attempt_id,))
                    if cur.rowcount != 1:
                        raise WorkerAdapterError("attempt is no longer running")
                    if intent_id is not None:
                        cur.execute("""UPDATE worker_execution_intents
                            SET status='succeeded',finished_at=clock_timestamp()
                            WHERE intent_id=%s AND assignment_id=%s AND worker_id=%s
                              AND lease_generation=%s AND capability=%s AND status='running'""",
                            (intent_id, assignment_id, worker_id, generation, capability))
                        if cur.rowcount != 1:
                            raise WorkerAdapterError("execution intent is absent or no longer current")
                    lost = False
        if lost:
            raise WorkerLeaseLost("lease was fenced before result commit")
        return {"attempt_id": attempt_id, "status": "succeeded",
                "result": result, "result_sha256": result_digest}

    def mark_execution_intent(self, intent_id, status, *, failure_class=None):
        """Settle a caught action failure without claiming an uncertain effect succeeded."""
        if status not in {"failed", "outcome_unknown"}:
            raise ValueError("unsupported execution intent outcome")
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""UPDATE worker_execution_intents
                    SET status=%s,finished_at=clock_timestamp(),failure_class=%s
                    WHERE intent_id=%s AND status='running' RETURNING intent_id""",
                    (status, failure_class, intent_id))
                return cur.fetchone() is not None

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
                     source_revision,source_sha256,retrieval_complete)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING observation_id""",
                    (assignment_id, worker_id, operation, result.status.value, action,
                     json.dumps(list(result.source_references)), result.source_revision,
                     result.source_sha256, result.retrieval_complete))
                return cur.fetchone()["observation_id"]

    def verify_attempt(self, assignment_id, attempt_id, verifier_id, credential,
                       verifier, *, idempotency_key):
        """Persist independent evidence, then advance only through the decision."""
        if not idempotency_key:
            raise ValueError("verification idempotency key is required")
        verifier_revision = getattr(verifier, "REVISION", None)
        if not isinstance(verifier_revision, str) or not verifier_revision:
            raise WorkerAdapterError("verifier revision is required")
        revalidation_key = f"grace-verifier-revalidation:{attempt_id}:{verifier_revision}"
        revalidation_requested = idempotency_key == revalidation_key
        db = self.ledger.db
        revalidation = False
        with db.transaction():
            with db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE",
                            (assignment_id,))
                assignment = cur.fetchone()
                if assignment is None:
                    raise WorkerAdapterError("unknown assignment")
                self._authorized_worker(cur, verifier_id, credential,
                                        self.VERIFICATION_CAPABILITY,
                                        assignment["authority_ref"])
                cur.execute("""SELECT verification_id,assignment_id,attempt_id,executor_id,
                                      decision,criteria,evidence_references,verifier_id,
                                      verifier_revision,summary FROM verification_records
                               WHERE idempotency_key=%s""", (idempotency_key,))
                existing = cur.fetchone()
                if existing:
                    if (existing["assignment_id"] != assignment_id or
                            existing["attempt_id"] != attempt_id or
                            existing["verifier_id"] != verifier_id or
                            existing["executor_id"] == verifier_id):
                        raise WorkerAdapterError("verification idempotency key collision")
                    decision = VerificationResult(
                        VerificationStatus(existing["decision"]), existing["criteria"],
                        tuple(existing["evidence_references"]),
                        existing["verifier_revision"], existing["summary"])
                else:
                    if assignment["state"] == "awaiting_verification":
                        if revalidation_requested:
                            raise WorkerAdapterError("revalidation key is invalid for a first decision")
                    elif assignment["state"] == "rework_required" and revalidation_requested:
                        cur.execute("""SELECT decision,verifier_revision FROM verification_records
                            WHERE attempt_id=%s AND verifier_id=%s
                            ORDER BY recorded_at DESC,verification_id DESC LIMIT 1""",
                            (attempt_id, verifier_id))
                        previous = cur.fetchone()
                        if (previous is None or previous["decision"] != "REJECTED" or
                                previous["verifier_revision"] == verifier_revision):
                            raise WorkerAdapterError("no prior rejected decision can be revalidated")
                        revalidation = True
                    else:
                        raise WorkerAdapterError("assignment is not awaiting verification")
                    decision = None
                if existing is None:
                    cur.execute("""SELECT a.attempt_id,a.assignment_id,a.worker_id,a.status,
                                          a.capability,
                                          a.input_sha256,r.result,r.result_sha256
                                   FROM worker_attempts a JOIN worker_results r USING(attempt_id)
                                   WHERE a.attempt_id=%s AND a.assignment_id=%s FOR UPDATE OF a""",
                                (attempt_id, assignment_id))
                    attempt = cur.fetchone()
                    if attempt is None:
                        raise WorkerAdapterError("attempt result is missing")
                    if attempt["worker_id"] == verifier_id:
                        raise WorkerAuthorizationError("executor cannot verify its own attempt")
                    decision = verifier.verify(dict(assignment), dict(attempt), attempt["result"])
                    if not isinstance(decision, VerificationResult):
                        raise WorkerAdapterError("verifier returned an unsupported result")
                    if decision.verifier_revision != verifier_revision:
                        raise WorkerAdapterError("verifier result revision does not match implementation")
                    if revalidation and decision.verifier_revision == previous["verifier_revision"]:
                        raise WorkerAdapterError("verifier revalidation must use a new revision")
                    cur.execute("""INSERT INTO verification_records
                        (verification_id,assignment_id,attempt_id,executor_id,verifier_id,
                         verifier_revision,decision,criteria,evidence_references,summary,
                         idempotency_key)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (uuid4(), assignment_id, attempt_id, attempt["worker_id"],
                         verifier_id, decision.verifier_revision, decision.status.value,
                         json.dumps(dict(decision.criteria), sort_keys=True),
                         json.dumps(list(decision.evidence_references)), decision.summary,
                         idempotency_key))
        if decision.status is VerificationStatus.ACCEPTED:
            step = "verification_rule_correction_accepted" if revalidation_requested else "independent_verification"
            self.ledger.transition(assignment_id, "completed", step,
                                   f"verification-transition:{idempotency_key}",
                                   actor_id=f"verifier:{verifier_id}", verified=True)
        elif decision.status is VerificationStatus.REJECTED and not revalidation_requested:
            self.ledger.transition(assignment_id, "rework_required", "verification_rejected",
                                   f"verification-transition:{idempotency_key}",
                                   actor_id=f"verifier:{verifier_id}")
        elif decision.status is VerificationStatus.INCONCLUSIVE and not revalidation_requested:
            self.ledger.transition(assignment_id, "blocked", "verification_inconclusive",
                                   f"verification-transition:{idempotency_key}",
                                   actor_id=f"verifier:{verifier_id}")
        return decision

    def execute_sha256(self, assignment_id, worker_id, credential, generation,
                       idempotency_key, data, *, intent_id=None):
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
                    if intent_id is not None:
                        cur.execute("""UPDATE worker_execution_intents
                            SET attempt_id=%s,status='succeeded',finished_at=clock_timestamp()
                            WHERE intent_id=%s AND assignment_id=%s AND worker_id=%s
                              AND lease_generation=%s AND status='running'""",
                            (existing["attempt_id"], intent_id, assignment_id,
                             worker_id, generation))
                        if cur.rowcount != 1:
                            raise WorkerAdapterError("execution intent is absent or no longer current")
                    return {"attempt_id": existing["attempt_id"], "status": "succeeded",
                            "result": saved["result"], "result_sha256": saved["result_sha256"]}
                attempt_id = uuid4()
                cur.execute("""INSERT INTO worker_attempts
                    (attempt_id,assignment_id,worker_id,lease_generation,capability,
                     idempotency_key,input_sha256,status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'running')""",
                    (attempt_id, assignment_id, worker_id, generation, capability,
                     idempotency_key, input_digest))
                if intent_id is not None:
                    cur.execute("""UPDATE worker_execution_intents
                        SET attempt_id=%s WHERE intent_id=%s AND assignment_id=%s
                          AND worker_id=%s AND lease_generation=%s AND status='running'""",
                        (attempt_id, intent_id, assignment_id, worker_id, generation))
                    if cur.rowcount != 1:
                        raise WorkerAdapterError("execution intent is absent or no longer current")

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
                    if intent_id is not None:
                        cur.execute("""UPDATE worker_execution_intents
                            SET status='succeeded',finished_at=clock_timestamp()
                            WHERE intent_id=%s AND status='running'""", (intent_id,))
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

    def incomplete_execution_intents(self):
        """List unfinished action intents, including actions without attempt rows yet."""
        with self.ledger.db.cursor() as cur:
            self.ledger._set_search_path(cur)
            cur.execute("""SELECT intent_id,assignment_id,worker_id,lease_generation,
                                  capability,effect_class,started_at
                           FROM worker_execution_intents WHERE status='running'
                           ORDER BY started_at,intent_id""")
            return cur.fetchall()
