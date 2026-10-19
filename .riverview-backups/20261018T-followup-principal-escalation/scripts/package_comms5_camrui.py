# Riverview Controlled Source
# File: scripts/package_comms5_camrui.py
# Component: COMMS5-CAMRUI-ADAPTER
# Revision: 1.0.1
# Purpose: Create a deterministic immutable package from committed Comms5 files only
# History: New file; no predecessor existed.
"""Build a source-commit-pinned Comms5 Camrui deployment archive."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
from gzip import GzipFile
from pathlib import Path

PACKAGE_FILES = (
    "src/riverview_core/comms5/server.py",
    "src/riverview_core/comms5/dashboard_backend.py",
    "src/riverview_core/comms5/tool_catalog.json",
    "deploy/systemd/riverview-comms5-camrui.service",
    "deploy/systemd/riverview-comms5-tunnel.service",
    "deploy/systemd/riverview-comms5-oauth.service",
    "deploy/comms5/caddy-comms5-oauth-block.caddy",
    "docs/components/COMMS5_CAMRUI_DEPLOYMENT.md",
    "docs/components/COMMS5_CAMRUI_MIGRATION.md",
)


def _git(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], input=input_bytes)


def build(root: Path, output: Path, commit: str | None = None) -> tuple[str, str]:
    root, output = root.resolve(), output.resolve()
    if output.is_relative_to(root):
        raise ValueError("package_output_must_be_outside_checkout")
    if output.exists():
        raise FileExistsError(output)
    if commit is None:
        _git(root, "diff", "--exit-code", "HEAD")
        _git(root, "diff", "--cached", "--exit-code", "HEAD")
        commit = _git(root, "rev-parse", "HEAD").decode().strip()
    else:
        commit = _git(root, "rev-parse", "--verify", commit + "^{commit}").decode().strip()

    tree = _git(root, "ls-tree", "-r", "-z", "--full-tree", commit)
    entries: dict[str, tuple[bytes, int]] = {}
    for record in tree.split(b"\x00"):
        if not record:
            continue
        metadata, path_bytes = record.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        path = path_bytes.decode("utf-8")
        if path not in PACKAGE_FILES:
            continue
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise ValueError("package_entry_must_be_regular_file:" + path)
        entries[path] = (oid, int(mode, 8) & 0o777)
    if set(entries) != set(PACKAGE_FILES):
        missing = sorted(set(PACKAGE_FILES) - set(entries))
        raise ValueError("package_source_files_missing:" + ",".join(missing))

    blob_data = _git(
        root,
        "cat-file",
        "--batch",
        input_bytes=b"".join(entries[path][0] + b"\n" for path in PACKAGE_FILES),
    )
    stream = io.BytesIO(blob_data)
    files: dict[str, tuple[bytes, int]] = {}
    for path in PACKAGE_FILES:
        expected_oid, mode = entries[path]
        header = stream.readline().split()
        if len(header) != 3 or header[:2] != [expected_oid, b"blob"]:
            raise ValueError("git_blob_response_invalid:" + path)
        size = int(header[2])
        data = stream.read(size)
        if len(data) != size or stream.read(1) != b"\n":
            raise ValueError("git_blob_truncated:" + path)
        files[path] = data, mode
    if stream.read():
        raise ValueError("unexpected_git_blob_data")

    manifest = {
        "schema": "rv.comms5.camrui.package.v1",
        "source_commit": commit,
        "files": [
            {"path": path, "size_bytes": len(files[path][0]), "sha256": hashlib.sha256(files[path][0]).hexdigest()}
            for path in PACKAGE_FILES
        ],
    }
    files["COMMS5_PACKAGE.json"] = (json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n", 0o644)
    files["SOURCE_COMMIT"] = ((commit + "\n").encode(), 0o644)
    checksums = "\n".join(
        f"{hashlib.sha256(data).hexdigest()}  {path}"
        for path, (data, _) in files.items()
    ) + "\n"
    files["PACKAGE_SHA256SUMS"] = (checksums.encode(), 0o644)

    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("xb") as raw,
        GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped,
        tarfile.open(fileobj=zipped, mode="w") as archive,
    ):
        for path, (data, mode) in files.items():
            item = tarfile.TarInfo(path)
            item.size = len(data)
            item.mode = mode
            item.uid = item.gid = 0
            item.uname = item.gname = "root"
            item.mtime = 0
            archive.addfile(item, io.BytesIO(data))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return commit, digest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        commit, digest = build(Path(__file__).resolve().parents[1], args.output)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print("source_commit=" + commit)
    print("archive_sha256=" + digest)
    print("archive_path=" + str(args.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
