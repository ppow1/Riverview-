#!/usr/bin/env python3
# Riverview~ Controlled Script
# File: scripts/invoke_isolated_website_acceptance.py
# Component: RIVERVIEW-WEBSITE-ACCEPTANCE
# Revision: 1.0.2
# Purpose: Run isolated canonical browser acceptance against the selected V2 assets.
# Execution Model: Request-driven pg_virtualenv subprocess.
# Observability: Machine-readable PASS/FAIL/BLOCKED/SKIPPED report and screenshots.
# Dependencies: Existing persona file, pg_virtualenv, PostgreSQL 16, Python, Chrome.
# Authority: Temporary test accounts/schemas only; persistent database DSNs are discarded.
# Changed: 2026-10-26 UTC | RV-ISSUE268-DELEGATION-CANCEL-ACCEPTANCE | Bind reserved test persona credentials only to disposable canonical Steward fixtures.
# Changed: 2026-10-26 UTC | RV-ISSUE268-ACTIVE-V2-ASSET-RESOLUTION | Resolve the actual served immutable V2 assets by content when release.json is absent.
# Changed: 2026-10-26 UTC | RV-ISSUE268-ASSET-RESOLUTION-REGRESSION | Require exact served-asset match and safely validate release identities.
# Contracts: Existing website runner and protected systemd LoadCredential persona source.
# Tests: scripts/run_isolated_website_acceptance_suite.py.
# History: Git and .riverview-backups/manifest.jsonl.
"""Acceptance-runner entry point for tests in a throw-away PostgreSQL cluster."""
from __future__ import annotations
import hashlib, json, os, re, shutil, ssl, subprocess, sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

REPORT=Path(os.environ.get("RIVERVIEW_ACCEPTANCE_REPORT_DIR","/var/lib/riverview-website-acceptance"))

def resolve_served_assets(origin: str, release_root: Path, fetch=None) -> Path:
    """Resolve a served V2 page to an immutable local package without trusting URL paths."""
    release_root=Path(release_root)
    if release_root.is_symlink() or not release_root.is_dir():
        raise ValueError("served_v2_release_root_invalid")
    release_root=release_root.resolve()
    if fetch is None:
        context=ssl._create_unverified_context()
        def fetch(url,limit=2_000_000):
            request=Request(url,headers={"Cache-Control":"no-cache"})
            with urlopen(request,context=context,timeout=6) as response:
                data=response.read(limit+1)
            if len(data)>limit:raise ValueError("served_v2_asset_size_exceeded")
            return data

    try:
        release_data=json.loads(fetch(origin+"/v2/release.json",4096))
    except HTTPError as exc:
        if exc.code!=404:raise
        release_data=None
    if release_data is not None:
        release_id=release_data.get("release_id","")
        if not isinstance(release_id,str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,120}",release_id):
            raise ValueError("served_v2_asset_release_invalid")
        candidate=release_root/release_id
        if candidate.is_symlink():raise ValueError("served_v2_asset_release_invalid")
        resolved=candidate.resolve()
        if release_root not in resolved.parents or not (resolved/"index.html").is_file():
            raise ValueError("served_v2_asset_release_invalid")
        return resolved

    # Older production Nginx aliases the immutable folder but has no release
    # manifest. Match the page and all assets it declares, never a guessed path.
    served_index=fetch(origin+"/v2/")
    declared=re.findall(rb'''(?:src|href)\s*=\s*["'](assets/[^"']+)''',served_index)
    asset_paths=sorted({"index.html"}|{item.decode("ascii").split("?",1)[0] for item in declared})
    if len(asset_paths)<2 or any(path.startswith("/") or ".." in Path(path).parts
                                  or not path.startswith("assets/") and path!="index.html"
                                  for path in asset_paths):
        raise ValueError("served_v2_asset_manifest_invalid")
    served={"index.html":served_index}
    for rel in asset_paths:
        if rel!="index.html":served[rel]=fetch(origin+"/v2/"+rel,5_000_000)
    hashes={rel:hashlib.sha256(data).digest() for rel,data in served.items()}
    matches=[]
    for candidate in release_root.iterdir():
        if not candidate.is_dir() or candidate.is_symlink():continue
        try:
            files={rel:candidate/rel for rel in asset_paths}
            if any(path.is_symlink() or not path.is_file() for path in files.values()):continue
            if all(hashlib.sha256(files[rel].read_bytes()).digest()==digest
                   for rel,digest in hashes.items()):matches.append(candidate.resolve())
        except OSError:continue
    if not matches:raise ValueError("served_v2_assets_do_not_match_an_immutable_local_release")
    return sorted(matches,key=lambda item:item.name)[-1]

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
        if supplied_assets:
            pass
        else:
            asset_root=resolve_served_assets(origin,release)
            env["RIVERVIEW_V2_ASSET_ROOT"]=str(asset_root)
    except Exception as exc:
        return {"overall":"BLOCKED","counts":{"PASS":0,"FAIL":0,"BLOCKED":1,"SKIPPED":0},
            "checks":[{"check":"isolated_website_acceptance","status":"BLOCKED",
                "reason":"active V2 assets could not be resolved safely ("+type(exc).__name__+")"}]}
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
