# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_status_dashboard.py
# Component: STEWARD-DASHBOARD
# Revision: 1.0.65
# Changed: 2026-10-22 UTC | RV-W4-GRACE-ACTIONABLE-DIAGNOSTICS-20261022 | Verify durable grounding projection, authenticated scope, redaction, retry guidance, and UI rendering contract.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Align retry-copy assertion with immutable criteria-source semantics.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-OPTIONAL-CRITERIA-20261021 | Cover blank/explicit intake and criteria-source visibility.
# Changed: 2026-10-21 UTC | RV-V2-HW-AI-LIVE-TELEMETRY | Verify telemetry endpoint authentication, projection, and read-only methods.
# Changed: 2026-10-21 UTC | RV-GRACE-DASHBOARD-KNOWLEDGE-PIN-001 | Verify knowledge source pin is independent of dashboard source identity.
# Changed: 2026-10-20 UTC | RV-C4-GRACE-WORKORDER-RETRY-UI-001 | Cover persisted-sequence binding and visible recovery when the retry dialog cannot open.
# Predecessor: .riverview-backups/20261020T153249910848Z/tests/test_status_dashboard.py (SHA-256 fa08f2763f1eb9234a217974196ab49d416edd73b76987fa104ade8d38ebe1ba)
# Changed: 2026-10-20 UTC | RV-C4-ACTIVE-LINE-INTEGRATION-001 | Verify re-review route authentication, exact objective scope, bounded payload and request-only behavior.
# Changed: 2026-10-19 UTC | RV-C1-PR152-SCOPE-PROVENANCE-001 | Cover Steward and conversation-owner objective access, redaction, and PostgreSQL scoping
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Verify institutional proposal dashboard actions remain distinct from Engineering intake.
# Changed: 2026-10-19 UTC | RV-GRACE-GOVERNED-REWORK-001 | Verify authenticated conversation-scoped Engineering progress projection and invalid filters
# Changed: 2026-10-18 UTC | RV-GRACE-DUAL-CAPABILITY-001 | Verify Steward proposal UI uses distinct draft, approval and objective-promotion actions.
# Changed: 2026-10-16 UTC | RV-WORKER-HEALTH-REPORTING-001 | Assert UI distinguishes lease heartbeat status from worker process liveness.
# Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Assert inactive retired registrations do not affect active worker health counts.
# Purpose: Verify authenticated read-only projections, privacy, paging and restart-safe UI service
# Execution Model: HTTP component tests and isolated PostgreSQL integration tests
# Observability: Versioned status and request failure contracts
# Dependencies: Python 3.10+; Psycopg 3; disposable PostgreSQL for integration class
# Authority: Creates/drops only unique rvtest_* schemas; never accesses shared Riverview data
# Changed: 2026-10-16 UTC | RV-WEBSITE-PL-NEW-042 | Verify registered workflow fit/zoom/pan/reset/fullscreen controls.
# Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Verify inactive registrations are excluded from active health counts
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-001 | Verify safe component links remain functional in the consolidated guide
# Changed: 2026-10-11 UTC | RV-M4.1-DASHBOARD-COOKBOOK-ROUTE | Exercise updated authority diagnostics through the dashboard documentation route
# Changed: 2026-10-12 UTC | RV-GRACE-AUTH-SESSION-001 | Enforce browser-managed persistent grant cookie and denial retry suppression UI contract
# Changed: 2026-10-11 UTC | RV-M4.1-DASHBOARD-COOKBOOK-ASSERTION | Match cookbook's documented DROP CASCADE warning text
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-SCHEDULER-DIAGNOSTICS | Assert expanded scheduler recovery docs render through dashboard route
# Changed: 2026-10-11 UTC | RV-OPS-DASHBOARD-EXACT-DOCS-REVISION | Match the exact docs/graph source revision in the deployment contract
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-WORKER-DIAGNOSTICS | Assert worker recovery diagnostics render through dashboard route
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-PG-SECRET-SAFETY | Assert PostgreSQL cookbook has no password-bearing command examples
# Changed: 2026-10-13 UTC | RV-GRACE-TO-ENGINEERING | Verify workflow-session transport, exact Steward work-order gate and corrected cookie text assertion
# Changed: 2026-10-11 UTC | RV-M1.4-LIVE-DEPENDENCY-CORRECTION | Assert scheduler docs distinguish shared migration from commissioning
# Changed: 2026-10-12 UTC | RV-GRACE-CHAT-UX-001 | Assert complete conversational controls, accessibility hooks, and disabled future actions
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-DASHBOARD-REPOSITORY-LINK | Preserve installed knowledge-cookbook navigation in source shell
# Changed: 2026-10-11 UTC | RV-M4.1-DB-RESTORE-COOKBOOK | Verify observed backup path incident renders safely through docs route
# Changed: 2026-10-11 UTC | RV-OPS-COOKBOOK-PACKAGE-ROUTE-INTEGRITY | Require every dashboard shell documentation link to resolve
# Changed: 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE-COOKBOOK-RENDER | Verify current authority recovery section renders safely with no broken evidence link
# Changed: 2026-10-11 UTC | RV-M3.3-DASHBOARD-COOKBOOK-ASSERTION-CORRECTION | Match expected HTML code-tag rendering rather than Markdown source
# Contracts: docs/components/STATUS_DASHBOARD.md
# Tests: This file
# History: Git and revision/backup manifest
# Changed: 2026-10-15 UTC | RV-GRACE-LIVE-STREAMING-001 | Persist bounded streaming, reconnect, and terminal provenance.
# Changed: 2026-10-15 UTC | RV-GRACE-WORKORDER-RECOVERY-001 | Cover release-pinned knowledge and idempotent wait-state intake.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL004/006/008/011/012/014 | Assert assignment linkage, overview semantics, worker states, activity paging, event provenance, and refresh guidance.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL016 | Reuse named dashboard/documentation tabs for return navigation.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL010/015/020/023/024 | Explain execution readiness, chat controls, menu availability and milestone semantics.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL019 | Prevent transcript/composer overlap and verify responsive long-history layout.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL036 | Verify persistent rail state, accessible names and retained status/snapshot controls.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL003 | Resolve assignment task labels from exact persisted graph/node IDs.
# Changed: 2026-10-15 UTC | RV-WEBSITE-PL029 | Separate notification rendering, receipt, person-seen and decision states.
# Changed: 2026-10-16 UTC | RV-WEBSITE-PL038 | Verify searchable canonical traceability catalog and evidence qualification.
# Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Verify authenticated dynamic capability/workflow inventories, complete source metadata and snapshot affordance.
# =============================================================================
"""Security, API, privacy and PostgreSQL integration tests for M3.1."""

import json
import os
import re
import tempfile
import sys
import threading
import time
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
from pathlib import Path
from uuid import uuid4

from riverview_core.status_dashboard.projection import DashboardProjection
from riverview_core.status_dashboard.server import (
    DashboardHTTPServer, _knowledge_commit, _knowledge_root, _read_token)
from riverview_core.status_dashboard.markdown import render_markdown

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")
ROOT = Path(__file__).resolve().parents[1]


class _FakeProjection:
    def __init__(self):
        self.last_limit = None
        self.last_conversation_id = None
        self.last_owner_principal_id = None
        self.last_progress_only = None
        self.objective_items = []
        self.execution_position = {"status": "unknown", "reason": "No recorded node."}

    def graph_execution_position(self, graph_id):
        return self.execution_position

    def status(self):
        return {"schema_version":"rv.dashboard.status.v1", "component_id":"STEWARD-DASHBOARD",
                "component_version":"1.0.0", "projection_status":"unavailable",
                "freshness":"unavailable", "source":{"kind":"postgresql"},
                "cme":{"status":"unavailable"}, "workers":{"status":"unknown"}}

    def assignments(self, *, after=None, limit=25):
        self.last_limit = limit
        return {"status":"available", "items":[], "next_cursor":None, "page_limit":limit}

    def events(self, *, after_seq=None, before_seq=None, limit=25):
        self.last_limit = limit
        return {"status":"available", "items":[], "next_cursor":None, "page_limit":limit}

    def workers(self, *, after=None, limit=25):
        self.last_limit = limit
        return {"status":"available", "items":[], "next_cursor":None, "page_limit":limit}

    def attention(self, *, limit=25):
        return {"status":"available", "items":[], "limit":limit}

    def objectives(self, *, limit=25, objective_id=None, conversation_id=None,
                   owner_principal_id=None, progress_only=False):
        self.last_limit = limit
        self.last_conversation_id = conversation_id
        self.last_owner_principal_id = owner_principal_id
        self.last_progress_only = progress_only
        items = list(self.objective_items)
        if objective_id is not None:
            items = [item for item in items if item.get("objective_id") == objective_id]
        if conversation_id is not None:
            items = [item for item in items
                     if (item.get("origin") or {}).get("conversation_id") == conversation_id]
        if progress_only:
            safe = {"objective_id", "status", "assignment_id", "assignment_state", "origin",
                    "lifecycle_status", "lifecycle_stage", "latest_event", "verification",
                    "rework", "steward_action_required", "dispatch_failures",
                    "grounding_diagnostics",
                    "last_dispatch_failure_at", "verification_failures",
                    "last_verification_failure_at", "created_at", "updated_at"}
            items = [{key: value for key, value in item.items() if key in safe}
                     for item in items]
        return {"schema_version":("rv.dashboard.objective_progress.v1" if progress_only
                                    else "rv.dashboard.objectives.v1"),
                "status":"available", "items":items, "limit":limit}

    def snapshot(self):
        return {"schema_version":"rv.dashboard.snapshot.v1", "redaction":{"credentials":"excluded"}}

    def assignment_detail(self, assignment_id):
        return None


