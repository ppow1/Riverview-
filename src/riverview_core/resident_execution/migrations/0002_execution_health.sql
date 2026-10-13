-- File Revision: 1.0.0
-- Task: RV-M4.4-PERSISTENT-EXECUTION
-- Purpose: Persist Grace execution-service heartbeat and last-cycle outcome.
CREATE TABLE grace_execution_health (
    service_id TEXT PRIMARY KEY CHECK (service_id = 'grace.execution.v1'),
    instance_id UUID NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('starting','healthy','degraded','stopping')),
    last_heartbeat_at TIMESTAMPTZ NOT NULL,
    last_cycle_at TIMESTAMPTZ,
    last_error_type TEXT,
    cycles_completed BIGINT NOT NULL DEFAULT 0 CHECK (cycles_completed >= 0)
);
