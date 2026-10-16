-- File Revision: 1.0.0
-- Controlled migration: durable, dependency-aware Engineering step assignments.
-- Predecessor state is preserved in the Grace objective/event tables.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint
        WHERE conrelid='grace_objectives'::regclass
          AND conname='grace_objectives_assignment_id_key') THEN
        ALTER TABLE grace_objectives DROP CONSTRAINT grace_objectives_assignment_id_key;
    END IF;
END $$;

CREATE TABLE grace_objective_steps (
    objective_id TEXT NOT NULL REFERENCES grace_objectives(objective_id),
    step_id TEXT NOT NULL,
    step_order INTEGER NOT NULL CHECK (step_order BETWEEN 1 AND 20),
    step_objective TEXT NOT NULL CHECK (length(step_objective) BETWEEN 1 AND 2000),
    acceptance_criteria JSONB NOT NULL CHECK (jsonb_typeof(acceptance_criteria)='array'),
    depends_on JSONB NOT NULL CHECK (jsonb_typeof(depends_on)='array'),
    status TEXT NOT NULL CHECK (status IN ('pending','assigned','verified','blocked')),
    assignment_id TEXT UNIQUE,
    dispatch_count INTEGER NOT NULL DEFAULT 0 CHECK (dispatch_count >= 0),
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (objective_id,step_id),
    UNIQUE (objective_id,step_order)
);
CREATE INDEX grace_objective_steps_ready
    ON grace_objective_steps(objective_id,step_order) WHERE status='pending';

-- Preserve already-proposed single-step objectives when the additive migration
-- is installed. A completed predecessor remains historically completed.
INSERT INTO grace_objective_steps
    (objective_id,step_id,step_order,step_objective,acceptance_criteria,
     depends_on,status,assignment_id,dispatch_count,verified_at)
SELECT o.objective_id, s.value->>'step_id', s.ordinality::integer,
       s.value->>'objective', s.value->'acceptance_criteria',
       COALESCE(s.value->'depends_on','[]'::jsonb),
       CASE WHEN o.status='COMPLETED' THEN 'verified'
            WHEN o.assignment_id IS NOT NULL THEN 'assigned'
            ELSE 'pending' END,
       CASE WHEN s.ordinality=1 THEN o.assignment_id ELSE NULL END,
       CASE WHEN o.assignment_id IS NOT NULL AND s.ordinality=1 THEN 1 ELSE 0 END,
       CASE WHEN o.status='COMPLETED' THEN o.updated_at ELSE NULL END
FROM grace_objectives o
CROSS JOIN LATERAL jsonb_array_elements(COALESCE(o.proposal->'steps','[]'::jsonb))
    WITH ORDINALITY AS s(value,ordinality)
WHERE o.proposal IS NOT NULL
ON CONFLICT (objective_id,step_id) DO NOTHING;

UPDATE grace_objective_events e SET payload=e.payload || jsonb_build_object(
    'completion_cycle', COALESCE((SELECT max(s.step_order)
        FROM grace_objective_steps s WHERE s.objective_id=e.objective_id),1))
WHERE e.event_type='objective.completed'
  AND jsonb_typeof(e.payload)='object'
  AND NOT e.payload ? 'completion_cycle';

-- The persistent worker uses this restricted runtime role. Grant only the
-- columns needed to persist, claim, and verify steps; no delete or table-wide
-- privileges are required. This migration remains unapplied in production.
DO $$
DECLARE
    runtime_role TEXT := 'riverview_core';
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = runtime_role) THEN
        EXECUTE format(
            'GRANT SELECT (objective_id, step_id, step_order, step_objective, acceptance_criteria, depends_on, status, assignment_id, dispatch_count, verified_at, created_at, updated_at), INSERT (objective_id, step_id, step_order, step_objective, acceptance_criteria, depends_on, status), UPDATE (status, assignment_id, dispatch_count, verified_at, updated_at) ON %I.grace_objective_steps TO %I',
            current_schema(), runtime_role);
    END IF;
END;
$$;
