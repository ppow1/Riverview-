<!--
Riverview~ Controlled Engineering Proposal
File: docs/architecture/JESSICA_CANONICAL_GRAPH_INTEGRATION_PROPOSAL.md
Component: JESSICA-CHARACTER-ARCHITECTURE
File Revision: 1.0.1
Purpose: Preserve an isolated canonical graph candidate and exact integration delta while shared registry ownership blocks registration
Authority: Proposal only; does not authorize shared-file edits, graph activation, or production changes
Changed: 2026-10-18 UTC | W3-DISPATCH-6253533433 | Prepare graph/edge mapping and safe handoff patch
Changed: 2026-10-18 UTC | W3-DISPATCH-6253533433 | Incorporate W1's precise read-only base/registry handoff
Source checkout: 1c136347f70ae6f98adc1da65b4bb868b67e36bf
Contracts: process_graphs/README.md; docs/standards/COMPONENT_DEFINITION_OF_DONE.md
-->
# Jessica Canonical Graph Integration Proposal

**Status: isolated proposal only; not registered and not canonical.** W3 assignment 6253533433 permits canonical registration only if it can be done without editing W1-owned paths. PR #127 currently edits `.riverview-revisions.json`; therefore W3 has not added JSON under `process_graphs/`, changed that registry, or generated aggregate projections.

## Provenance and verified behavior represented

The candidate describes only the current W3 Python adapter: an in-memory request-driven builder, source-linked proposal claims, local successor revisions, and a separate optional registry helper that records an existing Steward caller as actor and Jessica as advisory producer. It explicitly models that the helper validates only the shape of the supplied `steward:` string; the host authentication boundary is not present here. No Jessica identity, grant, route, approval, resident creation, continuous worker, or publication flow is represented as implemented.

Relevant code provenance: implementation file last changed in `3195e255469c5f33ff506db0441b5d83afc6cbfe`; focused tests last changed in `89261c5c8d34c57c5a22f48699539e8501ac82b6`. Jessica tests pass 10/10 on the W3 branch with `PYTHONPATH=src`. `tests/test_institutional_proposals.py` and the existing proposal GET routes are referenced for the parent contract; this candidate does not claim Jessica-specific connection to those routes.

The candidate is UTF-8 without BOM, LF line endings, final LF. SHA-256: `20d9c1a1225fe7ef26a4a0458372eeFA5076eb0bcbb6f190e9e31467c9c494ec` (case-insensitive); size: **12,144 bytes**. IDs follow `rv:jessica:character-advisory:<stable-node-name>`. Graph revision and initial repository file revision are `1.0.0`.

## Node and edge inventory

| Nodes | Type | Meaning |
|---|---|---|
| `request` | entry | Existing Python caller provides request/subject fields. |
| `request-boundary` | verification | Validate required fields, revision, criteria, and advisory constraint. |
| `evidence-gate` | decision | Require source records and evidence-bound historical claims; keep unknown identity fields unresolved. |
| `reject-input` | failure | Reject malformed/unsupported/unsubstantiated input before a package is returned. |
| `build-package` | process | Produce the in-memory PROPOSED package with provenance. |
| `successor-revision` | process | Caller may request a local successor retaining prior revision and evidence. |
| `package-returned` | exit | Return package without persistence or approval. |
| `import-call` | entry | Separate parent host explicitly calls dormant import helper. |
| `principal-shape-check` | verification | Validate string form only; host authentication is not performed. |
| `deny-import` | failure | Reject malformed actor values before calling registry. |
| `create-draft` | process | Existing registry `authorized_import` call writes a DRAFT when explicitly invoked. |
| `draft-returned` | exit | Return the DRAFT; review/decision remain separate. |
| `parent-visibility-contract` | measurement | Document existing Steward GET visibility for a separately persisted DRAFT; no Jessica status hook. |

Edges use 9 `runtime_transition` paths for code-observed direct calls/returns, 3 `diagnostic_branch` paths for rejection, 1 `prerequisite` edge showing the optional helper requires a package but is not automatically called, and 1 `documentation` edge to the parent visibility contract. There are **13 nodes and 14 edges** total. No runtime edge claims a connected Jessica route.

