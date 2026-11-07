# =============================================================================
# RIVERVIEW~ CONTROLLED SOURCE
# File: src/riverview_core/institutional_authority/permission_profiles.py
# Component: RESIDENT-PERMISSION-PROFILES
# Revision: 1.0.3
# Purpose: Evaluate and project effective resident permissions alongside exact grants
# Execution Model: Request-driven, PostgreSQL SECURITY DEFINER profile API
# Observability: Audited profile revisions and explicit policy decisions
# Dependencies: PostgreSQL authority migration 0008; psycopg 3
# Authority: Profiles can narrow exact grants; they never create authority grants
# Changed: 2026-10-25 UTC | RV-DYNAMIC-PERMISSIONS-20261025 | Add server-evaluated resident/action/resource decisions to the Steward's existing catalog response.
# Tests: tests/test_permission_profiles.py
# History: Git and .riverview-backups/manifest.jsonl
# =============================================================================
"""Resident permission policy primitives and constrained database adapter.

An active profile is an additional policy gate. Existing exact authority grants
remain independently required. A missing profile retains the legacy exact-grant
decision so staged adoption cannot silently revoke existing assignments.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg
from psycopg import sql
from .grants import _access_level


_SCHEMA = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,62}$")
TIERS = ("observer", "operator", "administrator", "institutional_administrator")
ACCESS_LEVELS = ("read", "write", "execute", "administer", "delegate")
CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")


def _permission_time(value):
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str
    profile_revision: int | None = None
    rule_id: str | None = None
    approval_required: bool = False


def evaluate_profile(profile, *, capability, resource, access_level,
                     classification="internal", export=False,
                     registered_resources=None, now=None) -> PermissionDecision:
    """Pure fail-closed evaluation; explicit resident rules outrank tier rules.

    Within equal specificity, deny wins. A profile with no matching policy
    denies. Expired/revoked rules are ignored. This function does not replace
    the separate exact-grant decision.
    """
    from datetime import datetime, timezone

    if not isinstance(profile, dict) or profile.get("status") != "active":
        return PermissionDecision(False, "profile_not_active")
    if (not capability or not resource or access_level not in ACCESS_LEVELS or
            classification not in CLASSIFICATIONS):
        return PermissionDecision(False, "invalid_request")
    if (not isinstance(registered_resources, (set, frozenset, tuple, list)) or
            resource not in registered_resources):
        return PermissionDecision(False, "resource_not_registered_for_capability")
    now = now or datetime.now(timezone.utc)
    rank = {name: index for index, name in enumerate(CLASSIFICATIONS)}
    ceiling = profile.get("classification_ceiling", "internal")
    if ceiling not in rank or rank[classification] > rank[ceiling]:
        return PermissionDecision(False, "classification_exceeds_profile")
    if export and profile.get("export_mode", "deny") != "allow":
        return PermissionDecision(False, "information_export_denied")
    access_rank = {name: index for index, name in enumerate(ACCESS_LEVELS)}
    candidates = []
    for source, rules in (("tier", profile.get("tier_rules", ())),
                          ("resident", profile.get("rules", ()))):
        for rule in rules:
            if (rule.get("revoked_at") or rule.get("capability_id") != capability
                    or rule.get("resource_id") not in {resource, "*"}
                    or rule.get("effect") not in {"allow", "deny"}
                    or rule.get("access_level") not in ACCESS_LEVELS):
                continue
            expiry = rule.get("valid_until")
            if expiry:
                if isinstance(expiry, str):
                    try:
                        expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                if expiry.tzinfo is None or expiry <= now:
                    continue
            if access_rank[rule["access_level"]] < access_rank[access_level]:
                continue
            specificity = 2 if source == "resident" else 1
            resource_specificity = int(rule["resource_id"] == resource)
            # Explicit resident policy wins over inherited tier policy; ties deny.
            candidates.append((specificity, resource_specificity,
                               int(rule["effect"] == "deny"), rule))
    if not candidates:
        return PermissionDecision(False, "no_matching_allow_rule",
                                  profile.get("revision"))
    candidates.sort(key=lambda item: item[:3], reverse=True)
    rule = candidates[0][3]
    if rule["effect"] == "deny":
        return PermissionDecision(False, "explicit_deny",
                                  profile.get("revision"), rule.get("rule_id"),
                                  bool(rule.get("approval_required")))
    if rank[classification] > rank.get(rule.get("data_classification"), -1):
        return PermissionDecision(False, "rule_classification_exceeded",
                                  profile.get("revision"), rule.get("rule_id"))
    if export and rule.get("export_mode") != "allow":
        return PermissionDecision(False, "rule_export_denied",
                                  profile.get("revision"), rule.get("rule_id"))
    allowed = True
    return PermissionDecision(allowed,
                              "rule_allow",
                              profile.get("revision"), rule.get("rule_id"),
                              bool(rule.get("approval_required")))


class ResidentPermissionStore:
    """Use only the authority schema's audited, narrow profile functions."""

    def __init__(self, connect, schema="riverview_authority"):
        if not isinstance(schema, str) or not _SCHEMA.fullmatch(schema):
            raise ValueError("invalid authority schema")
        self.connect = connect
        self.schema = schema

    def list_profiles(self, steward_principal_id):
        query = sql.SQL("SELECT {}.list_resident_permission_profiles(%s) AS result").format(
            sql.Identifier(self.schema))
        evaluator = sql.SQL("SELECT {}.evaluate_resident_permission(%s,%s,%s,%s,%s,false) AS result").format(
            sql.Identifier(self.schema))
        try:
            with self.connect() as connection, connection.cursor() as cursor:
                cursor.execute(query, (steward_principal_id,))
                row = cursor.fetchone()
                result = row[0] if not hasattr(row, "keys") else row["result"]
                if not isinstance(result, dict):
                    raise RuntimeError("resident_permission_registry_unavailable")
                resources = {item.get("resource_id"): item for item in result.get("resources", [])
                             if isinstance(item, dict)}
                now = datetime.now(timezone.utc)
                for profile in result.get("profiles", []):
                    effective = []
                    grants = profile.get("standing_grants", [])
                    for capability in result.get("capabilities", []):
                        action = capability.get("authority_action")
                        if not isinstance(action, str) or not action:
                            continue
                        level = _access_level(action)
                        for resource_id in capability.get("resource_ids", []):
                            resource = resources.get(resource_id)
                            if resource is None:
                                continue
                            matching_grants = [grant for grant in grants
                                if grant.get("action") == action and grant.get("scope_ref") == resource_id]
                            matched_grant = next((grant for grant in matching_grants
                                if not grant.get("revoked_at")
                                and (not grant.get("valid_from") or _permission_time(grant["valid_from"]) <= now)
                                and (not grant.get("valid_until") or _permission_time(grant["valid_until"]) > now)), None)
                            grant_state = "active" if matched_grant else "missing"
                            if not matched_grant and matching_grants:
                                if any(grant.get("revoked_at") for grant in matching_grants):
                                    grant_state = "revoked"
                                elif any(grant.get("valid_from") and _permission_time(grant["valid_from"]) > now
                                         for grant in matching_grants):
                                    grant_state = "not_yet_valid"
                                elif any(grant.get("valid_until") and _permission_time(grant["valid_until"]) <= now
                                         for grant in matching_grants):
                                    grant_state = "expired"
                                else:
                                    grant_state = "inactive"
                            cursor.execute(evaluator, (profile["principal_id"], action,
                                resource_id, level, resource.get("classification") or "internal"))
                            decision_row = cursor.fetchone()
                            decision = (decision_row[0] if not hasattr(decision_row, "keys")
                                        else decision_row["result"])
                            if isinstance(decision, str):
                                decision = json.loads(decision)
                            policy_allowed = isinstance(decision, dict) and decision.get("allowed") is True
                            approval_required = bool(decision.get("approval_required")) if isinstance(decision, dict) else False
                            effective.append({
                                "capability_id": capability.get("capability_id"),
                                "authority_action": action,
                                "resource_id": resource_id,
                                "access_level": level,
                                "classification": resource.get("classification") or "internal",
                                "export": False,
                                "policy_decision": decision,
                                "exact_grant_status": grant_state,
                                "grant_id": matched_grant.get("grant_id") if matched_grant else None,
                                "effective_status": ("authorized" if policy_allowed and matched_grant and not approval_required
                                                     else "approval_required" if policy_allowed and matched_grant and approval_required
                                                     else "denied"),
                            })
                    profile["effective_permissions"] = effective
                return result
        except psycopg.Error:
            raise RuntimeError("resident_permission_registry_unavailable") from None
        except (ValueError, TypeError, KeyError, IndexError):
            raise RuntimeError("resident_permission_registry_unavailable") from None

    def save_profile(self, steward_principal_id, resident_principal_id,
                     expected_revision, profile):
        self._validate_revision(expected_revision)
        self._validate_principal(steward_principal_id)
        self._validate_principal(resident_principal_id)
        self._validate_profile(profile)
        query = sql.SQL("SELECT {}.save_resident_permission_profile(%s,%s,%s,%s::jsonb) AS result").format(
            sql.Identifier(self.schema))
        try:
            with self.connect() as connection, connection.cursor() as cursor:
                cursor.execute(query, (steward_principal_id, resident_principal_id,
                                       expected_revision,
                                       json.dumps(profile, sort_keys=True)))
                row = cursor.fetchone()
                return row[0] if not hasattr(row, "keys") else row["result"]
        except psycopg.Error as exc:
            # Never relay SQL text or profile data through the HTTP/API boundary.
            code = getattr(exc, "sqlstate", None)
            if code == "40001":
                raise RuntimeError("permission_profile_revision_conflict") from None
            if code == "42501":
                raise PermissionError("resident_permission_change_not_authorized") from None
            raise RuntimeError("resident_permission_registry_unavailable") from None

    def approve_profile(self, steward_principal_id, resident_principal_id,
                        expected_revision):
        return self._transition("approve_resident_permission_profile",
                                steward_principal_id, resident_principal_id,
                                expected_revision)

    def revoke_profile(self, steward_principal_id, resident_principal_id,
                       expected_revision):
        return self._transition("revoke_resident_permission_profile",
                                steward_principal_id, resident_principal_id,
                                expected_revision)

    def _transition(self, function, actor, resident, revision):
        self._validate_revision(revision)
        self._validate_principal(actor)
        self._validate_principal(resident)
        query = sql.SQL("SELECT {}.{}(%s,%s,%s) AS result").format(
            sql.Identifier(self.schema), sql.Identifier(function))
        try:
            with self.connect() as connection, connection.cursor() as cursor:
                cursor.execute(query, (actor, resident, revision))
                row = cursor.fetchone()
                return row[0] if not hasattr(row, "keys") else row["result"]
        except psycopg.Error as exc:
            if getattr(exc, "sqlstate", None) == "40001":
                raise RuntimeError("permission_profile_revision_conflict") from None
            if getattr(exc, "sqlstate", None) == "42501":
                raise PermissionError("resident_permission_change_not_authorized") from None
            raise RuntimeError("resident_permission_registry_unavailable") from None

    @staticmethod
    def _validate_revision(revision):
        if type(revision) is not int or revision < 0 or revision > 2**63 - 1:
            raise ValueError("invalid permission profile revision")

    @staticmethod
    def _validate_principal(principal):
        if not isinstance(principal, str) or not principal or len(principal) > 256:
            raise ValueError("invalid institutional principal")

    @staticmethod
    def _validate_profile(profile):
        if (not isinstance(profile, dict) or
                set(profile) != {"tier", "classification_ceiling", "export_mode", "rules"} or
                not isinstance(profile.get("tier"), str) or
                not isinstance(profile.get("classification_ceiling"), str) or
                not isinstance(profile.get("export_mode"), str) or
                profile["tier"] not in TIERS or
                profile["classification_ceiling"] not in CLASSIFICATIONS or
                profile["export_mode"] not in {"deny", "allow"} or
                not isinstance(profile["rules"], list) or len(profile["rules"]) > 256):
            raise ValueError("invalid resident permission profile")
        if len(json.dumps(profile, sort_keys=True, separators=(",", ":")).encode("utf-8")) > 32768:
            raise ValueError("resident permission profile is too large")
        allowed = {"capability_id", "resource_id", "effect", "access_level",
                   "approval_required", "valid_until", "data_classification",
                   "export_mode", "provenance_ref"}
        for rule in profile["rules"]:
            if (not isinstance(rule, dict) or set(rule) != allowed or
                    not isinstance(rule["capability_id"], str) or
                    not isinstance(rule["resource_id"], str) or
                    not isinstance(rule["effect"], str) or
                    rule["effect"] not in {"allow", "deny"} or
                    not isinstance(rule["access_level"], str) or
                    rule["access_level"] not in ACCESS_LEVELS or
                    not isinstance(rule["approval_required"], bool) or
                    not isinstance(rule["data_classification"], str) or
                    rule["data_classification"] not in CLASSIFICATIONS or
                    not isinstance(rule["export_mode"], str) or
                    rule["export_mode"] not in {"deny", "allow"} or
                    (rule["valid_until"] is not None and not isinstance(rule["valid_until"], str)) or
                    not isinstance(rule["provenance_ref"], str) or
                    len(rule["provenance_ref"]) > 256 or
                    not rule["capability_id"] or len(rule["capability_id"]) > 256 or
                    not rule["resource_id"] or len(rule["resource_id"]) > 256 or
                    not rule["provenance_ref"]):
                raise ValueError("invalid resident permission rule")
            expiry = rule["valid_until"]
            if expiry is not None:
                from datetime import datetime, timezone
                try:
                    parsed = datetime.fromisoformat(expiry.replace("Z", "+00:00")) if isinstance(expiry, str) else None
                except ValueError:
                    parsed = None
                if parsed is None or parsed.tzinfo is None or parsed <= datetime.now(timezone.utc):
                    raise ValueError("permission rule expiry must be a future timezone-aware timestamp")
