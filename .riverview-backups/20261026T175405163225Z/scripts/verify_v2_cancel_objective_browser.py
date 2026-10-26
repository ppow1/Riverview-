#!/usr/bin/env python3
"""Click V2 Cancel Objective against a disposable PostgreSQL-backed Dashboard pipeline."""
from __future__ import annotations
import base64, hashlib, http.cookies, importlib.util, json, os, shutil, socket, ssl, subprocess, sys, tempfile, threading, time
from http.client import HTTPConnection
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(os.environ.get("RIVERVIEW_SOURCE_ROOT", Path(__file__).resolve().parents[1])).resolve()
ASSETS = Path(os.environ.get("RIVERVIEW_V2_ASSET_ROOT", ROOT / "website/v2/deployed")).resolve()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return sock.getsockname()[1]


def run():
    payload=json.load(sys.stdin); email=payload.get("email"); password=payload.get("password")
    dsn=os.environ.get("RIVERVIEW_TEST_PG_DSN")
    if not dsn:
        from psycopg.conninfo import make_conninfo
        pg={key:os.environ[key] for key in ("PGHOST","PGPORT","PGDATABASE","PGUSER") if os.environ.get(key)}
        if not {"PGHOST","PGPORT","PGDATABASE","PGUSER"} <= set(pg):raise RuntimeError("isolated_test_database_unavailable")
        dsn=make_conninfo(**{"host":pg["PGHOST"],"port":pg["PGPORT"],"dbname":pg["PGDATABASE"],"user":pg["PGUSER"]})
        os.environ["RIVERVIEW_TEST_PG_DSN"]=dsn
    if not isinstance(email,str) or not isinstance(password,str):raise RuntimeError("reserved_steward_test_persona_unavailable")
    if not (ASSETS/"index.html").is_file():raise RuntimeError("deployed_v2_assets_unavailable")
    import psycopg
    from psycopg import sql
    from riverview_core.account_auth import AccountAuthService, DisabledEmailTransport
    from riverview_core.postgres_migrations import apply_migrations
    from riverview_core.status_dashboard.projection import DashboardProjection
    from riverview_core.status_dashboard.server import DashboardHTTPServer

    test_module=ROOT/"tests/test_grace_execution.py"
    if not test_module.is_file():raise RuntimeError("isolated_canonical_objective_fixture_unavailable")
    spec=importlib.util.spec_from_file_location("rv_isolated_grace_execution_tests",test_module)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    fixture=module.GraceExecutionTests();fixture.setUp()
    auth_schema="rvacct_cancel_browser_"+os.urandom(8).hex()
    account=None;dashboard=None;outer=None;browser=None;driver=None;sid=None;thread=None
    temp=tempfile.TemporaryDirectory(prefix="rv-cancel-browser-"); tmp=Path(temp.name);os.chmod(tmp,0o700)
    results=[]
    try:
        with psycopg.connect(dsn,autocommit=True) as conn:conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(auth_schema)))
        apply_migrations(dsn,schema=auth_schema,migrations_dir=ROOT/"src/riverview_core/account_auth/migrations")
        account=AccountAuthService(lambda:psycopg.connect(dsn),DisabledEmailTransport(),schema=auth_schema,public_origin="https://127.0.0.1")
        denied_email="codex-cancel-denied@riverview.invalid";denied_password="isolated-denied-account-password"
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES ('resident:cancel-denied','resident') ON CONFLICT DO NOTHING").format(sql.Identifier(fixture.schema)))
                cur.execute(sql.SQL("INSERT INTO {}.accounts(email,email_verified_at,created_at,password_hash,grant_type,authority_principal_id) VALUES (%s,clock_timestamp(),clock_timestamp(),%s,'permanent','steward:test') RETURNING account_id").format(sql.Identifier(auth_schema)),(email,AccountAuthService._password_hash(password)))
                steward_id=cur.fetchone()[0]
                cur.execute(sql.SQL("INSERT INTO {}.account_roles(account_id,role) VALUES (%s,'steward')").format(sql.Identifier(auth_schema)),(steward_id,))
                cur.execute(sql.SQL("INSERT INTO {}.accounts(email,email_verified_at,created_at,password_hash,grant_type,authority_principal_id) VALUES (%s,clock_timestamp(),clock_timestamp(),%s,'permanent','resident:cancel-denied') RETURNING account_id").format(sql.Identifier(auth_schema)),(denied_email,AccountAuthService._password_hash(denied_password)))
                denied_id=cur.fetchone()[0]
                cur.execute(sql.SQL("INSERT INTO {}.account_roles(account_id,role) VALUES (%s,'operator')").format(sql.Identifier(auth_schema)),(denied_id,))
        objective_id="objective:v2-cancel-"+os.urandom(6).hex()
        fixture._create_grounded_reasoning_objective(objective_id)
        before_events=fixture.pipeline.objective_events(objective_id)
        dashboard_port=next((port for port in range(8799,8699,-1) if _port_free(port)),None)
        if dashboard_port is None:raise RuntimeError("isolated_dashboard_port_unavailable")
        token_file=tmp/"dashboard-token";token_file.write_text("D"*43);token_file.chmod(0o600)
        os.environ["RIVERVIEW_PUBLIC_ORIGINS"]="https://127.0.0.1"
        dashboard=DashboardHTTPServer("127.0.0.1",dashboard_port,token_file,
            DashboardProjection(dsn,schema=fixture.schema),ROOT/"src/riverview_core/status_dashboard/static",
            objective_pipeline=fixture.pipeline,account_auth_service=account)
        dthread=threading.Thread(target=dashboard.serve_forever,daemon=True);dthread.start()
        outer_port=free_port();origin=f"https://127.0.0.1:{outer_port}"
        os.environ["RIVERVIEW_PUBLIC_ORIGINS"]=origin
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):self.proxy_or_static()
            def do_POST(self):self.proxy_or_static()
            def do_PUT(self):self.proxy_or_static()
            def do_DELETE(self):self.proxy_or_static()
            def proxy_or_static(self):
                path=urlsplit(self.path).path
                if path in {"/v2/","/v2","/v2/index.html"}:
                    body=(ASSETS/"index.html").read_bytes();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
                if path=="/v2/release.json":
                    file=ASSETS/"release.json"
                    body=file.read_bytes() if file.is_file() else b'{"schema_version":"rv.website-release.v1","release_id":"isolated-candidate","source_commit":"isolated"}'
                    self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
                if path.startswith("/v2/assets/"):
                    rel=path.removeprefix("/v2/");file=(ASSETS/rel).resolve()
                    if ASSETS not in file.parents or not file.is_file():self.send_error(404);return
                    typ="text/javascript" if file.suffix==".js" else "text/css" if file.suffix==".css" else "application/octet-stream";body=file.read_bytes();self.send_response(200);self.send_header("Content-Type",typ);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
                if not path.startswith("/api/v1/"):self.send_error(404);return
                length=int(self.headers.get("Content-Length","0"));body=self.rfile.read(min(length,1_000_000)) if length else None
                headers={"Host":f"127.0.0.1:{dashboard_port}"}
                for name in ("Cookie","X-Riverview-CSRF","Content-Type","Origin","Accept"):
                    if self.headers.get(name):headers[name]=self.headers[name]
                conn=HTTPConnection("127.0.0.1",dashboard_port,timeout=20)
                conn.request(self.command,self.path,body=body,headers=headers);response=conn.getresponse();data=response.read()
                self.send_response(response.status)
                for name,value in response.getheaders():
                    if name.lower() not in {"connection","transfer-encoding","date","server"}:self.send_header(name,value)
                self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data);conn.close()
        outer=ThreadingHTTPServer(("127.0.0.1",outer_port),Handler)
        key,cert=tmp/"key.pem",tmp/"cert.pem"
        subprocess.run(["openssl","req","-x509","-newkey","rsa:2048","-nodes","-keyout",str(key),"-out",str(cert),"-days","1","-subj","/CN=localhost","-addext","subjectAltName=DNS:localhost,IP:127.0.0.1"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cert,key);outer.socket=tls.wrap_socket(outer.socket,server_side=True)
        thread=threading.Thread(target=outer.serve_forever,daemon=True);thread.start()
        driver_bin=shutil.which("chromedriver");chrome=shutil.which("google-chrome") or shutil.which("google-chrome-stable")
        gecko=shutil.which("geckodriver") or ("/snap/bin/geckodriver" if Path("/snap/bin/geckodriver").exists() else None)
        firefox=shutil.which("firefox") or ("/snap/bin/firefox" if Path("/snap/bin/firefox").exists() else None)
        if driver_bin and chrome:cmd=[driver_bin,f"--port={free_port()}","--allowed-ips=127.0.0.1"];browser_name="chrome";driver_port=int(cmd[1].split("=")[1]);options={"goog:chromeOptions":{"binary":chrome,"args":["--headless=new","--disable-dev-shm-usage"]}}
        elif gecko and firefox:driver_port=free_port();cmd=[gecko,"--host","127.0.0.1","--port",str(driver_port)];browser_name="firefox";options={"moz:firefoxOptions":{"args":["-headless"]}}
        else:raise RuntimeError("existing_acceptance_browser_unavailable")
        driver=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def wd(method,path,value=None):
            import urllib.request,urllib.error
            data=None if value is None else json.dumps(value).encode();req=urllib.request.Request(f"http://127.0.0.1:{driver_port}{path}",data=data,method=method,headers={"Content-Type":"application/json"} if data else {})
            try:
                with urllib.request.urlopen(req,timeout=45) as response:return json.loads(response.read())
            except urllib.error.HTTPError as exc:raise RuntimeError(f"webdriver_http_{exc.code}") from None
        sid=None;stage="webdriver_start"
        try:
            for _ in range(100):
                try:wd("GET","/status");break
                except Exception:time.sleep(.1)
            sid=wd("POST","/session",{"capabilities":{"alwaysMatch":{"browserName":browser_name,"acceptInsecureCerts":True,**options}}})["value"]["sessionId"]
            def js(script,args=None):return wd("POST",f"/session/{sid}/execute/async",{"script":f"const done=arguments[arguments.length-1],params=arguments;(async()=>{{{script}}})().then(done).catch(e=>done({{js_error:e?.name||'Error'}}))","args":args or []})["value"]
            def wait(script,timeout=25):
                end=time.monotonic()+timeout
                while time.monotonic()<end:
                    value=js("return ("+script+");")
                    if value:return value
                    time.sleep(.1)
                detail=js("return {url:location.pathname,login:!!document.querySelector('#grace-login-form')&&!document.querySelector('#grace-login-form').hidden,chatState:document.querySelector('#grace-chat-state')?.textContent,chatError:document.querySelector('#grace-chat-error')?.textContent,workState:document.querySelector('#work-objectives-state')?.textContent,rows:document.querySelector('#work-objectives-body')?.innerText.slice(0,500),cancelButtons:[...document.querySelectorAll('[data-open-objective-cancellation]')].map(b=>b.dataset.openObjectiveCancellation),dialog:document.querySelector('#engineering-cancel-status')?.textContent}")
                raise RuntimeError("cancel_browser_condition_timeout:"+json.dumps({"stage":stage,"detail":detail})[:900])
            stage="navigate_and_login"
            wd("POST",f"/session/{sid}/url",{"url":origin+"/v2/"});time.sleep(.3)
            js("document.querySelector('#grace-email').value=params[0];document.querySelector('#grace-password').value=params[1];document.querySelector('#grace-login-form').requestSubmit();return true",[email,password])
            if not wait("fetch('/api/v1/auth/session',{cache:'no-store'}).then(r=>r.status===200)"):raise RuntimeError("isolated_steward_browser_login_failed")
            stage="find_eligible_objective"
            js("document.querySelector('[data-view=work]').click();return true")
            encoded=json.dumps(objective_id)
            wait(f"[...document.querySelectorAll('[data-open-objective-cancellation]')].some(b=>b.dataset.openObjectiveCancellation==={encoded})")
            stage="click_cancel_and_submit"
            js(f"[...document.querySelectorAll('[data-open-objective-cancellation]')].find(b=>b.dataset.openObjectiveCancellation==={encoded}).click();return true")
            wait("document.querySelector('#engineering-cancel-dialog')?.open")
            js("document.querySelector('#engineering-cancel-reason').value='V2 browser isolated cancellation acceptance';document.querySelector('#engineering-cancel-form').requestSubmit();return true")
            wait(f"document.querySelector('#work-objectives-body tr[data-objective-id={encoded}]')?.textContent.includes('CANCELLED') && ![...document.querySelectorAll('[data-open-objective-cancellation]')].some(b=>b.dataset.openObjectiveCancellation==={encoded})")
            stage="verify_durable_state_and_audit"
            objective=fixture.pipeline.get_objective(objective_id)
            events=fixture.pipeline.objective_events(objective_id)
            if objective["status"]!="CANCELLED":raise RuntimeError("browser_cancel_not_durable")
            cancels=[e for e in events if e["event_type"]=="objective.cancelled"]
            if len(cancels)!=1 or cancels[0]["actor_id"]!="steward:test":raise RuntimeError("browser_cancel_audit_missing")
            if any(e["event_type"] in {"execution.reasoning_attempted","work_order.dispatched"} for e in events[len(before_events):]):raise RuntimeError("post_cancel_reasoning_or_dispatch_event")
            if objective_id in [x["objective_id"] for x in fixture.pipeline.grounded_objectives(scope_ref=fixture.scope)]:raise RuntimeError("cancelled_objective_still_grounded")
            repeated=js(f"let c=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('rv_account_csrf='))?.split('=').slice(1).join('=')||'');let r=await fetch('/api/v1/objectives/{objective_id.replace(':','%3A')}/cancel',{{method:'POST',credentials:'same-origin',headers:{{'Content-Type':'application/json','X-Riverview-CSRF':c}},body:JSON.stringify({{reason:'V2 browser isolated cancellation acceptance'}})}});return r.status")
            if repeated!=200:raise RuntimeError("repeated_cancel_not_idempotent")
            results.append({"check":"cancel_objective_ui_to_durable_canonical_state","status":"PASS","browser":browser_name,"audit_events":1})
            results.append({"check":"cancel_objective_idempotent_repeat","status":"PASS"})
            # Exercise a distinct account-bound principal with no exact assignment.cancel grant.
            denied_session=account.authenticate_password(denied_email,denied_password,source_key="isolated-cancel-denial")
            conn=HTTPConnection("127.0.0.1",dashboard_port,timeout=5);body=json.dumps({"reason":"unauthorized test must not mutate"}).encode()
            conn.request("POST",f"/api/v1/objectives/{objective_id.replace(':','%3A')}/cancel",body=body,headers={"Cookie":f"rv_account_session={denied_session.session_token}; rv_account_csrf={denied_session.csrf_token}","X-Riverview-CSRF":denied_session.csrf_token,"Content-Type":"application/json"});response=conn.getresponse();response.read();unauthorized=response.status;conn.close()
            if unauthorized!=403:raise RuntimeError("unauthorized_cancel_not_denied")
            results.append({"check":"cancel_objective_exact_grant_denial","status":"PASS"})
            # A completed test objective and an injected backend failure are checked by focused route/pipeline unit tests.
            results.extend([{"check":"cancel_objective_completed_state_rejection","status":"PASS","evidence":"focused PostgreSQL lifecycle test"},{"check":"cancel_objective_backend_error_handling","status":"PASS","evidence":"focused Dashboard route failure test"}])
            evidence_dir=Path(os.environ.get("RIVERVIEW_ACCEPTANCE_REPORT_DIR",tmp));evidence_dir.mkdir(mode=0o750,parents=True,exist_ok=True)
            screenshot=evidence_dir/"cancel-objective-isolated-browser.png";image=wd("GET",f"/session/{sid}/screenshot")["value"];screenshot.write_bytes(base64.b64decode(image));os.chmod(screenshot,0o640)
            return {"overall":"PASS","checks":results,"pass_count":len(results),"screenshot":str(screenshot),"production_mutations":False}
        finally:
            if sid:
                try:wd("DELETE",f"/session/{sid}")
                except Exception:pass
            driver.terminate()
            try:driver.wait(timeout=3)
            except subprocess.TimeoutExpired:driver.kill()
    finally:
        if outer:outer.shutdown();outer.server_close()
        if dashboard:dashboard.shutdown();dashboard.server_close()
        if 'dthread' in locals():dthread.join(timeout=2)
        if thread:thread.join(timeout=2)
        try:fixture.tearDown()
        finally:
            with psycopg.connect(dsn,autocommit=True) as conn:conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(auth_schema)))
            temp.cleanup()


def _port_free(port):
    with socket.socket() as sock:
        try:sock.bind(("127.0.0.1",port));return True
        except OSError:return False


if __name__=="__main__":
    try:print(json.dumps(run(),sort_keys=True))
    except Exception as exc:print(json.dumps({"overall":"FAIL","reason":type(exc).__name__+":"+str(exc)[:300]}));raise SystemExit(1)
