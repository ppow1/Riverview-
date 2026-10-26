#!/usr/bin/env python3
"""Integrate isolated canonical workflows into the existing acceptance runner."""
from __future__ import annotations
import argparse, os, tempfile
from pathlib import Path

RUN_ANCHOR='''            checks.extend(browser_acceptance(creds,
                account_admin_required=live_source_commit!=ACCOUNT_ADMIN_PRE_FEATURE_COMMIT,
                live_source_commit=live_source_commit))
'''
RUN_REPLACEMENT=RUN_ANCHOR+'''            stage="isolated_canonical_workflow_acceptance"
            isolated=subprocess.run([sys.executable,str(Path(__file__).resolve().parent/"invoke_isolated_website_acceptance.py")],
                input=json.dumps({"email":creds["steward_email"],"password":creds["steward"]}),
                text=True,capture_output=True,timeout=900,
                env={**os.environ,"RIVERVIEW_ACCEPTANCE_ORIGIN":BASE,
                     "RIVERVIEW_ACCEPTANCE_REPORT_DIR":str(REPORT_DIR)})
            reports=[]
            for line in isolated.stdout.splitlines():
                try:
                    value=json.loads(line)
                    if isinstance(value,dict) and "counts" in value and "checks" in value:reports.append(value)
                except ValueError:pass
            if reports:
                acceptance=reports[-1]
                checks.extend(acceptance.get("checks",[]))
                checks.append({"check":"isolated_canonical_workflow_summary",
                    "status":acceptance.get("overall","FAIL"),"counts":acceptance.get("counts",{}),
                    "evidence":"delegation-isolated-acceptance.png and cancel-objective-isolated-browser.png"})
            else:
                checks.append({"check":"isolated_canonical_workflow_summary","status":"FAIL",
                    "reason":"isolated acceptance returned no machine-readable evidence"})
'''

SETTINGS_ANCHOR='''                    body={"level":current["level"],"quiet_hours":current["quiet_hours"]}
                    write=js("let c=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('rv_account_csrf='))?.split('=').slice(1).join('=')||'');let r=await fetch('/api/v1/notification-settings',{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json','X-Riverview-CSRF':c},body:JSON.stringify(BODY)});return r.status".replace("BODY",json.dumps(body,separators=(',',':'))))
                    stage = "settings_write_readback"
                    check=js("let r=await fetch('/api/v1/notification-settings',{cache:'no-store'});if(!r.ok)return {status:r.status};let x=await r.json();return {status:r.status,level:x.level,quiet_hours:x.quiet_hours}")
                    same=check.get("status")==200 and check.get("level")==current["level"] and check.get("quiet_hours")==current["quiet_hours"]
                    results.append({"check":"settings_same_value_write_readback","status":"PASS" if write==200 and same else "FAIL","http":write})
'''
SETTINGS_REPLACEMENT='''                    results.append({"check":"settings_write_readback","status":"SKIPPED",
                        "reason":"Production acceptance is read-only; persistent setting writes remain covered by isolated API tests."})
'''

def apply(source:str)->str:
    if not isinstance(source,str):raise ValueError("acceptance_runner_source_invalid")
    marker='''stage="isolated_canonical_workflow_acceptance"'''
    if marker in source:
        if "isolated_canonical_workflow_summary" in source and '"settings_write_readback","status":"SKIPPED"' in source:return source
        raise ValueError("isolated_acceptance_overlay_partial")
    if source.count(RUN_ANCHOR)!=1:raise ValueError(f"runner_integration_anchor_count_{source.count(RUN_ANCHOR)}")
    if source.count(SETTINGS_ANCHOR)!=1:raise ValueError(f"runner_readonly_settings_anchor_count_{source.count(SETTINGS_ANCHOR)}")
    return source.replace(SETTINGS_ANCHOR,SETTINGS_REPLACEMENT,1).replace(RUN_ANCHOR,RUN_REPLACEMENT,1)

def write_candidate(source_path:Path,output_path:Path):
    if source_path.is_symlink() or not source_path.is_file():raise ValueError("acceptance_runner_source_not_regular")
    result=apply(source_path.read_text(encoding="utf-8"));output_path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix="."+output_path.name+".",dir=output_path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as stream:stream.write(result);stream.flush();os.fsync(stream.fileno())
        os.chmod(name,source_path.stat().st_mode & 0o777);os.replace(name,output_path)
    finally:
        try:os.unlink(name)
        except FileNotFoundError:pass

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("source",type=Path);parser.add_argument("output",type=Path);args=parser.parse_args()
    write_candidate(args.source,args.output);print("isolated acceptance overlay prepared");return 0
if __name__=="__main__":raise SystemExit(main())
