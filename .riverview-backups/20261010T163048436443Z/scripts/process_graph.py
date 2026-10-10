# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/process_graph.py
# Component: RV-PROCESS-GRAPH
# Revision: 1.0.2
# Purpose: Validate canonical workflow graphs and generate synchronized views
# Execution Model: Request-driven developer utility and CI check
# Observability: Structured validation errors and generated graph inventory
# Dependencies: Python 3.10+; jsonschema 4.10.3
# Authority: Reads repository graph data; writes only registered generated views
# Changed: 2026-10-10 UTC | RV-GRAPH-001 | Initial canonical graph pipeline
# Contracts: process_graphs/README.md; process_graphs/schema/riverview-process-graph.schema.json
# Tests: tests/test_process_graph.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Validate Riverview's canonical process graphs and generate Mermaid views."""

import argparse
import copy
import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
GRAPH_DIR = ROOT / "process_graphs"
SCHEMA_PATH = GRAPH_DIR / "schema/riverview-process-graph.schema.json"
REVISION_MANIFEST = ROOT / ".riverview-revisions.json"
MASTER_JSON = GRAPH_DIR / "generated/riverview-process-graph.json"
MASTER_MD = GRAPH_DIR / "generated/RIVERVIEW_PROCESS_GRAPH.md"
MERMAID_BLOCK = re.compile(r"```mermaid\n.*?\n```", re.DOTALL)
BUILTIN_NODE_TYPES = {"process", "entry", "exit", "decision", "measurement", "failure", "recovery", "verification", "jump", "escalation"}
BUILTIN_EDGE_TYPES = {"runtime_transition", "prerequisite", "diagnostic_branch", "recovery_route", "verification", "jump", "escalation", "documentation"}
EXTENSION_TYPE = re.compile(r"^x-[a-z0-9.-]+:[A-Za-z0-9._-]+$")


class GraphError(ValueError):
    """A graph violates the universal process graph contract."""


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def graph_paths():
    return sorted(path for path in GRAPH_DIR.glob("*/*.json")
                  if path.is_file() and path.parent.name not in {"schema", "generated"})


def validate_sidecar_entry(rel, data, manifest):
    entry = manifest.get("files", {}).get(rel)
    if not isinstance(entry, dict) or not re.fullmatch(r"\d+\.\d+\.\d+", str(entry.get("revision", ""))):
        raise GraphError(f"JSON file revision sidecar is missing or invalid: {rel}")
    import hashlib
    if entry.get("sha256") != hashlib.sha256(data).hexdigest() or entry.get("size_bytes") != len(data):
        raise GraphError(f"JSON file revision sidecar checksum mismatch: {rel}")


def validate_json_sidecar(path):
    if not REVISION_MANIFEST.is_file():
        raise GraphError("controlled JSON revision sidecar is missing")
    validate_sidecar_entry(path.relative_to(ROOT).as_posix(), path.read_bytes(),
                           read_json(REVISION_MANIFEST))


