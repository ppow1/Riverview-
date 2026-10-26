# V2 Operational Controls

<!-- Revision: 1.1.0 -->

This document records the shipped boundary for the operational controls increment.

## Steward delegation approvals

The Delegation Approvals panel is in **Settings → Permissions**. It reads a bounded
projection of `delegated_grant_requests` and delegated `authority_grants`, including
the current expected request SHA-256 and linked authority event IDs. The existing
`POST /api/v1/steward/delegation-grant-requests/{request_id}/decision` remains the
only decision endpoint. Grant revocation calls the existing
`AuthorityRegistry.revoke_grant` function; this increment adds no grant store and
does not issue or replay approvals.

The new list/detail/revoke routes are restricted to an authenticated Dashboard
account cookie bound to `steward:camrui`, the Steward role, and the canonical
`authority.grant` grant at `institution` scope. POST requests also pass the
Dashboard's existing CSRF validation. Request lists are limited to 100 rows and
include audit event references. The browser prompts for confirmation before
decisions and revocation. The backend remains authoritative for stale request
hashes, expiration, idempotency, authorization, and audit writes.

The 2026-10-26 production review found that release `42f76dc5` had the browser
routes but did not construct or inject the protected
`Comms5DelegationAuthorityAdapter` at Dashboard startup. Consequently the
delegation projections failed closed as unavailable. The corrective candidate
restores the adapter using the existing systemd-protected manager passfile and
Steward token; it does not read either credential from a browser request. It
also routes the existing hash-bound `/decision` POST to the adapter. This
change is not considered browser-accepted until an institutionally linked
Steward session exercises it.

GPU host requests support an exact registered host/action, a finite use count
and an expiration, either bound alone or together. Blank maximum executions
means time-limited access; one means a single execution. The existing authority
reservation path enforces finite-use bounds atomically. Expiration is required
and capped at one year; current institutional policy does not expose a
non-expiring choice in this UI.

The existing ChatGPT → Comms5 → Codex path uses action
`comms5.operations.non_destructive.v1` at `project:Riverview`, for target
`service:chatgpt`. Its canonical policy requires unlimited uses and ends the
grant 24 hours after activation; objective and assignment permissions remain
separate requirements. The active Comms5 release registers
`comms5_submit_direct_engineering_task`, but the current Authority Registry has
no active `service:chatgpt` principal, so the website must present this request
type as unavailable. Neither a GPU host grant nor this project grant by itself
authorizes objective submission or Engineering execution. No principal, grant,
or production request was created during this review.

These administrative routes are intentionally marked as capability exclusions:
they operate on institutional authority and must not become resident/Grace
invocable tools through automatic website operation discovery.

## GPU workload controls

The read-only ComfyUI runtime and queue projection remains available from PR #334.
Start/stop and workload switching are not enabled. The confirmed service units
run on the remote inference host, and the current deployment has no narrowly
scoped remote executor that checks active requests, verifies VRAM release, and
confirms service readiness. This interface must remain read-only until such an
authorized executor and its protected transport are available. No workload was
switched for this increment.

## ntfy attachments

Validated dashboard links and view-only actions remain enabled. Rich attachments
are not enabled because the existing dispatcher contract carries event and
record identifiers but no verified artifact reference/authorization metadata,
and the existing conversation attachment endpoint requires a resident account
session unavailable to the phone's ntfy fetch client. A phone-reachable contract
must bind a specific authorized artifact to a bounded retrieval credential or
equivalent existing phone identity; arbitrary filesystem URLs and public artifact
mounts are not acceptable substitutes. No notification attachments were sent.

## Codex fuel gauges

The original producer and a verified subscription-capacity data source have not
been recovered. Usage percentages remain unavailable; API billing is not a
substitute. This item stays open until an authoritative source is available.
