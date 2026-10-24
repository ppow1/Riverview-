# Proposal-origin rework correction — 2026-10-24

## Authorization and scope

This backend change is authorized by the Steward's separate directive
“RIVERVIEW — REPAIR PROPOSAL-ORIGIN REWORK AND RESUME GRACE.” It is a separate
engineering change and does not amend or rely on the r2 experiment grant's
source-change scope. The change is limited to routing rejected assignments
from an exactly promoted proposal through Grace's existing bounded rework
review, and supplying the diagnostic worker with bounded, read-only evidence
from the authoritative objective/event store.

The change preserves the original objective, proposal, assignment, rejection,
independent verifier, and work-order lineage. It does not accept a rejected
artifact, modify the historical cancelled objective, modify the website, call
Luna, or change the standing experiment grant or budget.

## Durable scope and audit lineage

- Existing objective: `objective:proposal:e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2`
- Existing step: `s2`, assignment
  `assignment:grace:de19cd78b86f1889d32cdf02c6d3fe51d4658834:step:ad328846aa18b32a`
- Rejected attempt: `8069d968-310b-400d-925d-321eb0c47ec4`
- Independent verification: `5e6e295b-d45a-46e3-a186-96d14877b33c`
- Implementation, focused test results, immutable release identity, and live
  outcome are preserved in the Git commit that adds this record and the
  corresponding production deployment history.

## Acceptance and safety checks

1. Proposal-origin review is eligible only when exact proposal promotion
   evidence exists and the objective identity derives from its proposal ID and
   revision.
2. Rework decisions remain bounded by the unchanged assignment criteria and
   existing independent rejection.
3. Proposal-origin review receipts correlate to the deterministic review
   request ID and are append-only/idempotent.
4. Diagnostic runtime evidence is server-derived, read-only, size bounded,
   restricted to the assigned objective and literal historical objective IDs
   referenced by its request, and cannot write runtime state.
5. Independent verification remains mandatory; rejected artifacts remain
   rejected until a new attempt is independently verified.

## Live defect found during commissioning

The first release exposed the proposal-origin path but the live reviewer raised
`ValueError` before invoking its provider. The exact mismatch was that
`pending_rejected_work_order_reviews()` included the durable
`rework_attempt_count` field, while the review context contract did not allow
that field. The service then wrote `review_provider_unavailable` but did not
exclude that verification on the next polling cycle. The follow-up correction
accepts the bounded count as context and fences a failed review to one attempt
per immutable source release. A changed release can retry once; repeated
failures from the same release remain held. No reasoning recovery or Luna
request was consumed during this diagnosis.

