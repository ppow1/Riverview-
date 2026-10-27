<!-- Riverview Controlled Document
File: docs/operations/CHATGPT_GITHUB_CONNECTOR_ISSUE_LOG.md
File Revision: 1.0.0
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

## Active punch list
- P1: Reconcile Comms5 direct Codex operation registration and ChatGPT tool schema.
- P1: Validate native GitHub issue and contents/object write alternatives, with read-back and no duplicate writes.
- P1: Prove ChatGPT → governed Codex worker → durable objective status → result.
- P2: Commission Camrui asynchronous Linux commands with exact host-scoped grants.
- P2: Expose and test Comms5 command_task_cancel in ChatGPT.
- P2: Publish async Gateway runbook and validate its provenance.
- P3: Document Windows service-account drive visibility and supported checkout locations.
- P3: Longer-running job, cancellation and recovery acceptance.

## Reporting template
ID | date | tool/path | intended action | error/result | server receipt | fallback | read-back verification | status.

Do not log tokens, SSH private keys, command secrets, or sensitive output.
