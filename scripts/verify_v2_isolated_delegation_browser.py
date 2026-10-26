#!/usr/bin/env python3
# Riverview~ Controlled Script
# File: scripts/verify_v2_isolated_delegation_browser.py
# Component: RIVERVIEW-V2-DELEGATION-ACCEPTANCE
# Revision: 1.0.1
# Purpose: Verify complete delegation lifecycle using the reserved persona and an isolated canonical authority schema.
# Execution Model: Authenticated headless Chrome and ephemeral PostgreSQL-backed V2 API.
# Observability: Safe per-check JSON, audit assertions, and screenshot evidence.
# Dependencies: PostgreSQL 16, Psycopg 3, Python, OpenSSL, ChromeDriver.
# Authority: Isolated steward:test grants and disposable service principals only; never production identity or grants.
# Changed: 2026-10-26 UTC | RV-ISSUE268-DELEGATION-CANCEL-ACCEPTANCE | Test registration, request/hash approval, policy enforcement, revocation and errors through V2.
# Changed: 2026-10-26 UTC | RV-ISSUE268-SYSTEMD-CHROME-ACCEPTANCE | Prefer the installed Chrome/ChromeDriver pair and fail clearly if the driver does not become ready.
# Contracts: Existing canonical AuthorityRegistry and V2 Delegation Approvals API.
# Tests: scripts/verify_v2_isolated_delegation_browser.py and tests/test_delegation_routes.py.
# History: Git and .riverview-backups/manifest.jsonl.
"""Authenticated V2 delegation lifecycle acceptance against a disposable canonical registry.

The reserved acceptance Steward credentials arrive on stdin from the existing runner,
are hashed into a temporary account schema, and are never written or printed in cleartext.
All authority data and the one-time service credential live in temporary fixtures.
"""
from __future__ import annotations
import hashlib, http.cookies, json, os, secrets, shutil, socket, ssl, subprocess, sys, tempfile, threading, time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(os.environ.get("RIVERVIEW_SOURCE_ROOT",Path(__file__).resolve().parents[1])).resolve()
ASSETS = Path(os.environ.get("RIVERVIEW_V2_ASSET_ROOT",ROOT/"website/v2/deployed")).resolve()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return sock.getsockname()[1]


