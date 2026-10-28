<!-- Riverview Controlled Document
File: docs/development/GRACE_AUTONOMY_CONTINUATION_20261028.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.3
Changed: 2026-10-28 UTC | RV-GRACE-REQUEST-DIAGNOSTICS-359
-->
# Autonomy Grace continuation — request-construction blocker

**Current update, October 28:** the Camrui launcher is installed and source editing,
tests and exact-session resume passed. The diagnostic patch has now been ported
to the exact deployed-source files and passed 55 provider tests on Camrui. Its
hash-verified candidate files are published in PR #364. Earlier read-only and
source-access blockers below are historical. No production deployment or Run 2
retry/state change has occurred.

## Current milestone and authoritative status

Continue the existing objective → Grace proposal → Engineering assignment →
execution → independent verification → completion/continuity sequence. Do not
replace Grace's deliverable with an operator-authored artifact.

Live Comms5 reads on October 28 UTC:
- Run 1 `objective:grace-issue310:run1-20261025` is COMPLETED, revision 5,
  independent verifier ACCEPTED. Issue #310's later recovery comment records
  that its artifact nevertheless lacked a GitHub commit and contradicted the
  terminal lifecycle. This remains an acceptance limitation, not a full PASS.
- Actual October 25 Run 2 is
  `objective:proposal:4ab91570-c31a-5420-994b-33474fe567ed:r2`.
  It is still GROUNDED, revision 2, no assignment, steps, intents or verification.
  Its original reasoning failed and its one authorized local recovery failed.
  Last recorded failure: 2026-10-25 19:40:36 EDT.
- Separate direct-dispatch objective
  `objective:5e29a3bb-f322-53d8-bebd-0acce2a25700` remains PROPOSED, revision 3,
  grounded evidence VERIFIED, no assignment. Do not equate this with Grace Run 2.
- Old qualification objective `objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2`
  is NOT the October 25 Run 2. An initial Codex summary confused these; a second
  exact-thread read corrected the identity before implementation.

## New live evidence and selected gap

Existing Camrui Codex thread `01a17fdf-6d58-7050-92cc-1762ac986518` was resumed
read-only, using the existing forced-command handler and active host grants.
The Codex tool executed local reads: Camrui is not limited to marker-only model
responses, but its entry point still does not provide unrestricted Bash.

The active readable release symlink resolves to
`/opt/riverview-grace-execution/releases/9f56cb72f3bd2961babf2527a26bd843526e18ce`;
SOURCE_COMMIT matches. GitHub returns 422/no commit found for that SHA.
This is newer than PR #327's documented deployed release `1d3208a…`.
Do not overwrite it with this older published source. Service health is NOT
VERIFIED: Codex's systemctl query could not connect to the system bus, and its
filtered journal query returned no entries.

Codex read `/var/log/syslog:6779`: latest accessible matching diagnostic
2026-10-25 19:40:35.696297 EDT, request
`e380728d-d20f-5aa4-9c42-d027c923f6e1`, PROPOSAL_REQUEST_INVALID.
Current deployed local_reasoning_provider.py returns that code at line 388 for
empty/oversized context and line 493 for request-construction TypeError/ValueError.
Neither branch logs the reason. This is confirmed missing observability, not a
demonstrated proof that the actual request was oversized or unserializable.

Selected increment: expose the exact request-rejection stage safely, so the
existing blocked proposal can be repaired from evidence without speculative
limit increases or unauthorized retry. This increment does NOT unblock Run 2
by itself and does NOT complete Autonomy Grace.

## Implementation and validation

Source base: `b79ea4dc1ae644b768c6684b715d7d3105b09340`, tree
`cddbf292ff37af8af196eb9195c2b3a4db49cf26`, byte-identical tree to the documented
PR #327 merge `1d3208a83d9b6c0b3a13c9be42579100ccd069cd`.
Branch: `codex/grace-request-diagnostics-20261028`.
This is a review candidate against the existing published recovery branch,
not a release candidate reconciled with 9f56cb7.

Changed files:
- local_reasoning_provider.py 1.3.32 → 1.3.33: reuse existing sanitized validation
  log helper for context serialization, empty context, UTF-8 size rejection,
  and body serialization; record byte counts only for size failures.
