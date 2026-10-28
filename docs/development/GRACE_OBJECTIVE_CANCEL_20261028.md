<!-- Riverview Controlled Document
File: docs/development/GRACE_OBJECTIVE_CANCEL_20261028.md
Component: RESIDENT-ORCHESTRATION
File Revision: 1.0.0
Changed: 2026-10-28 UTC
-->
# Objective cancellation through Comms5

Steward directed fresh bounded development requests rather than prolonged stale
request recovery. Existing Comms5 draft cancellation cannot cancel objectives.
This candidate adds comms5_cancel_objective through the existing authenticated
Dashboard bridge and GraceExecutionPipeline.cancel_work_order. It derives the
scope from the target, requires explicit confirmation and exact assignment.cancel
authority, preserves append-only events and existing active-work exclusions.
It creates no grant and does not bypass any cancellation eligibility check.

Actual Engineering task on Camrui:
grace-fresh-intake-control-gap-20261028-01;
execution d9c53604-df15-4bd6-a024-ae83f37ae6e0, CLI exit 0.
Exact persisted thread 01a17fdf-6d58-7050-92cc-1762ac986518.
Result execution 0d804553-942e-4fa6-87fe-22a9bad20c1a;
audit 3d9f8e7b-2421-48f1-94f5-c18b57d7aaec.
Five focused tests passed on Camrui. PostgreSQL integration test was not run
(no RIVERVIEW_TEST_PG_DSN); HTTP-bind testing was sandbox blocked.
No full-suite, hosted-CI or live cancellation pass is claimed.

Candidate was developed against deployed Grace source 9f56cb72.
The compact tracked-only patch SHA256 is
083ba3f900054e8145d30d952823d847f12253e5ea8abceb0105737af5daa0c3.
Its gzip/base64 export was integrity verified after bounded result transfer.
Patch applies cleanly to published recovery source b79ea4dc1ae644b768c6684b715d7d3105b09340.
Seven predecessor files are byte-identical; test_grace_execution.py has newer
9f56cb72 changes elsewhere. This PR ports its cancellation-test delta into the
published predecessor and does not claim to republish the entire deployed tree.
Static Python compilation passed after reconstruction.

Exact published predecessor files are preserved under
docs/history/GRACE_OBJECTIVE_CANCEL_20261028/ with their original relative paths.
Camrui retains its actual full predecessors and feature manifest in
.riverview-write-acceptance/grace-cancel-feature.manifest.json.

## Current operational state and next actions

Fresh approved proposal: proposal:f34ed871-1779-42ff-866e-53ac1ae61551 revision 2.
Canonical objective: objective:proposal:f6af71cc-39f4-5457-99bd-de9110c23cd2:r2.
Engineering assignment: assignment:grace:d391056762e0a6f718dd6489e8cdcc6bb367d46e.
Worker attempt 8247d85c-30b6-4122-9f6e-a849985a7c72 succeeded;
independent verifier 1.0.5 REJECTED at 2026-10-28 09:16:40 EDT.
State WORK_ORDER_CREATED / rework_required. Recovery advice was consumed but
did not resolve rejection. This is measurable workflow progress, not acceptance.
CME monitor was healthy in a fresh live status read.

Old objective objective:proposal:4ab91570-c31a-5420-994b-33474fe567ed:r2
has not been cancelled. No live objective mutation was made by this feature.

Important integration boundary: live Comms5/Gateway modules are newer than this
older published recovery base. Do NOT replace current services with whole files
from this PR. Port only reviewed cancellation deltas onto exact current service
sources, preserve Gateway/delegation routes and record predecessor hashes.
Inspect current service paths first; obtain focused integration evidence before
using the established development deployment and rollback procedure.
The feature is source-only, not deployed or exposed by the connected tool yet.

Next thread run grace-current-verifier-release-inspect-20261028-01 inspects only
current verifier/artifact evidence and current service release paths. Continue
from its durable result; do not rediscover old Run 2 or create duplicate objectives.
