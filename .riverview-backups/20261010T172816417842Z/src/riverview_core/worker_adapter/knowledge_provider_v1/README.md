# Riverview knowledge-provider handoff

**Document Revision:** 1.0.0  
**Contract version:** `1.0.0`  
**Status:** Frozen additive interface for independent provider implementation  
**Runtime package:** `src/riverview_core/worker_adapter/knowledge_provider_v1/`  
**Owner:** Riverview Steward

This directory is the self-contained v1 handoff for OctoMiner 2. It contains the
actual Python protocol and result type used by Camrui, a JSON result schema, an
explicitly simulated provider, and standalone contract tests. The mock is test
data; it does not retrieve institutional knowledge or establish real facts.

## Interface

Implement `KnowledgeProvider` from `contract.py`. Inputs are read-only mappings
containing at least `id: str`, `authority_ref: str`, and `objective_ref: str`;
the current worker may supply additional ledger fields. `action` and `trigger`
are non-empty strings. `outcome` is a mapping describing a result or failure.
Provider calls are synchronous and must be safe for concurrent calls.

```python
ground_assignment(assignment: Mapping[str, Any]) -> KnowledgeResult
preflight_action(assignment: Mapping[str, Any], action: str) -> KnowledgeResult
reground_assignment(assignment: Mapping[str, Any], trigger: str) -> KnowledgeResult
record_learning(assignment: Mapping[str, Any], outcome: Mapping[str, Any]) -> KnowledgeResult
```

`KnowledgeResult` has these exact fields:

| Field | Type | Meaning |
|---|---|---|
| `status` | `KnowledgeStatus` | One of the six stable machine values below |
| `value` | `Any` | Optional provider fact/data for the worker; it is not persisted by this interface |
| `source_references` | `tuple[str, ...]` | Stable references such as `repo://docs/file.md`, `https://…`, or `urn:…` |
| `source_revision` | `str \| None` | Immutable source revision/version when available |
| `source_sha256` | `str \| None` | Lowercase 64-character SHA-256 of the source material when available |
| `retrieval_complete` | `bool \| None` | Whether the provider completed the relevant search/retrieval scope |

`VERIFIED` requires one or more safe source references and
`retrieval_complete=True`. The provider may claim VERIFIED only after checking
the cited source and resolving relevant contradictions for the requested scope.
This is provider evidence, not independent task acceptance. Completion still
requires Riverview's separate outcome verifier. `INCOMPLETE` cannot claim a
complete retrieval. `NO_MATCH` means the completed search scope returned no
applicable source; it is not permission to invent a fact. A missing provider
returns `UNAVAILABLE`. Unknown result objects map to `UNVERIFIED`; provider
exceptions map to `UNAVAILABLE`.

## Status meanings

- `VERIFIED`: complete, source-backed answer suitable for the gated action.
- `NO_MATCH`: lookup completed and found no applicable knowledge.
- `UNAVAILABLE`: provider absent, timed out, exhausted its bounded call slots, or errored.
- `INCOMPLETE`: some retrieval occurred but the requested scope was not completed.
- `CONTRADICTORY`: relevant sources conflict and remain unresolved.
- `UNVERIFIED`: result lacks verification; it never authorizes an action.

Only VERIFIED grounding, action preflight, and pre-action regrounding permit the
worker to proceed. Every other outcome persists as an observation and leaves
that assignment `blocked` with workflow step `WAITING_FOR_EVIDENCE`; the next
worker poll remains eligible to process other assignments. There is no fallback
to guessed API signatures, commands, or contracts. Learning capture is recorded
as an outcome and never automatically promotes knowledge or authorizes work.

The current worker wait deadline defaults to five seconds and is configurable per
worker. A timed-out call is recorded as UNAVAILABLE; its late result is discarded
and cannot authorize the current action. In-process Python cannot forcibly stop a
provider thread. At most four timed-out provider calls per worker remain in
flight; when all slots are occupied, new calls immediately return UNAVAILABLE.
Provider implementations must therefore use their own bounded I/O deadlines,
avoid unbounded resource use, and tolerate concurrent calls. A provider timeout
does not stop other worker instances or the global assignment scheduler.

Observation persistence includes operation, status, action label, safe source
references, source revision/hash, retrieval completeness, and database timestamp.
Provider `value` and arbitrary `outcome` payloads are not copied into this
observation ledger. Do not place credentials or private payloads in references.

## Compatibility

Contract `1.0.0` is the stable v1 line. Patch releases clarify documentation or
fix package defects without changing behavior. A new method, field, status,
signature, type, or status meaning requires a new major contract directory and an
explicit compatibility adapter; consumers must not silently assume unknown
statuses are VERIFIED. Providers may keep optional private configuration outside
this interface. The scheduler and worker do not depend on provider internals.

Relevant process-graph nodes:

- `rv:worker-adapter:deterministic-attempt:continuous-cycle`
- `rv:worker-adapter:deterministic-attempt:ground`
- `rv:worker-adapter:deterministic-attempt:preflight`
- `rv:worker-adapter:deterministic-attempt:reground`
- `rv:worker-adapter:deterministic-attempt:evidence-wait`
- `rv:worker-adapter:deterministic-attempt:learning`

## Independent implementation and test

Implement the four methods using only this contract. Keep retrieval-specific
dependencies and storage private to the provider. Return one of the declared
statuses, cite stable source references, set completeness honestly, and never
return VERIFIED for a partial, unavailable, unverified, or contradictory result.
Do not change the scheduler or worker implementation to integrate a provider.

From the repository root, run the isolated standard-library tests:

```sh
PYTHONPATH=src python3 -m unittest \
  riverview_core.worker_adapter.knowledge_provider_v1.test_contract -v
```

The same files can be zipped and tested after extraction with:

```sh
python3 -m unittest test_contract -v
```

The repository package has no secret, database, network, or Camrui runtime
dependency. See `manifest.json` for the contract version, source commit, and
checksums. The linked graph nodes describe the integration points; this package
does not implement institutional retrieval, learning promotion, or a service.
