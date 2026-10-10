#!/usr/bin/env python3
# RIVERVIEW~ CONTROLLED SOURCE
# File: scripts/verify_event_processor.py
# Component: EVENT-PROCESSOR
# Revision: 1.0.0
# Purpose: Commission one unattended assignment through the installed processor
# Execution Model: Request-driven verifier; processor remains independently supervised
# Observability: Sanitized JSON evidence with assignment/event/cursor identities
# Dependencies: Installed Riverview package; PostgreSQL; protected PGPASSFILE
# Authority: Creates one uniquely named development acceptance assignment
# Changed: 2026-10-10 UTC | RV-M1.3-002 | Add repeatable live progression verifier
# Contracts: docs/development/M1.3-002_REVISION_RECORD.md
# Tests: Isolated PostgreSQL integration and Camrui commissioned execution
# History: New file; Git
"""Create and verify one uniquely named M1.3 development assignment."""

import argparse
import json
import os
import time
from uuid import uuid4

import psycopg

from riverview_core.event_processor import PostgresEventProcessor
from riverview_core.postgres_ledger import PostgresLedger


def verify(dsn, schema, consumer_id, timeout):
    if "password" in psycopg.conninfo.conninfo_to_dict(dsn):
        raise ValueError("database password in DSN is forbidden")
    assignment_id = "m13-commission-" + uuid4().hex
    ledger = PostgresLedger(dsn, schema=schema)
    try:
        ledger.create(assignment_id, "engineering", "commission-create:" + assignment_id,
                     authority_ref="commissioning:RV-M1.3-002",
                     objective_ref="verify unattended assignment progression",
                     actor_id="commissioner:RV-M1.3-002",
                     workflow_id="m13-commissioning.v1", workflow_step="intake")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            assignment = ledger.get(assignment_id)
            if assignment and assignment["state"] == "ready":
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("assignment did not advance before timeout")
        events = [event for event in ledger.events() if event["assignment_id"] == assignment_id]
        if len(events) != 2 or events[0]["event_type"] != "assignment.created" or \
                events[1]["event_type"] != "assignment.transitioned":
            raise RuntimeError("expected exactly one created and one transition event")
        if events[1]["causation_id"] != events[0]["event_id"]:
            raise RuntimeError("transition event does not reference its source event")
        processor = PostgresEventProcessor(dsn, schema=schema, consumer_id=consumer_id)
        try:
            cursor = processor.cursor_position()
        finally:
            processor.close()
        if cursor < events[1]["seq"]:
            deadline = time.monotonic() + timeout
            while cursor < events[1]["seq"] and time.monotonic() < deadline:
                time.sleep(0.1)
                processor = PostgresEventProcessor(dsn, schema=schema, consumer_id=consumer_id)
                try:
                    cursor = processor.cursor_position()
                finally:
                    processor.close()
            if cursor < events[1]["seq"]:
                raise RuntimeError("consumer cursor did not cover the transition event")
        return {"status": "PASS", "assignment_id": assignment_id,
                "state": assignment["state"], "created_event_id": str(events[0]["event_id"]),
                "transition_event_id": str(events[1]["event_id"]),
                "created_seq": events[0]["seq"], "transition_seq": events[1]["seq"],
                "causation_matches": True, "cursor": cursor, "consumer_id": consumer_id}
    finally:
        ledger.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()
    dsn = os.environ.get("RIVERVIEW_PG_DSN", "")
    schema = os.environ.get("RIVERVIEW_PG_SCHEMA", "riverview_dev")
    consumer = os.environ.get("RIVERVIEW_PROCESSOR_ID", "assignment-intake.v1")
    try:
        if not dsn or args.timeout <= 0:
            raise ValueError("valid RIVERVIEW_PG_DSN and positive timeout are required")
        report = verify(dsn, schema, consumer, args.timeout)
        code = 0
    except (OSError, ValueError, RuntimeError, psycopg.Error) as exc:
        report = {"status": "FAIL", "failure_type": type(exc).__name__}
        code = 1
    print(json.dumps(report, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
