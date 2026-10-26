# File Revision: 1.0.0
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from riverview_core.institutional_authority.registry import (
    AuthorityRegistry,
    grant_expiry_at,
    normalize_grant_duration,
)
from riverview_core.comms5.server import _TOOLS, _valid
from riverview_core.institutional_authority.comms5_adapter import (
    Comms5DelegationAuthorityAdapter,
)
from riverview_core.resident_execution.comms5_operations import Comms5Operations


@pytest.mark.parametrize(("spec", "seconds"), [
    ({"unit": "minutes", "value": 30}, 1800),
    ({"unit": "hours", "value": 2}, 7200),
    ({"unit": "days", "value": 7}, 604800),
    ({"unit": "weeks", "value": 2}, 1209600),
    ({"unit": "custom", "seconds": 90}, 90),
])
def test_fixed_duration_units_are_exact(spec, seconds):
    start = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    assert (grant_expiry_at(start, spec) - start).total_seconds() == seconds


@pytest.mark.parametrize(("spec", "expected"), [
    ({"unit": "months", "value": 1}, datetime(2024, 2, 29, 12, tzinfo=timezone.utc)),
    ({"unit": "quarters", "value": 1}, datetime(2024, 4, 30, 12, tzinfo=timezone.utc)),
    ({"unit": "years", "value": 1}, datetime(2025, 1, 31, 12, tzinfo=timezone.utc)),
])
def test_calendar_durations_clamp_to_last_valid_day(spec, expected):
    start = datetime(2024, 1, 31, 12, 0, tzinfo=timezone.utc)
    assert grant_expiry_at(start, spec) == expected


def test_calendar_year_from_leap_day_clamps_to_february_end():
    start = datetime(2024, 2, 29, 12, 0, tzinfo=timezone.utc)
    assert grant_expiry_at(start, {"unit": "years", "value": 1}) == datetime(
        2025, 2, 28, 12, 0, tzinfo=timezone.utc)


def test_indefinite_duration_has_no_expiry_and_one_time_count_is_supported():
    assert grant_expiry_at(datetime.now(timezone.utc), {"unit": "indefinite"}) is None
    AuthorityRegistry._validate_delegated_grant_values(
        "steward:camrui", "comms5.proposal.promote", "project:Riverview",
        proposal_ref="request:one-time", proposal_digest="a" * 64,
        approval_ref="steward:approval:one-time", policy_ref="policy:delegation.v1",
        max_uses=1, valid_until=None, duration_spec={"unit": "indefinite"})


@pytest.mark.parametrize("spec", [
    {"unit": "minutes", "value": 0},
    {"unit": "months", "value": True},
    {"unit": "unsupported", "value": 1},
    {"unit": "custom", "seconds": -1},
    {"unit": "indefinite", "value": 1},
])
def test_duration_rejects_unbounded_or_ambiguous_values(spec):
    with pytest.raises(ValueError):
        normalize_grant_duration(spec)


def test_broad_comms5_action_no_longer_has_special_24_hour_expiry():
    source = Path("src/riverview_core/institutional_authority/registry.py").read_text()
    assert "expires_24h_after_activation" not in source
    assert "grant_expiry_at(activation_time, duration_spec)" in source


def test_contract_examples_and_openapi_cover_lifecycle():
    root = Path("docs/delegation-grants")
    examples = json.loads((root / "examples.json").read_text())
    required = {
        "one_time", "fixed_count", "unlimited_count", "time_limited",
        "combined_count_and_time", "indefinite", "calendar_duration",
        "custom_duration", "request", "approve", "deny", "inspect",
        "extend", "upgrade", "extend_and_upgrade", "revoke", "surrender",
        "host_scoped_command_caller", "host_scoped_command_execution",
    }
    assert required <= set(examples)
    openapi_doc = json.loads((root / "openapi.json").read_text())
    openapi = json.dumps(openapi_doc)
    for operation in ("requestGrant", "decideGrantRequest", "inspectGrant",
                      "requestGrantChange", "revokeGrant", "surrenderGrant"):
        assert operation in openapi
    for key in ("request", "inspect", "extend", "upgrade", "extend_and_upgrade", "surrender",
                "host_scoped_command_caller", "host_scoped_command_execution"):
        call = examples[key]
        tool = call["params"]["name"]
        assert _valid(_TOOLS[tool]["inputSchema"], call["params"]["arguments"])
    for key in ("one_time", "fixed_count", "unlimited_count", "time_limited",
                "combined_count_and_time", "indefinite", "custom_duration"):
        call = examples[key]
        assert _valid(_TOOLS[call["params"]["name"]]["inputSchema"],
                      call["params"]["arguments"])
    for call in examples["calendar_duration"].values():
        assert _valid(_TOOLS[call["params"]["name"]]["inputSchema"],
                      call["params"]["arguments"])


