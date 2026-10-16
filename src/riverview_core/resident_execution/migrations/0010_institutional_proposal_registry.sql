-- File Revision: 1.0.0
-- Component: INSTITUTIONAL-PROPOSALS
-- Task: RV-INSTITUTIONAL-PROPOSAL-LIFECYCLE-001
-- Purpose: Add append-oriented proposal revisions, lifecycle, reviews and work links.
-- Authority: Proposal persistence never authorizes objective or assignment execution.
-- Rollback: Preserve records; disable proposal API and retain additive tables for review.

CREATE TABLE institutional_proposals (
    proposal_id TEXT PRIMARY KEY CHECK (proposal_id ~ '^proposal:[0-9a-f-]{36}$'),
    created_by TEXT NOT NULL CHECK (length(created_by) BETWEEN 1 AND 256),
    origin_kind TEXT NOT NULL CHECK (origin_kind IN
        ('grace_conversation','steward_authored','authorized_import')),
    privacy_classification TEXT NOT NULL CHECK (privacy_classification IN
        ('institutional','confidential','restricted','local_only')),
    retention_policy TEXT NOT NULL CHECK (retention_policy IN
        ('standard','minimum_required','ephemeral')),
    retention_until TIMESTAMPTZ,
    current_revision INTEGER NOT NULL CHECK (current_revision >= 1),
    lifecycle_status TEXT NOT NULL CHECK (lifecycle_status IN
        ('DRAFT','READY_FOR_REVIEW','UNDER_REVIEW','CHANGES_REQUIRED',
         'READY_FOR_STEWARD_DECISION','APPROVED','DEFERRED','REJECTED',
         'SUPERSEDED','ARCHIVED')),
    content_sha256 TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    idempotency_key TEXT UNIQUE CHECK (idempotency_key IS NULL OR length(idempotency_key) BETWEEN 1 AND 240),
    idempotency_request_sha256 TEXT CHECK (idempotency_request_sha256 IS NULL OR idempotency_request_sha256 ~ '^[0-9a-f]{64}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((retention_policy='standard' AND retention_until IS NULL) OR
           (retention_policy<>'standard' AND retention_until IS NOT NULL)),
    CHECK ((idempotency_key IS NULL AND idempotency_request_sha256 IS NULL) OR
           (idempotency_key IS NOT NULL AND idempotency_request_sha256 IS NOT NULL))
);

CREATE TABLE institutional_proposal_revisions (
    proposal_id TEXT NOT NULL REFERENCES institutional_proposals(proposal_id),
    revision INTEGER NOT NULL CHECK (revision >= 1),
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 200),
    summary TEXT NOT NULL CHECK (length(summary) BETWEEN 1 AND 1000),
    objective TEXT NOT NULL CHECK (length(objective) BETWEEN 1 AND 4000),
    scope TEXT NOT NULL CHECK (length(scope) BETWEEN 1 AND 4000),
    proposed_approach TEXT NOT NULL CHECK (length(proposed_approach) BETWEEN 1 AND 6000),
    constraints JSONB NOT NULL CHECK (jsonb_typeof(constraints)='array'),
    acceptance_criteria JSONB NOT NULL CHECK (jsonb_typeof(acceptance_criteria)='array'),
    tags TEXT[] NOT NULL DEFAULT '{}',
    source_references JSONB NOT NULL CHECK (jsonb_typeof(source_references)='array'),
    provenance JSONB NOT NULL CHECK (jsonb_typeof(provenance)='object'),
    created_by TEXT NOT NULL CHECK (length(created_by) BETWEEN 1 AND 256),
    lifecycle_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (lifecycle_status IN
        ('DRAFT','READY_FOR_REVIEW','UNDER_REVIEW','CHANGES_REQUIRED',
         'READY_FOR_STEWARD_DECISION','APPROVED','DEFERRED','REJECTED',
         'SUPERSEDED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    search_document TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', title || ' ' || summary || ' ' || objective || ' ' ||
            scope || ' ' || proposed_approach) ||
        jsonb_to_tsvector('simple', constraints, '["string"]'::jsonb) ||
        jsonb_to_tsvector('simple', acceptance_criteria, '["string"]'::jsonb)
    ) STORED,
    PRIMARY KEY (proposal_id,revision)
);

