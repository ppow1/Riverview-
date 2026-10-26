# RIVERVIEW~ CONTROLLED SOURCE
# File: tests/test_institutional_authority.py
# Component: INSTITUTIONAL-AUTHORITY
# Revision: 1.0.22
# Changed: 2026-10-26 UTC | RV-V2-CHAT-VISION-AUTHORITY-ORDER | Expect the additive conversation capability migration after declaration enforcement.
# Changed: 2026-10-25 UTC | C3-AUTOMATIC-CAPABILITY-REGISTRATION | Test migration 0015 reconciliation and declaration updates
# Purpose: Verify durable identity separation and fail-closed exact scoped grants
# Execution Model: PostgreSQL integration tests in rvtest_* disposable schemas
# Observability: unittest evidence, authority events, binding/state revisions
# Dependencies: RIVERVIEW_TEST_PG_DSN; PostgreSQL 16; Psycopg 3
# Authority: Creates/drops only unique test schemas
# Changed: 2026-10-11 UTC | RV-M4.1-001 | Verify expiry validation and Steward recovery credential
# Changed: 2026-10-11 UTC | RV-M4.1-FRESH-SCHEMA-MIGRATION-LEDGER | Run authority tests against fresh schema with no precreated ledger
# Changed: 2026-10-11 UTC | RV-M4.1-BOOTSTRAP-WRITE-AHEAD | Verify pre-persistable root bootstrap token is stored only as a digest
# Changed: 2026-10-11 UTC | RV-M4.1-EXACT-GRANT-MIGRATION-EXPECTATION | Include runtime exact-grant migration in idempotency assertion
# Changed: 2026-10-11 UTC | RV-M4.1-BOUND-OCCUPANT-WRITE | Bind office-state persistence tests to the current occupant identity
# Changed: 2026-10-11 UTC | RV-M4.1-RESIDENT-RUNTIME | Include resident office-state API migration in migration sequence assertion
# Changed: 2026-10-13 UTC | RV-GRACE-ACCOUNT-AUTHORITY | Include linked-principal exact-grant migration in migration sequence assertion
# Changed: 2026-10-14 UTC | RV-GRACE-DEFERRED-ROUTER-UPGRADE | Require and checksum-apply the audited successor migration in authority fixtures
# Changed: 2026-10-14 UTC | RV-GRACE-DOPS-ROLE-CONTEXT-001 | Verify Steward-only office-role CAS, audit event, and binding/occupant preservation
# Changed: 2026-10-16 UTC | RV-WORKER-REGISTRY-RETIRE-001 | Include worker retirement audit migration in authority sequence
# Contracts: docs/components/INSTITUTIONAL_AUTHORITY.md
# Tests: This file
# History: Git and .riverview-backups/manifest.jsonl
"""PostgreSQL integration tests for the institutional authority boundary."""

import os
import hashlib
import json
import secrets
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

DSN = os.environ.get("RIVERVIEW_TEST_PG_DSN")


