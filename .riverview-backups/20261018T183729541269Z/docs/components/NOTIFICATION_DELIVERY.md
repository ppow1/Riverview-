<!--
Riverview~ Controlled Document
File: docs/components/NOTIFICATION_DELIVERY.md
Component: NOTIFICATION-DELIVERY
File Revision: 1.0.3
Purpose: Define durable visual notice and read-only provider delivery status projections
Authority: Records notification state only; cannot approve or resolve institutional decisions
Changed: 2026-10-11 UTC | RV-M3.2-001 | Normalize controlled Markdown spacing
Changed: 2026-10-18 UTC | RV-NOTIFICATION-STATUS-PROJECTION-20261018 | Add redacted push queue/freshness projection to authenticated notification API
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

This section describes the existing visual channel `dashboard.visual.v1`.
Provider-based mobile delivery is a separate additive consumer of these same
durable notices; see `NOTIFICATION_IPHONE_DELIVERY.md`. This visual path does
not itself call an external provider.

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

The optional iPhone provider delivery contract and setup/recovery instructions
are in `NOTIFICATION_IPHONE_DELIVERY.md` and
`NOTIFICATION_IPHONE_DELIVERY_COOKBOOK.md`.

## Routes and security

| Route | Contract | Authority |
| --- | --- | --- |
| `GET /api/v1/notifications?limit=n` | Authenticated, read-only, maximum 50 visual notices, dispatcher health, and provider delivery status. | Projection only. |
| `POST /api/v1/notifications/{uuid}/delivered` | Empty body; record client rendering receipt after visible render. | Receipt only. |
| `POST /api/v1/notifications/{uuid}/acknowledge` | Empty body; requires `delivered_at`; append receipt acknowledgment. | Receipt only; cannot decide. |

Every route is loopback and Host-header checked. API access requires the
existing dashboard bearer over the same origin. Request bodies, browser URLs,
and credentials are not logged. Other mutating methods remain rejected. A
receipt before delivery returns conflict; malformed/unknown notices return
not-found; database errors return unavailable. There is no endpoint that can
change `steward_decision_requests.status`.

### Provider delivery status contract

The authenticated `GET /api/v1/notifications` response includes a bounded
`push_delivery` object (`rv.notification_push_status.v2`). It reads only
aggregate states from migration 0007's `notification_delivery_queue` and
`notification_delivery_health`; it does not change queue, lease, retry, event,
or decision state. The projection reports component status (`healthy`, `stale`,
`degraded`, `not_initialized`, `unavailable`, or `unknown`), observation time,
heartbeat age against a 15-second threshold, counts by queue state, due retries,
expired sending leases, recovery condition, last sanitized error code and
aggregate worker counters.

The projection intentionally excludes delivery IDs, notification titles and
bodies, provider receipt values, message content, assignment/event details,
provider URLs, credentials, and worker instance IDs. Error codes are constrained
to a short identifier character set; any unexpected value is represented by
`notification_error_code_redacted`. HTTP provider acceptance remains distinct
from iPhone display or acknowledgment. `not_initialized` means the additive push
schema or its worker heartbeat is absent. An incomplete schema or query
permission failure yields an `unavailable` provider projection while preserving
the visual notification page where its own source tables remain available.

The API contract and sanitized response examples are in
`NOTIFICATION_DELIVERY_API.schema.json` and
`../../tests/fixtures/notification_delivery_status_examples.json`. This change
adds a machine-readable field to the existing authenticated API only; it does
not add or claim a Steward UI panel. The dashboard owner must integrate the
field into the page, preserve the state distinctions, and avoid treating
provider acceptance as handset delivery.

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
