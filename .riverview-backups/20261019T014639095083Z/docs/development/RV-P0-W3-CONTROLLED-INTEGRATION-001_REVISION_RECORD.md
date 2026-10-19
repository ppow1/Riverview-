<!--
Riverview Controlled Document
File: docs/development/RV-P0-W3-CONTROLLED-INTEGRATION-001_REVISION_RECORD.md
Component: P0-CONTROLLED-INTEGRATION
Revision: 1.0.10
Status: Offline integration evidence; no merge or deployment authority
Date: 2026-10-18 UTC
Purpose: Record W3 branch assembly and isolated verification
Authority: Issue #120 comment 6254574126
History: New record; source and test artifacts preserved by owner branches and the integration commit history
-->

# P0 controlled integration revision record

## Scope

Created a disposable integration branch from PR #119 and assembled the available
published C3, C4, C2, W2, C1 and W1 branches in the assigned order. Cherry-picked
only W3's workflow proposal document from PR #129. The exact branch heads, merged
HEAD and backup manifest reconciliation are recorded in
[P0_CONTROLLED_INTEGRATION_MANIFEST.md](P0_CONTROLLED_INTEGRATION_MANIFEST.md).

## Verification

At integrated HEAD `683be8b581c1d14b78c3d91ae1aa5aa61b497f81`, the focused unittest
selection recorded in the manifest produced 33 passes, 6 PostgreSQL configuration
skips, and one import error because PyJWT is unavailable. The dispatcher and trace
tests passed. `git diff --check` passed after each merge. No live doorbell, database,
production service, credential, grant, or deployment action was performed.

## Blocker

C3's integrated exchange lacks `claim_next_doorbell_request` and
`record_doorbell_receipt`, and the Grace owner loop does not register the C2
Dispatcher. These prevent the combined acceptance test from exercising the full
cycle. C3 must publish the assigned follow-up. W2 must then run with an isolated
PostgreSQL DSN; C4 tests require the repository's declared PyJWT test dependency.

## Troubleshooting

- PostgreSQL cases report skipped when `RIVERVIEW_TEST_PG_DSN` is unset. Supply an
  isolated test database only; do not point this suite at production.
- `tests.test_external_reasoning_mcp` needs the declared PyJWT dependency. The
  current integration shell lacks `jwt`; no package was installed as part of this
  coordinator task.
- Do not invoke `DoorbellDispatcher` against the live browser. Synthetic tests are
  the only doorbell verification performed here.


## Closure round update — 2026-10-18

Integrated C3 PR #135, latest C2 PR #131 owner-session wiring, C4 PR #130 expired
response correction, and W2 PR #136 acceptance tests. The W3 closure checkpoint
code SHA is `d138e35269252d5bab0d0ee99be4fd3ec1c5cfc6`; see the manifest for exact
source heads and subsequent documentation/graph commits.

Focused validation on that head: 56 tests ran, 34 passed, 22 PostgreSQL tests
skipped because `RIVERVIEW_TEST_PG_DSN` was absent. C4 expired response regression,
C2 dispatcher and runtime wiring, and C3 typed-subject unit cases passed. Graph
validation/check passed for 22 graphs and 573 nodes. Revision-control audit against
PR #119 baseline passed. No live browser wake or production action occurred.

Still required for offline acceptance: W2 disposable PostgreSQL execution; C2/C3
integrated connection confirmation; W1 trace over actual W2 events; C1 readiness
projection over integrated state. Live ChatGPT review remains outside this branch's
authority.


## Latest integration verification — 2026-10-18

Integrated C1's expiry-specific readiness regression head `d9a8332006d59c443473ea7ef8b1b45e0271bbb6` and W2's test/snapshot head `8b4dcd0f9291f2c7c61bf47047063c8f33ffbea1`. At W3 code head `8203370f8deb518e87d7822cf54e090d077400d3`, 97 focused tests ran: 75 passed and 22 PostgreSQL tests skipped without a local test DSN. Graph validation/check passed (22 graphs / 573 nodes), revision audit passed, and the LF-checkout diff check passed.

Hosted W2 run #39164629198 failed with an absent `created_at` column in its trace export, a C2 test fixture lease that expires during full-suite order, an expiry assertion needing alignment to terminal-expiry semantics, and a missing revision successor in the W2 restart case. These are recorded in the integration manifest and issue #120 comment 6254953224. They prevent completion of database-backed W2 acceptance and actual W1 trace evidence. W3 is awaiting owner corrections to integrate and retest.


## Mailbox #144 integration closure update — 2026-10-18

