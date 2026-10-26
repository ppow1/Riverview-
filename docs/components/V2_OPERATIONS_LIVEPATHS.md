<!--
Riverview~ Controlled Document
File: docs/components/V2_OPERATIONS_LIVEPATHS.md
Component: RIVERVIEW-V2-OPERATIONS
Revision: 1.0.0
Changed: 2026-10-26 UTC | RV-V2-OPERATIONS-LIVEPATHS-20261026 | Record recovered runtime paths, safe independently deployable increments, and confirmed integration boundaries.
Authority: Read-only operational reporting; no grants or workload changes
-->
# V2 operations live paths — 2026-10-26

## Confirmed runtime paths

The active V2 static baseline before this increment was
`RV-WEB-V2-OPS-VISUAL-8d2489f80f31`. The Dashboard service's active immutable
release was `a5d58640ce019f0555a6c2a4d8780467fa2ccebe`; the independent
notification dispatcher release was `f22404093f0a1d23232947a95bfec1e348897c41`.
These components must be advanced independently. A Dashboard package from the
older V2 source checkout must not replace the active Dashboard release.

Read-only inspection of OCTOMINER1 confirmed:

| Service | Unit / endpoint | Observed state | Safe current operation |
| --- | --- | --- | --- |
| ComfyUI | `riverview-comfyui.service`, `192.168.1.160:8188` | Running, version 0.9.2; `/queue` had 0 running and 0 pending | Read `/system_stats` and queue counts only |
| Grace 30B vision | `grace-vision.service`, `192.168.1.160:18080` | Unit loaded but inactive; HTTP health endpoints unreachable | No launch or stop operation performed |

ComfyUI reports its own CUDA device namespace as CUDA index 0, RTX 4090. At
inspection it reported 25,386,352,640 total VRAM bytes and 17,481,695,182 free.
The host `nvidia-smi` index is different; the display therefore labels the
index as ComfyUI's CUDA index and does not infer a physical bay mapping.

The V2 Hardware & AI readout added in this increment calls the existing
authenticated Dashboard telemetry projection. It displays endpoint response,
version, queue counts, reported device/VRAM and observation time. Queue items,
prompt IDs and prompt content are never projected. Unreachable or malformed
responses remain explicitly unavailable. This is status visibility, not a
systemd assertion and not a control interface.

## Recovered controls and boundary

The 30B launch unit resolves to `/usr/local/bin/grace-vision-fast`. Its existing
command binds the Qwen3-VL-30B-A3B GGUF and mmproj files, pins the configured GPU
UUID, uses all model layers, and listens on port 18080. The deployed ComfyUI
unit invokes its existing virtualenv and `/mnt/model-storage/riverview-comfyui`
working tree on port 8188. Systemd start/stop of these units is the existing
operational mechanism. No start/stop command was run.

The Dashboard's current telemetry SSH identity is read-only and permits
inspection, not unit control. No narrow authenticated control executor was
found in the deployed release, systemd unit, current deployment scripts, or
searched shell-history command lines. The existing Dashboard service runs with
`NoNewPrivileges` and a restricted filesystem. A control API would therefore
need a deliberately scoped remote executor and canonical Steward capability;
using the existing telemetry identity or broad root SSH would bypass that
boundary. No executor, grant or capability was added. Switching remains
blocked until such an authorized narrow executor exists. Any future switch
must refuse while active inference requests exist, stop only the conflicting
unit, verify VRAM release, and then start and verify the requested unit.

## Delegation approval API recovery

The active Dashboard release implements the existing Steward-only route
`POST /api/v1/steward/delegation-grant-requests/{request_id}/decision`. It
requires a signed-in `steward` account linked to `steward:camrui`, CSRF
protection, decision, expected request SHA-256 and idempotency key, and calls
the canonical Comms5 authority operation. Its response maps authorization,
identity conflict and registry-unavailable failures without replacing the
authority mechanism.

The corresponding read/list endpoint needed to discover pending requests and
obtain their expected request hash is absent from the active browser-facing
API. The registry implementation inspected also has no request-list operation
and no browser-facing revoke route. The already-approved request must not be
replayed. A V2 approval UI is consequently not safely implementable against
the currently exposed read contract; adding a UI with fabricated hashes or
calling the internal attested Comms5 route would be unsafe. The minimal next
backend increment is an authorized, read-only pending/active/history projection
and an existing-authority revoke adapter, with the same Steward session/CSRF
contract and no new grant store.

## NTFY rich message support

The existing publisher now supports fixed event titles/priorities and an
optional validated HTTPS Dashboard link. A notification click or `Open in
Riverview` view action navigates to the existing authenticated Communications
or Work view with a stable notification/assignment reference. Opening that
view does not write a receipt. This extends the existing NTFY transport and
does not introduce a second delivery mechanism.

Protected attachment delivery is not enabled. The current event projection
does not provide an authorized attachment URL or a protected attachment
retrieval contract usable by the ntfy client. An ordinary filesystem path or
unauthenticated local attachment URL would expose private material. The
publisher therefore sends no images/files until an existing authorized artifact
URL contract can be used without changing the subscription or authentication
model. Phone receipt is not inferred from NTFY HTTP acceptance.

## Codex capacity gauge search

The original Codex gauge producer was not recovered. The search covered:

- all available Git history and refs in the active Riverview checkout, including
  tracked filenames and content searches for `five-hour`, `Codex fuel`, fuel
  gauge, weekly capacity/usage, and related capacity terms;
- the original `ppow1/Riverview` repository checkout available for inspection;
- the historical archive inventory and manifests;
- repository backup files available on Camrui.

No original producer, API, or stored five-hour/weekly subscription-capacity
measurements were found. Existing Codex execution token budgets and OpenAI API
billing are not the same data source and are not substitutes. No percentage or
reset time is displayed. A verified replacement requires an authorized source
that exposes the Codex subscription's five-hour and weekly windows, remaining
capacity, reset timestamps and reading time.

## Tests and unresolved acceptance

Focused local tests cover ComfyUI schema projection and redaction, unavailable
source behavior, NTFY Click/Actions formatting and URL validation, V2 deep-link
navigation, and the existing notification dispatcher contract. The full test
run's PostgreSQL-backed notification cases are skipped where the isolated
database is unavailable. Authenticated live browser acceptance must be run
against the installed release; source-level and endpoint-level tests do not
establish that an iPhone displayed or sounded a notification.
