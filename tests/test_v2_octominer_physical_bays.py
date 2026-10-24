from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "website/v2/deployed"


def test_twelve_physical_bays_follow_manufacturer_left_to_right_order():
    html = (WEB / "index.html").read_text()
    buttons = re.findall(r'data-octo-component="bay-(\d+)" style="--hotspot-x:([0-9.]+)%', html)
    assert len(buttons) == 12
    assert [int(number) for number, _ in buttons] == list(range(12, 0, -1))
    assert [float(x) for _, x in buttons] == sorted(float(x) for _, x in buttons)
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
"""Focused checks for the read-only X12 Ultra physical bay view."""