def run():
    payload=json.load(sys.stdin)
    email, password=payload.get("email"), payload.get("password")
    dsn=os.environ.get("RIVERVIEW_TEST_PG_DSN")
    if not dsn and all(os.environ.get(key) for key in ("PGHOST","PGPORT","PGDATABASE","PGUSER")):
        from psycopg.conninfo import make_conninfo
        dsn=make_conninfo(host=os.environ["PGHOST"],port=os.environ["PGPORT"],
            dbname=os.environ["PGDATABASE"],user=os.environ["PGUSER"])
    if not dsn or not isinstance(email,str) or not isinstance(password,str):
        raise RuntimeError("isolated_test_database_or_reserved_persona_unavailable")
    import psycopg
    from psycopg import sql
    from riverview_core.postgres_migrations import apply_migrations
    from riverview_core.account_auth import AccountAuthService, DisabledEmailTransport
    from riverview_core.institutional_authority import AuthorityRegistry
    from riverview_core.institutional_authority.comms5_adapter import Comms5DelegationAuthorityAdapter
    from riverview_core.institutional_authority.service_principal_credentials import ProtectedChatGPTCredentialStore
    from riverview_core.status_dashboard.delegation_routes import dispatch

    auth_schema="rvacct_"+secrets.token_hex(8); authority_schema="rvauth_"+secrets.token_hex(8)
    with psycopg.connect(dsn,autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(auth_schema)))
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(authority_schema)))
    account_migrations=ROOT/"src/riverview_core/account_auth/migrations"
    authority_migrations=ROOT/"src/riverview_core/institutional_authority/migrations"
    registry=None; server=None; driver=None; session=None
    temp=tempfile.TemporaryDirectory(prefix="rv-delegation-fixture-"); temp_path=Path(temp.name); os.chmod(temp_path,0o700)
    results=[]
    try:
        apply_migrations(dsn,schema=auth_schema,migrations_dir=account_migrations)
        apply_migrations(dsn,schema=authority_schema,migrations_dir=authority_migrations)
        registry=AuthorityRegistry(dsn,schema=authority_schema)
        steward_token=secrets.token_urlsafe(40)
        with psycopg.connect(dsn,autocommit=True) as conn:
            conn.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES ('steward:test','steward')").format(sql.Identifier(authority_schema)))
            conn.execute(sql.SQL("INSERT INTO {}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,'steward:test',%s)").format(sql.Identifier(authority_schema)),(secrets.token_hex(16),hashlib.sha256(steward_token.encode()).digest()))
            for action in ("authority.grant","identity.manage"):
                conn.execute(sql.SQL("INSERT INTO {}.authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) VALUES (%s,'steward:test',%s,'institution','steward:test','rv.policy:acceptance.v1')").format(sql.Identifier(authority_schema)),("test:"+action,action))
            conn.execute(sql.SQL("INSERT INTO {}.institutional_authority_events(event_id,event_type,actor_id,subject_id) VALUES (%s,'steward_bootstrapped','steward:test','steward:test')").format(sql.Identifier(authority_schema)),(secrets.token_hex(16),))
        account=AccountAuthService(lambda:psycopg.connect(dsn),DisabledEmailTransport(),schema=auth_schema,public_origin="https://127.0.0.1")
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("INSERT INTO {}.accounts(email,email_verified_at,created_at,password_hash,grant_type,authority_principal_id) VALUES (%s,clock_timestamp(),clock_timestamp(),%s,'permanent','steward:test') RETURNING account_id").format(sql.Identifier(auth_schema)),(email,AccountAuthService._password_hash(password)))
                account_id=cur.fetchone()[0]
                cur.execute(sql.SQL("INSERT INTO {}.account_roles(account_id,role) VALUES (%s,'steward')").format(sql.Identifier(auth_schema)),(account_id,))
                cur.execute(sql.SQL("INSERT INTO {}.account_audit(event_type,account_id,subject_email) VALUES ('website_test_persona_seeded',%s,%s)").format(sql.Identifier(auth_schema)),(account_id,email))
        store=ProtectedChatGPTCredentialStore(temp_path/"service-chatgpt.credential")
        adapter=object.__new__(Comms5DelegationAuthorityAdapter)
        adapter._registry=registry; adapter._steward_token=steward_token
        adapter._steward_principal_id="steward:test"; adapter._chatgpt_credential_store=store
        # Fail before browser startup if this disposable canonical context cannot
        # authenticate the exact isolated Steward grants.
        if adapter._authenticated_steward() != "steward:test":raise RuntimeError("isolated_steward_adapter_identity_mismatch")
        for action in ("authority.grant","identity.manage"):
            if registry.authorize(steward_token,action,"institution").get("principal_id") != "steward:test":
                raise RuntimeError("isolated_steward_institution_authority_missing")
        from riverview_core.status_dashboard.delegation_projection import list_grants
        try:list_grants(adapter,state="active",limit=5)
        except Exception as exc:raise RuntimeError("isolated_grant_projection_failed:"+str(exc)) from None
        class PermissionStore:
            def list_profiles(self,principal):
                names=("read","start","stop","switch")
                return {"capabilities":[{"capability_id":"hardware.gpu.workload."+n,"authority_action":"hardware.gpu.workload."+n,"enabled":True,"registration_blocker":None,"description":"Isolated registered "+n} for n in names]}
        class Telemetry:
            def read(self): return {"hosts":[{"host_id":"octominer1","display_name":"OCTOMINER1 isolated fixture","identity_state":"verified"}]}
            def workload_controller_registrations(self): return {"octominer1":{"services":[{"service_id":"vision-fixture","display_name":"Vision fixture"}],"capabilities":[{"capability_id":"hardware.gpu.workload."+n} for n in ("read","start","stop","switch")]}}
        class Ops: SUPPORTED={"comms5_submit_direct_engineering_task"}; delegation_grant_requests=adapter
        class State: authority_available=True; last_api=None; api_history=[]
        state=State()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def send_json(self,code,value,headers=()):
                if self.path.startswith("/api/v1/steward/delegation-") or self.path.startswith("/api/v1/steward/service-principals/"):
                    state.last_api={"path":urlsplit(self.path).path,"status":code,"error":value.get("error") if isinstance(value,dict) else None,
                                    "status_value":value.get("status") if isinstance(value,dict) else None}
                    state.api_history.append(state.last_api)
                data=json.dumps(value,separators=(",",":")).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Cache-Control","no-store")
                for h,v in headers:self.send_header(h,v)
                self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
            def do_GET(self): self.route()
            def do_POST(self): self.route()
            def do_PUT(self): self.route()
            def route(self):
                path=urlsplit(self.path).path
                if path=="/v2/" or path=="/v2":
                    data=(ASSETS/"index.html").read_bytes();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);return
                if path.startswith("/v2/assets/"):
                    file=(ASSETS/path.removeprefix("/v2/")).resolve();base=ASSETS
                    if base not in file.parents or not file.is_file():self.send_error(404);return
                    typ="text/javascript" if file.suffix==".js" else "text/css" if file.suffix==".css" else "application/octet-stream";data=file.read_bytes();self.send_response(200);self.send_header("Content-Type",typ);self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);return
                if path=="/api/v1/auth/session" and self.command=="POST":
                    data=self.body();
                    try:s=account.authenticate_password(data.get("email"),data.get("password"),source_key="isolated-acceptance")
                    except Exception:self.send_json(401,{"error":"login_denied"});return
                    ident={"account_id":s.account_id,"email":s.email,"roles":s.roles,
                           "authority_principal_id":"steward:test"}
                    self.send_json(200,{"status":"authenticated","identity":ident},[("Set-Cookie",f"rv_account_session={s.session_token}; Path=/api/v1; Secure; HttpOnly; SameSite=Lax"),("Set-Cookie",f"rv_account_csrf={s.csrf_token}; Path=/; Secure; SameSite=Strict")]);return
                if path.startswith("/api/v1/"):
                    cookie=http.cookies.SimpleCookie();cookie.load(self.headers.get("Cookie",""));session_cookie=cookie.get("rv_account_session");csrf_cookie=cookie.get("rv_account_csrf")
                    token=session_cookie.value if session_cookie else ""
                    if path=="/api/v1/auth/session" and self.command=="GET":
                        ident=account.authenticate(token,csrf_token=csrf_cookie.value if csrf_cookie else None)
                        if not ident:self.send_json(401,{"error":"authentication_required"});return
                        self.send_json(200,{"identity":{"account_id":ident["account_id"],"email":ident["email"],"roles":ident["roles"]}});return
                    if path=="/api/v1/auth/session" and self.command=="DELETE":
                        if not account.authenticate(token,csrf_token=self.headers.get("X-Riverview-CSRF"),state_changing=True):self.send_json(401,{"error":"authentication_required"});return
                        account.logout(token);self.send_json(200,{"status":"logged_out"});return
                    if path=="/api/v1/resident/conversation-session" and self.command=="POST":
                        self.send_json(403,{"error":"resident_conversation_not_authorized"});return
                    ident=account.authenticate(token,csrf_token=self.headers.get("X-Riverview-CSRF") or (csrf_cookie.value if csrf_cookie else None),state_changing=self.command not in {"GET","HEAD"})
                    if not ident:self.send_json(401,{"error":"authentication_required"});return
                    data=self.body()
                    shim=SimpleNamespace(command=self.command,_account_identity=ident,_account_cookie_authenticated=True,server=SimpleNamespace(_comms5_operations=Ops() if state.authority_available else None,_permission_store=PermissionStore(),_resource_telemetry=Telemetry()))
                    shim._json=lambda code,value,request_id:self.send_json(code,value)
                    shim._error=lambda code,message,request_id:self.send_json(code,{"error":message})
                    shim._json_body=lambda maximum:data
                    try:
                        handled=dispatch(shim,urlsplit(self.path),"acceptance")
                        if handled:return
                    except Exception:self.send_json(503,{"error":"isolated_route_failed"});return
                    if path=="/api/v1/resident/conversations" and self.command=="GET":self.send_json(200,{"status":"available","items":[]});return
                    if path=="/api/v1/objectives" and self.command=="GET":self.send_json(200,{"status":"available","observed_at":None,"items":[]});return
                    if path=="/api/v1/assignments" and self.command=="GET":self.send_json(200,{"status":"available","observed_at":None,"items":[]});return
                    if path=="/api/v1/notification-settings" and self.command=="GET":self.send_json(200,{"schema_version":"rv.notification_settings.v1","status":"available","level":"all","quiet_hours":{"enabled":False,"start":"22:00","end":"07:00","timezone":"UTC"}});return
                    self.send_json(404,{"error":"isolated_fixture_route_not_found"});return
                self.send_error(404)
            def body(self):
                try:return json.loads(self.rfile.read(min(int(self.headers.get("Content-Length","0")),16384)) or b"{}")
                except Exception:return {}
        from types import SimpleNamespace
        # The canonical registry object deliberately owns one psycopg connection.
        # Serialize the fixture server requests so Promise.all fetches cannot
        # interleave transactions through that single connection.
        port=free_port();server=HTTPServer(("127.0.0.1",port),Handler)
        key,cert=temp_path/"key.pem",temp_path/"cert.pem"
        subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-keyout",str(key),"-out",str(cert),"-days","1","-subj","/CN=localhost","-addext","subjectAltName=DNS:localhost,IP:127.0.0.1"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert,key);server.socket=tls.wrap_socket(server.socket,server_side=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        driver_port=free_port();chrome_driver=shutil.which("chromedriver");chrome=shutil.which("google-chrome") or shutil.which("google-chrome-stable")
        gecko=shutil.which("geckodriver") or ("/snap/bin/geckodriver" if Path("/snap/bin/geckodriver").exists() else None)
        firefox=shutil.which("firefox") or ("/snap/bin/firefox" if Path("/snap/bin/firefox").exists() else None)
        if chrome_driver and chrome:
            driver_command=[chrome_driver,f"--port={driver_port}","--allowed-ips=127.0.0.1"]
            browser_name="chrome"
            browser_options={"goog:chromeOptions":{"binary":chrome,"args":["--headless=new","--disable-dev-shm-usage"]}}
        elif gecko and firefox:
            driver_command=[gecko,"--host","127.0.0.1","--port",str(driver_port)]
            browser_name="firefox"
            browser_options={"moz:firefoxOptions":{"args":["-headless"]}}
        else:raise RuntimeError("existing_acceptance_browser_unavailable")
        driver=subprocess.Popen(driver_command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        sid=None
        def wd(method,path,value=None):
            from urllib.request import Request,urlopen
            from urllib.error import HTTPError
            data=json.dumps(value).encode() if value is not None else None;req=Request(f"http://127.0.0.1:{driver_port}{path}",data=data,method=method,headers={"Content-Type":"application/json"} if data is not None else {})
            try:
                with urlopen(req,timeout=45) as res:return json.loads(res.read())
            except HTTPError as exc:raise RuntimeError(f"browser_protocol_http_{exc.code}")
        def js(source,*args):return wd("POST",f"/session/{sid}/execute/sync",{"script":source,"args":list(args)})["value"]
        try:
            driver_ready=False
            for _ in range(100):
                try:wd("GET","/status");driver_ready=True;break
                except Exception:
                    if driver.poll() is not None:break
                    time.sleep(.1)
            if not driver_ready:raise RuntimeError("browser_driver_start_failed")
            caps={"capabilities":{"alwaysMatch":{"browserName":browser_name,"acceptInsecureCerts":True,**browser_options}}}
            sid=wd("POST","/session",caps)["value"]["sessionId"]
            wd("POST",f"/session/{sid}/url",{"url":f"https://127.0.0.1:{port}/v2/"})
            time.sleep(.4)
            # Existing account-auth password login uses the reserved test persona.
            # Credentials are only WebDriver arguments and are never printed or stored.
            wd("POST",f"/session/{sid}/execute/sync",{"script":"document.querySelector('#grace-email').value=arguments[0];document.querySelector('#grace-password').value=arguments[1];document.querySelector('#grace-login-form').requestSubmit();return true","args":[email,password]})
            authenticated=False
            for _ in range(60):
                authenticated=js("return fetch('/api/v1/auth/session',{cache:'no-store'}).then(r=>r.status===200)")
                if authenticated:break
                time.sleep(.1)
            if not authenticated:raise RuntimeError("reserved_test_steward_login_failed")
            js("window.confirm=()=>true;window.prompt=()=>\"isolated acceptance approval\";document.querySelector('[data-view=resident-permissions]').click()")
            time.sleep(.5)
            wait="""return document.querySelector('#delegation-state')?.textContent.includes('authorization options loaded')"""
            for _ in range(50):
                if js(wait):break
                time.sleep(.1)
            page=js("return {panel:!document.querySelector('#delegation-approvals').hidden,requester:document.querySelector('#delegation-request-requester').textContent,type:document.querySelector('#delegation-request-type').options.length}")
            if not page["panel"] or page["requester"]!="steward:test":
                diag=js("return {state:document.querySelector('#delegation-state')?.textContent,request:document.querySelector('#delegation-request-result')?.textContent,requester:document.querySelector('#delegation-request-requester')?.textContent,options:document.querySelector('#delegation-request-type')?.textContent,identity:document.querySelector('#grace-chat-state')?.textContent}")
                diag["api"]=state.last_api
                diag["api_history"]=state.api_history[-12:]
                raise RuntimeError("isolated_delegation_options_not_loaded:"+json.dumps(diag)[:900])
            results.append({"check":"delegation_isolated_authenticated_options","status":"PASS","canonical_test_principal":page["requester"]})
            discovery=js("const type=document.querySelector('#delegation-request-type');type.value='gpu_host';type.dispatchEvent(new Event('change',{bubbles:true}));const host=document.querySelector('#delegation-request-host');host.value='octominer1';host.dispatchEvent(new Event('change',{bubbles:true}));return {types:[...type.options].map(x=>x.value),hosts:[...host.options].map(x=>x.value),capabilities:[...document.querySelector('#delegation-request-capability').options].map(x=>x.value)}")
            if ("gpu_host" not in discovery["types"] or "octominer1" not in discovery["hosts"] or
                    not any(item.startswith("hardware.gpu.workload.") for item in discovery["capabilities"])):
                raise RuntimeError("registered_host_capability_discovery_missing")
            js("const type=document.querySelector('#delegation-request-type');type.value='';type.dispatchEvent(new Event('change',{bubbles:true}))")
            results.append({"check":"delegation_registered_hosts_and_capabilities_loaded","status":"PASS"})
            # The service is registered only by explicit in-browser confirmation.
            js("document.querySelector('#chatgpt-principal-register').click()")
            for _ in range(50):
                state_text=js("return document.querySelector('#chatgpt-principal-registration-state').textContent")
                if "was not returned" in state_text:break
                time.sleep(.1)
            if not store.path.is_file() or (store.path.stat().st_mode & 0o077):raise RuntimeError("isolated_one_time_credential_not_protected")
            # Explicitly select the registered ChatGPT operation and submit through V2.
            js("const s=document.querySelector('#delegation-request-type');s.value='comms5_codex';s.dispatchEvent(new Event('change',{bubbles:true}));document.querySelector('#delegation-request-purpose').value='Isolated UI delegation lifecycle acceptance';document.querySelector('#delegation-request-form').requestSubmit()")
            policy_note=js("return document.querySelector('#delegation-request-type-note').textContent")
            if "Separate objective and assignment authorization remains required" not in policy_note:
                raise RuntimeError("codex_separate_objective_assignment_authority_not_disclosed")
            for _ in range(60):
                text=js("return document.querySelector('#delegation-request-result').textContent")
                if "Pending request recorded" in text:break
                time.sleep(.1)
            if "Pending request recorded" not in text:
                diag=js("return {result:document.querySelector('#delegation-request-result')?.textContent,state:document.querySelector('#delegation-state')?.textContent,type:document.querySelector('#delegation-request-type')?.value,submitDisabled:document.querySelector('#delegation-request-submit')?.disabled,expiryDisabled:document.querySelector('#delegation-request-expiry')?.disabled}")
                diag["api"]=state.last_api
                raise RuntimeError("isolated_delegation_request_not_submitted:"+json.dumps(diag)[:180])
            hash_data=None
            for _ in range(60):
                hash_data=js("const x=document.querySelector('[data-delegation-decision=approve]');return x?{id:x.dataset.requestId,hash:x.dataset.requestHash}:null")
                if hash_data:break
                time.sleep(.1)
            if not hash_data:
                # The submit response is rendered before the list refresh completes.
                js("document.querySelector('#delegation-refresh').click()")
                for _ in range(60):
                    hash_data=js("const x=document.querySelector('[data-delegation-decision=approve]');return x?{id:x.dataset.requestId,hash:x.dataset.requestHash}:null")
                    if hash_data:break
                    time.sleep(.1)
            if not hash_data or len(hash_data["hash"])!=64:raise RuntimeError("isolated_request_hash_missing")
            js("document.querySelector('[data-delegation-decision=approve]').click()")
            for _ in range(60):
                status=js("return document.querySelector('#delegation-state').textContent")
                if "approved recorded" in status.lower() or "approved" in status.lower():break
                time.sleep(.1)
            request=registry.get_status(requester_id="steward:test",request_id=hash_data["id"])
            if request["status"]!="approved" or request["request_sha256"]!=hash_data["hash"]:raise RuntimeError("isolated_hash_bound_approval_failed")
            grant=registry.get_status(requester_id="steward:test",grant_id=request["grant_id"])
            delta=datetime.fromisoformat(grant["valid_until"])-datetime.fromisoformat(grant["approved_at"])
            if grant["duration_spec"]!={"unit":"hours","value":24} or abs(delta.total_seconds()-86400)>2 or grant["max_uses"] is not None:raise RuntimeError("codex_grant_policy_mismatch")
            service_credential=store.path.read_text().strip()
            registry.authorize_delegated_principal_operation("service:chatgpt","comms5.operations.non_destructive.v1","project:Riverview","policy:delegation.v1","acceptance:allowed")
            from riverview_core.institutional_authority.registry import AuthorityDenied
            try:registry.authorize_delegated_principal_operation("service:chatgpt","comms5.operations.non_destructive.v1","host:octominer1","policy:delegation.v1","acceptance:wrong-scope")
            except AuthorityDenied:pass
            else:raise RuntimeError("unauthorized_scope_was_allowed")
            results.extend([{"check":"delegation_ui_register_and_protect_credential","status":"PASS","credential_returned_to_browser":False},{"check":"delegation_ui_request_hash_approval_and_24h_policy","status":"PASS","request_id":request["request_id"],"grant_id":grant["grant_id"],"usage":"unlimited"},{"check":"delegation_exact_operation_allowed_and_wrong_scope_denied","status":"PASS"}])
            # Disposable one-use grant verifies backend usage limits, then revoke and deny.
            finite_token=registry.create_principal(steward_token,"service:finite-test","service")
            pending=registry.request_grant(requester_id="steward:test",principal_id="service:finite-test",action="hardware.gpu.workload.start",scope_ref="host:octominer1",policy_ref="policy:delegation.v1",request_ref="isolated one-use acceptance",max_uses=1,valid_until=None,idempotency_key="acceptance-finite-0001")
            dec=registry.decide_request(steward_token=steward_token,request_id=pending["request_id"],decision="approve",expected_request_sha256=pending["request_sha256"],idempotency_key="acceptance-finite-approve-0001",approval_ref="isolated test Steward approval")
            reservation=registry.reserve_delegated_grant(finite_token,dec["grant_id"],"hardware.gpu.workload.start","host:octominer1","acceptance:one",idempotency_key="acceptance-use-one-0001")
            registry.consume_delegated_grant(finite_token,reservation["reservation_id"],"acceptance:result")
            try:registry.reserve_delegated_grant(finite_token,dec["grant_id"],"hardware.gpu.workload.start","host:octominer1","acceptance:two",idempotency_key="acceptance-use-two-0001")
            except AuthorityDenied:pass
            else:raise RuntimeError("use_limit_not_enforced")
            registry.revoke_grant(steward_token,dec["grant_id"],reason_code="acceptance_complete")
            results.append({"check":"delegation_use_count_enforced_and_revocation_denied","status":"PASS"})
            # UI revocation uses the canonical POST; refresh and verify the revoked record.
            js("document.querySelector('#delegation-grant-filter').value='all';document.querySelector('#delegation-grant-filter').dispatchEvent(new Event('change',{bubbles:true}))")
            browser_grant_id=request["grant_id"]
            revoke_clicked=False
            for _ in range(60):
                revoke_clicked=js("const b=[...document.querySelectorAll('[data-delegation-revoke]')].find(x=>x.dataset.delegationRevoke===arguments[0]);return !!b", browser_grant_id)
                if revoke_clicked:break
                time.sleep(.1)
            if not revoke_clicked: raise RuntimeError("approved_grant_revoke_control_missing")
            js("const b=[...document.querySelectorAll('[data-delegation-revoke]')].find(x=>x.dataset.delegationRevoke===arguments[0]);b.click()", browser_grant_id)
            revoked_in_ui=False
            for _ in range(60):
                revoked_in_ui=js("return [...document.querySelectorAll('.delegation-record')].some(a=>a.textContent.includes(arguments[0])&&a.querySelector('[data-state]')?.dataset.state==='revoked')",browser_grant_id)
                if revoked_in_ui:break
                time.sleep(.1)
            if not revoked_in_ui:raise RuntimeError("ui_revocation_not_rendered")
            grant=registry.get_status(requester_id="steward:test",grant_id=request["grant_id"])
            if grant["status"]!="revoked":raise RuntimeError("ui_revocation_not_durable")
            try:registry.authorize_delegated_principal_operation("service:chatgpt","comms5.operations.non_destructive.v1","project:Riverview","policy:delegation.v1","acceptance:after-revoke")
            except AuthorityDenied:pass
            else:raise RuntimeError("revoked_codex_operation_still_allowed")
            results.append({"check":"delegation_ui_revocation_and_subsequent_denial","status":"PASS"})
            # Expiration is exercised in the isolated canonical registry (no waiting or live grant).
            exp_token=registry.create_principal(steward_token,"service:expiry-test","service")
            exp=registry.request_grant(requester_id="steward:test",principal_id="service:expiry-test",action="hardware.gpu.workload.read",scope_ref="host:octominer1",policy_ref="policy:delegation.v1",request_ref="isolated expiry acceptance",max_uses=None,duration_spec={"unit":"minutes","value":1},idempotency_key="acceptance-expiry-0001")
            expdec=registry.decide_request(steward_token=steward_token,request_id=exp["request_id"],decision="approve",expected_request_sha256=exp["request_sha256"],idempotency_key="acceptance-expiry-approve-0001",approval_ref="isolated expiry test")
            with registry.db.transaction(), registry.db.cursor() as cur:
                registry._path(cur);cur.execute("UPDATE authority_grants SET valid_from=clock_timestamp()-interval '2 minutes',valid_until=clock_timestamp()-interval '1 minute' WHERE grant_id=%s",(expdec["grant_id"],))
            try:registry.authorize_delegated_principal_operation("service:expiry-test","hardware.gpu.workload.read","host:octominer1","policy:delegation.v1","acceptance:expired")
            except AuthorityDenied:pass
            else:raise RuntimeError("grant_expiration_not_enforced")
            results.append({"check":"delegation_expiration_enforced","status":"PASS"})
            # Reopen the same page, confirm durable request history; show unavailable authority clearly.
            wd("POST",f"/session/{sid}/url",{"url":f"https://127.0.0.1:{port}/v2/"});time.sleep(.25)
            js("document.querySelector('[data-view=resident-permissions]').click()")
            for _ in range(40):
                if js("return document.querySelector('#delegation-approvals')&&!document.querySelector('#delegation-approvals').hidden"):break
                time.sleep(.1)
            # Navigation triggers its own async refresh. Wait until that read
            # settles before injecting the isolated service failure, otherwise
            # clicking Refresh can be ignored by the UI's in-flight guard.
            for _ in range(80):
                state_text=js("return document.querySelector('#delegation-state').textContent")
                if ("Reading the canonical delegation registry" not in state_text and
                        state_text != "Delegation requests have not been loaded."):break
                time.sleep(.1)
            if state_text == "Delegation requests have not been loaded." or "Reading the canonical delegation registry" in state_text:
                raise RuntimeError("delegation_initial_refresh_did_not_settle")
            failure_request_start=len(state.api_history)
            state.authority_available=False
            js("document.querySelector('#delegation-refresh').click()")
            err=""
            for _ in range(80):
                err=js("return document.querySelector('#delegation-state').textContent")
                recent=state.api_history[failure_request_start:]
                if (len(recent)>=3 and all(item["status"]==503 for item in recent[-3:]) and
                        "requests unavailable" in err.lower() and "options unavailable" in err.lower()):break
                time.sleep(.1)
            if "requests unavailable" not in err.lower() or "options unavailable" not in err.lower():
                recent=state.api_history[failure_request_start:]
                raise RuntimeError("delegation_service_failure_not_shown:"+
                    json.dumps({"status":err[:240],"api_statuses":[item["status"] for item in recent[-3:]]}))
            state.authority_available=True
            results.append({"check":"delegation_refresh_and_service_error_handling","status":"PASS"})
            results.append({"check":"delegation_resident_account_binding","status":"PASS","principal":"steward:test","production_identity_used":False})
            evidence_dir=Path(os.environ.get("RIVERVIEW_ACCEPTANCE_REPORT_DIR",temp_path))
            evidence_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
            screenshot=evidence_dir/"delegation-isolated-acceptance.png"
            js("document.querySelector('#delegation-approvals').scrollIntoView({block:'start'})")
            time.sleep(.1)
            image=wd("GET",f"/session/{sid}/screenshot")["value"]
            import base64
            screenshot.write_bytes(base64.b64decode(image));os.chmod(screenshot,0o600)
            return {"overall":"PASS" if all(x["status"]=="PASS" for x in results) else "FAIL","checks":results,"pass_count":sum(x["status"]=="PASS" for x in results),"screenshot":str(screenshot)}
        finally:
            if sid:
                try:wd("DELETE",f"/session/{sid}")
                except Exception:pass
            driver.terminate()
            try:driver.wait(timeout=4)
            except subprocess.TimeoutExpired:driver.kill()
            server.shutdown();server.server_close();thread.join(timeout=2)
    finally:
        if registry:registry.close()
        with psycopg.connect(dsn,autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(auth_schema)))
            conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(authority_schema)))
        temp.cleanup()

if __name__=="__main__":
    try: print(json.dumps(run(),sort_keys=True))
    except Exception as exc:
        import traceback
        print(json.dumps({"overall":"FAIL","reason":type(exc).__name__+":"+str(exc)[:1000],"trace":traceback.format_exc(limit=8)[-1800:]}));raise SystemExit(1)
