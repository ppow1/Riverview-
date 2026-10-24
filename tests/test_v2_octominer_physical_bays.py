# Revision: 1.0.0
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "website/v2/deployed"


def test_twelve_physical_bays_follow_manufacturer_left_to_right_order():
    html = (WEB / "index.html").read_text()
    buttons = re.findall(r'data-octo-component="bay-(\d+)" style="--image-x:([0-9.]+)%;--image-y:([0-9.]+)%', html)
    assert len(buttons) == 12
    assert [int(number) for number, _, _ in buttons] == list(range(12, 0, -1))
    assert [float(x) for _, x, _ in buttons] == sorted(float(x) for _, x, _ in buttons)
    assert all(0 < float(x) < 100 and 0 < float(y) < 100 for _, x, y in buttons)
    css = (WEB / "assets/resource-monitor.css").read_text()
    assert "aspect-ratio:1565/1568" in css and "object-fit:contain" in css
    assert "left:var(--image-x);top:var(--image-y)" in css
    assert "X12ULTRA_QUICK_START_GUIDE_V.1.pdf.pdf" in html


def test_bay_selection_keeps_physical_gpu_and_pcie_ids_separate_and_unavailable():
    js = (WEB / "assets/resource-monitor.js").read_text()
    html = (WEB / "index.html").read_text()
    assert 'id.startsWith("bay-")' in js
    assert 'state.selected={kind:"bay",id}' in js
    assert 'NVIDIA GPU index' in js and 'PCIe bus address' in js
    assert 'no verified bay-to-device mapping' in js
    assert 'GPU assignment is derived from the live GPU process projection' in html
    assert "GET" in js and 'method:"POST"' not in js and 'method:"PUT"' not in js


def test_visualization_reuses_existing_manufacturer_chassis_asset_and_read_only_telemetry():
    html = (WEB / "index.html").read_text()
    assert (WEB / "assets/octominer/x12ultra-front-open-chassis-reference.png").is_file()
    assert 'id="octo1-chassis-artwork"' in html
    assert 'id="octo1-bay-hotspots"' in html
    assert "Physical GPU bay" in (WEB / "assets/resource-monitor.js").read_text()
    assert "OCTO1 · HARDWARE · INFERENCE" in html


def test_steward_reported_bay_inventory_is_separate_from_coordinates_and_unverified():
    html = (WEB / "index.html").read_text()
    js = (WEB / "assets/resource-monitor.js").read_text()
    inventory = (WEB / "assets/octominer-bay-assignments.js").read_text()
    assert 'assets/octominer-bay-assignments.js?rev=' in html
    assert '"1": Object.freeze({ type: "p100", gpu: "Tesla P100", memory: "16 GB" })' in inventory
    assert '"4": Object.freeze({ type: "p100", gpu: "Tesla P100", memory: "16 GB" })' in inventory
    assert '"10": Object.freeze({ type: "rtx3060ti", gpu: "RTX 3060 Ti", memory: "8 GB" })' in inventory
    assert '"12": Object.freeze({ type: "rtx4090", gpu: "RTX 4090", memory: "24 GB" })' in inventory
    assert 'pendingInstallation: Object.freeze({ gpu: "Tesla P100", memory: "16 GB", bay: null' in inventory
    assert 'Steward-reported assignment; physical installation and bay mapping are not independently verified.' in inventory
    assert 'Reported GPU assignment' in js and 'Assignment provenance' in js
    assert 'NVIDIA GPU index","Unavailable' in js and 'PCIe bus address","Unavailable' in js
    assert "renderBayAssignments();renderSelectionButtons()" in js
"""Focused checks for the read-only X12 Ultra physical bay view."""
