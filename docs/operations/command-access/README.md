<!-- Document Revision: 1.0.0 -->

# ChatGPT ↔ Riverview Command Access — commissioning record v0.1

> **PROVISIONAL, 2026-10-26.** This records the working Windows path and the commissioning chronology. Facts labeled *reported* came from Windows/Camrui Codex and require source/configuration reconciliation. Do not store bearer values, private keys, or credentials in Git. This is **not yet a complete reproducible installation manual**. See [verification punch list](PUNCH_LIST.md).

## Navigation and operating baseline

**Verified live from ChatGPT Comms5:** `ChatGPT → Comms5 → Riverview Dashboard on Camrui → authenticated Windows agent → standard PowerShell → response/audit`.

- Windows host: `DESKTOP-JA3RPNQ`, LAN `192.168.1.88`, agent HTTPS port `8443`.
- Camrui: `192.168.1.155`; Steward Dashboard `https://192.168.1.155/`.
- Windows execution account: `desktop-ja3rpnq\riverviewcmdagent` (standard, not elevated).
- Windows agent scheduled task: `Riverview Command Gateway Agent`; executable `C:\WINDOWS\system32\cmd.exe`; arguments `/d /c ""C:\Program Files\Riverview\CommandGateway\scripts\start_windows_command_agent.cmd""`; working directory `C:\Program Files\Riverview\CommandGateway`.
- Agent Python process observed: `C:\Users\wille\AppData\Local\Programs\Python\Python312\python.exe -u "C:\Program Files\Riverview\CommandGateway\scripts\run_windows_command_agent.py"`.
- Windows agent module reported at `C:\Program Files\Riverview\CommandGateway\...` with installed `command_gateway.py` SHA-256 `B615B77F8313C30779D5ED03CD8353F380F3A86D4B62C9E488B36C999578D2EE` (exact module path to verify). Prior module backup `command_gateway.py.pre-ad764f1.bak`.
- Windows firewall: port 8443 restricted to Camrui (reported). Windows agent TLS cert issued by Riverview LAN Root CA; chain and `desktop-ja3rpnq` hostname verified. Root CA on Camrui: `/etc/riverview/command-gateway/agent-ca.pem`.
- Agent bearer installed on Camrui: `/etc/riverview/command-gateway/agent.token`, `root:root`, mode `0400`; transferred once over existing strict-host-key SSH alias from Windows via staging file `/tmp/command-gateway-agent.token.incoming`, then staged copy removed after installation (removal to verify).
- Service principal `service:command-gateway` registered through authenticated Steward POST `/api/v1/steward/service-principals/command-gateway/register`, JSON `{"confirmation":"REGISTER service:command-gateway"}`; HTTP 201 and credential_stored true. Protected credential: `/var/lib/riverview-status-dashboard/identity-credentials/service-command-gateway.credential`, owner `riverview:riverview`, mode `0400`.
- Dashboard systemd credential drop-in installed; `riverview-status-dashboard.service` restarted and authenticated agent GET returned HTTP 200. Exact drop-in file and environment key mapping to verify.
- Windows dedicated SSH identity public-key fingerprint `SHA256:mqhE3Ax4u/FDvAQlVZzw9Hs5TMO+aDtUYPdiEJqMUPo`; Camrui SSH host fingerprint `SHA256:dtKs11Qd1CyyH5nQ9z3GCB0k5XSPcYPO0OvmIoQ78mU` (Windows Codex reported). These are **not** the Windows agent HTTPS certificate fingerprint.

## Comms5 tool registration and refresh

Original conversation exposed 39 MCP tools; updated connector advertises 41, including `comms5_command_task_submit` and `comms5_command_task_status`. Older `comms5_command_submit/status` were fixed-operation probes, not general command execution. Fresh ChatGPT session initially refreshed schema; later this session also showed all 41. `comms5_capabilities` operation count is **not** MCP tool count. Tool registration, schema publication, OAuth verified caller attestation, and client schema-refresh mechanics require source verification.

