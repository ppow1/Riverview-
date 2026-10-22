# Riverview~ AI Engineering Hints

**Document Revision:** 1.0.6  
**Status:** Working agent guidance  
**Date:** 2026-10-21  
**Component:** ENG-AGENT-GUIDANCE  
**Purpose:** Startup instructions for any AI agent performing engineering work on Riverview~.  
**Authority:** Guidance for work in this repository; subordinate to the user's explicit instructions and the governing engineering standards.

## Start here — every new engineering session

1. Confirm the repository is **ppow1/Riverview-** (trailing hyphen). Do not substitute `ppow1/Riverview` or the historical archive. Identify branch, commit, working-tree changes, and target runtime before editing.
2. Read `docs/CODEX_ENGINEERING_CAMPAIGN.md` as the standing **full-roadmap Codex execution specification**, including its non-negotiable API/visibility hooks, real internal workflow state, component flowcharts, Steward web interface, diagnostic mapping and Definition of Done evidence. Then read `docs/ROADMAP.md` and use its **Current cursor**: when the Steward says **“go”** or **“next”**, work on the earliest unfinished step and report its acceptance evidence. Read `docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md`, `docs/standards/COMPONENT_DEFINITION_OF_DONE.md`, and `docs/standards/ENGINEERING_RECORDS_STANDARD.md`. Read relevant architecture/component contracts for the task.
3. Inspect the **complete relevant implementation and dependencies**, not just a small code snippet. Check what already exists before proposing or writing replacements.
4. State the task objective, scope, affected files, existing revision numbers, success criteria, and verification plan. Keep the process proportional to the actual work; do not invent infrastructure or redesign unrelated systems.
5. Preserve each existing file's **exact predecessor bytes and SHA-256 before modifying it**. Record the predecessor location, revision, task ID, and restoration method. Confirm that the backup can be read back. Do not treat an unprotected working copy as an immutable backup.
6. Increment the **individual file revision** on every content change, including metadata-only edits. New text/source files begin at `1.0.0` unless explicitly experimental. Keep language-appropriate source headers; use a sidecar for formats that cannot contain comments.
7. Make the smallest coherent change. Maintain intended **persistent/event-driven** behavior when required. Do not silently replace continuous agents with turn-based, one-shot, or human-approval loops.
8. Test affected behavior and relevant regressions. Record actual commands, exit codes, pass/fail/skip counts, environment, and limitations. Never report unexecuted tests as PASS.
9. Review the diff, verify only intended files changed, and confirm predecessor restoration remains possible. Do not commit, push, deploy, or alter production data unless the task authorizes it.
10. End with a precise handoff: files and revisions changed, predecessor locations, test evidence, commit/deployment status, outstanding problems, and next action. **After the handoff, display the final Codex completion banner required by `docs/CODEX_ENGINEERING_CAMPAIGN.md` (Mandatory Codex session completion indicator), with window identifier, SUCCESS/BLOCKED/FAILED status, and task.** The banner does not replace Definition of Done evidence.


## Machine access and operational recovery

**Before requesting SSH settings or probing hosts**, read [the canonical Riverview machine-access index](docs/operations/network/RIVERVIEW_MACHINE_ACCESS.md). It records Camrui, OctoMiner1, OctoMiner2, Windows development machine, their LAN addresses, verified aliases, and recovery links. Follow linked operational runbooks and historical records; distinguish verified details from pending inventory items.

## Institutional proposal authoring