Integrated exact C2 fix `13d1730054628994daa8e2f46ee0bbe789ebd8f6` and W2 fix
`37093dc5ba15e8d7e2b61e16e51eb6976162eee3` into W3 merge commit
`5c71bb6119f41a8cdec763c91d16f227a25602db`. Append-only backup records were merged
without deleting or reordering integration entries; the two shared registry
predecessors were captured/read-back verified before conflict resolution. The
sidecar's stale version/hash for `RESIDENT_REASONING_FLOW.md` was aligned to the
existing generated document revision and canonical LF content.

Focused combined offline unit selection on the assembled files: 97 tests, 75 passed,
22 PostgreSQL skips because no local `RIVERVIEW_TEST_PG_DSN` is configured. C2's
latest head passed its 17 focused dispatcher/runtime tests, as reported by C2. W2's
exact-head hosted run #39173980276 failed before C2's latest commit was included
(708 tests, 4 skips, 14 failures: 13 stale-fixture dispatcher cases and one W2
restart assertion). It is not acceptance evidence for the combined W3 branch. W2 must
repair that final restart assertion; W3 must rerun hosted PostgreSQL on the exact
combined head. No actual W1 trace bundle or C1 runtime readiness projection is yet
verified from a successful combined database run.

Pending validation after push: exact-head CI/PostgreSQL, graph check, revision and
predecessor audit against PR #119, and LF `git diff --check`. PR #139 remains draft;
no main merge, deployment, live browser wake, credential or grant changes occurred.


## W2 restart fixture and acceptance correction — 2026-10-18

Integrated W2 PR #140 exact head `5df1705da353c7acc0ffc38c95b7a7f39c462954` at W3
merge commit `92db8078e08c3bff105e4659332f44c363ba3fbc`. The updated W2 fixture
restores the provider target on every reconstructed Grace instance and asserts the
stable subject ID, increased revision, changed digest, and no extra reasoning after
restart. C3 verified its durable successor lookup with this configuration and found
no C3 source correction needed (isolated PG16 exchange tests 21/21 PASS).

W3 local focused combined selection after import: 97 tests, 75 passed, 22 PostgreSQL
cases skipped without a local DSN. Exact combined W3 hosted PG acceptance after the
latest W2 fix remains pending. Prior W3 run #39174307337 on head `48f06544` was
708/4 skips/1 failure; C3's isolated diagnosis established that failure came from
the W2 restart helper omitting provider targets and asserting a new subject ID. The
existing W1 projector result from that run was `complete` for one synthetic round,
zero blockers, with `execution_kind_verified=false`; it is not live provider
evidence.

Before this documentation edit, predecessor bytes for the manifest and revision
record were captured and logged under task
`RV-P0-W3-INTEGRATION-CLOSURE-003`; verify the corresponding manifest entries and
backup hashes. The next gate is a fresh exact-head W3 hosted run, followed by graph
and revision checks on the published source. PR #139 remains draft; there was no
production action, main merge, deployment, browser wake, or credential/grant change.


## Revision-index integrity correction — 2026-10-18

The PR #119 baseline audit on W3 head `c403553071bacdc9f6f57c85621c381659bfc844`
found that merging the latest C2/W2 revision records changed `.riverview-revisions.json`
without incrementing its self revision (1.1.241). The self revision is now 1.1.242.
The exact predecessor sidecar and revision-record bytes were backed up under task
`RV-P0-W3-REVISION-INDEX-001`; read-back SHA-256 verification and the subsequent
baseline audit are required before publishing. No process graph or runtime behavior
changed in this correction.


## Final exact-head verification — 2026-10-18