CREATE INDEX institutional_proposal_search_gin
    ON institutional_proposal_revisions USING GIN(search_document);
CREATE INDEX institutional_proposal_tags_gin
    ON institutional_proposal_revisions USING GIN(tags);
CREATE INDEX institutional_proposal_current_status
    ON institutional_proposals(lifecycle_status,updated_at DESC);

CREATE TABLE institutional_proposal_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id TEXT NOT NULL REFERENCES institutional_proposals(proposal_id),
    revision INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK (length(event_type) BETWEEN 1 AND 80),
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 240),
    actor_id TEXT NOT NULL CHECK (length(actor_id) BETWEEN 1 AND 256),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload)='object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (proposal_id,revision)
        REFERENCES institutional_proposal_revisions(proposal_id,revision)
);
CREATE INDEX institutional_proposal_events_history
    ON institutional_proposal_events(proposal_id,occurred_at,event_id);

CREATE TABLE institutional_proposal_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    reviewer_office TEXT NOT NULL CHECK (length(reviewer_office) BETWEEN 1 AND 256),
    reviewer_principal TEXT NOT NULL CHECK (length(reviewer_principal) BETWEEN 1 AND 256),
    review_outcome TEXT NOT NULL CHECK (review_outcome IN
        ('NO_OBJECTION','APPROVED_WITH_CONDITIONS','CHANGES_REQUIRED','BLOCKED','INSUFFICIENT_EVIDENCE')),
    findings TEXT NOT NULL CHECK (length(findings) BETWEEN 1 AND 4000),
    conditions JSONB NOT NULL CHECK (jsonb_typeof(conditions)='array'),
    evidence_references JSONB NOT NULL CHECK (jsonb_typeof(evidence_references)='array'),
    authority_reference TEXT NOT NULL CHECK (length(authority_reference) BETWEEN 1 AND 256),
    idempotency_key TEXT NOT NULL UNIQUE CHECK (length(idempotency_key) BETWEEN 1 AND 240),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (proposal_id,revision)
        REFERENCES institutional_proposal_revisions(proposal_id,revision)
);
CREATE INDEX institutional_proposal_reviews_revision
    ON institutional_proposal_reviews(proposal_id,revision,created_at);

CREATE TABLE institutional_proposal_work_orders (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id TEXT NOT NULL,
    proposal_revision INTEGER NOT NULL,
    objective_id TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    approved_purpose TEXT NOT NULL CHECK (length(approved_purpose) BETWEEN 1 AND 1000),
    linked_by TEXT NOT NULL CHECK (length(linked_by) BETWEEN 1 AND 256),
    authority_reference TEXT NOT NULL CHECK (length(authority_reference) BETWEEN 1 AND 256),
    linked_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (proposal_id,proposal_revision)
        REFERENCES institutional_proposal_revisions(proposal_id,revision),
    UNIQUE (proposal_id,proposal_revision,objective_id,assignment_id)
);
CREATE INDEX institutional_proposal_work_order_lookup
    ON institutional_proposal_work_orders(objective_id,assignment_id);

DO $$
DECLARE runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=runtime_role) THEN
        EXECUTE format('GRANT SELECT,INSERT ON %I.institutional_proposals TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT UPDATE (current_revision,lifecycle_status,content_sha256,updated_at) ON %I.institutional_proposals TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT SELECT,INSERT ON %I.institutional_proposal_revisions TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT UPDATE (lifecycle_status) ON %I.institutional_proposal_revisions TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT SELECT,INSERT ON %I.institutional_proposal_events TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT SELECT,INSERT ON %I.institutional_proposal_reviews TO %I',current_schema(),runtime_role);
        EXECUTE format('GRANT SELECT,INSERT ON %I.institutional_proposal_work_orders TO %I',current_schema(),runtime_role);
    END IF;
END;
$$;
