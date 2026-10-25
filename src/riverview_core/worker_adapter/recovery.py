# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/recovery.py
# Component: WORKER-ADAPTER
# Revision: 1.2.15
# Changed: 2026-10-25 UTC | RV-GRACE-S5-EVIDENCE-RETRY-20261025 | Reconcile a narrowly proven pre-execution ObjectiveStateError during same-assignment rework while retaining prior artifacts and rejection history.
# Changed: 2026-10-20 UTC | RV-GRACE-S3-RECOVERY-DISPOSITION-001 | Add an exact-grant, append-only single-use disposition for one exhausted no-artifact assignment retry.
# Changed: 2026-10-20 UTC | RV-GRACE-MULTISTEP-PROVENANCE-RECOVERY-001 | Select no-artifact recovery through the exact durable objective-step assignment, dispatch event, and persisted proposal step rather than the latest objective assignment pointer.
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Reconcile assignment-defined artifact sets and detect partial output without fixed extensions
# Purpose: Reconcile expired worker leases without losing or blindly repeating work
# Execution Model: Explicit PostgreSQL recovery pass at worker startup or polling
# Observability: Recovery records and causal assignment transition events
# Dependencies: Psycopg 3; PostgreSQL ledger, scheduler and worker migrations
# Authority: Recovery only; unknown external outcomes wait for Steward decision
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Enforce optional persistent retry ceilings
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Reconcile only legacy Git ownership failures proven to precede Codex launch and all durable effects
# Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Resume bounded, durable no-launch failures after correcting provenance validation
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-BOUNDED-RETRY-001 | Requeue only typed Codex failures with expired leases and no attempt, verifier result, or durable artifact
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001 | Requeue the same assignment after fresh verified grounding and fail-closed no-effect checks
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001-JSON-FIX | Persist metadata-only grounding provenance in atomic recovery
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIED-GROUNDING-RESUME-001-GUARD-REVIEW | Require verified action preflight and honor retry ceiling before evidence requeue
# Changed: 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Scope recovery to authenticated worker authority and preserve validated late Codex artifacts for verification
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Retain the fixed Codex output name and validated file-change scope when reconciling a late artifact
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Recover the established fixed deliverable scope for immutable legacy attempts without rerunning Codex
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Reconcile scoped source-change failures only when no durable patch, execution result, or verifier record exists
# Contracts: docs/ROADMAP.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Recover expired leases and narrowly proven no-durable-artifact Codex failures."""

import hashlib
import hmac
import json
import os
from datetime import timedelta
from pathlib import Path
import re
import stat
from uuid import uuid4

from ..institutional_authority import ExactGrantAuthorizer, GrantCheckUnavailable, GrantDenied
from ..ledger import TRANSITIONS
from ..postgres_ledger import PostgresLedger, assignment_process_position
from .knowledge import KnowledgeResult, KnowledgeStatus


def _codex_artifact_prefix(assignment_id):
    return "codex-" + hashlib.sha256(assignment_id.encode("utf-8")).hexdigest()


def _codex_artifact_files(root, assignment_id):
    """Find durable adapter outputs for this assignment independent of file type."""
    prefix = _codex_artifact_prefix(assignment_id)
    files = []
    for directory in root.glob(prefix + "*"):
        try:
            info = directory.lstat()
            if (not stat.S_ISDIR(info.st_mode) or directory.is_symlink() or
                    info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700):
                continue
            files.extend(path for path in directory.iterdir()
                         if re.fullmatch(r"[0-9a-f]{12}", path.name))
        except OSError:
            continue
    return tuple(files)


