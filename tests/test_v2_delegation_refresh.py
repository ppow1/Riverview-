from pathlib import Path
# Revision: 1.0.1


def test_delegation_panel_listens_for_workspace_refresh_before_dom_ready():
    source = (Path(__file__).parents[1] / "website/v2/deployed/assets/delegation-approvals.js").read_text()
    workspace = (Path(__file__).parents[1] / "website/v2/deployed/assets/workspace.js").read_text()

    listener = 'window.addEventListener("rv:resident-permissions", refresh);'
    dispatch = 'window.dispatchEvent(new Event("rv:resident-permissions"))'
    assert listener in source
    assert dispatch in workspace
    assert source.index(listener) < source.index('document.addEventListener("DOMContentLoaded"')
    assert 'document.addEventListener("rv:resident-permissions"' not in source


def test_delegation_ui_distinguishes_authentication_authorization_and_service_failures():
    root = Path(__file__).parents[1] / "website/v2/deployed"
    source = (root / "assets/delegation-approvals.js").read_text()
    index = (root / "index.html").read_text()
    assert '"authentication_required"' in source
    assert "Sign in with an authenticated Steward account" in source
    assert '"steward_authority_denied"' in source
    assert "not the institutionally linked Steward" in source
    assert '"delegation_authority_unavailable"' in source
    assert "canonical delegation authority service is unavailable" in source
    assert "delegation-approvals.js?rev=delegation-policy-runtime-repair-20261026d" in index
    assert "delegation-approvals.css?rev=delegation-policy-runtime-repair-20261026b" in index
    assert "Maximum executions (optional with expiry; required without expiry)" in index
    assert '$("delegation-request-max-uses").required = false' in source
    assert '$("delegation-request-expiry-label").hidden = codex' in source
    assert '23 * 60 * 60 * 1000 + 59 * 60 * 1000' in source
    assert "register <code>service:chatgpt</code> as an active <code>service</code> principal" in source
    assert "requires the authenticated Steward's <code>identity.manage</code> authority" in source
    assert "24 hours after activation" in source
    assert 'id="delegation-authorization-type-details"' in index
