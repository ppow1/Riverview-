# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/verify_local_inference.py
# Component: LOCAL-INFERENCE-WORKER
# Revision: 1.0.5
# Purpose: Run two real local model jobs through an isolated PostgreSQL worker cycle
# Execution Model: Temporary loopback llama.cpp server and unique disposable schema
# Observability: Redacted report with assignment, attempt, verification, queue and latency evidence
# Dependencies: Python 3.10+; Psycopg 3; built llama-server; pinned local GGUF model
# Authority: Rejects root/shared DSNs; synthetic test identities and schema only
# Changed: 2026-10-11 UTC | RV-M4.3-LOCAL-INFERENCE | Derive queue latency from durable assignment-created event
# Contracts: docs/components/WORKER_ADAPTER.md; docs/ROADMAP.md
# Tests: tests/test_local_inference.py; tests/test_worker_adapter.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Execute and independently verify two real loopback-model jobs in isolation."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from riverview_core.postgres_ledger import PostgresLedger
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.worker_adapter import (
    ContinuousWorker, KnowledgeResult, KnowledgeStatus, LocalInferenceAction,
    PostgresWorkerAdapter, VerificationResult, VerificationStatus,
)


MODEL_REVISION = "23749fefcc72300e3a2ad315e1317431b06b590a"
MODEL_SHA256 = "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031"
MODEL_ID = "qwen3-0.6b-q8_0-local"
TEST_CASES = (
    ("authentication", "AUTH", "/no_think\nClassify the operational symptom. "
     "Reply with exactly one label, AUTH or RESOURCE. Expired bearer credentials "
     "are an authentication failure. Symptom: expired bearer credentials."),
    ("storage", "RESOURCE", "/no_think\nClassify the operational symptom. "
     "Reply with exactly one label, AUTH or RESOURCE. A full disk is a resource "
     "failure. Symptom: the filesystem has no free space."),
)


def _choose_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_ready(process, port, log_path, timeout=90):
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("local inference server exited before health readiness")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(0.25)
    raise RuntimeError(f"local inference server did not become ready; log={log_path.name}")


def _require_isolated_dsn(dsn):
    if os.geteuid() == 0:
        raise RuntimeError("run as an unprivileged development user")
    values = conninfo_to_dict(dsn)
    host = values.get("host", "")
    if (not host.startswith("/tmp/rv-m43-sock-") or
            values.get("port") != "55489" or values.get("dbname") != "postgres"):
        raise RuntimeError("DSN must target the private /tmp/rv-m43-sock-* test cluster on port 55489")
    with psycopg.connect(dsn, autocommit=True) as db:
        row = db.execute("SELECT current_database(),r.rolsuper FROM pg_roles r WHERE r.rolname=current_user").fetchone()
        if row is None or row[0] != "postgres" or not row[1]:
            raise RuntimeError("isolated test connection must be a PostgreSQL superuser in database postgres")


class FixtureKnowledge:
    """Test-only complete lookup over the two fixed, versioned test prompts."""

    def __init__(self, prompts, source_sha):
        self.prompts = prompts
        self.source_sha = source_sha

    def _verified(self, value):
        return KnowledgeResult(
            KnowledgeStatus.VERIFIED, value=value,
            source_references=("repo://scripts/verify_local_inference.py",),
            source_revision="RV-M4.3-fixture-v1", source_sha256=self.source_sha,
            retrieval_complete=True)

    def ground_assignment(self, assignment):
        return self._verified(self.prompts[assignment["id"]])

    def preflight_action(self, assignment, action):
        return self._verified({"action": action, "test_fixture": True})

    def reground_assignment(self, assignment, trigger):
        return self._verified(self.prompts[assignment["id"]])

    def record_learning(self, assignment, outcome):
        return KnowledgeResult(KnowledgeStatus.UNAVAILABLE)


