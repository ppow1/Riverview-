#!/usr/bin/env python3
# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/validate_capability_declaration_changes.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.0
# Purpose: Require a capability declaration or documented exclusion for added website API operations
# Execution Model: Pull-request diff validation; read-only Git and source inspection
# Authority: Checks dashboard API route additions only; makes no registry or production changes
# Tests: tests/test_capability_declaration_gate.py
# =============================================================================
"""Require declarations or inline exclusions for new website API dispatches.

Scope is the status-dashboard HTTP dispatcher, which hosts the Riverview
website's backend API. UI routes/assets are outside this check. New API route
conditions must carry an inline ``capability-operation`` marker naming a
release-shipped declaration, or a ``capability-exclusion`` marker explaining
why no executable catalog entry is appropriate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


SERVER = "src/riverview_core/status_dashboard/server.py"
DECLARATIONS = Path("src/riverview_core/institutional_authority/capability_declarations")
OPERATION_MARKER = re.compile(r"#\s*capability-operation:\s*([A-Za-z0-9._:-]+)\b")
EXCLUSION_MARKER = re.compile(r"#\s*capability-exclusion:\s*(.*?)\s*$")


def declared_operations(directory: Path) -> set[str]:
    """Load operation and capability identifiers from release declarations."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("capability declaration directory is missing or unsafe")
    result: set[str] = set()
    for path in sorted(directory.iterdir()):
        if path.suffix != ".json" or path.is_symlink() or not path.is_file():
            raise ValueError(f"unsupported capability declaration entry: {path.name}")
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid capability declaration: {path.name}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"invalid capability declaration: {path.name}")
        for key in ("capability_id", "operation"):
            value = item.get(key)
            if isinstance(value, str) and value:
                result.add(value)
    return result


def api_path_symbols(source: str) -> set[str]:
    """Find route constants whose definitions include a website API path."""
    symbols = set()
    for line in source.splitlines():
        if "/api/v1/" not in line:
            continue
        match = re.match(r"\s*([A-Z_][A-Z0-9_]*)\s*=", line)
        if match:
            symbols.add(match.group(1))
    return symbols


def is_api_dispatch(line: str, symbols: set[str]) -> bool:
    """Return true for a status-dashboard route condition targeting an API."""
    if "parsed.path" not in line:
        return False
    if "/api/v1/" in line:
        return True
    return any(re.search(rf"\b{re.escape(symbol)}\b", line) for symbol in symbols)


def validate_added_dispatches(diff: str, known_operations: set[str],
                              source: str = "") -> list[str]:
    """Validate added API dispatch lines from a zero-context Git diff."""
    source_lines = [line[1:] for line in diff.splitlines()
                    if line.startswith("+") and not line.startswith("+++")]
    symbols = api_path_symbols(source)
    errors = []
    for line_number, line in enumerate(source_lines, 1):
        if not is_api_dispatch(line, symbols):
            continue
        operations = OPERATION_MARKER.findall(line)
        exclusions = EXCLUSION_MARKER.findall(line)
        if len(operations) + len(exclusions) != 1:
            errors.append(
                f"added API dispatch diff line {line_number} needs exactly one inline "
                "capability-operation or capability-exclusion marker")
            continue
        if operations and operations[0] not in known_operations:
            errors.append(
                f"added API dispatch diff line {line_number} names undeclared operation "
                f"{operations[0]}")
        elif exclusions and len(exclusions[0].strip()) < 20:
            errors.append(
                f"added API dispatch diff line {line_number} has no meaningful exclusion reason")
    return errors


def check_repository(root: Path, base: str) -> tuple[int, list[str]]:
    declarations = declared_operations(root / DECLARATIONS)
    result = subprocess.run(
        ["git", "diff", "--unified=0", f"{base}...HEAD", "--", SERVER],
        cwd=root, text=True, capture_output=True, check=True)
    source = (root / SERVER).read_text(encoding="utf-8")
    errors = validate_added_dispatches(result.stdout, declarations, source)
    added_routes = sum(
        1 for line in result.stdout.splitlines()
        if line.startswith("+") and not line.startswith("+++")
        and "parsed.path" in line
    )
    return added_routes, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True,
                        help="base ref used for the feature/PR diff, e.g. origin/main")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        added_routes, errors = check_repository(root, args.base)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"capability declaration check failed: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        return 2
    if errors:
        print("capability declaration check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"capability declaration check passed ({added_routes} added API dispatch line(s) checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
