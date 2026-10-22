-- Permit grounding receipts to supply their correlated event identity.
-- Keep all other event-history columns at their existing narrow grants.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'riverview_core') THEN
        EXECUTE format(
            'GRANT INSERT (event_id) ON %I.grace_objective_events TO riverview_core',
            current_schema());
    END IF;
END;
$$;