## Exact registration delta (pending W1 owner handoff)

The canonical destination and manifest entry are:

```text
Path: process_graphs/jessica/character-advisory.json
File revision: 1.0.0
SHA-256 (UTF-8, no BOM, LF): 20d9c1a1225fe7ef26a4a0458372eeFA5076eb0bcbb6f190e9e31467c9c494ec
Size: 12144 bytes
```

Add this exact value under `.riverview-revisions.json` → `files`:

```json
"process_graphs/jessica/character-advisory.json": {
  "path": "process_graphs/jessica/character-advisory.json",
  "revision": "1.0.0",
  "sha256": "20d9c1a1225fe7ef26a4a0458372eeFA5076eb0bcbb6f190e9e31467c9c494ec",
  "size_bytes": 12144
}
```

On the W3 PR #116 head recorded above, the sidecar's self revision is `1.1.235`, so a registry-only follow-up from that exact base would increment it to `1.1.236` and update its own digest/size after adding the entry. W1 reports its separate PR #127 sidecar at `1.1.247`; that PR has a different base and is editing the same shared path. Do **not** apply either revision number until the integration owner identifies the actual parent commit and accepts a single combined registry edit. The tracked process-graph schema blob is already 3,203 LF bytes and exactly matches its recorded SHA-256. The Windows working copy expands it to 3,257 CRLF bytes under `core.autocrlf=true`; do not change the schema or record a CRLF digest to suppress that local check failure.

After the shared registry owner hands off a clean target, the authorized graph owner can preserve the immediate registry predecessor, add the graph and manifest entry, then run `python scripts/process_graph.py generate` in a canonical-LF checkout. That generator must update `process_graphs/generated/riverview-process-graph.json`, `process_graphs/generated/RIVERVIEW_PROCESS_GRAPH.md`, and the single Mermaid block in `docs/components/JESSICA_CHARACTER_ADVISORY_FLOW.md`. The flow document is explicitly marked draft; promote its status through a backed-up, versioned edit when the canonical registration is accepted. Then run `python scripts/process_graph.py check` and controlled predecessor/revision checks. Generated projections must not be hand-edited.

## Blocker and coordination

PR #127 is open at `29a0b45a97cda96795bced0e7a0a0eff1da66888`; its file list shows `.riverview-revisions.json` modified with 128 additions / 26 deletions. W1's canonical-LF validation passes at 23 workflows / 577 nodes; the Windows check has the CRLF sidecar limitation described above. W1 provided a read-only handoff in issue #120 comment 6253567313: W3 PR #116 is based on `codex/riverview-four-pr-integration-20261018` at `1c136347f70ae6f98adc1da65b4bb868b67e36bf`; its revision index has 82 fewer entries and aggregate graph is 192 lines behind the registry-activation branch. Before adding W3 graph records, the handoff says to reconcile against the latest integration target, union path entries without replacing newer hashes/revisions, preserve canonical LF, and regenerate projections. Doing so on W3 would modify the shared revision index plus W1-owned generated aggregate/projection paths, which the dispatch excludes. No W1 branch or PR is edited, and no history is rewritten. W3 therefore retains this exact candidate and patch proposal until an integration owner selects a safe target and path ownership.

PostgreSQL integration is **NOT VERIFIED**: `RIVERVIEW_TEST_PG_DSN` is absent. No database test was attempted.

## Candidate canonical JSON

The following is the exact candidate file content after normalizing the fenced block to UTF-8 without BOM, LF, and a final LF:

