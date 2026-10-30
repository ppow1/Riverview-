<!-- Controlled document revision 1.0.0 | 2026-10-28 -->
# Grace artifact publication admission candidate

## Outcome

The current Grace objective remains rework_required; it was dispatched with
engineering.codex-cli-artifact.v1 despite unsupported repository publication
requirements. This candidate rejects that unsupported artifact contract before
objective lookup or proposal persistence. It maps the rejection to the fixed
PROPOSAL_PUBLICATION_CAPABILITY_UNAVAILABLE code and existing revision fence.
It reuses the artifact verifier's existing detector only for artifact-capability
steps. It does not claim source-change publication support or add a publisher.

Independent review rejected an earlier all-capabilities variant because a valid
source-change criterion mentioning its pinned repository commit triggered the
artifact detector. The corrected variant preserves that provenance criterion,
ordinary artifact plans, and all other capability/authority contracts.

## Exact tested patch

patches/grace_artifact_publication_admission_20261028.patch
SHA256: 77931e84586879f1ac6de62c0f02d740c6303200771400f4a40d1b5a341beab0
Bytes: 9542
Files: src/riverview_core/resident_execution/pipeline.py (1.1.48),
src/riverview_core/resident_execution/service.py (1.0.63),
tests/test_grace_execution.py (1.0.91).

Exact pre-edit SHA256 values:
- pipeline.py: 51d2428fba6836746392ec5a26c3de497932603c2348b865baabfef0fcf59233
- service.py: 3a31111efe3bea0910be6571cef97076dc1a9562fbc57cdff526ca2507394c2d
- test_grace_execution.py: 48185707b6ab4529d675ee74ee03de5aec0b630c79ba3c04c15a26f95b001510

These are saved pre-edit worktree bytes in /tmp/grace-source-scope-before on
Camrui, not an assertion that the entire worktree equals clean HEAD. Its HEAD is
9f56cb72f3bd2961babf2527a26bd843526e18ce. That complete deployed commit is not
published in GitHub. This PR therefore preserves the exact tested delta as a
patch bundle instead of replacing current runtime files with an older branch.
Do not apply against mismatched predecessors or replace the whole deployed tree.
The patch excludes prior workspace edits and PR368 cancellation/diagnostic changes.
Preserve the installed Comms5/Dashboard controls separately.

## Verification and traceability

Camrui run grace-source-scope-review-20261028-01 completed exit 0 on exact thread
01a17fdf-6d58-7050-92cc-1762ac986518. Execution:
c63bddca-e078-46df-a8ee-8d59ab362fce; final audit:
bd0649cc-a3b5-457b-bac3-1699a721d8f1.

PYTHONPATH=src python3 -m unittest -v tests.test_grace_execution.GraceReasoningFailureDiagnosticTests
Result reported by the existing Camrui Codex session: 8 passed, 0 skipped, exit 0.
Scoped git diff --check passed. Work independently reconstructed the complete
9542-byte patch, matched the recorded SHA256, and parsed it with git apply --numstat.
PostgreSQL integration and live deployment have not been verified. No objective,
worker permission, grant, credential, or live service was changed by this candidate.

## Next source-worker boundary

The declared worker configuration pins repo://ppow1/Riverview- to
4391e3f1283277ee0582000e7170c497d791f7f2 and permits only
tests/test_local_reasoning_provider.py. Its actual loaded/active state is not yet
confirmed: Codex's system bus access was denied. Do not infer active enrollment
from declared files or from generic CME worker counts.

The concrete proposed reconciliation is in
GRACE_SOURCE_WORKER_CHANGE_PLAN_20261028.json. It retains the existing allowed
provider test, adds only pipeline.py, service.py and test_grace_execution.py, and
pins the source checkout to 9f56cb72f3bd2961babf2527a26bd843526e18ce. No new
identity, credentials, grant or publisher is proposed. Actual loaded baseline,
existing exact worker authority and a safe idle activation point must be checked
through the established operator path before application. This proposal changes
filesystem policy and requires Steward approval under the mission's explicit
permission-change boundary. It has not been applied.

Source-change execution produces a scoped patch with independent replay/tests.
Repository publication remains a separate uncommissioned capability; exclude it
from acceptance until the real publisher and independent verifier exist.
