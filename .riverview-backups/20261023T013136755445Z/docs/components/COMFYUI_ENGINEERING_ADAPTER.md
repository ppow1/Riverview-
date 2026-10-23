# ComfyUI Engineering execution adapter

**Status:** source implementation and mock qualification only; not commissioned or deployed.

## Contract and authority

The adapter is an action for the existing `ContinuousWorker`, not a new work-order,
queue, authorization, or GPU manager. Its capability is
`engineering.comfyui-image.v1`. `PostgresWorkerAdapter` maps it to the existing
exact `assignment.execute` grant; assignment claiming still checks the registered
worker, scope, capability, lease and current grant. Repository-backed grounding
and preflight remain required.

Construct `ComfyUIWorkflowRegistry` from the operator-reviewed workflow registry
and a `ComfyUIKnowledgeProvider` around the normal verified knowledge provider.
Its required `request_resolver(assignment)` must read a typed request from the
already authorized, durable Engineering work order and return only
`{"workflow_id": <registered id>, "parameters": {...}}`. The registry rejects
unknown workflows, unknown/missing parameters, invalid types and out-of-range
values before network access. Do not use a model-generated arbitrary ComfyUI graph
or a browser-supplied endpoint.

The ComfyUI endpoint is fixed at worker startup, plain HTTP, and must be a literal
loopback or private IP address. GPU selection remains external configuration of
the existing resource-control/deployment layer (for example, the ComfyUI service
runtime's `CUDA_VISIBLE_DEVICES`); this adapter neither selects a GPU nor changes
model placement. Do not register the ComfyUI worker until the operator has an
exclusive allocation policy for the configured ComfyUI instance.

The existing worker lifecycle can host it without a new scheduler:

```python
engine = ContinuousWorker(
    adapter, worker_id, worker_credential,
    knowledge=ComfyUIKnowledgeProvider(verified_provider, persisted_request_resolver),
    action=comfyui_action,
    action_capability=ComfyUIAction.CAPABILITY,
    action_effect_class="retry_safe",
    recovery_max_retries=3,
)
```

The worker must be registered for this exact capability and the scope must have
current grants. The independent verifier must use a different identity with the
existing `assignment.verify` grant. Service-unit allowlisting, credential
provisioning, capability-specific verifier dispatch, and the persisted request
resolver are not installed by this source-only implementation.

## Execution, recovery and artifacts

The action POSTs only the rendered registered graph to `/prompt`, tagged with the
assignment and registered template digest. It polls `/history/{prompt_id}` and
`/queue`, reports only assignment/prompt/status/output counts to the optional
progress callback, and accepts image references only from registered output
nodes. It bounds the graph (2 MiB), response, time (up to one hour), count (8),
per-image bytes (16 MiB), and aggregate image bytes (48 MiB). Image references
cannot select arbitrary filesystem paths. The action verifies PNG chunk CRCs,
JPEG envelope, or WebP RIFF length before writing.

Images use the existing private artifact-root layout:
`<sha256(assignment-id)>/<sha256(output-name)[0:12]>`. Directories are mode
0700 and files mode 0600. PostgreSQL receives only bounded JSON metadata and
SHA-256 digests; the large binary image bytes stay in the artifact store. The
`ComfyUIOutputVerifier` independently opens each stored file without following
symlinks and checks assignment-bound names, media, sizes, hashes, provenance,
and the canonical ledger result digest. Semantic image suitability still needs
acceptance criteria and a separate human or approved vision review.

A durable 0600 journal records the workflow hash, prompt id, output inventory,
and execution state. Retries with a known prompt id resume polling and recover
missing output files; completed retries return the same artifact result. A lost
connection after prompt creation never causes a second POST. If the POST response
is lost before the prompt id is known, state becomes `indeterminate`; the adapter
fails closed and requires explicit reconciliation rather than risking duplicate
GPU work. `cancel()` removes only the exact prompt from ComfyUI's pending queue.
It does not call the global `/interrupt` endpoint, so a running prompt cannot
currently be preempted safely on a shared instance.

The existing dashboard already projects registered worker capabilities,
assignment state, result metadata, and artifact path. This implementation returns
those projection fields plus an artifact inventory. There is not currently a
browser download route for these binary worker artifacts; adding an authorized,
assignment-scoped download operation is a commissioning dependency before Grace
can return generated images directly in conversation.

## Mock qualification

Run from the source root:

```sh
PYTHONPATH=src python3 -m unittest tests.test_comfyui_adapter -v
```

The test module runs a local mock HTTP server, never a real ComfyUI endpoint. It
covers successful prompt/output, workflow/parameter rejection, bounded timeout
and resume, duplicate idempotency, lost POST response, lost connection after a
known prompt, partial-output recovery, queued cancellation, structured verified
work-order grounding, and independent binary artifact verification.

## Commissioning sequence (not performed)

1. Identify the actual GPU host and current 30B service through its operator
   inventory. This source environment had no NVIDIA device, model service, or
   ComfyUI installation, so no 30B process was stopped and no GPU was allocated.
2. Prepare a protected registry of small workflows and approved node/input
   bindings; pin each registry revision and hash. Verify all referenced models,
   custom nodes and output nodes are installed on the ComfyUI runtime.
3. Define the typed image request in the existing authorized Engineering
   work-order/provider contract. The current generic assignment row does not
   contain workflow id/parameters, so the resolver is a required integration
   item; it may not introduce a second work-order database.
4. Add a separately provisioned worker identity with exact
   `worker.register` and `assignment.execute` grants scoped to
   `work-order:engineering`; register only this capability. Configure the
   existing worker service lifecycle with the private endpoint, artifact/state
   directories, immutable workflow registry, and a bounded timeout. Do not give
   it permission to stop models or manage GPU allocation.
5. Add the Comfy output verifier to the existing distinct verifier identity and
   capability dispatch. Run worker, verification and dashboard projection tests
   against isolated PostgreSQL before activation.
6. Confirm the existing GPU resource controller can reserve/release the chosen
   allocation and can report conflicts. ComfyUI must be dedicated or support
   prompt-specific cancellation before active-job cancellation can be enabled.
7. Add authorized artifact download to the existing dashboard/Grace operation
   boundary, with assignment scope, current auth/CSRF rules, path-safe serving,
   byte limits, and tests. No public static file mount.
8. After isolated real-GPU workflow execution and integration qualification,
   submit a separate controlled deployment proposal. No production unit or
   service is installed by this change.
