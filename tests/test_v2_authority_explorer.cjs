const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const read = (name) => fs.readFileSync(path.join(root, name), 'utf8');

const html = read('website/v2/deployed/index.html');
const shell = read('website/v2/deployed/assets/workspace.js');
const explorer = read('website/v2/deployed/assets/authority-explorer.js');
assert.match(html, /data-view="settings"/);
assert.match(html, /id="settings-workspace"/);
for (const tab of ['preferences','notifications','accounts','residents','permissions','capabilities','hardware']) {
  assert.match(html, new RegExp(`data-settings-tab="${tab}"`));
}
assert.match(html, /id="notification-settings-workspace"/);
assert.match(html, /id="account-administration-workspace"/);
assert.match(html, /id="resident-permissions-workspace"/);
assert.match(html, /id="resource-monitor-workspace"/);
assert.match(shell, /RiverviewV2AuthorityExplorer\?\.renderResidents/);
assert.match(shell, /activateSettingsTab/);
assert.match(explorer, /fetch\("\/api\/v1\/resident-permissions"/);
assert.match(explorer, /credentials:"same-origin"/);
assert.match(explorer, /cache:"no-store"/);
assert.match(explorer, /No directory or registry data was exposed/);
assert.doesNotMatch(explorer, /RIVERVIEW_V2_FIXTURES|fixture-resident/);

const context = {window:{}, Object, Array, Map, Set};
vm.runInNewContext(read('website/v2/deployed/assets/resident-permissions-model.js'), context);
const payload = {
  profiles:[{principal_id:'resident:test',rules:[],inherited_rules:[],standing_grants:[{action:'old.action',scope_ref:'institution:riverview'}],effective_permissions:[{capability_id:'new.c3.operation',effective_status:'allowed'}]}],
  capabilities:[{capability_id:'new.c3.operation',description:'Newly registered operation',enabled:true,input_schema:{type:'object'},authorization_contract:{action:'new.c3.operation'}}],
  resources:[{resource_id:'service:runtime',resource_kind:'service',classification:'internal'}],
};
const model = context.window.RVResidentPermissionsModel.create(payload);
assert.equal(model.capabilities.length, 1, 'newly registered capability appears from API data without a code list');
assert.equal(model.status('new.c3.operation'), 'registered');
assert.equal(model.resource('service:runtime').resource_kind, 'service');
assert.equal(model.status('removed.operation'), 'unavailable');
const lifecycle = context.window.RVResidentPermissionsModel.create({capabilities:[
  {capability_id:'old.operation',description:'Old',enabled:true,catalog_status:'deprecated'},
  {capability_id:'off.operation',description:'Off',enabled:false},
]});
assert.equal(lifecycle.status('old.operation'), 'deprecated');
assert.equal(lifecycle.status('off.operation'), 'disabled');
assert.equal(lifecycle.assignableCapabilities.length, 0, 'deprecated and disabled entries are never presented as assignable');
assert.equal(model.unavailableGrantActions[0].action, 'old.action', 'unmatched historical grants remain visible without fabricated capability identity');

const history = JSON.parse(read('website/v2/deployed/assets/resident-history-reference.json'));
assert.equal(history.records.length, 7, 'six pinned Estate records plus documented Jessica reference');
assert.equal(history.classification, 'historical_reference_only');
assert.ok(history.records.every((item) => item.source && item.reference_state));
assert.match(history.records.find((item) => item.name === 'Jessica').reference_state, /Uncommissioned/);
assert.match(history.records.find((item) => item.name === 'Alfred').conflict, /unresolved/);
console.log('V2 authority explorer contracts and dynamic registry projection: PASS');
