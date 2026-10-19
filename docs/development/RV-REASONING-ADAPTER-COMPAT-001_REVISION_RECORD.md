# Final reasoning adapter integration candidate

**Document Revision:** 1.0.0  
**Task:** RV-REASONING-ADAPTER-COMPAT-001  
**Component:** RESIDENT-REASONING  
**Base candidate:** PR #113, `6e18ff8fd1ea19b19ff769b559bd74e7411cd4bf`  
**Source correction:** PR #114, `cda5581361eccf79d88c67494d76a62b6cc52978`

## Integration scope and dependency

This candidate layers the provider-specific response corrections from #114 onto
the complete four-PR candidate from #113. #114 was authored from the common
pre-integration base, so its whole-branch changes were not applied wholesale:
the source diff removed #113's external escalation intent and immutable source
repository fields, and regressed the resident reasoning narrative and graph.
This integration preserves those #113 contracts and carries over only the
local chat normalization, fixture coverage, compatibility matrix, and matching
canonical graph behavior.

Grace remains one persistent resident with 0.6B, 30B, and 80B model
capabilities. Local chat accepts a string or ordered exact text blocks, rejects
tool/function calls, mixed refusal/text, unsupported content, and multiple
choices, and returns no tool execution. Local proposal parsing retains the
configured external escalation intent and pinned repository reference/revision
fields. External ChatGPT escalation remains a separate exact-authorized durable
MCP advisory exchange. Codex CLI remains the bounded artifact-result adapter
with separate independent artifact verification.

No database migrations are introduced or applied. The test suite uses only an
isolated disposable PostgreSQL cluster and synthetic provider fixtures.

## Validation evidence

- Full isolated UTF-8 PostgreSQL 16 suite: `RIVERVIEW_TEST_PG_DSN='host=/tmp/rv-fourpr-pg port=55449 dbname=riverview_test user=admin1' PYTHONPATH=src python3 -m unittest discover -s tests -v` — **623 passed, 0 failed, 0 errors, 0 skipped** (565.990 seconds).
- Focused reasoning suite covering local adapter, Codex CLI, external reasoning MCP/exchange, resident reasoning, and conversation: **129 passed**.
- Focused adapter plus bounded Codex CLI contract: **53 passed**.
- `python3 scripts/process_graph.py check` — **PASS**, 22 graphs / 565 nodes.
- `python3 scripts/revision_control.py check --baseline /tmp/rv-final-reasoning-baseline.json` — **PASS** against the #113 integration candidate.
- `python3 -m compileall -q src scripts` and `git diff --check` — **PASS**.
- A complete deployment package is built and independently verified for review after commit; it is not installed.

## Commissioning blockers

- Steward review and acceptance of the combined candidate.
- Production-specific local 80B response compatibility must be commissioned
  against the bound provider under a separately approved work plan.
- Production external ChatGPT provider identity, exact grants, credentials,
  and service activation require independent approval and commissioning.
- Source repository identity, immutable revision, worker identities,
  authorization grants, and service configuration remain production change
  prerequisites from PR #113.

No credential, grant, service, production database, or live Engineering work
was changed or exercised by this integration.

## Rollback plan

No schema change is part of this task. Before any later approved commissioning,
record the deployed commit, package digest, and runtime configuration. If
response parsing regresses, stop the separately approved release and restore
the preceding package/configuration; preserve conversation, exchange,
proposal, assignment, and verification records. Rollback or forward repair in
production requires its own approved change record.

## Review checklist

- Steward reviews provider semantics and the exact #113 contracts retained by
  this candidate.
- Verify the package digest and test evidence in the integration PR.
- Before production use, test the configured local 80B provider, verify the
  exact external advisory grants and durable restart behavior, and revalidate
  pinned repository provenance and independent verification.
- No merge, migration, credential/grant change, restart, deployment, package
  installation, or live Engineering objective is authorized by this record.
