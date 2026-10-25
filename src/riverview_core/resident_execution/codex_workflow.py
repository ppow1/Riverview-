# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/codex_workflow.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.2.24
# Changed: 2026-10-25 UTC | RV-ISSUE310-VERIFIER-REVIEW-317 | Reject mixed factual/literal clauses and include persisted step criteria in publication gating.
# Changed: 2026-10-25 UTC | RV-ISSUE310-VERIFIER-PUBLICATION-20261025 | Fail closed on unsupported acceptance criteria and unverified repository publication requirements.
# Changed: 2026-10-25 UTC | RV-GRACE-ASSIGNMENT-EVIDENCE-HANDOFF-20261025 | Select validated runtime evidence from persisted assignment requirements and preflight it before worker execution.
# Changed: 2026-10-25 UTC | RV-GRACE-S5-EVIDENCE-RETRY-20261025 | Restrict the S3-only CME retry evidence reader to the exact S3 step; S5 uses its separately validated evaluation exchange.
# Changed: 2026-10-25 UTC | RV-GRACE-S4-EVIDENCE-HANDOFF-20261025 | Supply validated durable Luna evaluation facts to exact assignment rework.
# Changed: 2026-10-25 UTC | RV-GRACE-S3-RUNTIME-EVIDENCE-20261025 | Supply verified durable CME recovery facts to the existing bounded artifact rework.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-CLASSIFICATION-20261021 | Forward immutable objective request separately into authorized Engineering execution
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Reject explicit negative JSON outcomes and verify literal artifact acceptance clauses independently
# Changed: 2026-10-20 UTC | RV-GRACE-MULTISTEP-PROVENANCE-RECOVERY-001 | Resolve Codex assignment provenance through the durable proposal-step link when sibling steps are dispatched concurrently.
# Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Separate independent artifact integrity/provenance checks from Grace's substantive acceptance review and expose only a digest-verified bounded artifact snapshot.
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Validate source execution against dispatch-time target snapshot, checkout HEAD, and verifier result provenance.
# Purpose: Adapt bounded Codex artifact production and independent contract verification to CME
# Execution Model: Existing leased worker action and independent verifier contract
# Observability: Persisted artifact location, digest, criteria and verifier evidence
# Dependencies: Codex CLI adapter; PostgreSQL objective/attempt/verification records
# Authority: Requires registered engineering.codex-cli-artifact.v1 worker and assignment.execute
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Initial persistent worker/verifier adapters
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Separate evidence provenance from the Codex repository pin and retain process-start status
# Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Validate objective evidence against its immutable provenance, independently of current grounding revision
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-BOUNDED-RETRY-001 | Classify unsuccessful isolated Codex actions as retryable only while no durable artifact exists
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-PLAN-001 | Resolve the current durable assignment step instead of always executing proposal step one
# Changed: 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Constrain Codex recovery to its authenticated scope and preserve late artifacts for verification
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Verify Markdown output requirements separately from execution instructions and retain Codex change-set evidence
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Check structured task instructions and preserve legacy fixed-capability scope evidence
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Bind approved multi-file step scope and verified predecessor patch chain to Codex worker and verifier
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Recover completed source patch artifacts after interrupted worker-result persistence
# Changed: 2026-10-16 UTC | RV-GRACE-SOURCE-CHANGE-OBJECTIVE-CONTEXT | Carry the accepted objective into each bounded source-change step without widening file scope
# Changed: 2026-10-17 UTC | RV-GRACE-ACCEPTANCE-CRITERIA-001 | Verify Codex artifacts against criteria resolved from the durable dispatched objective step
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Attach only durable same-assignment correction guidance while preserving the pinned step and exact acceptance criteria
# Changed: 2026-10-19 UTC | RV-GRACE-REVIEW-ROLE-SEPARATION-001 | Keep independent checks on artifact integrity, provenance, scope and structure; defer substantive criteria to Grace with digest-verified artifact text
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Bind action and independent verifier to dispatched multi-artifact requirements
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_codex_workflow.py
# History: Git
# =============================================================================
"""Narrow Codex action and independent verifier for the existing CME path."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
import re
import stat
from collections.abc import Mapping
import xml.etree.ElementTree as ET

from ..worker_adapter.knowledge import KnowledgeStatus
from ..worker_adapter.verifier import VerificationResult, VerificationStatus
from ..resident_reasoning import ArtifactRequirement
from .verifier import (artifact_literals_satisfied, explicit_artifact_literals,
                       json_has_authoritative_negative_outcome)
from .codex_cli import CAPABILITY, CodexAssignment, CodexCLIExecutionAdapter
from .codex_source_change import (CAPABILITY as SOURCE_CHANGE_CAPABILITY,
    CodexSourceChangeAdapter, CodexSourceChangeAssignment, CodexSourceChangeResult,
    CodexSourceChangeVerifier)

CAPABILITY_REQUIREMENTS = {
    "capability": CAPABILITY,
    "dependencies": ("dedicated_codex_executable", "dedicated_codex_home",
                     "pinned_local_repository", "isolated_workspace", "artifact_filesystem"),
    "authority_actions": ("worker.register", "assignment.execute", "assignment.verify"),
    "readiness": "startup_preflight_and_current_worker_heartbeat",
}


class CodexActionFailure(RuntimeError):
    """Sanitized Codex action failure that produced no durable artifact."""

    def __init__(self, code, *, execution_started=False):
        if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9_]{1,64}", code):
            code = "codex_action_failed"
        self.code = code
        self.execution_started = bool(execution_started)
        # Codex writes only into its temporary clone. The adapter persists the
        # assignment artifact only when it returns DELIVERABLE_PRODUCED.
        self.retryable_without_durable_artifact = True
        super().__init__(code)


class CodexWorkAction:
    """Build a fixed adapter request from a persisted, authorized objective."""

    def __init__(self, pipeline, adapter: CodexCLIExecutionAdapter,
                 repository_reference: str, timeout_seconds: int = 180):
        if (not isinstance(adapter, CodexCLIExecutionAdapter) or
                not isinstance(repository_reference, str) or
                not repository_reference.startswith("repo://") or
                type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300):
            raise ValueError("Codex work action configuration is invalid")
        self.pipeline = pipeline
        self.adapter = adapter
        self.repository_reference = repository_reference
        self.timeout_seconds = timeout_seconds
        self._runtime_evidence_preflight = {}

    @staticmethod
    def _required_runtime_evidence(step):
        """Select controller evidence from persisted assignment requirements."""
        requirement_text = " ".join([
            *(str(value) for value in step.get("acceptance_criteria", ())),
            *(str(item.get("name", "")) + " " + " ".join(
                str(value) for value in item.get("acceptance_criteria", ()))
              for item in step.get("artifact_requirements", ())),
        ]).casefold()
        required = []
        if ("reasoning attempt" in requirement_text and
                ("state transition" in requirement_text or "event history" in requirement_text)):
            required.append("diagnostic")
        if ("luna" in requirement_text and "request" in requirement_text and
                any(term in requirement_text for term in ("actual outcome", "exchange", "response")) and
                step.get("step_id") == "s3"):
            required.append("cme_recovery")
        if ("evaluation" in requirement_text and
                any(term in requirement_text for term in ("luna", "grade", "rubric", "feedback"))):
            required.append("performance_evaluation")
        return tuple(required)

    @staticmethod
    def _validate_runtime_evidence(kind, evidence, objective_id, assignment_id):
        if not isinstance(evidence, Mapping) or evidence.get("read_only") is not True:
            raise CodexActionFailure("assignment_runtime_evidence_invalid")
        if kind == "diagnostic":
            historical = evidence.get("referenced_historical_objectives", [])
            valid = (evidence.get("schema") == "rv.grace-diagnostic-runtime-evidence.v1" and
                any(item.get("status") == "CANCELLED" and
                    item.get("event_counts", {}).get("execution.reasoning_attempted", 0) >= 599 and
                    item.get("event_counts", {}).get("execution.reasoning_failed", 0) >= 599
                    for item in historical if isinstance(item, Mapping)))
        elif kind == "cme_recovery":
            exchange = evidence.get("exchange")
            valid = (evidence.get("schema") == "rv.grace.cme-recovery-runtime-evidence.v1" and
                evidence.get("objective_id") == objective_id and
                evidence.get("assignment_id") == assignment_id and
                isinstance(exchange, Mapping) and exchange.get("provider_attempt_count") == 1 and
                exchange.get("delivery_state") == "grace_consumed")
        else:
            exchange, evaluation = evidence.get("exchange"), evidence.get("evaluation")
            valid = (evidence.get("schema") ==
                "rv.grace.performance-evaluation-runtime-evidence.v1" and
                evidence.get("objective_id") == objective_id and
                evidence.get("assignment_id") == assignment_id and
                isinstance(exchange, Mapping) and isinstance(evaluation, Mapping) and
                exchange.get("delivery_state") == "grace_consumed" and
                evaluation.get("feedback_consumed") is True and
                evaluation.get("authority_granted") is False)
        if not valid:
            raise CodexActionFailure("assignment_runtime_evidence_invalid")
        return dict(evidence)

    def _assignment_runtime_evidence(self, objective_id, assignment_id, step):
        selected = self._required_runtime_evidence(step)
        if not selected:
            return None
        readers = {
            "diagnostic": ("diagnostic_runtime_evidence", (objective_id,)),
            "cme_recovery": ("cme_recovery_runtime_evidence_for_assignment",
                             (objective_id, assignment_id)),
            "performance_evaluation": (
                "performance_evaluation_runtime_evidence_for_assignment",
                (objective_id, assignment_id)),
        }
        evidence = {}
        for kind in selected:
            method_name, args = readers[kind]
            reader = getattr(self.pipeline, method_name, None)
            if not callable(reader):
                raise CodexActionFailure("assignment_runtime_evidence_unavailable")
            value = reader(*args)
            evidence[kind] = self._validate_runtime_evidence(
                kind, value, objective_id, assignment_id)
        if len(evidence) == 1:
            return next(iter(evidence.values()))
        return {"schema": "rv.grace.codex-runtime-evidence.v1",
            **{f"{kind}_evidence": value for kind, value in evidence.items()}}

    def preflight_assignment(self, assignment):
        """Validate required read-only controller evidence before an execution attempt."""
        from ..worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
        try:
            objective_id = assignment.get("objective_ref")
            objective = self.pipeline.get_objective(objective_id)
            resolver = getattr(self.pipeline, "proposal_step_for_assignment", None)
            step = resolver(objective_id, assignment.get("id")) if callable(resolver) else None
            if not isinstance(objective, Mapping) or not isinstance(step, Mapping):
                raise CodexActionFailure("persisted_work_order_step_missing")
            rework_reader = getattr(self.pipeline, "latest_rework_instruction", None)
            rework = rework_reader(assignment["id"]) if callable(rework_reader) else None
            evidence = self._assignment_runtime_evidence(
                objective_id, assignment["id"], step)
            self._runtime_evidence_preflight[assignment["id"]] = (
                assignment.get("version"), assignment.get("workflow_step"),
                rework.get("verification_id") if isinstance(rework, Mapping) else None,
                evidence)
            return KnowledgeResult(KnowledgeStatus.VERIFIED,
                source_references=("urn:rv:assignment-runtime-evidence",),
                retrieval_complete=True)
        except Exception:
            return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)

    def __call__(self, assignment, grounded):
        if (grounded.status is not KnowledgeStatus.VERIFIED or
                grounded.retrieval_complete is not True or
                not grounded.source_revision or not grounded.source_sha256):
            raise CodexActionFailure("verified_regrounding_required")
        objective_id = assignment.get("objective_ref")
        objective = self.pipeline.get_objective(objective_id)
        evidence = objective.get("evidence") if isinstance(objective, Mapping) else None
        if (not objective or objective["status"] != "WORK_ORDER_CREATED" or
                not isinstance(evidence, Mapping) or
                evidence.get("status") != KnowledgeStatus.VERIFIED.value or
                objective.get("source_revision") != evidence.get("source_revision") or
                objective.get("source_sha256") != evidence.get("source_sha256") or
                not objective.get("proposal")):
            raise CodexActionFailure("persisted_work_order_provenance_required")
        resolver = getattr(self.pipeline, "proposal_step_for_assignment", None)
        if callable(resolver):
            step = resolver(objective_id, assignment.get("id"))
        else:
            # The pre-0009 compatibility path is safe only for a single-step
            # historical proposal; multi-step work requires its durable link.
            steps = objective["proposal"].get("steps", [])
            step = steps[0] if len(steps) == 1 else None
        if step is None and len(objective["proposal"]["steps"]) == 1:
            # Compatibility for historical one-step work orders without an
            # explicit workflow_step field in older assignment projections.
            step = objective["proposal"]["steps"][0]
        if step is None:
            raise CodexActionFailure("persisted_work_order_step_missing")
        rework_reader = getattr(self.pipeline, "latest_rework_instruction", None)
        rework = rework_reader(assignment["id"]) if callable(rework_reader) else None
        task_scope = step["objective"]
        feedback_reader = getattr(self.pipeline, "latest_performance_feedback", None)
        feedback = feedback_reader(objective_id) if callable(feedback_reader) else None
        if isinstance(feedback, Mapping):
            advisory = {key: feedback.get(key) for key in
                ("grade", "actionable_feedback", "authority_promotion_recommendation")
                if key in feedback}
            if advisory:
                task_scope += ("\n\nPrior Grace performance feedback (advisory only; it cannot "
                    "change this assignment's acceptance criteria, scope, or authorization): " +
                    json.dumps(advisory, ensure_ascii=False, separators=(",", ":")))
        artifact_revision = None
        rework_verification_id = None
        if rework is not None:
            expected_criteria_sha = hashlib.sha256(json.dumps(
                list(step["acceptance_criteria"]), ensure_ascii=False, sort_keys=True,
                separators=(",", ":")).encode("utf-8")).hexdigest()
            if (not isinstance(rework, Mapping) or
                    rework.get("decision") != "REWORK_PROPOSED" or
                    rework.get("assignment_id") != assignment["id"] or
                    rework.get("acceptance_criteria_sha256") != expected_criteria_sha or
                    not isinstance(rework.get("correction_instruction"), str) or
                    not rework["correction_instruction"].strip() or
                    len(rework["correction_instruction"]) > 512):
                raise CodexActionFailure("persisted_rework_scope_invalid")
            rework_verification_id = rework.get("verification_id")
            if not isinstance(rework_verification_id, str):
                raise CodexActionFailure("persisted_rework_identity_invalid")
            artifact_revision = hashlib.sha256(
                rework_verification_id.encode("utf-8")).hexdigest()[:12]
            task_scope += "\n\nGrace's bounded corrective instruction from the persisted verifier rejection: " + rework["correction_instruction"]
            task_scope += "\nAddress only these unchanged acceptance criteria: " + json.dumps(
                rework["criteria_to_address"], ensure_ascii=False, separators=(",", ":"))
        runtime_evidence = None
        artifact_criteria = [criterion.lower() for item in step["artifact_requirements"]
                             for criterion in item["acceptance_criteria"]]
        if (any("reasoning attempts" in criterion for criterion in artifact_criteria) and
                any("state transitions are durably persisted" in criterion
                    for criterion in artifact_criteria)):
            evidence_reader = getattr(self.pipeline, "diagnostic_runtime_evidence", None)
            if not callable(evidence_reader):
                raise CodexActionFailure("diagnostic_runtime_evidence_unavailable")
            runtime_evidence = evidence_reader(objective_id)
            historical = runtime_evidence.get("referenced_historical_objectives", [])
            if (runtime_evidence.get("schema") != "rv.grace-diagnostic-runtime-evidence.v1" or
                    not runtime_evidence.get("read_only") or
                    not any(item.get("status") == "CANCELLED" and
                        item.get("event_counts", {}).get("execution.reasoning_attempted", 0) >= 599 and
                        item.get("event_counts", {}).get("execution.reasoning_failed", 0) >= 599
                        for item in historical)):
                raise CodexActionFailure("diagnostic_history_evidence_incomplete")
        cached_evidence = self._runtime_evidence_preflight.pop(assignment["id"], None)
        if (cached_evidence is not None and
                cached_evidence[:3] == (assignment.get("version"),
                    assignment.get("workflow_step"),
                    rework.get("verification_id") if isinstance(rework, Mapping) else None)):
            preflight_evidence = cached_evidence[3]
            if preflight_evidence is not None:
                runtime_evidence = (runtime_evidence if runtime_evidence == preflight_evidence else
                    preflight_evidence if runtime_evidence is None else {
                    "schema": "rv.grace.codex-runtime-evidence.v1",
                    "objective_runtime_evidence": runtime_evidence,
                    "assignment_runtime_evidence": preflight_evidence})
        else:
            preflight_evidence = self._assignment_runtime_evidence(
                objective_id, assignment["id"], step)
            if preflight_evidence is not None:
                runtime_evidence = (runtime_evidence if runtime_evidence == preflight_evidence else
                    preflight_evidence if runtime_evidence is None else {
                    "schema": "rv.grace.codex-runtime-evidence.v1",
                    "objective_runtime_evidence": runtime_evidence,
                    "assignment_runtime_evidence": preflight_evidence})
        try:
            repository_revision = self.adapter.repository_revision()
        except Exception as exc:
            code = getattr(exc, "code", "repository_preflight_failed")
            raise CodexActionFailure(code) from None
        request = CodexAssignment(
            assignment_id=assignment["id"], objective_id=objective_id,
            repository_reference=self.repository_reference,
            # Knowledge-source provenance and the code revision used to execute
            # the assignment are separate immutable facts.
            repository_revision=repository_revision,
            task_scope=task_scope,
            acceptance_criteria=tuple(step["acceptance_criteria"]),
            steward_instructions=objective["request"],
            artifact_requirements=tuple(ArtifactRequirement(
                item["name"], item["path"], item["media_type"],
                tuple(item["acceptance_criteria"]), item.get("max_bytes", 32768))
                for item in step["artifact_requirements"]),
            timeout_seconds=self.timeout_seconds, artifact_revision=artifact_revision,
            rework_verification_id=rework_verification_id,
            runtime_evidence=runtime_evidence)
        result = self.adapter.execute(request)
        if result.status != "DELIVERABLE_PRODUCED" or not result.artifact_name:
            raise CodexActionFailure(result.detail_code,
                                     execution_started=result.execution_started)
        artifact_path = self.adapter.artifact_root / result.artifact_name
        return {
            "status": "SUCCEEDED", "artifact_schema": "rv.codex-cli.artifacts.v3",
            "capability": CAPABILITY, "assignment_id": assignment["id"],
            "objective_id": objective_id, "artifact_name": result.artifact_name,
            "artifact_path": str(artifact_path),
            "artifact_sha256": result.artifact_sha256,
            "artifact_bytes": result.artifact_bytes,
            "source_revision": grounded.source_revision,
            "source_sha256": grounded.source_sha256,
            "repository_revision": result.repository_revision,
            "source_artifact_name": result.source_artifact_name,
            "changed_files": list(result.changed_files),
            "artifacts": list(result.artifacts),
            "artifact_contract": [{"name": item.name, "path": item.path,
                "media_type": item.media_type,
                "acceptance_criteria": list(item.acceptance_criteria),
                "max_bytes": item.max_bytes} for item in request.artifact_requirements],
            "acceptance_criteria": list(request.acceptance_criteria),
            "rework_verification_id": result.rework_verification_id,
            "detail_code": result.detail_code,
        }

    def reconcile_retryable_no_artifact_failures(self, recovery, *, scope_ref, worker_id):
        """Retry only typed Codex failures with no durable worker result or artifact."""
        try:
            repository_revision = self.adapter.repository_revision()
        except Exception:
            return []
        requeued = recovery.reconcile_codex_failures_without_artifact(
            repository_revision=repository_revision,
            artifact_root=self.adapter.artifact_root, scope_ref=scope_ref,
            worker_id=worker_id)
        if not self.adapter.legacy_git_ownership_refused():
            return requeued
        legacy = recovery.reconcile_confirmed_codex_preexecution_failures(
            repository_revision=repository_revision,
            artifact_root=self.adapter.artifact_root,
            scope_ref=scope_ref, worker_id=worker_id,
            legacy_git_refusal_verified=True)
        return requeued + legacy

    def reconcile_late_artifacts(self, recovery, *, worker_adapter, worker_id,
                                 credential, capability, scope_ref):
        """Preserve a late artifact for independent verification without replay."""
        try:
            repository_revision = self.adapter.repository_revision()
        except Exception:
            return []
        return recovery.reconcile_late_codex_artifacts(
            worker_adapter=worker_adapter, worker_id=worker_id,
            credential=credential, capability=capability, scope_ref=scope_ref,
            artifact_root=self.adapter.artifact_root,
            repository_revision=repository_revision)


class CodexArtifactVerifier:
    """Independently verify every persisted assignment-defined artifact."""

    REVISION = "1.0.5"
    MAX_GRACE_REVIEW_BYTES = 12 * 1024
    _NAME = re.compile(r"^codex-[0-9a-f]{64}(?:-r[0-9a-f]{12})?/[0-9a-f]{12}$")

    def __init__(self, artifact_root: str | Path, pipeline=None):
        self.artifact_root = Path(artifact_root)
        if pipeline is not None and not callable(
                getattr(pipeline, "proposal_step_for_assignment", None)):
            raise ValueError("persisted objective-step artifact resolver is required")
        self.pipeline = pipeline

    @staticmethod
    def _valid_media(raw, media_type):
        if not raw:
            return False
        try:
            body = raw.decode("utf-8")
            if media_type in {"text/plain", "text/markdown"}:
                return bool(body.strip())
            if media_type == "application/json":
                json.loads(body)
                return True
            if media_type == "text/csv":
                import csv
                return bool(next(csv.reader(body.splitlines()), []))
            if media_type == "application/xml":
                ET.fromstring(body)
                return True
        except (UnicodeError, ValueError, json.JSONDecodeError, StopIteration, ET.ParseError):
            return False
        return False

    def _open_verified(self, entry, assignment_id, rework_id=None):
        name = entry.get("storage_name")
        if not isinstance(name, str) or not self._NAME.fullmatch(name):
            raise ValueError("artifact storage identity is invalid")
        key = hashlib.sha256(assignment_id.encode("utf-8")).hexdigest()
        suffix = ("-r" + hashlib.sha256(rework_id.encode("utf-8")).hexdigest()[:12]
                  if isinstance(rework_id, str) else "")
        expected = f"codex-{key}{suffix}/{hashlib.sha256(entry['name'].encode('utf-8')).hexdigest()[:12]}"
        if name != expected:
            raise ValueError("artifact storage identity is not assignment-bound")
        directory, basename = name.split("/", 1)
        root_fd = os.open(self.artifact_root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                          getattr(os, "O_NOFOLLOW", 0))
        try:
            directory_fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                                   getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd)
        finally:
            os.close(root_fd)
        try:
            fd = os.open(basename, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
        finally:
            os.close(directory_fd)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or
                    type(entry.get("bytes")) is not int or
                    not 0 < info.st_size == entry["bytes"] <= 32768):
                raise ValueError("artifact protection metadata is invalid")
            raw = os.read(fd, 32769)
        finally:
            os.close(fd)
        if (len(raw) != entry["bytes"] or
                hashlib.sha256(raw).hexdigest() != entry.get("sha256") or
                not self._valid_media(raw, entry.get("media_type"))):
            raise ValueError("artifact integrity or declared type check failed")
        return raw

    @staticmethod
    def _publication_required(contract, step_criteria=()):
        """Detect repository publication obligations in step and artifact criteria."""
        criteria_groups = [step_criteria]
        criteria_groups.extend(
            item.get("acceptance_criteria", ())
            for item in (contract if isinstance(contract, list) else ())
            if isinstance(item, Mapping))
        for group in criteria_groups:
            if not isinstance(group, (list, tuple)):
                continue
            for criterion in group:
                if not isinstance(criterion, str):
                    continue
                text = criterion.casefold()
                has_github = "github" in text or "git hub" in text
                has_commit = any(term in text for term in ("commit", "committed", "commit sha"))
                has_remote_proof = "remote content" in text or "remote artifact" in text
                has_repository_commit = "repository" in text and has_commit
                has_github_delivery = has_github and any(term in text for term in
                    ("commit", "push", "publish", "repository", "remote"))
                if (has_github_delivery or has_repository_commit or has_remote_proof):
                    return True
        return False

    @staticmethod
    def _publication_receipt_consistent(contract, entries, result, step_criteria=()):
        """Reject absent or self-contradictory worker receipts without trusting them."""
        if not CodexArtifactVerifier._publication_required(contract, step_criteria):
            return True
        receipt = result.get("publication_evidence")
        if not isinstance(receipt, Mapping) or not isinstance(entries, list) or len(entries) != 1:
            return False
        entry = entries[0]
        commit = receipt.get("commit_sha")
        remote_digest = receipt.get("remote_sha256")
        delivered_digest = receipt.get("delivered_sha256")
        return (isinstance(commit, str) and bool(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit)) and
            receipt.get("repository_path") == entry.get("path") and
            isinstance(remote_digest, str) and bool(re.fullmatch(r"[0-9a-f]{64}", remote_digest)) and
            remote_digest == entry.get("sha256") and delivered_digest == entry.get("sha256"))

    @staticmethod
    def _criterion_has_supported_check(criterion):
        """Accept only a complete literal-presence clause, never a factual conjunct."""
        if not isinstance(criterion, str):
            return False
        quoted = r"(?:`[^`\n]{1,512}`|'[^'\n]{1,512}'|\"[^\"\n]{1,512}\")"
        subject = r"(?:the\s+[A-Za-z][A-Za-z0-9_-]*|create\s+`?[A-Za-z0-9_./-]+`?)"
        marker = r"(?:exact\s+phrase|literal)"
        forms = (
            rf"{subject}\s+(?:contains?|contain|containing)\s+{marker}\s+{quoted}",
            rf"{subject}\s+contains\s+exactly\s+{quoted}",
        )
        return bool(explicit_artifact_literals(criterion)) and any(
            re.fullmatch(rf"(?is)\s*{form}[.!]?\s*", criterion) for form in forms)

    def verify(self, assignment, attempt, result):
        result = result if isinstance(result, dict) else {}
        step = (self.pipeline.proposal_step_for_assignment(
            assignment.get("objective_ref"), assignment.get("id"))
            if self.pipeline is not None else None)
        contract = step.get("artifact_requirements") if isinstance(step, Mapping) else None
        step_criteria = step.get("acceptance_criteria") if isinstance(step, Mapping) else None
        entries = result.get("artifacts")
        publication_required = self._publication_required(contract, step_criteria)
        criteria = {
            "attempt_succeeded": attempt.get("status") == "succeeded",
            "executor_capability_matches": attempt.get("capability") == CAPABILITY,
            "worker_report_succeeded": result.get("status") == "SUCCEEDED",
            "result_schema_matches": result.get("artifact_schema") == "rv.codex-cli.artifacts.v3",
            "assignment_and_objective_match": result.get("assignment_id") == assignment.get("id") and
                result.get("objective_id") == assignment.get("objective_ref"),
            "artifact_contract_matches_persisted_assignment": False,
            "all_required_artifacts_integrity_and_type_verified": False,
            "artifact_path_projection_matches_contract": False,
            "authorized_acceptance_criteria_bound": False,
            "artifact_semantic_outcome_not_negative": True,
            "all_acceptance_criteria_supported": False,
            "all_required_step_criteria_supported": False,
            "all_required_step_criteria_satisfied": False,
            "all_artifact_acceptance_criteria_supported": False,
            "explicit_artifact_acceptance_clauses_satisfied": False,
            # A worker receipt cannot independently establish remote publication.
            "required_repository_publication_independently_verified": not publication_required,
            "repository_publication_receipt_consistent": self._publication_receipt_consistent(
                contract, entries, result, step_criteria),
            "source_provenance_is_pinned": bool(
                re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", str(result.get("source_revision", ""))) and
                re.fullmatch(r"[0-9a-f]{64}", str(result.get("source_sha256", "")))),
            "repository_provenance_is_pinned": bool(
                re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                             str(result.get("repository_revision", "")))),
        }
        evidence = (f"urn:rv:worker-attempt:{attempt.get('attempt_id', 'unknown')}",)
        try:
            root_info = self.artifact_root.lstat()
            safe_root = (stat.S_ISDIR(root_info.st_mode) and not self.artifact_root.is_symlink() and
                root_info.st_uid == os.geteuid() and stat.S_IMODE(root_info.st_mode) == 0o700 and
                self.artifact_root.resolve() == self.artifact_root.absolute())
            if not safe_root or not isinstance(contract, list) or not contract or not isinstance(entries, list):
                raise ValueError("persisted artifact contract unavailable")
            criteria["artifact_contract_matches_persisted_assignment"] = (
                result.get("artifact_contract") == contract and len(entries) == len(contract) and
                len({item.get("name") for item in entries if isinstance(item, dict)}) == len(entries) and
                {item.get("name") for item in entries if isinstance(item, dict)} ==
                    {item.get("name") for item in contract if isinstance(item, dict)})
            criteria["authorized_acceptance_criteria_bound"] = criteria[
                "artifact_contract_matches_persisted_assignment"] and all(
                    entry.get("path") == requirement.get("path") and
                    entry.get("media_type") == requirement.get("media_type") and
                    entry.get("acceptance_criteria") == requirement.get("acceptance_criteria")
                    for requirement in contract for entry in entries
                    if isinstance(requirement, dict) and isinstance(entry, dict) and
                    entry.get("name") == requirement.get("name"))
            if criteria["artifact_contract_matches_persisted_assignment"]:
                verified = []
                verified_contents = []
                all_artifact_criteria_supported = True
                all_artifact_criteria_satisfied = True
                for requirement in contract:
                    entry = next(item for item in entries if item.get("name") == requirement["name"])
                    raw = self._open_verified(entry, assignment["id"],
                        result.get("rework_verification_id"))
                    verified.append(entry)
                    verified_contents.append((raw, entry.get("media_type")))
                    if entry.get("media_type") == "application/json":
                        criteria["artifact_semantic_outcome_not_negative"] = (
                            criteria["artifact_semantic_outcome_not_negative"] and
                            not json_has_authoritative_negative_outcome(json.loads(raw.decode("utf-8"))))
                    acceptance = entry.get("acceptance_criteria", ())
                    supported = bool(acceptance) and all(
                        self._criterion_has_supported_check(clause) for clause in acceptance)
                    satisfied = supported and artifact_literals_satisfied(
                        raw, acceptance, entry.get("media_type"))
                    all_artifact_criteria_supported = (
                        all_artifact_criteria_supported and supported)
                    all_artifact_criteria_satisfied = (
                        all_artifact_criteria_satisfied and satisfied)
                    evidence += ("workspace://" + entry["storage_name"],
                                 "sha256:" + entry["sha256"])
                step_supported = (isinstance(step_criteria, (list, tuple)) and bool(step_criteria) and
                    all(self._criterion_has_supported_check(clause) for clause in step_criteria))
                step_satisfied = step_supported and all(
                    any(artifact_literals_satisfied(raw, (clause,), media_type)
                        for raw, media_type in verified_contents)
                    for clause in step_criteria)
                criteria["all_required_step_criteria_supported"] = bool(step_supported)
                criteria["all_required_step_criteria_satisfied"] = bool(step_satisfied)
                criteria["all_artifact_acceptance_criteria_supported"] = (
                    bool(contract) and all_artifact_criteria_supported)
                criteria["all_acceptance_criteria_supported"] = (
                    bool(contract) and bool(step_supported) and all_artifact_criteria_supported)
                criteria["explicit_artifact_acceptance_clauses_satisfied"] = (
                    bool(contract) and all_artifact_criteria_satisfied)
                criteria["all_required_artifacts_integrity_and_type_verified"] = len(verified) == len(contract)
                first = entries[0]
                criteria["artifact_path_projection_matches_contract"] = (
                    result.get("artifact_name") == first.get("storage_name") and
                    result.get("artifact_path") == str(self.artifact_root / first.get("storage_name", "")) and
                    result.get("artifact_sha256") == first.get("sha256") and
                    result.get("artifact_bytes") == first.get("bytes") and
                    result.get("source_artifact_name") == first.get("path") and
                    result.get("changed_files") == sorted(item.get("path") for item in contract))
        except (OSError, ValueError, TypeError, StopIteration):
            pass
        accepted = all(criteria.values())
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, evidence, self.REVISION,
            "Assignment artifact set, formats, integrity, provenance and criteria binding verified" if accepted else
            "Assignment artifact set failed independent contract, integrity, type or provenance verification")

    def read_artifact_for_grace_review(self, assignment_id, result):
        """Reopen the bounded artifact set only after repeating integrity checks."""
        if (not isinstance(assignment_id, str) or not isinstance(result, Mapping) or
                result.get("status") != "SUCCEEDED" or
                result.get("artifact_schema") != "rv.codex-cli.artifacts.v3" or
                result.get("capability") != CAPABILITY or
                result.get("assignment_id") != assignment_id or
                not isinstance(result.get("artifacts"), list) or
                not 1 <= len(result["artifacts"]) <= 8):
            raise ValueError("verified assignment artifact set is required for Grace review")
        root_info = self.artifact_root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode) or self.artifact_root.is_symlink() or
                root_info.st_uid != os.geteuid() or stat.S_IMODE(root_info.st_mode) != 0o700 or
                self.artifact_root.resolve() != self.artifact_root.absolute()):
            raise ValueError("artifact root is not protected for Grace review")
        outputs = []
        total = 0
        for entry in result["artifacts"]:
            raw = self._open_verified(entry, assignment_id, result.get("rework_verification_id"))
            total += len(raw)
            if total > self.MAX_GRACE_REVIEW_BYTES:
                raise ValueError("artifact set exceeds Grace review bounds")
            outputs.append({"name": entry["name"], "path": entry["path"],
                "media_type": entry["media_type"], "sha256": entry["sha256"],
                "body": raw.decode("utf-8")})
        return {"artifacts": outputs}


class CodexSourceChangeWorkAction:
    """Execute only proposal-persisted, exact source paths through the patch adapter."""

    def __init__(self, pipeline, adapter: CodexSourceChangeAdapter,
                 repository_reference: str, timeout_seconds: int = 300):
        if (not isinstance(adapter, CodexSourceChangeAdapter) or
                not isinstance(repository_reference, str) or
                not repository_reference.startswith("repo://") or
                type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300):
            raise ValueError("source-change action configuration is invalid")
        self.pipeline = pipeline
        self.adapter = adapter
        self.repository_reference = repository_reference
        self.timeout_seconds = timeout_seconds

    def validate_proposal_target(self, step):
        """Check target identity, commit, and ceiling before CME assignment creation."""
        if (not isinstance(step, Mapping) or
                step.get("repository_reference") != self.repository_reference or
                not isinstance(step.get("repository_revision"), str) or
                not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})",
                                 step["repository_revision"]) or
                not isinstance(step.get("authorized_paths"), (tuple, list)) or
                not set(step["authorized_paths"]) <= set(self.adapter.authorized_paths)):
            return False
        try:
            return self.adapter.base.repository_revision() == step["repository_revision"]
        except Exception:
            return False

    def _assignment(self, assignment):
        objective_id = assignment.get("objective_ref")
        objective = self.pipeline.get_objective(objective_id)
        step = self.pipeline.proposal_step_for_assignment(objective_id, assignment.get("id"))
        if (not objective or objective.get("status") != "WORK_ORDER_CREATED" or
                objective.get("assignment_id") != assignment.get("id") or not step or
                step.get("execution_capability") != SOURCE_CHANGE_CAPABILITY or
                not objective.get("proposal") or
                objective.get("source_revision") is None):
            raise CodexActionFailure("persisted_source_change_scope_required")
        binding = step.get("source_target_binding")
        raw_step = next((item for item in objective["proposal"].get("steps", [])
                         if isinstance(item, Mapping) and item.get("step_id") == step["step_id"]), None)
        expected_hash = (hashlib.sha256(json.dumps(raw_step, sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
            if isinstance(raw_step, Mapping) else None)
        if (not isinstance(binding, Mapping) or
                binding.get("version") != "grace.source-target-binding.v1" or
                binding.get("objective_id") != objective_id or
                binding.get("assignment_id") != assignment.get("id") or
                binding.get("step_id") != step["step_id"] or
                binding.get("capability") != SOURCE_CHANGE_CAPABILITY or
                binding.get("proposal_step_sha256") != expected_hash or
                binding.get("repository_reference") != step.get("repository_reference") or
                binding.get("repository_revision") != step.get("repository_revision") or
                binding.get("authorized_paths") != step.get("authorized_paths") or
                binding.get("test_targets") != step.get("test_targets")):
            raise CodexActionFailure("persisted_source_target_binding_invalid")
        evidence = objective.get("evidence")
        if (not isinstance(evidence, Mapping) or evidence.get("status") != "VERIFIED" or
                evidence.get("retrieval_complete") is not True or
                evidence.get("source_revision") != objective.get("source_revision") or
                evidence.get("source_sha256") != objective.get("source_sha256")):
            raise CodexActionFailure("persisted_resident_grounding_invalid")
        if step.get("depends_on"):
            from ..resident_reasoning import PlanStep
            predecessor = self.pipeline.verified_source_change_predecessor(
                objective_id, PlanStep(step["step_id"], step["objective"],
                    tuple(step["acceptance_criteria"]), tuple(step["depends_on"]),
                    step["execution_capability"], tuple(step["authorized_paths"]),
                    tuple(step["test_targets"]), step["repository_reference"],
                    step["repository_revision"]))
        else:
            predecessor = {"prior_patches": (), "authorized_paths": (), "test_targets": (),
                           "repository_reference": binding["repository_reference"],
                           "repository_revision": binding["repository_revision"]}
        if (predecessor.get("repository_reference") != binding["repository_reference"] or
                predecessor.get("repository_revision") != binding["repository_revision"]):
            raise CodexActionFailure("source_change_predecessor_target_mismatch")
        authorized_paths = tuple(dict.fromkeys(
            (*predecessor["authorized_paths"], *step["authorized_paths"])))
        test_targets = tuple(dict.fromkeys(
            (*predecessor["test_targets"], *step["test_targets"])))
        task_scope = ("Original accepted objective:\n" + objective["request"] +
                      "\n\nCurrent authorized step:\n" + step["objective"])
        if len(task_scope.encode("utf-8")) > 4000:
            raise CodexActionFailure("source_change_task_scope_too_large")
        request = CodexSourceChangeAssignment(
            assignment_id=assignment["id"], objective_id=objective_id,
            repository_reference=binding["repository_reference"],
            repository_revision=binding["repository_revision"],
            task_scope=task_scope,
            acceptance_criteria=tuple(step["acceptance_criteria"]),
            authorized_paths=authorized_paths, test_targets=test_targets,
            timeout_seconds=self.timeout_seconds,
            prior_patches=tuple(predecessor["prior_patches"]))
        return objective, step, request

    def __call__(self, assignment, grounded):
        if (grounded.status is not KnowledgeStatus.VERIFIED or
                grounded.retrieval_complete is not True or
                not grounded.source_revision or not grounded.source_sha256):
            raise CodexActionFailure("verified_regrounding_required")
        try:
            _, _, request = self._assignment(assignment)
            if request.repository_reference != self.repository_reference:
                raise CodexActionFailure("source_change_repository_provenance_mismatch")
            result = self.adapter.execute(request)
        except CodexActionFailure:
            raise
        except Exception as exc:
            raise CodexActionFailure(getattr(exc, "code", "source_change_scope_invalid"),
                                     execution_started=False) from None
        if result.status != "PATCH_PRODUCED":
            raise CodexActionFailure(result.detail_code,
                                     execution_started=result.execution_started)
        return {"status": "SUCCEEDED", "artifact_schema": "rv.codex-cli.source-change.v1",
            "capability": result.capability, "assignment_id": result.assignment_id,
            "objective_id": result.objective_id,
            "repository_reference": result.repository_reference,
            "repository_revision": result.repository_revision,
            "authorized_paths": list(request.authorized_paths),
            "test_targets": list(request.test_targets),
            "changed_files": list(result.changed_files),
            "patch_path": result.patch_path, "patch_sha256": result.patch_sha256,
            "patch_bytes": result.patch_bytes, "test_status": result.test_status,
            "detail_code": result.detail_code,
            "execution_started": result.execution_started}

    def reconcile_retryable_no_artifact_failures(self, recovery, *, scope_ref, worker_id):
        """Requeue only completed source-change failures with no assignment patch or result."""
        try:
            repository_revision = self.adapter.base.repository_revision()
        except Exception:
            return []
        return recovery.reconcile_codex_failures_without_artifact(
            repository_revision=repository_revision,
            artifact_root=self.adapter.base.artifact_root,
            scope_ref=scope_ref, worker_id=worker_id,
            capability=SOURCE_CHANGE_CAPABILITY)


class CodexSourceChangeResultVerifier:
    """Independently replay and test the persisted scoped patch result."""

    REVISION = "1.0.0"

    def __init__(self, pipeline, verifier: CodexSourceChangeVerifier,
                 action: CodexSourceChangeWorkAction):
        self.pipeline = pipeline
        self.verifier = verifier
        self.action = action

    def verify(self, assignment, attempt, result):
        try:
            _, _, request = self.action._assignment(assignment)
            if (result.get("repository_reference") != request.repository_reference or
                    result.get("repository_revision") != request.repository_revision or
                    tuple(result.get("authorized_paths", ())) != request.authorized_paths or
                    tuple(result.get("test_targets", ())) != request.test_targets):
                raise ValueError("source result binding does not match dispatched request")
            parsed = CodexSourceChangeResult(
                status="PATCH_PRODUCED" if result.get("status") == "SUCCEEDED" else result.get("status"),
                capability=result["capability"], assignment_id=result["assignment_id"],
                objective_id=result["objective_id"],
                repository_reference=result["repository_reference"],
                repository_revision=result["repository_revision"],
                changed_files=tuple(result["changed_files"]), patch_path=result["patch_path"],
                patch_sha256=result["patch_sha256"], patch_bytes=result["patch_bytes"],
                test_status=result["test_status"], detail_code=result["detail_code"],
                execution_started=result["execution_started"])
            checked = self.verifier.verify(request, parsed)
        except Exception:
            checked = {"decision": "REJECTED", "reason": "source_change_verification_contract_invalid",
                       "evidence": []}
        accepted = checked.get("decision") == "ACCEPTED"
        criteria = {"scoped_patch_independently_replayed": accepted,
                    "fixed_tests_passed_in_offline_sandbox": accepted,
                    "changed_paths_within_authorized_work_order_scope": accepted}
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, tuple(checked.get("evidence", ())), self.REVISION,
            "scoped source patch independently accepted" if accepted else
            "scoped source patch failed independent verification")
