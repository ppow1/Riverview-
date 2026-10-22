-- File Revision: 1.0.0
-- Add only the event identity column needed by the objective event-history read.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'riverview_core') THEN
        EXECUTE format(
            'GRANT SELECT (event_id) ON %I.grace_objective_events TO riverview_core',
            current_schema());
    END IF;
END;
$$;