```json
{
  "graph_id": "rv:jessica:character-advisory",
  "graph_revision": "1.0.0",
  "component_id": "JESSICA-CHARACTER-ARCHITECTURE",
  "workflow_id": "jessica.character-advisory.v1",
  "diagram_order": 92,
  "source_references": [
    "src/riverview_core/jessica_character_architecture.py",
    "src/riverview_core/resident_execution/proposals.py",
    "src/riverview_core/status_dashboard/server.py",
    "tests/test_jessica_character_architecture.py"
  ],
  "documentation_references": [
    "docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md",
    "docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md",
    "docs/components/INSTITUTIONAL_PROPOSALS.md",
    "docs/components/JESSICA_CHARACTER_ADVISORY_FLOW.md"
  ],
  "verification_evidence": [
    "tests/test_jessica_character_architecture.py",
    "tests/test_institutional_proposals.py"
  ],
  "nodes": [
    {
      "id": "rv:jessica:character-advisory:request",
      "node_revision": "1.0.0",
      "type": "entry",
      "label": "A host calls the request-driven advisory package builder with a bounded subject and request",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:request-boundary",
      "node_revision": "1.0.0",
      "type": "verification",
      "label": "Validate required fields, nonnegative base revision, acceptance criteria, and mandatory advisory-only constraints",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:evidence-gate",
      "node_revision": "1.0.0",
      "type": "decision",
      "label": "Require exact source records; bind historical claims to matching evidence and keep unresolved identity fields out of factual claims",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:reject-input",
      "node_revision": "1.0.0",
      "type": "failure",
      "label": "Reject malformed requests, missing or mismatched evidence, unsupported historical claims, identity expansion, or omitted authority boundary",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:build-package",
      "node_revision": "1.0.0",
      "type": "process",
      "label": "Build an in-memory PROPOSED package with request, subject, base revision, source references, claims, and advisory provenance",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:successor-revision",
      "node_revision": "1.0.0",
      "type": "process",
      "label": "On a separate caller request, build a successor package retaining predecessor revision and evidence context",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:package-returned",
      "node_revision": "1.0.0",
      "type": "exit",
      "label": "Return package to caller; no persistence, Jessica resident creation, review, approval, or activation occurs",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:import-call",
      "node_revision": "1.0.0",
      "type": "entry",
      "label": "A separate parent host explicitly calls the dormant import helper with a package and purported Steward principal",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:principal-shape-check",
      "node_revision": "1.0.0",
      "type": "verification",
      "label": "Helper checks only that the supplied value is a nonempty steward-prefixed string; caller authentication is not implemented here",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md",
        "docs/components/INSTITUTIONAL_PROPOSALS.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:deny-import",
      "node_revision": "1.0.0",
      "type": "failure",
      "label": "Reject non-Steward-shaped caller values before registry invocation; this does not authenticate a caller",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py"
      ],
      "documentation_references": [
        "docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:create-draft",
      "node_revision": "1.0.0",
      "type": "process",
      "label": "Map to the existing authorized_import contract; persist a DRAFT as the supplied Steward actor and Jessica as advisory producer",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py",
        "src/riverview_core/resident_execution/proposals.py"
      ],
      "documentation_references": [
        "docs/components/INSTITUTIONAL_PROPOSALS.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:draft-returned",
      "node_revision": "1.0.0",
      "type": "exit",
      "label": "Return existing registry DRAFT; review and decision remain separate Steward actions, and no Jessica route is connected",
      "source_references": [
        "src/riverview_core/jessica_character_architecture.py",
        "src/riverview_core/resident_execution/proposals.py"
      ],
      "documentation_references": [
        "docs/components/INSTITUTIONAL_PROPOSALS.md",
        "docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md"
      ],
      "verification_evidence": [
        "tests/test_jessica_character_architecture.py"
      ]
    },
    {
      "id": "rv:jessica:character-advisory:parent-visibility-contract",
      "node_revision": "1.0.0",
      "type": "measurement",
      "label": "Existing Steward proposal GET endpoints can retrieve a separately persisted DRAFT; no Jessica-specific status or API hook exists",
      "source_references": [
        "src/riverview_core/status_dashboard/server.py"
      ],
      "documentation_references": [
        "docs/components/INSTITUTIONAL_PROPOSALS.md",
        "docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md"
      ],
      "verification_evidence": [
        "tests/test_institutional_proposals.py"
      ]
    }
  ],
  "edges": [
    {
      "from": "rv:jessica:character-advisory:request",
      "to": "rv:jessica:character-advisory:request-boundary",
      "type": "runtime_transition",
      "label": "builder receives request"
    },
    {
      "from": "rv:jessica:character-advisory:request-boundary",
      "to": "rv:jessica:character-advisory:evidence-gate",
      "type": "runtime_transition",
      "label": "request shape and advisory constraints valid"
    },
    {
      "from": "rv:jessica:character-advisory:request-boundary",
      "to": "rv:jessica:character-advisory:reject-input",
      "type": "diagnostic_branch",
      "label": "required field, revision, criteria, or boundary invalid"
    },
    {
      "from": "rv:jessica:character-advisory:evidence-gate",
      "to": "rv:jessica:character-advisory:reject-input",
      "type": "diagnostic_branch",
      "label": "evidence missing/mismatched, claim unsupported, or unresolved identity asserted"
    },
    {
      "from": "rv:jessica:character-advisory:evidence-gate",
      "to": "rv:jessica:character-advisory:build-package",
      "type": "runtime_transition",
      "label": "all supplied claims map to exact supplied source records"
    },
    {
      "from": "rv:jessica:character-advisory:build-package",
      "to": "rv:jessica:character-advisory:successor-revision",
      "type": "runtime_transition",
      "label": "caller separately requests revise_character_proposal"
    },
    {
      "from": "rv:jessica:character-advisory:build-package",
      "to": "rv:jessica:character-advisory:package-returned",
      "type": "runtime_transition",
      "label": "return initial local package"
    },
    {
      "from": "rv:jessica:character-advisory:successor-revision",
      "to": "rv:jessica:character-advisory:package-returned",
      "type": "runtime_transition",
      "label": "return successor with predecessor revision"
    },
    {
      "from": "rv:jessica:character-advisory:package-returned",
      "to": "rv:jessica:character-advisory:import-call",
      "type": "prerequisite",
      "label": "a separate host call requires a package; no automatic import call is wired"
    },
    {
      "from": "rv:jessica:character-advisory:import-call",
      "to": "rv:jessica:character-advisory:principal-shape-check",
      "type": "runtime_transition",
      "label": "host explicitly invokes optional helper"
    },
    {
      "from": "rv:jessica:character-advisory:principal-shape-check",
      "to": "rv:jessica:character-advisory:deny-import",
      "type": "diagnostic_branch",
      "label": "value is not a nonempty steward-prefixed string"
    },
    {
      "from": "rv:jessica:character-advisory:principal-shape-check",
      "to": "rv:jessica:character-advisory:create-draft",
      "type": "runtime_transition",
      "label": "string shape passes; actual trusted authentication remains the host's unimplemented integration responsibility"
    },
    {
      "from": "rv:jessica:character-advisory:create-draft",
      "to": "rv:jessica:character-advisory:draft-returned",
      "type": "runtime_transition",
      "label": "existing registry returns DRAFT"
    },
    {
      "from": "rv:jessica:character-advisory:draft-returned",
      "to": "rv:jessica:character-advisory:parent-visibility-contract",
      "type": "documentation",
      "label": "parent visibility contract only; no connected Jessica route or runtime transition"
    }
  ]
}
```

