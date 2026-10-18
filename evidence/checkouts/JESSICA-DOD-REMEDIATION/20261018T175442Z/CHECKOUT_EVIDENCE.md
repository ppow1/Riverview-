<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/JESSICA-DOD-REMEDIATION/20261018T175442Z/CHECKOUT_EVIDENCE.md
Component: JESSICA-CHARACTER-ARCHITECTURE
File Revision: 1.0.0
Purpose: Reproduce the W3 Jessica DoD remediation checkout, tests, provenance, and restoration
Authority: Evidence of isolated repository work only; no resident or production authorization
Recorded: 2026-10-18T17:54:42Z
Source commit: 29dcd0afdd90baf41413322b7390b16694dda454
Source tree: a977ec9dbcc3d3c22e2a45627e503a21d2b129ff
Task: Issue #120 comment 6253138751, W3 PR #116
-->
# W3 Jessica DoD Remediation Checkout Evidence

## Checkout identity

- Repository: `ppow1/Riverview-`
- Worktree: `A:\AI\Riverview-Development\Jessica-Recovery`
- Branch: `dev/jessica-recovery`
- Tested source commit: `29dcd0afdd90baf41413322b7390b16694dda454`
- Tested source tree: `a977ec9dbcc3d3c22e2a45627e503a21d2b129ff`
- Parent commit before this remediation: `3195e255469c5f33ff506db0441b5d83afc6cbfe`
- Pull request: [#116](https://github.com/ppow1/Riverview-/pull/116)
- Governing reviewed assignment: issue #120 comment 6253138751

The evidence is tied to the immutable source commit above. Reproduce the focused test from the repository root on Windows PowerShell with ` $env:PYTHONPATH='src'; python -m pytest tests/test_jessica_character_architecture.py -q `.

## Controlled changes and provenance

| Path | Revision | SHA-256 | Predecessor / restore |
|---|---:|---|---|
| `docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md` | 1.0.5 | `a8661655ddcb53670276871531d9422474f996879a8f2fd6cb18eb54ed66a7b0` | 1.0.4 backup below |
| `docs/operations/cookbooks/JESSICA_CHARACTER_ADVISORY_COOKBOOK.md` | 1.0.0 | `1cb22473a0e71caec78a5a5a32f20160a24f456c8d9921123f348c23669711fc` | New file; remove through a revert of source commit if this increment is withdrawn |
| `.riverview-backups/20261018T175226897571Z/docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md` | 1.0.4 | `25c2f4c2114f85fc29b69ebdc8e680442ad195be458086d006eb75f25d93d78b` | Exact predecessor bytes; verified by SHA-256 readback |

The backup manifest entry is in `.riverview-backups/manifest.jsonl`, task `W3-DOD-6253138751`, timestamp `20261018T175226897571Z`. Existing historical backup records were not rewritten. The generic manifest format does not contain source commit or restore instructions; this W3 record supplies them prospectively.

To restore the repository to the exact pre-remediation tracked source, run `git revert --no-edit 29dcd0afdd90baf41413322b7390b16694dda454` from this branch and verify that the Jessica recovery document matches parent commit `3195e255469c5f33ff506db0441b5d83afc6cbfe`. Git history retains both the increment and its predecessor backup. The evidence record itself is a later additive commit and should be retained as the rollback audit record.

## Standards and observed branch divergence

- Current `origin/main` at review: `f6558554a1d360aebdb24036d3a8b7781e7e92b5`, AI_HINTS 1.0.4, Component DoD Rev 1.6.
- The PR base has AI_HINTS 1.0.5 and Component DoD Rev 1.7. This increment documents the divergence and does not change either standard.
- Development Lifecycle Standard 1.0.0 and Engineering Records Standard 1.0.0 are marked Proposed in the reviewed trees; neither is treated as an accepted authority.
- The process graph standard is `process_graphs/README.md` revision 1.0.1.

## Commands and results

| Command / check | Result | Notes |
|---|---|---|
| `PYTHONPATH=src python -m pytest tests/test_jessica_character_architecture.py -q` | **PASS — 10 passed, exit 0** | Isolated in-process tests; no database. |
| Initial `python -m pytest ...` without `PYTHONPATH=src` | **SETUP ERROR — collection failed** | Windows source package is not installed in this environment; rerunning with the repository's `src` path passed. |
| `python scripts/process_graph.py check` | **FAIL — exit 1** | Existing checksum mismatch at `process_graphs/schema/riverview-process-graph.schema.json`; details below. |
| `git diff --check` | **PASS — exit 0** | Checked staged documentation before source commit. |
| `RIVERVIEW_TEST_PG_DSN` presence | **ABSENT** | PostgreSQL persistence/integration is **NOT VERIFIED**; no fallback database was used. |

Schema/sidecar isolation evidence: branch schema SHA-256 is `95596d4def44a2ff201b2b32be7ebe1890a2903c2beff8cdabbc857e31c1b41f`; `.riverview-revisions.json` records `0c03d29216d6d3cb08e58ab7bff12b545211f78fbdffb0767118553b52025da7`. The recorded digest matches the `origin/main` schema bytes and sidecar entry. This branch-specific mismatch prevents graph generation/check. W1's reviewed remediation owns the shared revisions registry, so W3 did not edit it or the process graph schema.

## Delivered scope and remaining gates

Delivered: a controlled recovery cookbook with implemented behavior, negative paths, a focused Mermaid view, read-only diagnostic commands, safe recovery steps, and the parent proposal visibility contract; a versioned update to the recovery record with standards divergence, exact branch checksum evidence, and explicit blockers; exact predecessor backup and restore provenance.

Not delivered in this increment: canonical Jessica graph JSON registration or generated graph projections. This part is blocked pending W1 reconciliation/handoff of `.riverview-revisions.json` and the branch schema checksum. The Mermaid view is not claimed as a canonical graph. The Jessica role remains inactive; no route, principal, grant, approval, resident creation, database migration, or production change exists. Database integration is NOT VERIFIED. Full component DoD and operational commissioning remain incomplete.
