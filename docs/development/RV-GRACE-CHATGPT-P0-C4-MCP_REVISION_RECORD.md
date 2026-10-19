<!--
Riverview Controlled Document
File: docs/development/RV-GRACE-CHATGPT-P0-C4-MCP_REVISION_RECORD.md
Component: EXTERNAL-REASONING-MCP-TRANSPORT
File Revision: 1.0.5
Purpose: Record C4 exact-proposal MCP integration, isolated verification, and live gates
Authority: Existing provider-scoped MCP identity and resident.reasoning.escalate grant only
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-MCP | Initial implementation record
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-MCP | Record exact-head CI and complete PostgreSQL suite result
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-TYPED-REVIEW-SUBJECT | Reconcile MCP validation with the typed resident proposal contract
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-TYPED-REVIEW-SUBJECT-CI | Record exact-head CI for the typed subject correction
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-EXPIRED-RESPONSE-MCP | Correct expired response mapping, document recovery, and verify terminal non-success
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE | Add a single-Comms5 authenticated Steward bridge for four durable advisory exchange tools.
History: Git; source predecessors retained in .riverview-backups/manifest.jsonl
-->
# RV-GRACE-CHATGPT-P0-C4-MCP — provider MCP exact-review binding

## Provenance and scope

This C4 implementation branch is based on PR #119's current head
`97128626df967bc992696dca38eaa7116f3616e9`, which contains the selected PR
#115 integration and restricted-role migration ACL correction. The earlier C4
operator-sheet branch and PR #126 are preserved and unchanged. This increment
does not change the exchange schema, Grace lifecycle, browser doorbell,
credentials, grants, service state, or production configuration. C3 owns the
durable review-subject persistence and final response digest enforcement; C2
owns the metadata-only browser wake worker.

## Shared interface

The authenticated provider list returns the exact top-level
`review_subject={schema_version,subject_id,revision,sha256,proposal}` stored by
the exchange. The digest is SHA-256 of UTF-8 canonical JSON for
`{subject_id,revision,proposal}` with sorted keys, compact separators,
`ensure_ascii=false`, and `allow_nan=false`; schema and digest fields are
excluded. The MCP submit tool accepts the explicit `review_subject_sha256`
argument. Existing provider identity and request/correlation ownership checks
remain in force, and the durable exchange is the final authority for matching
the submitted digest to its immutable stored subject. Requests without a review
subject preserve the existing advisory-only contract.

The subject is bounded to 16 KiB after JSON encoding. It carries a UUID subject
ID, revision 1 through 3, a summary of at most 4,000 characters, and one to 20
typed `PlanStep` objects. The MCP adapter validates every step with the same
resident `PlanStep` and `PlanProposal` constructors used by C3, normalizes the
four array fields to tuples for validation, then returns every dataclass field
as JSON. Source-change repository pin, authorized paths, and test targets
therefore remain part of the canonical digest and provider-visible subject.
The complete provider list item remains within the existing 32 KiB context
response bound. The browser bridge receives only its existing
request/correlation IDs and fixed wake operation.

## Files and predecessor protection

