#!/usr/bin/env python3
# Read-only, exact-objective diagnostic. Emits artifact paths and booleans only.
from __future__ import annotations

import json
import os
import pwd
import re
import stat
import sys
from pathlib import Path

OBJECTIVE_ID = "objective:grace-conversation:be52c097-4609-53a1-b62c-d03db7f4b5b9"
EXPECTED_PATH = "reports/grace_delivery_20261029.txt"
UNIT = "riverview-grace-execution-owner-session.service"
OFFICE_ID_ENV = "RIVERVIEW_RESIDENT_OFFICE_ID"


def path_named(path: str, text: str) -> bool:
    return bool(re.search(r"(?<![A-Za-z0-9._/-])" + re.escape(path) +
                          r"(?![A-Za-z0-9_/-]|\.(?=[A-Za-z0-9._/-]))", text))


def main() -> int:
    try:
        from riverview_core.assignment_intake import AuthorizedAssignmentIntake
        from riverview_core.institutional_authority import AuthorityRegistry, ExactGrantAuthorizer
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.resident_execution.pipeline import GraceExecutionPipeline
        from riverview_core.resident_reasoning import PlanArchiveInvalid, ResidentReasoner

        expected_uid = pwd.getpwnam("admin1").pw_uid
        if os.geteuid() != expected_uid:
            raise RuntimeError("runtime_identity_mismatch")
        if any(os.environ.get(name) for name in
               ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS")):
            raise RuntimeError("ambient_database_override")
        # Pin the non-secret connection target and schemas to the readable owner
        # unit contract; only the resident office identity comes from its protected
        # EnvironmentFile. No environment or DSN value is emitted.
        dsn = ("host=127.0.0.1 port=5432 dbname=riverview user=riverview_core "
               "application_name=riverview-grace-artifact-scope-diagnostic "
               "options='-c default_transaction_read_only=on'")
        office_id = os.environ.get(OFFICE_ID_ENV, "")
        if not office_id.startswith("office:") or len(office_id) > 120:
            raise RuntimeError("resident_office_unavailable")
        credential_dir = Path(os.environ.get("CREDENTIALS_DIRECTORY", ""))
        if (not credential_dir.is_absolute() or credential_dir.parent != Path("/run/credentials")
                or not re.fullmatch(r"[a-z0-9][a-z0-9_.@-]*\.service", credential_dir.name)):
            raise RuntimeError("credential_directory_mismatch")
        directory_info = credential_dir.lstat()
        if (not stat.S_ISDIR(directory_info.st_mode) or directory_info.st_uid != 0
                or stat.S_IMODE(directory_info.st_mode) != 0o550
                or credential_dir.resolve(strict=True) != credential_dir):
            raise RuntimeError("credential_directory_mismatch")
        resident_path = credential_dir / "resident-token"
        pgpass = credential_dir / "pgpass"
        for path in (resident_path, pgpass):
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
                    or stat.S_IMODE(info.st_mode) != 0o440 or path.resolve(strict=True) != path
                    or not os.access(path, os.R_OK, effective_ids=True)):
                raise RuntimeError("existing_runtime_credential_unavailable")
        raw_token = resident_path.read_bytes()
        try:
            resident_credential = raw_token.decode("ascii").removesuffix("\n")
        except UnicodeDecodeError:
            raise RuntimeError("resident_credential_invalid") from None
        if not 32 <= len(resident_credential) <= 512 or any(c.isspace() for c in resident_credential):
            raise RuntimeError("resident_credential_invalid")
        os.environ["PGPASSFILE"] = str(pgpass)
        schema = "riverview_dev"
        authority_schema = "riverview_authority"
        registry = AuthorityRegistry(dsn, schema=authority_schema, runtime_safe=True)
        snapshot = registry.authorize_office_state(resident_credential, office_id)
        state = snapshot.get("state")
        if not isinstance(state, dict):
            raise RuntimeError("authorized_office_state_unavailable")
        runtime = state.get(ResidentReasoner.STATE_KEY)
        plans = ResidentReasoner._decode_plan_cache(runtime)

        ledger = PostgresLedger(dsn, schema=schema)
        authorizer = ExactGrantAuthorizer(authority_schema)
        pipeline = GraceExecutionPipeline(
            ledger, authorizer, AuthorizedAssignmentIntake(ledger, authorizer), None)
        objective = pipeline.get_objective(OBJECTIVE_ID)
        if not isinstance(objective, dict):
            raise RuntimeError("objective_not_found")
        request = objective.get("request")
        criteria = objective.get("acceptance_criteria")
        if not isinstance(request, str) or not isinstance(criteria, (list, tuple)) or any(
                not isinstance(value, str) for value in criteria):
            raise RuntimeError("objective_scope_unavailable")
        scope = [request, *criteria]
        plan = plans.get(OBJECTIVE_ID)
        if plan is not None and not isinstance(plan, dict):
            raise RuntimeError("cached_plan_shape_invalid")
        steps = plan.get("steps", []) if plan else []
        if not isinstance(steps, list) or len(steps) > 20:
            raise RuntimeError("cached_plan_shape_invalid")
        candidates = []
        for step in steps:
            if not isinstance(step, dict):
                raise RuntimeError("cached_plan_shape_invalid")
            requirements = step.get("artifact_requirements", [])
            if not isinstance(requirements, list) or len(requirements) > 32:
                raise RuntimeError("cached_artifact_requirements_invalid")
            for requirement in requirements:
                if not isinstance(requirement, dict) or not isinstance(requirement.get("path"), str):
                    raise RuntimeError("cached_artifact_requirements_invalid")
                path = requirement["path"]
                if not path or len(path) > 300:
                    raise RuntimeError("cached_artifact_path_invalid")
                candidates.append(path)
        if len(candidates) > 32:
            raise RuntimeError("cached_artifact_requirements_invalid")
        unique = list(dict.fromkeys(candidates))
        result = {
            "objective_id": OBJECTIVE_ID,
            "plan_found": plan is not None,
            "candidate_artifact_paths": unique,
            "expected_requested_path": EXPECTED_PATH,
            "expected_path_in_request": path_named(EXPECTED_PATH, request),
            "expected_path_in_acceptance_criteria": any(
                path_named(EXPECTED_PATH, criterion) for criterion in criteria),
            "authorization_match_flags": [
                {"candidate_path": path,
                 "named_in_approved_request_or_criteria": any(
                     path_named(path, text) for text in scope),
                 "matches_expected_requested_path": path == EXPECTED_PATH}
                for path in unique],
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        close = getattr(getattr(ledger, "db", None), "close", None)
        if callable(close):
            close()
        return 0
    except Exception as exc:
        reason = "cached_plan_archive_invalid" if type(exc).__name__ == "PlanArchiveInvalid" else (
            str(exc) if type(exc) is RuntimeError and str(exc) in {
            "runtime_identity_mismatch", "ambient_database_override", "database_dsn_invalid",
            "resident_office_unavailable", "credential_directory_mismatch",
            "existing_runtime_credential_unavailable", "resident_credential_invalid",
            "authorized_office_state_unavailable",
            "objective_not_found", "objective_scope_unavailable", "cached_plan_shape_invalid",
            "cached_artifact_requirements_invalid", "cached_artifact_path_invalid"} else "diagnostic_unavailable")
    print(json.dumps({"objective_id": OBJECTIVE_ID, "status": "BLOCKED",
                      "reason_code": reason}, sort_keys=True, separators=(",", ":")))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
