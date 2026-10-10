# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_process_graph.py
# Component: RV-PROCESS-GRAPH
# Revision: 1.0.1
# Purpose: Verify global identity, references, typed edges, schema and synchronized views
# Execution Model: Request-driven unittest suite
# Observability: Assertion failures identify violated process graph contract
# Dependencies: Python 3.10+; jsonschema 4.10.3
# Authority: Test-only graph fixtures; no database or service access
# Changed: 2026-10-10 UTC | RV-GRAPH-001 | Initial graph validation regression suite
# Contracts: process_graphs/README.md; process_graphs/schema/riverview-process-graph.schema.json
# Tests: python3 -m unittest tests.test_process_graph -v
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Regression tests for canonical process graph validation and generated views."""

import copy
import unittest

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


if __name__ == "__main__":
    unittest.main()
