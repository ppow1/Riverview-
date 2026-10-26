#!/usr/bin/env python3
# Riverview~ Controlled Script
# File: scripts/invoke_isolated_website_acceptance.py
# Component: RIVERVIEW-WEBSITE-ACCEPTANCE
# Revision: 1.0.0
# Purpose: Run isolated canonical browser acceptance against the selected V2 assets.
# Execution Model: Request-driven pg_virtualenv subprocess.
# Observability: Machine-readable PASS/FAIL/BLOCKED/SKIPPED report and screenshots.
# Dependencies: Existing persona file, pg_virtualenv, PostgreSQL 16, Python, Chrome.
# Authority: Temporary test accounts/schemas only; persistent database DSNs are discarded.
# Changed: 2026-10-26 UTC | RV-ISSUE268-DELEGATION-CANCEL-ACCEPTANCE | Bind reserved test persona credentials only to disposable canonical Steward fixtures.
# Contracts: Existing website runner and protected systemd LoadCredential persona source.
# Tests: scripts/run_isolated_website_acceptance_suite.py.
# History: Git and .riverview-backups/manifest.jsonl.
"""Acceptance-runner entry point for tests in a throw-away PostgreSQL cluster."""
from __future__ import annotations
import json, os, shutil, subprocess, sys
from pathlib import Path

REPORT=Path(os.environ.get("RIVERVIEW_ACCEPTANCE_REPORT_DIR","/var/lib/riverview-website-acceptance"))

def main():
    payload=json.dumps(json.load(sys.stdin),separators=(",",":"))
    pg_virtualenv=shutil.which("pg_virtualenv")
    if not pg_virtualenv:
        return {"overall":"BLOCKED","counts":{"PASS":0,"FAIL":0,"BLOCKED":1,"SKIPPED":0},
            "checks":[{"check":"isolated_website_acceptance","status":"BLOCKED","reason":"pg_virtualenv unavailable"}]}
    runner=Path(__file__).resolve().parent/"run_isolated_website_acceptance_suite.py"
    env=os.environ.copy()
    # Never let a service or shell override redirect mutation tests to a
    # persistent database. pg_virtualenv supplies the only permitted PG*
    # connection parameters for this child suite.
    for key in ("RIVERVIEW_TEST_PG_DSN", "RIVERVIEW_DATABASE_DSN", "DATABASE_URL",
                "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"):
        env.pop(key, None)
    dashboard=Path(env.get("RIVERVIEW_SOURCE_ROOT","/opt/riverview-status-dashboard/current")).resolve()
    env["RIVERVIEW_SOURCE_ROOT"]=str(dashboard)
    env["PYTHONPATH"]=str(dashboard/"src")+":"+str(dashboard/"tests")+":"+env.get("PYTHONPATH","")
    env["RIVERVIEW_ACCEPTANCE_REPORT_DIR"]=str(REPORT)
    release=Path("/var/www/riverview-v2-preview/releases")
    # The release identity is read from the actual served site; its validated
    # identifier selects only the corresponding immutable local asset folder.
    import urllib.request, ssl, re
    origin=env.get("RIVERVIEW_ACCEPTANCE_ORIGIN","https://192.168.1.155")
    try:
        supplied_assets=env.get("RIVERVIEW_V2_ASSET_ROOT")
        if supplied_assets:
            asset_root=Path(supplied_assets).resolve()
            if not (asset_root/"index.html").is_file():raise ValueError("candidate_v2_assets_unavailable")
            env["RIVERVIEW_V2_ASSET_ROOT"]=str(asset_root)
            supplied_assets=True
        else:supplied_assets=False
    except Exception:
        return {"overall":"BLOCKED","counts":{"PASS":0,"FAIL":0,"BLOCKED":1,"SKIPPED":0},
            "checks":[{"check":"isolated_website_acceptance","status":"BLOCKED","reason":"candidate V2 assets could not be resolved safely"}]}
    try:
        if supplied_assets: raise StopIteration
        request=urllib.request.Request(origin+"/v2/release.json",headers={"Cache-Control":"no-cache"})
        with urllib.request.urlopen(request,context=ssl._create_unverified_context(),timeout=5) as response:
            release_data=json.loads(response.read(4096))
        release_id=release_data.get("release_id","")
        asset_root=(release/release_id).resolve()
        if (not re.fullmatch(r"[A-Za-z0-9._-]{1,120}",release_id) or release not in asset_root.parents
                or not (asset_root/"index.html").is_file()):raise ValueError("served_v2_asset_release_unavailable")
        env["RIVERVIEW_V2_ASSET_ROOT"]=str(asset_root)
    except StopIteration:
        pass
    except Exception:
        return {"overall":"BLOCKED","counts":{"PASS":0,"FAIL":0,"BLOCKED":1,"SKIPPED":0},
            "checks":[{"check":"isolated_website_acceptance","status":"BLOCKED","reason":"active V2 release assets could not be resolved safely"}]}
    command=[pg_virtualenv,"-t",sys.executable,str(runner)]
    try:
        result=subprocess.run(command,input=payload,text=True,capture_output=True,timeout=600,env=env)
    except subprocess.TimeoutExpired:
        return {"overall":"BLOCKED","counts":{"PASS":0,"FAIL":0,"BLOCKED":1,"SKIPPED":0},
            "checks":[{"check":"isolated_website_acceptance","status":"BLOCKED","reason":"isolated browser suite timed out"}]}
    reports=[]
    for line in result.stdout.splitlines():
        try:
            value=json.loads(line)
            if isinstance(value,dict) and "counts" in value and "checks" in value:reports.append(value)
        except ValueError:pass
    if reports:return reports[-1]
    return {"overall":"FAIL","counts":{"PASS":0,"FAIL":1,"BLOCKED":0,"SKIPPED":0},
        "checks":[{"check":"isolated_website_acceptance","status":"FAIL","reason":"isolated suite did not return a machine-readable report"}]}

if __name__=="__main__":
    try:
        report=main();print(json.dumps(report,sort_keys=True))
        raise SystemExit(0 if report.get("overall")=="PASS" else 1)
    except SystemExit:raise
    except Exception as exc:
        print(json.dumps({"overall":"FAIL","counts":{"PASS":0,"FAIL":1,"BLOCKED":0,"SKIPPED":0},
            "checks":[{"check":"isolated_website_acceptance","status":"FAIL",
                "reason":type(exc).__name__+":"+str(exc)[:160]}]}))
        raise SystemExit(1)