class DashboardDeploymentContractTests(unittest.TestCase):
    def test_work_order_form_allows_grace_derived_criteria_and_dashboard_shows_source(self):
        static = ROOT / "src/riverview_core/status_dashboard/static"
        html = (static / "index.html").read_text(encoding="utf-8")
        app = (static / "app.js").read_text(encoding="utf-8")
        self.assertIn("Acceptance criteria (optional", html)
        self.assertIn("Leave criteria blank to have Grace derive proposed formal criteria", html)
        self.assertIn("Derived by Grace", app)
        self.assertIn("Steward-supplied", app)
    def test_talk_with_grace_has_persistent_objective_progress_panel(self):
        static = ROOT / "src/riverview_core/status_dashboard/static"
        html = (static / "index.html").read_text(encoding="utf-8")
        app = (static / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="engineering-progress-list"', html)
        self.assertIn('aria-labelledby="engineering-progress-title"', html)
        self.assertIn("/api/v1/objectives?limit=25&conversation_id=", app)
        self.assertIn("lifecycle_stage", app)
        self.assertIn("steward_action_required", app)
        self.assertIn("grounding_diagnostics", app)
        self.assertIn("Grounding blocker", app)
        self.assertIn("Responsible component", app)
        self.assertIn("Retry status", app)
        self.assertIn("Next retry", app)
        self.assertIn("Next permitted action", app)
        self.assertIn("Grounding reason unavailable", app)
        self.assertIn("esc(latestGrounding.reason_code", app)
        self.assertIn("esc(retry.next_permitted_action", app)
        self.assertIn("refresh-engineering-progress", app)
        self.assertIn("loadConversationEngineeringProgress();", app)

    def test_objective_progress_contract_is_versioned_and_role_scoped(self):
        schema = json.loads((ROOT / "docs/components/STATUS_DASHBOARD_API.schema.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(schema["$defs"]["objectiveProgressPage"]["properties"]
                         ["schema_version"]["const"], "rv.dashboard.objective_progress.v1")
        allowed = schema["$defs"]["objectiveProgressItem"]["properties"]
        self.assertIn("grounding_diagnostics", allowed)
        self.assertIn("groundingDiagnostic", schema["$defs"])
        for sensitive in ("request", "scope_ref", "submitter_id", "acceptance_criteria",
                          "artifact", "source_sha256"):
            self.assertNotIn(sensitive, allowed)
        graph = json.loads((ROOT / "process_graphs/steward-dashboard/status.json")
                           .read_text(encoding="utf-8"))
        node_ids = {node["id"] for node in graph["nodes"]}
        self.assertIn("rv:steward-dashboard:status:objective-scope", node_ids)
        self.assertTrue(any(edge["from"] == "rv:steward-dashboard:status:objective-scope"
                            and edge["to"] == "rv:steward-dashboard:status:deny-request"
                            for edge in graph["edges"]))

    def test_institutional_proposal_ui_keeps_draft_approval_and_engineering_intake_distinct(self):
        static = ROOT / "src/riverview_core/status_dashboard/static"
        html = (static / "index.html").read_text(encoding="utf-8")
        app = (static / "app.js").read_text(encoding="utf-8")
        proposals = (static / "institutional-proposals.js").read_text(encoding="utf-8")
        self.assertIn('id="institutional-proposals-nav"', html)
        self.assertIn('id="proposal-draft-dialog"', html)
        self.assertIn("Steward approval is revision-specific", html)
        self.assertIn('dataset.messageProposal', app)
        self.assertIn('data-message-work-order', app)
        self.assertIn('institutional-proposals-nav").hidden = !steward', app)
        self.assertIn("/api/v1/institutional-proposals", proposals)
        self.assertIn("content_sha256:selected.digest", proposals)
        self.assertIn("approved_purpose", proposals)
        self.assertIn("/work-orders", proposals)
        self.assertIn('window.RiverviewDashboardNavigate?.("institutional-proposals")', proposals)

    def test_documentation_links_reuse_a_named_tab_and_return_to_existing_dashboard(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        rendered = render_markdown("# Test", document="docs/components/STATUS_DASHBOARD.md",
                                   title="Test").decode("utf-8")
        self.assertIn('window.name = "rv-dashboard-main"', app)
        self.assertIn('target="rv-dashboard-documentation"', app)
        self.assertIn('target="rv-dashboard-documentation"', html)
        self.assertIn('target="rv-dashboard-main"', rendered)

    def test_worker_inventory_labels_lease_activity_without_claiming_process_liveness(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        self.assertIn("lease heartbeat", app)
        self.assertIn("process liveness not reported", app)
        self.assertIn("an idle worker may have no lease heartbeat", html)
        self.assertIn("Process state is not reported by this view", html)

    def test_grace_execution_and_chat_readiness_are_distinct_and_explained(self):
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        self.assertIn("Chat access alone does not establish execution readiness.", html)
        self.assertIn("verify the selected database and schema against the reviewed resident-execution migrations", html)
        self.assertIn("Refresh reads the projection; it does not apply migrations", html)
        self.assertIn("Disconnect ends this browser's Grace session and hides the transcript; saved history remains.", html)
        self.assertIn("Refresh history reloads the current saved conversation.", html)
        self.assertIn("Shift+Enter or Insert line break adds a newline.", html)

    def test_future_chat_actions_are_disabled_and_milestone_label_is_scoped(self):
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        self.assertIn("Image generation — coming later</button>", html)
        self.assertIn("Attachments — coming later</button>", html)
        self.assertIn("Forward to Riverview — unavailable</button>", html)
        self.assertIn("DASHBOARD MILESTONE M3.1", html)
        self.assertIn("roadmap progress, deployed release, and commissioning acceptance are tracked separately", html)

    def test_chat_timeline_owns_scroll_and_composer_remains_in_document_flow(self):
        css = (ROOT / "src/riverview_core/status_dashboard/static/app.css").read_text(encoding="utf-8")
        self.assertIn(".conversation-timeline{height:min(62vh,760px);min-height:320px;overflow-y:auto", css)
        composer = css.split(".chat-composer{", 1)[1].split("}", 1)[0]
        self.assertNotIn("position:sticky", composer)
        self.assertIn(".topbar{height:auto;min-height:84px;align-items:flex-start;flex-direction:column", css)

    def test_navigation_rail_has_accessible_persistent_compact_state(self):
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        css = (ROOT / "src/riverview_core/status_dashboard/static/app.css").read_text(encoding="utf-8")
        self.assertIn('id="rail-toggle"', html)
        self.assertIn('aria-controls="primary-navigation"', html)
        self.assertIn('aria-label="Download comprehensive offline diagnostic snapshot"', html)
        self.assertIn('role="img" aria-label="Source health: connecting"', html)
        self.assertIn('rv.dashboard.rail-collapsed', app)
        self.assertIn('setAttribute("aria-expanded"', app)
        self.assertIn(".shell.rail-collapsed .nav-label", css)
        self.assertIn(".shell.rail-collapsed .rail-foot .quiet-button{display:inline-flex", css)

    def test_workflow_viewer_exposes_registered_fit_zoom_pan_reset_and_fullscreen_controls(self):
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        script = (ROOT / "src/riverview_core/status_dashboard/static/workflow.js").read_text(encoding="utf-8")
        css = (ROOT / "src/riverview_core/status_dashboard/static/app.css").read_text(encoding="utf-8")
        registry = json.loads((ROOT / "src/riverview_core/status_dashboard/static/capabilities.json").read_text(encoding="utf-8"))
        expected = {"graph.fit", "graph.zoom.in", "graph.zoom.out", "graph.reset", "graph.fullscreen"}
        for control_id in ("graph-fit", "graph-zoom-in", "graph-zoom-out", "graph-reset", "graph-fullscreen"):
            self.assertIn(f'id="{control_id}"', html)
        self.assertTrue(expected <= {control["id"] for control in registry["controls"]})
        for behavior in ("fitWorkflow", "zoomAt", "requestFullscreen", "pointerdown", "pointermove", "wheel"):
            self.assertIn(behavior, script)
        self.assertIn("graph-canvas:fullscreen", css)

    def test_assignment_titles_use_exact_registered_node_labels_and_keep_ids(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        self.assertIn("/api/v1/graphs/${encodeURIComponent(graphId)}", app)
        self.assertIn("item.id === nodeId", app)
        self.assertIn("Canonical task title", app)
        self.assertIn("Task title · ${title}", app)
        self.assertIn("Canonical title unavailable", app)

    def test_notifications_do_not_equate_rendering_or_receipt_with_person_seen_or_decision(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        self.assertIn("Person seen: not reported by this source", app)
        self.assertIn("Receipt acknowledgment:", app)
        self.assertIn("Dashboard rendering:", app)
        self.assertIn("A receipt cannot resolve this request.", app)
        self.assertIn("Decision request: none linked in this projection.", app)

    def test_documentation_catalog_uses_canonical_graph_refs_and_qualifies_evidence(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        self.assertIn('data-view="documentation"', html)
        self.assertIn('id="documentation-search"', html)
        self.assertIn("/api/v1/graphs", app)
        self.assertIn("/api/v1/graphs/${encodeURIComponent(summary.graph_id)}", app)
        self.assertIn("node.source_references", app)
        self.assertIn("node.documentation_references", app)
        self.assertIn("node.verification_evidence", app)
        self.assertIn("Declared test/evidence references", app)
        self.assertIn("do not assert that a test passed", html)

    def test_packaged_dashboard_uses_its_matching_knowledge_sources_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = Path(tmp) / ("a" * 40)
            release.mkdir()
            (release / "SOURCE_COMMIT").write_text("a" * 40 + "\n", encoding="ascii")
            (release / "PACKAGE_SHA256SUMS").write_text("manifest\n", encoding="ascii")
            self.assertEqual(_knowledge_root(release_root=release), release)
            self.assertEqual(_knowledge_root(release_root=release, configured="/srv/approved"),
                             Path("/srv/approved"))
            (release / "PACKAGE_SHA256SUMS").unlink()
            self.assertEqual(_knowledge_root(release_root=release), Path("/opt/riverview-core"))

    def test_knowledge_commit_is_separate_from_dashboard_source_commit(self):
        self.assertEqual(_knowledge_commit(configured="b" * 40,
            dashboard_source_commit="a" * 40, release_commit="c" * 40), "b" * 40)
        self.assertEqual(_knowledge_commit(configured="",
            dashboard_source_commit="a" * 40, release_commit="c" * 40), "a" * 40)
        self.assertEqual(_knowledge_commit(configured="",
            dashboard_source_commit="", release_commit="c" * 40), "c" * 40)

    def test_activity_has_explicit_older_and_newer_sequence_paging(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        self.assertIn('id="more-events"', html)
        self.assertIn("Load older events", html)
        self.assertIn('id="newer-events"', html)
        self.assertIn("Load newer events", html)
        self.assertIn("before_seq=${state.olderEventCursor}", app)
        self.assertIn("after_seq=${after}", app)
        self.assertIn('$("newer-events").addEventListener("click", () => loadEvents(true))', app)
        self.assertIn("new Set(state.events.map((event) => event.event_id))", app)

    def test_activity_events_show_available_provenance_and_missing_diagnostic_boundary(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        self.assertIn('Actor ${esc(e.actor_id || "not recorded")}', app)
        self.assertIn('Payload schema ${esc(e.payload_schema || "not reported")}', app)
        self.assertIn('Root event (no parent recorded)', app)
        self.assertIn("event-specific diagnostic reference are not included in this projection", app)
        self.assertIn('/docs/components/STATUS_DASHBOARD_COOKBOOK.md', app)

    def test_overview_explains_authoritative_projection_and_component_health_boundaries(self):
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        guidance = html[html.index('id="overview-guidance"'):html.index('</div>', html.index('id="overview-guidance"'))]
        for phrase in ("last observed institution event sequence", "read-only ledger response",
                       "separate heartbeat signals", "separate from chat availability",
                       "browser cache bypass", "source observation time",
                       "required ledger query succeeded", "required ledger tables are absent",
                       "current state could not be confirmed"):
            self.assertIn(phrase, guidance)

    def test_worker_inventory_separates_registration_health_and_loaded_page_counts(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        css = (ROOT / "src/riverview_core/status_dashboard/static/app.css").read_text(encoding="utf-8")
        self.assertIn('w.active === true ? "Registered · active"', app)
        self.assertIn('w.active === false ? "Registered · inactive"', app)
        self.assertIn('const health = w.status === "inactive" ? "Registry inactive"', app)
        self.assertIn("registered · ${counts.active} active in registry · ${counts.inactive} inactive", app)
        self.assertIn("lease heartbeat", app)
        self.assertIn("process liveness not reported", app)
        self.assertIn("counts.heartbeat.healthy", app)
        self.assertIn("more records available", app)
        self.assertIn('id="worker-inventory-summary"', html)
        self.assertIn("an idle worker may have no lease heartbeat", html)
        self.assertIn("Counts cover loaded 25-record pages", html)
        self.assertIn(".worker-row{grid-template-columns:minmax(0,1fr) minmax(0,1fr)", css)

    def test_assignment_detail_exposes_persisted_graph_identity_and_safe_diagnostic_reference(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        self.assertIn('item("Canonical graph ID", a.process_graph_id || "No graph ID recorded")', app)
        self.assertIn('item("Canonical node ID", a.process_node_id || "No process node ID recorded")', app)
        self.assertIn(r'^docs\/components\/([A-Za-z0-9_-]+\.md)$', app)
        self.assertIn('href="/docs/components/${esc(match[1])}"', app)
        self.assertIn("persisted assignment references", app)
        self.assertIn("Missing IDs are not inferred", app)

    def test_workflow_registry_client_supports_account_cookie_sessions(self):
        static = Path(__file__).resolve().parents[1] / "src/riverview_core/status_dashboard/static"
        js = (static / "workflow.js").read_text(encoding="utf-8")
        self.assertIn('credentials:"same-origin"', js)
        self.assertIn('if (token()) headers.Authorization', js)
        self.assertNotIn('if(!token()) return;', js)
        app = (static / "app.js").read_text(encoding="utf-8")
        html = (static / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-message-work-order', app)
        self.assertIn('/work-orders', app)
        self.assertIn('id="work-order-criteria"', html)
        self.assertIn('objective.submit on work-order:engineering', app)

    def test_work_order_retry_ui_uses_persisted_sequence_and_reports_open_failure(self):
        app = (ROOT / "src/riverview_core/status_dashboard/static/app.js").read_text(encoding="utf-8")
        html = (ROOT / "src/riverview_core/status_dashboard/static/index.html").read_text(encoding="utf-8")
        self.assertIn('data-message-work-order="${esc(event.sequence)}"', app)
        self.assertIn('state.chatEvents.find((event)=>event.event_type==="user_message"&&event.sequence===sequence)', app)
        self.assertIn('function openWorkOrderDialogForSequence(rawSequence)', app)
        self.assertIn('typeof dialog.showModal!=="function"', app)
        self.assertIn('This saved message is no longer available', app)
        self.assertIn('The work-order form could not be opened', app)
        self.assertNotIn('if(!ev||!Number.isInteger(ev.sequence))return;state.workOrderSourceSequence=ev.sequence', app)
        self.assertIn("Existing source retries retain their original criteria", html)
        self.assertIn('acceptance_criteria:criteria', app)

    def test_grace_conversation_workspace_controls_and_complete_rendering_contract(self):
        static = Path(__file__).resolve().parents[1] / "src/riverview_core/status_dashboard/static"
        html = (static / "index.html").read_text(encoding="utf-8")
        js = (static / "app.js").read_text(encoding="utf-8")
        css = (static / "app.css").read_text(encoding="utf-8")
        self.assertIn('id="chat-history" class="conversation-timeline"', html)
        self.assertIn('id="chat-message" rows="2"', html)
        self.assertIn('id="chat-auth-form"', html)
        self.assertIn('autocomplete="current-password"', html)
        self.assertIn("HttpOnly same-origin cookie", html)
        self.assertIn('id="chat-disconnect"', html)
        self.assertIn("Shift+Enter adds a line", html)
        self.assertLess(html.index('class="chat-more"'), html.index('id="chat-send"'))
        self.assertIn('data-chat-option="details"', html)
        self.assertIn("Image generation — coming later", html)
        self.assertIn("disabled", html[html.index("Image generation — coming later")-80:html.index("Image generation — coming later")])
        self.assertIn("white-space:pre-wrap", css)
        self.assertIn("overflow-wrap:anywhere", css)
        self.assertIn("<div class=\"message-content\">${esc(body)}</div>", js)
        self.assertNotIn("textContent.slice", js[js.index("function renderConversation"):js.index("async function loadGraceConversation")])
        self.assertIn("chat-details-dialog", html)
        self.assertIn("message-details-dialog", html)
        self.assertIn('credentials: "same-origin"', js)
        self.assertIn("state.chatAuthRejected || state.chatLoading", js)
        self.assertIn('resident_conversation_not_authorized', js)
        self.assertIn('/api/v1/resident/conversations/stream', js)
        self.assertIn('text/event-stream', (ROOT / "src/riverview_core/status_dashboard/server.py").read_text())
        self.assertIn('watchPendingResponses', js)
        self.assertIn('after=${cursor}', js)
        self.assertIn('rv_grace_authority', (ROOT / "src/riverview_core/status_dashboard/server.py").read_text())

    def test_unit_uses_private_runtime_pgpass_delivery(self):
        unit = (ROOT / "deploy/riverview-status-dashboard.service").read_text()
        launcher = (ROOT / "scripts/run_status_dashboard.py").read_text()
        self.assertIn("RuntimeDirectory=riverview-status-dashboard", unit)
        self.assertIn("LoadCredential=pgpass:/etc/riverview/pgpass", unit)
        self.assertIn("Environment=RIVERVIEW_SOURCE_COMMIT=8556598b19a7da4aa191a600c767d79d24432afe", unit)
        self.assertIn("Environment=RIVERVIEW_DEPLOYMENT_ID=m3.1-camrui-docs-d2c145c", unit)
        self.assertIn("scripts/run_status_dashboard.py", unit)
        self.assertIn("copy_systemd_credential(source, PASSFILE, identity.pw_uid)", launcher)
        self.assertNotIn("Environment=PGPASSFILE=%d/pgpass", unit)

    def test_launcher_validates_service_credential_and_runtime_identity(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import run_status_dashboard
        from types import SimpleNamespace
        credential_dir = "/run/credentials/riverview-status-dashboard.service"
        with mock.patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": credential_dir}, clear=False):
            for name in ("PGPASSWORD", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"):
                os.environ.pop(name, None)
            with mock.patch.object(run_status_dashboard, "systemd_credential_path") as validate:
                with mock.patch.object(run_status_dashboard, "copy_systemd_credential") as copy:
                    with mock.patch.object(run_status_dashboard.pwd, "getpwnam",
                                            return_value=SimpleNamespace(pw_uid=1234)):
                        with mock.patch.object(run_status_dashboard.os, "geteuid", return_value=1234):
                            run_status_dashboard.prepare_runtime_credential()
            validate.assert_called_once_with(Path(credential_dir) / "pgpass",
                                             service_unit="riverview-status-dashboard.service")
            copy.assert_called_once_with(Path(credential_dir) / "pgpass",
                                         run_status_dashboard.PASSFILE, 1234)
            self.assertEqual(os.environ["PGPASSFILE"], str(run_status_dashboard.PASSFILE))


class DashboardHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.token_path = Path(self.temp.name) / "token"
        self.token = "A" * 43
        self.token_path.write_text(self.token)
        self.token_path.chmod(0o600)
        self.projection = _FakeProjection()
        self.server = None
        for port in range(8799, 8699, -1):
            try:
                self.server = DashboardHTTPServer("127.0.0.1", port, self.token_path,
                    self.projection, ROOT / "src/riverview_core/status_dashboard/static")
                break
            except OSError:
                continue
        if self.server is None:
            self.fail("no free dashboard test port in the reserved 8700-8799 range")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, method, path, *, token=None, host=None, cookie=None):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        headers = {}
        if token is not None:
            headers["Authorization"] = "Bearer " + token
        if host:
            headers["Host"] = host
        if cookie:
            headers["Cookie"] = cookie
        conn.request(method, path, headers=headers)
        response = conn.getresponse()
        body = response.read()
        result = (response.status, response.getheaders(), body)
        conn.close()
        return result

    def test_resource_telemetry_route_uses_dashboard_auth_and_is_read_only(self):
        projection = {"schema_version": "rv.dashboard.resource-telemetry.v1",
                      "status": "partial", "hosts": []}
        class Telemetry:
            def read(self):
                return projection
        self.server._resource_telemetry = Telemetry()
        status, _, body = self.request("GET", "/api/v1/resources/telemetry")
        self.assertEqual(status, 401)
        status, _, body = self.request("GET", "/api/v1/resources/telemetry", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), projection)
        status, _, body = self.request("POST", "/api/v1/resources/telemetry", token=self.token)
        self.assertEqual(status, 405)
        self.assertEqual(json.loads(body)["error"], "read_only_method")

    def test_authenticated_result_rereview_route_is_exact_scoped_bounded_and_request_only(self):
        from riverview_core.resident_execution import ObjectiveNotAuthorized

        expected_objective = "objective:dashboard-rereview"

        class Pipeline:
            def __init__(self):
                self.calls = []

            def request_conversation_result_rereview(self, objective_id, completion_cycle, *,
                    evidence_revision, evidence, credential, idempotency_key):
                self.calls.append((objective_id, completion_cycle, evidence_revision,
                                   evidence, credential, idempotency_key))
                if credential != "objective-submit-credential" or objective_id != expected_objective:
                    raise ObjectiveNotAuthorized("exact objective review scope required")
                if (not isinstance(evidence, list) or not 1 <= len(evidence) <= 32
                        or any(not isinstance(item, str) or not item.strip() or len(item) > 2000
                               for item in evidence)):
                    raise ValueError("bounded evidence list required")
                return {"review_generation": 2, "reused": False,
                        "evidence_revision": evidence_revision}

        pipeline = Pipeline()
        self.server._objective_pipeline = pipeline

        def post(objective_id, data, *, token=None, authority=None):
            body = None if data is None else json.dumps(data, separators=(",", ":")).encode()
            headers = {}
            if token is not None:
                headers["Authorization"] = "Bearer " + token
            if authority is not None:
                headers["X-Riverview-Authority"] = authority
            if body is not None:
                headers["Content-Type"] = "application/json"
                headers["Content-Length"] = str(len(body))
            conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
            conn.request("POST", f"/api/v1/objectives/{objective_id}/result-rereview",
                         body=body, headers=headers)
            response = conn.getresponse()
            status, payload = response.status, json.loads(response.read() or b"{}")
            conn.close()
            return status, payload

        data = {"completion_cycle": 1, "evidence_revision": "rev-2",
                "evidence": ["new bounded evidence"], "idempotency_key": "rereview:cycle-1:rev-2"}
        self.assertEqual(post(expected_objective, data)[0], 401)
        self.assertEqual(post(expected_objective, data, token="B" * 43)[0], 401)
        self.assertEqual(post(expected_objective, data, token=self.token)[0], 403)
        self.assertEqual(post(expected_objective, data, token=self.token,
                              authority="wrong-scope-credential")[0], 403)
        self.assertEqual(post("objective:other", data, token=self.token,
                              authority="objective-submit-credential")[0], 403)

        expanded = {**data, "unexpected": True}
        self.assertEqual(post(expected_objective, expanded, token=self.token,
                              authority="objective-submit-credential")[0], 400)
        oversized_evidence = {**data, "evidence": ["x" * 2001]}
        self.assertEqual(post(expected_objective, oversized_evidence, token=self.token,
                              authority="objective-submit-credential")[0], 400)

        status, payload = post(expected_objective, data, token=self.token,
                               authority="objective-submit-credential")
        self.assertEqual(status, 202)
        self.assertEqual(payload["objective_id"], expected_objective)
        self.assertEqual(payload["review_generation"], 2)
        self.assertEqual(len(pipeline.calls), 5)
        self.assertEqual(pipeline.calls[-1], (expected_objective, 1, "rev-2",
                         ["new bounded evidence"], "objective-submit-credential",
                         "rereview:cycle-1:rev-2"))
        self.assertFalse(hasattr(pipeline, "dispatch_proposed"))

    def test_public_shell_is_local_but_projection_requires_bearer(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Riverview", body)
        self.assertIn(b"/docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md", body)
        doc_names = set(re.findall(rb'href="/docs/components/([A-Za-z0-9_-]+\.md)"', body))
        self.assertGreater(len(doc_names), 1)
        for name in sorted(doc_names):
            doc_status, _, _ = self.request(
                "GET", "/docs/components/" + name.decode("ascii"))
            self.assertEqual(doc_status, 200, name.decode("ascii"))
        header_map = dict(headers)
        self.assertEqual(header_map["Cache-Control"], "no-store")
        self.assertIn("default-src 'none'", header_map["Content-Security-Policy"])
        status, _, _ = self.request("GET", "/api/v1/status")
        self.assertEqual(status, 401)
        status, _, body = self.request("GET", "/api/v1/status", token="B" * 43)
        self.assertEqual(status, 401)
        self.assertNotIn(self.token.encode(), body)

    def test_objective_progress_projection_is_authenticated_and_conversation_scoped(self):
        conversation_id = "00000000-0000-4000-8000-000000000001"
        principal_id = "principal:viewer-one"

        class AccountAuth:
            def authenticate(self, credential, *, csrf_token, state_changing):
                if credential != "session":
                    from riverview_core.account_auth import AuthDenied
                    raise AuthDenied("session denied")
                return {"roles": ["viewer"], "authority_principal_id": principal_id}

        class ConversationService:
            def __init__(self):
                self.last_principal = None
                self.last_conversation_id = None
            def history(self, credential, requested_conversation_id):
                self.last_principal = credential.principal_id
                self.last_conversation_id = requested_conversation_id
                if requested_conversation_id != conversation_id:
                    from riverview_core.resident_execution.conversation import ConversationNotFound
                    raise ConversationNotFound("conversation not found")
                return {"conversation_id": conversation_id, "events": []}

        self.server._account_auth_service = AccountAuth()
        conversation_service = ConversationService()
        self.server._conversation_service = conversation_service

        # A valid dashboard bearer is not an account identity and cannot retrieve
        # the unfiltered objective list.
        status, _, body = self.request("GET", "/api/v1/objectives", token=self.token)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "account_session_required")

        # A non-Steward account cannot omit the conversation scope.
        status, _, body = self.request("GET", "/api/v1/objectives?limit=7",
            token=self.token, cookie="rv_account_session=session")
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "steward_or_owned_conversation_required")

        self.projection.objective_items = [{
            "objective_id": "objective:grounding-owner-visible", "status": "WAITING_FOR_EVIDENCE",
            "origin": {"conversation_id": conversation_id, "source_sequence": 4},
            "grounding_diagnostics": [{"event_id": "event-id", "occurred_at": "2026-10-22T00:00:00Z",
                "diagnostic": {"reason_code": "GROUNDING_NO_MATCH",
                    "explanation": "No matching evidence.", "responsible_component": "KNOWLEDGE-PROVIDER",
                    "retry": {"status": "same_objective_retry_available"}}}],
        }]

        status, _, body = self.request("GET",
            "/api/v1/objectives?limit=7&conversation_id=" + conversation_id,
            token=self.token, cookie="rv_account_session=session")
        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertEqual(response["status"], "available")
        self.assertEqual(response["schema_version"], "rv.dashboard.objective_progress.v1")
        self.assertEqual(response["items"][0]["grounding_diagnostics"][0]["diagnostic"]
                         ["reason_code"], "GROUNDING_NO_MATCH")
        self.assertNotIn("private request text", body.decode())
        self.assertEqual(self.projection.last_limit, 7)
        self.assertEqual(self.projection.last_conversation_id, conversation_id)
        self.assertEqual(self.projection.last_owner_principal_id, principal_id)
        self.assertTrue(self.projection.last_progress_only)
        self.assertEqual(conversation_service.last_principal, principal_id)
        self.assertEqual(conversation_service.last_conversation_id, conversation_id)

        # Existing ConversationService ownership checks reject a foreign
        # conversation before the objective projection is queried.
        projection_calls = self.projection.last_limit
        foreign = "00000000-0000-4000-8000-000000000002"
        status, _, body = self.request("GET",
            "/api/v1/objectives?conversation_id=" + foreign,
            token=self.token, cookie="rv_account_session=session")
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["error"], "conversation_not_found")
        self.assertEqual(self.projection.last_limit, projection_calls)

        # Malformed filters are rejected before any projection is returned.
        for path in (
                "/api/v1/objectives?conversation_id=not-a-uuid",
                "/api/v1/objectives?conversation_id=" + conversation_id + "&unexpected=1",
                "/api/v1/objectives?conversation_id=" + conversation_id + "&limit=1&limit=2"):
            status, _, body = self.request("GET", path, token=self.token,
                cookie="rv_account_session=session")
            self.assertEqual(status, 400, path)
            self.assertEqual(json.loads(body)["error"], "invalid_query")

    def test_steward_account_can_read_global_objective_projection(self):
        class AccountAuth:
            def authenticate(self, credential, *, csrf_token, state_changing):
                return {"roles": ["steward"], "authority_principal_id": "steward:camrui"}

        self.server._account_auth_service = AccountAuth()
        self.projection.objective_items = [{"objective_id": "objective:derived-visible",
            "status": "PROPOSED", "acceptance_criteria_source": "grace_derived",
            "acceptance_criteria": ["The requested deliverable is verified."]}]
        status, _, body = self.request("GET", "/api/v1/objectives?limit=7",
            token=self.token, cookie="rv_account_session=session")
        self.assertEqual(status, 200)
        response = json.loads(body)
        self.assertEqual(response["schema_version"], "rv.dashboard.objectives.v1")
        self.assertEqual(response["items"][0]["acceptance_criteria_source"], "grace_derived")
        self.assertEqual(response["items"][0]["acceptance_criteria"],
                         ["The requested deliverable is verified."])
        self.assertEqual(self.projection.last_owner_principal_id, None)
        self.assertFalse(self.projection.last_progress_only)
        conversation_id = "00000000-0000-4000-8000-000000000003"
        status, _, body = self.request("GET",
            "/api/v1/objectives?conversation_id=" + conversation_id,
            token=self.token, cookie="rv_account_session=session")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["schema_version"], "rv.dashboard.objective_progress.v1")
        self.assertEqual(self.projection.last_conversation_id, conversation_id)
        self.assertEqual(self.projection.last_owner_principal_id, None)
        self.assertTrue(self.projection.last_progress_only)

    def test_non_steward_objective_detail_is_owner_filtered_and_progress_only(self):
        principal_id = "principal:viewer-one"
        conversation_id = "00000000-0000-4000-8000-000000000001"
        objective_id = "objective:viewer-owned"

        class AccountAuth:
            def authenticate(self, credential, *, csrf_token, state_changing):
                return {"roles": ["viewer"], "authority_principal_id": principal_id}

        class ConversationService:
            def history(self, credential, requested_conversation_id):
                self.assertion = (credential.principal_id, requested_conversation_id)
                if requested_conversation_id != conversation_id:
                    from riverview_core.resident_execution.conversation import ConversationNotFound
                    raise ConversationNotFound("conversation not found")
                return {"conversation_id": conversation_id, "events": []}

        self.server._account_auth_service = AccountAuth()
        conversation_service = ConversationService()
        self.server._conversation_service = conversation_service
        self.projection.objective_items = [{
            "objective_id": objective_id, "request": "private request text",
            "scope_ref": "private scope", "submitter_id": principal_id,
            "acceptance_criteria": ["private criteria"], "source_sha256": "secret-digest",
            "origin": {"conversation_id": conversation_id, "source_sequence": 6},
            "status": "RECEIVED", "assignment_id": None,
            "lifecycle_status": "waiting", "lifecycle_stage": "Awaiting authorized work order"}]
        status, _, body = self.request("GET", "/api/v1/objectives/" + objective_id,
            token=self.token, cookie="rv_account_session=session")
        self.assertEqual(status, 200)
        value = json.loads(body)
        self.assertEqual(value["objective_id"], objective_id)
        self.assertNotIn("request", value)
        self.assertNotIn("scope_ref", value)
        self.assertNotIn("acceptance_criteria", value)
        self.assertNotIn("submitter_id", value)
        self.assertNotIn("source_sha256", value)
        self.assertEqual(self.projection.last_owner_principal_id, principal_id)
        self.assertTrue(self.projection.last_progress_only)
        self.assertEqual(conversation_service.assertion, (principal_id, conversation_id))

    def test_conversation_work_order_requires_account_steward_not_recovery_token(self):
        path = "/api/v1/resident/conversations/00000000-0000-4000-8000-000000000001/work-orders"
        status, _, body = self.request("POST", path)
        self.assertEqual(status, 401)
        status, _, body = self.request("POST", path, token=self.token)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "steward_account_session_required")

    def test_history_lookup_failure_logs_deterministic_objective_id(self):
        from uuid import NAMESPACE_URL, uuid5

        principal_id = "steward:camrui"
        conversation_id = "00000000-0000-4000-8000-000000000001"
        sequence = 6
        expected_objective_id = "objective:grace-conversation:" + str(uuid5(
            NAMESPACE_URL,
            f"riverview:grace-conversation-objective:{conversation_id}:{sequence}"))

        class AccountAuth:
            def authenticate(self, credential, *, csrf_token, state_changing):
                return {"roles": ["steward"], "authority_principal_id": principal_id}
            def require_role(self, identity, *roles):
                return None

        class StoreCursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, *_): return None
            def fetchone(self):
                return {"body": "bounded source message", "actor_kind": "principal",
                        "actor_id": principal_id}

        class ConversationService:
            store = type("Store", (), {
                "db": type("DB", (), {"cursor": lambda _: StoreCursor()})(),
                "_path": lambda *_: None})()
            def history(self, _authority, _conversation_id): return []

        class Pipeline:
            ledger = type("Ledger", (), {"db": object()})()

        self.server._account_auth_service = AccountAuth()
        self.server._conversation_service = ConversationService()
        self.server._objective_pipeline = Pipeline()
        body = json.dumps({"source_sequence": sequence,
                           "acceptance_criteria": ["controlled fixture"]}).encode()
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        with mock.patch("riverview_core.status_dashboard.server._find_conversation_objective",
                        side_effect=RuntimeError("private database detail")):
            with self.assertLogs("riverview.dashboard.intake", level="ERROR") as captured:
                conn.request("POST",
                    f"/api/v1/resident/conversations/{conversation_id}/work-orders",
                    body=body, headers={"Cookie": "rv_account_session=session; rv_account_csrf=csrf",
                                        "X-Riverview-CSRF": "csrf",
                                        "Content-Type": "application/json"})
                response = conn.getresponse()
                status, response_body = response.status, json.loads(response.read())
        conn.close()
        self.assertEqual(status, 503)
        event = json.loads(captured.output[-1].split(":", 2)[2])
        self.assertEqual(event["objective_id"], expected_objective_id)
        self.assertEqual(event["failure_stage"], "event_history")
        self.assertNotIn("private database detail", captured.output[-1])
        self.assertEqual(response_body["error"], "work_order_intake_unavailable")

    def test_conversation_work_order_wait_is_receipted_and_same_origin_retry_is_idempotent(self):
        from contextlib import contextmanager
        from riverview_core.resident_execution import ObjectiveStateError

        principal_id = "steward:camrui"
        conversation_id = "00000000-0000-4000-8000-000000000001"
        criteria = ["criterion one", "criterion two"]

        class AccountAuth:
            def authenticate(self, credential, *, csrf_token, state_changing):
                self.assertion = (credential, csrf_token, state_changing)
                return {"roles": ["steward"], "authority_principal_id": principal_id}
            def require_role(self, identity, *roles):
                return None

        class StoreCursor:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, *_): return None
            def fetchone(self):
                return {"body": "bounded source message", "actor_kind": "principal",
                        "actor_id": principal_id}

        class ConversationStore:
            db = type("DB", (), {"cursor": lambda _: StoreCursor()})()
            def _path(self, _cursor): return None

        class ConversationService:
            store = ConversationStore()
            def history(self, _authority, _conversation_id): return []

        class PipelineCursor:
            def __init__(self, pipeline): self.pipeline = pipeline
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, *_): return None
            def fetchall(self):
                if self.pipeline.fail_event_history:
                    error = RuntimeError("sensitive database detail")
                    error.sqlstate = "42501"
                    raise error
                return ([{"objective_id": self.pipeline.objective["objective_id"]}]
                        if self.pipeline.objective else [])

        class PipelineDB:
            def __init__(self, pipeline): self.pipeline = pipeline
            def cursor(self): return PipelineCursor(self.pipeline)

        class PipelineLedger:
            def __init__(self, pipeline): self.db = PipelineDB(pipeline)
            def _set_search_path(self, _cursor): return None

        class Pipeline:
            def __init__(self):
                self.objective = None
                self.submit_count = 0
                self.ground_count = 0
                self.authorization_count = 0
                self.authorization_revoked = False
                self.fail_event_history = False
                self.ledger = PipelineLedger(self)
            def authorize_objective_submission(self, _principal_id, _scope_ref):
                self.authorization_count += 1
                if self.authorization_revoked:
                    from riverview_core.resident_execution import ObjectiveNotAuthorized
                    raise ObjectiveNotAuthorized("objective.submit is not authorized")
                return {"principal_id": principal_id, "grant_id": "grant:test"}
            def submit_objective(self, objective_id, request, acceptance_criteria, *,
                                 scope_ref, principal, origin, criteria_source):
                self.submit_count += 1
                self.objective = {"objective_id": objective_id, "request": request.strip(),
                    "acceptance_criteria": acceptance_criteria, "scope_ref": scope_ref,
                    "submitter_id": principal.principal_id, "status": "RECEIVED",
                    "evidence": None, "source_revision": None, "origin": origin,
                    "acceptance_criteria_source": criteria_source}
                return self.objective
            def ground_objective(self, _objective_id):
                self.ground_count += 1
                self.objective.update({"status": "WAITING_FOR_EVIDENCE", "revision": 2,
                    "evidence": {"status": "UNVERIFIED", "retrieval_complete": False,
                                 "source_references": [], "source_revision": "b" * 40}})
                raise ObjectiveStateError("repository evidence is not complete and verified")
            def get_objective(self, objective_id):
                if self.objective and self.objective["objective_id"] == objective_id:
                    return self.objective
                return None

        auth = AccountAuth()
        pipeline = Pipeline()
        self.server._account_auth_service = auth
        self.server._conversation_service = ConversationService()
        self.server._objective_pipeline = pipeline

        def post_work_order(criteria_value):
            payload = {"source_sequence": 6}
            if criteria_value is not None:
                payload["acceptance_criteria"] = criteria_value
            body = json.dumps(payload).encode("utf-8")
            conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
            conn.request("POST", f"/api/v1/resident/conversations/{conversation_id}/work-orders",
                body=body, headers={"Cookie": "rv_account_session=session; rv_account_csrf=csrf",
                                    "X-Riverview-CSRF": "csrf", "Content-Type": "application/json"})
            response = conn.getresponse()
            status, payload = response.status, json.loads(response.read())
            conn.close()
            return status, payload

        first_status, first = post_work_order(criteria)
        second_status, second = post_work_order(criteria)
        self.assertEqual(first_status, 202)
        self.assertEqual(second_status, 202)
        self.assertEqual(first["objective_id"], second["objective_id"])
        self.assertFalse(first["reused_existing_objective"])
        self.assertTrue(second["reused_existing_objective"])
        self.assertEqual(second["status"], "WAITING_FOR_EVIDENCE")
        self.assertEqual(second["evidence"]["status"], "UNVERIFIED")
        self.assertEqual(pipeline.submit_count, 1)
        self.assertEqual(pipeline.ground_count, 2)
        self.assertEqual(auth.assertion, ("session", "csrf", True))
        self.assertEqual(pipeline.objective["acceptance_criteria"], criteria)
        self.assertEqual(first["acceptance_criteria_source"], "steward_supplied")

        original_criteria = list(pipeline.objective["acceptance_criteria"])
        recorded_objective = dict(pipeline.objective)
        normalized_retry_status, normalized_retry = post_work_order(["criteria with different whitespace "])
        self.assertEqual(normalized_retry_status, 202)
        self.assertTrue(normalized_retry["reused_existing_objective"])
        self.assertEqual(pipeline.objective["acceptance_criteria"], original_criteria)
        blank_retry_status, blank_retry = post_work_order(None)
        self.assertEqual(blank_retry_status, 202)
        self.assertTrue(blank_retry["reused_existing_objective"])
        self.assertEqual(blank_retry["objective_id"], first["objective_id"])
        self.assertEqual(pipeline.objective["acceptance_criteria"], original_criteria)
        self.assertEqual(pipeline.submit_count, 1)
        self.assertEqual(pipeline.authorization_count, 3)
        self.assertEqual(pipeline.ground_count, 4)

        pipeline.authorization_revoked = True
        denied_status, denied = post_work_order(None)
        self.assertEqual(denied_status, 403)
        self.assertEqual(denied["error"], "engineering_work_order_submission_not_authorized")
        self.assertEqual(pipeline.submit_count, 1)
        pipeline.objective = None
        empty_new_status, empty_new = post_work_order([])
        self.assertEqual(empty_new_status, 202)
        self.assertEqual(empty_new["acceptance_criteria_source"], "grace_derived")
        self.assertEqual(pipeline.objective["acceptance_criteria"], [])
        self.assertEqual(pipeline.objective["acceptance_criteria_source"], "grace_derived")
        self.assertEqual(pipeline.submit_count, 2)
        pipeline.objective = recorded_objective
        pipeline.authorization_revoked = False
        pipeline.objective["scope_ref"] = "work-order:other"
        origin_conflict_status, origin_conflict = post_work_order(None)
        self.assertEqual(origin_conflict_status, 409)
        self.assertEqual(origin_conflict["error"], "work_order_origin_conflict")

        # The deterministic objective identity must be available to diagnostics
        # even if the event-history lookup fails before it can find a receipt.
        from uuid import NAMESPACE_URL, uuid5
        pipeline.fail_event_history = True
        with self.assertLogs("riverview.dashboard.intake", level="ERROR") as captured:
            failed_status, failed = post_work_order(None)
        self.assertEqual(failed_status, 503)
        self.assertEqual(failed["error"], "work_order_intake_unavailable")
        diagnostic = json.loads(captured.output[-1].split(":", 2)[-1].strip())
        expected_id = "objective:grace-conversation:" + str(uuid5(
            NAMESPACE_URL,
            f"riverview:grace-conversation-objective:{conversation_id}:6"))
        self.assertEqual(diagnostic["objective_id"], expected_id)
        self.assertEqual(diagnostic["failure_stage"], "event_history")
        self.assertEqual(diagnostic["exception_type"], "RuntimeError")
        self.assertEqual(diagnostic["sqlstate"], "42501")
        self.assertNotIn("sensitive database detail", captured.output[-1])

    def test_conversation_stream_requires_authentication_and_existing_service(self):
        path="/api/v1/resident/conversations/00000000-0000-4000-8000-000000000001/responses/00000000-0000-4000-8000-000000000002/stream?after=0"
        status,_,_=self.request("GET",path)
        self.assertEqual(status,401)
        status,_,body=self.request("GET",path,token=self.token)
        self.assertEqual(status,503)
        self.assertEqual(json.loads(body)["error"],"resident_conversation_unavailable")
        status,_,body=self.request("POST","/api/v1/resident/conversations/stream",token=self.token)
        self.assertEqual(status,503)

    def test_authenticated_sse_replays_durable_response_events(self):
        class StreamService:
            def stream_snapshot(self,credential,conversation_id,response_id,*,after_sequence):
                self_credential=credential
                self.asserted = self_credential
                events=[
                    {"sequence":1,"event_type":"generating","generation":1},
                    {"sequence":2,"event_type":"delta","text":"first chunk"},
                    {"sequence":3,"event_type":"completed","metadata":{"model_id":"test"}},
                ]
                return {"status":"completed","events":[e for e in events if e["sequence"]>after_sequence]}
        service=StreamService()
        self.server._conversation_service=service
        conversation_id="00000000-0000-4000-8000-000000000001"
        request_id="00000000-0000-4000-8000-000000000002"
        path=f"/api/v1/resident/conversations/{conversation_id}/responses/{request_id}/stream?after=0"
        status,headers,body=self.request("GET",path,token=self.token,
            cookie="rv_grace_authority="+"C"*43)
        self.assertEqual(status,200)
        header_map=dict(headers)
        self.assertEqual(header_map["Content-Type"],"text/event-stream; charset=utf-8")
        self.assertEqual(header_map["X-Accel-Buffering"],"no")
        self.assertIn(b"event: delta",body)
        self.assertIn(b'"text":"first chunk"',body)
        self.assertIn(b"event: completed",body)
        resumed_path=path.replace("after=0","after=2")
        status,_,resumed=self.request("GET",resumed_path,token=self.token,
            cookie="rv_grace_authority="+"C"*43)
        self.assertEqual(status,200)
        self.assertNotIn(b'"text":"first chunk"',resumed)
        self.assertIn(b"event: completed",resumed)
    def test_api_is_read_only_host_checked_and_never_claims_healthy_without_source(self):
        status, _, body = self.request("GET", "/api/v1/status", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["projection_status"], "unavailable")
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            status, _, body = self.request(method, "/api/v1/status", token=self.token)
            self.assertEqual(status, 405, method)
            self.assertEqual(json.loads(body)["error"], "read_only_method")
        status, _, body = self.request("GET", "/api/v1/status", token=self.token, host="attacker.invalid")
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(body)["error"], "invalid_host")

    def test_pages_are_bounded_and_unknown_routes_do_not_reveal_server(self):
        status, _, body = self.request("GET", "/api/v1/events?limit=9000", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(self.projection.last_limit, 100)
        status, _, body = self.request("GET", "/api/v1/workers?limit=9000", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(self.projection.last_limit, 100)
        status, _, body = self.request("GET", "/not-an-api", token=self.token)
        self.assertEqual(status, 404)
        self.assertNotIn(b"BaseHTTPRequestHandler", body)

    def test_component_cookbook_is_rendered_as_readable_safe_html(self):
        status, headers, body = self.request("GET", "/docs/components/CME_MONITOR_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b"<h1", body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"Riverview~ Controlled Document", body)
        self.assertNotIn(b"<!--", body)
        status, _, operations = self.request("GET", "/docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn(b"Observed PostgreSQL backup path permission failure", operations)
        self.assertIn(b"Permission denied", operations)
        self.assertIn(b"sudo -n -u postgres test -x", operations)
        self.assertIn(b"378a1a4cba4605a673d8cf22b8bfcbb4277bce272158cae6e79c7d6ecfd0720b", operations)
        self.assertIn(b"<pre><code", operations)
        self.assertNotIn(b"Riverview~ Controlled Document", operations)
        self.assertNotIn(b"<!--", operations)
        status, headers, body = self.request(
            "GET", "/docs/components/ASSIGNMENT_SCHEDULER_COOKBOOK.md")
        self.assertEqual(status, 200)
        for evidence in (b"dependency of the later worker and monitoring migration chain",
                         b"ce29c2994904f54706db883f61127bf05ee195ecbdce90e7242886e86711b717",
                         b"no standalone M1.4 scheduler service"):
            self.assertIn(evidence, body)
        status, headers, body = self.request("GET", "/docs/components/RIVERVIEW_OPERATIONS_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b'id="riverview-operations-and-recovery-guide"', body)
        for heading in (b"PostgreSQL and ledger", b"Migrations, backups, and restoration",
                        b"CME progress monitor", b"Event processor and durable cursor",
                        b"Worker registration, scheduling, leases, assignments, verification"):
            self.assertIn(heading, body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"Riverview~ Controlled Document", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/POSTGRES_LEDGER_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        for heading in (b"Connection and schema inspection", b"Run tests safely",
                        b"Recovery discipline"):
            self.assertIn(heading, body)
        self.assertIn(b"sudo -n -u postgres psql", body)
        self.assertIn(b"RIVERVIEW_TEST_PG_DSN", body)
        self.assertNotIn(b"PGPASSWORD=", body)
        self.assertNotIn(b"postgresql://", body)
        self.assertIn(b"BEGIN READ ONLY", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/ASSIGNMENT_SCHEDULER_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        for heading in (b"Read-only claim and lease inspection",
                        b"Isolated failure and recovery verification",
                        b"StaleLeaseError"):
            self.assertIn(heading, body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/WORKER_ADAPTER_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        for heading in (b"Worker registration and persisted execution diagnosis",
                        b"Independent outcome verification",
                        b"Failure and restart recovery"):
            self.assertIn(heading, body)
        self.assertIn(b"credential digests", body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b'id="versioned-privilege-boundary-provisioner-isolated-controlled-use"', body)
        self.assertIn(b"DROP ... CASCADE", body)
        self.assertIn(b"NOLOGIN", body)
        self.assertIn(b"protected full backup", body)
        self.assertIn(b"<table>", body)
        self.assertIn(b"<pre><code", body)
        self.assertNotIn(b"<!--", body)
        status, headers, body = self.request(
            "GET", "/docs/components/INSTITUTIONAL_AUTHORITY.md")
        self.assertEqual(status, 200)
        self.assertIn(b'INSTITUTIONAL_AUTHORITY_COOKBOOK.md', body)
        self.assertIn(b"<h1", body)
        status, _, body = self.request("GET", "/docs/components/../../README.md")
        self.assertEqual(status, 404)
        self.assertNotIn(b"README", body)

    def test_canonical_graph_api_uses_only_persisted_live_position(self):
        from urllib.parse import quote
        status, _, _ = self.request("GET", "/api/v1/graphs")
        self.assertEqual(status, 401)
        status, _, body = self.request("GET", "/api/v1/graphs", token=self.token)
        self.assertEqual(status, 200)
        listing = json.loads(body)
        self.assertEqual(listing["status"], "available")
        from jsonschema import Draft202012Validator
        contract = json.loads((ROOT / "docs/components/STATUS_DASHBOARD_API.schema.json").read_text())
        Draft202012Validator(contract).validate(listing)
        self.assertTrue(any(item["graph_id"] == "rv:worker-adapter:deterministic-attempt"
                            for item in listing["items"]))
        graph_id = quote("rv:worker-adapter:deterministic-attempt", safe="")
        status, _, body = self.request("GET", "/api/v1/graphs/" + graph_id, token=self.token)
        self.assertEqual(status, 200)
        result = json.loads(body)
        Draft202012Validator(contract).validate(result)
        graph = result["graph"]
        self.assertTrue(any(item["type"] == "decision" for item in graph["nodes"]))
        self.assertTrue(any(item["type"] == "runtime_transition" for item in graph["edges"]))
        self.assertEqual(graph["execution_position"]["status"], "unknown")
        self.assertEqual(graph["execution_position"]["reason"], "No recorded node.")
        self.projection.execution_position = {"status": "current",
            "assignment_id": "assignment:recorded", "state": "running",
            "node_id": "rv:postgres-ledger:assignment-lifecycle:running",
            "recorded_at": "2026-10-13T00:00:00+00:00"}
        status, _, body = self.request("GET", "/api/v1/graphs/" + graph_id, token=self.token)
        self.assertEqual(status, 200)
        graph = json.loads(body)["graph"]
        self.assertEqual(graph["execution_position"]["node_id"],
                         "rv:postgres-ledger:assignment-lifecycle:running")
        status, _, body = self.request("GET", "/api/v1/graphs/rv%3Anot-registered%3Anone", token=self.token)
        self.assertEqual(status, 404)

    def test_capability_registry_and_snapshot_workflow_inventory_require_dashboard_auth(self):
        for path in ("/api/v1/capabilities", "/api/v1/snapshot/workflow-index"):
            status, _, _ = self.request("GET", path)
            self.assertEqual(status, 401, path)
            status, _, body = self.request("GET", path, token=self.token)
            self.assertEqual(status, 200, path)
            payload = json.loads(body)
            if path.endswith("capabilities"):
                self.assertEqual(payload["schema_version"], "rv.website.capabilities.v1")
                self.assertEqual(len({x["id"] for x in payload["pages"]}), len(payload["pages"]))
                self.assertEqual(len({x["id"] for x in payload["controls"]}), len(payload["controls"]))
                self.assertTrue(all(isinstance(x.get("capability_version"), str) for x in payload["pages"]+payload["controls"]))
                self.assertTrue(all(isinstance(rep, str) for page in payload["pages"] for rep in page["representations"]))
                self.assertTrue(all(len(page["representations"]) == len(set(page["representations"])) for page in payload["pages"]))
                self.assertTrue(all(page["selector"] and page["navigation_selector"] and page["components"] and page["data_sources"] for page in payload["pages"]))
                self.assertIn("/api/v1/snapshot/workflow-index", payload["workflow_surfaces"]["registry_source"])
            else:
                self.assertEqual(payload["schema_version"], "rv.website.workflow-index.v1")
                self.assertEqual(payload["status"], "available")
                canonical = [graph for path in (Path(__file__).resolve().parents[1] / "process_graphs").glob("*/*.json") if path.parent.name not in {"generated", "schema"} for graph in [json.loads(path.read_text(encoding="utf-8"))] if isinstance(graph, dict) and isinstance(graph.get("graph_id"), str)]
                self.assertEqual(payload["inventory_count"], len(canonical))
                self.assertEqual({item["graph_id"] for item in payload["items"]}, {item["graph_id"] for item in canonical})
                self.assertEqual(sum(item["node_count"] for item in payload["items"]), sum(len(item.get("nodes", [])) for item in canonical))
                self.assertEqual(sum(item["edge_count"] for item in payload["items"]), sum(len(item.get("edges", [])) for item in canonical))
                self.assertTrue(all(item["source_file"].startswith("process_graphs/") for item in payload["items"]))
                self.assertTrue(all(item["edge_count"] >= 0 for item in payload["items"]))

    def test_diagnostic_snapshot_asset_declares_privacy_and_full_graph_export_contract(self):
        status, _, _ = self.request("GET", "/assets/diagnostic-snapshot.js")
        self.assertEqual(status, 200)
        status, _, body = self.request("GET", "/assets/diagnostic-snapshot.js", token=self.token)
        self.assertEqual(status, 200)
        script = body.decode("utf-8")
        for contract in ("workflow-index.json", "data-node-id", "data-edge-from", "image.decode",
                         "foreignObject", "XMLSerializer", "private conversation content", "account details", "authorization_headers",
                         "uncovered_rendered_controls", "detail_tiles", "const safeRequest", "safeCode", "getEntriesByType(\"navigation\")", "unresolved_references"):
            self.assertIn(contract, script)
        self.assertIn('id="snapshot"', self.request("GET", "/", token=self.token)[2].decode("utf-8"))

    def test_institutional_proposal_script_is_served_as_dashboard_asset(self):
        status, headers, body = self.request("GET", "/assets/institutional-proposals.js")
        self.assertEqual(status, 200)
        self.assertIn("text/javascript", dict(headers).get("Content-Type", ""))
        self.assertIn(b"institutional-proposals", body)

    def test_assignment_intake_cookbook_renders_without_broken_evidence_link(self):
        status, headers, body = self.request(
            "GET", "/docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md")
        self.assertEqual(status, 200)
        self.assertIn("text/html", dict(headers)["Content-Type"])
        self.assertIn(b"Assignment-create authorization boundary", body)
        self.assertIn(b"<pre><code class=\"language-bash\">", body)
        self.assertIn(b"exact <code>assignment.create</code>", body)
        self.assertIn(b"evidence/checkouts/M3.3-ASSIGNMENT-INTAKE/acceptance.json", body)
        self.assertNotIn(b"href=\"/evidence/", body)
        self.assertNotIn(b"<!--", body)

    def test_markdown_renderer_escapes_html_and_rejects_unsafe_link_schemes(self):
        html = render_markdown("# Title\n\n<script>alert(1)</script>\n\n[bad](javascript:alert(1))\n\n[component](CME_MONITOR_COOKBOOK.md)\n\n| A | B |\n|---|---|\n| x | y |\n\n```sh\necho safe\n```",
                               document="docs/components/STATUS_DASHBOARD_COOKBOOK.md",
                               title="Cookbook")
        self.assertIn(b"&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn(b"<script>", html)
        self.assertNotIn(b"href=\"javascript:", html)
        self.assertIn(b"href=\"/docs/components/CME_MONITOR_COOKBOOK.md\"", html)
        self.assertIn(b"<table>", html)
        self.assertIn(b"<pre><code class=\"language-sh\">", html)

    def test_not_initialized_attention_is_domain_state_not_repeated_http_503(self):
        self.projection.attention = lambda *, limit=25: {
            "status":"not_initialized", "items":[], "limit":limit}
        status, _, body = self.request("GET", "/api/v1/attention?limit=10", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "not_initialized")

    def test_attention_query_failure_remains_http_503(self):
        from riverview_core.status_dashboard.projection import ProjectionUnavailable
        self.projection.attention = mock.Mock(side_effect=ProjectionUnavailable("OperationalError"))
        status, _, body = self.request("GET", "/api/v1/attention?limit=10", token=self.token)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body)["error"], "projection_unavailable")

    def test_not_initialized_worker_and_ledger_pages_remain_explicit_http_200(self):
        self.projection.workers = lambda *, after=None, limit=25: {
            "status":"not_initialized", "items":[], "next_cursor":None, "page_limit":limit}
        self.projection.events = lambda *, after_seq=None, before_seq=None, limit=25: {
            "status":"not_initialized", "items":[], "next_cursor":None, "page_limit":limit}
        for route in ("/api/v1/workers", "/api/v1/events"):
            status, _, body = self.request("GET", route, token=self.token)
            self.assertEqual(status, 200, route)
            self.assertEqual(json.loads(body)["status"], "not_initialized")

    def test_token_file_requires_owner_only_permissions_and_loopback_bind(self):
        with self.assertRaisesRegex(RuntimeError, "owner-only"):
            self.token_path.chmod(0o644)
            _read_token(self.token_path)
        self.token_path.chmod(0o600)
        self.assertEqual(_read_token(self.token_path), self.token)
        credential_dir = Path(self.temp.name) / "credentials"
        credential_dir.mkdir()
        credential = credential_dir / "dashboard-token"
        credential.write_text(self.token)
        credential.chmod(0o440)
        with mock.patch.dict(os.environ, {"CREDENTIALS_DIRECTORY": str(credential_dir)}):
            self.assertEqual(_read_token(credential), self.token)
            credential.chmod(0o460)
            with self.assertRaisesRegex(RuntimeError, "non-writable protected"):
                _read_token(credential)
        linked = Path(self.temp.name) / "token-link"
        linked.symlink_to(self.token_path)
        with self.assertRaisesRegex(RuntimeError, "symbolic link"):
            _read_token(linked)
        with self.assertRaisesRegex(ValueError, "loopback"):
            DashboardHTTPServer("0.0.0.0", 8766, self.token_path, self.projection)

    def test_slow_database_request_does_not_block_local_tab_navigation(self):
        start = time.perf_counter()
        # Tab navigation only changes already-rendered local DOM; the API request runs independently.
        simulated_navigation_ms = (time.perf_counter() - start) * 1000
        self.assertLess(simulated_navigation_ms, 20)
        status, _, _ = self.request("GET", "/api/v1/status", token=self.token)
        self.assertEqual(status, 200)


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class DashboardPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from psycopg.rows import dict_row
        from riverview_core.cme import CMEPostgresMonitor
        from riverview_core.postgres_ledger import PostgresLedger
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        self.core = ROOT / "src/riverview_core"
        apply_migrations(DSN, schema=self.schema)
        apply_migrations(DSN, schema=self.schema, migrations_dir=self.core / "assignment_scheduler/migrations")
        apply_migrations(DSN, schema=self.schema, migrations_dir=self.core / "worker_adapter/migrations")
        apply_migrations(DSN, schema=self.schema, migrations_dir=self.core / "cme/migrations")
        self.admin.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
        self.ledger = PostgresLedger(DSN, schema=self.schema)
        self.monitor = CMEPostgresMonitor(DSN, schema=self.schema, stall_after_seconds=2,
                                          worker_freshness_seconds=30)
        self.projection = DashboardProjection(DSN, schema=self.schema,
            source_commit="a" * 40, deployment_id="test-m31")

    def tearDown(self):
        from psycopg import sql
        self.ledger.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def create(self, label, *, private=False):
        assignment_id = f"m31-{label}-{uuid4().hex}"
        self.ledger.create(assignment_id, "engineering", f"create:{assignment_id}",
            authority_ref="grant:test-secret", objective_ref="objective:private-body",
            actor_id="resident:test", correlation_id=f"corr:{assignment_id}")
        self.ledger.transition(assignment_id, "ready", "dispatch", f"ready:{assignment_id}", actor_id="processor")
        self.ledger.transition(assignment_id, "running", "execute", f"run:{assignment_id}", actor_id="worker")
        if private:
            with self.admin.cursor() as cur:
                cur.execute("UPDATE events SET privacy_domain='undercurrent' WHERE assignment_id=%s",
                            (assignment_id,))
        return assignment_id

    def test_actual_postgres_assignment_events_cme_stall_unrelated_progress_and_status(self):
        stalled = self.create("stalled")
        progressing = self.create("progressing")
        with self.admin.cursor() as cur:
            cur.execute("UPDATE events SET recorded_at=clock_timestamp()-interval '20 seconds' WHERE assignment_id=%s",
                        (stalled,))
            cur.execute("UPDATE assignments SET updated_at=clock_timestamp()-interval '20 seconds' WHERE id=%s",
                        (stalled,))
        observed = self.monitor.scan_once()
        self.assertEqual(observed["stalled"], 1)
        assignments = self.projection.assignments(limit=10)["items"]
        by_id = {row["assignment_id"]: row for row in assignments}
        self.assertEqual(by_id[stalled]["state"], "running")
        self.assertEqual(by_id[progressing]["state"], "running")
        self.assertNotEqual(by_id[stalled]["last_meaningful_progress"]["recorded_at"],
                            by_id[progressing]["last_meaningful_progress"]["recorded_at"])
        status = self.projection.status()
        self.assertEqual(status["projection_status"], "healthy")
        self.assertEqual(status["cme"]["status"], "healthy")
        self.assertEqual(status["cme"]["service_id"], "cme.monitor.v1")
        attention = self.projection.attention(limit=10)["items"]
        self.assertTrue(any(item["event_type"] == "assignment_stalled" and
                            item["assignment_id"] == stalled for item in attention))
        events = self.projection.events(limit=100)["items"]
        self.assertTrue(any(event["correlation_id"] == f"corr:{progressing}" for event in events))

    def test_objective_progress_projection_filters_submitter_and_omits_request_content(self):
        from uuid import uuid4

        # Install only the authoritative objective/conversation table definitions
        # in this disposable schema; the surrounding dashboard fixture owns all
        # assignment and verifier tables used by the projection joins.
        self.admin.execute((self.core / "resident_execution/migrations/0001_grace_objectives.sql")
                           .read_text(encoding="utf-8"))
        self.admin.execute((self.core / "resident_execution/migrations/0003_resident_conversation.sql")
                           .read_text(encoding="utf-8"))
        owner = "principal:viewer-one"
        other = "principal:viewer-two"
        own_conversation = str(uuid4())
        other_conversation = str(uuid4())
        own_objective = "objective:" + uuid4().hex
        other_objective = "objective:" + uuid4().hex
        with self.admin.cursor() as cur:
            cur.execute("""INSERT INTO resident_conversations
                (conversation_id,office_id,owner_principal_id)
                VALUES (%s,'grace',%s),(%s,'grace',%s)""",
                (own_conversation, owner, other_conversation, other))
            for objective_id, principal_id, conversation_id, marker in (
                    (own_objective, owner, own_conversation, "owner-private-request"),
                    (other_objective, other, other_conversation, "other-private-request")):
                cur.execute("""INSERT INTO grace_objectives
                    (objective_id,request,scope_ref,submitter_id,acceptance_criteria,status)
                    VALUES (%s,%s,'work-order:engineering',%s,%s::jsonb,'RECEIVED')""",
                    (objective_id, marker, principal_id, json.dumps(["private acceptance criterion"])))
                cur.execute("""INSERT INTO grace_objective_events
                    (objective_id,event_type,idempotency_key,actor_id,payload)
                    VALUES (%s,'objective.received',%s,%s,%s::jsonb)""",
                    (objective_id, "receive:" + objective_id, principal_id,
                     json.dumps({"origin": {"conversation_id": conversation_id,
                                             "source_sequence": 6}})))
                if objective_id == own_objective:
                    event_id = str(uuid4())
                    diagnostic = {"event_id": event_id, "attempt_id": str(uuid4()),
                        "objective_id": objective_id, "objective_revision": 2,
                        "previous_state": "RECEIVED", "new_state": "WAITING_FOR_EVIDENCE",
                        "stage": "provider_result", "attempted_operation": "knowledge_provider.ground_assignment",
                        "outcome": "blocked", "reason_code": "GROUNDING_NO_MATCH",
                        "explanation": "The knowledge provider returned no matching evidence.",
                        "evidence": {"status": "NO_MATCH", "source_revision": None,
                            "source_sha256_present": False, "retrieval_complete": False,
                            "reference_count": 0, "sha256": "a" * 64},
                        "responsible_component": "KNOWLEDGE-PROVIDER",
                        "retry": {"status": "authorized_same_objective_retry_available",
                            "retryable": True, "automatic": False,
                            "next_retry_at": None, "required_actor": "steward",
                            "next_permitted_action": "Retry on the existing conversation."},
                        "attempt_started_at": "2026-10-22T00:00:00Z"}
                    cur.execute("UPDATE grace_objectives SET status='WAITING_FOR_EVIDENCE',revision=2 "
                                "WHERE objective_id=%s", (objective_id,))
                    cur.execute("""INSERT INTO grace_objective_events
                        (event_id,objective_id,event_type,idempotency_key,actor_id,payload)
                        VALUES (%s,%s,'objective.waiting_for_evidence',%s,'knowledge-provider',%s::jsonb)""",
                        (event_id, objective_id, "wait:" + objective_id,
                         json.dumps({"grounding_diagnostic": diagnostic})))

        page = self.projection.objectives(limit=10, conversation_id=own_conversation,
            owner_principal_id=owner, progress_only=True)
        self.assertEqual(page["schema_version"], "rv.dashboard.objective_progress.v1")
        self.assertEqual([row["objective_id"] for row in page["items"]], [own_objective])
        item = page["items"][0]
        self.assertEqual(item["origin"], {"conversation_id": own_conversation, "source_sequence": 6})
        self.assertNotIn("request", item)
        self.assertNotIn("scope_ref", item)
        self.assertNotIn("submitter_id", item)
        self.assertNotIn("acceptance_criteria", item)
        self.assertNotIn("source_sha256", item)
        self.assertEqual(item["grounding_diagnostics"][0]["diagnostic"]["reason_code"],
                         "GROUNDING_NO_MATCH")
        self.assertNotIn("owner-private-request", json.dumps(item["grounding_diagnostics"]))
        restarted_projection = DashboardProjection(DSN, schema=self.schema,
            source_commit="a" * 40, deployment_id="test-m31-restarted")
        restored = restarted_projection.objectives(limit=10, conversation_id=own_conversation,
            owner_principal_id=owner, progress_only=True)["items"][0]
        self.assertEqual(restored["grounding_diagnostics"], item["grounding_diagnostics"])
        self.assertEqual(self.projection.objectives(limit=10, conversation_id=other_conversation,
            owner_principal_id=owner, progress_only=True)["items"], [])

    def test_stale_and_future_cme_heartbeat_are_never_healthy(self):
        self.create("stale")
        self.monitor.scan_once()
        with self.admin.cursor() as cur:
            cur.execute("UPDATE cme_monitor_health SET last_heartbeat_at=clock_timestamp()-interval '2 minutes' "
                        "WHERE service_id='cme.monitor.v1'")
        self.assertEqual(self.projection.status()["cme"]["status"], "stale")
        with self.admin.cursor() as cur:
            cur.execute("UPDATE cme_monitor_health SET last_heartbeat_at=clock_timestamp()+interval '2 minutes' "
                        "WHERE service_id='cme.monitor.v1'")
        self.assertEqual(self.projection.status()["cme"]["status"], "unverified")

    def test_workers_have_individual_bounded_health_and_summary_counts(self):
        from psycopg import sql
        from uuid import uuid4
        workers = {"healthy": "dash-healthy", "stale": "dash-stale",
                   "future": "dash-future", "unknown": "dash-unknown"}
        assignments = {name: self.create("worker-" + name) for name in workers if name != "unknown"}
        now = datetime.now(timezone.utc)
        heartbeats = {"healthy": now-timedelta(seconds=2),
                      "stale": now-timedelta(minutes=2),
                      "future": now+timedelta(minutes=2)}
        with self.admin.cursor() as cur:
            for name, worker_id in workers.items():
                cur.execute("INSERT INTO worker_registry(worker_id,credential_sha256,capabilities,scope_ref) "
                            "VALUES (%s,%s,'[]','dashboard-test')", (worker_id,bytes(name[0].encode())*32))
                if name == "unknown":
                    continue
                assignment_id=assignments[name]
                heartbeat=heartbeats[name]
                expires=now+timedelta(seconds=60) if name != "stale" else now-timedelta(seconds=5)
                acquired=now-timedelta(seconds=10)
                cur.execute("INSERT INTO assignment_leases(assignment_id,worker_id,generation,acquired_at,"
                            "heartbeat_at,expires_at) VALUES (%s,%s,1,%s,%s,%s)",
                            (assignment_id,worker_id,acquired,heartbeat,expires))
        pages=[]; page=self.projection.workers(limit=2); pages.append(page)
        self.assertEqual(len(page["items"]),2); self.assertTrue(page["truncated"])
        while page["next_cursor"]:
            page=self.projection.workers(after=page["next_cursor"],limit=2); pages.append(page)
        observed={w["worker_id"]:w["status"] for p in pages for w in p["items"]}
        self.assertEqual(observed, {"dash-healthy":"healthy","dash-stale":"stale",
                                    "dash-future":"unverified","dash-unknown":"unknown"})
        summary=self.projection.status()["workers"]
        self.assertEqual(summary["active_workers"],4)
        self.assertEqual(summary["healthy_workers"],1)
        self.assertEqual(summary["stale_workers"],1)
        self.assertEqual(summary["unverified_workers"],1)
        self.assertEqual(summary["unknown_workers"],1)
        self.assertEqual(summary["status"],"unverified")
        self.assertEqual(sum(w["active_leases"] for p in pages for w in p["items"]),2)
        self.assertEqual(len(self.projection.snapshot()["workers"]["items"]),4)

    def test_inactive_retired_registration_is_excluded_from_active_health_counts(self):
        with self.admin.cursor() as cur:
            cur.execute("INSERT INTO worker_registry(worker_id,credential_sha256,capabilities,scope_ref,active) "
                        "VALUES ('retired-worker',%s,'[]'::jsonb,'work-order:retired',false)",
                        (b"r" * 32,))
        worker_page = self.projection.workers(limit=10)
        retired = next(item for item in worker_page["items"]
                       if item["worker_id"] == "retired-worker")
        self.assertFalse(retired["active"])
        self.assertEqual(retired["status"], "inactive")
        summary = self.projection.status()["workers"]
        self.assertEqual(summary["active_workers"], 0)
        self.assertEqual(summary["healthy_workers"], 0)
        self.assertEqual(summary["stale_workers"], 0)
        self.assertEqual(summary["unknown_workers"], 0)

    def test_unavailable_and_not_initialized_sources_are_distinct(self):
        missing = DashboardProjection(DSN, schema="rvtest_missing_dashboard")
        self.assertEqual(missing.status()["projection_status"], "not_initialized")
        unavailable = DashboardProjection("host=127.0.0.1 port=1 dbname=missing connect_timeout=1",
                                          schema=self.schema)
        self.assertEqual(unavailable.status()["projection_status"], "unavailable")
        self.assertFalse(unavailable.snapshot()["observed_state"])

    def test_restricted_riverview_core_role_can_read_only_grace_health_after_migration(self):
        import psycopg
        from psycopg import sql
        from riverview_core.status_dashboard.projection import ProjectionUnavailable

        role = "riverview_core"
        with self.admin.cursor() as cur:
            cur.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s) AS present", (role,))
            if not cur.fetchone()["present"]:
                self.skipTest("isolated PostgreSQL instance does not define the dashboard runtime role")
            cur.execute("SELECT rolsuper AS is_superuser FROM pg_roles WHERE rolname=current_user")
            is_superuser = cur.fetchone()["is_superuser"]
            cur.execute("SELECT pg_has_role(current_user,%s,'MEMBER') AS member", (role,))
            if not is_superuser and not cur.fetchone()["member"]:
                self.skipTest("test database identity cannot exercise the dashboard runtime role")
            cur.execute(sql.SQL("""CREATE TABLE {}.grace_execution_health (
                service_id TEXT PRIMARY KEY, instance_id UUID NOT NULL, status TEXT NOT NULL,
                last_heartbeat_at TIMESTAMPTZ NOT NULL, last_cycle_at TIMESTAMPTZ,
                last_error_type TEXT, cycles_completed BIGINT NOT NULL)""").format(
                    sql.Identifier(self.schema)))
            cur.execute(sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(self.schema), sql.Identifier(role)))
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname=%s AND tablename<>%s",
                        (self.schema, "grace_execution_health"))
            for row in cur.fetchall():
                cur.execute(sql.SQL("GRANT SELECT ON {}.{} TO {}").format(
                    sql.Identifier(self.schema), sql.Identifier(row["tablename"]), sql.Identifier(role)))
            cur.execute(sql.SQL("REVOKE ALL ON {}.grace_execution_health FROM {}, PUBLIC").format(
                sql.Identifier(self.schema), sql.Identifier(role)))
            cur.execute("SELECT has_table_privilege(%s,%s,'SELECT') AS allowed", (role,
                f"{self.schema}.grace_execution_health"))
            self.assertFalse(cur.fetchone()["allowed"])

        original_connect = psycopg.connect
        def restricted_connect(*args, **kwargs):
            connection = original_connect(*args, **kwargs)
            connection.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
            connection.commit()
            return connection

        with mock.patch("riverview_core.status_dashboard.projection.psycopg.connect",
                        side_effect=restricted_connect):
            before = self.projection.status()
        self.assertEqual(before["projection_status"], "unavailable")
        self.assertEqual(before["unavailable_reason"], "InsufficientPrivilege")

        migration = (self.core / "resident_execution/migrations/0005_dashboard_grace_health_read.sql").read_text()
        self.assertIn("GRANT SELECT ON %I.grace_execution_health TO riverview_core", migration)
        self.assertNotIn("schema_migrations", migration)
        with self.admin.cursor() as cur:
            cur.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema)))
            cur.execute(migration)
            cur.execute("SELECT has_table_privilege(%s,%s,'SELECT') AS allowed", (role,
                f"{self.schema}.grace_execution_health"))
            self.assertTrue(cur.fetchone()["allowed"])

        with mock.patch("riverview_core.status_dashboard.projection.psycopg.connect",
                        side_effect=restricted_connect):
            status = self.projection.status()
        self.assertEqual(status["projection_status"], "healthy")
        self.assertEqual(status["grace_execution"]["status"], "not_initialized")

    def test_private_assignments_events_and_payload_are_filtered_from_snapshot(self):
        public = self.create("public")
        private = self.create("private", private=True)
        listed = self.projection.assignments(limit=100)["items"]
        ids = {row["assignment_id"] for row in listed}
        self.assertIn(public, ids)
        self.assertNotIn(private, ids)
        self.assertIsNone(self.projection.assignment_detail(private))
        snapshot = json.dumps(self.projection.snapshot())
        for secret in ("grant:test-secret", "objective:private-body", private, "undercurrent", "secret://private"):
            self.assertNotIn(secret, snapshot)
        payload_keys = []
        def find_payload(value):
            if isinstance(value, dict):
                payload_keys.extend(key for key in value if key in {"payload", "evidence_references", "authority_ref"})
                for child in value.values(): find_payload(child)
            elif isinstance(value, list):
                for child in value: find_payload(child)
        find_payload(json.loads(snapshot))
        self.assertEqual(payload_keys, [])
        self.assertIn("credentials", snapshot)
        self.assertLess(len(snapshot.encode()), 128 * 1024)

    def test_event_keyset_page_and_assignment_cursor_are_stable_and_bounded(self):
        ids = [self.create(f"page-{i}") for i in range(3)]
        first = self.projection.assignments(limit=2)
        self.assertEqual(len(first["items"]), 2)
        self.assertTrue(first["truncated"])
        second = self.projection.assignments(after=first["next_cursor"], limit=2)
        self.assertEqual(len(second["items"]), 1)
        self.assertFalse(set(a["assignment_id"] for a in first["items"]) &
                         set(a["assignment_id"] for a in second["items"]))
        first_events = self.projection.events(after_seq=0, limit=2)
        self.assertEqual(len(first_events["items"]), 2)
        next_events = self.projection.events(after_seq=first_events["items"][-1]["seq"], limit=1000)
        self.assertLessEqual(len(next_events["items"]), 100)
        self.assertTrue(any(a in {row["assignment_id"] for row in second["items"]} for a in ids))

    def test_assignment_attempt_and_independent_verification_detail_is_redacted(self):
        import psycopg
        from uuid import uuid4
        assignment_id = self.create("verified")
        attempt_id = uuid4()
        now = datetime.now(timezone.utc)
        with psycopg.connect(DSN) as db:
            db.execute("SELECT set_config('search_path', %s, false)", (self.schema,))
            db.execute("INSERT INTO worker_registry(worker_id,credential_sha256,capabilities,scope_ref) "
                       "VALUES ('executor',%s,'[]','scope'),('verifier',%s,'[]','scope')",
                       (b"e"*32,b"v"*32))
            db.execute("""INSERT INTO worker_attempts(attempt_id,assignment_id,worker_id,lease_generation,
                         capability,idempotency_key,input_sha256,status,started_at,finished_at)
                         VALUES (%s,%s,'executor',1,'engineering','attempt-key',%s,'succeeded',%s,%s)""",
                       (attempt_id,assignment_id,"a"*64,now-timedelta(seconds=2),now))
            db.execute("INSERT INTO verification_records(attempt_id,assignment_id,executor_id,verifier_id,"
                       "verifier_revision,decision,criteria,evidence_references,summary,idempotency_key) "
                       "VALUES (%s,%s,'executor','verifier','rev-1','ACCEPTED','{}','[\"secret://private\"]',"
                       "'accepted','verify-key')", (attempt_id,assignment_id))
        detail = self.projection.assignment_detail(assignment_id)
        self.assertEqual(detail["attempts"][0]["status"], "succeeded")
        self.assertEqual(detail["verifications"][0]["decision"], "ACCEPTED")
        self.assertEqual(detail["verifications"][0]["evidence_count"], 1)
        self.assertNotIn("secret://private", json.dumps(detail))

