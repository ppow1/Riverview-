# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/resident_execution/codex_workflow.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.2.13
# Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Separate independent artifact integrity/provenance checks from Grace's substantive acceptance review and expose only a digest-verified bounded artifact snapshot.
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Validate source execution against dispatch-time target snapshot, checkout HEAD, and verifier result provenance.
# Purpose: Adapt bounded Codex production and independent Markdown verification to CME
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
# Contracts: docs/components/GRACE_EXECUTION_PIPELINE.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_codex_workflow.py
# History: Git
# =============================================================================
"""Narrow Codex action and independent verifier for the existing CME path."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from collections.abc import Mapping

from ..worker_adapter.knowledge import KnowledgeStatus
from ..worker_adapter.verifier import VerificationResult, VerificationStatus
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

    def __call__(self, assignment, grounded):
        if (grounded.status is not KnowledgeStatus.VERIFIED or
                grounded.retrieval_complete is not True or
                not grounded.source_revision or not grounded.source_sha256):
            raise CodexActionFailure("verified_regrounding_required")
        objective_id = assignment.get("objective_ref")
        objective = self.pipeline.get_objective(objective_id)
        evidence = objective.get("evidence") if isinstance(objective, Mapping) else None
        if (not objective or objective["status"] != "WORK_ORDER_CREATED" or
                objective["assignment_id"] != assignment.get("id") or
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
            timeout_seconds=self.timeout_seconds, artifact_revision=artifact_revision,
            rework_verification_id=rework_verification_id)
        result = self.adapter.execute(request)
        if result.status != "DELIVERABLE_PRODUCED" or not result.artifact_name:
            raise CodexActionFailure(result.detail_code,
                                     execution_started=result.execution_started)
        artifact_path = self.adapter.artifact_root / result.artifact_name
        return {
            "status": "SUCCEEDED", "artifact_schema": "rv.codex-cli.deliverable.v2",
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


class CodexMarkdownVerifier:
    """Independently reopen artifact and verify assignment binding, digest and contract."""

    REVISION = "1.0.2"
    MAX_BYTES = 32 * 1024
    MAX_GRACE_REVIEW_BYTES = 12 * 1024

    _NAME = re.compile(r"^codex-[0-9a-f]{64}(?:-r[0-9a-f]{12})?\.md$")

    def __init__(self, artifact_root: str | Path, pipeline=None):
        self.artifact_root = Path(artifact_root)
        if pipeline is not None and not callable(
                getattr(pipeline, "proposal_step_for_assignment", None)):
            raise ValueError("persisted objective-step criteria resolver is required")
        self.pipeline = pipeline

    def verify(self, assignment, attempt, result):
        name = result.get("artifact_name") if isinstance(result, dict) else None
        attempt_id = attempt.get("attempt_id", "unknown")
        evidence = (f"urn:rv:worker-attempt:{attempt_id}",)
        criteria = {
            "attempt_succeeded": attempt.get("status") == "succeeded",
            "executor_capability_matches": attempt.get("capability") == CAPABILITY,
            "result_is_codex_deliverable": isinstance(result, dict) and
                result.get("status") == "SUCCEEDED" and
                result.get("artifact_schema") == "rv.codex-cli.deliverable.v2" and
                result.get("capability") == CAPABILITY,
            "artifact_path_is_assignment_bound": False,
            "artifact_owner_mode_and_size_valid": False,
            "artifact_digest_matches": False,
            "markdown_deliverable_matches_objective": False,
            "authorized_acceptance_criteria_bound": False,
            "source_provenance_is_pinned": False,
            "repository_provenance_is_pinned": False,
        }
        raw = None
        assignment_key = hashlib.sha256(assignment["id"].encode("utf-8")).hexdigest()
        rework_verification_id = result.get("rework_verification_id") if isinstance(result, dict) else None
        if rework_verification_id is not None:
            instruction = (self.pipeline.latest_rework_instruction(assignment["id"])
                           if self.pipeline is not None else None)
            expected_revision = hashlib.sha256(str(rework_verification_id).encode("utf-8")).hexdigest()[:12]
            if (not instruction or instruction.get("verification_id") != rework_verification_id or
                    instruction.get("acceptance_criteria_sha256") != hashlib.sha256(
                        json.dumps(list(result.get("acceptance_criteria", ())), ensure_ascii=False,
                            sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()):
                expected_revision = None
            expected_name = (f"codex-{assignment_key}-r{expected_revision}.md"
                             if expected_revision else "")
        else:
            expected_name = f"codex-{assignment_key}.md"
        path = self.artifact_root / expected_name
        criteria["artifact_path_is_assignment_bound"] = bool(
            expected_name and name == expected_name and self._NAME.fullmatch(str(name)) and
            result.get("artifact_path") == str(path))
        try:
            root_info = self.artifact_root.lstat()
            safe_root = (stat.S_ISDIR(root_info.st_mode) and
                not self.artifact_root.is_symlink() and
                root_info.st_uid == os.geteuid() and
                stat.S_IMODE(root_info.st_mode) == 0o700 and
                self.artifact_root.resolve() == self.artifact_root.absolute())
            if safe_root and criteria["artifact_path_is_assignment_bound"]:
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
                try:
                    info = os.fstat(fd)
                    criteria["artifact_owner_mode_and_size_valid"] = (
                        stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and
                        stat.S_IMODE(info.st_mode) == 0o600 and
                        0 < info.st_size <= self.MAX_BYTES)
                    raw = os.read(fd, self.MAX_BYTES + 1)
                finally:
                    os.close(fd)
                criteria["artifact_digest_matches"] = bool(
                    raw is not None and len(raw) <= self.MAX_BYTES and
                    len(raw) == result.get("artifact_bytes") and
                    hashlib.sha256(raw).hexdigest() == result.get("artifact_sha256"))
                if criteria["artifact_digest_matches"]:
                    body = raw.decode("utf-8")
                    criteria["markdown_deliverable_matches_objective"] = bool(
                        body.startswith("# ") and assignment.get("objective_ref") ==
                        result.get("objective_id") and body.strip())
                    expected_criteria = result.get("acceptance_criteria")
                    if self.pipeline is not None:
                        step = self.pipeline.proposal_step_for_assignment(
                            assignment.get("objective_ref"), assignment.get("id"))
                        expected_criteria = (step.get("acceptance_criteria")
                                             if isinstance(step, Mapping) else None)
                    # The verifier confirms that the executor's criteria snapshot
                    # exactly matches the immutable assigned step. It does not
                    # decide whether prose substantively satisfies those criteria;
                    # Grace's bound reasoning model receives the artifact below.
                    criteria["authorized_acceptance_criteria_bound"] = bool(
                        isinstance(expected_criteria, (list, tuple)) and expected_criteria and
                        all(isinstance(item, str) and item.strip()
                            for item in expected_criteria) and
                        ("acceptance_criteria" not in result or
                         list(result.get("acceptance_criteria", ())) == list(expected_criteria)))
                    evidence += ("workspace://" + name,
                                 "sha256:" + result["artifact_sha256"])
            criteria["source_provenance_is_pinned"] = bool(
                re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                             str(result.get("source_revision", ""))) and
                re.fullmatch(r"[0-9a-f]{64}",
                             str(result.get("source_sha256", ""))))
        except (OSError, UnicodeError, ValueError):
            pass
        criteria["repository_provenance_is_pinned"] = bool(
            isinstance(result, dict) and
            re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}",
                         str(result.get("repository_revision", ""))))
        accepted = all(criteria.values())
        return VerificationResult(
            VerificationStatus.ACCEPTED if accepted else VerificationStatus.REJECTED,
            criteria, evidence if raw is not None else evidence[:1], self.REVISION,
            ("Codex artifact integrity, provenance, authorization scope and required structure verified; "
             "substantive acceptance criteria remain for Grace's review") if accepted else
            "Codex Markdown artifact failed independent integrity, provenance, scope or structure verification")

    def read_artifact_for_grace_review(self, assignment_id, result):
        """Return bounded artifact text only after repeating its persisted integrity checks."""
        if (not isinstance(assignment_id, str) or not isinstance(result, Mapping) or
                result.get("status") != "SUCCEEDED" or
                result.get("artifact_schema") != "rv.codex-cli.deliverable.v2" or
                result.get("capability") != CAPABILITY or
                result.get("assignment_id") != assignment_id or
                result.get("source_artifact_name") != "deliverable.md" or
                result.get("changed_files") != ["deliverable.md"]):
            raise ValueError("verified Codex artifact identity is required for Grace review")
        key = hashlib.sha256(assignment_id.encode("utf-8")).hexdigest()
        rework_id = result.get("rework_verification_id")
        suffix = ("-r" + hashlib.sha256(rework_id.encode("utf-8")).hexdigest()[:12]
                  if isinstance(rework_id, str) and rework_id else "")
        expected_name = f"codex-{key}{suffix}.md"
        expected_path = self.artifact_root / expected_name
        if (result.get("artifact_name") != expected_name or
                result.get("artifact_path") != str(expected_path) or
                type(result.get("artifact_bytes")) is not int or
                not 0 < result["artifact_bytes"] <= self.MAX_GRACE_REVIEW_BYTES or
                not re.fullmatch(r"[0-9a-f]{64}", str(result.get("artifact_sha256", "")))):
            raise ValueError("Codex artifact exceeds Grace review bounds or identity")
        root_info = self.artifact_root.lstat()
        if (not stat.S_ISDIR(root_info.st_mode) or self.artifact_root.is_symlink() or
                root_info.st_uid != os.geteuid() or stat.S_IMODE(root_info.st_mode) != 0o700 or
                self.artifact_root.resolve() != self.artifact_root.absolute()):
            raise ValueError("Codex artifact root is not protected for Grace review")
        fd = os.open(expected_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                    stat.S_IMODE(info.st_mode) != 0o600 or
                    info.st_size != result["artifact_bytes"] or
                    info.st_size > self.MAX_GRACE_REVIEW_BYTES):
                raise ValueError("Codex artifact protection metadata changed before Grace review")
            raw = os.read(fd, self.MAX_GRACE_REVIEW_BYTES + 1)
        finally:
            os.close(fd)
        if (len(raw) != result["artifact_bytes"] or
                hashlib.sha256(raw).hexdigest() != result["artifact_sha256"]):
            raise ValueError("Codex artifact digest changed before Grace review")
        return {"artifact_name": expected_name,
                "sha256": result["artifact_sha256"],
                "body": raw.decode("utf-8")}


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
