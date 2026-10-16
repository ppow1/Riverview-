# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/worker_adapter/recovery.py
# Component: WORKER-ADAPTER
# Revision: 1.2.7
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
# Contracts: docs/ROADMAP.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_worker_adapter.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Recover expired leases and narrowly proven no-durable-artifact Codex failures."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

from ..ledger import TRANSITIONS
from ..postgres_ledger import PostgresLedger, assignment_process_position
from .knowledge import KnowledgeResult, KnowledgeStatus


class PostgresRecoveryCoordinator:
    """Atomically reconcile expired leases and persist each recovery decision."""

    def __init__(self, dsn, *, schema="public", max_retries=None):
        if max_retries is not None and (type(max_retries) is not int or not 0 <= max_retries <= 100):
            raise ValueError("max_retries must be None or an integer from 0 to 100")
        self.ledger = PostgresLedger(dsn, schema=schema)
        self.schema = schema
        self.max_retries = max_retries

    def close(self):
        self.ledger.close()

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
        artifact_name = "codex-" + hashlib.sha256(assignment_id.encode("utf-8")).hexdigest() + ".md"
        artifact = root / artifact_name

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
                            {"ground_assignment", "reground_assignment", "preflight_action"} or
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
                if artifact.exists() or artifact.is_symlink():
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
                    cur.execute("""SELECT step_objective,acceptance_criteria
                        FROM grace_objective_steps WHERE objective_id=%s AND assignment_id=%s""",
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
                    artifact_name = "codex-" + hashlib.sha256(
                        assignment["id"].encode("utf-8")).hexdigest() + ".md"
                    artifact = root / artifact_name
                    try:
                        fd = os.open(artifact, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                        try:
                            info = os.fstat(fd)
                            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                                    (info.st_mode & 0o777) != 0o600 or
                                    not 0 < info.st_size <= 32 * 1024):
                                continue
                            raw = os.read(fd, 32 * 1024 + 1)
                        finally:
                            os.close(fd)
                        body = raw.decode("utf-8")
                        if (not body.startswith("# ") or len(raw) != info.st_size or
                                artifact.is_symlink()):
                            continue
                    except (OSError, UnicodeError):
                        continue
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
                        "status": "SUCCEEDED", "artifact_schema": "rv.codex-cli.deliverable.v2",
                        "capability": capability, "assignment_id": assignment["id"],
                        "objective_id": assignment["objective_id"],
                        "artifact_name": artifact_name, "artifact_path": str(artifact),
                        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
                        "artifact_bytes": len(raw),
                        "source_artifact_name": "deliverable.md",
                        "changed_files": ["deliverable.md"],
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
                    artifact_name = "codex-" + hashlib.sha256(
                        assignment_id.encode("utf-8")).hexdigest() + ".md"
                    artifact = root / artifact_name
                    if artifact.exists() or artifact.is_symlink():
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
            self, *, repository_revision, artifact_root, scope_ref, worker_id, limit=10):
        """Retry completed typed Codex failures only when no durable result exists.

        Codex executes in a fresh network-disabled temporary clone. Its adapter
        copies a file into the assignment artifact store only on
        DELIVERABLE_PRODUCED. A CodexActionFailure therefore has no durable
        artifact effect; before retry this method independently checks the
        assignment-bound artifact path, attempts, results and verifications,
        plus the expired lease and configured retry ceiling. Claim-time exact
        worker grants are still revalidated by the normal adapter.
        """
        if (not isinstance(repository_revision, str) or
                not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", repository_revision) or
                not isinstance(scope_ref, str) or not scope_ref or
                not isinstance(worker_id, str) or not worker_id or
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
                        i.failure_class,o.source_revision,o.source_sha256,o.evidence
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
                            AND a.workflow_step='WORKER_RETRYABLE_NO_ARTIFACT'
                            AND i.status='failed'))
                      AND l.expires_at<=clock_timestamp()
                      AND i.capability='engineering.codex-cli-artifact.v1'
                      AND i.effect_class='external_uncertain'
                      AND (i.failure_class='CodexActionFailure'
                           OR i.failure_class LIKE 'CodexActionFailure:%%')
                      AND i.finished_at IS NOT NULL
                      AND o.status='WORK_ORDER_CREATED'
                      AND o.assignment_id=a.id
                      AND o.evidence->>'status'='VERIFIED'
                      AND o.source_revision IS NOT NULL
                      AND o.source_sha256 IS NOT NULL
                      AND o.evidence->>'source_revision'=o.source_revision
                      AND o.evidence->>'source_sha256'=o.source_sha256
                    ORDER BY i.started_at,a.id
                    FOR UPDATE OF a,l,i SKIP LOCKED LIMIT %s""", (scope_ref, worker_id, limit))
                for candidate in cur.fetchall():
                    assignment_id = candidate["id"]
                    generation = candidate["generation"]
                    if self.max_retries is not None:
                        cur.execute("SELECT count(*) AS n FROM worker_recovery_records "
                                    "WHERE assignment_id=%s AND decision='retry_safe'",
                                    (assignment_id,))
                        if int(cur.fetchone()["n"]) >= self.max_retries:
                            continue
                    artifact_name = "codex-" + hashlib.sha256(
                        assignment_id.encode("utf-8")).hexdigest() + ".md"
                    artifact = root / artifact_name
                    if artifact.exists() or artifact.is_symlink():
                        continue
                    cur.execute("SELECT count(*) AS n FROM worker_attempts WHERE assignment_id=%s",
                                (assignment_id,))
                    if int(cur.fetchone()["n"]) != 0:
                        continue
                    cur.execute("SELECT count(*) AS n FROM worker_results r "
                                "JOIN worker_attempts a USING(attempt_id) "
                                "WHERE a.assignment_id=%s", (assignment_id,))
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
                        WHERE intent_id=%s AND assignment_id=%s AND lease_generation=%s
                          AND status=%s""",
                        (candidate["intent_id"], assignment_id, generation,
                         candidate["intent_status"]))
                    if cur.rowcount != 1:
                        raise RuntimeError("Codex retry intent changed during reconciliation")
                    evidence = {
                        "proof": "typed_codex_failure_without_durable_artifact",
                        "execution_intent_finished": True,
                        "assignment_attempt_absent": True,
                        "worker_result_absent": True,
                        "verification_absent": True,
                        "assignment_artifact_absent": True,
                        "knowledge_source_revision": candidate["source_revision"],
                        "execution_repository_revision": repository_revision,
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
