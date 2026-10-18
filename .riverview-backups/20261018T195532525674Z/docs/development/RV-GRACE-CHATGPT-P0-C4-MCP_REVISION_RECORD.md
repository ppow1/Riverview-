<!--
Riverview Controlled Document
File: docs/development/RV-GRACE-CHATGPT-P0-C4-MCP_REVISION_RECORD.md
Component: EXTERNAL-REASONING-MCP-TRANSPORT
File Revision: 1.0.0
Purpose: Record C4 exact-proposal MCP integration, isolated verification, and live gates
Authority: Existing provider-scoped MCP identity and resident.reasoning.escalate grant only
Changed: 2026-10-18 UTC | RV-GRACE-CHATGPT-P0-C4-MCP | Initial implementation record
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

The subject is bounded to 16 KiB after JSON encoding. It contains a nonempty
summary of at most 8,000 characters and one to 32 nonempty steps of at most
2,000 characters each. The complete provider list item remains within the
existing 32 KiB context response bound. The browser bridge receives only its
existing request/correlation IDs and fixed wake operation.

## Files and predecessor protection

| File | Revision | Predecessor backup | Predecessor SHA-256 |
|---|---:|---|---|
| `src/riverview_core/resident_execution/external_reasoning_mcp.py` | 1.1.3 | `.riverview-backups/20261018T194638243733Z/src/riverview_core/resident_execution/external_reasoning_mcp.py` | `d0df25bc9a6c04776c7eba7d134b01e5573921bb1614e87858d73fe46fc9684d` |
| `tests/test_external_reasoning_mcp.py` | 1.0.8 | `.riverview-backups/20261018T194638527021Z/tests/test_external_reasoning_mcp.py` | `2ab9b68b42ed1d18ada6c4e22a1ee7025028242b273b146eeb97b3da8fe174b3` |
| `scripts/run_external_reasoning_mcp.py` | 1.1.1 | `.riverview-backups/20261018T194844646699Z/scripts/run_external_reasoning_mcp.py` | `9fabfb79993da4961d23483daf8d10acb5b3c1222ad9c334939b87e5982f7e9e` |

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
  exact-head CI, and final controlled revision inventory remain pending C2/C3/W3
  integration. No live MCP client or ChatGPT request was made.

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