class LabelVerifier:
    """Independent test verifier checks expected label and served model provenance."""

    REVISION = "RV-M4.3-label-verifier-v1"

    def verify(self, assignment, attempt, result):
        expected = assignment["objective_ref"].rsplit(":", 1)[-1]
        output = result.get("output", "") if isinstance(result, dict) else ""
        final = output.rsplit("</think>", 1)[-1].strip().upper()
        accepted_label = final == expected
        criteria = {
            "worker_attempt_succeeded": attempt.get("status") == "succeeded",
            "result_artifact_is_object": isinstance(result, dict),
            "model_returned_expected_label": accepted_label,
            "served_model_reported": bool(result.get("served_model")) if isinstance(result, dict) else False,
            "finish_reason_is_stop": result.get("finish_reason") == "stop" if isinstance(result, dict) else False,
        }
        return VerificationResult(
            VerificationStatus.ACCEPTED if all(criteria.values()) else VerificationStatus.REJECTED,
            criteria, (f"urn:rv:worker-attempt:{attempt['attempt_id']}",), self.REVISION,
            "local inference output matches the explicit isolated label criterion"
            if all(criteria.values()) else "local inference output did not match the criterion")


def _seed_identity(db, schema, principal_id, kind, granted_by, grants, scope):
    token = secrets.token_urlsafe(32)
    with db.transaction():
        db.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,%s)")
                   .format(sql.Identifier(schema)), (principal_id, kind))
        db.execute(sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)")
                   .format(sql.Identifier(schema)),
                   (uuid4(), principal_id, hashlib.sha256(token.encode()).digest()))
        for action, scope_ref in grants:
            db.execute(sql.SQL("""INSERT INTO {}.authority_grants
                (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
                VALUES (%s,%s,%s,%s,%s,'rv.policy:m43-isolated-test.v1')""")
                .format(sql.Identifier(schema)),
                (f"m43:{action}:{principal_id}", principal_id, action,
                 scope_ref or scope, granted_by))
    return token


