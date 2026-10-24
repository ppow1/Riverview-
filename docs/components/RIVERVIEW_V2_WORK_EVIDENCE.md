# V2 Work and Engineering evidence

The Work tables and Grace's Engineering Progress cards use the reusable view model in `website/v2/deployed/assets/work-evidence-adapter.js` and the read-only disclosure in `work-evidence.js`.

Sources remain the existing authenticated Dashboard APIs:

- `GET /api/v1/objectives?limit=25` — objective lifecycle stage/status, linked assignment ID, latest lifecycle activity, rework rationale, failure counts/times, verification, and sanitized grounding diagnostics. The existing account authorization scopes global listing to Steward and non-Steward reads to an owned conversation.
- `GET /api/v1/assignments?limit=25` — assignment state, recorded workflow stage, owner, last institution-visible event ID/sequence/time, and exact assignment IDs.
- `GET /api/v1/assignments/{assignment_id}` — on-demand owner/workflow node, bounded event history, worker attempts, and verification records. The source filters assignment histories that include non-institution privacy events.
- `GET /api/v1/events` remains the existing institution-level event stream; detail disclosure uses assignment detail so it can show the exact assignment-bound history rather than guessing by timestamp.

Objective to assignment links are joined only when `objective.assignment_id` equals `assignment.assignment_id`. The present API contracts do not expose objective step dependency edges or a blocker reason for every blocked row. The UI names those missing fields explicitly; it does not infer dependency links from ordering, request text, timestamps, or similar IDs.

Elapsed progress labels are calculated from the persisted event timestamp and the browser clock. Missing, invalid, or future timestamps remain explicit. On transient refresh failure, last-known rows remain visible as stale with their last successful source observation; authentication denial clears cached records. The UI makes GET requests only and does not alter cancellation or worker execution behavior.

Focused view-model tests: `node --test tests/test_v2_work_evidence.cjs`. Existing V2 cancellation and role authorization tests remain in `tests/test_status_dashboard.py`.
