#!/usr/bin/env python3
"""Run disposable canonical delegation and V2 cancellation acceptance with one PG cluster."""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

SCRIPTS=Path(__file__).resolve().parent

def run_script(name,payload,env):
    result=subprocess.run([sys.executable,str(SCRIPTS/name)],input=payload,text=True,
        capture_output=True,timeout=300,env=env)
    reports=[]
    for line in result.stdout.splitlines():
        try:
            item=json.loads(line)
            if isinstance(item,dict) and "overall" in item:reports.append(item)
        except (ValueError,TypeError):pass
    if not reports:
        status="BLOCKED" if any(code in result.stdout+result.stderr for code in
            ("isolated_test_database_unavailable","existing_acceptance_browser_unavailable")) else "FAIL"
        return {"overall":status,"checks":[{"check":name.removesuffix(".py"),"status":status,
            "reason":"isolated test runner did not produce a machine-readable result"}]}
    return reports[-1]

def main():
    payload=json.dumps(json.load(sys.stdin),separators=(",",":"))
    env=os.environ.copy()
    dsn=env.get("RIVERVIEW_TEST_PG_DSN")
    if not dsn:
        from psycopg.conninfo import make_conninfo
        required=("PGHOST","PGPORT","PGDATABASE","PGUSER")
        if not all(env.get(key) for key in required):raise RuntimeError("isolated_test_database_unavailable")
        dsn=make_conninfo(host=env["PGHOST"],port=env["PGPORT"],dbname=env["PGDATABASE"],user=env["PGUSER"])
        env["RIVERVIEW_TEST_PG_DSN"]=dsn
    results=[]
    for name in ("verify_v2_isolated_delegation_browser.py","verify_v2_cancel_objective_browser.py"):
        report=run_script(name,payload,env);results.extend(report.get("checks",[]))
        if report.get("overall")!="PASS" and not report.get("checks"):
            results.append({"check":name.removesuffix(".py"),"status":report.get("overall","FAIL"),
                "reason":report.get("reason","isolated acceptance failed")})
        if report.get("overall")!="PASS" and report.get("checks"):
            results.append({"check":name.removesuffix(".py")+"_suite_status","status":report.get("overall")})
    counts={status:sum(item.get("status")==status for item in results)
        for status in ("PASS","FAIL","BLOCKED","SKIPPED")}
    overall="FAIL" if counts["FAIL"] else "BLOCKED" if counts["BLOCKED"] else "WARNING" if counts["SKIPPED"] else "PASS"
    print(json.dumps({"overall":overall,"counts":counts,"checks":results},sort_keys=True))
    return 0 if overall=="PASS" else 1

if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"overall":"BLOCKED" if "unavailable" in str(exc) else "FAIL",
            "counts":{"PASS":0,"FAIL":0,"BLOCKED":1,"SKIPPED":0},
            "checks":[{"check":"isolated_website_acceptance","status":"BLOCKED" if "unavailable" in str(exc) else "FAIL",
                "reason":type(exc).__name__+":"+str(exc)[:160]}]}))
        raise SystemExit(1)