def _run(args):
    _require_isolated_dsn(args.dsn)
    model_path = Path(args.model).resolve(strict=True)
    server_path = Path(args.server).resolve(strict=True)
    actual_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if actual_sha != MODEL_SHA256:
        raise RuntimeError("model file does not match the pinned SHA-256")
    if not os.access(server_path, os.X_OK):
        raise RuntimeError("server binary is not executable")

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    server_log_path = output / "llama-server.log"
    port = _choose_port()
    endpoint = f"http://127.0.0.1:{port}/v1"
    prompts = {}
    expected = {}
    for label, answer, prompt in TEST_CASES:
        assignment_id = f"m43-{label}-{uuid4().hex}"
        prompts[assignment_id] = prompt
        expected[assignment_id] = answer
    source_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    schema = "rvtest_m43_" + uuid4().hex[:20]
    server_process = None
    adapters = []
    ledger = None
    db = psycopg.connect(args.dsn, autocommit=True)
    report = {
        "status": "IN_PROGRESS", "component": "LOCAL-INFERENCE-WORKER",
        "schema": schema, "endpoint_host": "127.0.0.1", "port": port,
        "model_revision": MODEL_REVISION, "model_sha256": actual_sha,
        "llama_cpp_source_commit": "d81235049384534c167caea52b85a694f6103d14",
        "llama_server_sha256": hashlib.sha256(server_path.read_bytes()).hexdigest(),
        "source_commit": subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parents[1]), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True).stdout.strip(),
        "source_tree_dirty": bool(subprocess.run(
            ["git", "-C", str(Path(__file__).resolve().parents[1]), "status", "--porcelain"],
            check=True, capture_output=True, text=True).stdout.strip()),
        "assignments": [], "server_exit_code": None,
        "cleanup": {"schema_dropped": False, "server_stopped": server_process is None},
        "fixture_knowledge_provider": "fixed test cases only; not institutional retrieval",
    }
    try:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        core = Path(__file__).resolve().parents[1] / "src/riverview_core"
        apply_migrations(args.dsn, schema=schema)
        apply_migrations(args.dsn, schema=schema,
                         migrations_dir=core / "assignment_scheduler/migrations")
        apply_migrations(args.dsn, schema=schema,
                         migrations_dir=core / "worker_adapter/migrations")
        apply_migrations(args.dsn, schema=schema,
                         migrations_dir=core / "institutional_authority/migrations")
        ledger = PostgresLedger(args.dsn, schema=schema)
        action = LocalInferenceAction(endpoint, MODEL_ID,
                                      model_revision=MODEL_REVISION,
                                      model_sha256=actual_sha,
                                      timeout_seconds=90, max_tokens=24)
        server_args = [str(server_path), "--model", str(model_path), "--alias", MODEL_ID,
                       "--host", "127.0.0.1", "--port", str(port), "--jinja",
                       "--threads", "2", "--threads-batch", "2", "--parallel", "2",
                       "--ctx-size", "2048", "--n-predict", "24", "--no-webui"]
        with server_log_path.open("wb") as server_log:
            server_process = subprocess.Popen(server_args, stdout=server_log,
                                              stderr=subprocess.STDOUT, close_fds=True)
            _wait_ready(server_process, port, server_log_path)

            steward_id = "steward:m43-isolated-test"
            steward_token = _seed_identity(
                db, schema, steward_id, "steward", steward_id,
                [("worker.register", "institution"), ("authority.grant", "institution")], "institution")
            # Test setup is performed by the database superuser; the random token
            # is kept in memory and no test identity or grant reaches shared state.
            del steward_token
            scope = "grant:m43-local-inference-test"
            worker_records = []
            for index, assignment_id in enumerate(prompts, start=1):
                worker_id = f"worker:m43-local-{index}"
                token = _seed_identity(
                    db, schema, worker_id, "worker", steward_id,
                    [("worker.register", scope), ("assignment.execute", scope)], scope)
                worker_records.append((worker_id, token, assignment_id))
            verifier_id = "worker:m43-independent-verifier"
            verifier_token = _seed_identity(
                db, schema, verifier_id, "worker", steward_id,
                [("worker.register", scope), ("assignment.verify", scope)], scope)

            for assignment_id in prompts:
                ledger.create(assignment_id, "engineering", f"create:{assignment_id}",
                              authority_ref=scope,
                              objective_ref=f"test:local-label:{expected[assignment_id]}",
                              actor_id=steward_id,
                              contract_ref="rv.local-inference.test.v1",
                              workflow_id="m43.local-inference.v1", workflow_step="intake")
                ledger.transition(assignment_id, "ready", "test_dispatch",
                                  f"ready:{assignment_id}", actor_id="fixture:dispatcher")

            knowledge = FixtureKnowledge(prompts, source_sha)
            def execute(worker_record):
                worker_id, token, assignment_id = worker_record
                adapter = PostgresWorkerAdapter(args.dsn, schema=schema,
                                                authority_schema=schema)
                adapters.append(adapter)
                adapter.register_worker(worker_id, [LocalInferenceAction.CAPABILITY], scope,
                                        credential=token)
                worker = ContinuousWorker(
                    adapter, worker_id, token, knowledge=knowledge,
                    lease_seconds=180, action=action,
                    action_effect_class="retry_safe",
                    action_capability=LocalInferenceAction.CAPABILITY)
                started = time.monotonic()
                outcome = worker.run_once()
                return {"assignment_id": assignment_id, "worker_id": worker_id,
                        "claimed_assignment_id": outcome.get("assignment_id"),
                        "elapsed_ms": round((time.monotonic()-started)*1000, 1),
                        "outcome": outcome}

            results = []
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(execute, item) for item in worker_records]
                for future in as_completed(futures, timeout=240):
                    results.append(future.result())
            if len(results) != 2 or any(item["outcome"].get("status") != "AWAITING_VERIFICATION"
                                        for item in results):
                raise RuntimeError("one or more local inference assignments did not persist a successful attempt")
            if ({item["claimed_assignment_id"] for item in results} != set(prompts) or
                    len({item["claimed_assignment_id"] for item in results}) != 2):
                raise RuntimeError("concurrent workers did not claim each distinct test assignment exactly once")
            report["assignments"] = results

            verifier_adapter = PostgresWorkerAdapter(args.dsn, schema=schema,
                                                      authority_schema=schema)
            adapters.append(verifier_adapter)
            verifier_adapter.register_worker(verifier_id, ["assignment.verify.v1"], scope,
                                             credential=verifier_token)
            for item in results:
                outcome = item["outcome"]
                assignment_id = item["claimed_assignment_id"]
                decision = verifier_adapter.verify_attempt(
                    assignment_id, outcome["attempt_id"], verifier_id,
                    verifier_token, LabelVerifier(),
                    idempotency_key=f"verify:{assignment_id}")
                assignment = ledger.get(assignment_id)
                with ledger.db.cursor() as cur:
                    ledger._set_search_path(cur)
                    cur.execute("""SELECT a.capability,a.status,a.started_at,a.finished_at,
                                          (SELECT min(e.recorded_at) FROM events e
                                           WHERE e.assignment_id=a.assignment_id
                                             AND e.event_type='assignment.created') AS created_at,
                                          r.result,r.result_sha256,v.decision,v.verifier_id
                                   FROM worker_attempts a JOIN worker_results r USING(attempt_id)
                                   JOIN verification_records v USING(attempt_id)
                                   WHERE a.attempt_id=%s""", (outcome["attempt_id"],))
                    durable = cur.fetchone()
                canonical = json.dumps(durable["result"], sort_keys=True,
                                       separators=(",", ":"), ensure_ascii=False).encode()
                artifact_hash_valid = hashlib.sha256(canonical).hexdigest() == durable["result_sha256"].strip()
                if (decision.status is not VerificationStatus.ACCEPTED or
                        assignment["state"] != "completed" or not artifact_hash_valid):
                    raise RuntimeError("independent artifact verification did not accept persisted output")
                item.update({"state": assignment["state"],
                             "attempt_id": str(outcome["attempt_id"]),
                             "capability": durable["capability"],
                             "attempt_status": durable["status"],
                             "result": durable["result"],
                             "result_sha256": durable["result_sha256"].strip(),
                             "verification": decision.status.value,
                             "verifier_id": durable["verifier_id"],
                             "artifact_hash_valid": artifact_hash_valid,
                             "queued_at": durable["created_at"].isoformat(),
                             "attempt_started_at": durable["started_at"].isoformat(),
                             "attempt_finished_at": durable["finished_at"].isoformat(),
                             "queue_delay_ms": round((durable["started_at"] - durable["created_at"]).total_seconds()*1000, 1),
                             "model_execution_ms": round((durable["finished_at"] - durable["started_at"]).total_seconds()*1000, 1)})
                starts = [item["attempt_started_at"] for item in results]
                finishes = [item["attempt_finished_at"] for item in results]
                from datetime import datetime
                start_times = [datetime.fromisoformat(value) for value in starts]
                finish_times = [datetime.fromisoformat(value) for value in finishes]
                overlap_ms = max(0.0, (min(finish_times) - max(start_times)).total_seconds()*1000)
                if overlap_ms <= 0:
                    raise RuntimeError("model attempts did not overlap in PostgreSQL runtime timestamps")
            results.sort(key=lambda item: item["assignment_id"])
            report.update({"status": "PASS", "assignments": results,
                           "concurrency": {"workers": 2, "max_workers": 2,
                                           "distinct_assignments": 2,
                                           "parallel_attempt_overlap_ms": round(overlap_ms, 1)},
                           "cleanup": {"schema_dropped": False,
                                       "server_stopped": False}})
    except Exception as exc:
        report.update({"status": "FAIL", "failure_type": type(exc).__name__,
                       "failure_detail": str(exc)[:300]})
        raise
    finally:
        for adapter in adapters:
            try:
                adapter.close()
            except Exception:
                pass
        if ledger is not None:
            try:
                ledger.close()
            except Exception:
                pass
        # Drop only this script's unpredictable test schema, in the verified
        # disposable database. Never contact or modify shared riverview_dev.
        try:
            db.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            report["cleanup"]["schema_dropped"] = True
            report["cleanup"]["schema_absent"] = db.execute(
                "SELECT to_regnamespace(%s) IS NULL", (schema,)).fetchone()[0]
        except Exception:
            report["cleanup"]["schema_dropped"] = False
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait(timeout=5)
            report["server_exit_code"] = server_process.returncode
            report["cleanup"]["server_stopped"] = server_process.poll() is not None
        db.close()
        (output / "acceptance.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="private UTF-8 test-cluster DSN; never riverview_dev")
    parser.add_argument("--server", required=True, help="llama-server binary built from pinned source")
    parser.add_argument("--model", required=True, help="pinned local Qwen3 GGUF path")
    parser.add_argument("--output", required=True, help="new evidence directory; must not exist")
    args = parser.parse_args()
    try:
        report = _run(args)
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "failure_type": type(exc).__name__,
                          "detail": str(exc)[:300]}), file=sys.stderr)
        return 1
    print(json.dumps({"status": report["status"],
                      "assignments": len(report.get("assignments", [])),
                      "all_verified": all(item.get("verification") == "ACCEPTED"
                                           for item in report.get("assignments", [])),
                      "server_stopped": report.get("cleanup", {}).get("server_stopped"),
                      "schema_dropped": report.get("cleanup", {}).get("schema_dropped")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