def test_comms5_operation_layer_enforces_duration_and_count_bounds():
    valid = [
        {"unit": "minutes", "value": 30}, {"unit": "hours", "value": 2},
        {"unit": "days", "value": 7}, {"unit": "weeks", "value": 1},
        {"unit": "months", "value": 1}, {"unit": "quarters", "value": 1},
        {"unit": "years", "value": 1}, {"unit": "custom", "seconds": 90},
        {"unit": "indefinite"},
    ]
    for duration in valid:
        assert Comms5Operations._delegation_validity(
            {"duration_spec": duration})[2] == duration
    for duration in ({"unit": "minutes", "value": 52560001},
                     {"unit": "years", "value": 101},
                     {"unit": "custom", "seconds": 0}):
        with pytest.raises(ValueError):
            Comms5Operations._delegation_validity({"duration_spec": duration})
    with pytest.raises(ValueError):
        Comms5Operations._delegation_validity({"max_uses": 1_000_001})


def test_protected_comms5_adapter_forwards_typed_grant_lifecycle_only():
    class Registry:
        def request_grant(self, **values):
            self.grant = values
            return {"status": "pending"}

        def request_change(self, **values):
            self.change = values
            return {"status": "pending"}

    adapter = object.__new__(Comms5DelegationAuthorityAdapter)
    adapter._registry = Registry()
    duration = {"unit": "days", "value": 7}
    adapter.request_grant(
        requester_id="steward:camrui", principal_id="steward:camrui",
        action="comms5.operations.non_destructive.v1", scope_ref="project:Riverview",
        policy_ref="policy:delegation.v1", request_ref="issue:343",
        max_uses=None, duration_spec=duration, idempotency_key="issue343-grant")
    assert adapter._registry.grant["duration_spec"] == duration
    assert adapter._registry.grant["max_uses"] is None
    adapter.request_change(
        requester_id="steward:camrui", grant_id="grant:source",
        action="comms5.proposal.promote", scope_ref="project:Riverview",
        policy_ref="policy:delegation.v1", request_ref="issue:343-extension",
        duration_spec={"unit": "weeks", "value": 1}, change_kind="extend",
        idempotency_key="issue343-extension")
    assert adapter._registry.change["duration_spec"] == {"unit": "weeks", "value": 1}
    assert adapter._registry.change["change_kind"] == "extend"
    assert "max_uses" not in adapter._registry.change
    assert "valid_until" not in adapter._registry.change


def test_comms5_adapter_allows_only_exact_command_gateway_host_grants():
    from riverview_core.institutional_authority import AuthorityDenied

    class Registry:
        def request_grant(self, **values):
            self.grant = values
            return {"status": "pending"}

    registry = Registry()
    adapter = object.__new__(Comms5DelegationAuthorityAdapter)
    adapter._registry = registry
    pairs = [
        ("comms5.command.submit.powershell_identity", "host:desktop-ja3rpnq",
         "steward:camrui"),
        ("comms5.command.execute.readonly.powershell_identity.standard",
         "host:desktop-ja3rpnq", "service:command-gateway"),
        ("comms5.command.submit.ssh_camrui_hostname", "host:camrui",
         "steward:camrui"),
        ("comms5.command.execute.readonly.ssh_camrui_hostname.standard",
         "host:camrui", "service:command-gateway"),
    ]
    for index, (action, scope, principal) in enumerate(pairs):
        adapter.request_grant(
            requester_id="steward:camrui", principal_id=principal,
            action=action, scope_ref=scope, policy_ref="policy:delegation.v1",
            request_ref="bounded Command Gateway grant fixture",
            max_uses=1 if action.startswith("comms5.command.execute.") else None,
            duration_spec={"unit": "days", "value": 7},
            idempotency_key=f"command-host-request-{index}")
        assert registry.grant["action"] == action
        assert registry.grant["scope_ref"] == scope

    with pytest.raises(AuthorityDenied):
        adapter.request_grant(
            requester_id="steward:camrui", principal_id="service:command-gateway",
            action="comms5.command.execute.readonly.powershell_identity.standard",
            scope_ref="host:camrui", policy_ref="policy:delegation.v1",
            request_ref="wrong action-host binding", max_uses=1,
            duration_spec={"unit": "days", "value": 7},
            idempotency_key="command-host-request-wrong-host")
    with pytest.raises(AuthorityDenied):
        adapter.request_grant(
            requester_id="steward:camrui", principal_id="service:command-gateway",
            action="comms5.command.execute.shell.anything", scope_ref="host:camrui",
            policy_ref="policy:delegation.v1", request_ref="unknown command grant",
            max_uses=1, duration_spec={"unit": "days", "value": 7},
            idempotency_key="command-host-request-unknown-action")
