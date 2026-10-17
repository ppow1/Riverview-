#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/verify_grace_conversation_browser.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.5
# Purpose: Commission the dashboard-to-Grace chat path in an isolated PostgreSQL and CPU-model environment
# Execution Model: Temporary loopback llama.cpp, dashboard, Firefox WebDriver, and disposable schema
# Observability: Redacted structured result with request, persistence, refresh, recovery and timing evidence
# Dependencies: PostgreSQL 16 private socket DSN; pinned llama.cpp; pinned Qwen3 GGUF; Firefox/geckodriver
# Authority: Rejects root/shared DB targets; creates and drops only its own unique test schema
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Add real browser-to-local-model isolated commissioning harness
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Use authoritative PostgreSQL dashboard projection in browser login
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Retain stage-specific sanitized diagnostics for browser commissioning failures
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Wait for durable error as well as success and capture bounded turn timing
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Apply repository-documented Qwen no-think prefix in isolated CPU commissioning
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Wait for the current browser turn rather than an older persisted attention event
# Contracts: docs/components/RESIDENT_CONVERSATION.md; docs/components/STATUS_DASHBOARD.md
# Tests: python3 scripts/verify_grace_conversation_browser.py --help
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Run isolated browser-to-real-local-model conversation and restart checks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

from riverview_core.institutional_authority import AuthorityRegistry, ExactGrantAuthorizer
from riverview_core.local_reasoning_provider import LocalReasoningProvider
from riverview_core.postgres_migrations import apply_migrations
from riverview_core.resident_execution.conversation import (
    ConversationStore, ResidentConversationService)
from riverview_core.status_dashboard.projection import DashboardProjection
from riverview_core.status_dashboard.server import DashboardHTTPServer


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MODEL_SHA = "9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031"
MODEL_ID = "qwen3-0.6b-q8_0-local"


def _free_port(low=None, high=None):
    if low is None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]
    for port in range(low, high + 1):
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError("no free loopback port in reserved dashboard range")


def _isolated_dsn(dsn):
    if os.geteuid() == 0:
        raise RuntimeError("run as an unprivileged development account")
    values = conninfo_to_dict(dsn)
    host = values.get("host", "")
    if (not host.startswith("/tmp/rv-m43-sock-")
            or values.get("dbname") != "postgres"
            or not values.get("port", "").isdigit()):
        raise RuntimeError("DSN must target an isolated /tmp/rv-m43-sock-* postgres test cluster")
    with psycopg.connect(dsn) as db:
        row = db.execute("SELECT current_database(),r.rolsuper FROM pg_roles r WHERE r.rolname=current_user").fetchone()
    if row is None or row[0] != "postgres" or not row[1]:
        raise RuntimeError("isolated test connection must be a PostgreSQL superuser in database postgres")


def _wait_http(url, process, *, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("isolated inference process exited before readiness")
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError, OSError):
            time.sleep(0.25)
    raise RuntimeError("isolated local inference did not become ready within 90 seconds")


