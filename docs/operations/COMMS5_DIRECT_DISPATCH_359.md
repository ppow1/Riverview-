<!-- Riverview Controlled Document
File: docs/operations/COMMS5_DIRECT_DISPATCH_359.md
Component: COMMS5-CAMRUI-ADAPTER
File Revision: 1.0.0
Changed: 2026-10-27 UTC | RV-COMMS5-DISPATCH-359
-->
# Direct Engineering dispatch: Issue #359

## Scope and confirmed cause

The connector lists `comms5_submit_direct_engineering_task`, but the static
catalog omits it from capabilities, help operations, descriptions and examples.
`Comms5Application.handle` resolves descriptions from `read_only_payloads`,
so the missing `describe:submit_direct_engineering_task` entry produces
`RIV-COMMS5-0004` even when the authenticated backend supports submission.
This change synchronizes those discovery surfaces without changing the callable
schema, router, grants, dispatcher, worker selection, or execution lifecycle.
The existing process graph is unchanged because no execution transition changes.

The integration source is on `codex/command-gateway-20261026`, verified at
`9f08b46d40bb8edfd7ea40f7ad65aa355af4971f`, the PR #358 merge. Default `main`
does not contain the Comms5 implementation at these paths. Deployment identity
and the active Camrui checkout have not yet been inspected in this session.

## Actual acceptance evidence

Through Riverview Comms 1.1 on October 27 at 11:07 EDT, one real bounded
documentation task was submitted using stable idempotency key
`issue359-workmode-doc-acceptance-20261027-01`. The server returned `executed:true`
and objective `objective:5e29a3bb-f322-53d8-bebd-0acce2a25700`.
The requested output is `docs/engineering/COMMS5_DIRECT_DISPATCH_ACCEPTANCE_359.md`;
`tests/test_comms5_mcp.py` is included only as an unchanged validation target.

Subsequent authenticated status reads show `PROPOSED`, revision 3, verified
grounding with seven references, and the recorded direct-dispatch event.
No assignment, worker execution, verification, or result artifact exists in that
projection. Do not equate the intake receipt with an executed Codex task.
CME reports healthy; that does not establish Grace execution readiness.

Source inspection shows `GraceExecutionService.dispatch_proposed` can skip a
source-change plan if the configured capability or repository validator does
not match. This is a diagnostic lead, not the confirmed cause of this live wait.
Inspect the actual worker configuration and service state before changing them.

## Focused development validation

Environment: ChatGPT Work Linux source snapshot of the named integration commit.
The new regression initially fails with `StopIteration` on the absent discovery
entry. After correction it passes. Existing standard-library unittest execution
runs 22 adapter tests successfully, including HTTP/authentication tests and the
new discovery/authenticated-route regression. One historical-catalog test is
omitted because its external-reasoning dependencies are not in this bounded
snapshot. This is not a full-repository or production test claim. `pytest` is
unavailable in this runtime; the first attempted pytest invocation failed before
collecting tests. `git diff --check` passes.

Reproduce the focused adapter tests in a complete checkout with:

```sh
PYTHONPATH=src:tests python -m unittest test_comms5_mcp
```

The full command above includes the omitted test and has not been run here.
The regression can be run independently with
`PYTHONPATH=src:tests python -m unittest test_comms5_mcp.Comms5MCPTests.test_direct_dispatch_discovery_and_authenticated_route_agree`.
It verifies discovery never dispatches work, documented required fields agree
with the schema, an authenticated backend receives the example, and provider
identity plus caller-selected worker input are rejected. Backend execution in
that unit test is simulated; the real intake evidence is separate above.

## Resume, diagnostics and rollback

Poll `comms5_objective_status` with the exact objective ID. Preserve this lineage;
do not submit a second acceptance objective just to retry. On authorized Camrui
access, identify the active checkout/release, Grace service state, configured
source-change worker, repository identity, pinned base and allowed path ceiling.
Inspect only non-secret configuration and diagnostics. Preserve the configured
security boundaries and resolve the actual mismatch through the existing worker.

Camrui grant-request service now accepts the bounded requests, unlike the prior
`BACKEND_UNAVAILABLE` observation. Two requests remain pending separate approval:

| Request | Grantee/action | Limit |
| --- | --- | --- |
| `delegation-request:0ee90c1d38ac42159be57ab416057f8f` | `steward:camrui` / `comms5.command.submit.task.camrui.standard` | `host:camrui`, two hours after activation |
| `delegation-request:4e9457068b0047eb903a5bea383c488d` | `service:command-gateway` / `comms5.command.execute.task.camrui.standard` | `host:camrui`, two hours, at most 20 executions |

The scope is standard-user Camrui execution for Issue #359. No authority is
activated by requesting it. OS elevation or service deployment may require a
separate existing authorization boundary after live inspection; do not assume
these standard grants permit privileged changes. Approval belongs to the
authenticated Steward grant-control path, not an ordinary Comms5 submission.

After authorized catalog deployment, read capabilities, help, description and
examples through the real connector, then finish assignment/execution/artifact/
independent-verification acceptance through the existing Grace/CME path.
Report direct ChatGPT intake separately from Grace reasoning and completion.

Exact predecessor bytes and SHA-256 are retained under
`.riverview-backups/RV-COMMS5-DISPATCH-359/`; verify hashes in its manifest before
copying predecessors to their original paths. Before deployment also preserve
the deployed predecessor and release pointer on the host. No production change
has been performed in this session. The mission remains incomplete until the
real acceptance task executes and returns verified results.
