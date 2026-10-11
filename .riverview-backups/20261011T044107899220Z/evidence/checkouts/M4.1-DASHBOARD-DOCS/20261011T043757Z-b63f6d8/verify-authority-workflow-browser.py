# RIVERVIEW~ CONTROLLED EVIDENCE SCRIPT
# File: evidence/checkouts/M4.1-DASHBOARD-DOCS/verify-authority-workflow-browser.py
# Component: STEWARD-DASHBOARD / INSTITUTIONAL-AUTHORITY
# Revision: 1.0.1
# Purpose: Independently render the deployed M4.1 canonical graph in Firefox
# Execution Model: Request-driven read-only browser acceptance utility
# Observability: Redacted JSON result and graph screenshot; no token output
# Dependencies: Python standard library, Firefox, geckodriver, protected local dashboard token
# Authority: Read-only dashboard APIs; no database/service/assignment mutation
# Changed: 2026-10-11 UTC | RV-M4.1-001 | Dispatch the proven SVG click event and capture first failed harness outcome
# Contracts: docs/components/STATUS_DASHBOARD.md; process_graphs/institutional-authority/identity-and-grants.json
# History: evidence artifacts manifest
"""Render and inspect the installed M4.1 graph in the authenticated dashboard."""
import json, os, socket, subprocess, time, urllib.error, urllib.request
from pathlib import Path

TOKEN=Path('/home/admin1/.config/riverview/status-dashboard.token')
GRAPH='rv:institutional-authority:identity-and-grants'

def main():
    if not TOKEN.is_file() or TOKEN.is_symlink() or TOKEN.stat().st_mode & 0o077:
        raise SystemExit('protected_dashboard_token_unavailable')
    token=TOKEN.read_text().strip()
    if not token: raise SystemExit('protected_dashboard_token_empty')
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1',0)); port=reservation.getsockname()[1]
    driver=subprocess.Popen(['geckodriver','--host','127.0.0.1','--port',str(port)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    sid=None
    def request(method,path,payload=None):
        raw=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',data=raw,method=method,headers={'Content-Type':'application/json'} if raw else {})
        with urllib.request.urlopen(req,timeout=15) as r:
            value=r.read(); return json.loads(value) if value else None
    def js(script,args=None): return request('POST',f'/session/{sid}/execute/sync',{'script':script,'args':args or []})['value']
    def wait(expr,timeout=15):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            value=js('return ('+expr+');')
            if value:return value
            time.sleep(.2)
        raise RuntimeError('browser_condition_timeout')
    try:
        for _ in range(80):
            try: request('GET','/status'); break
            except (OSError,urllib.error.URLError): time.sleep(.2)
        caps={'capabilities':{'alwaysMatch':{'browserName':'firefox','moz:firefoxOptions':{'args':['-headless']}}}}
        sid=request('POST','/session',caps)['value']['sessionId']
        request('POST',f'/session/{sid}/window/rect',{'x':0,'y':0,'width':1600,'height':1200})
        request('POST',f'/session/{sid}/url',{'url':'http://127.0.0.1:8766/'})
        js("window.__rvBrowserErrors=[];addEventListener('error',e=>window.__rvBrowserErrors.push(String(e.message||'error')));addEventListener('unhandledrejection',e=>window.__rvBrowserErrors.push('rejection')); ")
        js("document.querySelector('#token').value=arguments[0];document.querySelector('#login-form').requestSubmit();",[token])
        wait("!document.querySelector('#workspace').hidden")
        js("document.querySelector('[data-view=workflows]').click()")
        wait("document.querySelector('#graph-select').options.length>0")
        has=js("return [...document.querySelector('#graph-select').options].some(o=>o.value===arguments[0])",[GRAPH])
        if not has: raise RuntimeError('authority_graph_missing_from_index')
        js("const s=document.querySelector('#graph-select');s.value=arguments[0];s.dispatchEvent(new Event('change',{bubbles:true}));",[GRAPH])
        wait("document.querySelectorAll('#graph-canvas .graph-node').length===12")
        report=js("const g=document.querySelector('#graph-canvas svg');return {componentGraph:g.getAttribute('aria-label'),nodes:document.querySelectorAll('#graph-canvas .graph-node').length,decisions:document.querySelectorAll('#graph-canvas .graph-node.graph-decision').length,transitions:document.querySelectorAll('#graph-canvas .graph-edge').length,currentHighlights:document.querySelectorAll('#graph-canvas .graph-live-current').length,position:document.querySelector('#graph-execution-position').textContent,revision:document.querySelector('#graph-revision').textContent}")
        js("document.querySelector('#graph-canvas .graph-node').dispatchEvent(new MouseEvent('click',{bubbles:true}));return true;")
        report['selected_stable_id']=wait("document.querySelector('#graph-node-detail code')&&document.querySelector('#graph-node-detail code').textContent")
        report['browser_errors']=js('return window.__rvBrowserErrors')
        report['screenshot_bytes']=len(request('GET',f'/session/{sid}/screenshot')['value'])
        png=request('GET',f'/session/{sid}/screenshot')['value']
        import base64
        out=Path(os.environ['RV_EVIDENCE_DIR'])
        (out/'authority-workflow-view.png').write_bytes(base64.b64decode(png))
        report['screenshot']='authority-workflow-view.png'
        report['pass']=report['nodes']==12 and report['decisions']==1 and report['transitions']==13 and report['currentHighlights']==0 and 'unknown' in report['position'].lower() and not report['browser_errors'] and report['selected_stable_id'].startswith('rv:institutional-authority:identity-and-grants:')
        (out/'authority-workflow-browser.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        print(json.dumps(report,sort_keys=True))
        if not report['pass']: raise RuntimeError('authority_graph_browser_acceptance_failed')
    finally:
        if sid:
            try: request('DELETE',f'/session/{sid}')
            except Exception: pass
        driver.terminate()
        try: driver.wait(timeout=5)
        except subprocess.TimeoutExpired: driver.kill(); driver.wait(timeout=5)

if __name__=='__main__': main()
