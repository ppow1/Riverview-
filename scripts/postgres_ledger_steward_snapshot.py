"""Read-only Steward-facing JSON snapshot of the PostgreSQL ledger.

Requires RIVERVIEW_PG_DSN; optional RIVERVIEW_PG_SCHEMA (default public).
No schema creation, mutation, or dashboard server.
"""
import json
import os
import sys
from datetime import datetime, timezone

import psycopg
from psycopg import sql
from psycopg.rows import dict_row


def main():
    dsn = os.environ.get("RIVERVIEW_PG_DSN")
    schema = os.environ.get("RIVERVIEW_PG_SCHEMA", "public")
    snapshot = {
        "component": "postgres_assignment_ledger",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema": schema,
        "status": "unavailable",
        "assignment_counts": {},
        "last_event_seq": None,
        "last_event_at": None,
        "error": None,
    }
    if not dsn:
        snapshot["error"] = "RIVERVIEW_PG_DSN not set"
        print(json.dumps(snapshot, indent=2))
        return 2
    try:
        with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT to_regclass(%s) AS assignments, to_regclass(%s) AS events",
                            (schema + ".assignments", schema + ".events"))
                tables = cur.fetchone()
                if not tables["assignments"] or not tables["events"]:
                    snapshot["status"] = "not_initialized"
                else:
                    cur.execute(sql.SQL("SELECT state, count(*) AS n FROM {}.assignments GROUP BY state ORDER BY state").format(sql.Identifier(schema)))
                    snapshot["assignment_counts"] = {r["state"]: r["n"] for r in cur.fetchall()}
                    cur.execute(sql.SQL("SELECT max(seq) AS seq, max(occurred_at) AS at FROM {}.events").format(sql.Identifier(schema)))
                    last = cur.fetchone()
                    snapshot["last_event_seq"] = last["seq"]
                    snapshot["last_event_at"] = last["at"].isoformat() if last["at"] else None
                    snapshot["status"] = "connected"
    except Exception as exc:
        snapshot["error"] = type(exc).__name__ + ": " + str(exc)
    print(json.dumps(snapshot, indent=2))
    return 0 if snapshot["status"] in ("connected", "not_initialized") else 1


if __name__ == "__main__":
    sys.exit(main())
