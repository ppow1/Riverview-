# Riverview~ worker adapter contract

**Document Revision:** 1.0.1
**Component:** WORKER-ADAPTER
**Milestone:** M2.1
**Status:** IN PROGRESS — isolated engineering; no service deployment
**Implementation:** `src/riverview_core/worker_adapter/adapter.py`

## Scope and trust boundaries

The first adapter slice registers a worker identity, capability list, and exact
assignment authority scope. Registration creates a random high-entropy bearer
credential, returns it once, and stores only its SHA-256 digest. Execution
compares credentials in constant time, checks the registered capability and
requires worker scope to equal the assignment's `authority_ref`. Registration
itself is a trusted control-plane operation; this library does not authenticate
its registrar or validate the authority grant externally.

The only executable task is `deterministic.sha256.v1`: hash caller-provided UTF-8
text and return its digest and byte count. No shell, subprocess, network,
filesystem, GPU, or arbitrary code execution occurs. The input content is not
stored; only its digest and the deterministic result are persisted.

Each attempt records assignment, worker, fencing generation, capability,
idempotency key, input digest, status and timestamps. Results are separate
durable records with result digests. A repeated key returns the prior result only
when assignment, worker, generation, capability and input digest match; collision
is rejected. An unfinished attempt remains visible to `incomplete_attempts()`
for worker-loss detection. Result commit rechecks the active lease and records a
lost-lease failure rather than accepting a stale worker result.

The M2.1 migration is separate and explicit. No schema DDL is applied at adapter
startup and no M2.1 migration has been applied to shared `riverview_dev`. Secret
provisioning for a deployed worker and external worker transport/authentication
remain future operational integration work.

See the [workflow graph](WORKER_ADAPTER_FLOW.md),
[operational cookbook](WORKER_ADAPTER_COOKBOOK.md), and
[RV-M2.1-001 record](../development/M2.1-001_REVISION_RECORD.md).
