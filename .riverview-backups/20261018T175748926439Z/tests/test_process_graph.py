# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_process_graph.py
# Component: RV-PROCESS-GRAPH
# Revision: 1.0.5
# Purpose: Verify global identity, references, typed edges, schema and synchronized views
# Execution Model: Request-driven unittest suite
# Observability: Assertion failures identify violated process graph contract
# Dependencies: Python 3.10+; jsonschema 4.10.3
# Authority: Test-only graph fixtures; no database or service access
# Changed: 2026-10-10 UTC | RV-GRAPH-001 | Initial graph validation regression suite
# Changed: 2026-10-11 UTC | RV-GRAPH-FILE-REVISION-FIX | Verify generation increments file headers without changing body revisions
# Changed: 2026-10-18 UTC | RV-W2-DOD-001 | Verify generated-file backup carries its prospective revision
# Contracts: process_graphs/README.md; process_graphs/schema/riverview-process-graph.schema.json
# Tests: python3 -m unittest tests.test_process_graph -v
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Regression tests for canonical process graph validation and generated views."""

import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scripts.process_graph as process_graph


class ProcessGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graphs, cls.nodes = process_graph.load_and_validate()

    def changed_graphs(self):
        return copy.deepcopy(self.graphs)

    def test_all_graphs_match_json_schema_and_have_globally_unique_ids(self):
        graphs, nodes = process_graph.load_and_validate()
        self.assertEqual(len(nodes), sum(len(graph["nodes"]) for _, graph in graphs))
        self.assertGreaterEqual(len(graphs), 4)

    def test_revision_backup_forwards_prospective_revision(self):
        with patch("revision_control.backup") as backup:
            process_graph.revision_backup(Path(process_graph.ROOT / "docs/example.md"), "TEST", "1.0.1")
        backup.assert_called_once_with(process_graph.ROOT, "docs/example.md", "TEST", new_revision="1.0.1")
        self.assertIn("rv:runtime-baseline:commissioning", {graph["graph_id"] for _, graph in graphs})
        self.assertIn("rv:postgres-ledger:migration", {graph["graph_id"] for _, graph in graphs})

    def test_duplicate_global_node_identity_fails(self):
        graphs = self.changed_graphs()
        graphs[0][1]["nodes"].append(copy.deepcopy(graphs[0][1]["nodes"][0]))
        with self.assertRaisesRegex(process_graph.GraphError, "duplicate global node ID"):
            process_graph.validate_graphs(graphs)

    def test_unresolved_edge_reference_fails(self):
        graphs = self.changed_graphs()
        graphs[1][1]["edges"].append({"from": graphs[1][1]["nodes"][0]["id"], "to": "rv:missing:graph:node", "type": "runtime_transition"})
        with self.assertRaisesRegex(process_graph.GraphError, "unresolved edge target"):
            process_graph.validate_graphs(graphs)

    def test_unsupported_edge_type_fails(self):
        graphs = self.changed_graphs()
        graphs[1][1]["edges"][0]["type"] = "invented"
        with self.assertRaisesRegex(process_graph.GraphError, "not valid under any"):
            process_graph.validate_graphs(graphs)

    def test_broken_cross_component_jump_fails(self):
        graphs = self.changed_graphs()
        jump = next(node for _, graph in graphs for node in graph["nodes"] if node["type"] == "jump")
        jump["jump_target_id"] = "rv:missing:workflow:destination"
        owner = next(graph for _, graph in graphs if jump in graph["nodes"])
        edge = next(edge for edge in owner["edges"] if edge["type"] == "jump" and edge["from"] == jump["id"])
        edge["to"] = jump["jump_target_id"]
        with self.assertRaisesRegex(process_graph.GraphError, "unresolved edge target"):
            process_graph.validate_graphs(graphs)

    def test_extension_types_are_forward_compatible(self):
        graphs = self.changed_graphs()
        graphs[0][1]["nodes"][0]["type"] = "x-riverview:checkpoint"
        process_graph.validate_graphs(graphs)

    def test_runtime_transitions_cannot_impersonate_cross_component_dependencies(self):
        graphs = self.changed_graphs()
        source = graphs[0][1]["nodes"][0]["id"]
        target = graphs[1][1]["nodes"][0]["id"]
        graphs[0][1]["edges"].append({"from": source, "to": target, "type": "runtime_transition"})
        with self.assertRaisesRegex(process_graph.GraphError, "cannot cross workflow/component"):
            process_graph.validate_graphs(graphs)

    def test_generated_json_and_mermaid_views_are_synchronized(self):
        result = process_graph.generate(check=True)
        self.assertEqual(result["status"], "PASS")

    def test_aggregate_mermaid_is_a_workflow_overview_with_jump_links(self):
        source = process_graph.MASTER_MD.read_text(encoding="utf-8")
        self.assertIn("RUNTIME-BASELINE", source)
        self.assertIn("POSTGRES-LEDGER", source)
        self.assertIn("STEWARD-DASHBOARD", source)
        self.assertNotIn("rv:event-processor:assignment-progression:start", source)
        self.assertIn("prerequisite", source)
        self.assertIn("jump", source)

    def test_json_sidecar_checksum_is_enforced(self):
        sidecar = {"files": {"graph.json": {"revision": "1.0.0", "sha256": "0" * 64, "size_bytes": 5}}}
        with self.assertRaisesRegex(process_graph.GraphError, "checksum mismatch"):
            process_graph.validate_sidecar_entry("graph.json", b"{}", sidecar)

    def test_generated_flow_increments_file_revision_not_body_revision(self):
        with tempfile.TemporaryDirectory(dir=process_graph.ROOT) as directory:
            path = Path(directory) / "flow.md"
            old = "<!--\nFile Revision: 1.2.3\n-->\n\n**Document Revision:** 9.8.7\nold view\n"
            path.write_text(old, encoding="utf-8")
            new = old.replace("old view", "new view")
            with patch.object(process_graph, "revision_backup") as backup:
                process_graph.write_markdown_output(path, new)
            result = path.read_text(encoding="utf-8")
            self.assertIn("File Revision: 1.2.4", result)
            self.assertIn("**Document Revision:** 9.8.7", result)
            backup.assert_called_once()

    def test_generated_aggregate_increments_document_revision(self):
        with tempfile.TemporaryDirectory(dir=process_graph.ROOT) as directory:
            path = Path(directory) / "aggregate.md"
            old = "**Document Revision:** 2.4.8\nold view\n"
            path.write_text(old, encoding="utf-8")
            new = old.replace("old view", "new view")
            with patch.object(process_graph, "revision_backup"):
                process_graph.write_markdown_output(path, new)
            self.assertIn("**Document Revision:** 2.4.9", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
