#!/usr/bin/env python3
"""Check a candidate static bundle is complete before the Nginx alias is switched.

Revision: 1.0.1
Changed: 2026-10-25 UTC | RV-V2-BATCH1-20261025 | Validate the new Settings, resident directory, capability registry, and pinned history asset.
"""
from html.parser import HTMLParser
from pathlib import Path
import sys


class Assets(HTMLParser):
    def __init__(self): super().__init__(); self.paths=[]
    def handle_starttag(self, tag, attrs):
        values=dict(attrs)
        for key in ("src","href"):
            value=values.get(key,"")
            if value.startswith("assets/"): self.paths.append(value.split("?",1)[0])


def main():
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path("website/v2/deployed")
    page=root/"index.html"
    if not page.is_file(): raise SystemExit("FAIL: candidate_index_missing")
    parser=Assets(); parser.feed(page.read_text())
    if not parser.paths: raise SystemExit("FAIL: candidate_assets_missing")
    missing=[name for name in parser.paths if not (root/name).is_file()]
    if missing: raise SystemExit("FAIL: candidate_asset_missing:"+missing[0])
    text=page.read_text()
    for marker in ('data-view="notification-settings"','id="engineering-progress-panel"',
                   'id="resource-monitor-workspace"','id="communications-workspace"',
                   'id="snapshot-action"','data-view="institutional-proposals"',
                   'data-view="process-workflows"','data-view="documentation"',
                   'id="proposal-draft-dialog"','id="graph-canvas"',
                   'data-view="settings"','id="resident-directory-workspace"',
                   'id="capability-registry-workspace"','authority-explorer.js',
                   'proposal-lifecycle-20261025','verification-status.js'):
        if marker not in text: raise SystemExit("FAIL: candidate_contract_missing:"+marker)
    history=root/"assets"/"resident-history-reference.json"
    if not history.is_file(): raise SystemExit("FAIL: candidate_asset_missing:resident-history-reference.json")
    print(f"PASS candidate bundle: {len(parser.paths)} referenced assets present")


if __name__=="__main__": main()
