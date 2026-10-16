#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/run_grace_execution_service.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.1.7
# Purpose: Run persistent Grace dispatch, bounded worker, and independent verification cycles
# Execution Model: systemd polling or explicitly supervised one-objective TTY run
# Observability: Structured sanitized lifecycle logs and existing dashboard/PostgreSQL projections
# Dependencies: PostgreSQL; protected systemd credentials; pinned Riverview release
# Authority: Exact grants for Grace dispatch, executor registration/execution, and verification
# Changed: 2026-10-11 UTC | RV-M4.4-PERSISTENT-EXECUTION | Add supervised runtime entry point
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Bind runtime to current Grace office grant and persisted office state
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Select bounded Codex worker/verifier only from explicit service configuration
# Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Remove API-key auth and permit only interactive owning-user subscription mode
# Changed: 2026-10-14 UTC | RV-GRACE-ADB-LOOP-001 | Use the active bound router for proposal/review and return verified outcomes to chat
# Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Add persistent no-copy ChatGPT owner-session runtime mode
# Changed: 2026-10-16 UTC | RV-GRACE-STRUCTURED-REVIEW-001 | Bind same-objective continuation decisions to the existing durable objective-step pipeline
# Changed: 2026-10-15 UTC | RV-GRACE-PROPOSAL-TIMEOUT-001 | Align bounded 80B provider and resident proposal deadlines
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Run narrowly fenced legacy pre-execution recovery through existing CME at startup
# Changed: 2026-10-16 UTC | RV-GRACE-RECOVERY-HOOK-001 | Call the current bounded Codex no-artifact recovery hook and fail with a typed configuration error if unavailable
# Changed: 2026-10-16 UTC | RV-GRACE-OWNER-CODEX-HOME-001 | Use the explicitly configured service-local CODEX_HOME rather than deriving credentials from HOME
# Changed: 2026-10-16 UTC | RV-GRACE-SCOPE-LEASE-RECONCILE-001 | Authenticate recovery scope before startup Codex recovery
# Changed: 2026-10-16 UTC | RV-GRACE-RESULT-RETURN-DIAGNOSTICS-001 | Default verified-result review to the supported bounded 512-token output budget
# Changed: 2026-10-16 UTC | RV-GRACE-MULTISTEP-REASONING-BUDGET-001 | Default persistent resident plans to a bounded 768-token completion budget
# Changed: 2026-10-16 UTC | RV-GRACE-CAPABILITY-COMMISSIONING | Wire the separately scoped source-change capability through the existing leased worker and independent verifier
# Contracts: docs/components/GRACE_PERSISTENT_EXECUTION.md
# Tests: tests/test_grace_runtime_provider_wiring.py; tests/test_grace_execution.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Systemd entry point for the persistent model-independent Grace runtime."""

from __future__ import annotations

import json
import logging
import os
import pwd
import re
import signal
import sys
import threading
from pathlib import Path

from riverview_core.assignment_intake import AuthorizedAssignmentIntake
from riverview_core.institutional_authority import AuthorityRegistry, ExactGrantAuthorizer
from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.resident_execution import GraceExecutionPipeline
from riverview_core.resident_execution.pipeline import ObjectiveContextReader
from riverview_core.resident_execution.service import GraceExecutionService
from riverview_core.resident_execution.worker import BoundedLocalCodingWorker
from riverview_core.resident_execution.codex_cli import CAPABILITY as CODEX_CAPABILITY
from riverview_core.resident_execution.codex_cli import CodexAdapterError, CodexCLIExecutionAdapter
from riverview_core.resident_execution.codex_workflow import (CodexMarkdownVerifier, CodexWorkAction,
    CodexSourceChangeResultVerifier, CodexSourceChangeWorkAction)
from riverview_core.resident_execution.codex_source_change import (
    CAPABILITY as SOURCE_CHANGE_CAPABILITY, CodexSourceChangeAdapter,
    CodexSourceChangeVerifier)
from riverview_core.worker_adapter import ContinuousWorker, PostgresWorkerAdapter
from riverview_core.worker_adapter.recovery import PostgresRecoveryCoordinator
from riverview_core.worker_adapter.repository_knowledge import RepositoryKnowledgeProvider
from riverview_core.worker_adapter.resident_knowledge import TaskRelevantRepositoryKnowledgeProvider
from riverview_core.worker_adapter.service import (WorkerServiceConfigurationError,
    ensure_registered, load_runtime_config, read_worker_credential)
