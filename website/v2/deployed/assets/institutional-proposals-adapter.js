// Revision: 1.1.0
/* View models for the existing authenticated institutional proposal API. */
(() => {
  "use strict";
  const value = (input) => typeof input === "string" && input.trim() ? input.trim() : null;
  const listItem = (item = {}) => Object.freeze({
    proposalId: value(item.proposal_id),
    title: value(item.title) || "Untitled proposal",
    status: value(item.lifecycle_status) || "Status unavailable",
    revision: Number.isInteger(item.current_revision) ? item.current_revision : null,
    summary: value(item.summary) || "No summary recorded.",
    updatedAt: value(item.updated_at),
    privacy: value(item.privacy_classification),
    tags: Array.isArray(item.tags) ? item.tags.filter((tag) => typeof tag === "string") : []
  });
  const detail = (response = {}) => {
    const proposal = response.proposal && typeof response.proposal === "object" ? response.proposal : {};
    const revision = response.revision && typeof response.revision === "object" ? response.revision : {};
    return Object.freeze({
      proposalId: value(proposal.proposal_id),
      status: value(revision.lifecycle_status) || value(proposal.lifecycle_status),
      revision: Number.isInteger(revision.revision) ? revision.revision : null,
      contentSha256: value(revision.content_sha256),
      title: value(revision.title) || "Proposal revision unavailable",
      summary: value(revision.summary),
      objective: value(revision.objective),
      scope: value(revision.scope),
      proposedApproach: value(revision.proposed_approach),
      constraints: value(revision.constraints),
      acceptanceCriteria: Array.isArray(revision.acceptance_criteria) ? revision.acceptance_criteria.filter((item) => typeof item === "string") : [],
      tags: Array.isArray(revision.tags) ? revision.tags.filter((item) => typeof item === "string") : [],
      sourceReferences: Array.isArray(revision.source_references) ? revision.source_references : [],
      createdAt: value(revision.created_at),
      reviews: Array.isArray(response.reviews) ? response.reviews.map((row) => ({
        outcome: value(row.review_outcome), office: value(row.reviewer_office),
        findings: value(row.findings), conditions: Array.isArray(row.conditions) ? row.conditions.filter((item) => typeof item === "string") : [],
        recordedAt: value(row.created_at)
      })) : [],
      workOrders: Array.isArray(response.work_order_links) ? response.work_order_links.map((row) => ({
        objectiveId: value(row.objective_id), objectiveStatus: value(row.objective_status),
        assignmentId: value(row.assignment_id), linkedAt: value(row.linked_at)
      })) : [],
      events: Array.isArray(response.events) ? response.events.map((row) => ({
        type: value(row.event_type), revision: Number.isInteger(row.revision) ? row.revision : null,
        occurredAt: value(row.occurred_at)
      })) : []
    });
  };
  window.RiverviewV2ProposalAdapter = Object.freeze({listItem, detail});
})();