def validate_graphs(graphs):
    schema = read_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    nodes = {}
    graph_by_id = {}
    for path, graph in graphs:
        errors = sorted(validator.iter_errors(graph), key=lambda error: list(error.path))
        if errors:
            raise GraphError(f"{path.relative_to(ROOT)}: {errors[0].message}")
        if graph["graph_id"] in graph_by_id:
            raise GraphError(f"duplicate graph ID: {graph['graph_id']}")
        graph_by_id[graph["graph_id"]] = graph
        prefix = graph["graph_id"] + ":"
        for node in graph["nodes"]:
            node_id = node["id"]
            if not node_id.startswith(prefix):
                raise GraphError(f"node ID is outside its workflow namespace: {node_id}")
            if node_id in nodes:
                raise GraphError(f"duplicate global node ID: {node_id}")
            nodes[node_id] = (graph, node)
            if node["type"] not in BUILTIN_NODE_TYPES and not EXTENSION_TYPE.fullmatch(node["type"]):
                raise GraphError(f"unrecognized, unnamespaced node extension: {node['type']}")
        for ref in graph["source_references"] + graph["documentation_references"] + graph["verification_evidence"]:
            if not (ROOT / ref).is_file():
                raise GraphError(f"unresolved graph reference in {path.relative_to(ROOT)}: {ref}")
    for path, graph in graphs:
        graph_nodes = {node["id"]: node for node in graph["nodes"]}
        jumps = {node["id"]: node["jump_target_id"] for node in graph["nodes"] if node["type"] == "jump"}
        jump_edges = set()
        for edge in graph["edges"]:
            edge_type = edge["type"]
            if edge_type not in BUILTIN_EDGE_TYPES and not EXTENSION_TYPE.fullmatch(edge_type):
                raise GraphError(f"unrecognized, unnamespaced edge extension: {edge_type}")
            if edge["from"] not in graph_nodes:
                raise GraphError(f"edge source must be local to {graph['graph_id']}: {edge['from']}")
            if edge["to"] not in nodes:
                raise GraphError(f"unresolved edge target: {edge['to']}")
            target_graph, _ = nodes[edge["to"]]
            if edge_type == "runtime_transition" and target_graph is not graph:
                raise GraphError("runtime transition cannot cross workflow/component boundaries")
            if edge_type == "jump":
                source_node = graph_nodes[edge["from"]]
                if source_node["type"] != "jump" or jumps.get(edge["from"]) != edge["to"]:
                    raise GraphError(f"jump edge must resolve its jump node target: {edge['from']} -> {edge['to']}")
                jump_edges.add(edge["from"])
            elif graph_nodes[edge["from"]]["type"] == "jump":
                raise GraphError(f"jump node must use an explicit jump edge: {edge['from']}")
        for node_id, target_id in jumps.items():
            if target_id not in nodes:
                raise GraphError(f"unresolved cross-component jump target: {node_id} -> {target_id}")
            target_graph, _ = nodes[target_id]
            if target_graph["component_id"] == graph["component_id"]:
                raise GraphError(f"jump target must cross components: {node_id} -> {target_id}")
            if node_id not in jump_edges:
                raise GraphError(f"jump target lacks typed jump edge: {node_id}")
        for node in graph["nodes"]:
            for ref in node["source_references"] + node["documentation_references"] + node["verification_evidence"]:
                if not (ROOT / ref).is_file():
                    raise GraphError(f"unresolved node reference {node['id']}: {ref}")
    return graphs, nodes


def load_and_validate():
    validate_json_sidecar(SCHEMA_PATH)
    graphs = [(path, read_json(path)) for path in graph_paths()]
    for path, _ in graphs:
        validate_json_sidecar(path)
    return validate_graphs(graphs)


def aggregate(graphs):
    return {
        "graph_schema": "RiverviewProcessGraph/1.0.0",
        "aggregate_id": "rv:riverview:all-workflows",
        "graphs": [graph for _, graph in graphs],
        "node_registry": sorted(node_id for _, graph in graphs for node_id in (node["id"] for node in graph["nodes"])),
    }


def mermaid(graphs, title="Riverview process graph"):
    lines = ["flowchart LR"]
    index = 0
    aliases = {}
    for _, graph in graphs:
        lines.append(f"  subgraph {safe_id(graph['graph_id'])}[\"{escape(graph['component_id'] + ' / ' + graph['workflow_id'])}\"]")
        for node in graph["nodes"]:
            alias = f"n{index}"
            index += 1
            aliases[node["id"]] = alias
            label = escape(node["label"] + "<br/>" + node["id"])
            if node["type"] == "decision":
                lines.append(f"    {alias}{{\"{label}\"}}")
            elif node["type"] in {"entry", "exit"}:
                lines.append(f"    {alias}([\"{label}\"])")
            elif node["type"] in {"failure", "escalation"}:
                lines.append(f"    {alias}[[\"{label}\"]]")
            else:
                lines.append(f"    {alias}[\"{label}\"]")
        lines.append("  end")
    for _, graph in graphs:
        for edge in graph["edges"]:
            if edge["to"] not in aliases:
                alias = f"n{index}"
                index += 1
                aliases[edge["to"]] = alias
                lines.append(f"  {alias}[\"External graph target<br/>{escape(edge['to'])}\"]")
    for _, graph in graphs:
        for edge in graph["edges"]:
            label = edge.get("label", "")
            if edge["type"] != "runtime_transition":
                label = (edge["type"] + (": " + label if label else ""))
            suffix = f"|{escape(label)}|" if label else ""
            lines.append(f"  {aliases[edge['from']]} -->{suffix} {aliases[edge['to']]}")
    lines.append("  classDef failure fill:#fee,stroke:#b00,stroke-width:2px")
    return "\n".join(lines)


