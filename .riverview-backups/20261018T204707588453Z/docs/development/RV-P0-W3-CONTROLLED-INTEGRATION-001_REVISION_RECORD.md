<!--
Riverview Controlled Document
File: docs/development/RV-P0-W3-CONTROLLED-INTEGRATION-001_REVISION_RECORD.md
Component: P0-CONTROLLED-INTEGRATION
Revision: 1.0.1
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