- test_local_reasoning_provider.py 1.1.35 → 1.1.36: four new tests, including
  subcases for TypeError/circular ValueError, no private-value leakage, no HTTP
  on invalid input, UTF-8 bytes and exact-limit acceptance.
- GRACE_PERSISTENT_EXECUTION.md → 1.0.26: diagnostic stages and recovery cookbook.
  Its predecessor contained both 1.0.24 and 1.0.25 metadata lines; the updated
  header has one current revision.

Baseline provider suite: 48/48 passed after assembling unchanged dependencies.
First incomplete local checkout had one missing-module import error; adding the
unchanged external_reasoning.py and reasoning_escalation.py resolved it.
Candidate command:
`PYTHONPATH=/tmp/riverview-test-deps:src python -m unittest discover -s tests -p test_local_reasoning_provider.py -q`
Result: 52 tests, PASS, exit 0. Python 3 in Work scratch; psycopg installed only
to /tmp/riverview-test-deps. No database, live inference or paid provider used by
tests. No hosted CI/full PostgreSQL/production acceptance claimed.

Failure outcome remains PROPOSAL_REQUEST_INVALID. Prompt bounds, accepted valid
requests, authority, objective criteria, retry fences, model routing, provider
spending, assignments and services are unchanged. The parent structured-log
contract supplies observability; no workflow transition, graph node or UI
operation was added. This is a diagnostic defect repair, not a new component.

## Traceable host executions

| Purpose | Run / Comms5 execution | Terminal / audit |
| --- | --- | --- |
| Read-only runtime analysis | grace-recovery-analysis-20261028-01 / 30e6d33d-19ea-4f2f-b31b-c984cb0eed39 | exit 0 / 22cf4e06-9728-433d-a1ff-6825622c8fb0 |
| First artifact read (bounded text truncated) | 6cf2c01b-cab9-4466-82d2-7de54931bc5e | exit 0 / 09c86163-60f3-447f-ac63-0584470b8f06 |
| Corrected concise exact-thread analysis | grace-recovery-analysis-20261028-02 / 0575638e-545f-4d9f-b0d3-5c42d40dff15 | exit 0 / 09db1b81-c512-4065-b3d5-033070372366 |
| Corrected result read | 95634258-2713-4b83-9ead-6a07a670f376 | exit 0 / e4c96c50-2ce7-4b34-913e-b77bb5a6d7eb |

Original first submit key `grace-recovery-analysis-20261028-01`, digest
`f3b33fb8eb9c9ba4c407bee887299871189bd0c0fd9a2c5dcdef6f4ac0b84540`.
Second key `grace-recovery-analysis-20261028-02`, digest
`69df97a9ff8a8b473973e1bea793f882560546fdf0d98ea623d937dfe759c66c`.
Exact Codex thread above remains the continuity anchor; both runs are completed.
Account-owned events are below
`/home/admin1/.local/state/riverview/gateway-codex/<run_id>/events.jsonl`.

Current host grants, all unlimited:
- Windows caller `grant:bc790c0beb1746b295aade230d4a56cf`
- Windows executor `grant:2c4cd34bcc484a61814f6f489f25c8f1`
- Camrui caller `grant:6422d222eca74cb3b328bf3a80384a59`
- Camrui executor `grant:8327c8d7a74b4bf78e5529e53057fe69`
Live submits independently confirmed the Camrui caller and executor bindings;
Windows canonical grant reads confirm active/unlimited. Windows expires
November 2 19:55 EST; Camrui November 3 16:53 EST. No new grants requested.

## Preservation, rollback and next action

Exact predecessor backups are Git blobs retained as history files in this PR.
Verify SHA-256 before restoring the corresponding bytes to the original path:

- docs/history/local_reasoning_provider_rev1.3.32.py: `ead3aa5cdbf961bfcaa47604d34b77902a8f4cfc40f2bc66352b0644e5db3021`; original blob `e099fee3edbb7a99ced630da0943862f16a913f3`.

- docs/history/test_local_reasoning_provider_rev1.1.35.py: `82e31e2b52170d09f8a14476f9ebbc50ad5cdca287dba08227f2e4d91ea746ef`; original blob `b89adeb2392ff510f459a91c922d62c14813a47e`.

- docs/history/GRACE_PERSISTENT_EXECUTION_rev1.0.25.md: `cf96f7f473d019ab975e4c6f8b71c8f425994ea5e9d5b14a19877569a0764252`; original blob `3bebc3ce563f12ecb373b1d58b9292a55ae87d15`.

