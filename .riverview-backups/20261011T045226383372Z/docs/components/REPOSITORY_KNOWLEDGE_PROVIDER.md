<!--
Riverview~ Controlled Document
File: docs/components/REPOSITORY_KNOWLEDGE_PROVIDER.md
Component: REPOSITORY-KNOWLEDGE-PROVIDER
File Revision: 1.0.0
Purpose: Specify bounded, commit-pinned repository grounding for worker tasks
Authority: Read-only retrieval; does not grant assignment or worker authority
Changed: 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE | Initial contract
History: Git and .riverview-backups/manifest.jsonl
-->
# Repository knowledge provider

**Status:** Isolated engineering and tests; not configured in the live worker service.  
**Implementation:** `src/riverview_core/worker_adapter/repository_knowledge.py`  
**Contract:** Existing knowledge-provider v1.0.0; this is one replaceable provider.  
**Workflow:** `rv:repository-knowledge-provider:pinned-worker-contracts`

## Scope and trust boundary

The provider returns a fixed, bounded set of worker-contract documents from the
exact approved source revision. The current allowlist supports the worker
adapter contract and action `deterministic.sha256.v1`. It reads either a clean
Git checkout whose `HEAD` matches the configured full commit ID or an immutable
Camrui package containing `SOURCE_COMMIT` and `PACKAGE_SHA256SUMS`. It does not
search arbitrary paths, follow user-provided paths, access the network, execute
retrieved text, or write learning data.

`VERIFIED` means every configured source was read from the pinned revision,
passed integrity checks, decoded, and fit within the provider's byte limits.
The result carries stable `repo://` references, the full commit ID, and a
SHA-256 over ordered path/content pairs. This establishes retrieval provenance;
it does not establish that a requested assignment is authorized, that the code
is safe, or that a worker output is acceptable. Existing Steward grants and the
independent outcome verifier remain separate gates.

For an unknown contract or action, the allowlist lookup is complete and returns
`NO_MATCH`. A mismatch between an assignment's contract reference and an
allowlisted action returns `CONTRADICTORY`. A dirty checkout or pin mismatch is
`UNVERIFIED`; oversized material is `INCOMPLETE`; missing Git/package data or
read errors are `UNAVAILABLE`. None authorizes work. The worker records statuses,
references, revisions, hashes and completeness through the existing durable
knowledge-observation ledger. It never stores document bodies there.

`record_learning` returns `UNAVAILABLE`: this read-only provider has no learning
store. The worker still records that outcome in the existing observation ledger.
This is a deliberate capability boundary, not completed institutional learning
or a substitute for the independently developed OctoMiner provider.

## Verification and operation

Run provider unit tests with:

```sh
PYTHONPATH=src python3 -m unittest tests.test_repository_knowledge -v
```

Run the PostgreSQL-backed worker integration test as part of the full suite in
an isolated PostgreSQL test database. That test uses the actual provider and
worker contract, stores a result artifact, and sends it to the distinct
independent verifier. It does not target Camrui's shared schema.

See the [generated process flow](REPOSITORY_KNOWLEDGE_FLOW.md),
[diagnostic cookbook](REPOSITORY_KNOWLEDGE_COOKBOOK.md),
[worker contract](WORKER_ADAPTER.md), and
[M3.3 commissioning record](../development/M3.3-001_REVISION_RECORD.md).

**Deployment status:** No live authority grant, worker, secret, migration, or
service configuration was created by this component. M3.3 remains open until
authority is enforced on the live control path and its two-assignment recovery
demonstration is independently commissioned.
