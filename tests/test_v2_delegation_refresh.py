from pathlib import Path
# Revision: 1.0.0


def test_delegation_panel_listens_for_workspace_refresh_before_dom_ready():
    source = (Path(__file__).parents[1] / "website/v2/deployed/assets/delegation-approvals.js").read_text()
    workspace = (Path(__file__).parents[1] / "website/v2/deployed/assets/workspace.js").read_text()

    listener = 'window.addEventListener("rv:resident-permissions", refresh);'
    dispatch = 'window.dispatchEvent(new Event("rv:resident-permissions"))'
    assert listener in source
    assert dispatch in workspace
    assert source.index(listener) < source.index('document.addEventListener("DOMContentLoaded"')
    assert 'document.addEventListener("rv:resident-permissions"' not in source
