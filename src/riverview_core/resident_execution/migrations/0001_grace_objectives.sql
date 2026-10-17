-- File Revision: 1.0.0
-- Controlled migration: durable Grace objective and proposal provenance.
CREATE TABLE grace_objectives (
    objective_id TEXT PRIMARY KEY,
    request TEXT NOT NULL CHECK (length(request) BETWEEN 1 AND 4000),
    scope_ref TEXT NOT NULL,
    submitter_id TEXT NOT NULL,
    acceptance_criteria JSONB NOT NULL CHECK (jsonb_typeof(acceptance_criteria) = 'array'),
    status TEXT NOT NULL CHECK (status IN ('RECEIVED','WAITING_FOR_EVIDENCE','GROUNDED','PROPOSED','WORK_ORDER_CREATED','COMPLETED','FAILED','CANCELLED')),
    evidence JSONB,
    proposal JSONB,
    assignment_id TEXT UNIQUE,
    source_revision TEXT,
    source_sha256 TEXT,
    revision BIGINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE grace_objective_events (
    sequence BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    objective_id TEXT NOT NULL REFERENCES grace_objectives(objective_id),
    event_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    actor_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX grace_objective_events_by_objective
    ON grace_objective_events(objective_id, sequence);
