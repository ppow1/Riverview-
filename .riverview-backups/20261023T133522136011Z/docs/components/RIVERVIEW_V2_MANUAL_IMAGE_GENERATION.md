# Riverview V2 Manual Image Generation

**Document Revision:** 1.0.2  
**Component:** `V2-MANUAL-IMAGE-GENERATION`  
**Task:** `RV-V2-MANUAL-IMAGE-GENERATION-248`  
**Status:** Production integration candidate  
**Changed:** 2026-10-23 UTC
**Changed:** 2026-10-23 UTC | RV-V2-MANUAL-IMAGE-GENERATION-248 | Record separation between the fixture preview source and the production V2 bundle.

## Contract

The deployed V2 Manual Image Generation view in `website/v2/deployed/` submits operator initiated requests to the
registered ComfyUI workflow registry and runs the existing bounded
`ComfyUIAction` followed by `ComfyUIOutputVerifier`. It does not create an
Engineering work order, Grace proposal, alternate execution queue, image engine,
or GPU manager. Manual request records carry `execution_kind=operator_manual`
and null Engineering/work-order identities.

The browser uses the Dashboard account cookie. Only an account with the
`operator` or `steward` role can use the catalog, submit, inspect, or retrieve
artifacts. Mutating submission also passes the Dashboard CSRF check. Dashboard
bearer credentials alone are rejected at this API boundary. History is scoped
to the account, except that Stewards can review all records.

## Workflow and worker behavior

The browser obtains workflow IDs, revisions, parameter bindings, and fixed
dimensions from the runtime workflow registry. Inputs are rendered from those
bindings and are validated again by `ComfyUIWorkflowRegistry` before submission.
The current registered SD-Turbo graph binds prompt and seed and produces a
512-by-512 PNG.

The worker endpoint and workflow registry are systemd configuration. The
currently configured ComfyUI worker is the only execution target. Its device
name and VRAM are read from ComfyUI system statistics and copied into request
provenance only when the endpoint reports exactly one visible device; multiple
visible devices leave worker identity unavailable instead of assuming index 0.
The UI shows existing GPU telemetry and reservations, but per-request
GPU selection remains disabled because there is no qualified allocator and
unknown reservation state is not proof of availability. No model service is
stopped, reconfigured, or reassigned by this feature.

## Request and artifact lifecycle

1. The Dashboard validates the account session, role, CSRF token, request shape,
   idempotency UUID, registered workflow, and input parameters.
2. A mode-0600 owner-only durable record is atomically written before an
   asynchronous worker starts. A single configured ComfyUI worker is bounded to
   one active manual request.
3. `ComfyUIAction` submits and tracks the request using a stable `manual:<uuid>`
   identity and its existing journal/recovery behavior. Progress updates are
   persisted to the manual request record.
4. The existing independent output verifier must accept the artifact. The
   Dashboard additionally validates its PNG header and dimensions and stores
   its exact path, host, size, SHA-256, device identity and workflow provenance.
5. The browser previews and downloads through the authenticated, account-scoped
   image route. The route opens the artifact through no-follow directory/file
   descriptors and verifies owner, group, mode, size, media type and SHA-256
   before returning bytes.

If an outcome is uncertain, refresh history using the same request ID. Repeating
the same UUID and identical workflow parameters returns the original request;
reusing it for different input returns a conflict. The adapter relies on the
existing ComfyUI action journal to recover an interrupted submission without
silently duplicating indeterminate GPU work. Timeout and worker failures are
reported as failed records. Artifact download remains available only for a
verified completed PNG.

## Configuration and operation

Install `deploy/systemd/riverview-status-dashboard-manual-comfyui.conf` as a
Dashboard service drop-in after preparing the configured artifact and state
directories for the `riverview` service account. The configuration names the
existing ComfyUI endpoint and registered workflow file; those values are not
compiled into the adapter. The Dashboard service is the only service restarted.
Disable the feature by removing this drop-in and restarting only the Dashboard.

Before release, verify that the configured endpoint reports the intended
ComfyUI worker, the workflow registry can be read by the service account, and
the artifact/state roots have the required ownership and modes. Validate account
authorization and CSRF rejection. A rollback restores the previous Dashboard
`current` target, removes only this feature drop-in and restores the previous
V2 alias target; then restart the Dashboard and reload Nginx only if its alias
was changed. Preserve both immutable predecessor releases.

## Acceptance evidence

The fixture-only LAN preview remains in `website/v2/`; it is intentionally
separate from the production source tree under `website/v2/deployed/`. The
production V2 bundle retains its authenticated Dashboard integrations. Its
static release embeds the authenticated Snapshot mode marker already present in
the deployed bundle; the separate Dashboard-served route injects the marker at
request time and keeps it out of the fixture preview source.

Focused HTTP and service tests are in `tests/test_manual_image_generation.py`
and `tests/test_manual_image_generation_http.py`. Browser fixture acceptance is
run with `scripts/verify_v2_manual_image_generation_browser.py`. These fixtures
verify the UI contract and do not establish production authentication or a live
GPU generation; those require an authorized account session and actual
ComfyUI execution.
