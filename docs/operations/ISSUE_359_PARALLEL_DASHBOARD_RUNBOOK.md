<!-- RIVERVIEW~ CONTROLLED DOCUMENT
File: docs/operations/ISSUE_359_PARALLEL_DASHBOARD_RUNBOOK.md
Component: STEWARD-DASHBOARD
File Revision: 1.0.0
Purpose: Prepare a parallel Dashboard release without disturbing the original authority transaction
Authority: Staging only until the Issue #359 authorization gates below pass
Changed: 2026-10-27 UTC | RV-ISSUE-359-PARALLEL-DASHBOARD | Document inactive release staging, isolated service credentials, and gated Comms5 activation.
Contracts: docs/components/STATUS_DASHBOARD_COOKBOOK.md
Tests: tests/test_parallel_dashboard_service.py
History: Git and revision backup manifest
-->
# Issue #359 parallel Dashboard runbook

## CURRENT STATUS — 2026-10-27 14:54 EDT (supersedes historical staging gates below)

This document originally described an inactive parallel deployment. **Those historical preparation/activation steps are no longer applicable to Issue #359's current environment.** The Steward explicitly authorized discarding the disposable, stranded test transaction; the Dashboard was cleanly stopped and the old backend disconnected. Do not follow the old instructions below to preserve PID 390251 / backend 390316 or start a parallel Dashboard on port 8770.