Task submit parameters: `host_id`, task-specific `command`, `privilege_level`, `execution_grant_id`, `idempotency_key`. Windows standard is operational; Windows elevated unsupported. The live behavior recorded above had a 12-second synchronous limit. [PR #358](https://github.com/ppow1/Riverview-/pull/358) implements a separate asynchronous backend: it waits up to 2 seconds for fast results, then returns queued/running task IDs for status polling; the task deadline defaults to one hour (configurable up to 24 hours). It retains the 32 KiB per-stream output limit and 8,000-byte command bound, stores the command digest rather than command text, supports caller-authorized cancellation, and marks unfinished tasks interrupted on agent restart rather than replaying them. This code is not merged or deployed; C1's route restoration in #356 and a live >12-second acceptance remain outstanding.

## AuthorityRegistry and website Steward approvals

Authenticated OAuth steward is mapped by Dashboard to `steward:camrui` for command authorization. Executor is registered `service:command-gateway`. The two **separate host-scoped** grants use `policy:delegation.v1`, scope `host:desktop-ja3rpnq`, unlimited successful uses and a seven-day duration measured at approval:

| Function | Principal | Action | Request ID | Request SHA-256 | Grant ID |
| --- | --- | --- | --- | --- | --- |
| Submit | `steward:camrui` | `comms5.command.submit.task.desktop-ja3rpnq.standard` | `delegation-request:b17e212a49bc405090a6151b0631a5c1` | `27ef4abe6e6deaf174eb39887408ea1240cce1681a919880f72c28372966a5f1` | `grant:bc790c0beb1746b295aade230d4a56cf` |
| Execute | `service:command-gateway` | `comms5.command.execute.task.desktop-ja3rpnq.standard` | `delegation-request:7a7a42a08f544bd68c5a609ff9f2d59b` | `509949605b63067ba4fe1b3a55b4e60a56e3e769dc0a49241a56d251471770f4` | `grant:2c4cd34bcc484a61814f6f489f25c8f1` |

Both requests approved 2026-10-26 ~19:55 EDT and confirmed through `comms5_get_delegation_grant_status` as `approved`, `IMPLEMENTED`. These are historical identifiers, **not reusable installation defaults**. Use authenticated Steward website with CSRF and exact request digest for approval: POST `/api/v1/steward/delegation-grant-requests/{literal-request-id}/decision`; body `decision:approve`, `expected_request_sha256`, `idempotency_key`, `approval_ref`. Do not percent-encode the colon in `delegation-request:` for this route (encoded colon produced 405). Grant renewal, extension, revocation and different durations must be independently verified in the canonical registry.

## Chronology: failure → correction

1. Fixed command probes were mistaken for general execution. Added task-specific submit/status tools, deployed Comms5 41-tool catalog; initial combined deployment reported `9698cf5fbf1e24c4021ae2f9d4f2c53c936f43a8`.
2. Windows agent installed with TLS, dedicated `RiverviewCmdAgent`, restricted port 8443, scheduled task. TLS succeeded but anonymous HTTPS 401 did **not** establish authentication.
3. Gateway principal registration route initially blocked by Dashboard global POST allowlist 405. Corrected; Steward owner POST returned 201 registered. Dashboard release reported `d1cb69bc653c184f484070e3db65d3e27c6b3760`.
4. Agent bearer absent on Camrui; attempts via automated SSH stdin were runner-blocked. Normal owner-authorized SSH alias transfer succeeded. C1 installed token, CA and systemd credential drop-in. Authenticated GET returned HTTP 200.
5. Caller and executor grants requested and approved. First ChatGPT command returned `NOT_AUTHORIZED`: not a missing grant, but Dashboard database role `riverview_core` lacked protected AuthorityRegistry reservation table rights. Corrected reservation/release/consume through protected AuthorityRegistry adapter with service credential; release reported `143a5b64e4dfe6ff660f08c6213cd548c9349a1f`. Do **not** widen DB role grants as workaround.
6. POST still failed, originally obscured as 503; diagnostic propagation reported Windows agent HTTP 400 `invalid_command_request`. Dashboard release reported `ad764f1cd709e29db898de878c3d23e29d6e0805`.
7. Windows Codex found older agent strict 8-field validator, while Dashboard sent three additional fields `host_id`, `transport`, `command`. Updated Windows module from deployed Dashboard code; compilation succeeded, prior module backed up.
8. Windows agent restart failed with Security event 4625, status `0xC000015B` (batch logon denied). Owner added `DESKTOP-JA3RPNQ\RiverviewCmdAgent` to **Log on as a batch job** in Local Security Policy after checking **Deny log on as a batch job**. Do not add to Deny. Task Scheduler result `267009` (`0x41301`) means task running, not necessarily failed. Python process later observed. An earlier port check showed no listener; the successful remote command later proves agent was serving requests.
9. **Live ChatGPT acceptance passed.** Submitted `hostname; whoami; $PSVersionTable.PSVersion.ToString()` via `comms5_command_task_submit`. Result `completed`, `executed:true`, exit `0`, stderr empty; stdout `DESKTOP-JA3RPNQ`, `desktop-ja3rpnq\riverviewcmdagent`, `5.1.26100.9596`. Execution ID `d12f2b65-7f15-433d-9332-feb79c7d790c`; audit event `5e313d43-30a6-4df1-a50b-9c221413f368`; executor reservation `consumed`.

**Repository caveat:** Above deployment SHAs are C1-reported, **not yet independently located in connected GitHub default branch**. GitHub repository `PPOW1/Riverview-` has relevant operational issue #343, but GitHub commit lookup for those SHAs returned not found. Reconcile branches, deployment origins and repository visibility before calling them source-verified.

## Desired owner website automation

**Commission a host once; grant access repeatedly in a few clicks.** Website should let Steward select host(s), standard/elevated capability (only if supported), duration (e.g. 1 day, 7 days, 3 months, custom), and use limit (1/N/unlimited), then approve both caller/executor grants using existing AuthorityRegistry. Show active grant pair, exact principal/action/scope, activation/expiry, usage, audit and immediate revoke/extend. Do not regenerate CA, agent credentials or reinstall service for each grant. Separate machine enrollment and transport readiness from temporary access authorization. Reuse existing #343 grant lifecycle rather than new grant architecture. Verify true expiry/revocation on both caller and executor; prevent one-sided grants and partial activation.

## Next phase (not yet commissioned)

Camrui SSH task execution: verify actual agent SSH account, pinned host key and authorized noninteractive identity, host mapping, command handler, Camrui-specific caller/executor grants and sudo boundary for elevated commands. Do not claim operational until ChatGPT submits and receives an actual SSH command. Async execution is implemented for review in #358 but awaits #356 route integration, merge, and live >12-second acceptance. Windows elevated PowerShell remains separate work.

## Documentation evidence and completion

This file is a *publishable historical checkpoint*, not proof every installation detail is reproduced. [PUNCH_LIST.md](PUNCH_LIST.md) tracks missing exact files, code paths, deployment SHAs, tests, recovery, website UI and evidence. Every future correction should update this document and close the matching punch-list entry; do not reconstruct from chat again.
