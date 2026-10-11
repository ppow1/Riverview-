<!--
Riverview~ Controlled Document
File: docs/components/REPOSITORY_KNOWLEDGE_COOKBOOK.md
Component: REPOSITORY-KNOWLEDGE-PROVIDER
File Revision: 1.0.0
Purpose: Diagnose and safely recover repository knowledge lookup outcomes
Authority: Read-only diagnostics; never bypass VERIFIED or Steward grant checks
Changed: 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE | Initial cookbook
History: Git and .riverview-backups/manifest.jsonl
-->
# Repository knowledge provider cookbook

This procedure applies to the isolated, read-only provider. The component is
not enabled in the live worker service. Do not hand-edit assignment authority or
replace a non-verified result with a claimed success.

## Read-only diagnostics

In the source checkout, verify the configured full commit and the source files
used for grounding:

```sh
git rev-parse --verify 'HEAD^{commit}'
git status --porcelain --untracked-files=no -- \
  docs/components/WORKER_ADAPTER.md \
  src/riverview_core/worker_adapter/adapter.py \
  src/riverview_core/worker_adapter/continuous.py \
  src/riverview_core/worker_adapter/knowledge_provider_v1/contract.py \
  src/riverview_core/worker_adapter/repository_knowledge.py
```

The first command must equal the provider's configured approved commit. The
second must print nothing. In a built release, verify the package source and
checksums without printing document contents:

```sh
cat SOURCE_COMMIT
sha256sum --strict --check PACKAGE_SHA256SUMS
```

The configured source pin must equal `SOURCE_COMMIT`; every checksum line must
pass. These commands are read-only. Do not repair package bytes in place; build
a new package and deploy it through the controlled release procedure.

## Symptoms and recovery

| Observable result | Likely cause | Safe action and resume point |
|---|---|---|
| `NO_MATCH` on grounding | Missing or unknown `contract_ref` | Bind the assignment only to a reviewed, registered contract reference; resume at the next worker poll. Do not infer a contract from `objective_ref`. |
| `NO_MATCH` on preflight | Action identifier is outside the allowlist | Review the worker/action contract and add a versioned allowlist mapping with tests; never allow arbitrary shell or commands. |
| `CONTRADICTORY` | Action's registered contract differs from the assignment `contract_ref` | Resolve the contract assignment through the authorized intake path; do not rewrite scope or authority in SQL. |
| `UNVERIFIED` | Source pin differs from `HEAD`/`SOURCE_COMMIT`, or a source file is dirty/tampered | Rebuild from an exact reviewed commit; preserve the current release for rollback; resume only after hashes match. |
| `INCOMPLETE` | A source exceeds the per-file or total byte cap | Keep the assignment waiting; review whether the contract can be narrowed in a new revision. Do not raise limits merely to pass the task. |
| `UNAVAILABLE` | Git/package metadata is absent, a source is unreadable, or learning writes were requested | Restore the source package/provider capability; retry the lookup. `record_learning` is intentionally unavailable here. |

The worker persists status, source references, commit, hash, completeness and
timestamp in `knowledge_observations`. Use the existing
[worker-adapter cookbook](WORKER_ADAPTER_COOKBOOK.md) to inspect worker attempts
and observations. Do not print credentials or source contents into logs.

## Failure/recovery cautions

- All non-`VERIFIED` grounding, preflight and regrounding outcomes must leave
  the assignment in `WAITING_FOR_EVIDENCE`; unrelated assignment polling
  continues.
- This provider's `VERIFIED` is source retrieval evidence only. It cannot create
  a Steward grant, register a worker, authorize a database mutation, or replace
  independent output verification.
- Never edit `riverview_dev`, drop/recreate shared tables, or restart unrelated
  services to clear a lookup status. This provider is not yet commissioned as a
  live service dependency.
- Escalate if an allowlisted source is missing from the immutable package, its
  checksum differs, a package/commit pin cannot be reconciled, or a contract
  reference conflicts with the accepted assignment scope.