def safe_id(value):
    return "g_" + re.sub(r"[^A-Za-z0-9_]", "_", value)


def escape(value):
    return value.replace('"', "'").replace("|", "/").replace("\n", " ")


def bump(value):
    major, minor, patch = (int(part) for part in value.split("."))
    return f"{major}.{minor}.{patch + 1}"


def revision_backup(path, task):
    sys.path.insert(0, str(ROOT / "scripts"))
    import revision_control
    revision_control.backup(ROOT, path.relative_to(ROOT).as_posix(), task)


def write_json_output(path, data, manifest):
    rel = path.relative_to(ROOT).as_posix()
    content = (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode()
    previous = path.read_bytes() if path.exists() else None
    if previous == content:
        return False
    if previous is not None:
        revision_backup(path, "RV-GRAPH-GENERATE")
        manifest["files"][rel]["revision"] = bump(manifest["files"][rel]["revision"])
    else:
        manifest["files"][rel] = {"revision": "1.0.0"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    manifest["files"][rel].update({"path": rel, "sha256": __import__("hashlib").sha256(content).hexdigest(),
                                   "size_bytes": len(content)})
    return True


def write_markdown_output(path, content, task="RV-GRAPH-GENERATE"):
    if path.exists():
        old = path.read_text(encoding="utf-8")
        if old == content:
            return False
        revision_backup(path, task)
        match = re.search(r"(?m)^(\*\*(?:Document )?Revision:\*\*\s*)(\d+\.\d+\.\d+)", content)
        old_match = re.search(r"(?m)^(\*\*(?:Document )?Revision:\*\*\s*)(\d+\.\d+\.\d+)", old)
        if old_match and match:
            content = content[:match.start(2)] + bump(old_match.group(2)) + content[match.end(2):]
        elif old_match:
            raise GraphError(f"cannot increment document revision: {path.relative_to(ROOT)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def diagram_views(graphs):
    docs = {}
    for path, graph in graphs:
        for ref in graph["documentation_references"]:
            if ref.endswith("_FLOW.md"):
                docs.setdefault(ref, []).append((path, graph))
    output = {}
    for doc_ref, values in docs.items():
        doc = ROOT / doc_ref
        source = doc.read_text(encoding="utf-8")
        blocks = list(MERMAID_BLOCK.finditer(source))
        ordered = sorted(values, key=lambda item: (item[1].get("diagram_order", 1), item[1]["workflow_id"]))
        if len(blocks) != len(ordered):
            raise GraphError(f"diagram count mismatch for {doc_ref}: {len(blocks)} Mermaid blocks, {len(ordered)} registered graphs")
        rendered = source
        for block, (_, graph) in reversed(list(zip(blocks, ordered))):
            generated = "```mermaid\n" + mermaid([(None, graph)]) + "\n```"
            rendered = rendered[:block.start()] + generated + rendered[block.end():]
        output[doc] = rendered
    return output


def generate(check=False):
    graphs, _ = load_and_validate()
    aggregate_data = aggregate(graphs)
    markdown = diagram_views(graphs)
    master_body = mermaid(graphs)
    current_master = MASTER_MD.read_text(encoding="utf-8") if MASTER_MD.is_file() else ""
    current_revision = re.search(r"(?m)^\*\*Document Revision:\*\*\s*(\d+\.\d+\.\d+)", current_master)
    master_revision = current_revision.group(1) if current_revision else "1.0.0"
    master = (
        "# Riverview aggregate process graph\n\n"
        f"**Document Revision:** {master_revision}  \n"
        "**Generated from:** canonical workflow JSON; do not edit this projection by hand.  \n"
        "**Source:** `python3 scripts/process_graph.py generate`  \n\n"
        "The graph is complete across registered workflows. Use focused component flow documents for detailed reading. "
        "Unimplemented roadmap integration points are explicitly labeled planned.\n\n"
        "```mermaid\n" + master_body + "\n```\n"
    )
    if check:
        mismatches = []
        validate_json_sidecar(MASTER_JSON)
        if not MASTER_JSON.is_file() or read_json(MASTER_JSON) != aggregate_data:
            mismatches.append(MASTER_JSON.relative_to(ROOT).as_posix())
        if not MASTER_MD.is_file() or MASTER_MD.read_text(encoding="utf-8") != master:
            mismatches.append(MASTER_MD.relative_to(ROOT).as_posix())
        for path, expected in markdown.items():
            if path.read_text(encoding="utf-8") != expected:
                mismatches.append(path.relative_to(ROOT).as_posix())
        if mismatches:
            raise GraphError("generated views are stale: " + ", ".join(mismatches))
        return {"graphs": len(graphs), "nodes": len(aggregate_data["node_registry"]), "status": "PASS"}

    manifest = read_json(REVISION_MANIFEST) if REVISION_MANIFEST.exists() else {"manifest_revision": "1.0.0", "files": {}}
    manifest["files"] = {path: (value if isinstance(value, dict) else {"revision": value})
                          for path, value in manifest.get("files", {}).items()}
    changed = []
    if write_json_output(MASTER_JSON, aggregate_data, manifest):
        changed.append(MASTER_JSON.relative_to(ROOT).as_posix())
    for path, expected in markdown.items():
        if write_markdown_output(path, expected):
            changed.append(path.relative_to(ROOT).as_posix())
    if not MASTER_MD.exists() or MASTER_MD.read_text(encoding="utf-8") != master:
        write_markdown_output(MASTER_MD, master)
        changed.append(MASTER_MD.relative_to(ROOT).as_posix())
    tracked_json = [SCHEMA_PATH, *graph_paths(), MASTER_JSON]
    for path in tracked_json:
        rel = path.relative_to(ROOT).as_posix()
        if rel not in manifest["files"]:
            manifest["files"][rel] = {"revision": "1.0.0"}
        content = path.read_bytes()
        manifest["files"][rel].update({"path": rel, "sha256": __import__("hashlib").sha256(content).hexdigest(),
                                        "size_bytes": len(content)})
    if ".riverview-revisions.json" not in manifest["files"]:
        manifest["files"][".riverview-revisions.json"] = {"revision": manifest["manifest_revision"]}
    else:
        manifest["files"][".riverview-revisions.json"]["revision"] = manifest["manifest_revision"]
    if REVISION_MANIFEST.exists():
        existing = read_json(REVISION_MANIFEST)
        if existing != manifest:
            revision_backup(REVISION_MANIFEST, "RV-GRAPH-GENERATE")
            manifest["manifest_revision"] = bump(existing["manifest_revision"])
            manifest["files"][".riverview-revisions.json"]["revision"] = manifest["manifest_revision"]
    REVISION_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"graphs": len(graphs), "nodes": len(aggregate_data["node_registry"]), "changed": changed, "status": "GENERATED"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "generate", "check"))
    args = parser.parse_args()
    try:
        result = generate(check=args.command == "check") if args.command != "validate" else {
            "graphs": len(load_and_validate()[0]), "status": "PASS"}
        print(json.dumps(result, indent=2))
        return 0
    except (GraphError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
