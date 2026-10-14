-- File Revision: 1.0.0
-- Task: RV-GRACE-HEALTH-PROJECTION-ACL-001
-- Purpose: Permit the dashboard runtime to read only Grace execution health.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'riverview_core') THEN
        EXECUTE format('GRANT SELECT ON %I.grace_execution_health TO riverview_core',
                       current_schema());
    END IF;
END;
$$;
