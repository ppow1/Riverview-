# RIVERVIEW~ CONTROLLED EVIDENCE SCRIPT
# File: evidence/checkouts/RESIDENT-CONVERSATION/20261011T234000Z-pre-fix-six-four/reproduce.py
# Component: RESIDENT-CONVERSATION
# Revision: 1.0.0
# Purpose: Reproduce pre-fix same-connection six versus independent four event visibility
# Execution Model: Isolated disposable PostgreSQL schema and deterministic fake provider
# Observability: Sanitized counts and transaction state only; no message content
# Dependencies: Python 3.12, psycopg 3, tests from the pinned pre-fix commit
# Authority: Creates and drops only a unique rvtest schema through its test fixture
# Changed: 2026-10-11 UTC | RV-M3.4-CHAT-DURABILITY-001 | Preserve exact predecessor symptom reproducer
# Contracts: docs/components/RESIDENT_CONVERSATION.md
# History: Evidence artifact manifest

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

EXPECTED_COMMIT = "ea6748729fabfa3b93e3abb457f4e0e46357be26"
parser = argparse.ArgumentParser()
parser.add_argument("--repo", required=True, type=Path,
                    help="temporary worktree checked out at the expected predecessor commit")
args = parser.parse_args()
repo = args.repo.resolve()
actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
if actual != EXPECTED_COMMIT:
    raise SystemExit("reproducer requires the pinned pre-fix source commit")
sys.path.insert(0, str(repo))
sys.path.insert(0, str(repo / "src"))
sys.path.insert(0, str(repo / "tests"))
from test_resident_conversation import ResidentConversationTests
import psycopg
from psycopg import sql

if not os.environ.get("RIVERVIEW_TEST_PG_DSN"):
    raise SystemExit("RIVERVIEW_TEST_PG_DSN must target a throwaway PostgreSQL cluster")
case = ResidentConversationTests(methodName="test_authorized_chat_persists_and_reloads_by_human_and_office")
case.setUp()
try:
    first = case.service.send(case.steward_token, message="isolated first turn",
                              client_message_id=str(uuid4()))
    conversation_id = first["conversation_id"]
    case.service.send(case.steward_token, message="isolated second turn",
                      conversation_id=conversation_id, client_message_id=str(uuid4()))
    committed_before = case.service.history(case.steward_token, conversation_id)
    if len(committed_before["events"]) != 4:
        raise AssertionError("expected four committed baseline events")
    with case.store.db.transaction():
        acknowledged = case.service.send(case.steward_token,
            message="isolated nested transaction turn", conversation_id=conversation_id,
            client_message_id=str(uuid4()))
        same_connection_count = len(case.service.history(
            case.steward_token, conversation_id)["events"])
        with psycopg.connect(os.environ["RIVERVIEW_TEST_PG_DSN"], autocommit=True) as fresh:
            independent_count = fresh.execute(sql.SQL(
                "SELECT count(*) FROM {}.resident_conversation_events WHERE conversation_id=%s"
            ).format(sql.Identifier(case.schema)), (conversation_id,)).fetchone()[0]
        transaction_open = case.store.db.info.transaction_status == psycopg.pq.TransactionStatus.INTRANS
        outcome = {
            "preexisting_committed_events": len(committed_before["events"]),
            "api_ack_status": acknowledged["status"],
            "same_connection_api_events": same_connection_count,
            "independent_postgresql_events": independent_count,
            "connection_in_transaction_before_outer_commit": transaction_open,
            "exact_six_vs_four_reproduced": (
                acknowledged["status"] == "completed" and same_connection_count == 6
                and independent_count == 4 and transaction_open),
        }
        if not outcome["exact_six_vs_four_reproduced"]:
            raise AssertionError("expected the six-versus-four transaction visibility gap")
    print(json.dumps(outcome, sort_keys=True))
finally:
    case.tearDown()