def _webdriver(base, path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = Request(base + path, data=data,
        headers={"Content-Type": "application/json"} if data else {}, method=method)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _wait_browser(base, session, expression, *, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = _webdriver(base, f"/session/{session}/execute/sync", "POST",
                            {"script": "return (" + expression + ");", "args": []})
        if result.get("value"):
            return result["value"]
        time.sleep(0.2)
    raise RuntimeError("browser acceptance condition timed out")


def _browser_diagnostic(base, session):
    """Return bounded UI state labels only; never capture conversation text."""
    script = "return {ready:document.readyState,workspaceHidden:document.getElementById('workspace')?.hidden,loginError:document.getElementById('login-error')?.textContent.slice(0,120),chatState:document.getElementById('chat-state')?.textContent.slice(0,120),chatError:document.getElementById('chat-error')?.textContent.slice(0,120),visibleMessages:document.querySelectorAll('#chat-history article.row').length,activeView:document.querySelector('.view.active')?.id};"
    try:
        return _webdriver(base, f"/session/{session}/execute/sync", "POST",
                          {"script":script,"args":[]}).get("value", {})
    except Exception:
        return {"diagnostic":"webdriver_unavailable"}


def _serve_dashboard(token_path, projection, service, port):
    server = DashboardHTTPServer("127.0.0.1", port, token_path, projection,
        ROOT / "src/riverview_core/status_dashboard/static",
        conversation_service=service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _provision(dsn, schema, model_sha, endpoint):
    admin = psycopg.connect(dsn, autocommit=True)
    admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    apply_migrations(dsn, schema=schema,
                     migrations_dir=ROOT / "src/riverview_core/migrations")
    apply_migrations(dsn, schema=schema,
                     migrations_dir=ROOT / "src/riverview_core/institutional_authority/migrations")
    apply_migrations(dsn, schema=schema,
                     migrations_dir=ROOT / "src/riverview_core/resident_execution/migrations")
    registry = AuthorityRegistry(dsn, schema=schema)
    steward_id = "steward:" + uuid4().hex
    steward_token = secrets.token_urlsafe(32)
    with admin.cursor() as cur:
        cur.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES (%s,'steward')").format(sql.Identifier(schema)), (steward_id,))
        cur.execute(sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,%s,%s)").format(sql.Identifier(schema)), (uuid4(), steward_id, hashlib.sha256(steward_token.encode()).digest()))
        for action in ("authority.grant", "identity.manage", "office.manage"):
            cur.execute(sql.SQL("INSERT INTO {}.authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) VALUES (%s,%s,%s,'institution',%s,'rv.policy:test.v1')").format(sql.Identifier(schema)), ("bootstrap:" + uuid4().hex, steward_id, action, steward_id))
    office_id = "office:" + uuid4().hex
    registry.create_office(steward_token, office_id, "engineering director")
    resident_id = "resident:" + uuid4().hex
    resident_token = registry.create_principal(steward_token, resident_id,
                                                "resident", office_id=office_id)
    occupant_id = "occupant:" + uuid4().hex
    registry.create_occupant(steward_token, occupant_id, principal_id=resident_id)
    implementation_id = "implementation:" + uuid4().hex
    registry.create_implementation(steward_token, implementation_id,
        kind="model", provider_ref="local.inference.v1", revision=model_sha)
    registry.bind_office(steward_token, office_id, occupant_id, implementation_id)
    registry.grant(steward_token, resident_id, "office.state.write",
        "office:" + office_id, policy_ref="rv.policy:resident-runtime.v1")
    for action in ("resident.conversation.read", "resident.conversation.send"):
        registry.grant(steward_token, steward_id, action, "office:" + office_id,
                       policy_ref="rv.policy:resident-conversation.v1")
    store = ConversationStore(dsn, schema=schema)
    provider = LocalReasoningProvider(endpoint, MODEL_ID, model_sha,
                                      chat_prefix="/no_think\n")
    service = ResidentConversationService(store=store, registry=registry,
        authorizer=ExactGrantAuthorizer(schema), office_id=office_id,
        resident_credential=resident_token, providers={provider.provider_id: provider})
    return {"admin":admin,"registry":registry,"store":store,"service":service,
        "steward_token":steward_token,"steward_id":steward_id,
        "resident_token":resident_token,"office_id":office_id,
        "occupant_id":occupant_id,"implementation_id":implementation_id}


def _close_runtime(runtime):
    runtime["store"].close()
    runtime["registry"].close()
    runtime["admin"].close()


def _resume_runtime(dsn, schema, office_id, resident_token, steward_token,
                   steward_id, model_sha, endpoint):
    """Reconstruct the web/runtime adapters from durable identity and credentials."""
    admin = psycopg.connect(dsn, autocommit=True)
    registry = AuthorityRegistry(dsn, schema=schema)
    store = ConversationStore(dsn, schema=schema)
    provider = LocalReasoningProvider(endpoint, MODEL_ID, model_sha,
                                      chat_prefix="/no_think\n")
    service = ResidentConversationService(store=store, registry=registry,
        authorizer=ExactGrantAuthorizer(schema), office_id=office_id,
        resident_credential=resident_token, providers={provider.provider_id: provider})
    return {"admin":admin,"registry":registry,"store":store,"service":service,
        "steward_token":steward_token,"steward_id":steward_id,
        "resident_token":resident_token,"office_id":office_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsn", required=True, help="isolated private PostgreSQL test DSN")
    parser.add_argument("--server", default="/tmp/rv-llama-build/bin/llama-server")
    parser.add_argument("--model", default=str(Path.home() / ".cache/riverview/models/Qwen3-0.6B-Q8_0.gguf"))
    parser.add_argument("--output", required=True, help="new evidence directory under evidence/checkouts")
    args = parser.parse_args()
    _isolated_dsn(args.dsn)
    server_binary = Path(args.server).resolve(strict=True)
    model_path = Path(args.model).resolve(strict=True)
    if not os.access(server_binary, os.X_OK):
        raise RuntimeError("the specified local llama.cpp binary is not executable")
    model_sha = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if model_sha != EXPECTED_MODEL_SHA:
        raise RuntimeError("the local model file does not match the pinned SHA-256")
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    if ROOT / "evidence/checkouts" not in output.parents:
        raise RuntimeError("evidence output must be a new repository evidence checkout directory")
    output.mkdir(parents=True, exist_ok=False)
    schema = "rvtest_chat_" + uuid4().hex
    model_port = _free_port()
    dashboard_port = _free_port(8700, 8799)
    driver_binary = shutil.which("geckodriver")
    if not driver_binary:
        raise RuntimeError("geckodriver is unavailable")
    driver_port = _free_port()
    report = {"schema_version":"rv.grace.conversation.commissioning.v1",
        "task_id":"RV-M3.4-GRACE-CHAT", "host":"Camrui", "mode":"isolated",
        "status":"FAIL", "database_schema":schema,
        "database_socket":"private /tmp/rv-m43-sock-* test cluster",
        "model":{"id":MODEL_ID,"sha256":model_sha,"binary_sha256":hashlib.sha256(server_binary.read_bytes()).hexdigest(),
            "endpoint":"loopback only","gpu_layers":0,"context_size":4096},
        "ports":{"model_loopback":model_port,"dashboard_loopback":dashboard_port,
            "geckodriver_loopback":driver_port}, "turns":[], "recovery":{},
        "stage":"preflight",
        "cleanup":{"test_schema_dropped":False,"model_process_stopped":False,
            "dashboard_process_stopped":False,"browser_session_closed":False}}
    model_process = driver_process = None
    runtime = browser_session = dashboard = dashboard_thread = None
    token_temp = tempfile.TemporaryDirectory(prefix="rv-chat-credentials-")
    schema_created = False
    browser_base = f"http://127.0.0.1:{driver_port}"
    schema_catalog = None
    try:
        command = [str(server_binary), "--model", str(model_path), "--alias", MODEL_ID,
            "--host", "127.0.0.1", "--port", str(model_port), "--jinja",
            "--threads", "2", "--threads-batch", "2", "--parallel", "1",
            "--ctx-size", "4096", "--n-predict", "512", "--n-gpu-layers", "0", "--no-webui"]
        model_process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        model_endpoint = f"http://127.0.0.1:{model_port}/v1"
        report["stage"] = "wait_local_cpu_model"
        _wait_http(f"http://127.0.0.1:{model_port}/health", model_process)
        with urlopen(f"http://127.0.0.1:{model_port}/props", timeout=5) as response:
            props = json.loads(response.read())
        report["model"]["runtime_context"] = props.get("default_generation_settings", {}).get("n_ctx")
        report["model"]["loaded_model"] = props.get("model_alias", props.get("model_path", "observed"))

        runtime = _provision(args.dsn, schema, model_sha, model_endpoint)
        schema_created = True
        dashboard_token = secrets.token_urlsafe(36)
        token_path = Path(token_temp.name) / "dashboard-token"
        token_path.write_text(dashboard_token, encoding="ascii")
        token_path.chmod(0o600)
        projection = DashboardProjection(args.dsn, schema=schema,
            source_commit=os.environ.get("RIVERVIEW_SOURCE_COMMIT", "unknown"),
            deployment_id="isolated-chat-test")
        dashboard, dashboard_thread = _serve_dashboard(token_path, projection,
                                                       runtime["service"], dashboard_port)
        report["stage"] = "wait_geckodriver"
        driver_process = subprocess.Popen([driver_binary, "--host", "127.0.0.1",
            "--port", str(driver_port)], stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        _wait_http(browser_base + "/status", driver_process, timeout=15)
        session = _webdriver(browser_base, "/session", "POST", {"capabilities":{"alwaysMatch":{
            "browserName":"firefox","moz:firefoxOptions":{"args":["-headless"]}}}})
        browser_session = session["value"].get("sessionId") or session.get("sessionId")
        if not browser_session:
            raise RuntimeError("Firefox WebDriver session was not created")
        report["stage"] = "load_dashboard_in_firefox"
        _webdriver(browser_base, f"/session/{browser_session}/url", "POST",
                    {"url":f"http://127.0.0.1:{dashboard_port}/"})
        _wait_browser(browser_base, browser_session, "document.readyState === 'complete'")
        report["stage"] = "dashboard_bearer_login"
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.getElementById('token').value=arguments[0];document.getElementById('login-form').requestSubmit();",
            "args":[dashboard_token]})
        _wait_browser(browser_base, browser_session, "document.getElementById('workspace').hidden === false")
        report["stage"] = "resident_chat_authorized_history"
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('[data-view=grace-chat]').click();document.getElementById('chat-authority').value=arguments[0];document.getElementById('chat-authority').dispatchEvent(new Event('change'));",
            "args":[runtime["steward_token"]]})
        _wait_browser(browser_base, browser_session,
                      "document.getElementById('chat-state').textContent.includes('PostgreSQL')")

        def browser_turn(message):
            report["stage"] = "browser_chat_model_turn"
            started = time.monotonic()
            before = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
                "script":"window.__rvTurnStart=performance.now();window.__rvBeforeChatCount=document.querySelectorAll('#chat-history article.row').length;document.getElementById('chat-message').value=arguments[0];document.getElementById('chat-form').requestSubmit();",
                "args":[message]})
            _wait_browser(browser_base, browser_session,
                "(document.getElementById('chat-history').querySelectorAll('article.row').length >= window.__rvBeforeChatCount + 2 || (!document.getElementById('chat-send').disabled && document.getElementById('chat-error').textContent.includes('Grace response failed'))) && document.getElementById('chat-state').textContent.includes('PostgreSQL')",
                timeout=150)
            failure = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
                "script":"return document.getElementById('chat-error').textContent;","args":[]})["value"]
            if failure:
                raise RuntimeError("browser chat returned a failed response: " + str(failure)[:100])
            values = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
                "script":"return {messages:Array.from(document.querySelectorAll('#chat-history article.row')).map(x=>x.innerText),elapsed_ms:performance.now()-window.__rvTurnStart,conversation:localStorage.getItem('rv.grace.conversation')};",
                "args":[]})["value"]
            return {"elapsed_wall_ms":round((time.monotonic()-started)*1000,2),
                "browser_elapsed_ms":round(values["elapsed_ms"],2),
                "conversation_id":values["conversation"],
                "last_message":str(values["messages"][-1])[:500]}

        first = browser_turn("Hi Grace. Reply with one short greeting and identify your resident role.")
        report["turns"].append({"phase":"first_browser_inference",**first})
        conversation_id = first["conversation_id"]
        if not conversation_id:
            raise RuntimeError("browser did not retain the conversation identifier")

        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST",
                   {"script":"location.reload();","args":[]})
        _wait_browser(browser_base, browser_session,
                      "document.getElementById('workspace').hidden === false", timeout=30)
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('[data-view=grace-chat]').click();document.getElementById('chat-authority').value=arguments[0];document.getElementById('chat-authority').dispatchEvent(new Event('change'));",
            "args":[runtime["steward_token"]]})
        _wait_browser(browser_base, browser_session,
            "document.getElementById('chat-history').innerText.includes('Hi Grace')", timeout=30)
        report["browser_refresh"] = {"status":"PASS","history_reloaded":True,
            "conversation_id_retained":conversation_id}

        binding = runtime["registry"].authorize_office_state(
            runtime["resident_token"], runtime["office_id"])
        runtime["store"].begin_turn(office_id=runtime["office_id"],
            principal_id=runtime["steward_id"], occupant=binding,
            implementation={"office_id":runtime["office_id"],
                "implementation_id":binding["implementation_id"],
                "implementation_revision":binding["implementation_revision"],
                "provider_ref":binding["provider_ref"],"model_id":MODEL_ID},
            message="controlled interruption fixture",conversation_id=conversation_id,
            client_message_id=str(uuid4()))
        dashboard.shutdown(); dashboard.server_close(); dashboard_thread.join(timeout=3)
        dashboard = dashboard_thread = None
        previous = runtime
        _close_runtime(runtime)
        runtime = _resume_runtime(args.dsn, schema, previous["office_id"],
            previous["resident_token"], previous["steward_token"],
            previous["steward_id"], model_sha, model_endpoint)
        interrupted = runtime["store"].recover_pending()
        report["recovery"] = {"supporting_http_service_restarted":True,
            "unfinished_turns_marked_interrupted":interrupted}
        projection = DashboardProjection(args.dsn, schema=schema,
            source_commit=os.environ.get("RIVERVIEW_SOURCE_COMMIT", "unknown"),
            deployment_id="isolated-chat-test")
        dashboard, dashboard_thread = _serve_dashboard(token_path, projection,
                                                       runtime["service"], dashboard_port)
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST",
                   {"script":"location.reload();","args":[]})
        _wait_browser(browser_base, browser_session,
                      "document.getElementById('workspace').hidden === false", timeout=30)
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('[data-view=grace-chat]').click();document.getElementById('chat-authority').value=arguments[0];document.getElementById('chat-authority').dispatchEvent(new Event('change'));",
            "args":[runtime["steward_token"]]})
        _wait_browser(browser_base, browser_session,
            "document.getElementById('chat-history').innerText.includes('controlled interruption fixture')", timeout=30)
        _wait_browser(browser_base, browser_session,
            "document.getElementById('chat-error').textContent.includes('service_restarted')", timeout=30)
        report["recovery"]["browser_history_and_interruption_visible"] = True
        second = browser_turn("Continue after restart. Reply briefly that Grace's office history remains available.")
        report["turns"].append({"phase":"post_restart_browser_inference",**second})

        with psycopg.connect(args.dsn, row_factory=psycopg.rows.dict_row) as verify_db:
            verify_db.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            row = verify_db.execute("""SELECT count(*) FILTER (WHERE event_type='user_message') AS user_messages,
                count(*) FILTER (WHERE event_type='assistant_message') AS assistant_messages,
                count(*) FILTER (WHERE event_type='response_interrupted') AS interruptions,
                count(DISTINCT model_id) FILTER (WHERE event_type='assistant_message') AS models
                FROM resident_conversation_events""").fetchone()
            work_orders = verify_db.execute("SELECT count(*) FROM grace_objectives").fetchone()[0]
        report["postgresql"] = {key:int(value) for key,value in row.items()}
        report["postgresql"]["objectives_created_by_chat"] = int(work_orders)
        if row["assistant_messages"] < 2 or row["interruptions"] != 1 or work_orders != 0:
            raise RuntimeError("persisted conversation verification did not match the expected outcomes")
        report["browser_refresh"]["post_restart_continuation"] = "PASS"
        report["status"] = "PASS"
    except Exception as exc:
        report["failure_type"] = type(exc).__name__
        report["failure_code"] = str(exc)[:180]
        report["failed_stage"] = report.get("stage")
        if browser_session and driver_process and driver_process.poll() is None:
            report["browser_state"] = _browser_diagnostic(browser_base, browser_session)
    finally:
        if browser_session and driver_process and driver_process.poll() is None:
            try:
                _webdriver(browser_base, f"/session/{browser_session}", "DELETE")
                report["cleanup"]["browser_session_closed"] = True
            except Exception:
                pass
        if dashboard is not None:
            dashboard.shutdown(); dashboard.server_close()
            if dashboard_thread:
                dashboard_thread.join(timeout=3)
            report["cleanup"]["dashboard_process_stopped"] = True
        if runtime is not None:
            _close_runtime(runtime)
        if driver_process is not None:
            driver_process.terminate()
            try:
                driver_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                driver_process.kill(); driver_process.wait(timeout=5)
        if model_process is not None:
            model_process.terminate()
            try:
                model_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                model_process.kill(); model_process.wait(timeout=5)
            report["cleanup"]["model_process_stopped"] = True
        try:
            with psycopg.connect(args.dsn, autocommit=True) as cleanup_db:
                cleanup_db.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            report["cleanup"]["test_schema_dropped"] = True
        except Exception:
            report["cleanup"]["test_schema_dropped"] = False
        token_temp.cleanup()
        report["finished_at_epoch"] = time.time()
        evidence_file = output / "browser-commissioning.json"
        evidence_file.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        evidence_file.with_suffix(".sha256").write_text(
            hashlib.sha256(evidence_file.read_bytes()).hexdigest() + "  " + evidence_file.name + "\n",
            encoding="ascii")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