At W3 head `ce497440409bfa782ef55f3edd6be0ed54f6d870`, hosted run
[#39175326234](https://github.com/ppow1/Riverview-/actions/runs/39175326234)
passed **708 tests / 4 skips / 0 failures**. Graph validation passed (22 / 573);
revision/predecessor audit passed with zero issues. Local focused selection passed
75 tests and skipped 22 PostgreSQL cases without a local DSN. The exact PR #119
baseline audit passed after incrementing `.riverview-revisions.json` self revision
from 1.1.241 to 1.1.242 and preserving its predecessor.

The exact hosted run emitted a body-free synthetic trace snapshot. The W1 projector
returned complete for one round, no blockers, `synthetic_metadata_only`, and
`execution_kind_verified=false`. W1 independently verified the W2 database-derived
trace at issue comment 6256193503. C1 exact-head integrated readiness remains
pending. Therefore W3's controlled integration/hosted acceptance is verified, while
overall offline readiness handoff remains incomplete and PR #139 stays draft. No
real ChatGPT review, browser wake, production change, credential/grant change, main
merge or deployment occurred.

Before this evidence edit, predecessor bytes for both controlled documents were
backed up under task `RV-P0-W3-INTEGRATION-FINAL-EVIDENCE-001`; verify the entries
and hashes in `.riverview-backups/manifest.jsonl`.

## C4 PR #150 controlled reconciliation — 2026-10-19

Steward authorization is issue #120 comment 6257187443. Starting W3 head was
`e6fa5758df1c23bf5058afa60f0d6b3ac6e6bebf`; C4 PR #130 was already an ancestor,
and W2 PR #140 head `5df1705da353c7acc0ffc38c95b7a7f39c462954` was already present.
Only C4 PR #150 head `e9495343e5895f415b86e4699e030b502273469d` was reconciled.
The exchange retains C3's immutable review-subject digest conflict checks and C4's
Steward list/status/claim/response operations; their exchange acceptance cases are
combined. The canonical Comms5 graph and aggregate validate at 22 graphs / 575
nodes. Both branch backup histories are retained; exact W3 predecessor bytes for
changed tracked files are logged in the manifest.

Local focused verification in the isolated Windows test venv passed 53 tests and
skipped 20 PostgreSQL cases because `RIVERVIEW_TEST_PG_DSN` is unset. The local
full-suite run discovered 625 tests and reported 3 failures, 70 errors and 216
skips; it is not acceptance evidence because this workstation lacks the disposable
PostgreSQL service and POSIX-only permissions/TTY behavior. Hosted PostgreSQL
acceptance on the published exact integration head is the required final test.
No merge to main, deployment, service action, migration, credential/grant change,
live review or connector refresh is authorized or performed.

## Exact-head PostgreSQL correction — 2026-10-19

Hosted run [#39182240680](https://github.com/ppow1/Riverview-/actions/runs/39182240680)
on `f367747de09da4a1c1c526f03fa72f17f67a0806` ran 701 tests / 4 skips and failed
with two errors. The Steward exchange test correctly expects `ExchangeUnauthorized`
for a bad Steward digest, while the C3 provider proposal path expects
`ExchangeConflict`; the integration now preserves those caller-specific results.
The process-graph test also found that the index checksum had captured the Windows
CRLF working copy of the graph schema, while Git stores LF. The worktree copy was
restored to the exact tracked LF bytes and the sidecar now hashes that exact blob;
the CRLF predecessor was retained and recorded. A follow-up scan found 37 indexed
JSON checksum entries, including all 22 workflow graphs, captured from Windows
CRLF working copies. Their SHA-256 values and sizes now match the exact committed
Git blobs; JSON payloads are unchanged. Latest graph and diff checks pass; the
exact-head PostgreSQL workflow was rerun and passed on the final candidate.

## Final combined exact-head acceptance — 2026-10-19

Final controlled head: `c7c29ca66bd386cbe279d705045b082af8612c96` on draft PR #139.
Hosted run [#39182995705](https://github.com/ppow1/Riverview-/actions/runs/39182995705)
passed **714 tests / 4 skipped / 0 failures** with PostgreSQL 16. Canonical graph
validation passed **22 graphs / 575 nodes**. The controlled revision and
predecessor audit passed with **0 issues**. `git diff --check` passed before
publication. PR #130 and W2 PR #140 were already in the lineage; only PR #150 was
added.

### W1 and C1 handoffs

W1's body-free PostgreSQL-emitted trace is from test run 39173980276 and is at
[issue comment 6256193503](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6256193503).
W1 independently projected it with exit 0, one round complete, zero blockers,
report SHA-256 `5c0ac02a1c452e9f0921e2dac7baacd951c6e256a3fb19f771e007b58954c454`;
the trace is synthetic and reports `execution_kind_verified=false` ([verification
6256352265](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6256352265)).
C1's offline readiness handoff ([comment
6256648441](https://github.com/ppow1/Riverview-/issues/120#issuecomment-6256648441))
passed 19 readiness tests and 22 trace tests on earlier W3 head `e6fa5758` and
marked production/live readiness NOT READY / unverified. Neither the W1 projector
nor C1 readiness suite was rerun on final head c7c29ca6; the hosted suite is
combined code/DB acceptance, not a fresh W1/C1 readiness handoff.

### Remaining blockers and authority

No real ChatGPT browser wake or external review was triggered. Production service
activation, connector refresh, and real provider identity/configuration remain
unverified; the last C1 report also lacked evidence of approved provider mapping,
protected configuration, and service activation. A live commissioning/review
requires separate Steward authorization. PR #139 remains draft and unmerged; no
deployment, service restart, migration, credential/grant change or production
action occurred.
