# PR #115/#119 commissioning preflight revision record

**Document Revision:** 1.0.2
**Task:** RV-C4-PR115-119-READINESS-001
**Component:** GRACE-COMMISSIONING
**Candidate base:** PR #119, `97128626df967bc992696dca38eaa7116f3616e9`
**Previous:** None; this is a new read-only operator record.

## Change

Added `docs/operations/PR115_119_COMMISSIONING_OPERATOR_DECISION.md` to
consolidate the current PR dependency/CI state, verified isolated migration and
ACL evidence, rollback limitations, deployment package identity, and the live
provider/worker/Steward gates. The decision is NO-GO at commissioning milestone
1/5. The record explicitly distinguishes prior isolated or historical evidence
from state that must be rechecked immediately before any separately approved
production change. It now also records the C4 disposable deployment/execution
rehearsal: package migration directories applied in order and reapplied
idempotently; the actual restricted `riverview_core` role passed permitted
retry-state operations and was denied identity update/delete/truncate; the
package pointer switched from a synthetic predecessor to the candidate and
back; and four focused PostgreSQL lifecycle/verification tests passed, including
a loopback dashboard and reconstructed Grace service execution. The
current fetched-head ancestry was also checked: #109–#112 → #113 → #115 → #119
are ancestor relationships, while current #114 is not an ancestor of #115 and
only the reviewed provider-response corrections are integrated there.

No runtime code, migration, credential, grant, service configuration, graph,
or production system was changed. Existing C4 57-test isolated worker execution
evidence was linked rather than rerun. The package was independently checked
read-only: source commit `97128626df967bc992696dca38eaa7116f3616e9`, archive
SHA-256 `8a3c4f50f4331bfc298d1e15a2bd188462c9f5b85065afbee37f993b38a96fc7`,
manifest PASS, shell compatibility PASS.

## Verification

- PRs #109–#115 and #119: OPEN, MERGEABLE, controlled-checkout SUCCESS at the
  observed heads recorded in the operator decision.
- Package verifier: PASS for manifest and shell compatibility.
- `python3 scripts/process_graph.py check`: PASS, 22 graphs / 565 nodes.
- Migration/runtime, full suite, restricted-role, and rollback evidence is
  cited with its prior isolated test scope and is not represented as fresh
  production verification.
- Focused rehearsal tests: 4 passed, 0 failed, 0 skipped. The loopback test
  server shut down cleanly; the disposable PG cluster was stopped and its
  unique migration schema was removed. No systemd unit was started.

## Authorization boundary

This document does not approve merge, deployment, migration, credential or
grant changes, service start/restart, external provider activation, or live
Engineering execution. The exact external provider identity/credential/route
and escalation grant, objective approval, and separate production change
authorization remain unresolved.

## Remediation record — 2026-10-18

Task: RV-C4-PR115-119-READINESS-001-REMEDIATION.

The operator decision document and this record were incremented prospectively
from their declared revision 1.0.0 to 1.0.1. Exact current predecessor bytes
were read back and SHA-256 verified before editing. Backup paths, source
commit, previous hash, revisions and restoration instructions are recorded in
.riverview-backups/manifest.jsonl. Earlier unversioned historical edits remain
disclosed in the operator record; this revision does not invent missing
historical backup timing.

A structured commissioning blocker register, Comms5-versus-external-reasoning
OAuth trace, nonproduction-only rollback cookbook, canonical readiness graph,
and durable isolated checkout evidence were added. The graph is limited
to preflight, isolated rehearsal, explicit blocked gates, and handoff for
separate Steward review. It has no production activation step. The graph, its flow projection, and the operator cookbook carry controlled revisions and preserved immediate predecessors. The isolated evidence directory records 57 worker tests passing (0 failed, 0 skipped), four focused lifecycle checks, migration/ACL evidence, and synthetic pointer restoration. Production rollback remains unverified.

The corrected hash from issue #120 comment 6253109270 is
fcf1111d7fa6e6bb26a2de8817562505bc7e66657ddd994733663e0c5b699e50 for
.codex-monitor/engineering-worker-test-evidence-20261018.md.

The feature checkout carries branch-local AI_HINTS 1.0.5 / DoD 1.7 copies,
while main has AI_HINTS 1.0.4 / active DoD 1.6. Neither copy was overwritten;
the documented procedure follows the main authority revision specified by
the assignment.


## Provider and commissioning decision dossier — 2026-10-18

Task: RV-C4-PROVIDER-COMMISSIONING-DOSSIER-001.

Extended the operator record from revision 1.0.1 to 1.0.2 after preserving and
hashing its exact predecessor. Corrected the distinction between the Grace-side
`RIVERVIEW_EXTERNAL_REASONING_PROVIDER_MAP` identity registry and the external
MCP systemd `provider-auth-map` credential. Recorded exact adapter settings,
Comms5 ingress path/audience/principal, conditional listener collision based
on host/network namespace, and the two supported issuer decision paths. Added
the precise identity/scope, route, grant, objective, and deployment decisions
needed from their respective authorities. No provider values were inferred;
no source code, runtime, grant, credential, graph behavior, or production state
was changed.

The canonical graph remains unchanged because this is a documentation-only
contract clarification; its existing preflight node already covers the
read-only OAuth comparison and gated handoff. Graph validation is rerun to
confirm generated projections remain synchronized.