## Safe validation already performed

The candidate parsed as JSON and passed the repository's Draft 2020-12 schema and graph relationship validator in memory alongside the 22 existing W3-local workflows: **23 workflows / 577 nodes** after adding this candidate. More fully, a disposable local clone at W3 base `1c136347f70ae6f98adc1da65b4bb868b67e36bf` was checked out with `core.autocrlf=false`; the candidate and its exact new graph sidecar entry were added there only after backing up the predecessor manifest. `python scripts/process_graph.py generate` returned **23 graphs / 577 nodes, GENERATED**; `python scripts/process_graph.py check` returned **PASS**; `python scripts/revision_control.py --root <clone> check --baseline <pre-change inventory>` returned `{"passed": true, "issues": []}`. The generated focused Mermaid matched `docs/components/JESSICA_CHARACTER_ADVISORY_FLOW.md`. The W3 focused adapter suite remains **10 passed**. These are isolated checkout results; no shared registry, generated view, or W1 file was changed on either PR branch. The canonical `process_graph.py check` on this Windows worktree still fails at the schema because `core.autocrlf=true` expands the 3,203-byte LF Git blob to 3,257 CRLF working-copy bytes; the tracked blob matches the recorded sidecar.

Restoration: this is a new proposal file; withdraw it with a revert of the commit that adds it. No existing resident or source implementation is replaced.
