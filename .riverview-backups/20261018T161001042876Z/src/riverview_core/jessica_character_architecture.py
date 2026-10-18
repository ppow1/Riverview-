# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/jessica_character_architecture.py
# Component: JESSICA-CHARACTER-ARCHITECTURE
# Revision: 1.0.3
# Purpose: Build evidence-gated, non-persistent character proposal packages
# Execution Model: Request-driven pure library
# Observability: Returned package includes request, evidence and revision provenance
# Dependencies: INSTITUTIONAL-PROPOSALS ProposalContent contract (serialization only)
# Authority: Advisory role only; cannot create residents, approve proposals or change production
# Changed: 2026-10-18 UTC | W3-DORMANT-JESSICA-AUTHORSHIP-001 | Normalize malformed actor labels to permission denial
# Contracts: docs/architecture/JESSICA_CHARACTER_ARCHITECTURE_RECOVERY.md
# Tests: tests/test_jessica_character_architecture.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Evidence-gated Jessica design proposals, without persistence or authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ROLE_ID = "resident:jessica"
OFFICE = "Chief Character Architect"
HISTORICAL_SOURCE = {
    "repository": "ppow1/Riverview",
    "commit": "eaade03a4632cb355df524a410b6ecb01a640e49",
    "path": "docs/architecture/resident_localization/jessica_character_architecture_professional_doctrine_v1.md",
}
UNRESOLVED_IDENTITY_FIELDS = (
    "biography", "backstory", "surname", "appearance", "visual_identity",
    "expanded_personality", "personal_history", "original_memories",
)
FORBIDDEN_ACTIONS = frozenset({
    "resident.create", "resident.activate", "character.approve",
    "authority.grant", "engineering.execute", "production.change",
})


class CharacterProposalError(ValueError):
    """A request lacks evidence or crosses Jessica's advisory boundary."""


@dataclass(frozen=True)
class JessicaRoleProfile:
    """Office responsibilities are historical; personal canon stays unresolved."""

    principal_id: str = ROLE_ID
    office: str = OFFICE
    active: bool = False
    responsibilities: tuple[str, ...] = (
        "resident identity and continuity design",
        "character traits, behavioral boundaries, and developmental arcs",
        "intelligence profiles, skill domains, relationships, and collaboration patterns",
        "character briefs, continuity notes, and coherence review for new characters",
        "advisory recommendations on cognition, models, prompts, memory, and implementation",
        "bounded work-package decomposition and evidence-based critique",
    )
    authority: tuple[str, ...] = ()
    unresolved_identity: tuple[str, ...] = UNRESOLVED_IDENTITY_FIELDS
    historical_source: dict[str, str] | None = None

    def __post_init__(self):
        if self.historical_source is None:
            object.__setattr__(self, "historical_source", dict(HISTORICAL_SOURCE))


@dataclass(frozen=True)
class CharacterProposalPackage:
    """One local proposal revision; downstream persistence/review is external."""

    request_id: str
    subject_resident_id: str
    base_revision: int
    revision: int
    content: dict[str, Any]
    source_references: tuple[dict[str, str], ...]
    provenance: dict[str, Any]
    status: str = "PROPOSED"


def _required_text(value, field, limit=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise CharacterProposalError(f"invalid {field}")
    return value.strip()


def _validate_sources(sources):
    if not isinstance(sources, (list, tuple)) or not sources:
        raise CharacterProposalError("proposal requires source evidence")
    result = []
    ids = set()
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"evidence_id", "repository", "commit", "path", "claim"}:
            raise CharacterProposalError("evidence must identify its claim and exact provenance")
        packed = {key: _required_text(value, f"evidence {key}", 2000) for key, value in source.items()}
        if packed["evidence_id"] in ids:
            raise CharacterProposalError("duplicate evidence id")
        ids.add(packed["evidence_id"])
        result.append(packed)
    return tuple(result)


