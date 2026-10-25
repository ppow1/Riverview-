-- RV-GRACE-ASSIGNMENT-EVIDENCE-HANDOFF-20261025
-- Persist the action-specific runtime evidence gate as a first-class wait cause.
ALTER TABLE knowledge_observations
    DROP CONSTRAINT knowledge_observations_operation_check;

ALTER TABLE knowledge_observations
    ADD CONSTRAINT knowledge_observations_operation_check
    CHECK (operation IN (
        'ground_assignment',
        'preflight_action',
        'preflight_assignment_evidence',
        'reground_assignment',
        'record_learning'
    ));
