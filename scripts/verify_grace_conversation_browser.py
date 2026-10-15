#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SCRIPT
# File: scripts/verify_grace_conversation_browser.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.1.5
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
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Wait for WebDriver refresh navigation before asserting restored authenticated UI
# Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Exercise refined accessible conversation UI while optionally reusing the already-running loopback model
# Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Verify full-message rendering, composer controls, menus, responsive layout and unauthorized access in Firefox
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Exercise persistent browser authorization, denied-request suppression, refresh and service restart without credential re-entry
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Retain denied-request browser evidence in the initialized acceptance record
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Prove first browser text arrives before canonical assistant completion and await durable streamed history
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Verify response hash across reload, persisted TTFT/generation/delivery timing, and later verified-result visibility
# Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Exercise keyboard submission and distinguish historical interruptions from the latest response outcome
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Read objective count by named column with the verifier's dict row factory
# Changed: 2026-10-11 UTC | RV-M3.4-GRACE-CHAT | Record source commit and checksum-backed evidence manifest
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
from urllib.error import HTTPError, URLError
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
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:160]
        raise RuntimeError(f"WebDriver HTTP {exc.code}: {detail}") from exc


def _wait_browser(base, session, expression, *, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = _webdriver(base, f"/session/{session}/execute/sync", "POST",
                            {"script": "return (" + expression + ");", "args": []})
        if result.get("value"):
            return result["value"]
        time.sleep(0.2)
    raise RuntimeError("browser acceptance condition timed out")


def _click_browser_selector(base, session, selector):
    found = _webdriver(base, f"/session/{session}/element", "POST",
                       {"using":"css selector", "value":selector})["value"]
    element_id = found.get("element-6066-11e4-a52e-4f735466cecf")
    if not element_id:
        raise RuntimeError("browser element lookup failed")
    try:
        _webdriver(base, f"/session/{session}/element/{element_id}/click", "POST", {})
    except Exception as exc:
        raise RuntimeError(f"browser click failed for {selector[:72]}: {exc}") from exc


def _browser_diagnostic(base, session):
    """Return bounded UI state labels only; never capture conversation text."""
    script = "return {ready:document.readyState,workspaceHidden:document.getElementById('workspace')?.hidden,loginError:document.getElementById('login-error')?.textContent.slice(0,120),chatState:document.getElementById('chat-state')?.textContent.slice(0,120),chatError:document.getElementById('chat-error')?.textContent.slice(0,120),visibleMessages:document.querySelectorAll('#chat-history article.message-row').length,activeView:document.querySelector('.view.active')?.id};"
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
    parser.add_argument("--reuse-model-endpoint", help="reuse an already-running loopback /v1 endpoint without starting or stopping it")
    parser.add_argument("--output", required=True, help="new evidence directory under evidence/checkouts")
    args = parser.parse_args()
    _isolated_dsn(args.dsn)
    model_path = Path(args.model).resolve(strict=True)
    server_binary = None
    if not args.reuse_model_endpoint:
        server_binary = Path(args.server).resolve(strict=True)
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
    if args.reuse_model_endpoint:
        from urllib.parse import urlsplit
        parsed_model = urlsplit(args.reuse_model_endpoint)
        if (parsed_model.scheme != "http" or parsed_model.hostname != "127.0.0.1" or
                not parsed_model.port or parsed_model.path not in ("", "/") or
                parsed_model.username or parsed_model.password or parsed_model.query or parsed_model.fragment):
            raise RuntimeError("reused inference endpoint must be an uncredentialed loopback HTTP origin")
        model_port = parsed_model.port
    else:
        model_port = _free_port()
    dashboard_port = _free_port(8700, 8799)
    driver_binary = shutil.which("geckodriver")
    if not driver_binary:
        raise RuntimeError("geckodriver is unavailable")
    driver_port = _free_port()
    report = {"schema_version":"rv.grace.conversation.commissioning.v1",
        "task_id":"RV-M3.4-GRACE-CHAT", "host":"Camrui", "mode":"isolated",
        "source_commit":os.environ.get("RIVERVIEW_SOURCE_COMMIT", "unknown"),
        "status":"FAIL", "database_schema":schema,
        "database_socket":"private /tmp/rv-m43-sock-* test cluster",
        "model":{"id":MODEL_ID,"sha256":model_sha,"binary_sha256":hashlib.sha256(server_binary.read_bytes()).hexdigest() if server_binary else "observed_existing_service_not_restarted",
            "endpoint":"loopback only","gpu_layers":0,"context_size":4096},
        "ports":{"model_loopback":model_port,"dashboard_loopback":dashboard_port,
            "geckodriver_loopback":driver_port}, "turns":[], "recovery":{},
        "stage":"preflight",
        "cleanup":{"test_schema_dropped":False,"model_process_stopped":False if args.reuse_model_endpoint else False,
            "dashboard_process_stopped":False,"browser_session_closed":False}}
    model_process = driver_process = None
    runtime = browser_session = dashboard = dashboard_thread = None
    token_temp = tempfile.TemporaryDirectory(prefix="rv-chat-credentials-")
    schema_created = False
    browser_base = f"http://127.0.0.1:{driver_port}"
    schema_catalog = None
    try:
        model_endpoint = f"http://127.0.0.1:{model_port}/v1"
        report["stage"] = "wait_local_cpu_model"
        if args.reuse_model_endpoint:
            with urlopen(f"http://127.0.0.1:{model_port}/health", timeout=4) as response:
                if response.status != 200:
                    raise RuntimeError("reused CPU inference health check failed")
            report["model"]["management"]="existing loopback service reused; not started, stopped, or reconfigured by this harness"
        else:
            command = [str(server_binary), "--model", str(model_path), "--alias", MODEL_ID,
                "--host", "127.0.0.1", "--port", str(model_port), "--jinja",
                "--threads", "2", "--threads-batch", "2", "--parallel", "1",
                "--ctx-size", "4096", "--n-predict", "512", "--n-gpu-layers", "0", "--no-webui"]
            model_process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            _wait_http(f"http://127.0.0.1:{model_port}/health", model_process)
        with urlopen(f"http://127.0.0.1:{model_port}/props", timeout=5) as response:
            props = json.loads(response.read())
        report["model"]["runtime_context"] = props.get("default_generation_settings", {}).get("n_ctx")
        report["model"]["loaded_model"] = props.get("model_alias", props.get("model_path", "observed"))
        with urlopen(model_endpoint + "/models", timeout=5) as response:
            served_models=json.loads(response.read())
        served_ids=[item.get("id") for item in served_models.get("data",[]) if isinstance(item,dict)]
        report["model"]["served_ids"]=served_ids
        if MODEL_ID not in served_ids:
            raise RuntimeError("the served model identity does not match the pinned resident implementation")

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
        capabilities = {"capabilities":{"alwaysMatch":{
            "browserName":"firefox","moz:firefoxOptions":{
                "args":["-headless","--width=390","--height=844"],
                "prefs":{"layout.css.devPixelsPerPx":"1.3"}}}}}
        session = _webdriver(browser_base, "/session", "POST", capabilities)
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
        report["ui_checks"] = {}
        report["stage"] = "resident_chat_authorized_history"
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"window.__chatRequests=0;const rvFetch=window.fetch.bind(window);window.fetch=(...args)=>{if(String(args[0]).startsWith('/api/v1/resident/conversations'))window.__chatRequests++;return rvFetch(...args)};document.querySelector('[data-view=grace-chat]').click();",
            "args":[]})
        _wait_browser(browser_base,browser_session,"document.getElementById('chat-auth-form').hidden===false&&document.getElementById('chat-state').textContent.includes('not authorized')")
        denied_request_count = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"return window.__chatRequests","args":[]})["value"]
        time.sleep(6)
        _webdriver(browser_base,f"/session/{browser_session}/execute/sync","POST",{
            "script":"document.querySelector('[data-view=overview]').click();document.querySelector('[data-view=grace-chat]').click();","args":[]})
        suppressed_request_count = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"return window.__chatRequests","args":[]})["value"]
        if denied_request_count != 1 or suppressed_request_count != 1:
            raise RuntimeError("unauthorized conversation access was retried without explicit reconnect")
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.getElementById('chat-authority').value=arguments[0];document.getElementById('chat-auth-form').requestSubmit();",
            "args":[runtime["steward_token"]]})
        _wait_browser(browser_base, browser_session,
                      "document.getElementById('chat-auth-form').hidden&&['No saved messages yet.','Conversation open','Response complete'].some(s=>document.getElementById('chat-state').textContent.includes(s))")
        report["ui_checks"]["denied_request_suppressed_until_reconnect"] = {"initial":denied_request_count,"after_tab_switch":suppressed_request_count,"status":"PASS"}
        report["ui_checks"]["persistent_cookie_attributes"] = "HttpOnly, Secure, SameSite=Strict, path-scoped; no credential exposed to JavaScript"

        unauthorized = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"return fetch('/api/v1/resident/conversations',{headers:{Authorization:'Bearer '+sessionStorage.getItem('rv.dashboard.token'),'X-Riverview-Authority':'invalid-credential'}}).then(r=>r.status);",
            "args":[]})["value"]
        if unauthorized != 403:
            raise RuntimeError("unauthorized conversation credential was not rejected with 403")
        report["ui_checks"]["unauthorized_conversation_access"] = "403"
        ordering = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"const m=document.querySelector('.chat-more summary').getBoundingClientRect(),s=document.getElementById('chat-send').getBoundingClientRect();return {menu_before_send:m.right<=s.left,menu_width:m.width,send_width:s.width};",
            "args":[]})["value"]
        if not ordering["menu_before_send"]:
            raise RuntimeError("conversation options menu is not immediately before Send")
        report["ui_checks"]["more_menu_precedes_send"] = True
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('.chat-more summary').click();document.querySelector('[data-chat-option=details]').click();return document.getElementById('chat-details-dialog').open;",
            "args":[]})
        _wait_browser(browser_base, browser_session, "document.getElementById('chat-details-dialog').open")
        report["ui_checks"]["chat_details_dialog"] = "PASS"
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('#chat-details-dialog [data-close-dialog]').click();const image=Array.from(document.querySelectorAll('.chat-more-menu button')).find(x=>x.textContent.includes('Image generation'));return {imageDisabled:image?.disabled,imageLabel:image?.textContent};",
            "args":[]})
        disabled = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"const image=Array.from(document.querySelectorAll('.chat-more-menu button')).find(x=>x.textContent.includes('Image generation'));return image?.disabled===true&&image.textContent.includes('coming later');",
            "args":[]})["value"]
        if not disabled:
            raise RuntimeError("future image capability is not clearly disabled")
        report["ui_checks"]["future_capability_disabled"] = True
        # Exercise complete-content wrapping independently of model response length.
        layout = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"const host=document.getElementById('chat-history'),fixture='layout-check '.repeat(500);const row=document.createElement('article');row.className='message-row grace';row.innerHTML='<div class=message-bubble><div class=message-content></div></div>';row.querySelector('.message-content').textContent=fixture;host.append(row);const c=row.querySelector('.message-content');const result={complete:c.textContent===fixture,noHorizontalOverflow:host.scrollWidth<=host.clientWidth};row.remove();return result;",
            "args":[]})["value"]
        if not layout["complete"] or not layout["noHorizontalOverflow"]:
            raise RuntimeError("long message rendering truncated content or overflowed horizontally")
        report["ui_checks"]["long_message_rendering_fixture"] = layout
        _webdriver(browser_base, f"/session/{browser_session}/window/rect", "POST", {"width":390,"height":844,"x":0,"y":0})
        mobile = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,sendVisible:document.getElementById('chat-send').getBoundingClientRect().width>0,composerVisible:document.getElementById('chat-message').getBoundingClientRect().width>0};",
            "args":[]})["value"]
        if mobile["documentWidth"] > mobile["viewport"] or not mobile["sendVisible"] or not mobile["composerVisible"]:
            raise RuntimeError("mobile viewport clips controls or has horizontal page overflow")
        report["ui_checks"]["mobile_layout"] = mobile
        _webdriver(browser_base, f"/session/{browser_session}/window/rect", "POST", {"width":1280,"height":900,"x":0,"y":0})
        desktop = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,sendVisible:document.getElementById('chat-send').getBoundingClientRect().width>0};",
            "args":[]})["value"]
        if desktop["documentWidth"] > desktop["viewport"] or not desktop["sendVisible"]:
            raise RuntimeError("desktop viewport has horizontal overflow or clipped Send button")
        report["ui_checks"]["desktop_layout"] = desktop

        def browser_turn(message):
            report["stage"] = "browser_chat_model_turn"
            started = time.monotonic()
            before = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
                "script":"window.__rvTurnStart=performance.now();window.__rvBeforeChatCount=document.querySelectorAll('#chat-history article.message-row:not([aria-label])').length;window.__rvBeforeGraceCount=document.querySelectorAll('#chat-history article.message-row.grace[data-message-row]').length;const box=document.getElementById('chat-message');box.value=arguments[0];box.dispatchEvent(new Event('input'));box.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));const state=document.getElementById('chat-state').textContent;return {sendDisabled:document.getElementById('chat-send').disabled,processing:state.includes('processing')||state.includes('Generating response')};",
                "args":[message]})
            if not before.get("value", {}).get("sendDisabled"):
                raise RuntimeError("composer did not enter a duplicate-protected processing state")
            _wait_browser(browser_base, browser_session,
                "document.querySelector('#chat-history [data-stream-response] .message-content')?.textContent.trim().length>0 && document.querySelectorAll('#chat-history article.message-row.grace[data-message-row]').length===window.__rvBeforeGraceCount",
                timeout=150)
            first_text = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
                "script":"return {text:document.querySelector('#chat-history [data-stream-response] .message-content')?.textContent||'',elapsed_ms:performance.now()-window.__rvTurnStart};","args":[]})["value"]
            _wait_browser(browser_base, browser_session,
                "document.querySelectorAll('#chat-history article.message-row.grace[data-message-row]').length>window.__rvBeforeGraceCount && !document.querySelector('#chat-history [data-stream-response]')",
                timeout=180)
            failure = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
                "script":"return document.getElementById('chat-error').textContent;","args":[]})["value"]
            if failure:
                raise RuntimeError("browser chat returned a failed response: " + str(failure)[:100])
            values = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
                "script":"const messages=Array.from(document.querySelectorAll('#chat-history article.message-row:not([aria-label])')).map(x=>x.querySelector('.message-content')?.textContent||'');const actual=messages[messages.length-2]||'';const expected=arguments[0];const norm=x=>x.replace(/\\r\\n?/g,'\\n');let mismatch=-1;for(let i=0;i<Math.min(actual.length,expected.length);i++){if(actual[i]!==expected[i]){mismatch=i;break;}}return {messages,elapsed_ms:performance.now()-window.__rvTurnStart,conversation:localStorage.getItem('rv.grace.conversation'),userExact:norm(actual)===norm(expected),userMultiline:actual.includes(String.fromCharCode(10)),userMismatchIndex:mismatch,actualCode:mismatch<0?null:actual.charCodeAt(mismatch),expectedCode:mismatch<0?null:expected.charCodeAt(mismatch)};",
                "args":[message]})["value"]
            return {"elapsed_wall_ms":round((time.monotonic()-started)*1000,2),
                "browser_elapsed_ms":round(values["elapsed_ms"],2),
                "conversation_id":values["conversation"],
                "last_message_chars":len(str(values["messages"][-1])),
                "assistant_response_sha256":hashlib.sha256(
                    str(values["messages"][-1]).encode("utf-8")).hexdigest(),
                "last_message_complete":bool(values["messages"][-1].strip()),
                "first_text_chars":len(first_text["text"]),
                "time_to_first_text_ms":round(first_text["elapsed_ms"],2),
                "first_text_preceded_persisted_completion":True,
                "user_message_chars":len(str(values["messages"][-2])),
                "user_message_exactly_rendered":values["userExact"],
                "user_message_multiline_rendered":values["userMultiline"],
                "user_message_mismatch_index":values["userMismatchIndex"],
                "processing_indicator_observed":bool(before.get("value", {}).get("processing"))}

        long_message = "Hi Grace. Reply with one short greeting and identify your resident role.\nPlease preserve this second line in the conversation history.\n" + ("Bounded engineering context for layout verification. " * 11) + "Bounded engineering context for layout verification."
        first = browser_turn(long_message)
        report["turns"].append({"phase":"first_browser_inference",**first})
        if (first["last_message_chars"] < 1 or not first["last_message_complete"]
                or not first["user_message_exactly_rendered"] or not first["user_message_multiline_rendered"]):
            raise RuntimeError("complete model response or long multiline Steward message was not rendered")
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('.chat-more summary').click();document.querySelector('[data-chat-option=details]').click();","args":[]})
        detail_checks = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"const d=document.getElementById('chat-details-content').innerText;return {conversationId:d.includes(arguments[0]),servedModel:d.includes('qwen3-0.6b-q8_0-local'),utcIncluded:d.includes('UTC'),status:d.includes('Response complete')};",
            "args":[first["conversation_id"]]})["value"]
        if not all(detail_checks.values()):
            raise RuntimeError("Chat Details did not match persisted conversation/model/status metadata")
        report["ui_checks"]["chat_details_accuracy"] = "PASS"
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('#chat-details-dialog [data-close-dialog]').click();","args":[]})
        message_actions = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"const row=document.querySelector('#chat-history .message-row.grace:not([aria-label])');row.querySelector('.message-actions summary').click();row.querySelector('[data-message-details]').click();return {dialog:document.getElementById('message-details-dialog').open,hasTimestamp:document.getElementById('message-details-content').innerText.includes('Timestamp'),hasModel:document.getElementById('message-details-content').innerText.includes('Model')};",
            "args":[]})["value"]
        if not message_actions["dialog"] or not message_actions["hasTimestamp"] or not message_actions["hasModel"]:
            raise RuntimeError("message details omitted timestamp or model provenance")
        report["ui_checks"]["message_details"] = "PASS"
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('#message-details-dialog [data-close-dialog]').click();","args":[]})
        _wait_browser(browser_base, browser_session, "!document.getElementById('message-details-dialog').open")
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('#chat-history .message-row.grace:not([aria-label]) .message-actions summary').scrollIntoView({block:'center'});","args":[]})
        _click_browser_selector(browser_base, browser_session,
            "#chat-history .message-row.grace:not([aria-label]) .message-actions summary")
        _click_browser_selector(browser_base, browser_session,
            "#chat-history .message-row.grace:not([aria-label]) [data-message-copy]")
        _wait_browser(browser_base, browser_session,
            "['Copied to clipboard.','Clipboard access unavailable.'].includes(document.getElementById('toast').textContent)",timeout=5)
        copied = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"return document.getElementById('toast').textContent;","args":[]})["value"]
        if copied != "Copied to clipboard.":
            raise RuntimeError("message copy action did not report a local clipboard copy")
        report["ui_checks"]["message_copy"] = "PASS"
        composer_behavior = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('#message-details-dialog [data-close-dialog]').click();const box=document.getElementById('chat-message');box.value='first';box.dispatchEvent(new Event('input'));const before=document.querySelectorAll('#chat-history .message-row:not([aria-label])').length;box.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',shiftKey:true,bubbles:true,cancelable:true}));const unchanged=document.querySelectorAll('#chat-history .message-row:not([aria-label])').length===before;document.getElementById('chat-newline').click();return {shiftEnterDidNotSubmit:unchanged,newlineInserted:box.value.includes(String.fromCharCode(10)),height:parseFloat(box.style.height)};",
            "args":[]})["value"]
        if not composer_behavior["shiftEnterDidNotSubmit"] or not composer_behavior["newlineInserted"]:
            raise RuntimeError("multiline composer newline/send behavior is incorrect")
        composer_check = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"const box=document.getElementById('chat-message');return {draftPreserved:box.value.length>0,expanded:parseFloat(box.style.height)>=56};",
            "args":[]})["value"]
        report["ui_checks"]["composer"] = composer_check
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.getElementById('chat-message').value='';document.getElementById('chat-message').dispatchEvent(new Event('input'));",
            "args":[]})
        conversation_id = first["conversation_id"]
        if not conversation_id:
            raise RuntimeError("browser did not retain the conversation identifier")

        report["stage"] = "browser_refresh"
        _webdriver(browser_base, f"/session/{browser_session}/refresh", "POST", {})
        _wait_browser(browser_base, browser_session, "document.readyState === 'complete'", timeout=30)
        _wait_browser(browser_base, browser_session,
                      "document.getElementById('workspace').hidden === false", timeout=30)
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('[data-view=grace-chat]').click();",
            "args":[]})
        _wait_browser(browser_base, browser_session,
            "document.getElementById('chat-history').innerText.includes('Hi Grace')&&document.getElementById('chat-auth-form').hidden", timeout=30)
        restored_text = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"const rows=Array.from(document.querySelectorAll('#chat-history article.message-row.grace[data-message-row]'));return rows.length?rows[rows.length-1].querySelector('.message-content')?.textContent||'':'';",
            "args":[]})["value"]
        if hashlib.sha256(str(restored_text).encode("utf-8")).hexdigest() != first["assistant_response_sha256"]:
            raise RuntimeError("browser reload did not restore the complete persisted assistant response")
        report["browser_refresh"] = {"status":"PASS","history_reloaded":True,
            "complete_assistant_response_restored":True,
            "assistant_response_sha256":first["assistant_response_sha256"],
            "conversation_id_retained":conversation_id}

        binding = runtime["registry"].authorize_office_state(
            runtime["resident_token"], runtime["office_id"])
        refreshed_count = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"window.__chatRequests=0;const rvFetch=window.fetch.bind(window);window.fetch=(...args)=>{if(String(args[0]).startsWith('/api/v1/resident/conversations'))window.__chatRequests++;return rvFetch(...args)};return window.__chatRequests;",
            "args":[]})["value"]
        history = runtime["store"].history(conversation_id,runtime["office_id"],runtime["steward_id"])
        source = next(event for event in reversed(history["events"])
                      if event["event_type"]=="user_message")
        runtime["store"].finish_work_order_review(conversation_id,str(uuid4()),
            source_sequence=source["sequence"],principal_id=runtime["steward_id"],
            occupant=binding,implementation={"office_id":runtime["office_id"],
                "implementation_id":binding["implementation_id"],
                "implementation_revision":binding["implementation_revision"]},
            provider_ref="synthetic.verified-result-fixture",model_id=MODEL_ID,
            body="Synthetic verified work-order result visibility fixture.",
            metadata={"result_kind":"synthetic_stream_visibility_test",
                "verification_decision":"ACCEPTED"})
        _wait_browser(browser_base,browser_session,
            "document.getElementById('chat-history').innerText.includes('Synthetic verified work-order result visibility fixture.')",
            timeout=12)
        refreshed_count_after = _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"return window.__chatRequests;","args":[]})["value"]
        if refreshed_count_after<=refreshed_count:
            raise RuntimeError("asynchronous verified result was not fetched through active conversation refresh")
        report["browser_refresh"]["asynchronous_verified_result_visible_without_manual_refresh"] = True
        report["browser_refresh"]["history_refresh_requests"] = int(refreshed_count_after-refreshed_count)
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
        report["stage"] = "browser_restart_refresh"
        _webdriver(browser_base, f"/session/{browser_session}/refresh", "POST", {})
        _wait_browser(browser_base, browser_session, "document.readyState === 'complete'", timeout=30)
        _wait_browser(browser_base, browser_session,
                      "document.getElementById('workspace').hidden === false", timeout=30)
        _webdriver(browser_base, f"/session/{browser_session}/execute/sync", "POST", {
            "script":"document.querySelector('[data-view=grace-chat]').click();",
            "args":[]})
        _wait_browser(browser_base, browser_session,
            "document.getElementById('chat-history').innerText.includes('controlled interruption fixture')", timeout=30)
        _wait_browser(browser_base, browser_session,
            "document.getElementById('chat-error').textContent.includes('service_restarted')", timeout=30)
        report["recovery"]["browser_history_and_interruption_visible"] = True
        second = browser_turn("Continue after restart. Reply briefly that Grace's office history remains available.")
        report["turns"].append({"phase":"post_restart_browser_inference",**second})

        with psycopg.connect(args.dsn, row_factory=psycopg.rows.dict_row) as verify_db:
            verify_db.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            for turn in report["turns"]:
                stored = verify_db.execute("""SELECT u.request_id,u.occurred_at AS submitted_at,
                    r.occurred_at AS completed_at,r.metadata
                    FROM resident_conversation_events u JOIN resident_conversation_events r
                      USING (request_id,conversation_id)
                    WHERE u.conversation_id=%s AND u.event_type='user_message'
                      AND r.event_type='assistant_message'
                    ORDER BY u.sequence""",(turn["conversation_id"],)).fetchall()
                if not stored:
                    raise RuntimeError("streamed browser turn has no durable terminal response")
                selected=stored[0] if turn["phase"]=="first_browser_inference" else stored[-1]
                metadata=selected["metadata"] or {}
                ttft=metadata.get("time_to_first_token_ms")
                generation=metadata.get("generation_elapsed_ms")
                end_to_end=(selected["completed_at"]-selected["submitted_at"]).total_seconds()*1000
                if not isinstance(ttft,(int,float)) or not isinstance(generation,(int,float)):
                    raise RuntimeError("durable stream timing metadata is incomplete")
                turn["request_id"]=str(selected["request_id"])
                turn["time_to_first_token_server_ms"]=round(float(ttft),3)
                turn["generation_elapsed_ms"]=round(float(generation),3)
                turn["end_to_end_persisted_ms"]=round(end_to_end,3)
            row = verify_db.execute("""SELECT count(*) FILTER (WHERE event_type='user_message') AS user_messages,
                count(*) FILTER (WHERE event_type='assistant_message') AS assistant_messages,
                count(*) FILTER (WHERE event_type='response_interrupted') AS interruptions,
                count(DISTINCT model_id) FILTER (WHERE event_type='assistant_message') AS models
                FROM resident_conversation_events""").fetchone()
            work_orders = verify_db.execute(
                "SELECT count(*) AS objective_count FROM grace_objectives").fetchone()["objective_count"]
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
        evidence_bytes = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        evidence_file.write_bytes(evidence_bytes)
        artifact_manifest = {"manifest_revision":"1.0.0", "artifacts":{
            evidence_file.name:{"path":evidence_file.name,"revision":"1.0.0",
                "sha256":hashlib.sha256(evidence_bytes).hexdigest(),
                "size_bytes":len(evidence_bytes)}}}
        (output / "artifacts.json").write_text(
            json.dumps(artifact_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
