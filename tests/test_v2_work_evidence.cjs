const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const adapter = require("../website/v2/deployed/assets/work-evidence-adapter.js");
const ROOT = path.resolve(__dirname, "../website/v2/deployed");

test("blocked objective model uses recorded reason, lifecycle, owner, and evidence timestamps", () => {
  const model = adapter.objectiveModel({
    objective_id:"objective:blocked-1",status:"WORK_ORDER_CREATED",lifecycle_status:"blocked",
    lifecycle_stage:"Steward action required",assignment_id:"work-1",updated_at:"2026-10-24T11:00:00Z",
    rework:{rationale:"Evidence must be reviewed"}
  }, {assignment_id:"work-1",owner:"resident:engineering",state:"blocked",
    last_meaningful_progress:{event_type:"work.blocked",event_id:"event-1",event_seq:41,recorded_at:"2026-10-24T10:00:00Z"}}, Date.parse("2026-10-24T12:00:00Z"));
  assert.equal(model.stage,"Steward action required");
  assert.equal(model.status,"blocked");
  assert.equal(model.blocker,"Evidence must be reviewed");
  assert.equal(model.owner,"resident:engineering");
  assert.equal(model.progressAge,"2 hours ago");
  assert.equal(model.evidenceEventId,"event-1");
  assert.equal(model.evidenceEventSeq,41);
  assert.match(model.dependencyAvailability,/not exposed/);
});

test("unblocked work does not invent a blocker or dependencies", () => {
  const model = adapter.objectiveModel({objective_id:"objective:ok",status:"GROUNDED",lifecycle_status:"waiting",lifecycle_stage:"Awaiting authorized work order"});
  assert.equal(model.blocker,"Awaiting authorized work order");
  assert.equal(model.dependencies,null);
  assert.equal(model.assignmentId,null);
  assert.equal(model.owner,null);
});

test("missing, invalid, and old progress times remain explicit and use actual timestamps", () => {
  assert.equal(adapter.ageLabel(null,Date.parse("2026-10-24T12:00:00Z")),"Progress time not recorded");
  assert.equal(adapter.ageLabel("not-a-time",Date.parse("2026-10-24T12:00:00Z")),"Progress time not recorded");
  assert.equal(adapter.ageLabel("2026-10-20T12:00:00Z",Date.parse("2026-10-24T12:00:00Z")),"4 days ago");
  assert.match(adapter.ageLabel("2026-10-25T12:00:00Z",Date.parse("2026-10-24T12:00:00Z")),/future/);
});

test("objective relationships are joined only by exact recorded assignment IDs", () => {
  const objectives=[
    {objective_id:"objective:one",assignment_id:"assign-1"},
    {objective_id:"objective:two",assignment_id:"assign-10"},
    {objective_id:"objective:three",assignment_id:null}
  ];
  assert.deepEqual(adapter.exactLinkedObjectives("assign-1",objectives),["objective:one"]);
  assert.deepEqual(adapter.exactLinkedObjectives("assign-",objectives),[]);
  assert.deepEqual(adapter.assignmentModel({assignment_id:"assign-1"},objectives).linkedObjectiveIds,["objective:one"]);
});

test("work evidence uses existing protected read APIs and keeps access denial visible", () => {
  const html=fs.readFileSync(path.join(ROOT,"index.html"),"utf8");
  const work=fs.readFileSync(path.join(ROOT,"assets/work-monitor.js"),"utf8");
  const evidence=fs.readFileSync(path.join(ROOT,"assets/work-evidence.js"),"utf8");
  const grace=fs.readFileSync(path.join(ROOT,"assets/grace-chat.js"),"utf8");
  assert.match(html,/work-evidence-adapter\.js\?rev=blocker-20261024/);
  assert.match(html,/work-evidence\.js\?rev=blocker-20261024/);
  assert.match(html,/id="work-sort"/);
  assert.match(work,/\/api\/v1\/objectives\?limit=25/);
  assert.match(work,/\/api\/v1\/assignments\?limit=25/);
  assert.match(evidence,/\/api\/v1\/assignments\/\$\{encodeURIComponent\(model\.assignmentId\)\}/);
  assert.match(work,/\[401, 403\]\.includes\(result\.reason\?\.status\)/);
  assert.match(work,/state\[target\] = \[\]/);
  assert.match(work,/function sortRows\(/);
  assert.match(grace,/RiverviewV2WorkEvidence\.createDetails\(item\)/);
  assert.doesNotMatch(evidence,/method:\s*"(POST|PUT|PATCH|DELETE)"/);
});
