<!--
Riverview~ Controlled Document
File: docs/components/REPOSITORY_KNOWLEDGE_PROVIDER.md
Component: REPOSITORY-KNOWLEDGE-PROVIDER
File Revision: 1.0.0
Purpose: Specify bounded source-backed knowledge retrieval for worker contracts
Authority: Read only; repository content cannot grant action authority
Changed: 2026-10-11 UTC | RV-M3.3-REPOSITORY-KNOWLEDGE | Initial provider contract
History: .riverview-backups/manifest.jsonl and Git
-->
# Repository knowledge provider

**Status:** Engineering integration; live worker-service commissioning remains open.
**Implementation:** `src/riverview_core/worker_adapter/repository_knowledge.py`
**Contract:** `worker_adapter.knowledge_provider_v1`, version `1.0.0`
**Process graph:** `rv:repository-knowledge-provider:pinned-worker-contracts`

## Scope

The provider implements the frozen in-process knowledge-provider contract
against an exact repository revision. It is intentionally limited to the
deterministic worker contract and does not search arbitrary repository files,
interpret retrieved text as code, change authority, or write institutional
learning. A future institutional provider may replace it without scheduler
changes by implementing the same v1 interface.

The sole registered contract is
`repo://riverview/worker-adapter-contract.v1`, mapped to
`deterministic.sha256.v1`. It retrieves the component contract, worker adapter,
continuous worker, provider interface, and provider implementation. Unknown
contract references and unsupported action names return `NO_MATCH` with a
complete search result. A supported action paired with an unrelated contract
returns `CONTRADICTORY`.

## Source verification

Configure an exact full lowercase Git object ID (40 or 64 hexadecimal
characters). The provider requires checked-out `HEAD` to equal that pin and
reads only committed source blobs. Dirty checked-in contract files are
`UNVERIFIED`. A packaged release may instead supply `SOURCE_COMMIT` and
`PACKAGE_SHA256SUMS`; every allowlisted file must have a unique valid manifest
entry whose digest matches the bytes on disk. The checkout or package must be
immutable to the worker account in deployment.

Each file is limited to 256 KiB and the full retrieval to 768 KiB. A limit
returns `INCOMPLETE`; Git, filesystem, or decoding failures return
`UNAVAILABLE`. Pin or checksum disagreement returns `UNVERIFIED`. The provider
returns all stable `repo://` source references, source revision, a deterministic
aggregate SHA-256 and `retrieval_complete=True` only after reading the complete
allowlist. Worker persistence records the status and provenance, not the
retrieved text.

Only `VERIFIED`, complete retrieval reaches the worker action boundary. All
other statuses preserve an assignment-local wait. An unavailable provider is
never equivalent to a verified lookup. `record_learning` returns
`UNAVAILABLE`: this read-only provider has no learning store.

## Operations and verification

Run isolated provider tests with:

```sh
PYTHONPATH=src python3 -m unittest tests.test_repository_knowledge -v
```

The PostgreSQL worker integration test also exercises this provider using a
temporary Git snapshot and unique `rvtest_*` schema:

```sh
PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='<isolated test DSN>' \
  python3 -m unittest tests.test_worker_adapter.WorkerAdapterTests.test_pinned_repository_provider_drives_worker_artifact_and_independent_verification -v
```

Use only a disposable PostgreSQL test database for the latter command. Live
deployment additionally requires a protected, read-only, commit-pinned package,
a registered credentialed worker, current exact grants, and an independent
verifier identity. No such live worker service is implied by contract tests.

See [worker adapter operations](WORKER_ADAPTER_COOKBOOK.md),
[authority operations](INSTITUTIONAL_AUTHORITY_COOKBOOK.md), and the
[repository knowledge process graph](REPOSITORY_KNOWLEDGE_FLOW.md).
