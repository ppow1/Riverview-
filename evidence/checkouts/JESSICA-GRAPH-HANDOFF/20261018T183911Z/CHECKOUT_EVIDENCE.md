<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/JESSICA-GRAPH-HANDOFF/20261018T183911Z/CHECKOUT_EVIDENCE.md
Component: JESSICA-CHARACTER-ARCHITECTURE
File Revision: 1.0.0
Purpose: Preserve W3 graph candidate provenance, isolated generation/check results, restoration data, and ownership blocker
Authority: Evidence of isolated engineering only; does not authorize shared-file edits, resident activation, or production changes
Recorded: 2026-10-18T18:44:09Z
Source commit: 1ce8917a3e66bb0c4870ae68fcc39c91e4635d17
Source tree: 67bf1a09ae7a3b1f7eaf213dc785d88c7a506fb7
Base commit: 1c136347f70ae6f98adc1da65b4bb868b67e36bf
Task: issue #120 comment 6253533433, W3 PR #116
-->
# W3 Jessica Graph Handoff — Checkout Evidence

## Identity and scope

- Repository: `ppow1/Riverview-`
- Worktree: `A:\AI\Riverview-Development\Jessica-Recovery`
- Branch / PR: `dev/jessica-recovery` / [#116](https://github.com/ppow1/Riverview-/pull/116)
- Initial graph-proposal documentation commit: `d77afbd40589dab0ab579b91f6d16e48b98bc80b`; current proposal revision 1.0.1 and W1 handoff correction: `1ce8917a3e66bb0c4870ae68fcc39c91e4635d17`.
- Source tree at evidence commit: `67bf1a09ae7a3b1f7eaf213dc785d88c7a506fb7`.
- Candidate behavior source commit: `3195e255469c5f33ff506db0441b5d83afc6cbfe`; focused test source commit: `89261c5c8d34c57c5a22f48699539e8501ac82b6`.
- W1 handoff: issue #120 comment 6253567313. W3's coordination and correction posts are issue comments 6253557874, 6253577952, 6253581806, and 6253656746. PR #127 is `29a0b45a97cda96795bced0e7a0a0eff1da66888` and changes the shared registry on its own branch.

This W3 increment prepared an isolated graph JSON candidate and edge mapping; it did not add a canonical JSON file to `process_graphs/`, change `.riverview-revisions.json`, or update generated projections on either branch.

## Candidate identity and mapping

The exact 12,144-byte UTF-8, no-BOM, LF graph candidate is embedded in `docs/architecture/JESSICA_CANONICAL_GRAPH_INTEGRATION_PROPOSAL.md`; the extraction was byte-compared to the tested candidate and matched. SHA-256: `20d9c1a1225fe7ef26a4a0458372eefa5076eb0bcbb6f190e9e31467c9c494ec`. It proposes `process_graphs/jessica/character-advisory.json`, graph/file revision `1.0.0`, with 13 stable nodes and 14 typed edges. The exact `.riverview-revisions.json` entry and conditional registry-revision handling are in the proposal.

The companion `docs/components/JESSICA_CHARACTER_ADVISORY_FLOW.md` is explicitly a draft. Its single Mermaid block was compared to `process_graph.py`'s renderer for the candidate and matched exactly. The proposal distinguishes direct code transitions from the separate optional import call, records that the helper only shape-checks the supplied `steward:` value, and does not invent a Jessica route or authenticated identity.

## Validation commands and results

| Command / environment | Result |
|---|---|
| `PYTHONPATH=src python -m pytest tests/test_jessica_character_architecture.py -q` | **PASS — 10 passed, exit 0.** |
| In-memory `validate_graphs` with 22 existing W3-local workflows and the graph candidate | **PASS — 23 workflows / 577 nodes; candidate 13 nodes / 14 edges.** Candidate source/document/evidence paths resolved. |
| Candidate Mermaid compared with `diagram_views` output | **PASS — exact match.** |
| Candidate embedded in proposal compared byte-for-byte with tested candidate | **PASS — exact match, 12,144 bytes, SHA-256 above.** |
| Disposable full clone at `A:\AI\Temp\tmp\w3-jessica-graph-acceptance-t3os1i15\checkout`, based on `d77afbd40589dab0ab579b91f6d16e48b98bc80b`, `core.autocrlf=false` | **PASS.** Candidate entry was added only in that disposable clone after backing up its prior registry. `python scripts/process_graph.py generate` produced 23 graphs / 577 nodes; `python scripts/process_graph.py check` passed; revision/predecessor check against the pre-change inventory returned `{"passed": true, "issues": []}`. Generated projections and temporary sidecar change remain only in that clone. |
| `python scripts/process_graph.py check` in the W3 Windows worktree (`core.autocrlf=true`) | **FAIL — exit 1**, schema sidecar checksum mismatch. Git blob is 3,203 LF bytes and hashes to the recorded `0c03d29216d6d3cb08e58ab7bff12b545211f78fbdffb0767118553b52025da7`; working copy is 3,257 CRLF bytes and hashes to `95596d4def44a2ff201b2b32be7ebe1890a2903c2beff8cdabbc857e31c1b41f`. This is CRLF normalization, not tracked schema divergence. Do not change the sidecar to the CRLF digest. |
| `git diff --check` | **PASS.** |
| `RIVERVIEW_TEST_PG_DSN` | **ABSENT — PostgreSQL integration NOT VERIFIED; no database test attempted.** |

## Changed controlled files and exact restore metadata

| Path | New revision | SHA-256 | Immediate predecessor / restoration |
|---|---:|---|---|
| `docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md` | 1.0.6 | `2a1a0ce32b2c0184a12dc13abaa060dfab7b8ea4caab17a90e91a54a47abb39e` | Revision 1.0.5 at `.riverview-backups/20261018T183300361327Z/docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md`, SHA-256 `a8661655ddcb53670276871531d9422474f996879a8f2fd6cb18eb54ed66a7b0`. Restore those exact bytes; record restoration as a new forward revision. |
| `docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md` | 1.0.1 | `b9571b57e634485ae3ed47da76ca1a34f88dae3f63ae28f286bfa75df4ecb966` | Revision 1.0.0 at `.riverview-backups/20261018T183300474420Z/docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md`, SHA-256 `1cb22473a0e71caec78a5a5a32f20160a24f456c8d9921123f348c23669711fc`. Restore those exact bytes; record restoration as a new forward revision. |
| `docs/architecture/JESSICA_CANONICAL_GRAPH_INTEGRATION_PROPOSAL.md` | 1.0.1 | `f64e73272857ac79c22b0225c240671927104aedf8a357a02a4b9694160eb113` | Revision 1.0.0 is preserved at `.riverview-backups/20261018T184031742688Z/docs/architecture/JESSICA_CANONICAL_GRAPH_INTEGRATION_PROPOSAL.md`, SHA-256 `72494607f22e192e4824769149d7f0d6c5be465f763ef386308c743999096bb1`. Restore exact predecessor bytes, then record restoration as a new forward revision. |
| `docs/components/JESSICA_CHARACTER_ADVISORY_FLOW.md` | 1.0.0 | `b642e1f5e534ab8d79e36a5f375bc1aff9736799edf153b9c6d6b2bef78aaeeb` | New draft file. Withdraw using a revert of the introducing commit. |

The three predecessor backup entries are recorded under task `W3-DISPATCH-6253533433` in `.riverview-backups/manifest.jsonl`; all backup bytes were read back and SHA-256 verified before editing. W1's read-only handoff (comment 6253567313) says W3's revision index has 82 fewer entries and its aggregate graph is 192 lines behind the registry-activation branch, whose W1 PR #127 index is at revision 1.1.247. The prescribed reconciliation would union entries, preserve newer hashes/revisions, retain LF, then regenerate. On this W3 branch that would modify the W1-owned shared registry and generated aggregate, so the assigned fallback remains in force. Existing historical evidence `evidence/checkouts/JESSICA-DOD-REMEDIATION/20261018T175442Z/CHECKOUT_EVIDENCE.md` is unchanged; this new record corrects its earlier interpretation of the CRLF hash difference.

For the final canonical-LF acceptance clone, the tracked revision 1.0.0 proposal blob from source commit `d77afbd40589dab0ab579b91f6d16e48b98bc80b` was separately backed up inside that disposable clone before the 1.0.1 proposal file was overlaid. This was needed because the actual W3 worktree predecessor backup preserves Windows working-copy bytes while the clone baseline uses the canonical Git blob. The clone's extra backup and all generated files/sidecar edits were temporary and are not in either branch.

## Blocker and remaining scope

The candidate passes complete graph generation/check and revision/predecessor testing in an isolated copy. Canonical registration on PR #116 remains blocked because W1's handoff says the target needs an 82-entry registry union and a 192-line generated aggregate update; that would edit W1-owned shared registry/projection paths on W3's branch. The exact candidate and handoff patch are preserved in the proposal. No branch history was rewritten and neither W1 nor another worker's worktree/PR was modified. Once an integration owner identifies an approved target/path owner, register the graph and regenerate views there.

No resident implementation was overwritten. Jessica remains dormant. No identity, grant, route, database, live resident, production, merge, or deployment action occurred. Full component DoD and commissioning are not claimed.
