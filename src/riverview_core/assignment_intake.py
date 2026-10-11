# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/assignment_intake.py
# Component: ASSIGNMENT-INTAKE
# Revision: 1.0.0
# Purpose: Require exact Steward assignment.create grant for durable intake
# Execution Model: One PostgreSQL transaction spans authorization and ledger creation
# Observability: Safe deny/unavailable status; durable actor and assignment-created event
# Dependencies: PostgreSQL ledger; M4.1 ExactGrantAuthorizer; applied migrations
# Authority: Caller cannot supply actor identity; missing or unavailable grant denies
# Changed: 2026-10-11 UTC | RV-M3.3-ASSIGNMENT-INTAKE | Add exact-grant assignment creation boundary
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md; docs/components/WORKER_ADAPTER.md
# Tests: tests/test_assignment_intake.py
# History: .riverview-backups/manifest.jsonl and Git
# =============================================================================
"""Grant-gated application path for creating durable Riverview assignments."""

from .institutional_authority import (
    ExactGrantAuthorizer,
    GrantCheckUnavailable,
    GrantDenied,
)
from .postgres_ledger import PostgresLedger


class AssignmentIntakeDenied(RuntimeError):
    """The request lacks a current exact assignment.create grant."""


class AssignmentIntakeUnavailable(RuntimeError):
    """The authority service cannot produce a trustworthy decision."""


class AuthorizedAssignmentIntake:
    """Create an assignment only while its exact authority grant is locked.

    The authority function and ledger write run on the ledger's same PostgreSQL
    connection and outer transaction. PostgreSQL holds the matched grant row
    lock through assignment and `assignment.created` event commit. The actor ID
    is derived from the protected grant result and cannot be caller supplied.
    """

    ACTION = "assignment.create"

    def __init__(self, ledger: PostgresLedger, authorizer: ExactGrantAuthorizer):
        if not hasattr(ledger, "db") or not callable(getattr(authorizer, "require", None)):
            raise TypeError("a PostgreSQL ledger and exact-grant authorizer are required")
        self.ledger = ledger
        self.authorizer = authorizer

    def create(self, assignment_id, owner, idempotency_key, *, credential,
               authority_ref, objective_ref, contract_ref=None,
               workflow_id="assignment.v1", workflow_step="intake",
               occupant_id=None, correlation_id=None):
        """Check exact scope and persist one attributed assignment atomically."""
        try:
            with self.ledger.db.transaction():
                with self.ledger.db.cursor() as cur:
                    self.ledger._set_search_path(cur)
                    principal = self.authorizer.require(
                        cur, credential, self.ACTION, authority_ref)
                return self.ledger.create(
                    assignment_id, owner, idempotency_key,
                    authority_ref=authority_ref,
                    objective_ref=objective_ref,
                    actor_id=principal["principal_id"],
                    contract_ref=contract_ref,
                    workflow_id=workflow_id,
                    workflow_step=workflow_step,
                    occupant_id=occupant_id,
                    correlation_id=correlation_id,
                )
        except GrantDenied:
            raise AssignmentIntakeDenied("assignment.create is not authorized for this exact scope") from None
        except GrantCheckUnavailable:
            raise AssignmentIntakeUnavailable("institutional authority is unavailable") from None
