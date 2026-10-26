"""Focused contract checks for the in-place website acceptance extension."""
# Revision: 1.0.4
# Changed: 2026-10-26 UTC | RV-ISSUE268-OBJECTIVE-PROJECTION-ACCEPTANCE | Assert browser-runner projection regression coverage and cancellation eligibility evidence.
from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "delegation_acceptance_overlay", ROOT / "scripts/apply_delegation_acceptance_overlay.py")
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)


RUNNER_FIXTURE = '''            if role == "steward" and proposal_decisions_available: views.append("institutional-proposals")
            if role == "steward":
                stage = "live_overview_projection_acceptance"
            elif role in {"operator","viewer"}:
                denied=js("return fetch('/api/v1/notification-settings',{cache:'no-store'}).then(r=>r.status)")
    report={"schema_version":"rv.website-acceptance.v1","timestamp":timestamp,
            "checks":checks,"overall":"FAIL" if any(x["status"]=="FAIL" for x in checks) else
            ("WARNING" if any(x["status"] in {"WARNING","SKIPPED"} for x in checks) else "PASS")}
    return 1 if report["overall"]=="FAIL" else 0
'''


def test_overlay_adds_authenticated_delegation_and_denial_checks_and_is_idempotent():
    result = overlay.apply(RUNNER_FIXTURE)
    assert overlay.apply(result) == result
    assert 'views.append("resident-permissions")' in result
    assert "delegation_approvals_navigation" in result
    assert "delegation_registration_interface" in result
    assert "#chatgpt-principal-register" in result
    assert '"protected server-side credential store"' in result
    assert "/api/v1/steward/delegation-grant-requests/options" in result
    assert "/api/v1/steward/delegation-grant-requests?status=pending" in result
    assert "/api/v1/steward/delegation-grant-requests?status=approved" in result
    assert "/api/v1/steward/delegation-grant-requests?status=rejected" in result
    assert "/api/v1/steward/delegated-grants?state=active" in result
    assert "/api/v1/steward/delegated-grants?state=all" in result
    assert '"status":"BLOCKED"' in result
    assert '("BLOCKED" if any(x["status"]=="BLOCKED" for x in checks) else' in result
    assert 'return 1 if report["overall"] in {"FAIL","BLOCKED"} else 0' in result
    assert "delegation_unauthorized_" in result
    assert '"check":"work_objectives_projection_available"' in result
    assert "projection_failed" in result
    assert "source unavailable" in result.lower()
    assert '"check":"cancel_objective_action_visible_when_eligible"' in result


def test_overlay_refuses_unknown_or_partially_patched_runner():
    import pytest
    with pytest.raises(ValueError, match="anchor_count"):
        overlay.apply("unrecognized runner source")
    with pytest.raises(ValueError, match="partial"):
        overlay.apply(RUNNER_FIXTURE + '\n"check":"delegation_approvals_navigation"\n')


def test_overlay_upgrades_the_already_deployed_delegation_browser_check():
    legacy = '''                delegation_page = js("""
                    return {visible:true,hostField:true,typeField:true,policyCards:true,
                        refresh:!!document.querySelector('#delegation-refresh')}
                """)
                page_ok=(delegation_page.get("visible") and delegation_page.get("hostField")
                         and delegation_page.get("typeField") and delegation_page.get("policyCards")
                         and delegation_page.get("refresh"))
                results.append({"check":"delegation_approvals_navigation",
                    "status":"PASS" if page_ok else "FAIL"})
'''
    result = overlay.apply(legacy)
    assert "delegation_registration_interface" in result
    assert "registrationButton" in result
    assert "identity.manage" in result
    assert overlay.apply(result) == result