@unittest.skipUnless(DSN, "RIVERVIEW_TEST_PG_DSN not configured")
class InstitutionalAuthorityTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        from psycopg import sql
        from riverview_core.institutional_authority import AuthorityRegistry
        from riverview_core.postgres_migrations import apply_migrations

        self.schema = "rvtest_" + uuid4().hex
        self.admin = psycopg.connect(DSN, autocommit=True)
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        migration = Path(__file__).resolve().parents[1] / "src/riverview_core/institutional_authority/migrations"
        # A dedicated new authority schema has no shared Core migration ledger.
        self.migrations = apply_migrations(DSN, schema=self.schema, migrations_dir=migration)
        self.registry = AuthorityRegistry(DSN, schema=self.schema)
        # Fixture setup is the trusted authority boundary in this disposable schema.
        self.steward_token = secrets.token_urlsafe(32)
        with self.admin.cursor() as cur:
            cur.execute(f"INSERT INTO {self.schema}.institutional_principals(principal_id,principal_kind) VALUES ('steward:test','steward')")
            cur.execute(f"INSERT INTO {self.schema}.principal_credentials(credential_id,principal_id,credential_sha256) VALUES (%s,'steward:test',%s)",
                        (uuid4(), hashlib.sha256(self.steward_token.encode()).digest()))
            for action in ("authority.grant", "identity.manage", "office.manage"):
                cur.execute(f"INSERT INTO {self.schema}.authority_grants(grant_id,principal_id,action,scope_ref,granted_by,policy_ref) VALUES (%s,'steward:test',%s,'institution','steward:test','rv.policy:test.v1')",
                            (f"bootstrap:{action}", action))
            cur.execute(f"INSERT INTO {self.schema}.institutional_authority_events(event_id,event_type,actor_id,subject_id) VALUES (%s,'steward_bootstrapped','steward:test','steward:test')",
                        (uuid4(),))

    def tearDown(self):
        from psycopg import sql
        self.registry.close()
        self.admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema)))
        self.admin.close()

    def test_migration_is_idempotent_and_bootstrap_is_single_use(self):
        from riverview_core.institutional_authority import AuthorityDenied, IdentityConflict
        from riverview_core.postgres_migrations import apply_migrations
        migration = Path(__file__).resolve().parents[1] / "src/riverview_core/institutional_authority/migrations"
        self.assertEqual(self.migrations, [
            "0000_authority_migration_ledger",
            "0001_institutional_authority",
            "0002_exact_grant_authorization",
            "0003_resident_office_state_api",
            "0004_exact_principal_grant_authorization",
            "0005_audited_model_rebinding",
            "0006_authorized_implementation_successor",
            "0007_audited_office_role_update",
            "0008_resident_permission_profiles",
            "0009_worker_registration_retirement_event",
            "0010_grace_autonomy_experiment_grant",
                        "0011_exact_grace_luna_escalation_check",
            "0012_grace_supervisory_authority",
            "0013_grace_capability_registry_read",
            "0014_resident_status_read_schema",
            "0015_deployed_capability_declarations",
            "0016_resident_conversation_workspace_capability",
            "0017_reusable_scoped_grants",
            "0018_delegated_host_scopes",
            "0019_generalized_delegation_lifecycle",
        ])
        self.assertEqual(apply_migrations(DSN, schema=self.schema, migrations_dir=migration), [])
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT input_schema FROM {self.schema}.capability_catalog "
                        "WHERE capability_id='resident.status.read'")
            status_schema = cur.fetchone()[0]
        self.assertEqual(status_schema, {
            "type": "object", "additionalProperties": False,
            "required": [], "properties": {},
        })
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT authority_action,implementation_ref,authorization_contract,"
                        f"registration_blocker,declaration_source "
                        f"FROM {self.schema}.capability_catalog "
                        "WHERE capability_id='resident.status.read'")
            declaration = cur.fetchone()
        self.assertEqual(declaration[0], "resident.status.read")
        self.assertEqual(declaration[1], "dashboard.projection.v1")
        self.assertEqual(declaration[2]["mode"], "exact_grant")
        self.assertIsNone(declaration[3])
        self.assertEqual(declaration[4], "resident_status_read.json")
        if os.geteuid() != 0:
            with self.assertRaises(AuthorityDenied):
                self.registry.bootstrap_steward("steward:second")
        else:
            with self.assertRaises(IdentityConflict):
                self.registry.bootstrap_steward("steward:second")

    def test_generalized_grant_activation_extension_and_lineage(self):
        """Typed lifetimes and successor changes persist through the real authority API."""
        from datetime import datetime, timedelta, timezone

        grantee_token = self.registry.create_principal(
            self.steward_token, "chatgpt:issue343-test", "service")
        pending = self.registry.request_grant(
            requester_id="steward:test", principal_id="chatgpt:issue343-test",
            action="comms5.proposal.promote", scope_ref="project:Riverview",
            policy_ref="policy:delegation.v1", request_ref="issue:343:test",
            max_uses=1, duration_spec={"unit": "minutes", "value": 30},
            idempotency_key="issue343:initial")
        approved = self.registry.decide_request(
            steward_token=self.steward_token, request_id=pending["request_id"],
            decision="approve", expected_request_sha256=pending["request_sha256"],
            idempotency_key="issue343:approve-initial", approval_ref="steward:issue343:initial")
        original_id = approved["grant_id"]
        original = self.registry.get_status(
            requester_id="steward:test", grant_id=original_id)
        self.assertEqual(original["duration_spec"], {"unit": "minutes", "value": 30})
        activation = datetime.fromisoformat(original["approved_at"])
        expiry = datetime.fromisoformat(original["valid_until"])
        self.assertGreaterEqual(expiry - activation, timedelta(minutes=29, seconds=59))
        self.assertLessEqual(expiry - activation, timedelta(minutes=30, seconds=1))

        reservation = self.registry.reserve_delegated_grant(
            grantee_token, original_id, "comms5.proposal.promote", "project:Riverview",
            "work-order:issue343:test", idempotency_key="issue343:use-1")
        self.registry.consume_delegated_grant(
            grantee_token, reservation["reservation_id"], "result:issue343:test")

        change = self.registry.request_change(
            requester_id="steward:test", grant_id=original_id,
            action="objective.submit", scope_ref="project:Riverview",
            policy_ref="policy:delegation.v1", request_ref="issue:343:combined-change",
            max_uses=None, duration_spec={"unit": "days", "value": 7},
            change_kind="extend_upgrade", idempotency_key="issue343:combined-change")
        changed = self.registry.decide_request(
            steward_token=self.steward_token, request_id=change["request_id"],
            decision="approve", expected_request_sha256=change["request_sha256"],
            idempotency_key="issue343:approve-change", approval_ref="steward:issue343:change")
        successor = self.registry.get_status(
            requester_id="steward:test", grant_id=changed["grant_id"])
        predecessor = self.registry.get_status(
            requester_id="steward:test", grant_id=original_id)
        self.assertEqual(successor["supersedes_grant_id"], original_id)
        self.assertEqual(successor["used_count"], 1)
        self.assertEqual(successor["max_uses"], None)
        self.assertEqual(successor["duration_spec"], {"unit": "days", "value": 7})
        self.assertEqual(successor["action"], "objective.submit")
        successor_expiry = datetime.fromisoformat(successor["valid_until"])
        self.assertGreater(successor_expiry, expiry + timedelta(days=6, hours=23))
        self.assertEqual(predecessor["status"], "revoked")

        indefinite_request = self.registry.request_grant(
            requester_id="steward:test", principal_id="chatgpt:issue343-test",
            action="comms5.proposal.promote", scope_ref="project:Riverview",
            policy_ref="policy:delegation.v1", request_ref="issue:343:indefinite-upgrade",
            max_uses=None, duration_spec={"unit": "indefinite"},
            idempotency_key="issue343:indefinite-upgrade-source")
        indefinite_approval = self.registry.decide_request(
            steward_token=self.steward_token, request_id=indefinite_request["request_id"],
            decision="approve", expected_request_sha256=indefinite_request["request_sha256"],
            idempotency_key="issue343:indefinite-upgrade-source-approve",
            approval_ref="steward:issue343:indefinite-source")
        indefinite_change = self.registry.request_change(
            requester_id="steward:test", grant_id=indefinite_approval["grant_id"],
            action="objective.submit", scope_ref="project:Riverview",
            policy_ref="policy:delegation.v1", request_ref="issue:343:indefinite-upgrade",
            change_kind="upgrade", idempotency_key="issue343:indefinite-upgrade")
        indefinite_successor = self.registry.decide_request(
            steward_token=self.steward_token, request_id=indefinite_change["request_id"],
            decision="approve", expected_request_sha256=indefinite_change["request_sha256"],
            idempotency_key="issue343:indefinite-upgrade-approve",
            approval_ref="steward:issue343:indefinite-upgraded")
        indefinite_status = self.registry.get_status(
            requester_id="steward:test", grant_id=indefinite_successor["grant_id"])
        self.assertIsNone(indefinite_status["valid_until"])
        self.assertIsNone(indefinite_status["max_uses"])
        self.assertEqual(indefinite_status["duration_spec"], {"unit": "indefinite"})

        outstanding = self.registry.reserve_delegated_grant(
            grantee_token, changed["grant_id"], "objective.submit", "project:Riverview",
            "work-order:issue343:revoke", idempotency_key="issue343:pending-revocation")
        self.registry.revoke_grant(self.steward_token, changed["grant_id"],
                                   reason_code="issue343_verified")
        self.assertEqual(self.registry.consume_delegated_grant(
            grantee_token, outstanding["reservation_id"], "result:after-revoke")["status"],
            "released")
        self.assertEqual(self.registry.get_status(
            requester_id="steward:test", grant_id=changed["grant_id"])["status"], "revoked")

        rejected_request = self.registry.request_grant(
            requester_id="steward:test", principal_id="chatgpt:issue343-test",
            action="comms5.proposal.promote", scope_ref="project:Riverview",
            policy_ref="policy:delegation.v1", request_ref="issue:343:denial-example",
            max_uses=1, duration_spec={"unit": "indefinite"},
            idempotency_key="issue343:rejected-request")
        rejected = self.registry.decide_request(
            steward_token=self.steward_token, request_id=rejected_request["request_id"],
            decision="reject", expected_request_sha256=rejected_request["request_sha256"],
            idempotency_key="issue343:reject", approval_ref=None)
        self.assertEqual(rejected["status"], "rejected")
        self.assertIsNone(rejected["grant_id"])

        surrender_request = self.registry.request_grant(
            requester_id="steward:test", principal_id="chatgpt:issue343-test",
            action="comms5.proposal.promote", scope_ref="project:Riverview",
            policy_ref="policy:delegation.v1", request_ref="issue:343:surrender-example",
            max_uses=1, duration_spec={"unit": "indefinite"},
            idempotency_key="issue343:surrender-request")
        surrender_approval = self.registry.decide_request(
            steward_token=self.steward_token, request_id=surrender_request["request_id"],
            decision="approve", expected_request_sha256=surrender_request["request_sha256"],
            idempotency_key="issue343:surrender-approve", approval_ref="steward:issue343:surrender")
        surrendered = self.registry.surrender_grant(
            grantee_id="chatgpt:issue343-test", grant_id=surrender_approval["grant_id"],
            idempotency_key="issue343:surrender")
        self.assertEqual(surrendered["status"], "surrendered")
        self.assertEqual(self.registry.surrender_grant(
            grantee_id="chatgpt:issue343-test", grant_id=surrender_approval["grant_id"],
            idempotency_key="issue343:surrender"), surrendered)
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {self.schema}.institutional_authority_events "
                        "WHERE grant_id=%s AND event_type IN "
                        "('authority_delegation_grant_extended','authority_delegation_grant_upgraded')",
                        (changed["grant_id"],))
            self.assertEqual(cur.fetchone()[0], 2)


    def test_deployed_declarations_register_update_and_record_blockers(self):
        import psycopg
        from psycopg import sql
        from riverview_core.postgres_migrations import apply_migrations

        source_migrations = (Path(__file__).resolve().parents[1]
                             / "src/riverview_core/institutional_authority/migrations")
        with tempfile.TemporaryDirectory(prefix="rv-capability-declaration-test-") as temp:
            component = Path(temp) / "institutional_authority"
            migrations = component / "migrations"
            declarations = component / "capability_declarations"
            migrations.mkdir(parents=True)
            declarations.mkdir()
            for source in source_migrations.glob("*.sql"):
                shutil.copyfile(source, migrations / source.name)
            registered = {
                "capability_id": "estate.proposal.read.v1",
                "description": "Read a proposal through the existing authorized API",
                "operation": "proposal.read",
                "owner_office": "office:steward",
                "implementation_ref": "unavailable:website-proposal-api",
                "dependencies": ["institutional-proposals-api"],
                "approval_default": False,
                "input_schema": {"type": "object", "additionalProperties": False,
                    "required": ["proposal_id"], "properties": {
                        "proposal_id": {"type": "string", "minLength": 1,
                                         "maxLength": 128}}},
                "authorization_contract": {"mode": "authenticated_account_session",
                    "reason": "existing Steward-account session boundary"},
                "availability_policy": "executor_and_worker_health",
                "registration_blocker": "no_session_compatible_registry_executor",
                "enabled": False,
            }
            declaration_file = declarations / "estate_proposal_read.json"
            declaration_file.write_text(json.dumps(registered), encoding="utf-8")
            schema = "rvtest_capdecl_" + uuid4().hex
            self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            try:
                self.assertEqual(len(apply_migrations(
                    DSN, schema=schema, migrations_dir=migrations)), len(list(migrations.glob("*.sql"))))
                with self.admin.cursor() as cur:
                    cur.execute(sql.SQL("SELECT input_schema,authorization_contract,"
                                        "declaration_source,declaration_source_commit,"
                                        "enabled,registration_blocker "
                                        "FROM {}.capability_catalog WHERE capability_id=%s").format(
                                            sql.Identifier(schema)), (registered["capability_id"],))
                    row = cur.fetchone()
                self.assertEqual(row[0], registered["input_schema"])
                self.assertEqual(row[1], registered["authorization_contract"])
                self.assertEqual(row[2], declaration_file.name)
                self.assertFalse(row[4])
                self.assertEqual(row[5], registered["registration_blocker"])
                with self.admin.cursor() as cur:
                    cur.execute(sql.SQL("SELECT {}.list_capability_registry()").format(
                        sql.Identifier(schema)))
                    live_catalog = cur.fetchone()[0]
                    cur.execute(sql.SQL("SELECT p.prosecdef, EXISTS ("
                                        "SELECT 1 FROM pg_catalog.aclexplode(p.proacl) acl "
                                        "WHERE acl.grantee=0 AND acl.privilege_type='EXECUTE') "
                                        "FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n "
                                        "ON n.oid=p.pronamespace WHERE n.nspname=%s "
                                        "AND p.proname='reconcile_capability_declarations'"),
                                (schema,))
                    reconciliation_acl = cur.fetchone()
                self.assertIn(registered["capability_id"],
                              {item["capability_id"] for item in live_catalog})
                self.assertEqual(reconciliation_acl, (False, False))
                with self.admin.cursor() as cur:
                    cur.execute(sql.SQL("SELECT count(*) FROM {}.authority_grants").format(
                        sql.Identifier(schema)))
                    self.assertEqual(cur.fetchone()[0], 0)

                # Reconciliation runs on a no-op migration pass and picks up a
                # changed declaration shipped by the next feature release.
                registered["description"] = "Updated proposal read contract"
                declaration_file.write_text(json.dumps(registered), encoding="utf-8")
                self.assertEqual(apply_migrations(
                    DSN, schema=schema, migrations_dir=migrations), [])
                with self.admin.cursor() as cur:
                    cur.execute(sql.SQL("SELECT description FROM {}.capability_catalog "
                                        "WHERE capability_id=%s").format(sql.Identifier(schema)),
                                (registered["capability_id"],))
                    self.assertEqual(cur.fetchone()[0], registered["description"])

                blocked = dict(registered, capability_id="website.account.session.admin",
                    description="Account administration requiring a Steward session",
                    operation="pending.website.account.session.admin",
                    implementation_ref="unavailable:account-session-api",
                    authorization_contract={"mode": "authenticated_account_session",
                                            "reason": "preserve caller session"},
                    enabled=False,
                    registration_blocker="executor_and_session_authorization_not_supported")
                (declarations / "website_account_session.json").write_text(
                    json.dumps(blocked), encoding="utf-8")
                self.assertEqual(apply_migrations(
                    DSN, schema=schema, migrations_dir=migrations), [])
                with self.admin.cursor() as cur:
                    cur.execute(sql.SQL("SELECT enabled,registration_blocker,authorization_contract "
                                        "FROM {}.capability_catalog WHERE capability_id=%s").format(
                                            sql.Identifier(schema)), (blocked["capability_id"],))
                    row = cur.fetchone()
                self.assertFalse(row[0])
                self.assertEqual(row[1], blocked["registration_blocker"])
                self.assertEqual(row[2]["mode"], "authenticated_account_session")
            finally:
                self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    sql.Identifier(schema)))

    def test_experiment_grant_requires_authenticated_exact_grant_and_is_idempotent(self):
        from datetime import datetime, timedelta, timezone
        from riverview_core.institutional_authority import AuthorityDenied
        grant_id = "grant:grace-autonomy:" + str(uuid4())
        scope = ("grace-autonomy:objective:proposal:"
                 "e8b3e6bb-b179-5c4a-90b1-5bf71dd3f7b4:r2")
        expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        self.admin.execute(f"""INSERT INTO {self.schema}.institutional_principals
            (principal_id,principal_kind) VALUES ('resident:grace','resident')""")
        self.admin.execute(f"""INSERT INTO {self.schema}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES ('luna:exact','resident:grace','resident.reasoning.escalate',
                'provider:gpt-6-luna','steward:test','rv.policy:test.v1')""")
        self.assertEqual(self.registry.issue_grace_autonomy_experiment_grant(
            actor_id="steward:test", grant_id=grant_id, scope_ref=scope,
            valid_until=expiry), grant_id)
        from riverview_core.institutional_authority import ExactGrantAuthorizer, GrantDenied
        checker = ExactGrantAuthorizer(self.schema)
        with self.registry.db.cursor() as cur:
            self.assertEqual(checker.require_grace_experiment_grant(cur, grant_id, scope),
                {"principal_id": "resident:grace", "grant_id": grant_id})
            with self.assertRaises(GrantDenied):
                checker.require_grace_experiment_grant(cur, "grant:wrong", scope)
            with self.assertRaises(GrantDenied):
                checker.require_grace_experiment_grant(cur, grant_id, "unrelated-objective")
        self.assertEqual(self.registry.issue_grace_autonomy_experiment_grant(
            actor_id="steward:test", grant_id=grant_id, scope_ref=scope,
            valid_until=expiry), grant_id)
        with self.assertRaises(AuthorityDenied):
            self.registry.issue_grace_autonomy_experiment_grant(
                actor_id="steward:unregistered", grant_id=grant_id,
                scope_ref=scope, valid_until=expiry)
        result=self.admin.execute(f"""SELECT count(*) FROM {self.schema}.authority_grants
            WHERE grant_id=%s AND principal_id='resident:grace'
              AND action='grace.experiment.execute' AND scope_ref=%s
              AND valid_until=%s AND revoked_at IS NULL""",(grant_id,scope,expiry)).fetchone()[0]
        self.assertEqual(result,1)
        events=self.admin.execute(f"""SELECT count(*) FROM {self.schema}.institutional_authority_events
            WHERE grant_id=%s AND event_type='authority_granted'""",(grant_id,)).fetchone()[0]
        self.assertEqual(events,1)

    def test_grace_luna_lookup_is_fixed_scope_and_fails_closed(self):
        from riverview_core.institutional_authority import AuthorityDenied
        with self.assertRaises(AuthorityDenied):
            self.registry.active_grace_luna_escalation_grant()
        self.admin.execute(f"""INSERT INTO {self.schema}.institutional_principals
            (principal_id,principal_kind) VALUES ('resident:grace','resident')""")
        self.admin.execute(f"""INSERT INTO {self.schema}.authority_grants
            (grant_id,principal_id,action,scope_ref,granted_by,policy_ref)
            VALUES ('luna:exact','resident:grace','resident.reasoning.escalate',
                'provider:gpt-6-luna','steward:test','rv.policy:test.v1')""")
        self.assertEqual(self.registry.active_grace_luna_escalation_grant(),
            {"principal_id": "resident:grace", "grant_id": "luna:exact"})
        self.admin.execute(f"UPDATE {self.schema}.authority_grants SET revoked_at=clock_timestamp() WHERE grant_id='luna:exact'")
        with self.assertRaises(AuthorityDenied):
            self.registry.active_grace_luna_escalation_grant()
    def test_office_role_update_is_steward_only_cas_and_preserves_binding(self):
        from riverview_core.institutional_authority import AuthorityDenied, IdentityConflict
        self.registry.create_office(self.steward_token, "office:grace-role",
                                    "AI director of engineering")
        self.registry.create_principal(self.steward_token, "resident:grace-role", "resident")
        self.registry.create_occupant(self.steward_token, "occupant:grace-role",
                                      principal_id="resident:grace-role")
        self.registry.create_implementation(self.steward_token, "implementation:grace-role",
            kind="model", provider_ref="test.provider", revision="a" * 64)
        self.registry.bind_office(self.steward_token, "office:grace-role",
            "occupant:grace-role", "implementation:grace-role")
        service_token = self.registry.create_principal(self.steward_token,
            "service:role-editor", "service")
        self.registry.grant(self.steward_token, "service:role-editor", "office.manage",
            "institution", policy_ref="rv.policy:test.v1")
        with self.assertRaises(AuthorityDenied):
            self.registry.update_office_role(service_token, "office:grace-role",
                "Director of Operations", expected_office_role="AI director of engineering")
        with self.assertRaises(IdentityConflict):
            self.registry.update_office_role(self.steward_token, "office:grace-role",
                "Director of Operations", expected_office_role="stale role")
        result = self.registry.update_office_role(self.steward_token, "office:grace-role",
            "Director of Operations", expected_office_role="AI director of engineering")
        self.assertEqual(result, {"office_id": "office:grace-role",
            "office_role": "Director of Operations", "changed": True})
        snapshot = self.registry.office_snapshot("office:grace-role")
        self.assertEqual(snapshot["occupant_id"], "occupant:grace-role")
        self.assertEqual(snapshot["implementation_id"], "implementation:grace-role")
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT event_type,payload FROM {self.schema}.institutional_authority_events "
                        "WHERE office_id='office:grace-role' AND event_type='office_role_updated'")
            event = cur.fetchone()
        if hasattr(event, "keys"):
            event_type, payload = event["event_type"], event["payload"]
        else:
            event_type, payload = event
        self.assertEqual(event_type, "office_role_updated")
        self.assertEqual(payload["previous_office_role"], "AI director of engineering")
        self.assertEqual(payload["office_role"], "Director of Operations")
    def test_bootstrap_accepts_preallocated_token_for_write_ahead_persistence(self):
        from unittest.mock import patch
        import psycopg
        from psycopg import sql
        from riverview_core.institutional_authority import AuthorityRegistry
        from riverview_core.postgres_migrations import apply_migrations

        schema = "rvtest_bootstrap_" + uuid4().hex
        self.admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        registry = None
        try:
            migration = (Path(__file__).resolve().parents[1]
                         / "src/riverview_core/institutional_authority/migrations")
            apply_migrations(DSN, schema=schema, migrations_dir=migration)
            registry = AuthorityRegistry(DSN, schema=schema)
            token = secrets.token_urlsafe(32)
            with patch("riverview_core.institutional_authority.registry.os.geteuid", return_value=0):
                self.assertEqual(registry.bootstrap_steward(token=token), token)
            self.assertEqual(registry.authorize(token, "identity.manage", "institution")["principal_id"],
                             "steward:camrui")
            with self.admin.cursor() as cur:
                cur.execute(sql.SQL("SELECT credential_sha256 FROM {}.principal_credentials").format(
                    sql.Identifier(schema)))
                digest = cur.fetchone()[0]
            self.assertEqual(digest, hashlib.sha256(token.encode("utf-8")).digest())
            self.assertNotIn(token.encode("utf-8"), digest)
        finally:
            if registry is not None:
                registry.close()
            self.admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))

    def test_grants_are_exact_scoped_and_cannot_be_self_issued(self):
        from riverview_core.institutional_authority import AuthorityDenied
        worker_token = self.registry.create_principal(
            self.steward_token, "worker:one", "worker")
        grant_id = self.registry.grant(
            self.steward_token, "worker:one", "assignment.execute",
            "grant:demo-one", policy_ref="rv.policy:test.v1")
        authorized = self.registry.authorize(
            worker_token, "assignment.execute", "grant:demo-one")
        self.assertEqual(authorized["principal_id"], "worker:one")
        self.assertEqual(authorized["principal_kind"], "worker")
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize(worker_token, "assignment.execute", "grant:demo-two")
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize(worker_token, "authority.grant", "institution")
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize("not-a-valid-bearer-credential", "assignment.execute", "grant:demo-one")
        self.assertTrue(grant_id.startswith("grant:"))

    def test_grant_revocation_is_durable_and_fail_closed(self):
        from riverview_core.institutional_authority import AuthorityDenied
        token = self.registry.create_principal(self.steward_token, "service:worker", "service")
        grant = self.registry.grant(self.steward_token, "service:worker", "worker.run",
                                    "scope:one", policy_ref="rv.policy:test.v1")
        self.registry.authorize(token, "worker.run", "scope:one")
        self.registry.revoke_grant(self.steward_token, grant)
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize(token, "worker.run", "scope:one")

    def test_codex_delegation_is_exact_scoped_and_expires_after_activation(self):
        from riverview_core.institutional_authority import AuthorityDenied
        unprivileged = self.registry.create_principal(self.steward_token,
            "service:registration-test", "service")
        with self.assertRaises(AuthorityDenied):
            self.registry.create_principal(unprivileged, "service:chatgpt", "service")
        issued_credential = self.registry.create_principal(
            self.steward_token, "service:chatgpt", "service")
        self.assertGreaterEqual(len(issued_credential), 32)
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT event_type FROM {self.schema}.institutional_authority_events WHERE subject_id=%s", ("service:chatgpt",))
            self.assertIn("principal_created", [item[0] for item in cur.fetchall()])
        request = self.registry.request_grant(requester_id="steward:test",
            principal_id="service:chatgpt", action="comms5.operations.non_destructive.v1",
            scope_ref="project:Riverview", policy_ref="policy:delegation.v1",
            request_ref="Isolated Codex delegation authorization fixture",
            max_uses=None, valid_until=datetime.now(timezone.utc)+timedelta(hours=24),
            idempotency_key="codex-integration-request-0001")
        self.assertEqual(request["status"], "pending")
        decision = self.registry.decide_request(steward_token=self.steward_token,
            request_id=request["request_id"], decision="approve",
            expected_request_sha256=request["request_sha256"],
            idempotency_key="codex-integration-decision-0001",
            approval_ref="isolated PostgreSQL acceptance fixture")
        self.assertEqual(decision["status"], "approved")
        grant_id = decision["grant_id"]
        allowed = self.registry.authorize_delegated_principal_operation(
            "service:chatgpt", "comms5.operations.non_destructive.v1",
            "project:Riverview", "policy:delegation.v1", "codex-call:fixture-1")
        self.assertEqual(allowed["grant_id"], grant_id)
        self.assertEqual(allowed["status"], "authorized")
        self.assertEqual(allowed["use_limit"], "unlimited")
        grant = self.registry.get_status(requester_id="steward:test", grant_id=grant_id)
        activated_for = (datetime.fromisoformat(grant["valid_until"]) -
                         datetime.fromisoformat(grant["approved_at"]))
        self.assertLessEqual(abs(activated_for - timedelta(hours=24)), timedelta(seconds=2))
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize_delegated_principal_operation(
                "service:chatgpt", "comms5.operations.non_destructive.v1",
                "host:octominer1", "policy:delegation.v1", "codex-call:wrong-scope")
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT event_type FROM {self.schema}.institutional_authority_events WHERE grant_id=%s", (grant_id,))
            events = [item[0] for item in cur.fetchall()]
            self.assertIn("authority_grant_used", events)
            cur.execute(f"UPDATE {self.schema}.authority_grants SET valid_from=clock_timestamp()-interval '2 hours', valid_until=clock_timestamp()-interval '1 hour' WHERE grant_id=%s", (grant_id,))
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize_delegated_principal_operation(
                "service:chatgpt", "comms5.operations.non_destructive.v1",
                "project:Riverview", "policy:delegation.v1", "codex-call:expired")

    def test_finite_delegation_use_is_reserved_consumed_exhausted_and_revocable(self):
        from riverview_core.institutional_authority import AuthorityDenied
        grantee_token = self.registry.create_principal(self.steward_token,
            "service:finite-delegation-test", "service")
        action, scope = "hardware.gpu.workload.start", "host:octominer1"
        request = self.registry.request_grant(requester_id="steward:test",
            principal_id="service:finite-delegation-test", action=action,
            scope_ref=scope, policy_ref="policy:delegation.v1",
            request_ref="One-use disposable delegated grant fixture", max_uses=1,
            valid_until=None, idempotency_key="finite-integration-request-0001")
        decision = self.registry.decide_request(steward_token=self.steward_token,
            request_id=request["request_id"], decision="approve",
            expected_request_sha256=request["request_sha256"],
            idempotency_key="finite-integration-decision-0001",
            approval_ref="isolated PostgreSQL acceptance fixture")
        grant_id = decision["grant_id"]
        reserved = self.registry.reserve_delegated_grant(grantee_token, grant_id,
            action, scope, "workload-job:fixture-1", idempotency_key="finite-use-0001")
        self.assertEqual(reserved["status"], "reserved")
        consumed = self.registry.consume_delegated_grant(grantee_token,
            reserved["reservation_id"], "fixture-result:started")
        self.assertEqual(consumed["status"], "consumed")
        with self.assertRaises(AuthorityDenied):
            self.registry.reserve_delegated_grant(grantee_token, grant_id,
                action, scope, "workload-job:fixture-2", idempotency_key="finite-use-0002")
        self.registry.revoke_grant(self.steward_token, grant_id,
            reason_code="isolated_acceptance_revoked")
        with self.assertRaises(AuthorityDenied):
            self.registry.reserve_delegated_grant(grantee_token, grant_id,
                action, scope, "workload-job:fixture-3", idempotency_key="finite-use-0003")

    def test_credential_rotation_and_revocation_preserve_steward_recovery(self):
        from riverview_core.institutional_authority import AuthorityDenied, IdentityConflict
        with self.assertRaises(ValueError):
            self.registry.issue_credential(self.steward_token, "steward:test",
                                           expires_at=datetime.now(timezone.utc)-timedelta(seconds=1))
        replacement = self.registry.issue_credential(self.steward_token, "steward:test")
        # Credential identifiers are not returned to callers; find only the row bound to
        # this token digest in the database fixture to exercise revocation.
        import hashlib
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT credential_id FROM {self.schema}.principal_credentials WHERE credential_sha256=%s",
                        (hashlib.sha256(replacement.encode()).digest(),))
            credential_id = cur.fetchone()[0]
        self.registry.revoke_credential(self.steward_token, credential_id)
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize(replacement, "identity.manage", "institution")
        self.registry.authorize(self.steward_token, "identity.manage", "institution")
        with self.assertRaises(IdentityConflict):
            self.registry.revoke_credential(self.steward_token,
                                            self._credential_id_for(self.steward_token))
        self.registry.authorize(self.steward_token, "identity.manage", "institution")
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {self.schema}.institutional_authority_events WHERE event_type IN ('credential_issued','credential_revoked')")
            self.assertEqual(cur.fetchone()[0], 2)

    def _credential_id_for(self, token):
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT credential_id FROM {self.schema}.principal_credentials WHERE credential_sha256=%s",
                        (hashlib.sha256(token.encode()).digest(),))
            return cur.fetchone()[0]

    def test_office_occupant_implementation_and_state_are_separate_across_replacement(self):
        from riverview_core.institutional_authority import AuthorityDenied
        self.registry.create_office(self.steward_token, "office:grace", "engineering-director")
        occupant_one = self.registry.create_principal(
            self.steward_token, "resident:grace-occupant-1", "resident", office_id="office:grace")
        self.registry.create_occupant(self.steward_token, "occupant:grace-1",
                                      principal_id="resident:grace-occupant-1")
        self.registry.create_implementation(self.steward_token, "impl:reasoner-1", kind="model",
                                            provider_ref="local:test-provider", revision="1")
        first_binding = self.registry.bind_office(
            self.steward_token, "office:grace", "occupant:grace-1", "impl:reasoner-1")
        state_grant = self.registry.grant(
            self.steward_token, "resident:grace-occupant-1", "office.state.write",
            "office:office:grace", policy_ref="rv.policy:office-state.v1")
        self.registry.set_office_state(occupant_one, "office:grace",
                                       {"objective_id": "objective:durable"}, expected_revision=1)

        second_occupant = self.registry.create_principal(
            self.steward_token, "resident:grace-occupant-2", "resident", office_id="office:grace")
        self.registry.create_occupant(self.steward_token, "occupant:grace-2",
                                      principal_id="resident:grace-occupant-2")
        self.registry.create_implementation(self.steward_token, "impl:reasoner-2", kind="model",
                                            provider_ref="local:replacement", revision="2")
        second_binding = self.registry.bind_office(
            self.steward_token, "office:grace", "occupant:grace-2", "impl:reasoner-2")
        self.registry.grant(self.steward_token, "resident:grace-occupant-2",
                            "office.state.write", "office:office:grace",
                            policy_ref="rv.policy:office-state.v1")
        snapshot = self.registry.office_snapshot("office:grace")
        self.assertEqual(first_binding, 1)
        self.assertEqual(second_binding, 2)
        self.assertEqual(snapshot["office_role"], "engineering-director")
        self.assertEqual(snapshot["occupant_id"], "occupant:grace-2")
        self.assertEqual(snapshot["implementation_id"], "impl:reasoner-2")
        self.assertEqual(snapshot["state"], {"objective_id": "objective:durable"})
        self.assertEqual(snapshot["state_revision"], 2)
        with self.assertRaises(AuthorityDenied):
            self.registry.authorize(occupant_one, "office.state.write", "office:office:grace")
        self.registry.authorize(second_occupant, "office.state.write", "office:office:grace")
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {self.schema}.institutional_authority_events WHERE event_type='authority_revoked'")
            self.assertEqual(cur.fetchone()[0], 1)

    def test_model_binding_compare_and_swap_preserves_occupant_and_supports_rollback(self):
        from riverview_core.institutional_authority import IdentityConflict
        self.registry.create_office(self.steward_token, "office:binding-cas", "resident")
        self.registry.create_principal(self.steward_token, "resident:binding-cas", "resident")
        self.registry.create_occupant(self.steward_token, "occupant:binding-cas",
                                      principal_id="resident:binding-cas")
        for implementation, revision in (("impl:binding-before", "a" * 64),
                                          ("impl:binding-after", "b" * 64)):
            self.registry.create_implementation(self.steward_token, implementation,
                kind="model", provider_ref="test.provider", revision=revision)
        self.registry.bind_office(self.steward_token, "office:binding-cas",
            "occupant:binding-cas", "impl:binding-before")
        updated = self.registry.update_office_implementation(self.steward_token,
            "office:binding-cas", "impl:binding-after", expected_binding_revision=1)
        self.assertEqual(updated["occupant_id"], "occupant:binding-cas")
        self.assertEqual(updated["binding_revision"], 2)
        with self.assertRaises(IdentityConflict):
            self.registry.update_office_implementation(self.steward_token,
                "office:binding-cas", "impl:binding-before", expected_binding_revision=1)
        rolled_back = self.registry.update_office_implementation(self.steward_token,
            "office:binding-cas", "impl:binding-before",
            expected_binding_revision=updated["binding_revision"])
        snapshot = self.registry.office_snapshot("office:binding-cas")
        self.assertEqual(rolled_back["binding_revision"], 3)
        self.assertEqual(snapshot["occupant_id"], "occupant:binding-cas")
        self.assertEqual(snapshot["implementation_id"], "impl:binding-before")
        with self.admin.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM {self.schema}.institutional_authority_events "
                        "WHERE event_type='office_model_implementation_changed'")
            self.assertEqual(cur.fetchone()[0], 2)

    def test_office_state_restart_compare_and_swap_and_size_bound(self):
        from riverview_core.institutional_authority import IdentityConflict
        self.registry.create_office(self.steward_token, "office:restart", "specialist")
        token = self.registry.create_principal(self.steward_token, "resident:restart", "resident")
        occupant = "occupant:restart"
        implementation = "implementation:restart"
        self.registry.create_occupant(self.steward_token, occupant,
                                      principal_id="resident:restart")
        self.registry.create_implementation(self.steward_token, implementation,
                                            kind="tool", provider_ref="test.runtime",
                                            revision="restart-v1")
        self.registry.bind_office(self.steward_token, "office:restart", occupant,
                                  implementation)
        self.registry.grant(self.steward_token, "resident:restart", "office.state.write",
                            "office:office:restart", policy_ref="rv.policy:state.v1")
        self.registry.set_office_state(token, "office:restart", {"plan_revision": 1}, expected_revision=1)
        self.registry.close()
        from riverview_core.institutional_authority import AuthorityRegistry
        self.registry = AuthorityRegistry(DSN, schema=self.schema)
        with self.assertRaises(IdentityConflict):
            self.registry.set_office_state(token, "office:restart", {"plan_revision": 2}, expected_revision=1)
        self.assertEqual(self.registry.office_snapshot("office:restart")["state"], {"plan_revision": 1})
        with self.assertRaises(ValueError):
            self.registry.set_office_state(token, "office:restart", {"large": "x" * 70000})

    def test_authority_event_ledger_is_append_only(self):
        import psycopg
        from psycopg import sql
        with self.assertRaises(psycopg.errors.RaiseException):
            self.admin.execute(sql.SQL("DELETE FROM {}.institutional_authority_events").format(
                sql.Identifier(self.schema)))


if __name__ == "__main__":
    unittest.main()
