-- =============================================================================
-- RIVERVIEW~ CONTROLLED SQL MIGRATION
-- File: src/riverview_core/institutional_authority/migrations/0008_resident_permission_profiles.sql
-- Component: RESIDENT-PERMISSION-PROFILES
-- Revision: 1.0.7
-- Purpose: Add audited profiles, capability/resource catalog metadata and policy gate
-- Execution Model: Explicit additive PostgreSQL migration; never applied by application startup
-- Observability: Profile revision events and deterministic profile decision function
-- Dependencies: PostgreSQL 16; authority migrations 0001-0007
-- Authority: Does not issue authority grants or activate any resident profile
-- Tests: tests/test_permission_profiles.py; disposable PostgreSQL migration suite
-- History: Git and .riverview-backups/manifest.jsonl
-- =============================================================================
CREATE TABLE capability_catalog (
    capability_id TEXT PRIMARY KEY,
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 1000),
    authority_action TEXT UNIQUE NOT NULL,
    owner_office TEXT,
    implementation_ref TEXT NOT NULL,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(dependencies)='array'),
    approval_default BOOLEAN NOT NULL DEFAULT TRUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (length(capability_id)>0 AND length(authority_action)>0)
);

CREATE TABLE resource_catalog (
    resource_id TEXT PRIMARY KEY,
    resource_kind TEXT NOT NULL CHECK (resource_kind IN
        ('host','service','database','filesystem','model','adapter','institutional')),
    description TEXT NOT NULL CHECK (length(description) BETWEEN 1 AND 1000),
    classification TEXT NOT NULL CHECK (classification IN
        ('public','internal','confidential','restricted')),
    owner_office TEXT,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(dependencies)='array'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE capability_resources (
    capability_id TEXT NOT NULL REFERENCES capability_catalog(capability_id),
    resource_id TEXT NOT NULL REFERENCES resource_catalog(resource_id),
    implementation_ref TEXT NOT NULL,
    PRIMARY KEY (capability_id,resource_id)
);

CREATE TABLE resident_permission_tiers (
    tier_id TEXT PRIMARY KEY CHECK (tier_id IN
        ('observer','operator','administrator','institutional_administrator')),
    tier_rank SMALLINT NOT NULL UNIQUE CHECK (tier_rank BETWEEN 1 AND 4),
    label TEXT NOT NULL,
    description TEXT NOT NULL,
    profile_only BOOLEAN NOT NULL DEFAULT TRUE
);
INSERT INTO resident_permission_tiers(tier_id,tier_rank,label,description) VALUES
 ('observer',1,'Observer','Read authorized information and inspect permitted status, logs, and reports.'),
 ('operator',2,'Operator','Use authorized tools, perform routine operations, and update assigned work.'),
 ('administrator',3,'Administrator','Manage assigned services, hosts, filesystems, databases, and operational resources.'),
 ('institutional_administrator',4,'Institutional Administrator','Broad cross-system operations only within explicitly delegated institutional boundaries.');

CREATE TABLE resident_permission_profiles (
    principal_id TEXT PRIMARY KEY REFERENCES institutional_principals(principal_id),
    office_id TEXT NOT NULL REFERENCES institutional_offices(office_id),
    tier_id TEXT NOT NULL REFERENCES resident_permission_tiers(tier_id),
    status TEXT NOT NULL CHECK (status IN ('pending','active','suspended','revoked')),
    revision BIGINT NOT NULL CHECK (revision>0),
    classification_ceiling TEXT NOT NULL CHECK (classification_ceiling IN
        ('public','internal','confidential','restricted')),
    export_mode TEXT NOT NULL CHECK (export_mode IN ('deny','allow')),
    created_by TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    approved_by TEXT REFERENCES institutional_principals(principal_id),
    approved_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((status='active' AND approved_by IS NOT NULL AND approved_at IS NOT NULL)
        OR status<>'active')
);

-- Pending edits are separate from the effective profile. Editing a live profile
-- never temporarily removes its current policy gate or activates proposed rules.
CREATE TABLE resident_permission_profile_drafts (
    principal_id TEXT PRIMARY KEY REFERENCES institutional_principals(principal_id),
    expected_active_revision BIGINT NOT NULL CHECK (expected_active_revision>=0),
    draft_revision BIGINT NOT NULL CHECK (draft_revision>0),
    profile JSONB NOT NULL CHECK (jsonb_typeof(profile)='object'),
    created_by TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE resident_permission_tier_rules (
    rule_id UUID PRIMARY KEY,
    tier_id TEXT NOT NULL REFERENCES resident_permission_tiers(tier_id),
    capability_id TEXT NOT NULL REFERENCES capability_catalog(capability_id),
    resource_id TEXT NOT NULL,
    effect TEXT NOT NULL CHECK (effect IN ('allow','deny')),
    access_level TEXT NOT NULL CHECK (access_level IN ('read','write','execute','administer','delegate')),
    approval_required BOOLEAN NOT NULL DEFAULT TRUE,
    data_classification TEXT NOT NULL CHECK (data_classification IN ('public','internal','confidential','restricted')),
    export_mode TEXT NOT NULL CHECK (export_mode IN ('deny','allow')),
    provenance_ref TEXT NOT NULL,
    valid_until TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE resident_permission_rules (
    rule_id UUID PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES resident_permission_profiles(principal_id),
    capability_id TEXT NOT NULL REFERENCES capability_catalog(capability_id),
    resource_id TEXT NOT NULL,
    effect TEXT NOT NULL CHECK (effect IN ('allow','deny')),
    access_level TEXT NOT NULL CHECK (access_level IN ('read','write','execute','administer','delegate')),
    approval_required BOOLEAN NOT NULL DEFAULT TRUE,
    data_classification TEXT NOT NULL CHECK (data_classification IN ('public','internal','confidential','restricted')),
    export_mode TEXT NOT NULL CHECK (export_mode IN ('deny','allow')),
    provenance_ref TEXT NOT NULL,
    valid_until TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (resource_id='*' OR length(resource_id)>0)
);
CREATE INDEX resident_permission_rule_lookup_idx
    ON resident_permission_rules(principal_id,capability_id,resource_id)
    WHERE revoked_at IS NULL;

CREATE TABLE resident_permission_events (
    event_id UUID PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    actor_id TEXT NOT NULL REFERENCES institutional_principals(principal_id),
    event_type TEXT NOT NULL CHECK (event_type IN
      ('profile_saved','profile_approved','profile_suspended','profile_revoked')),
    profile_revision BIGINT NOT NULL,
    snapshot JSONB NOT NULL CHECK (jsonb_typeof(snapshot)='object'),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX resident_permission_events_subject_idx
    ON resident_permission_events(principal_id,recorded_at,event_id);
CREATE FUNCTION reject_resident_permission_event_mutation()
RETURNS trigger LANGUAGE plpgsql AS $rv$
BEGIN RAISE EXCEPTION 'resident_permission_events is append-only'; END;
$rv$;
CREATE TRIGGER resident_permission_events_append_only
    BEFORE UPDATE OR DELETE ON resident_permission_events
    FOR EACH ROW EXECUTE FUNCTION reject_resident_permission_event_mutation();

-- Metadata only. Operational status/capacity continues to come from the owning
-- worker/provider/service health projections and is not implied by registration.
INSERT INTO capability_catalog(capability_id,description,authority_action,owner_office,implementation_ref,dependencies,approval_default) VALUES
 ('resident.status.read','Read bounded institutional status projections','resident.status.read','office:grace','dashboard.projection.v1','["riverview.status-dashboard"]',false),
 ('cme.progress.read','Inspect CME progress and ready work','cme.progress.read','office:grace','cme.monitor.v1','["postgres.cme-ledger"]',false),
 ('engineering.work_order.submit','Submit a governed Engineering objective','objective.submit','office:grace','grace.execution-pipeline.v1','["assignment-intake","office:engineering"]',true),
 ('engineering.assignment.create','Create an authorized Engineering assignment','assignment.create','office:grace','assignment-intake.v1','["work-order-scope","exact-grant"]',true),
 ('engineering.assignment.cancel','Cancel eligible queued Engineering work','assignment.cancel','office:grace','grace.execution-pipeline.v1','["work-order-scope","lease-state"]',true),
 ('engineering.assignment.execute','Execute an authorized Engineering assignment','assignment.execute','office:engineering','worker-adapter.v1','["registered-worker","assignment-lease"]',true),
 ('codex.cli.execute','Execute bounded work through supervised Codex CLI','codex.execute','office:engineering','codex.cli.adapter.v1','["supervised-codex-cli","approved-workspace"]',true),
 ('resident.office.state.write','Persist bounded state for the currently bound office occupant','office.state.write','office:grace','AuthorityRegistry.set_office_state.v1','["current-occupant","exact-grant","expected-revision"]',true),
 ('resource.status.read','Inspect capability/resource readiness and capacity','resource.status.read','office:grace','capability-resource-projection.v1','["provider-health","capacity-observation"]',false),
 ('operations.shell.execute','Run an institutionally approved bounded command','host.command.execute','office:operations','authorized-command-adapter.v1','["named-command","approved-host","service-identity"]',true),
 ('operations.ssh.execute','Use approved SSH operations on a registered host','host.ssh.execute','office:operations','authorized-ssh-adapter.v1','["host-alias","credential-reference","approved-operation"]',true),
 ('operations.filesystem.inspect','Inspect files under an authorized path scope','filesystem.read','office:operations','bounded-filesystem-adapter.v1','["path-scope","classification-policy"]',false),
 ('operations.filesystem.modify','Modify files under an authorized path scope','filesystem.write','office:operations','bounded-filesystem-adapter.v1','["path-scope","change-record","rollback"]',true),
 ('operations.database.inspect','Read authorized operational database projections','database.read','office:operations','read-only-database-adapter.v1','["database-scope","approved-query"]',false),
 ('operations.database.update','Apply an approved operational database mutation','database.write','office:operations','governed-database-adapter.v1','["migration-or-transaction","backup","rollback"]',true),
 ('operations.service.monitor','Inspect service health and diagnostics','service.monitor','office:operations','service-monitor.v1','["registered-service","health-contract"]',false),
 ('operations.service.recover','Perform an approved service recovery action','service.recover','office:operations','service-recovery.v1','["approved-recovery-plan","rollback"]',true),
 ('cme.progress.coordinate','Coordinate authorized CME progression','cme.progress.coordinate','office:grace','cme.monitor.v1','["durable-objective","exact-grant"]',true);
INSERT INTO resource_catalog(resource_id,resource_kind,description,classification,owner_office,dependencies) VALUES
 ('institution:riverview','institutional','Riverview institutional state and bounded projections','internal','office:steward','[]'),
 ('work-order:engineering','institutional','Governed Engineering work-order scope','internal','office:engineering','["exact-assignment-grant"]'),
 ('office:office:grace','institutional','Grace office-scoped durable state','confidential','office:steward','["current-bound-occupant"]'),
 ('service:riverview-status-dashboard','service','Authenticated Riverview status dashboard','internal','office:operations','["postgresql"]'),
 ('service:riverview-cme-monitor','service','Continuous Momentum Engine monitoring service','internal','office:operations','["postgresql"]'),
 ('service:riverview-assignment-intake','service','Governed Engineering assignment intake','internal','office:engineering','["objective-submit-grant"]'),
 ('service:riverview-event-processor','service','Durable event progression and recovery','internal','office:operations','["postgresql-outbox"]'),
 ('host:camrui-authorized','host','Camrui host actions limited to separately authorized exact resources','confidential','office:operations','["host-identity","specific-authority-grant"]'),
 ('path:approved-engineering-workspace','filesystem','Steward-approved Engineering workspace only','confidential','office:engineering','["filesystem-scope-grant"]'),
 ('database:riverview-operational','database','Operational data through approved projections and transactions','confidential','office:operations','["database-scope-grant","migration-policy"]'),
 ('adapter:codex-cli-supervised','adapter','Supervised subscription-authenticated Codex execution','internal','office:engineering','["approved-work-order","authenticated-cli-session"]');
INSERT INTO capability_resources(capability_id,resource_id,implementation_ref) VALUES
 ('resident.status.read','institution:riverview','dashboard.projection.v1'),
 ('cme.progress.read','institution:riverview','cme.monitor.v1'),
 ('engineering.work_order.submit','work-order:engineering','grace.execution-pipeline.v1'),
 ('engineering.assignment.create','work-order:engineering','assignment-intake.v1'),
 ('engineering.assignment.cancel','work-order:engineering','grace.execution-pipeline.v1'),
 ('engineering.assignment.execute','work-order:engineering','worker-adapter.v1'),
 ('engineering.assignment.execute','adapter:codex-cli-supervised','worker-adapter.v1'),
 ('codex.cli.execute','work-order:engineering','codex.cli.adapter.v1'),
 ('codex.cli.execute','adapter:codex-cli-supervised','codex.cli.adapter.v1'),
 ('resident.office.state.write','office:office:grace','AuthorityRegistry.set_office_state.v1'),
 ('resource.status.read','institution:riverview','capability-resource-projection.v1'),
 ('operations.shell.execute','host:camrui-authorized','authorized-command-adapter.v1'),
 ('operations.ssh.execute','host:camrui-authorized','authorized-ssh-adapter.v1'),
 ('operations.filesystem.inspect','path:approved-engineering-workspace','bounded-filesystem-adapter.v1'),
 ('operations.filesystem.modify','path:approved-engineering-workspace','bounded-filesystem-adapter.v1'),
 ('operations.database.inspect','database:riverview-operational','read-only-database-adapter.v1'),
 ('operations.database.update','database:riverview-operational','governed-database-adapter.v1'),
 ('operations.service.monitor','service:riverview-status-dashboard','service-monitor.v1'),
 ('operations.service.monitor','service:riverview-cme-monitor','service-monitor.v1'),
 ('operations.service.monitor','service:riverview-assignment-intake','service-monitor.v1'),
 ('operations.service.monitor','service:riverview-event-processor','service-monitor.v1'),
 ('operations.service.recover','service:riverview-status-dashboard','service-recovery.v1'),
 ('operations.service.recover','service:riverview-cme-monitor','service-recovery.v1'),
 ('operations.service.recover','service:riverview-assignment-intake','service-recovery.v1'),
 ('operations.service.recover','service:riverview-event-processor','service-recovery.v1'),
 ('cme.progress.coordinate','institution:riverview','cme.monitor.v1');

-- Tier policies are onboarding defaults only. They still require exact grants,
-- resident-specific profile activation, resource scopes and all safety checks.
INSERT INTO resident_permission_tier_rules(rule_id,tier_id,capability_id,resource_id,effect,
 access_level,approval_required,data_classification,export_mode,provenance_ref)
SELECT gen_random_uuid(),tier.tier_id,policy.capability_id,'*','allow',policy.access_level,
 policy.approval_required,'restricted','deny','policy:resident-tier-defaults.v1'
FROM resident_permission_tiers tier
JOIN (VALUES
 (1,'resident.status.read','read',false),
 (1,'cme.progress.read','read',false),
 (1,'resource.status.read','read',false),
 (1,'operations.filesystem.inspect','read',false),
 (1,'operations.database.inspect','read',false),
 (1,'operations.service.monitor','read',false),
 (2,'engineering.work_order.submit','write',false),
 (2,'engineering.assignment.create','write',false),
 (2,'engineering.assignment.cancel','write',true),
 (2,'cme.progress.coordinate','write',false),
 (3,'resident.office.state.write','write',true),
 (3,'operations.shell.execute','execute',true),
 (3,'operations.ssh.execute','execute',true),
 (3,'operations.filesystem.modify','write',true),
 (3,'operations.database.update','write',true),
 (3,'operations.service.recover','administer',true),
 (4,'engineering.assignment.execute','execute',true),
 (4,'codex.cli.execute','execute',true)
) AS policy(min_tier,capability_id,access_level,approval_required)
 ON tier.tier_rank>=policy.min_tier;

CREATE FUNCTION list_resident_permission_profiles(p_actor TEXT)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER AS $rv$
DECLARE result JSONB;
BEGIN
 PERFORM 1 FROM institutional_principals p
   JOIN authority_grants g ON g.principal_id=p.principal_id
   WHERE p.principal_id=p_actor AND p.principal_kind='steward' AND p.status='active'
     AND g.action='office.manage' AND g.scope_ref='institution'
     AND g.revoked_at IS NULL AND g.valid_from<=clock_timestamp()
     AND (g.valid_until IS NULL OR g.valid_until>clock_timestamp())
   FOR SHARE OF p,g;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'resident permission profile access denied' USING ERRCODE='42501';
 END IF;
 SELECT jsonb_build_object(
   'profiles',COALESCE((SELECT jsonb_agg(jsonb_build_object(
      'principal_id',i.principal_id,'principal_kind',i.principal_kind,
      'identity_status',i.status,'office_id',COALESCE(p.office_id,i.office_id),
      'profile_office_id',p.office_id,'current_office_id',i.office_id,
      'office_role',o.office_role,'tier',COALESCE(d.profile->>'tier',p.tier_id),
      'status',CASE WHEN d.principal_id IS NOT NULL THEN 'pending' ELSE p.status END,
      'effective_status',p.status,'revision',COALESCE(d.draft_revision,p.revision,0),
      'has_pending_changes',d.principal_id IS NOT NULL,
      'classification_ceiling',COALESCE(d.profile->>'classification_ceiling',p.classification_ceiling),
      'export_mode',COALESCE(d.profile->>'export_mode',p.export_mode),
      'created_by',p.created_by,'approved_by',p.approved_by,'approved_at',p.approved_at,
      'rules',COALESCE(d.profile->'rules',(SELECT jsonb_agg(to_jsonb(r)-'principal_id') FROM resident_permission_rules r
         WHERE r.principal_id=i.principal_id AND r.revoked_at IS NULL),'[]'::jsonb),
      'inherited_rules',COALESCE((SELECT jsonb_agg(to_jsonb(tr)-'rule_id' ORDER BY tr.capability_id,tr.resource_id)
         FROM resident_permission_tier_rules tr
         JOIN resident_permission_tiers rule_tier ON rule_tier.tier_id=tr.tier_id
         JOIN resident_permission_tiers active_tier ON active_tier.tier_id=COALESCE(d.profile->>'tier',p.tier_id)
         WHERE rule_tier.tier_rank<=active_tier.tier_rank AND tr.revoked_at IS NULL),'[]'::jsonb),
      'audit',COALESCE((SELECT jsonb_agg(jsonb_build_object('event_type',e.event_type,
         'actor_id',e.actor_id,'revision',e.profile_revision,'recorded_at',e.recorded_at)
         ORDER BY e.recorded_at DESC) FROM resident_permission_events e
         WHERE e.principal_id=i.principal_id),'[]'::jsonb),
      'standing_grants',COALESCE((SELECT jsonb_agg(jsonb_build_object('grant_id',g.grant_id,
         'action',g.action,'scope_ref',g.scope_ref,'policy_ref',g.policy_ref,
         'valid_from',g.valid_from,'valid_until',g.valid_until,'revoked_at',g.revoked_at)
         ORDER BY g.created_at,g.grant_id) FROM authority_grants g
         WHERE g.principal_id=i.principal_id),'[]'::jsonb)) ORDER BY i.principal_id)
     FROM institutional_principals i
     LEFT JOIN resident_permission_profiles p USING(principal_id)
     LEFT JOIN resident_permission_profile_drafts d USING(principal_id)
     LEFT JOIN institutional_offices o ON o.office_id=COALESCE(p.office_id,i.office_id)
     WHERE i.principal_kind='resident'),'[]'::jsonb),
   'tiers',(SELECT jsonb_agg(to_jsonb(t) ORDER BY t.tier_id) FROM resident_permission_tiers t),
   'capabilities',(SELECT jsonb_agg(
      to_jsonb(c)||jsonb_build_object('resource_ids',
        COALESCE((SELECT jsonb_agg(cr.resource_id ORDER BY cr.resource_id) FROM capability_resources cr
          WHERE cr.capability_id=c.capability_id),'[]'::jsonb))
      ORDER BY c.capability_id)
      FROM capability_catalog c WHERE c.enabled),
   'tier_rules',(SELECT COALESCE(jsonb_agg(to_jsonb(tr) ORDER BY tr.tier_id,tr.capability_id,tr.resource_id),'[]'::jsonb)
      FROM resident_permission_tier_rules tr WHERE tr.revoked_at IS NULL),
   'resources',(SELECT jsonb_agg(to_jsonb(r) ORDER BY r.resource_id) FROM resource_catalog r)) INTO result;
 RETURN result;
END;
$rv$;

CREATE FUNCTION save_resident_permission_profile(p_actor TEXT,p_resident TEXT,
 p_expected_revision BIGINT,p_profile JSONB) RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER AS $rv$
DECLARE current_revision BIGINT; active_revision BIGINT; new_revision BIGINT;
        resident_office TEXT; rule JSONB;
BEGIN
 PERFORM 1 FROM institutional_principals p
   JOIN authority_grants g ON g.principal_id=p.principal_id
   WHERE p.principal_id=p_actor AND p.principal_kind='steward' AND p.status='active'
     AND g.action='office.manage' AND g.scope_ref='institution' AND g.revoked_at IS NULL
     AND g.valid_from<=clock_timestamp() AND (g.valid_until IS NULL OR g.valid_until>clock_timestamp())
   FOR SHARE OF p,g;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'resident permission profile update denied' USING ERRCODE='42501';
 END IF;
 IF p_profile IS NULL OR jsonb_typeof(p_profile) IS DISTINCT FROM 'object'
   OR (p_profile - ARRAY['tier','classification_ceiling','export_mode','rules'])<>'{}'::jsonb
   OR jsonb_typeof(p_profile->'rules') IS DISTINCT FROM 'array'
   OR octet_length(p_profile::text)>32768
   OR jsonb_array_length(CASE WHEN jsonb_typeof(p_profile->'rules')='array'
           THEN p_profile->'rules' ELSE '[]'::jsonb END)>256 THEN
   RAISE EXCEPTION 'invalid permission profile';
 END IF;
 SELECT office_id INTO resident_office FROM institutional_principals
   WHERE principal_id=p_resident AND principal_kind='resident' AND status='active' FOR UPDATE;
 IF resident_office IS NULL THEN RAISE EXCEPTION 'active resident principal and office required'; END IF;
 SELECT revision INTO active_revision FROM resident_permission_profiles WHERE principal_id=p_resident FOR UPDATE;
 SELECT draft_revision INTO current_revision FROM resident_permission_profile_drafts WHERE principal_id=p_resident FOR UPDATE;
 current_revision:=COALESCE(current_revision,active_revision,0);
 IF current_revision<>p_expected_revision THEN
   RAISE EXCEPTION 'permission profile revision conflict' USING ERRCODE='40001';
 END IF;
 IF p_profile->>'tier' IS NULL OR p_profile->>'tier' NOT IN ('observer','operator','administrator','institutional_administrator')
   OR p_profile->>'classification_ceiling' IS NULL OR p_profile->>'classification_ceiling' NOT IN ('public','internal','confidential','restricted')
   OR p_profile->>'export_mode' IS NULL OR p_profile->>'export_mode' NOT IN ('deny','allow') THEN RAISE EXCEPTION 'invalid profile policy'; END IF;
 new_revision:=current_revision+1;
 FOR rule IN SELECT value FROM jsonb_array_elements(p_profile->'rules') LOOP
   IF jsonb_typeof(rule) IS DISTINCT FROM 'object'
      OR (rule - ARRAY['capability_id','resource_id','effect','access_level','approval_required',
          'valid_until','data_classification','export_mode','provenance_ref'])<>'{}'::jsonb
      OR NOT (rule ?& ARRAY['capability_id','resource_id','effect','access_level',
          'approval_required','valid_until','data_classification','export_mode','provenance_ref'])
      OR octet_length(rule::text)>2048
      OR NOT EXISTS(SELECT 1 FROM capability_catalog WHERE capability_id=rule->>'capability_id' AND enabled)
      OR NOT EXISTS(SELECT 1 FROM capability_resources cr
          WHERE cr.capability_id=rule->>'capability_id'
            AND (rule->>'resource_id'='*' OR cr.resource_id=rule->>'resource_id'))
      OR rule->>'effect' IS NULL OR rule->>'effect' NOT IN ('allow','deny')
      OR rule->>'access_level' IS NULL OR rule->>'access_level' NOT IN ('read','write','execute','administer','delegate')
      OR rule->>'data_classification' IS NULL OR rule->>'data_classification' NOT IN ('public','internal','confidential','restricted')
      OR rule->>'export_mode' IS NULL OR rule->>'export_mode' NOT IN ('deny','allow')
      OR jsonb_typeof(rule->'approval_required') IS DISTINCT FROM 'boolean'
      OR (rule->'valid_until'<>'null'::jsonb AND jsonb_typeof(rule->'valid_until') IS DISTINCT FROM 'string')
      OR COALESCE(length(rule->>'capability_id'),0)>256
      OR COALESCE(length(rule->>'resource_id'),0)>256
      OR COALESCE(length(rule->>'provenance_ref'),0)=0
      OR COALESCE(length(rule->>'provenance_ref'),0)>256
      OR (rule->>'valid_until' IS NOT NULL AND (rule->>'valid_until')::timestamptz<=clock_timestamp())
      THEN RAISE EXCEPTION 'invalid permission rule'; END IF;
 END LOOP;
 INSERT INTO resident_permission_profile_drafts(principal_id,expected_active_revision,draft_revision,
   profile,created_by,created_at)
 VALUES(p_resident,COALESCE(active_revision,0),new_revision,p_profile,p_actor,clock_timestamp())
 ON CONFLICT(principal_id) DO UPDATE SET expected_active_revision=EXCLUDED.expected_active_revision,
   draft_revision=EXCLUDED.draft_revision,profile=EXCLUDED.profile,created_by=EXCLUDED.created_by,
   created_at=clock_timestamp();
 INSERT INTO resident_permission_events(event_id,principal_id,actor_id,event_type,profile_revision,snapshot)
 VALUES(gen_random_uuid(),p_resident,p_actor,'profile_saved',new_revision,p_profile);
 RETURN jsonb_build_object('principal_id',p_resident,'status','pending','revision',new_revision,
   'effective_revision',COALESCE(active_revision,0));
END;
$rv$;

CREATE FUNCTION approve_resident_permission_profile(p_actor TEXT,p_resident TEXT,p_expected_revision BIGINT)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER AS $rv$
DECLARE next_revision BIGINT;
        draft resident_permission_profile_drafts%ROWTYPE;
        rule JSONB; profile_row resident_permission_profiles%ROWTYPE;
BEGIN
 PERFORM 1 FROM institutional_principals p
   JOIN authority_grants g ON g.principal_id=p.principal_id
   WHERE p.principal_id=p_actor AND p.principal_kind='steward' AND p.status='active'
     AND g.action='office.manage' AND g.scope_ref='institution' AND g.revoked_at IS NULL
     AND g.valid_from<=clock_timestamp() AND (g.valid_until IS NULL OR g.valid_until>clock_timestamp())
   FOR SHARE OF p,g;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'resident permission profile approval denied' USING ERRCODE='42501'; END IF;
 SELECT * INTO draft FROM resident_permission_profile_drafts WHERE principal_id=p_resident FOR UPDATE;
 IF NOT FOUND OR draft.draft_revision<>p_expected_revision THEN
   RAISE EXCEPTION 'permission profile revision conflict' USING ERRCODE='40001'; END IF;
 SELECT * INTO profile_row FROM resident_permission_profiles WHERE principal_id=p_resident FOR UPDATE;
 IF COALESCE(profile_row.revision,0)<>draft.expected_active_revision THEN
   RAISE EXCEPTION 'active permission profile changed during review' USING ERRCODE='40001'; END IF;
 next_revision:=draft.draft_revision;
 INSERT INTO resident_permission_profiles(principal_id,office_id,tier_id,status,revision,
   classification_ceiling,export_mode,created_by,approved_by,approved_at)
 VALUES(p_resident,(SELECT office_id FROM institutional_principals WHERE principal_id=p_resident),
   draft.profile->>'tier','active',next_revision,draft.profile->>'classification_ceiling',
   draft.profile->>'export_mode',draft.created_by,p_actor,clock_timestamp())
 ON CONFLICT(principal_id) DO UPDATE SET office_id=EXCLUDED.office_id,tier_id=EXCLUDED.tier_id,
   status='active',revision=EXCLUDED.revision,classification_ceiling=EXCLUDED.classification_ceiling,
   export_mode=EXCLUDED.export_mode,created_by=EXCLUDED.created_by,approved_by=p_actor,
   approved_at=clock_timestamp(),updated_at=clock_timestamp();
 UPDATE resident_permission_rules SET revoked_at=clock_timestamp()
   WHERE principal_id=p_resident AND revoked_at IS NULL;
 FOR rule IN SELECT value FROM jsonb_array_elements(draft.profile->'rules') LOOP
   INSERT INTO resident_permission_rules(rule_id,principal_id,capability_id,resource_id,effect,
     access_level,approval_required,data_classification,export_mode,provenance_ref,valid_until)
   VALUES(gen_random_uuid(),p_resident,rule->>'capability_id',rule->>'resource_id',rule->>'effect',
     rule->>'access_level',(rule->>'approval_required')::boolean,rule->>'data_classification',
     rule->>'export_mode',rule->>'provenance_ref',NULLIF(rule->>'valid_until','')::timestamptz);
 END LOOP;
 DELETE FROM resident_permission_profile_drafts WHERE principal_id=p_resident;
 INSERT INTO resident_permission_events(event_id,principal_id,actor_id,event_type,profile_revision,snapshot)
 SELECT gen_random_uuid(),p_resident,p_actor,'profile_approved',p.revision,
   jsonb_build_object('tier',p.tier_id,'status',p.status,'revision',p.revision,
     'classification_ceiling',p.classification_ceiling,'export_mode',p.export_mode,
     'rules',draft.profile->'rules')
 FROM resident_permission_profiles p WHERE p.principal_id=p_resident;
 RETURN jsonb_build_object('principal_id',p_resident,'status','active','revision',next_revision);
END;
$rv$;

CREATE FUNCTION revoke_resident_permission_profile(p_actor TEXT,p_resident TEXT,p_expected_revision BIGINT)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER AS $rv$
DECLARE next_revision BIGINT; effective_revision BIGINT; v_draft_revision BIGINT;
BEGIN
 PERFORM 1 FROM institutional_principals p
   JOIN authority_grants g ON g.principal_id=p.principal_id
   WHERE p.principal_id=p_actor AND p.principal_kind='steward' AND p.status='active'
     AND g.action='office.manage' AND g.scope_ref='institution' AND g.revoked_at IS NULL
     AND g.valid_from<=clock_timestamp() AND (g.valid_until IS NULL OR g.valid_until>clock_timestamp())
   FOR SHARE OF p,g;
 IF NOT FOUND THEN
   RAISE EXCEPTION 'resident permission profile revocation denied' USING ERRCODE='42501'; END IF;
 SELECT revision INTO effective_revision FROM resident_permission_profiles WHERE principal_id=p_resident FOR UPDATE;
 SELECT d.draft_revision INTO v_draft_revision FROM resident_permission_profile_drafts d WHERE d.principal_id=p_resident FOR UPDATE;
 effective_revision:=COALESCE(v_draft_revision,effective_revision,0);
 IF effective_revision<>p_expected_revision THEN
   RAISE EXCEPTION 'permission profile revision conflict' USING ERRCODE='40001'; END IF;
 next_revision:=effective_revision+1;
 UPDATE resident_permission_profiles SET status='revoked',revision=next_revision,updated_at=clock_timestamp()
 WHERE principal_id=p_resident;
 DELETE FROM resident_permission_profile_drafts WHERE principal_id=p_resident;
 UPDATE resident_permission_rules SET revoked_at=clock_timestamp()
   WHERE principal_id=p_resident AND revoked_at IS NULL;
 INSERT INTO resident_permission_events(event_id,principal_id,actor_id,event_type,profile_revision,snapshot)
 VALUES(gen_random_uuid(),p_resident,p_actor,'profile_revoked',next_revision,
   jsonb_build_object('status','revoked','previous_revision',effective_revision));
 RETURN jsonb_build_object('principal_id',p_resident,'status','revoked','revision',next_revision);
END;
$rv$;

CREATE FUNCTION evaluate_resident_permission(p_resident TEXT,p_action TEXT,p_resource TEXT,
 p_access_level TEXT,p_classification TEXT,p_export BOOLEAN)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER AS $rv$
DECLARE profile resident_permission_profiles%ROWTYPE; selected RECORD; cap TEXT;
        resident_status TEXT; resident_office TEXT;
BEGIN
 SELECT * INTO profile FROM resident_permission_profiles WHERE principal_id=p_resident;
 IF NOT FOUND THEN
   RETURN jsonb_build_object('allowed',true,'mode','legacy_exact_grant_only','profile_revision',NULL);
 END IF;
 IF profile.status<>'active' THEN
   RETURN jsonb_build_object('allowed',false,'reason','profile_not_active','profile_revision',profile.revision);
 END IF;
 SELECT status,office_id INTO resident_status,resident_office FROM institutional_principals
   WHERE principal_id=p_resident AND principal_kind='resident';
 IF resident_status IS DISTINCT FROM 'active' OR resident_office IS DISTINCT FROM profile.office_id THEN
   RETURN jsonb_build_object('allowed',false,'reason','resident_identity_or_office_changed','profile_revision',profile.revision);
 END IF;
 IF p_access_level NOT IN ('read','write','execute','administer','delegate') OR
    p_classification NOT IN ('public','internal','confidential','restricted') THEN
   RETURN jsonb_build_object('allowed',false,'reason','invalid_permission_request','profile_revision',profile.revision);
 END IF;
 IF p_export AND profile.export_mode<>'allow' THEN
   RETURN jsonb_build_object('allowed',false,'reason','information_export_denied','profile_revision',profile.revision);
 END IF;
 IF array_position(ARRAY['public','internal','confidential','restricted'],p_classification) >
    array_position(ARRAY['public','internal','confidential','restricted'],profile.classification_ceiling) THEN
   RETURN jsonb_build_object('allowed',false,'reason','classification_exceeds_profile','profile_revision',profile.revision);
 END IF;
 SELECT capability_id INTO cap FROM capability_catalog WHERE authority_action=p_action AND enabled;
 IF cap IS NULL THEN RETURN jsonb_build_object('allowed',false,'reason','action_not_in_capability_catalog','profile_revision',profile.revision); END IF;
 IF NOT EXISTS(SELECT 1 FROM capability_resources cr
    WHERE cr.capability_id=cap AND cr.resource_id=p_resource) THEN
   RETURN jsonb_build_object('allowed',false,'reason','resource_not_registered_for_capability','profile_revision',profile.revision);
 END IF;
 SELECT policy.effect,policy.approval_required,policy.rule_id,
        policy.data_classification,policy.export_mode INTO selected FROM (
   SELECT r.effect,r.approval_required,r.rule_id,r.data_classification,r.export_mode,
     2 AS specificity,(r.resource_id=p_resource)::int AS resource_specificity
   FROM resident_permission_rules r WHERE r.principal_id=p_resident AND r.capability_id=cap
     AND r.resource_id IN (p_resource,'*') AND r.revoked_at IS NULL
     AND (r.valid_until IS NULL OR r.valid_until>clock_timestamp())
     AND array_position(ARRAY['read','write','execute','administer','delegate'],r.access_level) >=
         array_position(ARRAY['read','write','execute','administer','delegate'],p_access_level)
   UNION ALL
   SELECT r.effect,r.approval_required,r.rule_id,r.data_classification,r.export_mode,1,(r.resource_id=p_resource)::int
   FROM resident_permission_tier_rules r JOIN resident_permission_tiers rt ON rt.tier_id=r.tier_id
   JOIN resident_permission_tiers active_tier ON active_tier.tier_id=profile.tier_id
   WHERE rt.tier_rank<=active_tier.tier_rank AND r.capability_id=cap
     AND r.resource_id IN (p_resource,'*') AND r.revoked_at IS NULL
     AND (r.valid_until IS NULL OR r.valid_until>clock_timestamp())
     AND array_position(ARRAY['read','write','execute','administer','delegate'],r.access_level) >=
         array_position(ARRAY['read','write','execute','administer','delegate'],p_access_level)
 ) policy ORDER BY policy.specificity DESC,policy.resource_specificity DESC,
   (policy.effect='deny') DESC LIMIT 1;
 IF NOT FOUND THEN RETURN jsonb_build_object('allowed',false,'reason','no_matching_allow_rule','profile_revision',profile.revision); END IF;
 IF selected.effect='deny' THEN
   RETURN jsonb_build_object('allowed',false,'reason','explicit_deny','rule_id',selected.rule_id,'profile_revision',profile.revision);
 END IF;
 IF array_position(ARRAY['public','internal','confidential','restricted'],p_classification) >
    array_position(ARRAY['public','internal','confidential','restricted'],selected.data_classification) THEN
   RETURN jsonb_build_object('allowed',false,'reason','rule_classification_exceeded','rule_id',selected.rule_id,'profile_revision',profile.revision);
 END IF;
 IF p_export AND selected.export_mode<>'allow' THEN
   RETURN jsonb_build_object('allowed',false,'reason','rule_export_denied','rule_id',selected.rule_id,'profile_revision',profile.revision);
 END IF;
 RETURN jsonb_build_object('allowed',selected.effect='allow','reason',CASE WHEN selected.effect='allow' THEN 'profile_allow' ELSE 'explicit_deny' END,
   'approval_required',selected.approval_required,'rule_id',selected.rule_id,'profile_revision',profile.revision);
END;
$rv$;

REVOKE ALL ON FUNCTION list_resident_permission_profiles(TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION save_resident_permission_profile(TEXT,TEXT,BIGINT,JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION approve_resident_permission_profile(TEXT,TEXT,BIGINT) FROM PUBLIC;
REVOKE ALL ON FUNCTION revoke_resident_permission_profile(TEXT,TEXT,BIGINT) FROM PUBLIC;
REVOKE ALL ON FUNCTION evaluate_resident_permission(TEXT,TEXT,TEXT,TEXT,TEXT,BOOLEAN) FROM PUBLIC;

-- Keep SECURITY DEFINER name resolution pinned to this protected schema and
-- explicitly place pg_temp last to prevent temporary-object shadowing.
DO $pin$
DECLARE authority_schema TEXT := current_schema();
BEGIN
 EXECUTE format('ALTER FUNCTION %I.list_resident_permission_profiles(TEXT) SET search_path=%I,pg_catalog,pg_temp',authority_schema,authority_schema);
 EXECUTE format('ALTER FUNCTION %I.save_resident_permission_profile(TEXT,TEXT,BIGINT,JSONB) SET search_path=%I,pg_catalog,pg_temp',authority_schema,authority_schema);
 EXECUTE format('ALTER FUNCTION %I.approve_resident_permission_profile(TEXT,TEXT,BIGINT) SET search_path=%I,pg_catalog,pg_temp',authority_schema,authority_schema);
 EXECUTE format('ALTER FUNCTION %I.revoke_resident_permission_profile(TEXT,TEXT,BIGINT) SET search_path=%I,pg_catalog,pg_temp',authority_schema,authority_schema);
 EXECUTE format('ALTER FUNCTION %I.evaluate_resident_permission(TEXT,TEXT,TEXT,TEXT,TEXT,BOOLEAN) SET search_path=%I,pg_catalog,pg_temp',authority_schema,authority_schema);
END;
$pin$;
