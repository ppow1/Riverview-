# ComfyUI Engineering execution adapter

**Document Revision:** 1.0.3
**Changed:** 2026-10-23 UTC | RV-COMFYUI-REGISTERED-CAPABILITY
**Status:** adapter and Grace capability are deployed; OCTOMINER1 ComfyUI runs on the RTX 4090. Authorized Engineering assignment, independent acceptance and artifact download remain unverified without a Steward browser session.

## Contract and authority

The adapter is an action for the existing `ContinuousWorker`, not a new work-order,
queue, authorization, or GPU manager. Its capability is
`engineering.comfyui-image.v1`. `PostgresWorkerAdapter` maps it to the existing
exact `assignment.execute` grant; assignment claiming still checks the registered
worker, scope, capability, lease and current grant. Repository-backed grounding
and preflight remain required.

Grace resolves the exact typed request from the durable `work_order.dispatched`
event. The resolver validates the proposal-step digest and assignment binding,
then returns only `{"workflow_id": <registered id>, "parameters": {...}}`.
`ComfyUIWorkflowRegistry` rejects unknown workflows, unknown or missing
parameters, invalid types and out-of-range values before network access. A
model cannot provide an arbitrary ComfyUI graph or endpoint.

The existing Grace `ContinuousWorker` lifecycle hosts the capability. Grace
routes a proposal only if the ComfyUI worker and verifier are both configured.
The active `worker:grace-engineering` identity is extended only under its exact
`worker.register` grant; work claims still require its `assignment.execute`
grant, scoped to `work-order:engineering`. The distinct existing verifier
identity uses its existing `assignment.verify` grant. The capability adds no
GPU-management or model-service authority.

When enabled, the Grace service includes the ComfyUI capability in the exact
worker registration identity before starting `ContinuousWorker`. This keeps
the persisted capability set consistent across clean restarts. Disabling the
capability requires an authorized update to that same worker registration
before changing the service flag; a stale registration fails startup closed.

The endpoint is fixed at worker startup, plain HTTP, and must be a literal
loopback or private IP address. The current commissioning registration contains
one worker. Its host endpoint and GPU UUID are deployment configuration; the
adapter uses the endpoint but does not persist GPU indexes or change model
placement. Dynamic multi-host discovery, reservation-aware selection, and
authorized manual GPU preference are separate follow-up work and are not claimed
as implemented by this commissioning release.

## Execution, recovery and artifacts

The action posts only the rendered registered graph to `/prompt`, tagged with
the assignment and registered template digest. It polls `/history/{prompt_id}`
and `/queue`, reports only assignment, prompt ID, status and output count to the
optional progress callback, and accepts image references only from registered
output nodes. Bounds are 2 MiB for graphs, one hour for execution, eight images,
16 MiB per image and 48 MiB total. The action validates PNG chunk CRCs, JPEG
envelope, or WebP RIFF length before writing.

Binary files use the configured ComfyUI artifact root and assignment-bound
storage name `<sha256(assignment-id)>/<sha256(output-name)[0:12]>`. The worker
owns the group-shared root (mode 2750, group `riverview`), assignment directories
(mode 2750), and files (mode 0640); the dashboard receives group read and
traverse access only. Execution journals remain private in the Grace service
state directory. PostgreSQL stores only bounded metadata and SHA-256 values.

`ComfyUIOutputVerifier` independently reopens each file without following
symlinks and verifies assignment binding, media, sizes, hashes, workflow
provenance and canonical result digest. Semantic image quality still requires
task criteria and an independent human or approved vision review.

A durable private journal records workflow hash, prompt ID, output inventory and
execution state. Retries with a known prompt ID resume polling and recover
missing output files; completed retries return the same result. A lost connection
after prompt creation never causes a second submission. A lost POST response
before the prompt ID is known becomes `indeterminate` and fails closed. Cancel
removes only the exact prompt from ComfyUI's pending queue and never calls global
`/interrupt`; it cannot preempt a running job.

The authenticated dashboard download endpoint is
`GET /api/v1/assignments/{assignment_id}/artifacts/{1..8}`. It serves only an
output from a completed assignment with an intact result digest and latest
independent `ACCEPTED` decision. Account-cookie sessions must hold operator or
Steward role; the protected internal service bearer remains supported. Path
components are hash-derived, opened with no-follow semantics, checked against
the group-read mode and size limits, and rehashed before returning as an
attachment. There is no public static artifact mount.

The ComfyUI host unit binds to its configured private interface. Its API has no
authentication, so the dedicated `riverview-comfyui-firewall.service` restricts
port 8188 to Camrui `192.168.1.155`. Confirm the caller's observed source address
before activating that rule.

## Qualification

Mock-server tests cover successful execution, invalid workflows and parameters,
bounded timeout and resume, duplicate submission, lost POST response, lost
connection after a known prompt, partial-output recovery, queued cancellation,
structured work-order grounding and independent image integrity verification.
Dashboard tests cover authentication, successful binary delivery and tamper
rejection. Mock results do not count as real GPU acceptance.

## Commissioning and rollback

1. Verify the GPU host identity, exact GPU UUID, 30B service, 80B P100 placement
   and protected model health checks. Stop only the 30B under operator
   authorization; preserve the prior unit and configuration.
2. Pin ComfyUI and its runtime to the installed host software. OCTOMINER1 runs
   ComfyUI `v0.9.2` (`8f40b43e0204d5b9780f3e9618e140e929e80594`), PyTorch
   `2.6.0+cu124`, and `comfy-kitchen 0.2.6`. Newer ComfyUI/kitchen releases
   require a newer PyTorch/CUDA stack than the host driver provides; do not
   upgrade the model host runtime as part of routine worker startup.
3. Bind the service to the configured GPU UUID through `CUDA_VISIBLE_DEVICES`
   and restrict its unauthenticated API to the Camrui controller source. Use
   writable service-owned user, temp, database, and output paths.
4. Keep the operator-reviewed registry in `deploy/comfyui/workflows.json`, which
   the worker reads from its root-owned immutable release. Do not place it below
   `/etc/riverview`: that directory is root-only on Camrui. Verify models and
   nodes through `/object_info`. The service has started on OCTOMINER1 and its
   `/system_stats` and required SD Turbo nodes respond.
5. Enable the Grace worker only after verifying current exact grants and
   confirming no active Engineering assignment will be interrupted by its
   service restart.
6. Submit an authorized image request through Grace's existing Engineering
   work-order flow. Verify ComfyUI prompt progress, saved image metadata,
   independent verification and authorized byte-for-byte download.
7. Deploy only the immutable qualified Camrui release. Preserve the previous
   dashboard and Grace releases and both integration drop-ins. Roll back by
   restoring those releases and removing only the ComfyUI drop-ins. Restore the
   30B only after ComfyUI is stopped and the 4090's VRAM is clear. Recheck 0.6B
   and 80B health after either service transition.
