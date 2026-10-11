-- File Revision: 1.0.0
-- Task: RV-M4.4-PERSISTENT-EXECUTION
-- Purpose: Record the terminal retry-ceiling outcome for safe interrupted work.
ALTER TABLE worker_recovery_records
    DROP CONSTRAINT worker_recovery_records_decision_check;
ALTER TABLE worker_recovery_records
    ADD CONSTRAINT worker_recovery_records_decision_check
    CHECK (decision IN ('retry_safe','retry_exhausted','outcome_unknown','result_preserved'));
