// Revision: 1.1.0
// Focused contract checks for the V2 wrapper around the existing permission API.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..', 'website/v2/deployed');
const read = (name) => fs.readFileSync(path.join(root, name), 'utf8');

test('V2 navigation opens the resident permission workspace and refreshes its existing registry', () => {
  const html = read('index.html');
  const shell = read('assets/workspace.js');
  const client = read('assets/resident-permissions.js');
  const model = read('assets/resident-permissions-model.js');
  assert.match(html, /data-view="resident-permissions"/);
  assert.match(html, /id="resident-permissions-workspace"[^>]*hidden/);
  assert.match(html, /id="resident-permission-refresh"/);
  assert.match(html, /resident-permissions-model\.js[^\n]*dynamic-authority-catalog/);
  assert.ok(html.indexOf('resident-permissions-model.js') < html.indexOf('resident-permissions.js'));
  assert.match(shell, /resident-permissions-workspace/);
  assert.match(shell, /rv:resident-permissions/);
  assert.match(client, /fetch\(path/);
  assert.match(client, /credentials:"same-origin"/);
  assert.match(client, /cache:"no-store"/);
  assert.match(client, /GET/);
  assert.match(client, /api\/v1\/resident-permissions/);
  assert.match(model, /assignableCapabilities/);
});

test('a newly registered authority capability appears from API data without a website capability list', () => {
  const context = {window: {}};
  vm.runInNewContext(read('assets/resident-permissions-model.js'), context);
  const registeredLater = {
    capabilities: [{capability_id:'newly.registered.operation', description:'New registered operation',
      authority_action:'new.operation.execute', implementation_ref:'new.executor.v1', enabled:true,
      dependencies:['service:new'], resource_ids:['service:new'] }],
    resources: [{resource_id:'service:new',resource_kind:'service',classification:'internal'}],
    profiles: [{principal_id:'resident:test',rules:[{capability_id:'newly.registered.operation',resource_id:'service:new'}],inherited_rules:[]}],
  };
  const model = context.window.RVResidentPermissionsModel.create(registeredLater);
  assert.equal(model.capabilities[0].capability_id, 'newly.registered.operation');
  assert.equal(model.assignableCapabilities[0].authority_action, 'new.operation.execute');
  assert.equal(model.profileReferences(registeredLater.profiles[0])[0].status, 'registered');
  assert.deepEqual(Array.from(model.capability('newly.registered.operation').dependencies), ['service:new']);
  const client = read('assets/resident-permissions.js');
  assert.doesNotMatch(client, /newly\.registered\.operation|resident\.status\.read|cme\.progress\.read/);
});

test('removed registry entries remain visible as unavailable profile references and are not editable', () => {
  const context = {window: {}};
  vm.runInNewContext(read('assets/resident-permissions-model.js'), context);
  const payload = {capabilities:[],resources:[],profiles:[{principal_id:'resident:test',
    rules:[{capability_id:'retired.operation'}],inherited_rules:[]}]};
  const model = context.window.RVResidentPermissionsModel.create(payload);
  assert.equal(model.profileReferences(payload.profiles[0])[0].status, 'unavailable');
  assert.equal(model.unavailableReferences[0].capability_id, 'retired.operation');
  assert.match(read('assets/resident-permissions.js'), /editing this profile is disabled to avoid silently dropping/);
});

test('Permissions renders operation schema, authority contract, provenance, and effective decision from registry data', async () => {
  const listeners = {};
  const nodes = {
    'resident-permission-list': {innerHTML:'',textContent:'',querySelectorAll:() => []},
    'resident-permission-state': {textContent:''},
    'resident-permission-refresh': {addEventListener:() => {}},
  };
  const context = {
    window: {addEventListener:(name,fn) => {listeners[name]=fn;}},
    document: {cookie:'',getElementById:(id) => nodes[id] || null},
    fetch: async () => ({ok:true,json:async () => ({
      capabilities:[{capability_id:'runtime.new.read',description:'Runtime new read',authority_action:'runtime.new.read',
        implementation_ref:'runtime.adapter.v1',owner_office:'office:ops',dependencies:['service:ops'],
        approval_default:false,enabled:true,input_schema:{type:'object',additionalProperties:false},
        authorization_contract:{mode:'exact_grant',action:'runtime.new.read',scope_policy:'exact_scope'},
        availability_policy:'executor_and_worker_health',declaration_source:'runtime-declarations',
        declaration_source_commit:'deadcafe',registration_blocker:null,resource_ids:['service:ops']}],
      resources:[{resource_id:'service:ops',resource_kind:'service',classification:'internal',owner_office:'office:ops'}],
      profiles:[{principal_id:'resident:ops',status:'active',effective_status:'active',identity_status:'active',
        tier:'operator',revision:2,classification_ceiling:'internal',export_mode:'deny',rules:[],inherited_rules:[],audit:[],
        standing_grants:[{action:'runtime.new.read',scope_ref:'service:ops',grant_id:'g1'}],
        effective_permissions:[{capability_id:'runtime.new.read',authority_action:'runtime.new.read',resource_id:'service:ops',
          access_level:'read',classification:'internal',export:false,exact_grant_status:'active',grant_id:'g1',
          effective_status:'authorized',policy_decision:{allowed:true,mode:'legacy_exact_grant_only'}}]}],
    })}),
  };
  vm.runInNewContext(read('assets/resident-permissions-model.js'), context);
  vm.runInNewContext(read('assets/resident-permissions.js'), context);
  await listeners['rv:resident-permissions']();
  const rendered = nodes['resident-permission-list'].innerHTML;
  assert.match(rendered, /runtime\.new\.read/);
  assert.match(rendered, /Input schema:/);
  assert.match(rendered, /Authorization contract:/);
  assert.match(rendered, /runtime-declarations/);
  assert.match(rendered, /deadcafe/);
  assert.match(rendered, /authorized/);
  assert.match(rendered, /service:ops/);
});

test('V2 retains existing pending revision, explicit activation, revoke and CAS operations', () => {
  const client = read('assets/resident-permissions.js');
  assert.match(client, /expected_revision:Number\(selected\.revision/);
  assert.match(client, /\/PUT"|"PUT"/);
  assert.match(client, /data-approve/);
  assert.match(client, /data-revoke/);
  assert.match(client, /transition\("approve"/);
  assert.match(client, /transition\("revoke"/);
  assert.match(client, /window\.confirm\(prompt\)/);
  assert.match(client, /Save creates a pending revision/);
  assert.match(client, /office\.manage/);
});

test('missing institutional identity and denied/unavailable API responses are explicit and do not fabricate data', () => {
  const client = read('assets/resident-permissions.js');
  assert.match(client, /steward_account_required/);
  assert.match(client, /Institutional Steward identity is unavailable/);
  assert.match(client, /resident_permission_registry_unavailable/);
  assert.match(client, /authenticated/);
  assert.match(client, /no records were returned and no change was made/i);
});

test('V2 permission screen is responsive and keeps the server as the authority boundary', () => {
  const html = read('index.html');
  const css = read('assets/resident-permissions.css');
  const server = fs.readFileSync(path.join(__dirname, '..', 'src/riverview_core/status_dashboard/server.py'), 'utf8');
  assert.match(html, /the exact <code>office\.manage<\/code> grant/);
  assert.match(server, /not identity or "steward" not in identity\.get\("roles", \(\)\)/);
  assert.match(server, /not identity\.get\("authority_principal_id"\)/);
  assert.match(server, /resident_permission_change_not_authorized/);
  assert.match(css, /@media\(max-width:600px\)/);
});
