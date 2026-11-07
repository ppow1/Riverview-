# Registered GPU host workload controls

<!-- Revision: 1.1.0 -->

The Hardware & AI controller resolves eligible hosts from the existing
hardware/service telemetry and the Dashboard's verified controller
registrations. A host is controllable only when both sources identify it as
verified and its registration supplies a pinned controller endpoint, transport
credentials, and an allowlisted service mapping. Hosts without a registered
controller remain visible as unavailable and cannot receive commands.

OCTOMINER1 (`192.168.1.160`) is currently the only registered controller. Its
allowlist contains `grace-vision.service` and `riverview-comfyui.service`,
verified to share the RTX 4090. OCTOMINER2 is not registered or verified; no
unit name, executable, GPU index, or port is inferred for it. Adding a host
requires its own verified controller identity, pinned transport
configuration, service/readiness/job mappings, GPU resource identifiers, and
exact host-scoped capability registrations. This registration update does
not require website code changes.

## API and authority

- `GET /api/v1/hardware/workloads` — per-host unit state, queue/request counts,
  target GPU memory, active control job, and exact capability availability.
- `GET /api/v1/hardware/workloads/jobs/{uuid}` — sanitized state of a submitted
  operation.
- `POST /api/v1/hardware/workloads/start|stop|switch` with a selected
  `host_id` and service ID returned for that host.
- `GET /api/v1/steward/delegation-grant-requests/options` — registered,
  currently available host-scoped permission request options.
- `POST /api/v1/steward/delegation-grant-requests` — submits a pending request
  through the canonical authority registry.

Workload routes require a signed-in Steward account bound to
`steward:camrui`, the existing CSRF/session checks, and the canonical exact
grant for the selected operation at `host:<selected-host-id>`. The four
operation declarations are host-neutral and appear in dynamic Permissions
discovery. Delegation requests are self-targeted and remain pending until
explicit review and approval. Requesting or discovering a capability does not
grant execution authority.

## Transition safeguards

Each registered host accepts only fixed operation names and service units
through its own forced-command SSH identity restricted to Camrui. The
controller checks the relevant inference slots or ComfyUI queue and refuses if
that view is unavailable or busy. It also refuses when another process owns a
target GPU. A switch waits for systemd's exact inactive state, verifies the
unit cgroup is empty and target GPU memory has fallen to at most 1 GiB, then
starts the requested unit and polls its registered HTTP readiness endpoints.
A request may select only a verified, registered host and a service allowlisted
for that host. No arbitrary command, unit, GPU, or endpoint can be supplied by
an API caller. Conflict checks are local to the selected host's GPU resources;
a request for one host cannot stop services on another. Accepted transitions
are recorded in that host's protected JSONL audit file.

The controller status read is safe for production observation. Do not use
start, stop, or switch actions for acceptance; production workload transitions
require a separate explicit Steward authorization. If active-request or GPU
ownership data is unavailable, the operation fails closed.

## Host installation and rollback

The host program is `scripts/rv_gpu_workload_control.py`, installed as
`/usr/local/sbin/riverview-gpu-workload-control`. Each host's pinned SSH
identity and forced-command key are provisioned on Camrui and the registered
GPU host, outside source control. Keep keys, host pins, `authorized_keys`
restrictions, and audit directories separate from the Dashboard package. Do
not broaden the SSH key to a shell.

To roll back the Dashboard integration, restore the previous immutable
Dashboard and V2 releases using the standard dashboard rollback record, then
remove only the relevant forced-command key by its
`rv-gpu-workload-control-*` comment, restore the saved host program, and remove
the service-account traversal ACL only if no other deployment now depends on
it. Do not restore a whole `authorized_keys` snapshot over keys added after the
backup. Preserve host audit files during rollback.
