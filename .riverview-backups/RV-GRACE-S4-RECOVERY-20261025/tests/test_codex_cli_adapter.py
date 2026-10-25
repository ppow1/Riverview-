# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_codex_cli_adapter.py
# Component: RESIDENT-ORCHESTRATION
# Revision: 1.2.12
# Changed: 2026-10-25 UTC | RV-GRACE-S3-RUNTIME-EVIDENCE-20261025 | Forward verified durable CME recovery exchange evidence into bounded same-assignment artifact rework.
# Changed: 2026-10-21 UTC | RV-W4-GRACE-CRITERIA-CLASSIFICATION-20261021 | Ensure original Steward instructions remain separate from formal execution criteria
# Changed: 2026-10-21 UTC | RV-W4-GRACE-FOCUSED-CORRECTIONS | Reject negative JSON outcomes and check exact artifact literals at the independent Codex verifier boundary
# Changed: 2026-10-20 UTC | RV-GRACE-DYNAMIC-ARTIFACT-CONTRACT-001 | Cover dynamic assignment artifacts, multi-file persistence, and independent contract verification
# Changed: 2026-10-20 UTC | RV-GRACE-MULTISTEP-PROVENANCE-RECOVERY-001 | Cover concurrent sibling-step execution when the objective's latest assignment pointer names the other step.
# Changed: 2026-10-19 UTC | RV-C1-GRACE-REJECTION-ROLE-CLARIFICATION | Verify paraphrased substantive content passes integrity checks and Grace receives only digest-verified bounded artifact text.
# Purpose: Verify bounded subscription-authenticated Codex adapter contracts
# Execution Model: Isolated temporary Git repository and synthetic executable
# Observability: Assertions inspect sanitized adapter status and artifact metadata
# Dependencies: Python 3; Git
# Authority: No live model, service, or account credential is used
# Changed: 2026-10-13 UTC | RV-CODEX-CLI-ADAPTER-001 | Add isolated adapter contract tests
# Changed: 2026-10-13 UTC | RV-GRACE-CODEX-DISPATCH | Test leased worker action and independent Markdown verification contracts
# Changed: 2026-10-13 UTC | RV-CODEX-SUBSCRIPTION-SUPERVISOR-001 | Verify API-key-free child environment and interactive session gate
# Changed: 2026-10-15 UTC | RV-GRACE-OWNER-SESSION-EXECUTION-001 | Verify persistent owner-session mode without TTY or credential copy
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-SANDBOX-READINESS-001 | Verify workspace sandbox failure blocks before dispatch
# Changed: 2026-10-15 UTC | RV-GRACE-CODEX-REPOSITORY-PROVENANCE-001 | Verify scoped Git trust, separate source/repository pins, and explicit process-start provenance
# Changed: 2026-10-16 UTC | RV-GRACE-OBJ-SOURCE-PROVENANCE-001 | Verify older objective evidence remains valid under current grounding provenance
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-BOUNDED-RETRY-001 | Verify a single committed deliverable is accepted and all other workspace paths are rejected
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-OWNER-STATE-001 | Verify service-local writable Codex state, read-only auth bind, and missing Code Mode host rejection
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-SYSTEMD-NETLINK-001 | Require the readiness probe to exercise bubblewrap network namespace setup
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-ENABLE-001 | Require persistent Code Mode feature activation in the Codex CLI invocation
# Changed: 2026-10-16 UTC | RV-GRACE-CODEX-CODE-MODE-MDWE-001 | Require both Code Mode features and pinned package-path discovery for the companion host
# Changed: 2026-10-16 UTC | RV-GRACE-VERIFIER-REVALIDATION-001 | Cover objective-step criteria binding and one-file metadata independently of substantive prose review
# Changed: 2026-10-17 UTC | RV-GRACE-ACCEPTANCE-CRITERIA-001 | Verify canonical persisted step criteria remain available to independent verification
# Contracts: src/riverview_core/resident_execution/codex_cli.py
# Tests: python3 -m unittest tests.test_codex_cli_adapter -v
# History: Git
# =============================================================================
"""Synthetic tests for the Codex CLI boundary; never invokes the real CLI."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from riverview_core.resident_reasoning import ArtifactRequirement
from riverview_core.resident_execution.codex_cli import (
    CAPABILITY, CodexAdapterError, CodexAssignment, CodexCLIExecutionAdapter,
)
from riverview_core.resident_execution.codex_workflow import (
    CodexArtifactVerifier, CodexWorkAction,
)
from riverview_core.worker_adapter.knowledge import KnowledgeResult, KnowledgeStatus
from riverview_core.worker_adapter.recovery import _codex_artifact_files


class CodexCLIAdapterTests(unittest.TestCase):
    def setUp(self):
        self.sandbox_patch = patch.object(CodexCLIExecutionAdapter,
            "_verify_workspace_sandbox", return_value=None)
        self.sandbox_patch.start()
        self.addCleanup(self.sandbox_patch.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "source"
        self.repo.mkdir(mode=0o700)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "README.md").write_text("Pinned test source.\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.repo), "add", "README.md"], check=True)
        test_env = dict(os.environ, GIT_AUTHOR_NAME="Riverview Test",
                        GIT_AUTHOR_EMAIL="riverview-test@example.invalid",
                        GIT_COMMITTER_NAME="Riverview Test",
                        GIT_COMMITTER_EMAIL="riverview-test@example.invalid")
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "fixture"],
                       check=True, env=test_env)
        self.revision = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        self.codex = self.root / "fake-codex"
        self.codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            "args=sys.argv[1:]\n"
            "required=['--sandbox','workspace-write','--ephemeral','--ignore-user-config']\n"
            "required += ['approval_policy=\"never\"','sandbox_workspace_write.network_access=false']\n"
            "if any(value not in args for value in required): raise SystemExit(8)\n"
            "if '--fail' in args: raise SystemExit(4)\n"
            "prompt=sys.stdin.read()\n"
            "contract=json.loads(prompt.split('Artifact contract:\\n',1)[1])\n"
            "records=[]\n"
            "for item in contract:\n"
            " path=pathlib.Path.cwd()/item['path']; path.parent.mkdir(parents=True,exist_ok=True)\n"
            " body={'application/json':'{\\\"ok\\\":true}', 'text/csv':'id,value\\\\n1,ok\\\\n', 'application/xml':'<root/>', 'text/markdown':'# Verified\\\\n', 'text/plain':'Verified fixture\\\\n'}[item['media_type']]\n"
            " path.write_text(body)\n"
            " records.append({'name':item['name'],'path':item['path'],'summary':'Created fixture'})\n"
            "out=pathlib.Path(args[args.index('--output-last-message')+1])\n"
            "out.write_text(json.dumps({'status':'ARTIFACTS_PRODUCED','artifacts':records,'summary':'Created fixture'}))\n",
            encoding="utf-8")
        self.codex.chmod(0o700)
        self.codex_home = self.root / "service-codex-home"
        self.workspace = self.root / "workspaces"
        self.artifacts = self.root / "artifacts"
        for path in (self.codex_home, self.workspace, self.artifacts):
            path.mkdir(mode=0o700)

    def tearDown(self):
        self.temp.cleanup()

    def adapter(self):
        return CodexCLIExecutionAdapter(executable=str(self.codex),
            repository_path=self.repo, repository_reference="repo://example/test",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts)

    def assignment(self, **changes):
        values = dict(assignment_id="assignment:test-1", objective_id="objective:test-1",
            repository_reference="repo://example/test", repository_revision=self.revision,
            task_scope="Create a short test deliverable.",
            acceptance_criteria=("The report contains a verified summary.",),
            artifact_requirements=(ArtifactRequirement("report", "reports/summary.txt", "text/plain",
                ("The report contains a verified summary.",)),), timeout_seconds=5)
        values.update(changes)
        return CodexAssignment(**values)

    def test_fixed_pinned_workspace_produces_assignment_bound_artifact(self):
        result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "DELIVERABLE_PRODUCED")
        self.assertTrue(result.execution_started)
        self.assertEqual(result.capability, CAPABILITY)
        self.assertTrue(result.verification_required)
        path = self.artifacts / result.artifact_name
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertTrue(path.read_text(encoding="utf-8").startswith("Verified fixture"))
        self.assertEqual(result.artifact_bytes, path.stat().st_size)
        self.assertEqual(len(result.artifact_sha256), 64)
        self.assertEqual(result.source_artifact_name, "reports/summary.txt")
        self.assertEqual(result.changed_files, ("reports/summary.txt",))
        self.assertEqual(result.artifacts[0]["media_type"], "text/plain")
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_proposal_diagnostic_work_receives_bounded_read_only_authoritative_evidence(self):
        evidence = {"schema":"rv.grace-diagnostic-runtime-evidence.v1", "read_only":True,
            "referenced_historical_objectives":[{"objective_id":
                "objective:grace-conversation:74b28df1-ea8e-5944-8bde-0ff56b117794",
                "status":"CANCELLED", "event_counts":{
                    "execution.reasoning_attempted":599,
                    "execution.reasoning_failed":599}}]}
        criteria = ["Report reasoning attempts and failures from the referenced objective.",
            "State transitions are durably persisted in the authoritative event history."]
        requirements = [{"name":"diagnostic", "path":"reports/diagnostic.txt",
            "media_type":"text/plain", "acceptance_criteria":criteria, "max_bytes":32768}]

        class Pipeline:
            def get_objective(_self, objective_id):
                return {"objective_id":objective_id, "status":"WORK_ORDER_CREATED",
                    "request":"Inspect objective:grace-conversation:74b28df1-ea8e-5944-8bde-0ff56b117794",
                    "source_revision":self.revision, "source_sha256":"a" * 64,
                    "evidence":{"status":"VERIFIED", "source_revision":self.revision,
                        "source_sha256":"a" * 64}, "proposal":{"steps":[{}]}}
            def proposal_step_for_assignment(_self, _objective_id, _assignment_id):
                return {"objective":"Write a bounded diagnostic report",
                    "acceptance_criteria":criteria, "artifact_requirements":requirements}
            def diagnostic_runtime_evidence(_self, objective_id):
                self.assertEqual(objective_id, "objective:diagnostic:test")
                return evidence

        adapter = self.adapter()
        captured = {}
        def execute(assignment):
            captured["assignment"] = assignment
            return SimpleNamespace(status="DELIVERABLE_PRODUCED", artifact_name="diagnostic.json",
                artifact_sha256="b" * 64, artifact_bytes=10, repository_revision=self.revision,
                source_artifact_name="reports/diagnostic.txt", changed_files=("reports/diagnostic.txt",),
                artifacts=(), rework_verification_id=None, detail_code=None)
        adapter.execute = execute
        (self.artifacts / "diagnostic.json").write_text("fixture", encoding="utf-8")
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=self.revision,
            source_sha256="b" * 64, retrieval_complete=True)

        CodexWorkAction(Pipeline(), adapter, "repo://example/test", 5)(
            {"id":"assignment:diagnostic:test", "objective_ref":"objective:diagnostic:test"}, grounded)

        request = captured["assignment"]
        self.assertEqual(dict(request.runtime_evidence), evidence)
        prompt = CodexCLIExecutionAdapter._prompt(request)
        self.assertIn("Read-only server-derived runtime evidence", prompt)
        self.assertIn("do not claim this worker performed the recorded transitions", prompt)
        self.assertIn("execution.reasoning_attempted", prompt)

    def test_cme_rework_receives_persisted_exchange_evidence_without_runtime_access(self):
        criteria = ["The artifact identifies the authorized Luna request and its actual outcome."]
        requirements = [{"name":"recovery", "path":"reports/recovery.json",
            "media_type":"application/json", "acceptance_criteria":criteria,
            "max_bytes":32768}]
        assignment_id = "assignment:grace:s3-fixture"
        objective_id = "objective:grace:s3-fixture"
        verification_id = "2eb56a17-5ab1-4697-90c2-0ebe20843267"
        evidence = {"schema":"rv.grace.cme-recovery-runtime-evidence.v1",
            "read_only":True, "objective_id":objective_id,
            "assignment_id":assignment_id, "step_id":"s3",
            "stall_event_id":"8671a141-da3c-47c5-960d-324e3c51eeef",
            "progress_sequence":223, "recovery_action":"REWORK_PROPOSED",
            "exchange":{"request_id":"29e66ad4-5eba-5e55-8e88-1003b635235e",
                "correlation_id":"322f4240-37cf-4b01-abb3-0a0673ba4d64",
                "provider_id":"gpt-6-luna", "provider_model":"gpt-6-luna",
                "response_id":"resp_0df0c5556ec6ec00016add7e1cdb6887d284d801ed6187e2fe",
                "response_sha256":"a"*64, "delivery_state":"grace_consumed",
                "provider_attempt_count":1, "usage":{"input_tokens":4731,
                    "output_tokens":452,"cost_usd":"0.0006991"}},
            "authorization":{"authorization_id":"556cfa24-0a55-5000-9b31-c11242d749a4",
                "retry_grant_event_id":"d621148a-7426-53bb-9434-d476383713f6",
                "retry_consumption_event_id":"f631870f-a37d-488b-82b5-cb6174e80ea2",
                "reservation_event_id":"fa27a745-9d1d-4797-87a6-441ba3e3ff1e",
                "reserved_cost_usd":"0.05","actual_cost_usd":"0.0006991",
                "retry_exception_consumed":True}}

        class Pipeline:
            def get_objective(_self, value):
                self.assertEqual(value, objective_id)
                return {"objective_id":objective_id,"status":"WORK_ORDER_CREATED",
                    "request":"Use the existing durable Luna recovery result.",
                    "source_revision":self.revision,"source_sha256":"a"*64,
                    "evidence":{"status":"VERIFIED","source_revision":self.revision,
                        "source_sha256":"a"*64},"proposal":{"steps":[{}]}}
            def proposal_step_for_assignment(_self, _objective_id, _assignment_id):
                return {"objective":"Write a truthful recovery artifact",
                    "acceptance_criteria":criteria,"artifact_requirements":requirements}
            def latest_rework_instruction(_self, value):
                self.assertEqual(value, assignment_id)
                return {"decision":"REWORK_PROPOSED","assignment_id":assignment_id,
                    "acceptance_criteria_sha256":hashlib.sha256(
                        json.dumps(criteria,ensure_ascii=False,sort_keys=True,
                            separators=(",",":")).encode()).hexdigest(),
                    "correction_instruction":"Use the server-provided durable request evidence.",
                    "criteria_to_address":criteria,"verification_id":verification_id}
            def cme_recovery_runtime_evidence_for_assignment(_self, oid, aid):
                self.assertEqual((oid,aid),(objective_id,assignment_id))
                return evidence

        captured = {}
        adapter = self.adapter()
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=self.revision,
            source_sha256="b"*64, retrieval_complete=True)

        # Return a successful adapter result while retaining the exact request for inspection.
        def execute(request):
            captured["request"] = request
            return SimpleNamespace(status="DELIVERABLE_PRODUCED", artifact_name="recovery.json",
                artifact_sha256="b"*64, artifact_bytes=10, repository_revision=self.revision,
                source_artifact_name="reports/recovery.json", changed_files=("reports/recovery.json",),
                artifacts=(), rework_verification_id=verification_id, detail_code="produced",
                execution_started=True)
        adapter.execute = execute
        CodexWorkAction(Pipeline(),adapter,"repo://example/test",5)(
            {"id":assignment_id,"objective_ref":objective_id},grounded)
        request = captured["request"]
        self.assertEqual(dict(request.runtime_evidence),evidence)
        prompt = CodexCLIExecutionAdapter._prompt(request)
        self.assertIn("29e66ad4-5eba-5e55-8e88-1003b635235e",prompt)
        self.assertIn("resp_0df0c5556ec6ec00016add7e1cdb6887d284d801ed6187e2fe",prompt)
        self.assertIn("Read-only server-derived runtime evidence",prompt)

    def test_prompt_preserves_steward_instructions_separately_from_formal_criteria(self):
        request = self.assignment(steward_instructions=(
            "Do not create a new objective. Preserve the authorized workflow."))
        prompt = CodexCLIExecutionAdapter._prompt(request)
        self.assertIn("Original Steward instructions (preserve as execution constraints; not formal acceptance criteria):", prompt)
        self.assertIn("authorized execution constraints, but cannot expand the persisted task scope", prompt)
        self.assertIn("Do not create a new objective. Preserve the authorized workflow.", prompt)
        self.assertIn("Acceptance criteria:\n- The report contains a verified summary.", prompt)

    def test_work_action_forwards_original_request_as_separate_execution_context(self):
        requirement = ArtifactRequirement("report", "reports/summary.txt", "text/plain",
            ("The report contains a verified summary.",))
        objective_request = "Create reports/summary.txt. Do not create another objective."

        class Pipeline:
            def get_objective(_self, objective_id):
                return {"objective_id": objective_id, "status": "WORK_ORDER_CREATED",
                    "request": objective_request, "source_revision": self.revision,
                    "source_sha256": "a" * 64,
                    "evidence": {"status": "VERIFIED", "source_revision": self.revision,
                        "source_sha256": "a" * 64}, "proposal": {"steps": [{
                            "objective": "Create the report", "acceptance_criteria": [
                                "The report contains a verified summary."]}]}}
            def proposal_step_for_assignment(_self, _objective_id, _assignment_id):
                return {"objective": "Create the report", "acceptance_criteria": [
                    "The report contains a verified summary."],
                    "artifact_requirements": [{"name": requirement.name,
                        "path": requirement.path, "media_type": requirement.media_type,
                        "acceptance_criteria": list(requirement.acceptance_criteria),
                        "max_bytes": requirement.max_bytes}]}

        captured = []
        adapter = self.adapter()
        adapter.execute = lambda request: captured.append(request) or SimpleNamespace(
            status="DELIVERABLE_PRODUCED", artifact_name="report.txt",
            artifact_sha256="b" * 64, artifact_bytes=10,
            repository_revision=self.revision, source_artifact_name="reports/summary.txt",
            changed_files=("reports/summary.txt",), artifacts=(),
            rework_verification_id=None, detail_code="produced", execution_started=True)
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=self.revision,
            source_sha256="b" * 64, retrieval_complete=True)

        CodexWorkAction(Pipeline(), adapter, "repo://example/test", 5)(
            {"id": "assignment:test-1", "objective_ref": "objective:test-1"}, grounded)

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].steward_instructions, objective_request)
        self.assertEqual(captured[0].acceptance_criteria,
            ("The report contains a verified summary.",))

    def test_committed_artifact_is_accepted_when_it_is_the_only_changed_path(self):
        self.codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json,pathlib,subprocess,sys\n"
            "args=sys.argv[1:]\n"
            "prompt=sys.stdin.read()\n"
            "contract=json.loads(prompt.split('Artifact contract:\\n',1)[1])\n"
            "records=[]\n"
            "for item in contract:\n"
            " path=pathlib.Path.cwd()/item['path']; path.parent.mkdir(parents=True,exist_ok=True)\n"
            " path.write_text('\\\"ok\\\": true' if item['media_type']=='application/json' else 'Verified fixture')\n"
            " records.append({'name':item['name'],'path':item['path'],'summary':'Created'})\n"
            "subprocess.run(['/usr/bin/git','add','--',*[item['path'] for item in contract]],check=True)\n"
            "subprocess.run(['/usr/bin/git','-c','user.name=Riverview Test',"
            "'-c','user.email=riverview-test@example.invalid','commit','-m','bounded deliverable'],"
            "check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
            "out=pathlib.Path(args[args.index('--output-last-message')+1])\n"
            "out.write_text(json.dumps({'status':'ARTIFACTS_PRODUCED','artifacts':records,'summary':'Created fixture'}))\n",
            encoding="utf-8")
        result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "DELIVERABLE_PRODUCED")
        self.assertEqual(result.detail_code, "independent_verification_required")
        self.assertTrue((self.artifacts / result.artifact_name).is_file())
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_extra_workspace_path_is_rejected_even_when_required_artifact_exists(self):
        self.codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json,pathlib,sys\n"
            "args=sys.argv[1:]\n"
            "prompt=sys.stdin.read()\n"
            "contract=json.loads(prompt.split('Artifact contract:\\n',1)[1])\n"
            "records=[]\n"
            "for item in contract:\n"
            " path=pathlib.Path.cwd()/item['path']; path.parent.mkdir(parents=True,exist_ok=True); path.write_text('Verified fixture')\n"
            " records.append({'name':item['name'],'path':item['path'],'summary':'Created'})\n"
            "(pathlib.Path.cwd()/'unexpected.txt').write_text('out of scope')\n"
            "out=pathlib.Path(args[args.index('--output-last-message')+1])\n"
            "out.write_text(json.dumps({'status':'ARTIFACTS_PRODUCED','artifacts':records,'summary':'Created fixture'}))\n",
            encoding="utf-8")
        result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "INVALID_RESULT")
        self.assertEqual(result.detail_code, "workspace_change_set_invalid")
        self.assertTrue(result.execution_started)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_multiple_assignment_artifacts_support_json_and_csv_without_markdown_assumptions(self):
        requirements = (
            ArtifactRequirement("summary", "results/summary.json", "application/json",
                ("The summary has a boolean ok field.",)),
            ArtifactRequirement("rows", "results/rows.csv", "text/csv",
                ("The rows include a header and one result.",)),
        )
        requirement_data = [{"name": item.name, "path": item.path,
            "media_type": item.media_type, "acceptance_criteria": list(item.acceptance_criteria),
            "max_bytes": item.max_bytes} for item in requirements]
        class Pipeline:
            def get_objective(_self, objective_id):
                return {"objective_id": objective_id, "status": "WORK_ORDER_CREATED",
                    "request": "Create results/summary.json and results/rows.csv.",
                    "source_revision": self.revision, "source_sha256": "a" * 64,
                    "evidence": {"status": "VERIFIED", "source_revision": self.revision,
                        "source_sha256": "a" * 64}, "proposal": {"steps": [{
                            "objective": "Create report files", "acceptance_criteria": ["Complete" ]}]}}
            def proposal_step_for_assignment(_self, _objective_id, _assignment_id):
                return {"objective": "Create report files", "acceptance_criteria": ["Complete"],
                    "artifact_requirements": requirement_data}
        pipeline = Pipeline()
        assignment = {"id": "assignment:test-1", "objective_ref": "objective:test-1"}
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=self.revision,
            source_sha256="b" * 64, retrieval_complete=True)
        result = CodexWorkAction(pipeline, self.adapter(), "repo://example/test", 5)(assignment, grounded)
        self.assertEqual([item["path"] for item in result["artifacts"]],
            ["results/summary.json", "results/rows.csv"])
        self.assertEqual([item["media_type"] for item in result["artifacts"]],
            ["application/json", "text/csv"])
        self.assertEqual(set(result["changed_files"]), {item.path for item in requirements})
        self.assertTrue(all((self.artifacts / item["storage_name"]).is_file()
            for item in result["artifacts"]))
        verification = CodexArtifactVerifier(self.artifacts, pipeline).verify(assignment,
            {"status": "succeeded", "capability": CAPABILITY,
             "attempt_id": "attempt:multi-artifact"}, result)
        self.assertEqual(verification.status.value, "ACCEPTED")
        changed = dict(result)
        changed["artifact_contract"] = [dict(item) for item in result["artifact_contract"]]
        changed["artifact_contract"][0]["acceptance_criteria"] = ["unauthorized criterion"]
        rejected = CodexArtifactVerifier(self.artifacts, pipeline).verify(assignment,
            {"status": "succeeded", "capability": CAPABILITY,
             "attempt_id": "attempt:changed-contract"}, changed)
        self.assertEqual(rejected.status.value, "REJECTED")

    def test_codex_verifier_rejects_negative_json_and_requires_explicit_literal(self):
        from hashlib import sha256
        from riverview_core.resident_execution.codex_workflow import CodexArtifactVerifier

        assignment_id = "assignment:semantic-verifier"
        objective_id = "objective:semantic-verifier"
        requirement = {"name": "decision", "path": "reports/decision.json",
            "media_type": "application/json",
            "acceptance_criteria": ["Create `decision.json` containing exact phrase `verified delivery`."],
            "max_bytes": 32768}
        class Pipeline:
            def proposal_step_for_assignment(_self, _objective_id, _assignment_id):
                return {"artifact_requirements": [requirement]}

        storage_dir = "codex-" + sha256(assignment_id.encode()).hexdigest()
        basename = sha256(requirement["name"].encode()).hexdigest()[:12]
        artifact_directory = self.artifacts / storage_dir
        artifact_directory.mkdir(mode=0o700)
        artifact = artifact_directory / basename

        def result_for(body):
            raw = body.encode("utf-8")
            artifact.write_bytes(raw)
            artifact.chmod(0o600)
            digest = sha256(raw).hexdigest()
            entry = {"name": requirement["name"], "path": requirement["path"],
                "media_type": requirement["media_type"], "acceptance_criteria":
                    requirement["acceptance_criteria"], "storage_name": storage_dir + "/" + basename,
                "sha256": digest, "bytes": len(raw)}
            return {"status": "SUCCEEDED", "artifact_schema": "rv.codex-cli.artifacts.v3",
                "assignment_id": assignment_id, "objective_id": objective_id,
                "artifact_name": entry["storage_name"], "artifact_path": str(artifact),
                "artifact_sha256": digest, "artifact_bytes": len(raw),
                "source_artifact_name": requirement["path"],
                "changed_files": [requirement["path"]], "source_revision": "a" * 40,
                "source_sha256": "b" * 64, "repository_revision": "c" * 40,
                "artifact_contract": [requirement], "artifacts": [entry]}

        assignment = {"id": assignment_id, "objective_ref": objective_id}
        attempt = {"status": "succeeded", "capability": CAPABILITY,
            "attempt_id": "attempt:semantic-verifier"}
        verifier = CodexArtifactVerifier(self.artifacts, Pipeline())
        for negative_json in (
                '{"decision":"REJECTED","report":"verified delivery"}',
                '{"verification_decision":"FAILED_TESTS","report":"verified delivery"}',
                '{"result":{"status":"blocked"},"report":"verified delivery"}'):
            rejected = verifier.verify(assignment, attempt, result_for(negative_json))
            self.assertEqual(rejected.status.value, "REJECTED")
            self.assertFalse(rejected.criteria["artifact_semantic_outcome_not_negative"])

        missing_literal = verifier.verify(assignment, attempt,
            result_for('{"decision":"ACCEPTED","report":"delivery verified"}'))
        self.assertEqual(missing_literal.status.value, "REJECTED")
        self.assertFalse(missing_literal.criteria["explicit_artifact_acceptance_clauses_satisfied"])

        metadata_only = verifier.verify(assignment, attempt,
            result_for('{"decision":"ACCEPTED"}'))
        self.assertEqual(metadata_only.status.value, "REJECTED")
        self.assertFalse(metadata_only.criteria["explicit_artifact_acceptance_clauses_satisfied"],
                         "echoing the criterion in artifact metadata is not deliverable evidence")

        accepted = verifier.verify(assignment, attempt,
            result_for('{"decision":"ACCEPTED","report":"verified delivery"}'))
        self.assertEqual(accepted.status.value, "ACCEPTED", dict(accepted.criteria))

    def test_recovery_finds_assignment_bound_extensionless_multi_artifact_set(self):
        assignment_id = "assignment:recovery-dynamic-artifacts"
        key = __import__("hashlib").sha256(assignment_id.encode()).hexdigest()
        directory = self.artifacts / f"codex-{key}"
        directory.mkdir(mode=0o700)
        directory.chmod(0o700)
        for name, body in (("a1b2c3d4e5f6", b"{\"ok\":true}"),
                           ("0f1e2d3c4b5a", b"id,value\n1,ok\n")):
            path = directory / name
            path.write_bytes(body)
            path.chmod(0o600)
        recovered = _codex_artifact_files(self.artifacts, assignment_id)
        self.assertEqual({path.name for path in recovered}, {"a1b2c3d4e5f6", "0f1e2d3c4b5a"})
        self.assertTrue(all(path.parent == directory for path in recovered))

    def test_artifact_requirement_rejects_traversal_and_unsupported_type(self):
        with self.assertRaises(ValueError):
            ArtifactRequirement("escape", "../outside.txt", "text/plain", ("safe",))
        with self.assertRaises(ValueError):
            ArtifactRequirement("binary", "image.bin", "application/octet-stream", ("safe",))

    def test_codex_action_failure_exposes_only_bounded_retry_metadata(self):
        from riverview_core.resident_execution.codex_workflow import CodexActionFailure
        failure = CodexActionFailure("workspace_change_set_invalid", execution_started=True)
        self.assertEqual(failure.code, "workspace_change_set_invalid")
        self.assertTrue(failure.execution_started)
        self.assertTrue(failure.retryable_without_durable_artifact)

    def test_wrong_repository_and_revision_fail_before_codex(self):
        wrong_repo = self.adapter().execute(self.assignment(repository_reference="repo://other"))
        self.assertEqual(wrong_repo.detail_code, "repository_not_registered")
        wrong_revision = "0" * 40
        stale = self.adapter().execute(self.assignment(repository_revision=wrong_revision))
        self.assertEqual(stale.status, "WAITING_FOR_EVIDENCE")
        self.assertEqual(stale.detail_code, "repository_revision_mismatch")
        self.assertFalse(stale.execution_started)

    def test_git_trust_is_scoped_to_one_private_command_configuration(self):
        original_run = subprocess.run
        observed = []

        def capture(command, **kwargs):
            config = kwargs.get("env", {}).get("GIT_CONFIG_GLOBAL")
            if config:
                path = Path(config)
                observed.append((path.read_text(encoding="utf-8"),
                                 path.stat().st_mode & 0o777))
            return original_run(command, **kwargs)

        with patch("riverview_core.resident_execution.codex_cli.subprocess.run",
                   side_effect=capture):
            self.assertEqual(self.adapter().repository_revision(), self.revision)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][1], 0o600)
        self.assertIn(str(self.repo.resolve()), observed[0][0])
        self.assertNotIn("directory = *", observed[0][0])
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_legacy_git_ownership_refusal_is_detected_without_logging_git_output(self):
        adapter = self.adapter()
        completed = subprocess.CompletedProcess(
            ["git"], 128, stdout=b"", stderr=b"fatal: detected dubious ownership in repository")
        with patch.object(adapter, "_preflight", return_value=(self.codex, self.repo)), \
             patch("riverview_core.resident_execution.codex_cli.subprocess.run",
                   return_value=completed):
            self.assertTrue(adapter.legacy_git_ownership_refused())

    def test_unavailable_workspace_sandbox_fails_closed_before_codex(self):
        with patch.object(CodexCLIExecutionAdapter, "_verify_workspace_sandbox",
                          side_effect=CodexAdapterError("codex_sandbox_unavailable")):
            result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_sandbox_unavailable")
        self.assertFalse(result.execution_started)
        self.assertFalse(list(self.artifacts.iterdir()))
        self.assertFalse(list(self.workspace.iterdir()))

    def test_workspace_sandbox_probe_exercises_network_namespace_setup(self):
        self.sandbox_patch.stop()
        completed = subprocess.CompletedProcess(["bwrap"], 0)
        with patch("riverview_core.resident_execution.codex_cli.shutil.which",
                   return_value="/usr/bin/bwrap"), \
             patch("riverview_core.resident_execution.codex_cli.subprocess.run",
                   return_value=completed) as run:
            CodexCLIExecutionAdapter._verify_workspace_sandbox()
        command = run.call_args.args[0]
        self.assertIn("--unshare-net", command)
        self.assertEqual(command[-1], "/bin/true")
        self.assertEqual(run.call_args.kwargs["timeout"], 5)

    def test_network_namespace_sandbox_failure_is_reported_as_unavailable(self):
        self.sandbox_patch.stop()
        failed = subprocess.CompletedProcess(["bwrap"], 1)
        with patch("riverview_core.resident_execution.codex_cli.shutil.which",
                   return_value="/usr/bin/bwrap"), \
             patch("riverview_core.resident_execution.codex_cli.subprocess.run",
                   return_value=failed):
            with self.assertRaisesRegex(CodexAdapterError, "codex_sandbox_unavailable"):
                CodexCLIExecutionAdapter._verify_workspace_sandbox()

    def test_cli_failure_is_sanitized_and_creates_no_artifact(self):
        self.codex.write_text(self.codex.read_text().replace("args=sys.argv[1:]", "args=sys.argv[1:] + ['--fail']"),
                              encoding="utf-8")
        result = self.adapter().execute(self.assignment())
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_process_failed")
        self.assertTrue(result.execution_started)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_timeout_kills_the_codex_process_and_returns_no_artifact(self):
        self.codex.write_text(
            "#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n", encoding="utf-8")
        self.codex.chmod(0o700)
        result = self.adapter().execute(self.assignment(timeout_seconds=1))
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_timeout")
        self.assertTrue(result.execution_started)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_personal_codex_home_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dedicated service CODEX_HOME"):
            CodexCLIExecutionAdapter(executable=str(self.codex), repository_path=self.repo,
                repository_reference="repo://example/test", codex_home=Path.home() / ".codex",
                workspace_root=self.workspace, artifact_root=self.artifacts)

    def test_concurrent_multistep_action_uses_exact_durable_step_link(self):
        knowledge_revision = "a" * 40
        objective_revision = "c" * 40
        objective_digest = "d" * 64
        class Pipeline:
            def get_objective(self, _objective_id):
                return {"objective_id": "objective:test-1", "status": "WORK_ORDER_CREATED",
                    "request": "Create reports/summary.txt.",
                    "assignment_id": "assignment:test-s4", "source_revision": objective_revision,
                    "source_sha256": objective_digest,
                    "evidence": {"status": "VERIFIED", "source_revision": objective_revision,
                                 "source_sha256": objective_digest},
                    "proposal": {"steps": [{"objective": "Create bounded Markdown.",
                        "acceptance_criteria": ["The deliverable exists."]}]}}
            def proposal_step_for_assignment(self, objective_id, assignment_id):
                self.assertion = (objective_id, assignment_id)
                return {"objective": "Create bounded Markdown.",
                        "acceptance_criteria": ["The report contains a verified summary."],
                        "depends_on": [], "execution_capability": CAPABILITY,
                        "authorized_paths": [], "test_targets": [],
                        "artifact_requirements": [{"name":"report", "path":"reports/summary.txt",
                            "media_type":"text/plain", "acceptance_criteria":[
                                "The report contains a verified summary."], "max_bytes":32768}]}
        adapter = self.adapter()
        pipeline = Pipeline()
        action = CodexWorkAction(pipeline, adapter, "repo://example/test", 5)
        assignment = {"id": "assignment:test-1", "objective_ref": "objective:test-1"}
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=knowledge_revision,
            source_sha256="b" * 64, retrieval_complete=True)
        result = action(assignment, grounded)
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["source_revision"], knowledge_revision)
        self.assertEqual(result["source_sha256"], "b" * 64)
        self.assertEqual(result["repository_revision"], self.revision)
        self.assertTrue(Path(result["artifact_path"]).is_file())
        verification = CodexArtifactVerifier(self.artifacts, pipeline).verify(
            assignment, {"status": "succeeded", "capability": CAPABILITY,
                       "attempt_id": "attempt:fixture"}, result)
        self.assertEqual(verification.status.value, "ACCEPTED")
        self.assertTrue(all(verification.criteria.values()))
        self.assertEqual(pipeline.assertion, ("objective:test-1", "assignment:test-1"))
        # The verifier uses criteria persisted on the pre-dispatch step, even if
        # the durable executor result omitted its redundant criteria echo.
        missing_echo = {key: value for key, value in result.items()
                        if key != "acceptance_criteria"}
        recovered = CodexArtifactVerifier(self.artifacts, pipeline).verify(
            assignment, {"status": "succeeded", "capability": CAPABILITY,
                        "attempt_id": "attempt:criteria-recovery"}, missing_echo)
        self.assertEqual(recovered.status.value, "ACCEPTED")

    def test_independent_verifier_rejects_changed_artifact(self):
        class Pipeline:
            def get_objective(self, _objective_id):
                return {"objective_id": "objective:test-1", "status": "WORK_ORDER_CREATED",
                    "request": "Create reports/summary.txt.",
                    "assignment_id": "assignment:test-1", "source_revision": revision,
                    "source_sha256": "a" * 64, "evidence": {"status": "VERIFIED",
                        "source_revision": revision, "source_sha256": "a" * 64},
                    "proposal": {"steps": [{"objective": "Create bounded Markdown.",
                        "acceptance_criteria": ["The report contains a verified summary."]}]}}
            def proposal_step_for_assignment(self, _objective_id, _assignment_id):
                return {"objective": "Create bounded report",
                    "acceptance_criteria": ["The report contains a verified summary."],
                    "artifact_requirements": [{"name":"report", "path":"reports/summary.txt",
                    "media_type":"text/plain", "acceptance_criteria":[
                        "The report contains a verified summary."], "max_bytes":32768}]}
        revision = self.revision
        adapter = self.adapter()
        action = CodexWorkAction(Pipeline(), adapter, "repo://example/test", 5)
        assignment = {"id": "assignment:test-1", "objective_ref": "objective:test-1"}
        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=revision,
            source_sha256="b" * 64, retrieval_complete=True)
        result = action(assignment, grounded)
        self.assertEqual(result["repository_revision"], revision)
        Path(result["artifact_path"]).write_text("# altered\n", encoding="utf-8")
        verification = CodexArtifactVerifier(self.artifacts, Pipeline()).verify(
            assignment, {"status": "succeeded", "capability": CAPABILITY,
                       "attempt_id": "attempt:fixture"}, result)
        self.assertEqual(verification.status.value, "REJECTED")

    def test_independent_verifier_reopens_digest_checked_dynamic_artifact_set_for_grace(self):
        criterion = "Explain that source implementation does not establish production commissioning."

        class Pipeline:
            def get_objective(_self, _objective_id):
                return {"objective_id": "objective:test-1", "status": "WORK_ORDER_CREATED",
                    "request": "Create reports/summary.txt.",
                    "assignment_id": "assignment:test-1", "source_revision": self.revision,
                    "source_sha256": "a" * 64, "evidence": {"status": "VERIFIED",
                        "source_revision": self.revision, "source_sha256": "a" * 64},
                    "proposal": {"steps": [{"step_id": "s1",
                        "objective": "Write a concise report",
                        "acceptance_criteria": [criterion]}]}}

            def proposal_step_for_assignment(_self, _objective_id, _assignment_id):
                return {"objective": "Write a concise report", "acceptance_criteria": [criterion],
                    "depends_on": [], "execution_capability": CAPABILITY,
                    "authorized_paths": [], "test_targets": [], "artifact_requirements": [
                        {"name":"report", "path":"reports/summary.txt", "media_type":"text/plain",
                         "acceptance_criteria":[criterion], "max_bytes":32768}]}

        grounded = KnowledgeResult(KnowledgeStatus.VERIFIED,
            source_references=("repo://docs/example.md",), source_revision=self.revision,
            source_sha256="b" * 64, retrieval_complete=True)
        result = CodexWorkAction(Pipeline(), self.adapter(), "repo://example/test", 5)(
            {"id": "assignment:test-1", "objective_ref": "objective:test-1"}, grounded)
        body = "The checked-in files describe implementation only; no live deployment was tested.\n"
        path = Path(result["artifact_path"])
        path.write_text(body, encoding="utf-8")
        path.chmod(0o600)
        result["artifact_bytes"] = len(body.encode("utf-8"))
        result["artifact_sha256"] = __import__("hashlib").sha256(body.encode("utf-8")).hexdigest()
        result["artifacts"][0]["bytes"] = result["artifact_bytes"]
        result["artifacts"][0]["sha256"] = result["artifact_sha256"]

        verifier = CodexArtifactVerifier(self.artifacts, Pipeline())
        verification = verifier.verify({"id": "assignment:test-1",
            "objective_ref": "objective:test-1"}, {"status": "succeeded",
            "capability": CAPABILITY, "attempt_id": "attempt:substantive"}, result)
        self.assertEqual(verification.status.value, "ACCEPTED")
        self.assertTrue(verification.criteria["authorized_acceptance_criteria_bound"])
        self.assertNotIn("acceptance_criteria_are_present", verification.criteria)

        review = verifier.read_artifact_for_grace_review("assignment:test-1", result)
        self.assertEqual(review["artifacts"][0]["body"], body)
        self.assertEqual(review["artifacts"][0]["sha256"], result["artifact_sha256"])
        path.write_text("# Changed after verification\n", encoding="utf-8")
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "protection metadata|integrity"):
            verifier.read_artifact_for_grace_review("assignment:test-1", result)

    def test_codex_child_does_not_receive_an_api_key(self):
        script = self.codex.read_text(encoding="utf-8")
        self.codex.write_text(script.replace(
            "args=sys.argv[1:]",
            "import os\nif 'OPENAI_API_KEY' in os.environ: raise SystemExit(9)\nargs=sys.argv[1:]"),
            encoding="utf-8")
        result = CodexCLIExecutionAdapter(executable=str(self.codex),
            repository_path=self.repo, repository_reference="repo://example/test",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts).execute(self.assignment())
        self.assertEqual(result.status, "DELIVERABLE_PRODUCED")

    def test_subscription_session_requires_interactive_owner_terminal(self):
        with self.assertRaisesRegex(ValueError, "supervised ChatGPT authentication"):
            CodexCLIExecutionAdapter(executable=str(self.codex), repository_path=self.repo,
                repository_reference="repo://example/test", codex_home=Path.home() / ".codex",
                workspace_root=self.workspace, artifact_root=self.artifacts,
                supervised_chatgpt_session=True)

    def test_persistent_owner_session_uses_existing_protected_login_without_tty(self):
        owner_home = self.root / "admin1"
        codex_home = owner_home / "state" / "codex-home"
        codex_home.mkdir(parents=True, mode=0o700)
        auth = codex_home / "auth.json"
        auth.write_text("synthetic credential marker", encoding="utf-8")
        auth.chmod(0o600)
        original_access = os.access
        def access(path, mode):
            return False if Path(path) == auth else original_access(path, mode)
        with patch("riverview_core.resident_execution.codex_cli.Path.home",
                   return_value=owner_home), \
             patch("riverview_core.resident_execution.codex_cli.pwd.getpwnam",
                   return_value=SimpleNamespace(pw_uid=os.geteuid())), \
             patch("riverview_core.resident_execution.codex_cli.os.access", side_effect=access):
            adapter = CodexCLIExecutionAdapter(executable=str(self.codex),
                repository_path=self.repo, repository_reference="repo://example/test",
                codex_home=codex_home, workspace_root=self.workspace,
                artifact_root=self.artifacts, persistent_chatgpt_owner_session=True)
            self.assertTrue(adapter.persistent_chatgpt_owner_session)
            self.assertFalse(adapter.supervised_chatgpt_session)
            self.assertEqual(adapter._preflight()[1], self.repo.resolve())
        self.assertEqual(auth.read_text(encoding="utf-8"), "synthetic credential marker")

    def test_persistent_owner_session_rejects_writable_auth_bind(self):
        owner_home = self.root / "admin1"
        codex_home = owner_home / "state" / "codex-home"
        codex_home.mkdir(parents=True, mode=0o700)
        auth = codex_home / "auth.json"
        auth.write_text("synthetic credential marker", encoding="utf-8")
        auth.chmod(0o600)
        with patch("riverview_core.resident_execution.codex_cli.Path.home",
                   return_value=owner_home), \
             patch("riverview_core.resident_execution.codex_cli.pwd.getpwnam",
                   return_value=SimpleNamespace(pw_uid=os.geteuid())):
            with self.assertRaisesRegex(ValueError, "read-only owner auth bind"):
                CodexCLIExecutionAdapter(executable=str(self.codex),
                    repository_path=self.repo, repository_reference="repo://example/test",
                    codex_home=codex_home, workspace_root=self.workspace,
                    artifact_root=self.artifacts, persistent_chatgpt_owner_session=True)

    def test_missing_codex_code_mode_host_fails_before_cli_launch_when_required(self):
        adapter = CodexCLIExecutionAdapter(executable=str(self.codex),
            repository_path=self.repo, repository_reference="repo://example/test",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts, require_code_mode_host=True)
        result = adapter.execute(self.assignment())
        self.assertEqual(result.status, "UNAVAILABLE")
        self.assertEqual(result.detail_code, "codex_code_mode_host_missing")
        self.assertFalse(result.execution_started)

    def test_required_code_mode_host_feature_is_enabled_for_codex_invocation(self):
        helper = self.codex.with_name("codex-code-mode-host")
        helper.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        helper.chmod(0o700)
        script = self.codex.read_text(encoding="utf-8")
        script = script.replace("args=sys.argv[1:]", "import os\n"
            f"if os.environ['PATH'].split(':')[0] != {str(self.codex.parent)!r}: raise SystemExit(6)\n"
            "args=sys.argv[1:]")
        script = script.replace("if any(value not in args for value in required): raise SystemExit(8)",
            "if '--enable' not in args or 'code_mode' not in args or 'code_mode_host' not in args: raise SystemExit(7)\n"
            "if any(value not in args for value in required): raise SystemExit(8)")
        self.codex.write_text(script, encoding="utf-8")
        result = CodexCLIExecutionAdapter(executable=str(self.codex),
            repository_path=self.repo, repository_reference="repo://example/test",
            codex_home=self.codex_home, workspace_root=self.workspace,
            artifact_root=self.artifacts, require_code_mode_host=True).execute(self.assignment())
        self.assertEqual(result.status, "DELIVERABLE_PRODUCED")
        self.assertTrue(result.execution_started)

    def test_persistent_owner_session_rejects_copy_or_weak_auth_file(self):
        owner_home = self.root / "admin1"
        codex_home = owner_home / ".codex"
        codex_home.mkdir(parents=True, mode=0o700)
        auth = codex_home / "auth.json"
        auth.write_text("synthetic credential marker", encoding="utf-8")
        auth.chmod(0o644)
        with patch("riverview_core.resident_execution.codex_cli.Path.home",
                   return_value=owner_home), \
             patch("riverview_core.resident_execution.codex_cli.pwd.getpwnam",
                   return_value=SimpleNamespace(pw_uid=os.geteuid())):
            with self.assertRaisesRegex(ValueError, "read-only owner auth bind"):
                CodexCLIExecutionAdapter(executable=str(self.codex),
                    repository_path=self.repo, repository_reference="repo://example/test",
                    codex_home=codex_home, workspace_root=self.workspace,
                    artifact_root=self.artifacts, persistent_chatgpt_owner_session=True)


if __name__ == "__main__":
    unittest.main()