No production patch, deployment, restart, objective mutation, retry-fence reset
or paid reasoning call was performed. Production rollback is therefore N/A.
For a later authorized release, preserve the ACTUAL current deployed predecessor;
restoring these older source backups is only a candidate-source rollback.

Next action: recover/publish the exact 9f56cb7 source provenance through the
existing release owner, reconcile this small patch with that source, and obtain
the established production deployment approval. Then use the existing authorized
diagnostic/recovery path to identify the request-construction cause without
replaying provider calls. Repair the actual producer/size defect and resume
Run 2 only within its existing institutional authorization. Keep its criteria
and historical failure events intact; do not start Run 3 to evade the blocker.

## Exact deployed-source provenance follow-up

Read-only exact-thread analysis found the actual source object at
`/tmp/riverview-grace-worker-diagnostics`, clean worktree,
branch `codex/grace-worker-diagnostics-20261026`.
Commit `9f56cb72f3bd2961babf2527a26bd843526e18ce`, parent
`e37e87f9068395c946c0ae54f77312f654a3ffc8`, subject
"Persist Grace source-test diagnostics in worker intents".
The deployed provider file and exact commit file match SHA-256
`9c78392cad50ea20adafa467a44533fbd1efe44160518010164ec19a9137a0b2`;
both retain header revision 1.3.32. GitHub has neither that commit nor its branch.

Comparison against b79ea4d confirms newer proposal prompt/schema refinements and
two additional tests. Neither request-invalid branch nor _validation_failure
changed. Preserve those newer changes when porting this additive diagnostic
patch. Comparison is read-only evidence, not an exact-current-source test pass.
The comparison response was bounded/truncated after its compatibility statement;
the listed unchanged branches and changed-function evidence were fully received.
Do not infer missing trailing text.

Provenance run `grace-release-provenance-20261028-01`:
execution `a0b1e66f-07ef-4356-b7eb-3b8893e9173d`, exit 0,
terminal audit `48185afa-54e5-49c7-979f-37d7247e9631`.
Result retrieval `459ce8da-6831-4ed0-9b3e-a25c1b5d0255`, exit 0,
audit `4b73c5fc-5db4-4190-8e11-f235cf7a00ea`.
Comparison run `grace-release-source-compare-20261028-01`:
execution `cbb7bde0-8492-4105-926a-369eb66f0496`, exit 0,
terminal audit `999d633d-7e30-482e-a2af-c91ff644c9d2`.
Result retrieval `1f5e7e69-dcd1-4b07-a410-f5e8e8ea928b`, exit 0,
audit `2545e214-11c9-4c19-bab0-6b6fd7e2ef62`.
All four Codex analysis runs are terminal; resume the same exact thread for
further work. No Comms5 advisory requests were returned by the bounded list
(limit 10); that is not an audit of all historic/provider requests.

Concrete next authorized implementation path: an existing Camrui operator with
source-write authority creates an isolated worktree at exact 9f56cb7, ports ONLY
the diagnostic/test/doc changes, preserves the real exact predecessors, runs the
current provider-test baseline plus new regressions, and publishes the result
for the established release procedure. The current fixed read-only Codex entry
cannot create that worktree, patch source or deploy; host execution grants do not
override this sandbox or grant institutional recovery authority. No credentials,
SSH identity, forced command, grants or retry fences were changed to cross it.
Production deployment and a recovery attempt remain separate approved actions.
No exact-current-source suite was executed: only the older
published 48 baseline and 52 candidate tests were actually run in this Work session.

PR #364 commit `2c324c5301a5ad294ae6b34aab270d71c4b17efa` contains the candidate;
readback of its provider source matched the tested bytes. Seven changed paths
are limited to source/test/doc, three exact predecessor copies and this handoff.
Predecessor of this record, revision 1.0.0, is retained at
`docs/history/GRACE_AUTONOMY_CONTINUATION_20261028_rev1.0.0.md`.

Revision 1.0.2 removes an inferred current-source test count; predecessor 1.0.1 is retained in docs/history/GRACE_AUTONOMY_CONTINUATION_20261028_rev1.0.1.md.

## Exact-current-source implementation and verification

