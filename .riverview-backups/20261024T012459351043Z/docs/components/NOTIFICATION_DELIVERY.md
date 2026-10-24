<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_DELIVERY.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.1
Purpose: Define durable visual notification and pending decision-request projection
Authority: Records notification state only; cannot approve or resolve institutional decisions
Changed: 2026-10-11 UTC | RV-M3.2-001 | Normalize controlled Markdown spacing
History: Git and revision/backup manifest
-->
# Durable notification delivery

**Milestone:** M3.2 — Durable notification and decision requests
**State:** Engineering in progress; no shared-schema migration or service deployment is claimed until commissioning evidence is recorded.
**Canonical graph:** `rv:notification-delivery:visual-attention`.

## Boundary and authoritative inputs

The CME monitor remains responsible for detecting attention conditions and
recording `cme_monitor_events`. The notification dispatcher periodically scans
that durable table and writes only `attention_notifications`,
`steward_decision_requests`, `notification_events`, and
`notification_dispatcher_health`. It never changes assignment lifecycle,
leases, or source events. A transaction advisory lock limits active scanners;
stable source-event uniqueness makes restart and repeated scan safe. Migration
0006 adds a scan index to the existing CME event table, preventing periodic
reconciliation from requiring an ever-growing full-table scan. Receipt-event
rows are protected against update and delete by a database trigger.

Only these CME event types are projected: `assignment_stalled`,
`deadline_missed`, `assignment_attention`, `recovery_requested`,
`monitor_failed`, and `attention_resolved`. Private assignments are excluded by
the institution privacy-domain filter. Notice summaries are fixed server-side
strings; CME `details` and ledger payloads are never rendered.

An `assignment_attention` event creates a pending decision request only if the
authoritative current assignment state is `awaiting_steward`. The dashboard
bearer is a service credential and does not identify a Steward. M3.2 provides
no decision-resolution operation. Both browser receipts carry
`authenticated_dashboard_client` provenance and have `authority_effect: none`.
The request remains `pending` after rendering and receipt acknowledgment.

## Visual delivery contract

The only channel in this slice is `dashboard.visual.v1`; no external provider,
purchase, SMS, audio, or paid service is introduced.

| State | Meaning | Durable evidence |
| --- | --- | --- |
| `queued` | Source attention was durably projected; a dashboard client has not confirmed rendering. | `attention_notifications` and `notification_queued`. |
| `delivered` | An authenticated browser fetched the bounded page, rendered a notice while the Notifications view was visible, then confirmed rendering. | `delivered_at` and idempotent `delivery_confirmed`. |
| `acknowledged` | The authenticated dashboard client explicitly acknowledged receipt. This is not a decision. | `acknowledged_at` and idempotent `receipt_acknowledged`. |

If polling/API/database/UI work fails, the state is not advanced. A persisted
`queued` value is not reported as delivery. Service failure is exposed through
HTTP unavailable state, systemd/journal, and dispatcher health; no false success
record is written. The browser retries only on a later successful visible
refresh. Duplicate requests return the already-recorded state.
Dispatcher health is derived from its last successful durable heartbeat: an
explicit recorded failure is `degraded`, a future heartbeat is `unverified`, a
heartbeat older than 15 seconds is `stale`, and a fresh successful heartbeat is
`healthy`. A missing row is `not_initialized`.

See `NOTIFICATION_DELIVERY_API.schema.json` for bounded response schemas and
`NOTIFICATION_DELIVERY_COOKBOOK.md` for diagnosis/recovery steps.

## Routes and security

| Route | Contract | Authority |
| --- | --- | --- |
| `GET /api/v1/notifications?limit=n` | Authenticated, read-only, maximum 50 notifications and dispatcher health. | Projection only. |
| `POST /api/v1/notifications/{uuid}/delivered` | Empty body; record client rendering receipt after visible render. | Receipt only. |
| `POST /api/v1/notifications/{uuid}/acknowledge` | Empty body; requires `delivered_at`; append receipt acknowledgment. | Receipt only; cannot decide. |

Every route is loopback and Host-header checked. API access requires the
existing dashboard bearer over the same origin. Request bodies, browser URLs,
and credentials are not logged. Other mutating methods remain rejected. A
receipt before delivery returns conflict; malformed/unknown notices return
not-found; database errors return unavailable. There is no endpoint that can
change `steward_decision_requests.status`.

## Persistence and migration

Migration `0006_durable_notifications` is an additive explicit migration under
the selected schema. It has no startup DDL. Before applying it to the shared
`riverview_dev` schema, record preflight inventory, create a protected custom
format PostgreSQL backup, verify its checksum, and restore it to a disposable
cluster with successful `pg_restore --list` and application connectivity. Then
apply the reviewed migration with the controlled migration runner and verify
all four relations, migration checksum, grants, and M3.1/M2.4 health. Preserve
M1.1/M1.2/M1.3/M2.4 services and all existing assignment/event rows.

Rollback is forward recovery: do not drop the additive tables after records
exist. If a release fails, restore the dashboard and dispatcher release/unit
links while retaining the migration and records; fix forward. A database restore
is destructive and requires an explicit verified target, backup, and recovery
plan; never restore over the live schema as a routine rollback.

## Verification and status

Integration tests use only unique `rvtest_*` schemas in a disposable PostgreSQL
cluster. Live commissioning must prove a genuine CME condition flows through
the dispatcher into the dashboard; rendering/receipt/acknowledgment persist and
survive restart; pending requests remain pending; private rows never appear;
unrelated CME, worker and dashboard operations remain available. Unit tests or
the visual presence of a notice do not alone establish commissioning or full
Component DoD. M3.2 is not declared DONE until its roadmap gates, actual
deployment, browser behavior, process graph, evidence, revisions, CI, and full
applicable DoD are separately evaluated.
