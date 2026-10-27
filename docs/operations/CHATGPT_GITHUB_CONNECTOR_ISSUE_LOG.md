<!-- Riverview Controlled Document
File: docs/operations/CHATGPT_GITHUB_CONNECTOR_ISSUE_LOG.md
File Revision: 1.0.4
Changed: 2026-10-27
-->
# ChatGPT ↔ GitHub connector issue log

Purpose: retain reproducible failures and successes across GitHub connector operations, rather than concluding GitHub is unwritable after one failed call. This is a diagnostic record, not authorization to bypass controls.

## Write-path matrix
- GitHub native create_issue / update_issue / add_comment_to_issue.
- GitHub native create_file / update_file (contents API).
- GitHub native create_branch + create_tree + create_commit (Git objects API); inspect the exact available tool contracts before use.
- GitHub via existing authorized Codex repository workflow.
- GitHub via existing Windows/Camrui Git CLI only when the execution identity has established authorization and repository access.

For each failure record date/time, tool, input category (never secrets), exact error, whether GitHub itself received a request, retry/fallback, resulting commit/issue URL, and whether read-back confirmed persistence. Never assume a write failed solely because the tool response failed; check for duplicates before retry.

## Observations

### GH-CONN-001 — GitHub issue creation blocked
- Date: 2026-10-27.
- Tool: mcp__GitHub__create_issue.
- Request: create issue in PPOW1/Riverview- for Comms5/Codex connector mismatch.
- Result: 'This tool call was blocked by OpenAI's safety checks. Please double check what you are sending.'
- GitHub write receipt: none. Cannot determine from that error alone whether GitHub was contacted.
- Follow-up: inspect other native GitHub write methods and read-back; do not assume all writes are blocked.

### GH-CONN-002 — Comms5 tool catalog mismatch (separate from GitHub)
- Date: 2026-10-27.
- ChatGPT connector: 41 callable Riverview Comms 1.1 tools.
- Live Comms5 capabilities: 35 advertised operations; catalogs serve different purposes, so equal totals are not required.
- Direct Engineering tool is callable in connector, absent from live capabilities; describe_operation('submit_direct_engineering_task') returned RIV-COMMS5-0004 unknown.
- Live server advertises command_task_cancel, but callable connector lacks it.
- Next: reconcile exact operation contracts and verify end-to-end; don't build a duplicate dispatcher.

### GH-CONN-003 — Windows Gateway service account checkout visibility
- Date: 2026-10-27.
- Async PowerShell Get-ChildItem A:\Riverview-New-Core\docs\operations failed path-not-found under RiverviewCmdAgent; not evidence that the interactive user's A: checkout is missing.
- Next: inspect service-account-visible local paths without copying keys or weakening ACLs.

