# OCTOMINER1 GPU workload controls

<!-- Revision: 1.0.0 -->

The Hardware & AI controls address only `grace-vision.service` and
`riverview-comfyui.service` on OCTOMINER1 (`192.168.1.160`). The 30B vision
server and ComfyUI are verified against their existing service configuration
to share the same RTX 4090. Host GPU indices and ComfyUI's CUDA index are not
used as service selectors.

## API and authority

- `GET /api/v1/hardware/workloads` — current unit state, queue/request counts,
  target GPU memory, active control job, and exact capability availability.
- `GET /api/v1/hardware/workloads/jobs/{uuid}` — sanitized state of a submitted
  operation.
- `POST /api/v1/hardware/workloads/start|stop|switch` with
  `{"service":"vision"}` or `{"service":"comfyui"}`.

These routes require a signed-in Steward account bound to `steward:camrui`, the
existing CSRF/session checks, and the canonical exact grant for the selected
operation at `host:octominer1`. The four declarations are shipped with the
dashboard and appear in dynamic Permissions discovery. They do not issue
grants. Discovery or the visible controls do not grant execution authority.

## Transition safeguards

The host accepts only fixed operation names and service units through a
forced-command SSH key restricted to Camrui. It checks the relevant inference
slots or ComfyUI queue and refuses if that view is unavailable or busy. It also
refuses when another process owns the target GPU. A switch waits for systemd's
exact inactive state, verifies the unit cgroup is empty and target GPU memory
has fallen to at most 1 GiB, then starts the requested unit and polls its
existing HTTP readiness endpoints. No arbitrary command, unit, host, GPU, or
endpoint can be supplied by an API caller. Each accepted job transition is
recorded in the host's protected JSONL audit file.

The controller status read is safe for production observation. Do not use
start, stop, or switch actions for acceptance; production workload transitions
require a separate explicit Steward authorization. If active-request or GPU
ownership data is unavailable, the operation fails closed.

## Host installation and rollback

The host program is `scripts/rv_gpu_workload_control.py`, installed as
`/usr/local/sbin/riverview-gpu-workload-control`. Its pinned SSH identity and
forced-command key are provisioned on Camrui/OCTOMINER1, outside source control.
Keep its key, host pin, `authorized_keys` restriction, and audit directory
separate from the Dashboard package. Do not broaden that SSH key to a shell.

To roll back the Dashboard integration, restore the previous immutable
Dashboard and V2 releases using the standard dashboard rollback record, then
remove only the forced-command key by its `rv-gpu-workload-control-*` comment,
restore the saved host program, and remove the service-account traversal ACL
only if no other deployment now depends on it. Do not restore a whole
`authorized_keys` snapshot over keys added after the backup. Preserve the host
audit file during rollback.
