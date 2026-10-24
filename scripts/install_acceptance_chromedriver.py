#!/usr/bin/env python3
"""Install the ChromeDriver build matching installed Chrome from Google's CFT index.

Revision: 1.0.0
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from io import BytesIO

INDEX="https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
DEST=Path("/usr/local/bin/chromedriver")
ENTRY="chromedriver-linux64/chromedriver"


def cft_url(version: str, metadata: dict) -> str:
    row=next((item for item in metadata.get("versions",[]) if item.get("version")==version),None)
    if not row: raise ValueError("matching_chrome_driver_build_not_published")
    item=next((x for x in row.get("downloads",{}).get("chromedriver",[]) if x.get("platform")=="linux64"),None)
    url=item.get("url") if item else None
    parsed=urllib.parse.urlparse(url or "")
    expected=f"/chrome-for-testing-public/{version}/linux64/chromedriver-linux64.zip"
    if parsed.scheme!="https" or parsed.netloc!="storage.googleapis.com" or parsed.path!=expected:
        raise ValueError("unexpected_chrome_driver_download_url")
    return url


def main() -> int:
    if os.geteuid()!=0: raise SystemExit("FAIL: run as root")
    chrome=shutil.which("google-chrome") or shutil.which("google-chrome-stable")
    if not chrome: raise SystemExit("FAIL: native Chrome is unavailable")
    output=subprocess.check_output([chrome,"--version"],text=True,timeout=10).strip()
    match=re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b",output)
    if not match: raise SystemExit("FAIL: Chrome version could not be determined")
    version=match.group(1)
    if DEST.exists():
        installed=subprocess.run([str(DEST),"--version"],text=True,capture_output=True,timeout=10)
        if installed.returncode==0 and version in installed.stdout:
            print("UNCHANGED",installed.stdout.strip()); return 0
    with urllib.request.urlopen(INDEX,timeout=30) as response:
        metadata=json.load(response)
    url=cft_url(version,metadata)
    with urllib.request.urlopen(url,timeout=60) as response:
        archive_bytes=response.read(32*1024*1024+1)
    if len(archive_bytes)>32*1024*1024: raise SystemExit("FAIL: driver archive exceeds size limit")
    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        if archive.namelist().count(ENTRY)!=1 or archive.testzip() is not None:
            raise SystemExit("FAIL: driver archive structure or checksum invalid")
        binary=archive.read(ENTRY)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    temporary=DEST.with_name(".chromedriver.new")
    with temporary.open("wb") as stream:
        stream.write(binary); stream.flush(); os.fsync(stream.fileno())
    os.chmod(temporary,0o755); os.chown(temporary,0,0); os.replace(temporary,DEST)
    installed=subprocess.run([str(DEST),"--version"],text=True,capture_output=True,timeout=10)
    if installed.returncode or version not in installed.stdout:
        raise SystemExit("FAIL: installed ChromeDriver version did not match Chrome")
    print("INSTALLED",installed.stdout.strip())
    return 0


if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {str(exc)[:100]}",file=sys.stderr)
        raise SystemExit(1)
