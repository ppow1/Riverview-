# Engineering Progress: durable actionable diagnostics

Status: Steward-requested feature specification, 2026-10-21 EDT. **Not implemented or deployed.**

## Problem

Objective `objective:grace-conversation:cb419fc0-0354-515f-8a39-a0e91e0ab61f` (conversation `e01d1bbd-48af-481a-9592-a6784bb10561`, source message 4) was accepted via authenticated `/work-orders` POST (HTTP 202) at 23:47:45 EDT, but remained `WAITING_FOR_EVIDENCE` with no assignment. The Dashboard showed “Waiting for verified evidence” and “Steward action: Not currently required,” without a reason or actionable path. Read-only investigation identified the knowledge grounding gate but could not access the specific failed condition due to authenticated API and PostgreSQL permissions.

## Required behavior

1. **Durable diagnostic event per meaningful transition/failed gate**: record objective ID, source conversation/message, objective revision, event ID, timestamp, previous/new state, stage/component, attempted operation, outcome, machine-readable reason code, human-readable sanitized explanation, evidence reference or digest (not raw sensitive content), responsible component, retryability, next eligible retry time if any, required actor/action, and correlation/attempt ID. Ensure idempotent event insertion and bounded retention.
2. **Grounding validation details**: distinguish missing evidence, invalid/unverified status, missing source reference/revision/hash, serialization error, size limit, provider unavailable, and unknown error **only when actually observed**. Never infer a failure reason from generic `WAITING_FOR_EVIDENCE`. Persist the precise safe validation result at the failure site.
3. **Authenticated read API**: return diagnostic summaries with objective-specific authorization and provenance; never expose provider secrets, tokens, raw protected evidence, or cross-conversation data. Existing authorization rules remain authoritative.
4. **Engineering Progress UI**: show current blocking reason, last attempt, responsible component, retry schedule/eligibility, and whether Steward action is genuinely required. Offer expandable ordered event history and per-attempt details. Display “reason unavailable” when evidence is missing, not fabricated reasons. Never show “No action required” as a blanket substitute for unresolved indefinite wait.
5. **Lifecycle continuity**: diagnostics must survive refresh, service restart and retries; append new attempts rather than replacing history. A same-message retry must remain linked to the original objective, with no duplicate assignment.
6. **Verification**: test each grounding validation failure path, authorization boundary, event idempotency, UI rendering, retry lineage and restart persistence with disposable fixtures. Verify the exact current objective's status only via authorized read-only evidence; do not modify or retry it as part of implementing logging.

## Operational acceptance

Given an objective blocked in grounding, an authorized Steward can see **what failed, where, when, whether it will retry, and the smallest permitted next action** without SSH, database administration or interpreting generic status text.

## Implementation constraints

Start with the existing lifecycle event schema, status projection, grounding validator and authenticated Dashboard API. Reuse existing storage and status mechanisms; avoid parallel logging frameworks or unnecessary infrastructure. Changes require reviewed PR and independent acceptance before deployment. Preserve current live objective and services during investigation.
