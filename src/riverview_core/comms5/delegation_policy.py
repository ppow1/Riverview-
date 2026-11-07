# Revision: 1.0.0
"""Versioned allowlist for operations covered by a Riverview-wide grant.

Keep this list explicit. In particular, tool catalog annotations are not
runtime authorization policy. A new or renamed tool requires an explicit
classification here and parity-test update.
"""

NON_DESTRUCTIVE_DELEGATED_TOOLS = frozenset({
    "comms5_contract_info", "comms5_help", "comms5_capabilities",
    "comms5_describe_operation", "comms5_examples",
    "comms5_submit_steward_seed", "comms5_store_specification",
    "comms5_seed_status", "comms5_seed_lineage", "comms5_objective_status",
    "comms5_cme_status", "comms5_recent_steward_submissions",
    "comms5_transport_probe", "comms5_resource_policy_status",
    "comms5_set_resource_policy", "comms5_set_resource_policy_lock",
    "comms5_confirm_and_promote_seed", "comms5_form_and_queue_work",
    "comms5_revalidate_and_queue_work", "comms5_submit_direct_engineering_task",
    "comms5_cancel_draft",
    "comms5_supersede_seed", "comms5_revise_specification",
    "comms5_prepare_proposal_for_decision",
    "reasoning_exchange_list_requests", "reasoning_exchange_claim_request",
    "reasoning_exchange_submit_response", "reasoning_exchange_status",
    "comms5_authorize_grace_experiment", "comms5_amend_grace_experiment",
    "comms5_authorize_grace_supervision", "comms5_grace_supervision_status",
    "comms5_request_delegation_grant", "comms5_get_delegation_grant_status",
    "comms5_request_delegation_grant_change",
})

DESTRUCTIVE_OR_REVOCATION_TOOLS = frozenset({
    "comms5_revoke_grace_supervision", "comms5_revoke_delegation_grant",
})

DELEGATED_ACTION = "comms5.operations.non_destructive.v1"
DELEGATED_POLICY = "policy:delegation.v1"
DELEGATED_PROJECT_SCOPE = "project:Riverview"


def is_delegable_tool(tool: str) -> bool:
    return tool in NON_DESTRUCTIVE_DELEGATED_TOOLS and tool not in DESTRUCTIVE_OR_REVOCATION_TOOLS
