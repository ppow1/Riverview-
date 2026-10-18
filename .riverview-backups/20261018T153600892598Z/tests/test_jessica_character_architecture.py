# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_jessica_character_architecture.py
# Component: JESSICA-CHARACTER-ARCHITECTURE
# Revision: 1.0.0
# Purpose: Verify Jessica's advisory boundary and evidence-gated proposal package
# Execution Model: Isolated in-process unit tests
# Observability: Assertions use synthetic resident requests and provenance
# Dependencies: pytest; no database or resident runtime
# Authority: No resident creation, review decision, persistence, or production access
# Changed: 2026-10-18 UTC | W3-JESSICA-CHARACTER-INTEGRATION-001 | Initial acceptance tests
# Contracts: docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================

import pytest

from riverview_core.jessica_character_architecture import (
    FORBIDDEN_ACTIONS,
    UNRESOLVED_IDENTITY_FIELDS,
    CharacterProposalError,
    JessicaRoleProfile,
    build_character_proposal,
    revise_character_proposal,
)


BOUNDARY = "advisory only; no resident creation, approval, authority grant, or production change"
EVIDENCE = [{
    "evidence_id": "source:c471-doctrine",
    "repository": "ppow1/Riverview",
    "commit": "eaade03a4632cb355df524a410b6ecb01a640e49",
    "path": "docs/architecture/resident_localization/jessica_character_architecture_professional_doctrine_v1.md",
    "claim": "Office doctrine describes evidence-based, non-sovereign character architecture advice.",
}]


def draft(**overrides):
    values = {
        "request_id": "request:isolated-1",
        "requester_id": "steward:test",
        "subject_resident_id": "resident:sample",
        "base_revision": 0,
        "objective": "Prepare an evidence-bounded character design proposal.",
        "scope": "Design recommendations only.",
        "proposed_approach": "Separate established facts from unknowns and present a reviewable proposal.",
        "constraints": [BOUNDARY],
        "acceptance_criteria": ["Every historical claim has exact source provenance."],
        "evidence": EVIDENCE,
        "claims": [{"text": "The office provides non-sovereign character architecture advice.",
                    "evidence_id": "source:c471-doctrine", "claim_kind": "historical_fact"}],
    }
    values.update(overrides)
    return build_character_proposal(**values)


def test_role_profile_is_advisory_inactive_and_personal_unknowns_stay_explicit():
    role = JessicaRoleProfile()
    assert role.principal_id == "resident:jessica"
    assert role.office == "Chief Character Architect"
    assert role.active is False
    assert role.authority == ()
    assert set(role.unresolved_identity) == set(UNRESOLVED_IDENTITY_FIELDS)
    assert "authority.grant" in FORBIDDEN_ACTIONS
    assert not hasattr(role, "execute")


def test_proposal_and_revision_are_provenance_bound_and_non_persistent():
    first = draft()
    second = revise_character_proposal(first, proposed_approach="Add an explicit unknowns section.")
    assert first.revision == 1
    assert second.revision == 2
    assert second.provenance["predecessor_revision"] == 1
    assert second.source_references == first.source_references
    assert second.status == "PROPOSED"
    assert second.provenance["advisory_only"] is True
    assert set(second.content) == {"title", "summary", "objective", "scope", "proposed_approach",
                                   "constraints", "acceptance_criteria", "tags"}


def test_missing_evidence_is_rejected_even_for_a_proposal_without_claims():
    with pytest.raises(CharacterProposalError, match="requires source evidence"):
        draft(evidence=[], claims=[])


def test_unsupported_historical_claim_and_identity_expansion_are_rejected():
    unsupported = [{"text": "Jessica has a detailed biography.", "evidence_id": "missing",
                    "claim_kind": "historical_fact"}]
    with pytest.raises(CharacterProposalError, match="no matching source evidence"):
        draft(claims=unsupported)
    with pytest.raises(CharacterProposalError, match="remain unresolved"):
        draft(unresolved_fields=["biography"])


def test_authority_boundary_cannot_be_omitted_or_revised_away():
    with pytest.raises(CharacterProposalError, match="mandatory authority boundary"):
        draft(constraints=[])
    first = draft()
    with pytest.raises(CharacterProposalError, match="mandatory authority boundary"):
        revise_character_proposal(first, constraints=["Jessica may approve the proposal."])
