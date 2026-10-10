<!--
Riverview~ Controlled Document
File: docs/standards/ENGINEERING_RECORDS_STANDARD.md
Component: ENG-RECORDS
File Revision: 1.0.0
Purpose: Define engineering records and traceability requirements
Authority: Governs engineering records; content status remains Proposed pending Steward acceptance
Changed: 2026-10-10 UTC | RV-ENG-REV-003 | Establish file-level revision metadata for the existing Rev 1.0 standard
-->
# Riverview~ Engineering Records Standard — Rev 1.0

**Status:** Proposed engineering standard, pending Steward acceptance.  
**Date:** 2026-10-09  
**Related:** `docs/standards/COMPONENT_DEFINITION_OF_DONE.md` Rev 1.3.

## Intent

Provide traceability without redundant manual bureaucracy. Four distinct records answer four different questions. Each record references a stable task ID, component ID, and commit/deployment revision where applicable. A record is not proof of success unless it links to independently reproducible evidence.

## Record types

### 1. Development journal — why?
**Source:** `docs/development/JOURNAL.md` (append-only entries) or linked GitHub issues/PR decisions.  
**Trigger:** material design choice, experiment, discovery, incident, failed approach, blocker, or handoff. Not required for every edit.  
**Minimum fields:** timestamp UTC, task/component ID, actor, context, decision/experiment, evidence, outcome, next action, relevant commit/issue.  
**Retention:** Git history; amendments append a correction rather than silently rewriting a past conclusion.

### 2. Change history — what changed?
**Source of truth:** Git commits and pull requests; release-level summaries in `CHANGELOG.md`.  
**Trigger:** merged behavior/interface/security/operational change; release or deployment milestone.  
**Minimum fields:** version or commit, date, affected components, behavior/contract impact, migration/rollback implications, links to PR and acceptance evidence.  
**Automation:** derive commit/PR links; do not duplicate every diff manually. No separate mutable change blog required.

### 3. Checkout / acceptance evidence — what was actually verified?
**Source:** immutable, machine-generated test/deployment reports under `evidence/checkouts/<component-id>/<timestamp>-<short-sha>/` or equivalent durable artifact storage with links from Git.  
**Trigger:** integration test, deployment, regression, release candidate, fault/restart/recovery drill, or Steward acceptance.  
**Minimum fields:** UTC timestamp, task/component ID, source commit, target host/environment, exact command/tool version, test cases and counts, exit codes, stdout/stderr or artifact hashes, operator/automation identity, unresolved failures, decision and reviewer.  
**Rule:** FAIL and PARTIAL runs are retained, not overwritten by later PASS runs. Test data is sanitized; credentials are never logged. Checkout is evidence, not an approval by itself.

### 4. Operational event ledger — what happened during execution?
**Source:** authoritative PostgreSQL event stream and projections, not a manually edited Markdown log.  
**Trigger:** lifecycle transitions, dispatch, result, retry, approval, escalation, recovery, and relevant failures.  
**Minimum fields:** durable event ID, UTC timestamp, component/assignment ID, event type, correlation/causation ID, actor/authority, outcome, sanitized structured payload.  
**Rule:** event producers must not silently discard failures; retention, access and export follow component contracts. Operational events are not equivalent to development notes.

## Additional logs: only when justified

Structured runtime logs, metrics, traces, audit/security logs, backup/restore records, and incident reports may be necessary, but are not independent manual journals by default. Define them in the component's observability/security contract with ownership, retention, access, and incident response. Sensitive Undercurrent material must not be exported into ordinary records.

## Cross-record linkages

`task_id`, `component_id`, `source_commit`, `deployment_id`, and `correlation_id` are canonical linking keys. Where a field does not apply, mark N/A; do not invent it. Git holds engineering standards, source and change history; PostgreSQL holds operational state; durable checkout artifacts preserve evidence. Steward visualization links to these records rather than copying their contents.

## Definition of Ready / Done integration

At intake, classify task type and documentation depth; assign ID, owner, acceptance criteria, execution model, visibility contract and required record types. During work, journal only material decisions. At code change, link commit/PR. At checkout, automatically capture evidence. At deployment, record version, environment, acceptance result, and unresolved exceptions. A component cannot pass its DoD without traceable checkout evidence and operational logging appropriate to its responsibilities.

## Anti-bureaucracy rules

- No requirement to maintain multiple descriptions of the same commit.
- No hand-written duplicate of machine-captured output.
- No success claims based only on a command invocation or an assistant's narrative.
- No requirement for a development journal entry on trivial changes without a decision or learning.
- No manual approvals added for already-authorized routine work.
- The record system must not become a one-shot gate that prevents continuous authorized operation.

## First implementation sequence

1. Approve this standard and create the lightweight journal and change-history entry points.
2. Implement checkout evidence capture in test/deploy scripts, including failed runs.
3. Connect runtime event and monitoring contracts as the Core becomes persistent.
4. Verify that the Steward can navigate from component status to deployed revision, checkout result, change history, and relevant incident.
