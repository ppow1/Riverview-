# =============================================================================
# RIVERVIEW~ CONTROLLED TEST
# File: tests/test_permission_profiles.py
# Component: RESIDENT-PERMISSION-PROFILES
# Revision: 1.0.6
# Purpose: Verify deterministic resident profile policy and fail-closed validation
# Execution Model: unittest policy tests plus disposable PostgreSQL integration
# Observability: Explicit allow/deny reasons
# Dependencies: Python 3.10+; riverview_core.institutional_authority.permission_profiles
# Authority: No production database or institutional grants are modified
# History: Git
# =============================================================================
import unittest
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from riverview_core.institutional_authority.permission_profiles import (
    ResidentPermissionStore, evaluate_profile,
)
from riverview_core.institutional_authority.grants import ExactGrantAuthorizer, GrantDenied

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


class PermissionProfileTests(unittest.TestCase):
    def profile(self, **changes):
        result = {"status":"active", "revision":4,
                  "classification_ceiling":"confidential", "export_mode":"deny",
                  "tier_rules":[], "rules":[],
                  "capability_resources":{"cme.progress.read":["service:cme"]}}
        result.update(changes)
        return result

    def rule(self, *, effect="allow", resource="service:cme", level="read", **extra):
        result = {"rule_id":"rule:1", "capability_id":"cme.progress.read",
                  "resource_id":resource, "effect":effect, "access_level":level,
                  "approval_required":False, "data_classification":"internal",
                  "export_mode":"deny", "valid_until":None, "revoked_at":None}
        result.update(extra)
        return result

    def test_profile_allow_is_additional_policy_not_identity_grant(self):
        decision = evaluate_profile(self.profile(rules=[self.rule()]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", registered_resources={"service:cme"})
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.profile_revision, 4)
        # Registry decision is only a profile gate; callers still require exact grant.

    def test_missing_rule_denies_for_active_profile(self):
        decision = evaluate_profile(self.profile(), capability="cme.progress.read",
            resource="service:cme", access_level="read",
            registered_resources={"service:cme"})
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "no_matching_allow_rule")

    def test_resident_specific_allow_overrides_inherited_tier_denial(self):
        deny = self.rule(effect="deny", resource="*", rule_id="tier-deny")
        allow = self.rule(effect="allow", rule_id="resident-allow")
        decision = evaluate_profile(self.profile(tier_rules=[deny], rules=[allow]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", registered_resources={"service:cme"})
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.rule_id, "resident-allow")

    def test_equal_specificity_deny_wins_and_blocks_tier_allow(self):
        inherited = self.rule(effect="allow", resource="*", rule_id="tier-allow")
        explicit = self.rule(effect="deny", rule_id="explicit-deny")
        decision = evaluate_profile(self.profile(tier_rules=[inherited], rules=[explicit]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", registered_resources={"service:cme"})
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "explicit_deny")

    def test_expired_and_revoked_rules_do_not_authorize(self):
        expired = self.rule(valid_until=datetime.now(timezone.utc)-timedelta(seconds=1))
        revoked = self.rule(resource="*", revoked_at=datetime.now(timezone.utc).isoformat())
        decision = evaluate_profile(self.profile(rules=[expired, revoked]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", registered_resources={"service:cme"})
        self.assertFalse(decision.allowed)

    def test_classification_and_export_constraints_fail_closed(self):
        rule = self.rule()
        self.assertFalse(evaluate_profile(self.profile(rules=[rule]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", classification="restricted",
            registered_resources={"service:cme"}).allowed)
        self.assertFalse(evaluate_profile(self.profile(rules=[rule]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", export=True,
            registered_resources={"service:cme"}).allowed)

    def test_inactive_profile_never_authorizes_by_itself(self):
        decision = evaluate_profile(self.profile(status="pending", rules=[self.rule()]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", registered_resources={"service:cme"})
        self.assertFalse(decision.allowed)

    def test_unregistered_resource_is_denied_before_profile_allow(self):
        decision = evaluate_profile(self.profile(rules=[self.rule()]),
            capability="cme.progress.read", resource="database:other",
            access_level="read", registered_resources={"service:cme"})
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "resource_not_registered_for_capability")

    def test_explicit_deny_cannot_be_bypassed_by_classification_filter(self):
        deny = self.rule(effect="deny", data_classification="internal")
        inherited = self.rule(effect="allow", resource="*", rule_id="tier-allow")
        decision = evaluate_profile(self.profile(tier_rules=[inherited], rules=[deny]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", classification="confidential",
            registered_resources={"service:cme"})
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "explicit_deny")

    def test_rule_classification_and_export_are_independent_limits(self):
        rule = self.rule(data_classification="internal", export_mode="deny")
        high_class = evaluate_profile(self.profile(rules=[rule]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", classification="confidential",
            registered_resources={"service:cme"})
        exported = evaluate_profile(self.profile(export_mode="allow", rules=[rule]),
            capability="cme.progress.read", resource="service:cme",
            access_level="read", export=True,
            registered_resources={"service:cme"})
        self.assertEqual(high_class.reason, "rule_classification_exceeded")
        self.assertEqual(exported.reason, "rule_export_denied")

    def test_store_rejects_unknown_or_malformed_profile_fields(self):
        profile = {"tier":"administrator", "classification_ceiling":"internal",
                   "export_mode":"deny", "rules":[], "invented":"allow all"}
        with self.assertRaises(ValueError):
            ResidentPermissionStore._validate_profile(profile)

    def test_store_requires_provenance_and_exact_rule_shape(self):
        profile = {"tier":"operator", "classification_ceiling":"internal",
                   "export_mode":"deny", "rules":[{"capability_id":"x"}]}
        with self.assertRaises(ValueError):
            ResidentPermissionStore._validate_profile(profile)

    def test_profile_revision_and_serialized_size_are_bounded(self):
        for revision in (True, -1, 2**63):
            with self.assertRaises(ValueError):
                ResidentPermissionStore._validate_revision(revision)
        ResidentPermissionStore._validate_revision(0)
        oversized = {"tier":"operator", "classification_ceiling":"internal",
                     "export_mode":"deny", "rules":[{
                         "capability_id":"resource.read", "resource_id":"institution:riverview",
                         "effect":"allow", "access_level":"read", "approval_required":False,
                         "valid_until":None, "data_classification":"internal",
                         "export_mode":"deny", "provenance_ref":"x" * 33000}]}
        with self.assertRaises(ValueError):
            ResidentPermissionStore._validate_profile(oversized)

    def test_exact_grant_is_still_required_before_profile_allow(self):
        class Cursor:
            def __init__(self, decisions): self.decisions = iter(decisions)
            def execute(self, *_args): pass
            def fetchone(self): return next(self.decisions)
        authorized = Cursor([
            {"principal_id":"steward:grace","grant_id":"grant:exact"},
            ("r", True, 1), (False,),
            ({"allowed":True,"approval_required":False},),
        ])
        result = ExactGrantAuthorizer("riverview_authority").require_principal(
            authorized,"steward:grace","cme.progress.read","service:cme")
        self.assertEqual(result["grant_id"],"grant:exact")
        missing_grant = Cursor([None])
        with self.assertRaises(GrantDenied):
            ExactGrantAuthorizer("riverview_authority").require_principal(
                missing_grant,"steward:grace","cme.progress.read","service:cme")

    def test_active_profile_denial_rejects_existing_exact_grant(self):
        class Cursor:
            def __init__(self): self.index=0
            def execute(self,*_args): pass
            def fetchone(self):
                self.index+=1
                return {
                    1: {"principal_id":"steward:grace","grant_id":"grant:exact"},
                    2: ("r", True, 1), 3: (False,), 4: ({"allowed":False},),
                }[self.index]
        with self.assertRaises(GrantDenied):
            ExactGrantAuthorizer("riverview_authority").require_principal(
                Cursor(),"steward:grace","cme.progress.read","service:cme")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class ResidentPermissionPostgresTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.postgres_migrations import apply_migrations

        self.psycopg = psycopg
        self.sql = sql
        self.schema = "rvprofile_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {} AUTHORIZATION CURRENT_USER").format(
            sql.Identifier(self.schema)))
        migration_dir = Path(__file__).resolve().parents[1] / "src/riverview_core/institutional_authority/migrations"
        apply_migrations(DSN, schema=self.schema, migrations_dir=migration_dir)
        self.admin.execute(sql.SQL("INSERT INTO {}.institutional_offices(office_id,office_role) VALUES ('office:grace-test','Director of Operations'),('office:other-test','Other')").format(sql.Identifier(self.schema)))
        self.admin.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind) VALUES ('steward:profile-test','steward')").format(sql.Identifier(self.schema)))
        self.admin.execute(sql.SQL("INSERT INTO {}.institutional_principals(principal_id,principal_kind,office_id) VALUES ('resident:profile-test','resident','office:grace-test')").format(sql.Identifier(self.schema)))
        self.admin.execute(sql.SQL("INSERT INTO {}.authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) VALUES ('profile-test-manage','steward:profile-test','office.manage','institution','steward:profile-test','test:profile'),('profile-test-read','resident:profile-test','resident.status.read','institution:riverview','steward:profile-test','test:profile')").format(sql.Identifier(self.schema)))
        self.store = ResidentPermissionStore(lambda: psycopg.connect(DSN), schema=self.schema)

    def tearDown(self):
        self.admin.execute(self.sql.SQL("DROP SCHEMA {} CASCADE").format(self.sql.Identifier(self.schema)))
        self.admin.close()

    def document(self, *, effect="allow", resource="institution:riverview"):
        return {"tier":"observer", "classification_ceiling":"confidential",
                "export_mode":"deny", "rules":[{
                    "capability_id":"resident.status.read", "resource_id":resource,
                    "effect":effect, "access_level":"read", "approval_required":False,
                    "valid_until":None, "data_classification":"internal",
                    "export_mode":"deny", "provenance_ref":"steward:test-review"}]}

    def evaluate(self, resource="institution:riverview", classification="internal"):
        return self.admin.execute(self.sql.SQL(
            "SELECT {}.evaluate_resident_permission(%s,%s,%s,%s,%s,false)").format(
                self.sql.Identifier(self.schema)),
            ("resident:profile-test", "resident.status.read", resource, "read", classification)).fetchone()[0]

    def test_pending_approval_resource_binding_denial_and_revocation(self):
        from psycopg.rows import dict_row
        with self.admin.cursor(row_factory=dict_row) as cursor:
            before = cursor.execute(self.sql.SQL(
                "SELECT {}.evaluate_resident_permission(%s,%s,%s,%s,%s,false) AS result").format(
                    self.sql.Identifier(self.schema)),
                ("resident:profile-test", "resident.status.read", "institution:riverview", "read", "internal")).fetchone()["result"]
            self.assertTrue(before["allowed"])  # Legacy exact-grant-only until first profile approval.
        saved = self.store.save_profile("steward:profile-test", "resident:profile-test", 0,
                                        self.document())
        self.assertEqual(saved["status"], "pending")
        self.assertEqual(self.evaluate()["mode"], "legacy_exact_grant_only")
        activated = self.store.approve_profile("steward:profile-test", "resident:profile-test", 1)
        self.assertEqual(activated["status"], "active")
        self.assertTrue(self.evaluate()["allowed"])
        self.assertEqual(self.evaluate("service:riverview-status-dashboard")["reason"],
                         "resource_not_registered_for_capability")
        self.admin.execute(self.sql.SQL("UPDATE {}.institutional_principals SET office_id='office:other-test' WHERE principal_id='resident:profile-test'").format(self.sql.Identifier(self.schema)))
        self.assertEqual(self.evaluate()["reason"], "resident_identity_or_office_changed")
        # Restore office only to isolate the explicit revocation behavior.
        self.admin.execute(self.sql.SQL("UPDATE {}.institutional_principals SET office_id='office:grace-test' WHERE principal_id='resident:profile-test'").format(self.sql.Identifier(self.schema)))
        revoked = self.store.revoke_profile("steward:profile-test", "resident:profile-test", 1)
        self.assertEqual(revoked["status"], "revoked")
        self.assertEqual(self.evaluate()["reason"], "profile_not_active")

    def test_explicit_deny_wins_and_classification_and_history_are_durable(self):
        self.store.save_profile("steward:profile-test", "resident:profile-test", 0,
                                self.document(effect="deny"))
        self.store.approve_profile("steward:profile-test", "resident:profile-test", 1)
        self.assertEqual(self.evaluate(classification="confidential")["reason"], "explicit_deny")
        page = self.store.list_profiles("steward:profile-test")
        profile = next(row for row in page["profiles"] if row["principal_id"] == "resident:profile-test")
        self.assertEqual(profile["status"], "active")
        self.assertEqual(profile["identity_status"], "active")
        self.assertEqual(profile["profile_office_id"], "office:grace-test")
        self.assertEqual(profile["current_office_id"], "office:grace-test")
        self.assertEqual(profile["tier"], "observer")
        self.assertEqual([event["event_type"] for event in profile["audit"]],
                         ["profile_approved", "profile_saved"])

if __name__ == "__main__":
    unittest.main()