If the task is to suggest, formalize, submit, review, or track a Riverview proposal, read `docs/development/PROPOSAL_AUTHORING_PLAYBOOK.md` and the institutional contract `docs/components/INSTITUTIONAL_PROPOSALS.md` (currently on PR #70's branch; verify availability on the working branch) before acting. A proposal draft is not execution authority. Use only the documented authenticated Steward conversation submission flow; never invent proposal IDs, API routes, or grants. Explicit Steward approval and separate authorized promotion are required before Engineering objective intake. If the contract or endpoint is unavailable, produce a submission-ready draft and mark it NOT SUBMITTED.

## Operational facts and boundaries

- **Authoritative GitHub repository:** `ppow1/Riverview-`; Windows development checkout: `A:\Riverview-New-Core`.
- **Camrui Ubuntu controller:** `/home/admin1/riverview-core` on the Camrui host. Windows is a development/transport environment, not the autonomous runtime.
- The last confirmed controlled migration baseline when this file was created was commit `6ad9f63f618886bb3ae6d2d99c255ce5921e9ae2`. **This is historical context, not a permanently expected HEAD**; inspect current Git state.
- Existing baseline preservation artifacts must not be overwritten. Group 1 migrated Markdown revisions; Group 2 migrated Python revision headers. Neither migration establishes a complete CI enforcement system.
- PostgreSQL schema initialization, live autonomous execution, and deployment must be independently verified; do not infer runtime readiness from passing unit tests.

## Engineering discipline

- Follow the lifecycle standard as a **working procedure today**, even though mandatory GitHub/OS-level enforcement is not yet installed.
- Revision control protects file history; the lifecycle standard also covers design, evidence, test, acceptance, deployment, recovery, and maintenance. Do not claim revision checks alone enforce the entire lifecycle.
- Do not launch broad governance, agent isolation, permissions, or CI projects unless explicitly requested. Build the next needed Riverview capability first.
- Prefer reproducible, automated checks and compact evidence over repetitive manual inventories.
- Distinguish **verified**, **not verified**, **skipped**, and **planned**.
- Do not fabricate repository contents, tool results, commits, tests, or completion.
- Do not place secrets in source, headers, reports, or chat.

## PowerShell rules for this project

- Every supplied PowerShell script starts with `Clear-Host`.
- **Do not use PowerShell `else` statements or `throw` statements.** Use explicit `if` checks, exit-code checks, and `try`/`catch` where needed.
- Scripts producing reports copy the **entire report** to the clipboard using `Set-Clipboard`.
- Prefer a standalone `.ps1` file for substantial scripts instead of a long interactive-console paste.
- Do not mistake normal Git stderr progress output for a command failure; evaluate exit codes.

## Agent startup response

Before editing, briefly report: repository/branch/HEAD, applicable standards, task scope, relevant code/dependencies, predecessor-preservation plan, and tests to run. If the task is purely informational, do not modify files.

## Revision history

- **1.0.6 — 2026-10-21:** Point the final-handoff instruction to the campaign's mandatory Codex completion banner; predecessor: `docs/history/AI_HINTS_rev1.0.5.md` (original blob `44b9af171babb5dba7c2ab8897441cf83b98f0de`).

- **1.0.5 — 2026-10-19:** Add direct machine-access index link for Camrui, OctoMiner1, OctoMiner2 and development workstation. Predecessor: `docs/history/AI_HINTS_rev1.0.4.md`.

- **1.0.4 — 2026-10-16:** Link proposal authoring and submission playbook; clarify Steward authorization boundary. Predecessor: `docs/history/AI_HINTS_rev1.0.3.md`.

- **1.0.3 — 2026-10-09:** Require all engineering agents to load the full Codex campaign and its observability, web visibility, flowchart, troubleshooting and DoD obligations. Predecessor: `docs/history/AI_HINTS_rev1.0.2.md`.

- **1.0.2 — 2026-10-09:** Treat “go” and “next” as equivalent roadmap commands. Predecessor: `docs/history/AI_HINTS_rev1.0.1.md`.

- **1.0.1 — 2026-10-09:** Link authoritative implementation roadmap and define “next” behavior. Predecessor: `docs/history/AI_HINTS_rev1.0.0.md` (original blob `78056bfebddb15ee8f8e678d5671cf4a443c0b55`).

- **1.0.0 — 2026-10-09:** Initial root-level AI engineering startup guidance, reflecting the established lifecycle and controlled migrations.
