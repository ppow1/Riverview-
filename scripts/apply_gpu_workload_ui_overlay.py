# Riverview~ Controlled Source
# File: scripts/apply_gpu_workload_ui_overlay.py
# Component: V2-GPU-WORKLOAD-CONTROLS
# Purpose: Add the GPU control panel to an existing deployed V2 index without replacing newer page content
# Execution Model: Explicit file-in/file-out deployment preparation; never mutates live files
# Authority: Presentation-only static overlay
"""Merge the GPU workload panel into a newer deployed V2 HTML snapshot."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path


CSS_ANCHOR = '  <link rel="stylesheet" href="assets/delegation-approvals.css?rev=steward-delegation-refresh-76b02cfb">'
JS_ANCHOR = '  <script defer src="assets/delegation-approvals.js?rev=steward-delegation-refresh-76b02cfb"></script>'
PANEL_ANCHOR = ('                    <p class="resource-footnote">Queue contents are not exposed. ComfyUI CUDA device numbers are separate from host NVIDIA indices and physical chassis bays.</p>\n')
CSS_LINK = '  <link rel="stylesheet" href="assets/gpu-workload-controls.css?rev=gpu-controls-5612bb98">'
JS_LINK = '  <script defer src="assets/gpu-workload-controls.js?rev=gpu-controls-5612bb98"></script>'
PANEL_ID = 'id="gpu-workload-controls"'


class _SectionParser(HTMLParser):
    def __init__(self, html: str):
        super().__init__(convert_charrefs=False)
        self.html = html
        self.offsets = [0]
        for line in html.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.start = None
        self.depth = 0
        self.end = None

    def _offset(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag != "section":
            return
        attributes = dict(attrs)
        if self.start is None and attributes.get("id") == "gpu-workload-controls":
            self.start = self._offset()
            self.depth = 1
        elif self.start is not None:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag == "section" and self.start is not None:
            self.depth -= 1
            if self.depth == 0:
                self.end = self._offset() + len("</section>")


def _panel(feature_html: str) -> str:
    parser = _SectionParser(feature_html)
    parser.feed(feature_html)
    parser.close()
    if parser.start is None or parser.end is None:
        raise ValueError("feature_gpu_panel_not_found_or_unbalanced")
    return feature_html[parser.start:parser.end]


def apply(live_html: str, feature_html: str) -> str:
    if PANEL_ID in live_html:
        if CSS_LINK not in live_html or JS_LINK not in live_html:
            raise ValueError("deployed_gpu_panel_assets_incomplete")
        return live_html
    for anchor in (CSS_ANCHOR, JS_ANCHOR, PANEL_ANCHOR):
        if live_html.count(anchor) != 1:
            raise ValueError("deployed_v2_overlay_anchor_not_unique")
    if live_html.count(CSS_LINK) or live_html.count(JS_LINK):
        raise ValueError("partial_gpu_asset_reference_already_present")
    panel = _panel(feature_html)
    output = live_html.replace(CSS_ANCHOR, CSS_ANCHOR + "\n" + CSS_LINK, 1)
    output = output.replace(JS_ANCHOR, JS_ANCHOR + "\n" + JS_LINK, 1)
    output = output.replace(PANEL_ANCHOR, PANEL_ANCHOR + panel + "\n", 1)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("live_html", type=Path)
    parser.add_argument("feature_html", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    live = args.live_html.read_text(encoding="utf-8")
    feature = args.feature_html.read_text(encoding="utf-8")
    output = apply(live, feature)
    args.destination.write_text(output, encoding="utf-8")
    print(f"panel=installed index_bytes={len(output.encode())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