The installed workspace clone is pinned to actual deployed source
9f56cb72f3bd2961babf2527a26bd843526e18ce. The same existing Codex thread
01a17fdf-6d58-7050-92cc-1762ac986518 performed the port in that clone, preserving
the newer exact-criterion/schema refinements. Source revision is now 1.3.34,
test revision 1.1.38. New failures retain PROPOSAL_REQUEST_INVALID with safe,
correlated construction-stage/UTF-8 diagnostics.

Actual Camrui command for both baseline and candidate:
`PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_local_reasoning_provider.py' -v`
Baseline: 50 tests, PASS, exit 0. Candidate: 55 tests, PASS, exit 0.
git diff --check: PASS, exit 0. No live model/provider or production database
was used in these tests. The test revision header was corrected after the
55-test pass because deployed tests were already revision 1.1.37; only metadata
changed afterward, and tests were not needlessly repeated.

Current-file SHA256, independently verified after transfer:
- local_reasoning_provider.py:
  11d5b55c5c2acd7075d497f0cbe99b3e6fc2a3522f330ccf37af73da7d592abc
- test_local_reasoning_provider.py:
  c83d1b4fc3fc275833923ba3a4ff60d22d5bc0fc5713719bb6384e355a1c2daf

Runtime predecessor bytes (different from the older published recovery base)
are now durably retained in this PR:
- docs/history/local_reasoning_provider_9f56cb7_predecessor.py: 9c78392cad50ea20adafa467a44533fbd1efe44160518010164ec19a9137a0b2
- docs/history/test_local_reasoning_provider_9f56cb7_predecessor.py: 12ac376267576f12fd7ff6bc5b6e7223d3c98d64b60d721c6e991f75f59c0a7a

The source/test reconstruction matched the complete hashes of the actual
preserved Camrui predecessors. The complete candidate patch was transferred
through bounded existing Codex result reads, decompressed and checked against
SHA256 bf39788877cc1fa387966c6512db0b90ef21627d516f0ba979307a27e630d957;
it applied cleanly to the known published b79ea4d files. Both resulting file
hashes match Camrui. Static compilation passed. This was transfer/integrity
verification, not another claimed test run.

Camrui local Git branch/commit creation was denied by protected .git metadata.
No sandbox bypass, new credentials or permission changes were used. Source
editing and test execution worked; the existing GitHub connector publishes
the candidate branch/files. The prepared working-tree patch and local recovery
record remain in the Engineering clone, and smoke files were preserved.

Review scope: this PR is still based on the existing published recovery branch,
because actual deployed 9f56cb7 is not published in GitHub. Its provider/test diff
therefore includes already-deployed October 25–26 schema/prompt refinements,
plus this diagnostic change. The new feature in this task is diagnostics only;
the existing refinements were preserved, not replaced or newly deployed.

Do NOT deploy the entire older PR base over production. Release integration
must use the exact current deployed tree with only the reviewed patch and
the existing release/rollback procedure. No service restart, release pointer,
authorization, criteria, objective state or retry fence has changed. The
actual underlying Run 2 request failure is not yet diagnosed by a deployed
version of this patch. Full Grace autonomy remains incomplete.

Trace:
- Port task cde51998-baed-45c1-89fd-f710e1619fec, terminal audit
  87c4fd49-f5c3-4859-abc7-5087f30cea9d, exit 0.
- Result retrieval 5a40da32-5d70-42cd-aa55-629ac27c5414, audit
  21a9a0b7-71c0-4f42-968c-805ccd6a69a7.
- Metadata/artifact export 58e6bc65-9fb0-4e29-99d2-7e986cbff43c, terminal audit
  2a55f34d-9493-4376-8a61-5e1a5b08005d, exit 0.
- Raw/current candidate provenance and bounded transfer receipts:
  evidence/checkouts/GRACE-AUTONOMY/20261028T1230Z/current-source-diagnostics.md.

Immediate previous PR source/test revisions 1.3.33 / 1.1.36 are preserved in
docs/history/local_reasoning_provider_rev1.3.33.py and
docs/history/test_local_reasoning_provider_rev1.1.36.py.
Predecessor of this record (1.0.2):
docs/history/GRACE_AUTONOMY_CONTINUATION_20261028_rev1.0.2.md.

Next: review the exact-current-source candidate and integrate/package it from
the current deployed release line. Production deployment and institutional
recovery remain explicit boundaries; do not retry the fenced objective merely
because the inspection/CLI path now works.