- Active corrected Dashboard release: `1ae512d92d6ca8749566355930308e731bdd2405` (PR #361, per-thread PostgreSQL connections, commit-before-success). Deployment reported active PID 656705. Database/config backups were verified.
- Follow-up approval route correction deployed as `8325d3ffe8e53f3deaab4c9e14e471467454a08b`: URL-encoded `%3A` request-ID delimiter is normalized; 21 focused route tests passed. The earlier `405 read_only_method` is resolved.
- The authenticated Steward approved the **existing** two requests through the V2 browser console on 2026-10-27 ~14:53 EDT. Connected Comms5 independently returned both grants ACTIVE, correct actions and `host:camrui` scope:
  - Caller: `grant:54dafa24f70d4ee296b737e867091884` (`steward:camrui`, `comms5.command.submit.task.camrui.standard`, unlimited uses), expires 16:53:06 EDT.
  - Executor: `grant:06dad5aa461d46fd9af4924a73f4e0a5` (`service:command-gateway`, `comms5.command.execute.task.camrui.standard`, 20 uses), expires 16:53:07 EDT.
- **Live ChatGPT Comms5 command submission works**: standard Camrui command `hostname; id -un; pwd` accepted, execution `56f6b895-a6cc-4637-b2ac-16f0c42af095`, exact grants recognized, reservation consumed, audit recorded. Durable status returned FAILED, exit 255, stderr `ssh: Could not resolve hostname camrui: No such host is known.` Final audit event `97494068-6d56-451a-8fac-8f6b00bb371f`. See Issue #359 comment 6450854186.
- **Remaining acceptance blocker:** Command Gateway's SSH target name `camrui` does not resolve in its actual execution environment. Verify the registered host mapping and transport under Gateway service identity. Camrui LAN IP previously documented as `192.168.1.155`; verify before use. Do not change grants or database authorization to address SSH resolution. Test the same harmless command and retrieve durable status; require exit 0 and expected hostname/user/output before closing Issue #359.
- ChatGPT's current Riverview Comms 1.1 interface exposes callable `comms5_command_task_submit` and `comms5_command_task_status`; another C2 session's tool catalog may differ. A Comms5 transport probe verifies the adapter path, **not** SSH host execution.

### Immediate next steps

1. Inspect and fix only the Command Gateway SSH target configuration / host resolution for `camrui`, including where the gateway actually runs. Avoid assuming the Camrui local shell and Gateway process share SSH configuration.
2. Run a bounded harmless command through Comms5, then retrieve durable status and audit evidence. Check grants have not expired.
3. Record result in Issue #359 and close only on successful end-to-end execution.

---

### Historical parallel deployment plan (superseded; retained for audit)

## Scope and invariants

This candidate uses the corrected per-thread AuthorityRegistry and a separate
loopback listener. It must not replace or restart
`riverview-status-dashboard.service`, change `/opt/riverview-status-dashboard/current`,
or touch the original PostgreSQL backend. The existing Comms5 route remains on
the current Dashboard until authorization checks pass.

The parallel process receives separate systemd credentials and writes its
libpq passfile only to `/run/riverview-status-dashboard-parallel/pgpass`. It
uses the canonical `riverview_authority` Registry and the existing protected
credential sources. It does not enable the optional Grace model router, so it
does not start a second deferred-conversation worker.

## Candidate configuration

The unit definition is `deploy/riverview-status-dashboard-parallel.service`.
It binds to `127.0.0.1:8770`, uses a distinct database `application_name`, and
loads only the credentials required for Dashboard authentication, authority
decisions, and the existing Command Gateway agent. The launcher validates the
unit-specific systemd credential directory before copying `pgpass` into the
unit's private runtime directory.

The candidate release is referenced through the separate
`/opt/riverview-status-dashboard/parallel-current` link. The existing
`current` link remains unchanged. The active Comms5 adapter reads
`RIVERVIEW_COMMS5_DASHBOARD_URL`; its current value remains
`http://127.0.0.1:8767` until all authorization gates below pass.

## Prepare and stage

1. Merge the reviewed PR and build from the exact integrated commit in a clean
   checkout:

   ```sh
   python3 scripts/build_camrui_package.py /var/tmp/riverview-dashboard-issue359.tar.gz
   python3 scripts/verify_camrui_package.py /var/tmp/riverview-dashboard-issue359.tar.gz
   ```

   Record the source commit and archive SHA-256. The verifier must report a
   matching package manifest and compatible shell files.

2. Extract into a new root-owned immutable directory
   `/opt/riverview-status-dashboard/releases/<source-commit>`. Validate
   `SOURCE_COMMIT` and `PACKAGE_SHA256SUMS`; set root ownership and remove
   group/other write access. Do not overwrite an existing release.

3. Create the distinct `parallel-current` link to that exact release, stage
   `deploy/riverview-status-dashboard-parallel.service` for review, and run
   `systemd-analyze verify` against the staged unit. Do not install or start
   the unit before the authorization gates pass. Do not change the existing
   `current` link, existing unit/drop-ins, Nginx route, or Comms5 adapter.

## Authorization and activation gates

Before starting the parallel service or routing Comms5 to it:

1. Verify that the original transaction has been safely resolved through its
   owning Dashboard connection. Confirm both original request hashes, grant
   IDs, Steward decisions, and institutional audit events from a fresh
   PostgreSQL connection. Never commit through a separate session.
2. Confirm the caller and executor grants are visible as active through the
   exact AuthorityRegistry authorization functions, scoped to `host:camrui`
   and the required standard Comms5 actions. Check expiration against current
   time. Do not extend a grant automatically. Do not issue a duplicate request
   or grant while an original remains unresolved.
3. Confirm the active Dashboard PID and original PostgreSQL backend are still
   present. Start only `riverview-status-dashboard-parallel.service`; verify
   its source commit, deployment identity, loopback health, database access,
   and that the current Dashboard PID/backend remain unchanged.
4. Before routing, repeat the fresh-connection exact caller and executor
   checks. If either denies, is unavailable, or is expired, do not route
   Comms5 and do not submit a command.
5. Only after successful health and authorization checks, set
   `RIVERVIEW_COMMS5_DASHBOARD_URL=http://127.0.0.1:8770` in a dedicated
   drop-in for `riverview-comms5-camrui.service`, run `systemctl daemon-reload`,
   and restart only that Comms5 adapter. Leave the existing Dashboard and its
   transaction untouched. The Nginx website route continues using port 8767.

## Acceptance evidence

Through the ChatGPT Comms5 interface, submit one harmless standard Camrui
command. Record the task/execution ID, exact grant IDs and authorization
evidence, audit event ID, completion status, exit code, and returned hostname.
Then retrieve status through Comms5 and confirm the result is durable. Do not
claim acceptance from a local HTTP probe or an authorization status response.

If any authorization or health check fails before Comms5 routing changes, leave
the candidate staged and the existing service path untouched. This runbook does
not authorize grant creation, grant extension, transaction rollback, backend
termination, or Dashboard restart.
