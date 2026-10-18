<!--
Riverview~ Controlled Document
File: docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.md
Component: LINUX-BROWSER-ACCEPTANCE
File Revision: 1.0.0
Purpose: Define the safe read-only browser-run status projection contract for dashboard consumers
Execution Model: Request-driven local status projection; dashboard consumption is not yet integrated
Observability: `browser-status.json` validated against the adjacent schema; safe diagnostic component reference
Dependencies: `scripts/browser_status_projection.py`; local runner evidence
Authority: Read-only status metadata; no browser actions, credentials, approvals, or work-order mutations
Changed: 2026-10-18 UTC | RV-C2-BROWSER-STATUS-001 | Initial browser acceptance status contract
Contracts: docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.schema.json; docs/operations/LINUX_BROWSER_ACCEPTANCE.md
Tests: tests/test_browser_status_projection.py
History: Git and revision/backup manifest
-->
# Linux browser acceptance run status contract

The projection is a small, lossy JSON record for a future Steward dashboard/API consumer. It reports the state of a **local loopback acceptance run**, not the health of Grace, CME, production, or the dashboard. It never exposes target origin, host, path, conversation content, account label, cookie, request body, arbitrary exception text, output directory, or raw trace link.

The contract is `rv.browser-acceptance.status.v1`, described by `LINUX_BROWSER_ACCEPTANCE_STATUS.schema.json`. The local projector reads only fixed runner files and allowlisted error `kind` values. Its output fields are `schema_version`, `component_id`, `source_commit`, deterministic `run_id`, `environment`, `run_status`, `failure_category`, `observed_at`, `started_at`, `completed_at`, `freshness`, bounded test counts, and `diagnostic_ref`. `diagnostic_ref` is the stable component document identifier `docs/components/LINUX_BROWSER_ACCEPTANCE_STATUS.md`, which maps to the dashboard's existing allowlisted component-document route. It is never an arbitrary URL or filesystem path.

`run_id` is a stable SHA-256-derived correlation ID over the source commit and run start time. Freshness is `current` for observations no older than 15 minutes, `stale` for older runs, and `unknown`/`unavailable` when time evidence is missing or future-dated. Run state values distinguish `passed`, `failed`, `blocked`, `staging_not_available`, `running`, and `unknown`. Failure categories come from a closed enumeration; unrecognized strings are discarded. `blocked` includes denied mutations/cross-origin access or unsupported remote targets. `staging_not_available` is an explicit operator-observed prerequisite state and is not a fabricated run.

Generate a status for an existing local run:

```bash
python3 scripts/browser_status_projection.py \
  --evidence-dir /path/to/private/browser-evidence \
  --source-commit "$(git rev-parse HEAD)" \
  --output /path/to/private/browser-evidence/browser-status.json
```

To publish a safe prerequisite state without claiming a browser test ran:

```bash
python3 scripts/browser_status_projection.py \
  --state staging_not_available \
  --source-commit "$(git rev-parse HEAD)" \
  --output /path/to/private/browser-status.json
```

The command performs no network access and writes the projection atomically with mode `0600` in a mode `0700` directory. It requires a full Git SHA. The dashboard/API integration is not implemented by this change: the projection file must remain an operator/local artifact until the dashboard owner adds a read-only, allowlisted consumer and validates it against this schema. Do not add this JSON to a public static web root or mark dashboard status healthy from this record. Requests to the dashboard owner should consume these typed fields, preserve `stale`/`blocked`/`staging_not_available`, link only through the fixed `diagnostic_ref`, and ignore all unknown fields.
