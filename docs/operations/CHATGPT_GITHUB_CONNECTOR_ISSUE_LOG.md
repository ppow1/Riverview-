<!-- Riverview Controlled Document
File: docs/operations/CHATGPT_GITHUB_CONNECTOR_ISSUE_LOG.md
File Revision: 1.0.2
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


### GH-CONN-005 — Work continuation: discovery failure is not dispatch failure
- Date: 2026-10-27; task RV-COMMS5-DISPATCH-359; Issue #359.
- Native GitHub add_comment_to_issue succeeded and returned comment 6445569337.
- Real Comms5 submit_direct_engineering_task succeeded with the documented source-task fields, repo://ppow1/Riverview-, integration base 9f08b46d40bb8edfd7ea40f7ad65aa355af4971f, and stable key issue359-workmode-doc-acceptance-20261027-01.
- Durable objective: objective:5e29a3bb-f322-53d8-bebd-0acce2a25700. Status read-back confirms PROPOSED, verified grounding, and direct-dispatch event. Assignment, execution, verification and artifact remain absent; no completion claim.
- Confirmed discovery defect: static tool_catalog.json lacks this operation in read-only discovery payloads, although schema, Dashboard routing and backend intake exist. Repair adds discovery metadata and a regression test without weakening authority or replacing dispatch.
- PR #358 was merged into codex/command-gateway-20261026; default main lacks these source paths. A 404 on main did not establish source absence.

### GH-CONN-006 — Camrui scoped request service now responds
- Date: 2026-10-27; task RV-COMMS5-DISPATCH-359.
- Following inspection of exact supported host/action schemas, a new bounded Camrui standard caller request succeeded: delegation-request:0ee90c1d38ac42159be57ab416057f8f (two-hour duration).
- Matching service:command-gateway executor request succeeded: delegation-request:4e9457068b0047eb903a5bea383c488d (two-hour duration, 20-use maximum).
- Caller status read-back confirms pending, no grant_id or approval. Neither request activates authority. Prior BACKEND_UNAVAILABLE is retained above as historical evidence rather than treated as permanent unavailability.
- Live host inspection and deployment remain subject to actual approved grants and OS boundaries. See COMMS5_DIRECT_DISPATCH_359.md for exact actions, diagnostics, acceptance limits and rollback.