### GH-CONN-004 — Native issue creation succeeds on retry with bounded body
- Date: 2026-10-27.
- Tool: mcp__GitHub__create_issue.
- Result: created [issue #359](https://github.com/ppow1/Riverview-/issues/359) using concise scoped body, after earlier safety rejection of a longer request.
- Interpretation: failure was not a blanket prohibition on GitHub issue writes; precise cause of earlier safety rejection remains unknown.
- Follow-up: compare request shape and length, record exact error and read-back; do not claim a definitive cause.

### GH-CONN-005 — Windows Comms5 tool-level filtering: reproducible capability audit
- Date: 2026-10-27 ~16:05 EDT. Host: desktop-ja3rpnq; tool: comms5_command_task_submit; same active Windows standard grants.
- Earlier read-only Windows service inventory calls (one detailed Gateway inventory, one minimal Get-Service query) were rejected with exact message `This tool call was blocked by OpenAI's safety checks. Please double check what you are sending.` No execution ID or Gateway receipt returned; specific filtering rationale not exposed.
- Subsequent baseline commands all executed on Windows and returned exit 0, with durable execution/audit IDs: `Write-Output 'RV_AUDIT_OK'` (d2808f96-f5f4-4013-a1a8-983f1f2fa5ae), `Get-Date -Format o` (6fe8c13c-8f96-40a0-a977-5a9017f12246), `$PSVersionTable.PSVersion.ToString()` (a294565e-f690-41a5-bfc8-cc348beba631). PowerShell version 5.1.26100.9596.
- Interpretation: Windows transport and grants are operational; tool filtering is selective or variable. Do not infer a blanket inability to execute Windows commands, or claim the blocked requests reached Riverview. These observations do not establish an exhaustive allow/deny list or explain OpenAI filtering internals.
- Follow-up: maintain a small, bounded capability matrix for legitimate read-only inventory, repo operations, session management, and approved deployment steps; log exact command class, tool outcome, execution ID when present, date, host, and outcome. Avoid high-volume boundary probing or attempts to evade filtering. Favor dedicated typed Comms5 operations for persistent Codex sessions rather than relying on arbitrary shell command text.

## Active punch list
- P1: Establish and maintain a reproducible Comms5 Windows/Linux capability acceptance matrix with preflight checks and explicit tool-filter vs Gateway vs host failure classification.
- P1: Reconcile Comms5 direct Codex operation registration and ChatGPT tool schema.
- P1: Validate native GitHub issue and contents/object write alternatives, with read-back and no duplicate writes.
- P1: Prove ChatGPT → governed Codex worker → durable objective status → result.
- P1 [GRACE-AUTONOMY-CODEX-LOCAL-E2E, DEFERRED]: Test the dedicated Comms5 `submit_direct_engineering_task` path end-to-end, specifically verifying whether it dispatches to and controls an existing Codex worker/session on Windows development host `desktop-ja3rpnq` (not the Command Gateway shell path). Previous objective `objective:5e29a3bb-f322-53d8-bebd-0acce2a25700` reached PROPOSED with no assignment, dispatch_count=0, or verified Codex execution. Acceptance: worker identity and host evidenced; assignment created; Codex executes bounded task; durable status, artifact, verification, and result returned. Preserve existing dispatcher; no new test now.
- P1 [CODEX-DUAL-HOST-CONTROL]: Establish dedicated Codex start/attach/submit/status/result capability through Comms5 for both Camrui and Windows dev machine, with explicit host/session identity and their distinct resource access. Do not confuse with `command_task_submit` shell access or assume existing direct Engineering dispatcher supports host selection. Validate each host separately; use existing workers/sessions where possible. Camrui SSH hostname resolution remains separately tracked in Issue #359.
- P2: Commission Camrui asynchronous Linux commands with exact host-scoped grants.
- P2: Expose and test Comms5 command_task_cancel in ChatGPT.
- P2: Publish async Gateway runbook and validate its provenance.
- P3: Document Windows service-account drive visibility and supported checkout locations.
- P3: Longer-running job, cancellation and recovery acceptance.

## Reporting template
ID | date | tool/path | intended action | error/result | server receipt | fallback | read-back verification | status.

Do not log tokens, SSH private keys, command secrets, or sensitive output.

- P2 `[GRACE-AUTONOMY-LOCAL-SCRIPT-RUNNER, DEFERRED]`: Build a versioned library of user-approved, preinstalled PowerShell/Bash scripts on the Windows development machine and Camrui, callable from ChatGPT/Grace via existing authorized Comms5 command execution or a narrow typed operation (e.g., script ID + validated parameters). Preserve host-specific resource access, explicit user authorization, allowlisting, audit trails, result/status retrieval, and local execution permissions. Goal: reliably trigger previously authorized local operations without repeatedly transmitting complex shell command bodies. This is NOT an authorization bypass; tool/platform restrictions still apply. Do not interrupt the current Issue #359 dual-host Codex session-control work to implement this.

- P2 `[COMMS5-CROSS-CONVERSATION-GRANT-RESOLUTION, DEFERRED]`: An authorized ChatGPT conversation can lack the exact active execution grant ID required by `comms5_command_task_submit`, although grants persist in Riverview independently of chat context. Add an authenticated, scoped grant-resolution/discovery path (or backend binding) for host, operation, privilege, principal, expiration, and remaining uses; do not require users to transfer IDs across chats. Preserve backend authorization and audit. Acceptance: two separate authorized conversations can execute the same eligible operation without manually sharing grant IDs, while invalid/expired/out-of-scope grants fail. Related: Issue #359 caller authorization binding. Do not interrupt current Codex dual-host commissioning.