from riverview_core.resident_reasoning import ResidentReasoner
from riverview_core.local_reasoning_provider import LocalReasoningProvider
from riverview_core.resident_execution.model_router import GraceModelRouter
from riverview_core.resident_execution.conversation import (
    ConversationStore, ResidentConversationService)


def resident_reasoning_timeout(environ):
    """Return the shared bounded proposal-provider and caller deadline."""
    try:
        timeout = float(environ.get("RIVERVIEW_RESIDENT_REASONING_TIMEOUT", "60"))
    except (TypeError, ValueError):
        raise WorkerServiceConfigurationError("resident_reasoning_timeout_invalid") from None
    if not 1 <= timeout <= 60:
        raise WorkerServiceConfigurationError("resident_reasoning_timeout_invalid")
    return timeout


def resident_result_review_tokens(environ):
    """Return a bounded result-review output budget; structured reviews default to 512."""
    try:
        tokens = int(environ.get("RIVERVIEW_GRACE_RESULT_REVIEW_TOKENS", "512"))
    except (TypeError, ValueError):
        raise WorkerServiceConfigurationError("resident_result_review_tokens_invalid") from None
    if not 16 <= tokens <= 512:
        raise WorkerServiceConfigurationError("resident_result_review_tokens_invalid")
    return tokens


def source_change_path_allowlist(environ):
    """Load the operator-pinned maximum path set for source-change proposals."""
    try:
        values = json.loads(environ.get("RIVERVIEW_CODEX_SOURCE_ALLOWED_PATHS", "[]"))
    except (TypeError, json.JSONDecodeError):
        raise WorkerServiceConfigurationError("source_change_allowlist_invalid") from None
    if (not isinstance(values, list) or not 1 <= len(values) <= 128 or
            any(not isinstance(path, str) for path in values)):
        raise WorkerServiceConfigurationError("source_change_allowlist_invalid")
    try:
        from riverview_core.resident_execution.codex_source_change import _paths
        return _paths(tuple(values), maximum=128)
    except (TypeError, ValueError):
        raise WorkerServiceConfigurationError("source_change_allowlist_invalid") from None


def persistent_owner_codex_home(environ, state_root):
    """Select only the configured Codex home contained in private service state."""
    configured = environ.get("RIVERVIEW_CODEX_HOME")
    if not isinstance(configured, str) or not configured:
        configured = str(Path(state_root) / "codex-home")
    candidate = Path(configured)
    try:
        root = Path(state_root).resolve(strict=True)
        resolved = candidate.resolve(strict=False)
    except OSError:
        raise WorkerServiceConfigurationError("codex_service_home_outside_state_directory") from None
    if (not candidate.is_absolute() or candidate.is_symlink() or
            resolved == root or not resolved.is_relative_to(root)):
        raise WorkerServiceConfigurationError("codex_service_home_outside_state_directory")
    return str(candidate)