| File | Revision | Predecessor backup | Predecessor SHA-256 |
|---|---:|---|---|
| `src/riverview_core/resident_execution/external_reasoning_mcp.py` | 1.1.3 | `.riverview-backups/20261018T194638243733Z/src/riverview_core/resident_execution/external_reasoning_mcp.py` | `d0df25bc9a6c04776c7eba7d134b01e5573921bb1614e87858d73fe46fc9684d` |
| `tests/test_external_reasoning_mcp.py` | 1.0.8 | `.riverview-backups/20261018T194638527021Z/tests/test_external_reasoning_mcp.py` | `2ab9b68b42ed1d18ada6c4e22a1ee7025028242b273b146eeb97b3da8fe174b3` |
| `scripts/run_external_reasoning_mcp.py` | 1.1.1 | `.riverview-backups/20261018T194844646699Z/scripts/run_external_reasoning_mcp.py` | `9fabfb79993da4961d23483daf8d10acb5b3c1222ad9c334939b87e5982f7e9e` |
| `src/riverview_core/resident_execution/external_reasoning_mcp.py` typed-subject predecessor | 1.1.3 | `.riverview-backups/20261018T201203458949Z/src/riverview_core/resident_execution/external_reasoning_mcp.py` | `171299b3678f224f336eafd9cf6a6d90a468a3d8a981a6c2392f3c0b262e1a22` |
| `tests/test_external_reasoning_mcp.py` typed-subject predecessor | 1.0.8 | `.riverview-backups/20261018T201203735128Z/tests/test_external_reasoning_mcp.py` | `dd65f408163877fc8fc18703b60f684c2d36f00becd83ed6927cdd4c5fc7b066` |
| `docs/components/GRACE_CHATGPT_REVIEW_PROVIDER_PREFLIGHT.md` predecessor | 1.0.0 | `.riverview-backups/20261018T201204015298Z/docs/components/GRACE_CHATGPT_REVIEW_PROVIDER_PREFLIGHT.md` | `e4de1489fb99e6c14c649e462a85b37b35b88a7482d954c1880b4d9580acc2e6` |
| This revision record predecessor | 1.0.1 | `.riverview-backups/20261018T201204300289Z/docs/development/RV-GRACE-CHATGPT-P0-C4-MCP_REVISION_RECORD.md` | `d20186de280109bc0b7d7ab594eb2471542e390a6639d3b3d4611ad4cd5c0b4e` |
| This revision record typed-contract predecessor | 1.0.2 | `.riverview-backups/20261018T201637041313Z/docs/development/RV-GRACE-CHATGPT-P0-C4-MCP_REVISION_RECORD.md` | `bd27699590ac967527168b2d8e66cbebdb2dbd6d6883ae6c0d31fa08fb63942c` |
| `src/riverview_core/resident_execution/external_reasoning_mcp.py` expired-result predecessor | 1.1.4 | `.riverview-backups/20261018T203720473004Z/src/riverview_core/resident_execution/external_reasoning_mcp.py` | `e00ea544303bd101158e6ede0f653fdcc6d3b9971b465f65eab021114a2daadc` |
| `tests/test_external_reasoning_mcp.py` expired-result predecessor | 1.0.9 | `.riverview-backups/20261018T203720816926Z/tests/test_external_reasoning_mcp.py` | `f69fa59e8a3963feae3529d8b38709c210e54ecf3dc82fafd46b186d0e5ade3c` |
| `docs/components/EXTERNAL_REASONING_EXCHANGE.md` predecessor | 1.1.4 | `.riverview-backups/20261018T203721102540Z/docs/components/EXTERNAL_REASONING_EXCHANGE.md` | `5c27a2040b7f402dbf54a583be60e2587cfbae31c19bfeb0e9e2c385e4dd3269` |
| `docs/components/EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md` predecessor | 1.1.5 | `.riverview-backups/20261018T203721371022Z/docs/components/EXTERNAL_REASONING_EXCHANGE_COOKBOOK.md` | `4bd683546add896e5d8a7b85e7d6670a4db50469820edde54cd965ebf2db582d` |
| `process_graphs/resident-reasoning/runtime.json` predecessor | 1.0.25 | `.riverview-backups/20261018T203721605315Z/process_graphs/resident-reasoning/runtime.json` | `49e8424449e001975f0774928a845500a04bbd72e557d18b819081bf045e1926` |
| `docs/components/RESIDENT_REASONING_FLOW.md` predecessor | 1.0.17 | `.riverview-backups/20261018T203721809259Z/docs/components/RESIDENT_REASONING_FLOW.md` | `06482d7f1a7f54d188324c527d3eb8346400d93540a1c5eff61ebae12355d259` |
| This revision record expired-result predecessor | 1.0.3 | `.riverview-backups/20261018T203722042314Z/docs/development/RV-GRACE-CHATGPT-P0-C4-MCP_REVISION_RECORD.md` | `814a30a2722b89319710a4b5da2d519fbb241a955cf5acae3892b1bb7c824ee2` |

Each backup was created and verified before editing with
`scripts/revision_control.py backup --task RV-GRACE-CHATGPT-P0-C4-MCP`.
Restore by copying the listed backup bytes over the path, then verify the
recorded SHA-256 before rebuilding the package.

## Verification

- Focused MCP transport tests: **12 passed, 0 failed, 0 skipped** using
  `PYTHONPATH=src python3 -m pytest -q tests/test_external_reasoning_mcp.py`.
- Covered exact provider list exposure, canonical digest and subject bounds,
  conflicting subject rejection, absent/mismatched response digest rejection,
  and exact digest forwarding to the durable exchange.
- `python3 -m py_compile src/riverview_core/resident_execution/external_reasoning_mcp.py scripts/run_external_reasoning_mcp.py tests/test_external_reasoning_mcp.py`: **PASS**.
- `git diff --check`: **PASS**.
- Full disposable PostgreSQL cross-component chain, process graph regeneration,
  C2/C3 cross-window exact-proposal lifecycle, and final combined integration
  acceptance remain pending their owner branches. No live MCP client or
  ChatGPT request was made.
