"""Add read-only Delegation Approvals coverage to the installed acceptance runner.

The runner remains the existing Selenium test program; this idempotent overlay
is a small release-time patch, not a second test framework.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

VIEWS_ANCHOR = '''            if role == "steward" and proposal_decisions_available: views.append("institutional-proposals")
'''
VIEWS_REPLACEMENT = VIEWS_ANCHOR + '''            if role == "steward": views.append("resident-permissions")
'''
STEWARD_ANCHOR = '''            if role == "steward":
                stage = "live_overview_projection_acceptance"
'''
STEWARD_INSERT = '''            if role == "steward":
                stage = "delegation_approvals_navigation"
                delegation_page = js("""
                    let nav=document.querySelector('[data-view=resident-permissions]');nav?.click();
                    await new Promise(r=>setTimeout(r,350));
                    let panel=document.querySelector('#delegation-approvals');
                    return {visible:!!panel&&!panel.hidden,
                        hostField:!!document.querySelector('#delegation-request-host'),
                        typeField:!!document.querySelector('#delegation-request-type'),
                        policyCards:!!document.querySelector('#delegation-authorization-type-details'),
                        refresh:!!document.querySelector('#delegation-refresh')}
                """)
                page_ok=(delegation_page.get("visible") and delegation_page.get("hostField")
                         and delegation_page.get("typeField") and delegation_page.get("policyCards")
                         and delegation_page.get("refresh"))
                results.append({"check":"delegation_approvals_navigation",
                    "status":"PASS" if page_ok else "FAIL"})
                stage = "delegation_authorized_read"
                delegation=js("""
                    let paths=['/api/v1/steward/delegation-grant-requests/options',
                        '/api/v1/steward/delegation-grant-requests?status=pending&limit=5',
                        '/api/v1/steward/delegation-grant-requests?status=approved&limit=5',
                        '/api/v1/steward/delegation-grant-requests?status=rejected&limit=5',
                        '/api/v1/steward/delegated-grants?state=active&limit=5',
                        '/api/v1/steward/delegated-grants?state=all&limit=5'];
                    let out=[];for(let path of paths){let r=await fetch(path,{cache:'no-store'});
                        let body=r.ok?await r.json():null;out.push({status:r.status,body});}
                    return {out}
                """)
                statuses=[item.get("status") for item in delegation.get("out",[])]
                if len(statuses)==6 and all(status==200 for status in statuses):
                    options=delegation["out"][0]["body"]
                    types=options.get("authorization_types",[])
                    codex=next((item for item in types if item.get("type_id")=="comms5_codex"),{})
                    policy_ok=(options.get("requester_principal_id")=="steward:camrui"
                        and any(item.get("scope_ref")=="host:octominer1" for item in options.get("hosts",[]))
                        and codex.get("action")=="comms5.operations.non_destructive.v1"
                        and codex.get("scope_ref")=="project:Riverview"
                        and codex.get("target_principal_id")=="service:chatgpt"
                        and codex.get("effective_expiry_hours_after_approval")==24
                        and codex.get("usage_limits_supported") is False
                        and codex.get("additional_authority_required")==[
                            "objective.submit", "assignment.create", "assignment.execute", "assignment.verify"]
                        and codex.get("status") in {"available", "unavailable"}
                        and codex.get("target_principal_id")=="service:chatgpt")
                    results.append({"check":"delegation_authenticated_read",
                        "status":"PASS" if policy_ok else "FAIL",
                        "http":statuses,"requester":options.get("requester_principal_id"),
                        "registered_host_count":len(options.get("hosts",[])),
                        "codex_authorization_status":codex.get("status","unavailable"),
                        "pending_count":len(delegation["out"][1]["body"].get("items",[])),
                        "approved_count":len(delegation["out"][2]["body"].get("items",[])),
                        "denied_count":len(delegation["out"][3]["body"].get("items",[])),
                        "active_grant_count":len(delegation["out"][4]["body"].get("items",[])),
                        "grant_history_count":len(delegation["out"][5]["body"].get("items",[]))})
                    form=js("""return {uses:!!document.querySelector('#delegation-request-max-uses'),
                        expiry:!!document.querySelector('#delegation-request-expiry'),
                        purpose:!!document.querySelector('#delegation-request-purpose'),
                        policyText:(document.querySelector('#delegation-authorization-type-details')?.innerText||'')}
                        """)
                    results.append({"check":"delegation_request_policy_controls",
                        "status":"PASS" if form.get("uses") and form.get("expiry") and form.get("purpose") and
                            all(value in form.get("policyText","") for value in [
                                "comms5.operations.non_destructive.v1", "project:Riverview",
                                "service:chatgpt", "24 hours after activation"]) else "FAIL"})
                    pending=delegation["out"][1]["body"].get("items",[])
                    if pending:
                        request_id=pending[0].get("request_id","")
                        detail=js("let r=await fetch(params[0],{credentials:'same-origin',cache:'no-store'});let body=r.ok?await r.json():{};return {status:r.status,body}",
                            ["/api/v1/steward/delegation-grant-requests/"+request_id])
                        detail_ok=(detail.get("status")==200 and
                            detail.get("body",{}).get("request_sha256")==pending[0].get("request_sha256") and
                            bool(detail.get("body",{}).get("request_sha256")))
                        results.append({"check":"delegation_request_detail_and_hash",
                            "status":"PASS" if detail_ok else "FAIL","http":detail.get("status")})
                    else:
                        results.append({"check":"delegation_request_detail_and_hash","status":"SKIPPED",
                            "reason":"No production pending request exists; mutating production authority to create one is prohibited."})
                elif len(statuses)==6 and all(status in {401,403} for status in statuses):
                    results.append({"check":"delegation_authenticated_read","status":"BLOCKED",
                        "http":statuses,
                        "reason":"The reserved website Steward persona is not linked to canonical Steward authority."})
                    results.append({"check":"delegation_request_policy_controls","status":"BLOCKED",
                        "reason":"Dynamic registered authorization options require canonical Steward authority."})
                    results.append({"check":"delegation_request_detail_and_hash","status":"BLOCKED",
                        "reason":"No authenticated Steward authority to read request details."})
                else:
                    results.append({"check":"delegation_authenticated_read","status":"FAIL",
                        "http":statuses,"reason":"A delegation read endpoint failed or returned an unexpected response."})
                    results.append({"check":"delegation_request_detail_and_hash","status":"BLOCKED",
                        "reason":"Delegation list read failed before request detail could be tested."})
                stage = "live_overview_projection_acceptance"
'''
NON_STEWARD_ANCHOR = '''            elif role in {"operator","viewer"}:
                denied=js("return fetch('/api/v1/notification-settings',{cache:'no-store'}).then(r=>r.status)")
'''
NON_STEWARD_REPLACEMENT = '''            elif role in {"operator","viewer"}:
                delegation_denied=js("return fetch('/api/v1/steward/delegation-grant-requests/options',{cache:'no-store'}).then(r=>r.status)")
                results.append({"check":f"delegation_unauthorized_{persona}",
                    "status":"PASS" if delegation_denied==403 else "FAIL","http":delegation_denied})
                denied=js("return fetch('/api/v1/notification-settings',{cache:'no-store'}).then(r=>r.status)")
'''
REPORT_ANCHOR = '''    report={"schema_version":"rv.website-acceptance.v1","timestamp":timestamp,
            "checks":checks,"overall":"FAIL" if any(x["status"]=="FAIL" for x in checks) else
            ("WARNING" if any(x["status"] in {"WARNING","SKIPPED"} for x in checks) else "PASS")}
'''
REPORT_REPLACEMENT = '''    report={"schema_version":"rv.website-acceptance.v1","timestamp":timestamp,
            "checks":checks,"overall":"FAIL" if any(x["status"]=="FAIL" for x in checks) else
            ("BLOCKED" if any(x["status"]=="BLOCKED" for x in checks) else
             ("WARNING" if any(x["status"] in {"WARNING","SKIPPED"} for x in checks) else "PASS"))}
'''
EXIT_ANCHOR = '''    return 1 if report["overall"]=="FAIL" else 0
'''
EXIT_REPLACEMENT = '''    return 1 if report["overall"] in {"FAIL","BLOCKED"} else 0
'''

def _once(source: str, anchor: str, replacement: str, label: str) -> str:
    count=source.count(anchor)
    if count != 1:
        raise ValueError(f"acceptance_runner_{label}_anchor_count_{count}")
    return source.replace(anchor,replacement,1)

def apply(source: str) -> str:
    if not isinstance(source,str):
        raise ValueError("acceptance_runner_source_invalid")
    marker='"check":"delegation_approvals_navigation"'
    expected=(VIEWS_REPLACEMENT,STEWARD_INSERT,NON_STEWARD_REPLACEMENT,
              REPORT_REPLACEMENT,EXIT_REPLACEMENT)
    if marker in source:
        if all(item in source for item in expected):
            return source
        raise ValueError("acceptance_runner_delegation_overlay_partial")
    result=_once(source,VIEWS_ANCHOR,VIEWS_REPLACEMENT,"views")
    result=_once(result,STEWARD_ANCHOR,STEWARD_INSERT,"steward")
    result=_once(result,NON_STEWARD_ANCHOR,NON_STEWARD_REPLACEMENT,"non_steward")
    result=_once(result,REPORT_ANCHOR,REPORT_REPLACEMENT,"report")
    return _once(result,EXIT_ANCHOR,EXIT_REPLACEMENT,"exit")

def write_candidate(source_path: Path, output_path: Path) -> None:
    if source_path.is_symlink() or not source_path.is_file():
        raise ValueError("acceptance_runner_source_not_regular")
    result=apply(source_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix="."+output_path.name+".",dir=output_path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as stream:
            stream.write(result); stream.flush(); os.fsync(stream.fileno())
        os.chmod(name,source_path.stat().st_mode & 0o777)
        os.replace(name,output_path)
    finally:
        try: os.unlink(name)
        except FileNotFoundError: pass

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source",type=Path); parser.add_argument("output",type=Path)
    args=parser.parse_args()
    write_candidate(args.source,args.output)
    print("delegation acceptance overlay prepared")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