def build_character_proposal(*, request_id, requester_id, subject_resident_id,
                              base_revision, objective, scope, proposed_approach,
                              constraints, acceptance_criteria, evidence, claims=(),
                              unresolved_fields=()):
    """Prepare a registry-compatible proposal document, without writing records.

    Claims are strings with evidence IDs. Historical claims must cite a provided
    source. Identity fields known to be unresolved cannot be filled by this adapter.
    """
    request_id = _required_text(request_id, "request id", 240)
    requester_id = _required_text(requester_id, "requester id", 256)
    subject_resident_id = _required_text(subject_resident_id, "subject resident id", 256)
    if not isinstance(base_revision, int) or isinstance(base_revision, bool) or base_revision < 0:
        raise CharacterProposalError("base revision must be a nonnegative integer")
    objective = _required_text(objective, "objective", 4000)
    scope = _required_text(scope, "scope", 4000)
    proposed_approach = _required_text(proposed_approach, "proposed approach", 6000)
    if not isinstance(constraints, (list, tuple)) or not constraints:
        raise CharacterProposalError("proposal omits Jessica's mandatory authority boundary")
    constraints = tuple(_required_text(v, "constraint") for v in constraints)
    required_boundary = "advisory only; no resident creation, approval, authority grant, or production change"
    if required_boundary not in constraints:
        raise CharacterProposalError("proposal omits Jessica's mandatory authority boundary")
    if not isinstance(acceptance_criteria, (list, tuple)) or not acceptance_criteria:
        raise CharacterProposalError("acceptance criteria are required")
    acceptance_criteria = tuple(_required_text(v, "acceptance criterion") for v in acceptance_criteria)
    sources = _validate_sources(evidence)
    evidence_ids = {source["evidence_id"] for source in sources}

    if not isinstance(claims, (list, tuple)):
        raise CharacterProposalError("claims must be a list")
    normalized_claims = []
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"text", "evidence_id", "claim_kind"}:
            raise CharacterProposalError("claims require text, evidence_id, and claim_kind")
        text = _required_text(claim["text"], "claim", 1000)
        evidence_id = _required_text(claim["evidence_id"], "claim evidence id", 200)
        kind = _required_text(claim["claim_kind"], "claim kind", 40)
        if kind not in {"historical_fact", "design_inference", "proposed_change"}:
            raise CharacterProposalError("unsupported claim kind")
        if evidence_id not in evidence_ids:
            raise CharacterProposalError("claim has no matching source evidence")
        source = next(item for item in sources if item["evidence_id"] == evidence_id)
        if text != source["claim"]:
            raise CharacterProposalError("claim text is not supported by the cited evidence record")
        normalized_claims.append({"text": text, "evidence_id": evidence_id, "claim_kind": kind})

    if not isinstance(unresolved_fields, (list, tuple)):
        raise CharacterProposalError("unresolved fields must be a list")
    unresolved = tuple(dict.fromkeys(_required_text(field, "unresolved field", 120)
                                     for field in unresolved_fields))
    if set(unresolved) - set(UNRESOLVED_IDENTITY_FIELDS):
        raise CharacterProposalError("unknown unresolved identity field")
    if unresolved:
        raise CharacterProposalError("unresolved identity fields must remain unresolved, not enter a proposal as facts")

    content = {
        "title": f"Character design proposal: {subject_resident_id}",
        "summary": objective,
        "objective": objective,
        "scope": scope,
        "proposed_approach": proposed_approach,
        "constraints": list(constraints),
        "acceptance_criteria": list(acceptance_criteria),
        "tags": ["character-design", "jessica-advisory"],
    }
    return CharacterProposalPackage(
        request_id=request_id,
        subject_resident_id=subject_resident_id,
        base_revision=base_revision,
        revision=base_revision + 1,
        content=content,
        source_references=sources,
        provenance={
            "producer": ROLE_ID,
            "office": OFFICE,
            "requester_id": requester_id,
            "request_id": request_id,
            "claims": normalized_claims,
            "advisory_only": True,
            "persistence": "caller-controlled existing proposal registry only",
        },
    )


def revise_character_proposal(previous, **changes):
    """Build a successor revision while retaining predecessor evidence context."""
    if not isinstance(previous, CharacterProposalPackage):
        raise CharacterProposalError("previous proposal package is required")
    allowed = {"objective", "scope", "proposed_approach", "constraints", "acceptance_criteria", "evidence", "claims", "unresolved_fields"}
    if set(changes) - allowed:
        raise CharacterProposalError("unsupported revision fields")
    args = {
        "request_id": previous.request_id,
        "requester_id": previous.provenance["requester_id"],
        "subject_resident_id": previous.subject_resident_id,
        "base_revision": previous.revision,
        "objective": previous.content["objective"],
        "scope": previous.content["scope"],
        "proposed_approach": previous.content["proposed_approach"],
        "constraints": previous.content["constraints"],
        "acceptance_criteria": previous.content["acceptance_criteria"],
        "evidence": list(previous.source_references),
        "claims": previous.provenance["claims"],
    }
    args.update(changes)
    successor = build_character_proposal(**args)
    return CharacterProposalPackage(**{
        **successor.__dict__,
        "provenance": {**successor.provenance, "predecessor_revision": previous.revision},
    })


def create_advisory_import_draft(registry, package, *, authenticated_steward_id,
                                idempotency_key):
    """Persist this package as a draft through the existing registry contract.

    The principal must come from an already authenticated Steward transport, as
    with Comms5Operations. Jessica is recorded as advisory producer, never as the
    authenticated actor. This helper adds no endpoint, grant, approval, or route.
    """
    if not isinstance(package, CharacterProposalPackage):
        raise CharacterProposalError("character proposal package required")
    if (not isinstance(authenticated_steward_id, str)
            or not authenticated_steward_id.strip()
            or len(authenticated_steward_id) > 256):
        raise PermissionError("authenticated Steward principal required")
    principal = authenticated_steward_id.strip()
    if not principal.startswith("steward:") or not principal[len("steward:"):].strip():
        raise PermissionError("authenticated Steward principal required")
    idempotency_key = _required_text(idempotency_key, "idempotency key", 240)
    provenance = {
        **package.provenance,
        "advisory_producer": ROLE_ID,
        "authenticated_actor": principal,
        "authoring_mode": "steward_attested_advisory_import",
        "proposal_package_revision": package.revision,
        "proposal_base_revision": package.base_revision,
    }
    return registry.create_draft(
        package.content,
        created_by=principal,
        origin_kind="authorized_import",
        source_references=list(package.source_references),
        provenance=provenance,
        idempotency_key=idempotency_key,
    )