- Typed-subject correction focused MCP transport tests: **14 passed, 0 failed,
  0 skipped**. Exact-head CI run [39162360834](https://github.com/ppow1/Riverview-/actions/runs/39162360834)
  passed at source commit `49f5dcfb674d67416a68e43f1d756230c7372e46`: **628
  tests ran, 4 skipped, 0 failures**; process graphs **22 / 565 PASS**;
  controlled revision/predecessor check **PASS, zero issues**. Python
  compilation and `git diff --check`: **PASS**. This commit records that
  evidence; its exact-head CI is pending.
- Expired-response MCP mapping regression: `PYTHONPATH=src python3 -m pytest
  -q tests/test_external_reasoning_mcp.py` — **15 passed, 0 failed, 0 skipped**.
  The expired sentinel maps to `{state: expired, accepted: false}` without a
  response digest; valid and legacy advisory submit tests still pass. Graph
  regeneration and validation: **22 graphs / 565 nodes PASS**. Exact-head CI
  and controlled predecessor audit are pending for the correction commit.
- Exact-head GitHub Actions run
  [39160770015](https://github.com/ppow1/Riverview-/actions/runs/39160770015)
  passed at implementation commit `ca7b1f999ecfee4bb00544e4be5658f962bf40ec`:
  **627 passed, 0 failed, 4 skipped** in the full suite; process graphs
  **22 / 565 PASS**; controlled predecessor check **PASS, zero issues**.

## Readiness and remaining gates

See [provider preflight](../components/GRACE_CHATGPT_REVIEW_PROVIDER_PREFLIGHT.md)
for the non-secret operator checks. Source does not establish a production
ChatGPT provider ID: `chatgpt:plus` appears only as a synthetic fixture. Before
any live wake, the operator must verify the approved OAuth issuer/resource,
client/subject/provider/principal mapping, existing exact Grace escalation
grant, reachable MCP route, healthy services, and a Steward-approved harmless
subject, destination, effects, and time window. This PR authorizes no external
send, credential or grant change, service start, deployment, merge, or
production migration.

## Single-Comms5 25-tool Steward review bridge

The existing Comms5 catalog now advertises 25 tools (the historical 21 plus four `reasoning_exchange_*` operations). The Comms5 backend authenticates the existing Steward identity and routes these operations through `StewardReviewBridge`; the bridge records the authenticated Steward as the review actor and derives provider routing only from the locked durable request. It does not construct `ProviderPrincipal` or alter provider OAuth. The same exchange correlation, finite delivery/claim lease, fencing token, expiry, idempotency and immutable subject-digest checks apply. Advice remains non-authoritative and cannot approve, promote, or dispatch. No migration, second MCP app, or public endpoint is introduced.

Before editing, predecessor copies were made with `scripts/revision_control.py backup --task RV-GRACE-CHATGPT-P0-C4-STEWARD-COMMS5-BRIDGE`. The full path/SHA ledger is `.riverview-backups/manifest.jsonl`; notably the prior Comms5 server, migration/operator docs, exchange docs, canonical Comms5 graph, and this revision record are backed up under `20261018T235714*Z`. All earlier source, adapter, test, catalog, dashboard, and Comms5 operation predecessors are also recorded in the same manifest.

Focused offline evidence: `PYTHONPATH=src python3 -m pytest -q tests/test_external_reasoning_mcp.py tests/test_comms5_mcp.py tests/test_comms5_current_runtime.py` — **54 passed, 0 failed**. This covers the existing provider OAuth MCP tools and the Steward bridge tool list, auth boundary, authenticated internal operation routing and dispatch. PostgreSQL-backed restricted-runtime-role exchange acceptance ran in a disposable PostgreSQL 16 cluster: `pg_virtualenv -t sh -c 'RIVERVIEW_TEST_PG_DSN=... PYTHONPATH=src python3 -m pytest -q tests/test_external_reasoning_exchange.py'` — **15 passed, 0 failed, 0 skipped**. The Comms5 tests exercised migration setup, restricted runtime role ACLs, durable correlation, Steward delivery and fenced claim, route and subject-digest rejection, audit provenance, and no objective dispatch. The canonical Comms5 process graph is revision 1.0.15; graph validation is **22 graphs / 567 nodes PASS**. Revision/predecessor check against the branch baseline: **PASS, zero issues**. The repository canonical full command `PYTHONPATH=src python3 -m unittest discover -s tests -v` completed: **635 tests run, 421 passed, 214 skipped, 0 failed**. The skipped cases require a configured integration DSN; the new PostgreSQL module was run separately in the disposable cluster above. A preliminary `pytest -q` recursive collection attempt hit an existing archived-doc test import error (`docs/history/RV-M1.1-002/rev1.0.0/tests/test_runtime_baseline.py` cannot import archived `runtime_baseline`); canonical test discovery is scoped to `tests/` and passed. Exact-head CI is pending.

Connector refresh must use the existing Comms5 MCP registration so the 25-tool catalog is discovered. No autonomous ChatGPT browser wake, live review, external credential change, grant change, service activation, migration, merge, or deployment is included.