def configured_resident_providers(binding, environ=None, provider_factory=None):
    """Build only the provider set matching the current authorized office binding."""
    environ = os.environ if environ is None else environ
    provider_factory = LocalReasoningProvider if provider_factory is None else provider_factory
    endpoint = environ.get("RIVERVIEW_REASONING_ENDPOINT")
    model = environ.get("RIVERVIEW_REASONING_MODEL")
    digest = environ.get("RIVERVIEW_REASONING_MODEL_SHA256")
    if not all((endpoint, model, digest)):
        raise WorkerServiceConfigurationError("resident_reasoning_provider_incomplete")
    allow_lan = environ.get("RIVERVIEW_GRACE_ALLOW_APPROVED_OCTO1") == "1"
    autonomic = provider_factory(endpoint, model, digest,
        allow_approved_private_lan=allow_lan)
    provider_ref = binding.get("provider_ref")
    if provider_ref == autonomic.provider_id:
        if binding.get("implementation_revision") != autonomic.model_sha256:
            raise WorkerServiceConfigurationError("resident_reasoning_binding_mismatch")
        return {autonomic.provider_id: autonomic}, autonomic.model
    if provider_ref != GraceModelRouter.provider_id:
        raise WorkerServiceConfigurationError("resident_reasoning_provider_binding_mismatch")
    if (environ.get("RIVERVIEW_GRACE_ENABLE_MODEL_ROUTER") != "1" or not allow_lan):
        raise WorkerServiceConfigurationError("resident_model_router_opt_in_required")
    proposal_timeout = resident_reasoning_timeout(environ)
    vision_digest = environ.get("RIVERVIEW_GRACE_30B_MODEL_SHA256", "")
    reasoning_digest = environ.get("RIVERVIEW_GRACE_80B_MODEL_SHA256", "")
    # Reuse the exact endpoint/model pairs already allowlisted by LocalReasoningProvider.
    endpoint_30b = next(endpoint for endpoint, model_id in
        LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS.items() if "30B" in model_id)
    model_30b = LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS[endpoint_30b]
    endpoint_80b = next(endpoint for endpoint, model_id in
        LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS.items() if "80B" in model_id)
    model_80b = LocalReasoningProvider.APPROVED_PRIVATE_LAN_MODELS[endpoint_80b]
    vision = provider_factory(endpoint_30b, model_30b, vision_digest,
        allow_approved_private_lan=True)
    reasoning = provider_factory(endpoint_80b, model_80b, reasoning_digest,
        timeout_seconds=proposal_timeout, allow_approved_private_lan=True)
    router = GraceModelRouter(autonomic=autonomic, vision=vision, reasoning=reasoning)
    if binding.get("implementation_revision") != router.model_sha256:
        raise WorkerServiceConfigurationError("resident_reasoning_binding_mismatch")
    return {router.provider_id: router}, reasoning.model

SERVICE_UNIT = "riverview-grace-execution.service"
OWNER_SESSION_SERVICE_UNIT = "riverview-grace-execution-owner-session.service"


