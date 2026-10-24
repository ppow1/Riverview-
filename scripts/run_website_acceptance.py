#!/usr/bin/env python3
"""Run authenticated acceptance against the currently served Riverview V2 release.

Revision: 1.0.0
"""
from __future__ import annotations

import hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = os.environ.get("RIVERVIEW_ACCEPTANCE_ORIGIN", "https://192.168.1.155")
REPORT_DIR = Path(os.environ.get("RIVERVIEW_ACCEPTANCE_REPORT_DIR", "/var/lib/riverview-website-acceptance"))
PERSONAS = {"steward":"steward", "operator":"operator", "engineering":"operator", "viewer":"viewer"}


def browser_acceptance(credentials: dict) -> list[dict]:
    port = socket.socket(); port.bind(("127.0.0.1", 0)); driver_port = port.getsockname()[1]; port.close()
    driver = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(driver_port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sid = None
    results = []
    stage = "webdriver_start"
    def wd(method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{driver_port}{path}", data=data, method=method,
            headers={"Content-Type":"application/json"} if data is not None else {})
        try:
            with urllib.request.urlopen(req, timeout=45) as res:
                raw = res.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            try:
                value=json.loads(exc.read() or b"{}").get("value", {})
                detail=str(value.get("error", "unknown"))+"_"+str(value.get("message", ""))[:80]
                for secret in credentials.values():
                    if isinstance(secret,str) and len(secret)>12: detail=detail.replace(secret,"[redacted]")
                detail="".join(ch if ch.isalnum() or ch in "_.-" else "_" for ch in detail)
            except Exception: detail="unknown"
            raise RuntimeError(f"webdriver_http_{exc.code}_{str(detail)[:32]}") from None
    def js(expr, args=None):
        script=f"const done=arguments[arguments.length-1];const params=arguments;(async()=>{{{expr}}})().then(done).catch(e=>done({{js_error:e?.name||'Error'}}))"
        return wd("POST", f"/session/{sid}/execute/async", {"script":script, "args":args or []})["value"]
    try:
        for _ in range(100):
            try:
                wd("GET", "/status"); break
            except Exception: time.sleep(.1)
        caps={"capabilities":{"alwaysMatch":{"browserName":"firefox","acceptInsecureCerts":True,
             "moz:firefoxOptions":{"args":["-headless"]}}}}
        stage = "webdriver_session"
        sid=wd("POST","/session",caps)["value"]["sessionId"]
        stage = "navigate_live_v2"
        wd("POST",f"/session/{sid}/url",{"url":BASE+"/v2/"})
        time.sleep(.5)
        stage = "unauthenticated_session"
        anon=js("try { let r=await fetch('/api/v1/auth/session',{cache:'no-store'}); return r.status } catch(e){ return 0 }")
        results.append({"check":"unauthenticated_session_denied","status":"PASS" if anon==401 else "FAIL","http":anon})
        fresh=js("let s=[...document.scripts].find(x=>x.src.includes('grace-chat.js'))?.src||'';let r=await fetch('/v2/',{method:'HEAD',cache:'no-store'});return {script:s,cache:r.headers.get('cache-control')||''}")
        results.append({"check":"fresh_release_cache_contract","status":"PASS" if 'rev=' in fresh.get('script','') and 'no-store' in fresh.get('cache','').lower() else "FAIL"})
        wd("POST",f"/session/{sid}/url",{"url":BASE+"/v2/"})
        refreshed=js("return [...document.scripts].find(x=>x.src.includes('grace-chat.js'))?.src||''")
        results.append({"check":"browser_refresh_uses_versioned_grace_asset","status":"PASS" if refreshed==fresh.get('script') else "FAIL"})
        for persona, role in PERSONAS.items():
            stage = "login_" + persona
            email=credentials[persona+"_email"]
            password=credentials[persona]
            login=js("let r=await fetch('/api/v1/auth/session',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:params[0],password:params[1]})});return r.status",[email,password])
            if login != 200:
                results.append({"check":f"login_{persona}","status":"FAIL","http":login}); continue
            stage = "session_identity_" + persona
            who=js("let r=await fetch('/api/v1/auth/session',{cache:'no-store'});if(!r.ok)return {status:r.status};let x=await r.json();return {status:r.status,roles:x.identity?.roles||[]}")
            results.append({"check":f"login_role_{persona}","status":"PASS" if role in who.get("roles",[]) else "FAIL","http":who.get("status"),"expected_role":role})
            # Confirm the live route is serving the V2 shell and its current bundle.
            for view in ["resources","work","communications","notification-settings"]:
                stage = "navigation_" + persona + "_" + view
                shown=js("let b=document.querySelector('[data-view='+JSON.stringify(params[0])+']');if(!b)return false;b.click();return b.getAttribute('aria-current')==='page'",[view])
                results.append({"check":f"navigation_{persona}_{view}","status":"PASS" if shown else "FAIL"})
            if role == "steward":
                stage = "notification_settings_read"
                settings=js("let r=await fetch('/api/v1/notification-settings',{cache:'no-store'});return {status:r.status,body:r.ok?await r.json():null}")
                results.append({"check":"settings_authenticated_read","status":"PASS" if settings.get("status")==200 else "FAIL","http":settings.get("status")})
                if settings.get("status")==200:
                    stage = "settings_page_values"
                    current=settings["body"]
                    ui=js("await new Promise(r=>setTimeout(r,350));return {level:document.querySelector('#notification-settings-level').value,enabled:document.querySelector('#notification-quiet-enabled').checked,start:document.querySelector('#notification-quiet-start').value,end:document.querySelector('#notification-quiet-end').value,timezone:document.querySelector('#notification-quiet-timezone').value}")
                    expected={"level":current["level"],"enabled":current["quiet_hours"]["enabled"],"start":current["quiet_hours"]["start"],"end":current["quiet_hours"]["end"],"timezone":current["quiet_hours"]["timezone"]}
                    results.append({"check":"settings_page_matches_api","status":"PASS" if ui==expected else "FAIL"})
                    body={"level":current["level"],"quiet_hours":current["quiet_hours"]}
                    write=js("let c=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('rv_account_csrf='))?.split('=').slice(1).join('=')||'');let r=await fetch('/api/v1/notification-settings',{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Riverview-CSRF':c},body:JSON.stringify(BODY)});return r.status".replace("BODY",json.dumps(body,separators=(',',':'))))
                    stage = "settings_write_readback"
                    check=js("let r=await fetch('/api/v1/notification-settings',{cache:'no-store'});if(!r.ok)return {status:r.status};let x=await r.json();return {status:r.status,level:x.level,quiet_hours:x.quiet_hours}")
                    same=check.get("status")==200 and check.get("level")==current["level"] and check.get("quiet_hours")==current["quiet_hours"]
                    results.append({"check":"settings_same_value_write_readback","status":"PASS" if write==200 and same else "FAIL","http":write})
                # No ordinary reasoning request is sent. This identity is intentionally unlinked
                # and the page's own connect flow rejects it at conversation-session.
                stage = "grace_auth_boundary"
                grace=js("let r=await fetch('/api/v1/resident/conversation-session',{method:'POST',headers:{'X-Riverview-CSRF':decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('rv_account_csrf='))?.split('=').slice(1).join('=')||'')}});return r.status")
                results.append({"check":"grace_conversation_auth_boundary","status":"PASS" if grace==403 else "FAIL","http":grace})
                results.append({"check":"grace_natural_language_query","status":"SKIPPED","reason":"Test identity has no institutional principal/grant"})
                results.append({"check":"production_cancellation_mutation","status":"SKIPPED","reason":"No disposable production objective/work order"})
                results.append({"check":"snapshot_archive_write","status":"SKIPPED","reason":"Would create a durable production archive record"})
            elif role in {"operator","viewer"}:
                denied=js("return fetch('/api/v1/notification-settings',{cache:'no-store'}).then(r=>r.status)")
                results.append({"check":f"settings_denied_{persona}","status":"PASS" if denied==403 else "FAIL","http":denied})
            stage = "logout_" + persona
            logout=js("let c=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('rv_account_csrf='))?.split('=').slice(1).join('=')||'');let r=await fetch('/api/v1/auth/session',{method:'DELETE',credentials:'same-origin',headers:{'X-Riverview-CSRF':c}});return r.status")
            after=js("return fetch('/api/v1/auth/session',{cache:'no-store'}).then(r=>r.status)")
            results.append({"check":f"logout_{persona}","status":"PASS" if logout==200 and after==401 else "FAIL","http":logout})
        return results
    except Exception as exc:
        raise RuntimeError(stage + ":" + type(exc).__name__ + ":" + str(exc)[:72]) from None
    finally:
        if sid:
            try: wd("DELETE",f"/session/{sid}")
            except Exception: pass
        driver.terminate()
        try: driver.wait(timeout=3)
        except subprocess.TimeoutExpired: driver.kill()


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"
    if mode not in {"light", "full"}:
        raise SystemExit("usage: run_website_acceptance.py [light|full]")
    REPORT_DIR.mkdir(parents=True, exist_ok=True, mode=0o750)
    timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds")
    checks=[]
    try:
        request=urllib.request.Request(BASE+"/v2/",headers={"Cache-Control":"no-cache"})
        with urllib.request.urlopen(request,context=__import__('ssl')._create_unverified_context(),timeout=10) as res:
            html=res.read(1_000_000).decode("utf-8","replace")
            checks.append({"check":"live_v2_availability","status":"PASS" if res.status==200 and "Riverview" in html else "FAIL","http":res.status})
        try:
            with urllib.request.urlopen(BASE+"/v2/release.json",context=__import__('ssl')._create_unverified_context(),timeout=5) as response:
                release=json.loads(response.read(4096))
            valid=release.get("schema_version")=="rv.website-release.v1" and bool(release.get("release_id")) and bool(release.get("source_commit"))
            checks.append({"check":"live_release_identity","status":"PASS" if valid else "FAIL","release":release.get("release_id"),"source_commit":release.get("source_commit")})
        except urllib.error.HTTPError as exc:
            checks.append({"check":"live_release_identity","status":"WARNING","reason":f"http_{exc.code}"})
        cred_path=Path(os.environ.get("CREDENTIALS_DIRECTORY","/nonexistent"))/"personas.json"
        if mode == "full" and cred_path.is_file():
            data=json.loads(cred_path.read_text())
            creds={**data,**{name+"_email":f"codex-test-{name}@riverview.invalid" for name in PERSONAS}}
            checks.extend(browser_acceptance(creds))
        elif mode == "full":
            checks.append({"check":"authenticated_browser","status":"SKIPPED","reason":"persona credential unavailable"})
    except Exception as exc:
        checks.append({"check":"runner","status":"FAIL","reason":str(exc)[:120]})
    report={"schema_version":"rv.website-acceptance.v1","timestamp":timestamp,"origin":BASE,
            "checks":checks,"overall":"FAIL" if any(x["status"]=="FAIL" for x in checks) else
            ("WARNING" if any(x["status"] in {"WARNING","SKIPPED"} for x in checks) else "PASS")}
    incident_file=REPORT_DIR/"incident.json"
    if report["overall"] == "FAIL":
        try:
            active=json.loads(incident_file.read_text()) if incident_file.exists() else {"incident_id":timestamp}
            incident_key="website-acceptance:"+hashlib.sha256(active["incident_id"].encode()).hexdigest()[:32]
            pgpass=Path(os.environ.get("CREDENTIALS_DIRECTORY","/nonexistent"))/"pgpass"
            dsn=os.environ.get("RIVERVIEW_DATABASE_DSN")
            if dsn and pgpass.is_file():
                import psycopg
                temp=Path(tempfile.mkdtemp(prefix="rv-webaccept-pgpass-")); local_pass=temp/"pgpass"
                try:
                    local_pass.write_bytes(pgpass.read_bytes()); os.chmod(local_pass,0o600)
                    os.environ["PGPASSFILE"]=str(local_pass)
                    names=[x["check"] for x in checks if x["status"]=="FAIL"][:20]
                    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
                        cur.execute("""INSERT INTO riverview_dev.cme_monitor_events
                            (event_key,service_id,event_type,attention_key,details)
                            VALUES (%s,'riverview-website-acceptance','monitor_failed',%s,%s::jsonb)
                            ON CONFLICT(event_key) DO NOTHING""",
                            (incident_key,incident_key,json.dumps({"failure_type":"website_acceptance_failed","failed_checks":names})))
                    incident_file.write_text(json.dumps(active)+"\n"); os.chmod(incident_file,0o640)
                finally:
                    try: local_pass.unlink()
                    except FileNotFoundError: pass
                    try: temp.rmdir()
                    except OSError: pass
        except Exception:
            checks.append({"check":"failure_alert_enqueue","status":"WARNING","reason":"existing_notification_path_unavailable"})
            report["checks"]=checks
    else:
        try: incident_file.unlink()
        except FileNotFoundError: pass
    dest=REPORT_DIR/"latest.json"
    tmp=dest.with_suffix(".tmp")
    tmp.write_text(json.dumps(report,sort_keys=True)+"\n")
    os.chmod(tmp,0o640); tmp.replace(dest)
    print(json.dumps({"overall":report["overall"],"timestamp":timestamp,"checks":checks},separators=(',',':')))
    return 1 if report["overall"]=="FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