class PostgresRecoveryCoordinator:
    """Atomically reconcile expired leases and persist each recovery decision."""

    def __init__(self, dsn, *, schema="public", authority_schema=None, max_retries=None):
        if max_retries is not None and (type(max_retries) is not int or not 0 <= max_retries <= 100):
            raise ValueError("max_retries must be None or an integer from 0 to 100")
        self.ledger = PostgresLedger(dsn, schema=schema)
        self.schema = schema
        self.max_retries = max_retries
        self.authorizer = ExactGrantAuthorizer(authority_schema or schema)

    def close(self):
        self.ledger.close()

    def authorize_one_no_artifact_retry(self, *, assignment_id, objective_id, step_id,
            artifact_contract_sha256, worker_id, worker_credential,
            recovery_credential, authorization_reference, idempotency_key,
            artifact_root):
        """Consume one exact service-recovery disposition and ready the same assignment.

        This operation is an explicit, one-use exception to an exhausted retry
        ceiling. It never alters prior recovery rows or the configured ceiling.
        A service.recover exact grant authorizes this disposition; ordinary worker
        assignment.execute authorization is independently rechecked here and again
        by the normal lease claim. The disposition insert and transition are atomic.
        """
        if (not isinstance(assignment_id, str) or not assignment_id or
                not isinstance(objective_id, str) or not objective_id or
                not isinstance(step_id, str) or not re.fullmatch(r"s[1-9][0-9]?", step_id) or
                not isinstance(artifact_contract_sha256, str) or
                not re.fullmatch(r"[0-9a-f]{64}", artifact_contract_sha256) or
                not isinstance(worker_id, str) or not worker_id or
                not isinstance(worker_credential, str) or len(worker_credential) < 32 or
                not isinstance(recovery_credential, str) or len(recovery_credential) < 32 or
                not isinstance(authorization_reference, str) or
                not re.fullmatch(r"https://github\.com/ppow1/Riverview-/issues/120#issuecomment-[0-9]{8,20}", authorization_reference) or
                not isinstance(idempotency_key, str) or
                not re.fullmatch(r"[A-Za-z0-9._:-]{16,200}", idempotency_key)):
            raise ValueError("exact assignment, contract digest, authorization reference, and idempotency key are required")
        if type(self.max_retries) is not int or self.max_retries < 1:
            raise ValueError("a configured finite retry ceiling is required")

        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                try:
                    recovery_grant = self.authorizer.require(
                        cur, recovery_credential, "service.recover", "service-recovery.v1")
                except GrantDenied as exc:
                    raise PermissionError("exact service recovery grant is required") from exc
                except GrantCheckUnavailable:
                    raise RuntimeError("institutional recovery authority is unavailable") from None

                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE",
                            (assignment_id,))
                assignment = cur.fetchone()
                if assignment is None:
                    raise ValueError("target assignment is unavailable")

                cur.execute("""SELECT disposition_id,objective_id,step_id,artifact_contract_sha256,
                        worker_id,authorization_reference,idempotency_key,authorized_generation,
                        authorization_principal_id,authorization_grant_id
                    FROM worker_recovery_dispositions WHERE assignment_id=%s""",
                    (assignment_id,))
                prior = cur.fetchone()
                if prior is not None:
                    requested = (objective_id, step_id, artifact_contract_sha256, worker_id,
                                 authorization_reference, idempotency_key,
                                 recovery_grant["principal_id"], recovery_grant["grant_id"])
                    recorded = (prior["objective_id"], prior["step_id"],
                                prior["artifact_contract_sha256"], prior["worker_id"],
                                prior["authorization_reference"], prior["idempotency_key"],
                                prior["authorization_principal_id"], prior["authorization_grant_id"])
                    if requested != recorded:
                        raise ValueError("a different recovery disposition already consumed this assignment")
                    return {"assignment_id": assignment_id,
                            "disposition_id": str(prior["disposition_id"]),
                            "authorized_generation": prior["authorized_generation"],
                            "replayed": True}

                root = Path(artifact_root)
                try:
                    root_info = root.lstat()
                    safe_root = (root.is_absolute() and stat.S_ISDIR(root_info.st_mode) and
                                 not root.is_symlink() and root_info.st_uid == os.geteuid() and
                                 stat.S_IMODE(root_info.st_mode) == 0o700 and
                                 root.resolve() == root.absolute())
                except OSError:
                    safe_root = False
                if not safe_root or _codex_artifact_files(root, assignment_id):
                    raise ValueError("private artifact root required and no prior assignment artifact may exist")

                if (assignment["state"] != "blocked" or
                        assignment["workflow_step"] != "WORKER_RETRYABLE_NO_ARTIFACT" or
                        assignment["objective_ref"] != objective_id or
                        assignment["authority_ref"] != "work-order:engineering"):
                    raise ValueError("assignment is outside the bounded no-artifact recovery state")

                cur.execute("""SELECT credential_sha256,capabilities,scope_ref,active
                    FROM worker_registry WHERE worker_id=%s FOR SHARE""", (worker_id,))
                worker = cur.fetchone()
                if (worker is None or not worker["active"] or
                        "engineering.codex-cli-artifact.v1" not in worker["capabilities"] or
                        worker["scope_ref"] != assignment["authority_ref"] or
                        not hmac.compare_digest(bytes(worker["credential_sha256"]),
                            hashlib.sha256(worker_credential.encode("utf-8")).digest())):
                    raise PermissionError("registered exact-scope Codex worker is required")
                try:
                    worker_grant = self.authorizer.require(cur, worker_credential,
                        "assignment.execute", assignment["authority_ref"])
                except GrantDenied as exc:
                    raise PermissionError("active assignment.execute grant is required") from exc
                except GrantCheckUnavailable:
                    raise RuntimeError("institutional worker authority is unavailable") from None

                cur.execute("""SELECT o.status,o.scope_ref,o.evidence,o.proposal,
                        o.source_revision,o.source_sha256,
                        s.step_id,s.step_objective,s.acceptance_criteria,s.depends_on,
                        s.status AS step_status,s.assignment_id AS step_assignment_id,
                        s.dispatch_count,d.payload AS dispatch_payload
                    FROM grace_objectives o
                    JOIN grace_objective_steps s ON s.objective_id=o.objective_id
                    LEFT JOIN LATERAL (
                        SELECT payload FROM grace_objective_events e
                        WHERE e.objective_id=o.objective_id
                          AND e.event_type='work_order.dispatched'
                          AND e.payload->>'assignment_id'=s.assignment_id
                          AND e.payload->>'workflow_step'=s.step_id
                        ORDER BY e.sequence DESC LIMIT 1
                    ) d ON true
                    WHERE o.objective_id=%s AND s.assignment_id=%s AND s.step_id=%s
                    FOR UPDATE OF o,s""", (objective_id, assignment_id, step_id))
                objective_step = cur.fetchone()
                if (objective_step is None or objective_step["status"] != "WORK_ORDER_CREATED" or
                        objective_step["scope_ref"] != "work-order:engineering" or
                        not isinstance(objective_step["evidence"], dict) or
                        objective_step["evidence"].get("status") != "VERIFIED" or
                        objective_step["evidence"].get("retrieval_complete") is not True or
                        not objective_step["source_revision"] or not objective_step["source_sha256"] or
                        objective_step["evidence"].get("source_revision") != objective_step["source_revision"] or
                        objective_step["evidence"].get("source_sha256") != objective_step["source_sha256"] or
                        objective_step["step_status"] != "assigned" or
                        objective_step["dispatch_count"] != 1 or
                        not isinstance(objective_step["dispatch_payload"], dict)):
                    raise ValueError("durable verified objective-step assignment link is required")

                proposal = objective_step["proposal"] if isinstance(objective_step["proposal"], dict) else {}
                proposal_steps = proposal.get("steps", [])
                proposal_step = next((item for item in proposal_steps if isinstance(item, dict)
                                      and item.get("step_id") == step_id), None)
                contract = (proposal_step or {}).get("artifact_requirements")
                if (proposal_step is None or
                        proposal_step.get("objective") != objective_step["step_objective"] or
                        proposal_step.get("acceptance_criteria") != objective_step["acceptance_criteria"] or
                        proposal_step.get("depends_on") != objective_step["depends_on"] or
                        proposal_step.get("execution_capability") != "engineering.codex-cli-artifact.v1" or
                        not isinstance(contract, list) or not contract or
                        objective_step["dispatch_payload"].get("artifact_contract") != contract):
                    raise ValueError("persisted dispatched artifact contract is inconsistent")
                contract_bytes = json.dumps(contract, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False).encode("utf-8")
                if not hmac.compare_digest(hashlib.sha256(contract_bytes).hexdigest(),
                                           artifact_contract_sha256):
                    raise ValueError("persisted artifact contract digest changed")

                cur.execute("""SELECT count(*) AS n FROM grace_objective_steps dep
                    WHERE dep.objective_id=%s AND dep.step_id=ANY(%s)
                      AND dep.status='verified'""",
                    (objective_id, objective_step["depends_on"]))
                if int(cur.fetchone()["n"]) != len(objective_step["depends_on"]):
                    raise ValueError("all persisted step dependencies must remain verified")

                cur.execute("SELECT generation,expires_at FROM assignment_leases WHERE assignment_id=%s FOR UPDATE",
                            (assignment_id,))
                lease = cur.fetchone()
                cur.execute("SELECT clock_timestamp() AS now")
                now = cur.fetchone()["now"]
                if lease is None or lease["expires_at"] > now:
                    raise ValueError("a prior expired lease is required; active work cannot be recovered")
                authorized_generation = int(lease["generation"]) + 1

                cur.execute("""SELECT count(*) AS n FROM worker_recovery_records
                    WHERE assignment_id=%s AND decision='retry_safe'""", (assignment_id,))
                retry_count = int(cur.fetchone()["n"])
                if retry_count != self.max_retries:
                    raise ValueError("single-use disposition applies only at the exact configured retry ceiling")
                # Ordinary recovery preserves previous decisions and marks their
                # intents retry_scheduled. The exhausted current generation has
                # one completed failure and no recovery record yet.
                cur.execute("""SELECT i.*,r.decision AS recovery_decision,
                        r.intent_id AS recovery_intent_id
                    FROM worker_execution_intents i
                    LEFT JOIN worker_recovery_records r
                      ON r.assignment_id=i.assignment_id
                     AND r.lease_generation=i.lease_generation
                    WHERE i.assignment_id=%s ORDER BY i.lease_generation
                    FOR UPDATE OF i""", (assignment_id,))
                intents = cur.fetchall()
                if len(intents) != retry_count + 1:
                    raise ValueError("prior recovered intents and one current failure are required")
                for intent in intents:
                    current = intent["lease_generation"] == lease["generation"]
                    common_valid = (
                        intent["worker_id"] == worker_id and
                        intent["capability"] == "engineering.codex-cli-artifact.v1" and
                        intent["effect_class"] == "external_uncertain" and
                        intent["attempt_id"] is None and intent["finished_at"] is not None)
                    if current:
                        valid = (intent["status"] == "failed" and
                            intent["failure_class"] == "CodexActionFailure:deliverable_metadata_invalid" and
                            intent["recovery_decision"] is None)
                    else:
                        valid = (intent["lease_generation"] < lease["generation"] and
                            intent["status"] == "retry_scheduled" and
                            intent["recovery_decision"] == "retry_safe" and
                            intent["recovery_intent_id"] == intent["intent_id"])
                    if not common_valid or not valid:
                        raise ValueError("exact prior recovery history and current typed failure are required")
                if not any(i["lease_generation"] == lease["generation"] for i in intents):
                    raise ValueError("current expired lease must have its own completed failure")
                cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                            (assignment_id,))
                if int(cur.fetchone()["n"]) != 0:
                    raise ValueError("attempt, result, or verification evidence forbids replay")
                cur.execute("""SELECT count(*) AS n FROM worker_results r
                    JOIN worker_attempts a USING (attempt_id) WHERE a.assignment_id=%s""",
                    (assignment_id,))
                if int(cur.fetchone()["n"]) != 0:
                    raise ValueError("attempt, result, or verification evidence forbids replay")
                for table in ("verification_records",):
                    cur.execute(f"SELECT count(*) AS n FROM {table} WHERE assignment_id=%s",
                                (assignment_id,))
                    if int(cur.fetchone()["n"]) != 0:
                        raise ValueError("attempt, result, or verification evidence forbids replay")

                cur.execute("""INSERT INTO worker_recovery_dispositions
                    (assignment_id,objective_id,step_id,artifact_contract_sha256,
                     prior_retry_count,authorized_generation,worker_id,
                     authorization_reference,authorization_principal_id,
                     authorization_grant_id,idempotency_key)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    RETURNING disposition_id""",
                    (assignment_id, objective_id, step_id, artifact_contract_sha256,
                     retry_count, authorized_generation, worker_id, authorization_reference,
                     recovery_grant["principal_id"], recovery_grant["grant_id"],
                     idempotency_key))
                disposition_id = cur.fetchone()["disposition_id"]
                self.ledger._append_event(cur, assignment_id=assignment_id,
                    event_type="assignment.recovery_dispositioned",
                    idempotency_key=f"recovery-disposition:{idempotency_key}",
                    actor_id=recovery_grant["principal_id"],
                    authority_ref=assignment["authority_ref"],
                    correlation_id=assignment["correlation_id"],
                    causation_id=None, payload_schema="rv.assignment.recovery-disposition.v1",
                    payload={"disposition_id": str(disposition_id), "objective_id": objective_id,
                        "step_id": step_id, "artifact_contract_sha256": artifact_contract_sha256,
                        "prior_retry_count": retry_count,
                        "authorized_generation": authorized_generation,
                        "authorization_grant_id": recovery_grant["grant_id"],
                        "worker_grant_id": worker_grant["grant_id"]})
                self._transition_locked(cur, assignment, "ready", "STEWARD_DISPOSITIONED_ONCE",
                    f"recovery-disposition-ready:{idempotency_key}", evidence={
                        "disposition_id": str(disposition_id),
                        "authorization_reference": authorization_reference,
                        "authorized_generation": authorized_generation,
                        "retry_history_preserved": retry_count})
                return {"assignment_id": assignment_id,
                        "disposition_id": str(disposition_id),
                        "authorized_generation": authorized_generation,
                        "replayed": False}

    def resume_verified_waiting_for_evidence(self, assignment_id, result, preflight_result, *,
                                              worker_id, worker_scope, artifact_root):
        """Return one safely blocked Codex assignment to ready after fresh grounding.

        This is an idempotent recovery transition, not an execution authorization.
        The worker grant is checked by the caller while selecting the candidate and
        is checked again by the ordinary lease claim immediately before execution.
        No prior worker attempt, verifier record, artifact, running/unknown intent,
        or unreconciled Codex execution intent may be replayed.
        """
        if (not isinstance(assignment_id, str) or not assignment_id or
                not isinstance(worker_id, str) or not worker_id or
                worker_scope != "work-order:engineering" or
                not isinstance(result, KnowledgeResult) or
                not isinstance(preflight_result, KnowledgeResult) or
                any(item.status is not KnowledgeStatus.VERIFIED or
                    item.retrieval_complete is not True or
                    not isinstance(item.source_revision, str) or
                    not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", item.source_revision) or
                    not isinstance(item.source_sha256, str) or
                    not re.fullmatch(r"[0-9a-f]{64}", item.source_sha256) or
                    not isinstance(item.source_references, tuple) or
                    not 1 <= len(item.source_references) <= 100 or
                    any(not isinstance(ref, str) or not ref.startswith("repo://") or
                        len(ref) > 240 for ref in item.source_references)
                    for item in (result, preflight_result))):
            raise ValueError("fresh verified grounding and action preflight are required")
        root = Path(artifact_root)
        try:
            info = root.lstat()
            safe_root = (root.is_absolute() and root.is_dir() and not root.is_symlink() and
                         info.st_uid == os.geteuid() and (info.st_mode & 0o777) == 0o700 and
                         root.resolve() == root.absolute())
        except OSError:
            safe_root = False
        if not safe_root:
            raise ValueError("Codex artifact root is not a private owned directory")
        artifact_files = _codex_artifact_files(root, assignment_id)

        resumed = False
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("SELECT * FROM assignments WHERE id=%s FOR UPDATE",
                            (assignment_id,))
                assignment = cur.fetchone()
                if (assignment is None or assignment["state"] != "blocked" or
                        assignment["workflow_step"] != "WAITING_FOR_EVIDENCE" or
                        assignment["authority_ref"] != worker_scope):
                    return False
                cur.execute("""SELECT generation,expires_at FROM assignment_leases
                    WHERE assignment_id=%s FOR UPDATE""", (assignment_id,))
                lease = cur.fetchone()
                cur.execute("SELECT clock_timestamp() AS now")
                if lease is not None and lease["expires_at"] > cur.fetchone()["now"]:
                    return False
                if self.max_retries is not None:
                    cur.execute("""SELECT count(*) AS n FROM worker_recovery_records
                        WHERE assignment_id=%s AND decision='retry_safe'""", (assignment_id,))
                    if int(cur.fetchone()["n"]) >= self.max_retries:
                        return False
                cur.execute("""SELECT operation,status FROM knowledge_observations
                    WHERE assignment_id=%s ORDER BY recorded_at DESC,observation_id DESC LIMIT 1""",
                    (assignment_id,))
                prior_observation = cur.fetchone()
                if (prior_observation is None or
                        prior_observation["operation"] not in
                            {"ground_assignment", "reground_assignment", "preflight_action",
                             "preflight_assignment_evidence"} or
                        prior_observation["status"] == KnowledgeStatus.VERIFIED.value):
                    return False
                cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                            (assignment_id,))
                if int(cur.fetchone()["n"]) != 0:
                    return False
                cur.execute("SELECT count(*) AS n FROM verification_records WHERE assignment_id=%s",
                            (assignment_id,))
                if int(cur.fetchone()["n"]) != 0:
                    return False
                if artifact_files or _codex_artifact_files(root, assignment_id):
                    return False
                cur.execute("""SELECT count(*) AS n FROM worker_execution_intents i
                    WHERE i.assignment_id=%s AND
                      (i.capability<>'engineering.codex-cli-artifact.v1' OR
                       i.effect_class<>'external_uncertain' OR
                       i.status NOT IN ('failed','retry_scheduled') OR
                       i.failure_class IS NULL OR
                       i.failure_class NOT LIKE 'CodexActionFailure%%' OR
                       NOT EXISTS (SELECT 1 FROM worker_recovery_records r
                           WHERE r.assignment_id=i.assignment_id
                             AND r.lease_generation=i.lease_generation
                             AND r.decision='retry_safe'))""", (assignment_id,))
                if int(cur.fetchone()["n"]) != 0:
                    return False
                cur.execute("""SELECT 1 FROM grace_objectives o
                    WHERE o.objective_id=%s AND o.assignment_id=%s
                      AND o.scope_ref=%s AND o.status='WORK_ORDER_CREATED'
                      AND o.evidence->>'status'='VERIFIED'""",
                    (assignment["objective_ref"], assignment_id, worker_scope))
                if cur.fetchone() is None:
                    return False

                cur.execute("""INSERT INTO knowledge_observations
                    (assignment_id,worker_id,operation,status,action,source_references,
                     source_revision,source_sha256,retrieval_complete)
                    VALUES (%s,%s,'ground_assignment','VERIFIED',NULL,%s,%s,%s,true),
                           (%s,%s,'preflight_action','VERIFIED',%s,%s,%s,%s,true)""",
                    (assignment_id, worker_id, json.dumps(list(result.source_references)),
                     result.source_revision, result.source_sha256,
                     assignment_id, worker_id, "engineering.codex-cli-artifact.v1",
                     json.dumps(list(preflight_result.source_references)),
                     preflight_result.source_revision, preflight_result.source_sha256))
                evidence = {
                    "proof": "fresh_verified_grounding_after_wait",
                    "knowledge_observation_status": "VERIFIED",
                    "retrieval_complete": True,
                    "source_revision": result.source_revision,
                    "source_sha256": result.source_sha256,
                    "source_references": list(result.source_references),
                    "preflight_source_revision": preflight_result.source_revision,
                    "preflight_source_sha256": preflight_result.source_sha256,
                    "preflight_source_references": list(preflight_result.source_references),
                    "preflight_capability": "engineering.codex-cli-artifact.v1",
                    "retry_limit_respected": True,
                    "prior_attempts_absent": True,
                    "assignment_artifact_absent": True,
                    "intent_outcomes_reconciled": True,
                    "exact_worker_grant_rechecked_at_claim": True,
                }
                self._transition_locked(cur, assignment, "ready",
                    "EVIDENCE_REVALIDATED", f"grounding-resume:{assignment_id}:"
                    f"{result.source_revision}:{result.source_sha256}", evidence=evidence)
                resumed = True
        return resumed

    def _transition_locked(self, cur, assignment, to_state, step, key, *, evidence=None):
        from_state = assignment["state"]
        if to_state not in TRANSITIONS[from_state]:
            raise RuntimeError(f"invalid recovery transition: {from_state} -> {to_state}")
        cur.execute("SELECT event_id FROM events WHERE assignment_id=%s ORDER BY seq DESC LIMIT 1",
                    (assignment["id"],))
        cause = cur.fetchone()["event_id"]
        payload = {"from": from_state, "to": to_state, "step": step,
                   "actor_id": "cme:recovery", "verified_claim": False,
                   "privacy_domain": "institution"}
        graph_id, node_id = assignment_process_position(to_state)
        payload.update({"process_graph_id": graph_id, "process_node_id": node_id})
        if evidence:
            payload["recovery_evidence"] = evidence
        cur.execute("""UPDATE assignments
            SET state=%s,workflow_step=%s,process_graph_id=%s,process_node_id=%s,
                updated_at=clock_timestamp(),version=version+1 WHERE id=%s""",
            (to_state, step, graph_id, node_id, assignment["id"]))
        self.ledger._append_event(
            cur, assignment_id=assignment["id"], event_type="assignment.transitioned",
            idempotency_key=key, actor_id="cme:recovery",
            authority_ref=assignment["authority_ref"],
            correlation_id=assignment["correlation_id"], causation_id=cause,
            payload_schema="rv.assignment.transitioned.v1", payload=payload)
        assignment["state"] = to_state

    def reconcile_expired(self, *, scope_ref, worker_id, limit=100):
        """Reconcile expired running leases in isolated, idempotent transactions.

        A durable result is retained for independent verification. An intent
        classified retry-safe is requeued with the old generation fenced. Every
        other incomplete or legacy action goes to ``awaiting_steward`` because
        its external outcome cannot be proven absent.
        """
        if (not isinstance(scope_ref, str) or not scope_ref or
                not isinstance(worker_id, str) or not worker_id or
                not isinstance(limit, int) or limit < 1 or limit > 1000):
            raise ValueError("limit must be between 1 and 1000")
        recovered = []
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT a.*,l.generation,l.expires_at,l.worker_id AS lease_worker
                    FROM assignments a JOIN assignment_leases l ON l.assignment_id=a.id
                    WHERE a.state='running' AND a.authority_ref=%s
                      AND l.worker_id=%s
                      AND l.expires_at<=clock_timestamp()
                    ORDER BY l.expires_at,a.id FOR UPDATE OF a,l SKIP LOCKED LIMIT %s""",
                    (scope_ref, worker_id, limit))
                assignments = cur.fetchall()
                for assignment in assignments:
                    generation = assignment["generation"]
                    cur.execute("""SELECT * FROM worker_execution_intents
                        WHERE assignment_id=%s AND lease_generation=%s FOR UPDATE""",
                        (assignment["id"], generation))
                    intent = cur.fetchone()
                    cur.execute("""SELECT a.attempt_id,a.status,r.result_sha256
                        FROM worker_attempts a LEFT JOIN worker_results r USING(attempt_id)
                        WHERE a.assignment_id=%s AND a.lease_generation=%s
                        ORDER BY a.started_at DESC,a.attempt_id DESC
                        LIMIT 1 FOR UPDATE OF a""", (assignment["id"], generation))
                    attempt = cur.fetchone()
                    has_result = bool(attempt and attempt["result_sha256"] is not None)
                    if has_result:
                        decision, target, step = "result_preserved", "awaiting_verification", "RECOVERY_RESULT_PRESERVED"
                    elif intent and intent["effect_class"] == "retry_safe":
                        cur.execute("SELECT count(*) AS retries FROM worker_recovery_records "
                                    "WHERE assignment_id=%s AND decision='retry_safe'",
                                    (assignment["id"],))
                        retries = int(cur.fetchone()["retries"])
                        if self.max_retries is not None and retries >= self.max_retries:
                            decision, target, step = "retry_exhausted", "blocked", "RECOVERY_RETRY_LIMIT"
                        else:
                            decision, target, step = "retry_safe", "ready", "RECOVERY_REQUEUED"
                    else:
                        decision, target, step = "outcome_unknown", "awaiting_steward", "RECOVERY_OUTCOME_UNKNOWN"

                    cur.execute("""INSERT INTO worker_recovery_records
                        (assignment_id,lease_generation,intent_id,attempt_id,decision,
                         previous_state,resulting_state,observed_expiry)
                        VALUES (%s,%s,%s,%s,%s,'running',%s,%s)""",
                        (assignment["id"], generation,
                         intent["intent_id"] if intent else None,
                         attempt["attempt_id"] if attempt else None, decision,
                         target, assignment["expires_at"]))

                    if attempt and not has_result and attempt["status"] == "running":
                        cur.execute("""UPDATE worker_attempts
                            SET status='lease_lost',finished_at=clock_timestamp(),
                                failure_class='ProcessInterrupted'
                            WHERE attempt_id=%s AND status='running'""",
                            (attempt["attempt_id"],))
                    if intent and intent["status"] == "running":
                        new_status = {"retry_safe": "retry_scheduled",
                                      "retry_exhausted": "failed",
                                      "outcome_unknown": "outcome_unknown",
                                      "result_preserved": "succeeded"}[decision]
                        cur.execute("""UPDATE worker_execution_intents
                            SET status=%s,finished_at=clock_timestamp(),
                                failure_class=%s WHERE intent_id=%s""",
                            (new_status, None if has_result else "ProcessInterrupted",
                             intent["intent_id"]))

                    prefix = f"recovery:{assignment['id']}:{generation}"
                    if decision == "retry_safe":
                        self._transition_locked(cur, assignment, "blocked",
                                                "RECOVERY_RETRY_SCHEDULED", prefix + ":blocked")
                        self._transition_locked(cur, assignment, "ready", step, prefix + ":ready")
                    else:
                        self._transition_locked(cur, assignment, target, step,
                                                prefix + ":" + target)
                    recovered.append({"assignment_id": assignment["id"],
                                      "lease_generation": generation,
                                      "decision": decision, "resulting_state": target})
        return recovered

    def reconcile_late_codex_artifacts(self, *, worker_adapter, worker_id, credential,
                                       capability, scope_ref, artifact_root,
                                       repository_revision, limit=1):
        """Attach a late assignment-bound Codex artifact to normal verification.

        This path is intentionally narrower than retry: it only reconciles an
        existing outcome-unknown Codex intent after lease expiry, revalidates the
        worker grant in the transaction, and requires the exact private artifact
        path plus immutable objective, accepted step, and verified grounding.
        The prior recovery decision remains unchanged and the verifier still runs.
        """
        from .adapter import PostgresWorkerAdapter
        if (not isinstance(worker_adapter, PostgresWorkerAdapter) or
                not isinstance(worker_id, str) or not worker_id or
                not isinstance(credential, str) or not credential or
                capability != PostgresWorkerAdapter.CODEX_CLI_CAPABILITY or
                not isinstance(scope_ref, str) or not scope_ref or
                not isinstance(repository_revision, str) or
                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", repository_revision) or
                type(limit) is not int or not 1 <= limit <= 5):
            raise ValueError("late Codex artifact recovery evidence is invalid")
        root = Path(artifact_root)
        try:
            root_info = root.lstat()
            safe_root = (root.is_absolute() and root.is_dir() and not root.is_symlink() and
                         root_info.st_uid == os.geteuid() and
                         (root_info.st_mode & 0o777) == 0o700 and
                         root.resolve() == root.absolute())
        except OSError:
            safe_root = False
        if not safe_root:
            raise ValueError("Codex artifact root is not a private owned directory")

        recovered = []
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT a.*,l.generation,l.expires_at,i.intent_id,
                        i.worker_id AS intent_worker,i.capability,i.effect_class,
                        i.status AS intent_status,i.failure_class,i.started_at AS intent_started,
                        o.objective_id,o.status AS objective_status,o.source_revision,
                        o.source_sha256,o.evidence
                    FROM assignments a
                    JOIN assignment_leases l ON l.assignment_id=a.id
                    JOIN worker_execution_intents i ON i.assignment_id=a.id
                        AND i.lease_generation=l.generation
                    JOIN grace_objectives o ON o.assignment_id=a.id
                        AND o.objective_id=a.objective_ref
                    JOIN worker_recovery_records rr ON rr.assignment_id=a.id
                        AND rr.lease_generation=l.generation AND rr.decision='outcome_unknown'
                    WHERE a.state='awaiting_steward'
                      AND a.workflow_step IN ('ACTION_OUTCOME_UNKNOWN','RECOVERY_OUTCOME_UNKNOWN')
                      AND a.authority_ref=%s AND l.expires_at<=clock_timestamp()
                      AND i.worker_id=%s AND i.capability=%s
                      AND i.effect_class='external_uncertain'
                      AND i.status='outcome_unknown'
                      AND i.failure_class='ProcessInterrupted'
                      AND o.status='WORK_ORDER_CREATED'
                      AND o.evidence->>'status'='VERIFIED'
                    ORDER BY i.started_at,a.id
                    FOR UPDATE OF a,l,i,rr SKIP LOCKED LIMIT %s""",
                    (scope_ref, worker_id, capability, limit))
                candidates = cur.fetchall()
                for assignment in candidates:
                    worker_adapter._authorized_worker(
                        cur, worker_id, credential, capability, scope_ref)
                    cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                                (assignment["id"],))
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    cur.execute("SELECT count(*) AS n FROM verification_records WHERE assignment_id=%s",
                                (assignment["id"],))
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    cur.execute("""SELECT s.step_objective,s.acceptance_criteria,
                            d.payload->'artifact_contract' AS artifact_contract
                        FROM grace_objective_steps s LEFT JOIN LATERAL (
                            SELECT payload FROM grace_objective_events e
                            WHERE e.objective_id=s.objective_id
                              AND e.event_type='work_order.dispatched'
                              AND e.payload->>'assignment_id'=s.assignment_id
                              AND e.payload->>'workflow_step'=s.step_id
                            ORDER BY e.sequence DESC LIMIT 1) d ON true
                        WHERE s.objective_id=%s AND s.assignment_id=%s""",
                        (assignment["objective_id"], assignment["id"]))
                    step = cur.fetchone()
                    evidence = assignment["evidence"]
                    if (step is None or assignment["source_revision"] is None or
                            assignment["source_sha256"] is None or
                            not isinstance(evidence, dict) or
                            evidence.get("status") != "VERIFIED" or
                            evidence.get("source_revision") != assignment["source_revision"] or
                            evidence.get("source_sha256") != assignment["source_sha256"]):
                        continue
                    cur.execute("""SELECT source_references,source_revision,source_sha256,
                            retrieval_complete FROM knowledge_observations
                        WHERE assignment_id=%s AND operation='reground_assignment'
                          AND status='VERIFIED'
                        ORDER BY recorded_at DESC,observation_id DESC LIMIT 1""",
                        (assignment["id"],))
                    grounding = cur.fetchone()
                    refs = grounding["source_references"] if grounding else None
                    if (not isinstance(refs, list) or not refs or
                            grounding["retrieval_complete"] is not True or
                            not isinstance(grounding["source_revision"], str) or
                            not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                                             grounding["source_revision"]) or
                            not isinstance(grounding["source_sha256"], str) or
                            not re.fullmatch(r"[0-9a-f]{64}", grounding["source_sha256"]) or
                            any(not isinstance(ref, str) or not ref.startswith("repo://")
                                for ref in refs)):
                        continue
                    contract = step["artifact_contract"]
                    if not isinstance(contract, list) or not 1 <= len(contract) <= 8:
                        continue
                    assignment_key = _codex_artifact_prefix(assignment["id"])
                    artifact_records = []
                    safe_set = True
                    from ..resident_execution.codex_cli import CodexCLIExecutionAdapter
                    for requirement in contract:
                        if not isinstance(requirement, dict):
                            safe_set = False
                            break
                        identity_suffix = hashlib.sha256(requirement.get("name", "").encode(
                            "utf-8")).hexdigest()[:12]
                        matches = []
                        for directory in root.glob(assignment_key + "*"):
                            try:
                                directory_info = directory.lstat()
                                if (not stat.S_ISDIR(directory_info.st_mode) or directory.is_symlink() or
                                        directory_info.st_uid != os.geteuid() or
                                        stat.S_IMODE(directory_info.st_mode) != 0o700):
                                    continue
                                candidate = directory / identity_suffix
                                if candidate.exists() or candidate.is_symlink():
                                    matches.append(candidate)
                            except OSError:
                                continue
                        if len(matches) != 1:
                            safe_set = False
                            break
                        artifact = matches[0]
                        try:
                            fd = os.open(artifact, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                            try:
                                info = os.fstat(fd)
                                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                                        (info.st_mode & 0o777) != 0o600 or
                                        not 0 < info.st_size <= requirement.get("max_bytes", 32768)):
                                    safe_set = False
                                    break
                                raw = os.read(fd, 32769)
                            finally:
                                os.close(fd)
                            if (len(raw) != info.st_size or not CodexCLIExecutionAdapter._valid_media(
                                    raw, requirement.get("media_type"))):
                                safe_set = False
                                break
                        except OSError:
                            safe_set = False
                            break
                        artifact_records.append({"name": requirement["name"],
                            "path": requirement["path"], "media_type": requirement["media_type"],
                            "storage_name": artifact.relative_to(root).as_posix(),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytes": len(raw), "acceptance_criteria": requirement["acceptance_criteria"]})
                    if not safe_set or len(artifact_records) != len(contract):
                        continue
                    artifact_name = artifact_records[0]["storage_name"]
                    artifact = root / artifact_name
                    criteria = step["acceptance_criteria"]
                    if (not isinstance(criteria, list) or not criteria or
                            any(not isinstance(item, str) or not item for item in criteria)):
                        continue
                    input_data = json.dumps({
                        "assignment_id": assignment["id"],
                        "objective_ref": assignment["objective_ref"],
                        "contract_ref": assignment["contract_ref"],
                        "knowledge_status": "VERIFIED",
                        "source_references": refs,
                        "source_revision": grounding["source_revision"],
                        "source_sha256": grounding["source_sha256"],
                        "retrieval_complete": True,
                    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    result = {
                        "status": "SUCCEEDED", "artifact_schema": "rv.codex-cli.artifacts.v3",
                        "capability": capability, "assignment_id": assignment["id"],
                        "objective_id": assignment["objective_id"],
                        "artifact_name": artifact_name, "artifact_path": str(artifact),
                        "artifact_sha256": artifact_records[0]["sha256"],
                        "artifact_bytes": artifact_records[0]["bytes"],
                        "source_artifact_name": artifact_records[0]["path"],
                        "changed_files": [item["path"] for item in contract],
                        "artifacts": artifact_records,
                        "artifact_contract": contract,
                        "change_set_proof": "codex-cli-fixed-output-after-pinned-worktree-check",
                        "source_revision": grounding["source_revision"],
                        "source_sha256": grounding["source_sha256"],
                        "repository_revision": repository_revision,
                        "acceptance_criteria": criteria,
                        "detail_code": "late_artifact_reconciled",
                    }
                    result_json = json.dumps(result, sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=False, allow_nan=False)
                    result_digest = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
                    attempt_id = uuid4()
                    attempt_key = f"late-codex-artifact:{assignment['id']}:{assignment['generation']}"
                    cur.execute("""INSERT INTO worker_attempts
                        (attempt_id,assignment_id,worker_id,lease_generation,capability,
                         idempotency_key,input_sha256,status,started_at,finished_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'succeeded',%s,clock_timestamp())""",
                        (attempt_id, assignment["id"], worker_id, assignment["generation"],
                         capability, attempt_key,
                         hashlib.sha256(input_data.encode("utf-8")).hexdigest(),
                         assignment["intent_started"]))
                    cur.execute("INSERT INTO worker_results(attempt_id,result,result_sha256) "
                                "VALUES (%s,%s::jsonb,%s)",
                                (attempt_id, result_json, result_digest))
                    cur.execute("""UPDATE worker_execution_intents
                        SET attempt_id=%s,status='succeeded'
                        WHERE intent_id=%s AND status='outcome_unknown'
                          AND failure_class='ProcessInterrupted'""",
                        (attempt_id, assignment["intent_id"]))
                    if cur.rowcount != 1:
                        raise RuntimeError("late Codex execution intent changed during reconciliation")
                    transition_evidence = {
                        "proof": "assignment_bound_late_codex_artifact",
                        "prior_outcome_unknown_record_preserved": True,
                        "execution_intent_failure_class": "ProcessInterrupted",
                        "artifact_name": artifact_name,
                        "artifact_sha256": result["artifact_sha256"],
                        "artifact_bytes": result["artifact_bytes"],
                        "repository_revision": repository_revision,
                        "independent_verification_required": True,
                        "exact_grant_revalidated": True,
                    }
                    self._transition_locked(cur, assignment, "awaiting_verification",
                        "RECOVERY_LATE_CODEX_ARTIFACT_PRESERVED",
                        f"late-codex-artifact:{assignment['id']}:{assignment['generation']}",
                        evidence=transition_evidence)
                    recovered.append({"assignment_id": assignment["id"],
                        "attempt_id": str(attempt_id), "artifact_sha256": result["artifact_sha256"],
                        "decision": "result_preserved", "resulting_state": "awaiting_verification"})
        return recovered

    def reconcile_confirmed_codex_preexecution_failures(
            self, *, repository_revision, artifact_root, scope_ref, worker_id,
            legacy_git_refusal_verified,
            limit=10):
        """Requeue only Codex failures proven to precede all durable effects.

        The caller must have reproduced Git's protected-configuration ownership
        refusal for the configured root-owned repository. Within one transaction
        this method requires either the predecessor outcome-unknown record or a
        worker-recorded failure before process launch, a mismatched immutable
        objective/repository provenance pair, a very short execution-intent
        duration, an expired lease, verified objective provenance, no attempts or
        verification, and no assignment-bound artifact. Recovery is bounded by
        the configured retry ceiling. Normal claim-time exact grants remain
        mandatory before any resumed action can execute.
        """
        if (not isinstance(scope_ref, str) or not scope_ref or
                not isinstance(worker_id, str) or not worker_id or
                legacy_git_refusal_verified is not True or
                not isinstance(repository_revision, str) or
                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", repository_revision) or
                not isinstance(limit, int) or not 1 <= limit <= 100):
            raise ValueError("confirmed Codex recovery evidence is invalid")
        root = Path(artifact_root)
        try:
            info = root.lstat()
            safe_root = (root.is_absolute() and root.is_dir() and not root.is_symlink() and
                         info.st_uid == os.geteuid() and
                         (info.st_mode & 0o777) == 0o700 and root.resolve() == root.absolute())
        except OSError:
            safe_root = False
        if not safe_root:
            raise ValueError("Codex artifact root is not a private owned directory")

        recovered = []
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT a.id,a.state,a.workflow_step,a.authority_ref,
                        a.correlation_id,a.objective_ref,l.generation,l.expires_at,
                        i.intent_id,i.worker_id,i.capability,i.effect_class,i.status AS intent_status,
                        i.failure_class,i.started_at,i.finished_at,o.source_revision
                    FROM assignments a
                    JOIN assignment_leases l ON l.assignment_id=a.id
                    JOIN worker_execution_intents i ON i.assignment_id=a.id
                        AND i.lease_generation=l.generation
                    JOIN grace_objectives o ON o.assignment_id=a.id
                        AND o.objective_id=a.objective_ref
                    WHERE a.authority_ref=%s AND i.worker_id=%s AND ((a.state='awaiting_steward'
                            AND a.workflow_step='ACTION_OUTCOME_UNKNOWN'
                            AND i.status='outcome_unknown')
                        OR (a.state='blocked'
                            AND a.workflow_step='WORKER_PRE_EXECUTION_FAILED'
                            AND i.status='failed'))
                      AND l.expires_at<=clock_timestamp()
                      AND i.capability='engineering.codex-cli-artifact.v1'
                      AND i.effect_class='external_uncertain'
                      AND (i.failure_class='CodexActionFailure'
                           OR i.failure_class LIKE 'CodexActionFailure:%%')
                      AND i.finished_at-i.started_at<=interval '2 seconds'
                      AND o.status='WORK_ORDER_CREATED'
                      AND o.assignment_id=a.id
                      AND o.evidence->>'status'='VERIFIED'
                      AND o.source_revision IS NOT NULL
                      AND o.source_revision<>%s
                    ORDER BY i.started_at,a.id
                    FOR UPDATE OF a,l,i SKIP LOCKED LIMIT %s""",
                    (scope_ref, worker_id, repository_revision, limit))
                candidates = cur.fetchall()
                for candidate in candidates:
                    assignment_id = candidate["id"]
                    generation = candidate["generation"]
                    if self.max_retries is not None:
                        cur.execute("SELECT count(*) AS n FROM worker_recovery_records "
                                    "WHERE assignment_id=%s AND decision='retry_safe'",
                                    (assignment_id,))
                        if int(cur.fetchone()["n"]) >= self.max_retries:
                            continue
                    if _codex_artifact_files(root, assignment_id):
                        continue
                    cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                                (assignment_id,))
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    cur.execute("SELECT count(*) AS n FROM verification_records WHERE assignment_id=%s",
                                (assignment_id,))
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    cur.execute("SELECT 1 FROM worker_recovery_records "
                                "WHERE assignment_id=%s AND lease_generation=%s",
                                (assignment_id, generation))
                    if cur.fetchone() is not None:
                        continue
                    cur.execute("""INSERT INTO worker_recovery_records
                        (assignment_id,lease_generation,intent_id,attempt_id,decision,
                         previous_state,resulting_state,observed_expiry)
                        VALUES (%s,%s,%s,NULL,'retry_safe',%s,'ready',%s)""",
                        (assignment_id, generation, candidate["intent_id"],
                         candidate["state"], candidate["expires_at"]))
                    cur.execute("""UPDATE worker_execution_intents
                        SET status='retry_scheduled',finished_at=clock_timestamp()
                        WHERE intent_id=%s AND assignment_id=%s
                          AND lease_generation=%s AND status=%s""",
                        (candidate["intent_id"], assignment_id, generation,
                         candidate["intent_status"]))
                    if cur.rowcount != 1:
                        raise RuntimeError("Codex recovery intent changed during reconciliation")
                    evidence = {
                        "proof": ("legacy_git_safe_directory_refusal_before_cli_launch"
                                  if candidate["intent_status"] == "outcome_unknown" else
                                  "durable_worker_preexecution_failure_before_cli_launch"),
                        "legacy_failure_class": candidate["failure_class"],
                        "execution_process_started": False,
                        "assignment_attempt_absent": True,
                        "verification_absent": True,
                        "assignment_artifact_absent": True,
                        "knowledge_source_revision": candidate["source_revision"],
                        "execution_repository_revision": repository_revision,
                        "intent_id": str(candidate["intent_id"]),
                    }
                    key = f"codex-preexecution-recovery:{assignment_id}:{generation}:ready"
                    self._transition_locked(cur, candidate, "ready",
                        "RECOVERY_CONFIRMED_PREEXECUTION_NO_EFFECT", key,
                        evidence=evidence)
                    recovered.append({"assignment_id": assignment_id,
                        "intent_id": str(candidate["intent_id"]),
                        "lease_generation": generation, "decision": "retry_safe",
                        "resulting_state": "ready"})
        return recovered

    def reconcile_codex_failures_without_artifact(
            self, *, repository_revision, artifact_root, scope_ref, worker_id,
            capability="engineering.codex-cli-artifact.v1", limit=10):
        """Retry completed typed Codex failures only when no durable result exists.

        Codex executes in a fresh network-disabled temporary clone. Its adapter
        copies a file into the assignment artifact store only on
        DELIVERABLE_PRODUCED. A CodexActionFailure is retried only when the
        assignment has no prior durable effect. A narrowly proven
        ObjectiveStateError during same-assignment rework may retain earlier
        rejected artifacts and verification, but requires a matching durable
        REWORK_PROPOSED decision, no current-generation attempt/result/artifact,
        a finished sub-two-second intent, and an expired lease. Claim-time exact
        worker grants are still revalidated by the normal adapter.
        """
        if (not isinstance(repository_revision, str) or
                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", repository_revision) or
                not isinstance(scope_ref, str) or not scope_ref or
                not isinstance(worker_id, str) or not worker_id or
                capability not in {"engineering.codex-cli-artifact.v1",
                                   "engineering.codex-cli-source-change.v1"} or
                type(limit) is not int or not 1 <= limit <= 100):
            raise ValueError("Codex retry evidence is invalid")
        root = Path(artifact_root)
        try:
            info = root.lstat()
            safe_root = (root.is_absolute() and root.is_dir() and not root.is_symlink() and
                         info.st_uid == os.geteuid() and (info.st_mode & 0o777) == 0o700 and
                         root.resolve() == root.absolute())
        except OSError:
            safe_root = False
        if not safe_root:
            raise ValueError("Codex artifact root is not a private owned directory")

        recovered = []
        with self.ledger.db.transaction():
            with self.ledger.db.cursor() as cur:
                self.ledger._set_search_path(cur)
                cur.execute("""SELECT a.id,a.state,a.workflow_step,a.authority_ref,
                        a.correlation_id,a.objective_ref,l.generation,l.expires_at,
                        i.intent_id,i.capability,i.effect_class,i.status AS intent_status,
                        i.failure_class,i.attempt_id,i.started_at,i.finished_at,
                        o.source_revision,o.source_sha256,o.evidence
                    FROM assignments a
                    JOIN assignment_leases l ON l.assignment_id=a.id
                    JOIN worker_execution_intents i ON i.assignment_id=a.id
                        AND i.lease_generation=l.generation
                    JOIN grace_objectives o ON o.objective_id=a.objective_ref
                    JOIN grace_objective_steps s ON s.objective_id=o.objective_id
                        AND s.assignment_id=a.id
                        AND EXISTS (
                            SELECT 1 FROM grace_objective_events dispatched
                            WHERE dispatched.objective_id=s.objective_id
                              AND dispatched.event_type='work_order.dispatched'
                              AND dispatched.payload->>'assignment_id'=a.id
                              AND dispatched.payload->>'workflow_step'=s.step_id)
                    WHERE a.authority_ref=%s AND i.worker_id=%s AND ((a.state='awaiting_steward'
                            AND a.workflow_step='ACTION_OUTCOME_UNKNOWN'
                            AND i.status='outcome_unknown')
                        OR (a.state='blocked'
                            AND a.workflow_step='WORKER_RETRYABLE_NO_ARTIFACT'
                            AND i.status='failed'))
                      AND l.expires_at<=clock_timestamp()
                      AND i.capability=%s
                      AND i.effect_class=%s
                      AND ((i.failure_class='CodexActionFailure'
                            OR i.failure_class LIKE 'CodexActionFailure:%%')
                        OR (i.failure_class='ObjectiveStateError'
                            AND i.attempt_id IS NULL
                            AND i.finished_at-i.started_at<=interval '2 seconds'
                            AND EXISTS (
                                SELECT 1 FROM grace_objective_events rd
                                JOIN verification_records vr
                                  ON vr.assignment_id=a.id
                                 AND vr.verification_id::text=rd.payload->>'verification_id'
                                 AND vr.decision='REJECTED'
                                WHERE rd.objective_id=o.objective_id
                                  AND rd.event_type='engineering.rework_decided'
                                  AND rd.payload->>'assignment_id'=a.id
                                  AND rd.payload->>'decision'='REWORK_PROPOSED'
                                  AND rd.sequence=(SELECT max(latest.sequence)
                                    FROM grace_objective_events latest
                                    WHERE latest.objective_id=o.objective_id
                                      AND latest.event_type='engineering.rework_decided'
                                      AND latest.payload->>'assignment_id'=a.id))))
                      AND i.finished_at IS NOT NULL
                      AND o.status='WORK_ORDER_CREATED'
                      AND o.evidence->>'status'='VERIFIED'
                      AND o.source_revision IS NOT NULL
                      AND o.source_sha256 IS NOT NULL
                      AND o.evidence->>'source_revision'=o.source_revision
                      AND o.evidence->>'source_sha256'=o.source_sha256
                      AND EXISTS (
                          SELECT 1 FROM jsonb_array_elements(o.proposal->'steps')
                              AS proposal_step(value)
                          WHERE proposal_step.value->>'step_id'=s.step_id
                            AND proposal_step.value->>'objective'=s.step_objective
                            AND proposal_step.value->'acceptance_criteria'=s.acceptance_criteria)
                    ORDER BY i.started_at,a.id
                    FOR UPDATE OF a,l,i SKIP LOCKED LIMIT %s""",
                    (scope_ref, worker_id, capability,
                     "retry_safe" if capability ==
                        "engineering.codex-cli-source-change.v1" else "external_uncertain",
                     limit))
                for candidate in cur.fetchall():
                    assignment_id = candidate["id"]
                    generation = candidate["generation"]
                    if self.max_retries is not None:
                        cur.execute("SELECT count(*) AS n FROM worker_recovery_records "
                                    "WHERE assignment_id=%s AND decision='retry_safe'",
                                    (assignment_id,))
                        if int(cur.fetchone()["n"]) >= self.max_retries:
                            continue
                    if capability == "engineering.codex-cli-source-change.v1":
                        artifact = root / ("codex-source-" + hashlib.sha256(
                            assignment_id.encode("utf-8")).hexdigest() + ".patch")
                        artifact_present = artifact.exists() or artifact.is_symlink()
                    else:
                        artifact_present = bool(_codex_artifact_files(root, assignment_id))
                    preexecution_state_error = (
                        candidate["failure_class"] == "ObjectiveStateError" and
                        candidate["attempt_id"] is None and
                        candidate["finished_at"] - candidate["started_at"] <=
                            timedelta(seconds=2))
                    if artifact_present and not preexecution_state_error:
                        continue
                    if preexecution_state_error and any(
                            path.stat().st_mtime >= candidate["started_at"].timestamp()
                            for path in _codex_artifact_files(root, assignment_id)):
                        continue
                    attempt_sql = ("SELECT count(*) AS n FROM worker_attempts "
                        "WHERE assignment_id=%s AND lease_generation=%s" if preexecution_state_error else
                        "SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s")
                    attempt_params = ((assignment_id, generation) if preexecution_state_error else
                                      (assignment_id,))
                    cur.execute(attempt_sql, attempt_params)
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    result_sql = ("SELECT count(*) AS n FROM worker_results r "
                        "JOIN worker_attempts a USING(attempt_id) "
                        "WHERE a.assignment_id=%s AND a.lease_generation=%s"
                        if preexecution_state_error else
                        "SELECT count(*) AS n FROM worker_results r "
                        "JOIN worker_attempts a USING(attempt_id) WHERE a.assignment_id=%s")
                    result_params = ((assignment_id, generation) if preexecution_state_error else
                                     (assignment_id,))
                    cur.execute(result_sql, result_params)
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    if not preexecution_state_error:
                        cur.execute("SELECT count(*) AS n FROM verification_records WHERE assignment_id=%s",
                                    (assignment_id,))
                        if int(cur.fetchone()["n"]) != 0:
                            continue
                    cur.execute("SELECT 1 FROM worker_recovery_records "
                                "WHERE assignment_id=%s AND lease_generation=%s",
                                (assignment_id, generation))
                    if cur.fetchone() is not None:
                        continue

                    cur.execute("""INSERT INTO worker_recovery_records
                        (assignment_id,lease_generation,intent_id,attempt_id,decision,
                         previous_state,resulting_state,observed_expiry)
                        VALUES (%s,%s,%s,NULL,'retry_safe',%s,'ready',%s)""",
                        (assignment_id, generation, candidate["intent_id"],
                         candidate["state"], candidate["expires_at"]))
                    cur.execute("""UPDATE worker_execution_intents
                        SET status='retry_scheduled',finished_at=clock_timestamp()
                        WHERE intent_id=%s AND assignment_id=%s AND lease_generation=%s
                          AND status=%s""",
                        (candidate["intent_id"], assignment_id, generation,
                         candidate["intent_status"]))
                    if cur.rowcount != 1:
                        raise RuntimeError("Codex retry intent changed during reconciliation")
                    evidence = {
                        "proof": ("typed_codex_preexecution_state_error_during_rework"
                            if preexecution_state_error else
                            "typed_codex_failure_without_durable_artifact"),
                        "execution_intent_finished": True,
                        "execution_process_started": False if preexecution_state_error else None,
                        "current_generation_attempt_absent": True,
                        "current_generation_result_absent": True,
                        "prior_rejected_verification_preserved": bool(preexecution_state_error),
                        "prior_artifacts_preserved": bool(preexecution_state_error),
                        "assignment_attempt_absent": not preexecution_state_error,
                        "worker_result_absent": not preexecution_state_error,
                        "verification_absent": not preexecution_state_error,
                        "assignment_artifact_absent": not preexecution_state_error,
                        "knowledge_source_revision": candidate["source_revision"],
                        "execution_repository_revision": repository_revision,
                        "execution_capability": capability,
                        "intent_id": str(candidate["intent_id"]),
                    }
                    key = f"codex-no-artifact-recovery:{assignment_id}:{generation}:ready"
                    self._transition_locked(cur, candidate, "ready",
                        "CODEX_FAILURE_NO_DURABLE_ARTIFACT", key, evidence=evidence)
                    recovered.append({"assignment_id": assignment_id,
                        "intent_id": str(candidate["intent_id"]),
                        "lease_generation": generation, "decision": "retry_safe",
                        "resulting_state": "ready"})
        return recovered