def reconcile_codex_startup_recovery(execution_action, recovery, *, scope_ref, worker_id):
    """Run the current Codex recovery hook through the persistent-service contract."""
    reconcile = getattr(execution_action, "reconcile_retryable_no_artifact_failures", None)
    if not callable(reconcile):
        raise WorkerServiceConfigurationError("codex_recovery_hook_unavailable")
    return reconcile(recovery, scope_ref=scope_ref, worker_id=worker_id)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ledger = adapter = authority_registry = conversation_store = None
    try:
        codex_auth_mode = os.environ.get("RIVERVIEW_CODEX_AUTH_MODE", "service")
        credential_unit = (OWNER_SESSION_SERVICE_UNIT
            if codex_auth_mode == "chatgpt-owner-session" else SERVICE_UNIT)
        dsn, schema, authority_schema, worker_id, scope_ref, worker_token = load_runtime_config(
            credential_unit, "worker-token")
        dispatch_token = read_worker_credential(credential_unit, "dispatch-token")
        verifier_token = read_worker_credential(credential_unit, "verifier-token")
        resident_token = read_worker_credential(credential_unit, "resident-token")
        office_id = os.environ.get("RIVERVIEW_RESIDENT_OFFICE_ID", "")
        verifier_id = os.environ.get("RIVERVIEW_VERIFIER_ID", "")
        commit = os.environ.get("RIVERVIEW_KNOWLEDGE_COMMIT", "")
        repo_root = Path(os.environ.get("RIVERVIEW_KNOWLEDGE_ROOT", "/opt/riverview-core"))
        artifact_root = Path(os.environ.get("RIVERVIEW_ARTIFACT_DIR", "/var/lib/riverview-grace/artifacts"))
        if (not verifier_id or not office_id.startswith("office:")
                or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit)
                or not scope_ref.startswith("work-order:")):
            raise WorkerServiceConfigurationError("grace_runtime_configuration_invalid")
        ledger = PostgresLedger(dsn, schema=schema)
        adapter = PostgresWorkerAdapter(dsn, schema=schema, authority_schema=authority_schema)
        authorizer = ExactGrantAuthorizer(authority_schema)
        authority_registry = AuthorityRegistry(dsn, schema=authority_schema, runtime_safe=True)
        # Fail startup closed when the configured resident is not the currently bound,
        # explicitly authorized occupant. A service restart reloads the current credential.
        office = authority_registry.authorize_office_state(resident_token, office_id)
        if not office.get("provider_ref"):
            raise WorkerServiceConfigurationError("resident_office_unbound")
        intake = AuthorizedAssignmentIntake(ledger, authorizer)
        resident_knowledge = TaskRelevantRepositoryKnowledgeProvider(repo_root, commit)
        pipeline = GraceExecutionPipeline(ledger, authorizer, intake, resident_knowledge)
        reasoning_timeout = resident_reasoning_timeout(os.environ)
        providers, reasoning_model = configured_resident_providers(office)
        resident_reasoner = ResidentReasoner(
            registry=authority_registry, office_id=office_id,
            resident_credential=resident_token, assignments=ObjectiveContextReader(pipeline),
            knowledge=resident_knowledge, providers=providers,
            timeout_seconds=reasoning_timeout)
        conversation_store = ConversationStore(dsn, schema=schema)
        conversation_service = ResidentConversationService(
            store=conversation_store, registry=authority_registry,
            authorizer=authorizer, office_id=office_id,
            resident_credential=resident_token, providers=providers,
            max_response_tokens=resident_result_review_tokens(os.environ))
        conversation_service.continuation_handler = lambda context, step: pipeline.propose_continuation(
            context["objective_id"], context["assignment_id"], step,
            actor_id="office:" + office_id)
        adapter_mode = os.environ.get("RIVERVIEW_ENGINEERING_ADAPTER", "bounded-artifact")
        execution_capability = "engineering.bounded-artifact.v1"
        execution_action = BoundedLocalCodingWorker(pipeline, artifact_root)
        outcome_verifier = None
        if codex_auth_mode not in {"service", "supervised-chatgpt", "chatgpt-owner-session"}:
            raise WorkerServiceConfigurationError("codex_auth_mode_invalid")
        if (codex_auth_mode in {"supervised-chatgpt", "chatgpt-owner-session"} and
                adapter_mode not in {"codex-cli", "codex-source-change"}):
            raise WorkerServiceConfigurationError("supervised_mode_requires_codex_adapter")
        if adapter_mode == "codex-cli":
            executable = os.environ.get("RIVERVIEW_CODEX_EXECUTABLE", "")
            codex_home = os.environ.get("RIVERVIEW_CODEX_HOME", "")
            codex_workspace = os.environ.get("RIVERVIEW_CODEX_WORKSPACE_DIR", "")
            codex_repository = os.environ.get("RIVERVIEW_CODEX_REPOSITORY_PATH", "")
            repository_reference = os.environ.get("RIVERVIEW_CODEX_REPOSITORY_REF", "")
            if codex_auth_mode == "supervised-chatgpt":
                if (pwd.getpwuid(os.geteuid()).pw_name != "admin1" or
                        not sys.stdin.isatty()):
                    raise WorkerServiceConfigurationError("supervised_codex_requires_admin1_tty")
                operator_state = Path.home() / ".local" / "share" / "riverview-grace"
                codex_home = os.environ.get(
                    "RIVERVIEW_CODEX_HOME", str(state_root / "codex-home"))
                codex_home_path = Path(codex_home)
                if (not codex_home_path.is_absolute() or
                        not codex_home_path.resolve().is_relative_to(state_root.resolve())):
                    raise WorkerServiceConfigurationError("codex_service_home_outside_state_directory")
                codex_workspace = str(operator_state / "workspaces")
                artifact_root = operator_state / "artifacts"
            persistent_owner_session = codex_auth_mode == "chatgpt-owner-session"
            if persistent_owner_session:
                if pwd.getpwuid(os.geteuid()).pw_name != "admin1":
                    raise WorkerServiceConfigurationError("chatgpt_owner_session_requires_admin1")
                state_root = Path(os.environ.get(
                    "RIVERVIEW_CODEX_STATE_DIR", "/var/lib/riverview-grace-owner-session"))
                if not state_root.is_absolute() or state_root.resolve() in {
                        Path("/home/admin1").resolve(), Path("/home/admin1/.codex").resolve()}:
                    raise WorkerServiceConfigurationError("chatgpt_owner_state_path_invalid")
                codex_home = persistent_owner_codex_home(os.environ, state_root)
                codex_workspace = str(state_root / "workspaces")
                artifact_root = state_root / "artifacts"
            if not all((executable, codex_home, codex_workspace, codex_repository,
                        repository_reference)):
                raise WorkerServiceConfigurationError("codex_adapter_configuration_incomplete")
            supervised_chatgpt = codex_auth_mode == "supervised-chatgpt"
            if supervised_chatgpt and (pwd.getpwuid(os.geteuid()).pw_name != "admin1"
                                       or not sys.stdin.isatty()):
                raise WorkerServiceConfigurationError("supervised_codex_requires_admin1_tty")
            codex_adapter = CodexCLIExecutionAdapter(
                executable=executable, repository_path=codex_repository,
                repository_reference=repository_reference, codex_home=codex_home,
                workspace_root=codex_workspace, artifact_root=artifact_root,
                supervised_chatgpt_session=supervised_chatgpt,
                persistent_chatgpt_owner_session=persistent_owner_session,
                require_code_mode_host=True)
            if Path(executable).resolve().is_relative_to(Path("/home/admin1").resolve()):
                raise WorkerServiceConfigurationError("personal_codex_executable_forbidden")
            try:
                codex_adapter._preflight()
            except CodexAdapterError as exc:
                raise WorkerServiceConfigurationError(
                    "codex_adapter_resource_preflight_failed_" + exc.code) from None
            except Exception:
                raise WorkerServiceConfigurationError("codex_adapter_resource_preflight_failed") from None
            timeout_seconds = int(os.environ.get("RIVERVIEW_CODEX_TIMEOUT_SECONDS", "180"))
            if adapter_mode == "codex-cli":
                execution_capability = CODEX_CAPABILITY
                execution_action = CodexWorkAction(
                    pipeline, codex_adapter, repository_reference,
                    timeout_seconds=timeout_seconds)
                outcome_verifier = CodexMarkdownVerifier(artifact_root)
            else:
                allowed_paths = source_change_path_allowlist(os.environ)
                try:
                    source_adapter = CodexSourceChangeAdapter(
                        base_adapter=codex_adapter, repository_reference=repository_reference,
                        authorized_paths=allowed_paths, max_timeout_seconds=timeout_seconds)
                    source_verifier = CodexSourceChangeVerifier(
                        base_adapter=codex_adapter, authorized_paths=allowed_paths,
                        max_timeout_seconds=timeout_seconds)
                    execution_action = CodexSourceChangeWorkAction(
                        pipeline, source_adapter, repository_reference,
                        timeout_seconds=timeout_seconds)
                    outcome_verifier = CodexSourceChangeResultVerifier(
                        pipeline, source_verifier, execution_action)
                except (TypeError, ValueError):
                    raise WorkerServiceConfigurationError(
                        "source_change_allowlist_invalid") from None
                execution_capability = SOURCE_CHANGE_CAPABILITY
        elif adapter_mode != "bounded-artifact":
            raise WorkerServiceConfigurationError("engineering_adapter_not_registered")
        ensure_registered(adapter, worker_id, worker_token,
            (execution_capability,), scope_ref)
        ensure_registered(adapter, verifier_id, verifier_token,
            ("assignment.verify.v1",), scope_ref)
        if isinstance(execution_action, (CodexWorkAction, CodexSourceChangeWorkAction)):
            recovery = PostgresRecoveryCoordinator(dsn, schema=schema,
                max_retries=int(os.environ.get("RIVERVIEW_GRACE_MAX_WORKER_RECOVERIES", "3")))
            try:
                # Worker registration is established above; validate the current
                # credential and capability before the recovery query has effects.
                authenticated_scope = adapter.authenticated_scope(
                    worker_id, worker_token, execution_capability)
                if authenticated_scope != scope_ref:
                    raise WorkerServiceConfigurationError("codex_recovery_scope_mismatch")
                recovered = reconcile_codex_startup_recovery(
                    execution_action, recovery, scope_ref=scope_ref, worker_id=worker_id)
            finally:
                recovery.close()
            if recovered:
                logging.info(json.dumps({"event": "codex_preexecution_recovery_completed",
                    "assignments": [item["assignment_id"] for item in recovered],
                    "count": len(recovered)}, sort_keys=True))
        engine = ContinuousWorker(adapter, worker_id, worker_token,
            knowledge=RepositoryKnowledgeProvider(repo_root, commit),
            action=execution_action,
            action_effect_class="external_uncertain" if adapter_mode == "codex-cli" else "retry_safe",
            action_capability=execution_capability,
            recovery_max_retries=int(os.environ.get("RIVERVIEW_GRACE_MAX_WORKER_RECOVERIES", "3")))
        service = GraceExecutionService(pipeline, adapter, engine,
            dispatch_credential=dispatch_token, authority_ref=scope_ref,
            verifier_id=verifier_id, verifier_credential=verifier_token,
            artifact_root=artifact_root,
            max_dispatch_failures=int(os.environ.get("RIVERVIEW_GRACE_MAX_DISPATCH_FAILURES", "3")),
            resident_reasoner=resident_reasoner,
            resident_token_budget=int(os.environ.get("RIVERVIEW_RESIDENT_REASONING_TOKENS", "768")),
            verifier=outcome_verifier, execution_capability=execution_capability,
            conversation_result_publisher=conversation_service.review_verified_work_order)
        if codex_auth_mode == "supervised-chatgpt":
            if not re.search(r"80b", (reasoning_model or "").lower()) or not providers:
                raise WorkerServiceConfigurationError("supervised_mode_requires_configured_80b_reasoner")
            objective_id = os.environ.get("RIVERVIEW_SUPERVISED_OBJECTIVE_ID", "")
            if not re.fullmatch(r"objective:[A-Za-z0-9._:-]{1,120}", objective_id):
                raise WorkerServiceConfigurationError("supervised_objective_id_required")
            service.reason_one_grounded_objective(objective_id)
            objective = pipeline.get_objective(objective_id)
            if (objective is None or objective.get("status") not in
                    {"PROPOSED", "WORK_ORDER_CREATED"} or not objective.get("proposal")):
                logging.info(json.dumps({"event": "supervised_objective_waiting_for_proposal",
                    "objective_id": objective_id,
                    "status": objective.get("status") if objective else "NOT_FOUND"},
                    sort_keys=True))
                return 3
            summary = objective["proposal"].get("summary", "")
            print(json.dumps({"objective_id": objective_id,
                "proposal_summary": summary[:500],
                "acceptance_criteria": objective["proposal"]["steps"][0]["acceptance_criteria"]},
                ensure_ascii=False, sort_keys=True))
            if input(f"Type EXECUTE {objective_id} to dispatch this one proposal: ").strip() != f"EXECUTE {objective_id}":
                logging.info(json.dumps({"event": "supervised_execution_declined",
                    "objective_id": objective_id}, sort_keys=True))
                return 4
            result = service.execute_supervised_objective(objective_id)
            result["conversation_results_returned"] = service.publish_conversation_results()
            print(json.dumps(result, sort_keys=True))
            return 0 if result.get("status") == "COMPLETED" else 5
        if codex_auth_mode == "chatgpt-owner-session" and (
                not re.search(r"80b", (reasoning_model or "").lower()) or not providers):
            raise WorkerServiceConfigurationError("owner_session_requires_configured_80b_reasoner")
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())
        logging.info(json.dumps({"event": "grace_execution_service_started",
            "component_id": "RESIDENT-ORCHESTRATION", "worker_id": worker_id,
            "verifier_id": verifier_id, "resident_office_id": office_id,
            "resident_occupant_id": office["occupant_id"],
            "resident_binding_revision": office["binding_revision"],
            "resident_provider_ref": office["provider_ref"],
            "engineering_adapter": adapter_mode,
            "reasoning_provider_configured": bool(providers),
            "source_revision": commit, "scope_ref": scope_ref},
            sort_keys=True))
        service.run_forever(shutdown_requested=stop.is_set,
            poll_seconds=float(os.environ.get("RIVERVIEW_GRACE_POLL_SECONDS", "1")))
        return 0
    except WorkerServiceConfigurationError as exc:
        logging.error(json.dumps({"event": "grace_service_configuration_error",
                                  "failure_code": str(exc)}, sort_keys=True))
        return 2
    except Exception as exc:
        logging.error(json.dumps({"event": "grace_service_start_failed",
                                  "failure_type": type(exc).__name__}, sort_keys=True))
        return 1
    finally:
        if adapter is not None:
            adapter.close()
        if conversation_store is not None:
            conversation_store.close()
        if authority_registry is not None:
            authority_registry.close()
        if ledger is not None:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
