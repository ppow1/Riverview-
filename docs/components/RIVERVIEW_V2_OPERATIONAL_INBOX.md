<!-- Document Revision: 1.0.0 -->
# Riverview V2 Operational Inbox

The Communications view includes a reusable, read-only inbox adapter over the existing authenticated Dashboard projections:

- `GET /api/v1/notifications?limit=50` — notification history, source event, delivery state, dispatcher observation, and summary.
- `GET /api/v1/attention?limit=50` — CME attention events and their event IDs.
- `GET /api/v1/events?limit=50` — institution-visible event history and sequence IDs.

`website/v2/deployed/assets/operational-inbox-adapter.js` joins records by their authoritative event ID. The presentation module requests each feed on entry to Communications and on explicit refresh. It uses the same-origin authorized browser session, sends only GET requests, and creates no records or acknowledgments. The server APIs retain responsibility for authentication, authorization, privacy filtering, and data retention.

The current source contracts do not provide a general severity field, resident or service link, or event-detail URL for every row. The inbox states this where missing, retains notification delivery status where available, and links an assignment reference to the existing Work view. Event and notification identifiers are shown as evidence references; no unsupported detail route is fabricated.

Each feed has independent freshness. A failed refresh retains its last successfully loaded rows and marks them stale with the last successful time. Authentication denial clears that feed's in-memory rows. `not_initialized`, unavailable, denied, and empty are separate states.

Focused browser adapter checks: `node --test tests/test_v2_operational_inbox.cjs`. The existing fixture-shell regression suite is `python3 -m pytest -q tests/test_v2_workspace_shell.py`.
