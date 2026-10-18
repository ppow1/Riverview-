# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/WORK_REGISTRY.md
# Component: UNIVERSAL-WORK-REGISTRY
# File Revision: 1.1.1
# Purpose: Specify the shared observational worker, session, and work-order registry
# Authority: Registration is observability; existing schedulers and authority grants govern execution
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Document schema, integrations, import, and limits
# History: Git and revision/backup manifest
# Changed: 2026-10-18 UTC | RV-W1-REGISTRY-PROCESS-CONCURRENCY-001 | Record subprocess-level concurrent writer verification and cross-host limit
# =============================================================================
# Universal Work Registry

Changed: 2026-10-18 UTC | RV-WORK-REGISTRY-CONTROL-BOARD-001 | Reconcile Control Board v4 aliases and provide a dynamic Windows registry board.

## Purpose and boundary

The registry is one versioned, file-backed observation store shared by all worker types. `WorkRegistry` persists workers, sessions, and work orders under the `rv.work-registry.v1` contract in `WORK_REGISTRY.schema.json`. It does not dispatch work, allocate resources, make admission decisions, or grant authority. Existing schedulers, ResourcePlanner, AuthorityRegistry, and Engineering work-order engine remain authoritative for their own functions.

Worker identity is persistent. A worker can own multiple sessions; sessions remain historical after completion or disconnect. A session can accumulate sequential work orders. A work order can also exist before a live session is observed: its `session_id` and `worker_id` are null, while `owner_label` and `ownership_state=proposed` preserve a proposal without inventing an executor identity. Statuses include explicit `unknown`; snapshots derive stale from heartbeat age, while an ended crashed session can be marked `disconnected`. Activity is caller reported and heartbeat does not imply model reasoning.

Persistence uses an exclusive lock directory and atomic same-directory replace. All cooperating Windows, Linux, and Python clients must point at the same registry path on storage with working atomic rename and lock-directory semantics. The default path is per-user and is not a shared deployment; configure `RIVERVIEW_WORK_REGISTRY_PATH` for a deliberately shared development location. The implementation has no network service or database dependency.

## Registration interfaces

- `scripts/Start-RiverviewCodexSession.ps1` and `scripts/start-riverview-codex-session.sh` launch Codex only when explicitly invoked. Defaults preserve the existing Codex configuration. Optional model, reasoning-effort, and full-permission flags are passed only when requested; full permissions map to Codex `danger-full-access` and `ask-for-approval=never`.
- `scripts/register_work.py` is the lightweight Python interface for local AI services, Riverview residents, Engineering, browser-testing, verification, and other workers. Local AI job metadata supports model identity, endpoint reference, dynamic slot, queue state, timestamps, and task correlation. It accepts references and status only; prompts, secrets, credentials, and reasoning traces are not registry fields.
- `scripts/import_work_registry.py` imports legacy monitoring JSON only with an explicit mapping file. Missing identity or timestamps remain unknown. The importer never modifies its source; re-import is idempotent and reconciles only newer source reports.
- Legacy session records may include optional `identity_state` (`verified` or `unverified`). It is optional in v1 so older registry files remain valid; snapshots show old records as verified only if they were created by the normal registration API. A source-mapped migration must explicitly set unverified when it only has a board alias, not a process/session identity.
- Windows/Linux Codex startup accepts an existing `--work-order-id` / `RIVERVIEW_WORK_ORDER_ID`. The session wrapper acknowledges that assignment in the same registry transaction that binds worker and session, changing proposed ownership to acknowledged. Future assignment launchers should pass the canonical work-order ID; this updates the registry automatically without a status-file edit. It still grants no execution authority: existing assignment and authority checks remain required.
- For sequential assignments delivered to an already running session, the existing assignment dispatcher can call `python scripts/register_work.py --registry <path> acknowledge-work-order --work-order-id <id> --worker-id <id> --session-id <id>` when it delivers/acknowledges the assignment. This is the observational callback contract; it records only the assignment receipt and session linkage. It does not poll or replace the scheduler.

Every session start may create a new ID, and multiple sessions and work orders have independent IDs and lifecycle. No session-count constant is configured. `docs/operations/ISSUE_120_INITIAL_WORK_INVENTORY.json` is the initial inventory seeded from [issue #120](https://github.com/ppow1/Riverview-/issues/120). All entries are clearly marked as last-known work and proposed ownership; import creates no worker or session records. Re-importing is idempotent. Review it with `python scripts/import_issue_120_work_inventory.py --dry-run`, then import into the configured registry with `python scripts/import_issue_120_work_inventory.py`.

## Dashboard and privacy

With `RIVERVIEW_WORK_REGISTRY_PATH` configured, the authenticated local status dashboard exposes `GET /api/v1/work-registry` and a separate Work registry view. It enumerates each snapshot on refresh and shows registered workers with and without sessions, each session, and reported assignments. Long detail, blocker context, evidence, next action, and outcomes are available in the expandable detail. The route is read-only; registration clients write the file directly. The dashboard remains loopback-bound and uses existing dashboard authentication.

The registry schema contains no prompt, credential, or private reasoning fields. Field validation rejects common credential patterns and explicit prompt/reasoning-trace labels. Consumers must put only safe summaries and artifact references in free text. Do not use work-order detail, evidence, or outcomes for private conversation content or chain-of-thought.

## Local AI and resource telemetry

An inference service registers as a worker and each inference request is a work order with the optional `local_ai_job` object. Slot identity is optional and dynamically named. Context capacity is not fixed or inferred. The registry does not decide whether a request fits or select/allocate a GPU. Existing resource-routing telemetry may be referenced separately by safe correlation IDs; live inference configuration is outside this component.

## Grace readiness and authority

Future Grace status inspection can use the authenticated read-only snapshot endpoint with a specifically scoped service identity and a versioned, allowlisted projection. To publish a work-order observation, Grace must call an adapter that verifies its existing exact institutional grant for the specific event and scope, and writes only the authorized event fields. This registry itself provides no Grace credential, permission, or write route. Do not connect production Grace as part of this development change.

Process-map integration points are documented in `process_graphs/work-registry/observational-registry.json`: session/worker observation, optional scheduler/resource telemetry references, dashboard read projection, and future permission-checked Grace inspection/publication. Existing Grace, scheduler, ResourcePlanner, AuthorityRegistry, and Engineering graphs are not edited. Any later integration must revise the affected canonical graph's `graph_revision`, changed nodes' `node_revision`, documentation references, and `.riverview-revisions.json`, then regenerate and check aggregate process-graph views.

## Seven-session migration

The original Windows Control Board v4 script maps aliases W1–W3 to `_control/resource-routing.json`, `resident-learning.json`, and `jessica-recovery.json`; it maps C1–C3 to Camrui `.codex-monitor/codex-1.json` through `codex-3.json`, and C4 to `commissioning.json`. A read-only SSH inspection verified the Camrui host name and all four records. The source status files and issue #120 establish work labels, state, milestones, blockers, branches, PRs, and last report times. They do **not** expose Codex process/session UUIDs or per-session heartbeat/activity. Windows Codex process counts cannot safely map processes to the W1/W2/W3 aliases.

`docs/operations/CONTROL_BOARD_V4_IMPORT_MAP.json` preserves each existing W1–W3/C1–C4 alias and links it to its actual monitoring source. Its IDs are the historical board aliases, not claimed Codex session UUIDs. The mapping marks all seven `identity_state=unverified`, `lifecycle=unknown`, and activity unknown. No heartbeat or session start time is inferred from a status-file `updated_at`. A work order retains its independent status; for terminal statuses without an explicit completion timestamp, `completed_at` remains null. The map is a migration contract, not a hard-coded live worker count. Re-running the importer is idempotent: it adds unseen aliases/orders, updates the same task only from a newer source timestamp, and preserves a previous assignment as history when the task title changes. It never updates heartbeat/activity/lifecycle from v4 status timestamps.

Preview and import without interrupting sessions:

```powershell
$registry = 'A:\AI\Riverview-Development\_control\work-registry-v1.json'
python scripts/import_work_registry.py docs/operations/CONTROL_BOARD_V4_IMPORT_MAP.json --registry $registry --dry-run
python scripts/import_work_registry.py docs/operations/CONTROL_BOARD_V4_IMPORT_MAP.json --registry $registry
```

The Camrui source reads require the already configured `camrui` SSH alias in batch mode. The migration is additive/idempotent and reads remote status files; it never writes them. Do not register an unverified alias as a verified Codex session. Reconciliation steps for each row: (1) identify the actual Codex session ID from the owning Codex runtime's session metadata without exposing conversation content; (2) register that real ID through the platform wrapper and compare host, repository, and branch; (3) review each imported work order and explicitly link only supported historical assignments to the real session with `update-work-order`; (4) retain the old W1–W3/C1–C4 alias as unknown historical provenance. Never mark the alias as verified or delete it as a substitute for reconciling its links. A heartbeat may verify session presence but not reasoning activity.

The dynamic Windows board is `scripts/Start-RiverviewControlBoard-Registry.ps1`. Run the repository launcher after installing it beside the existing monitor:

```powershell
Copy-Item .\scripts\Start-RiverviewControlBoard-Registry.Launcher.ps1 `
  A:\AI\Riverview-Development\Start-RiverviewControlBoard-Registry.ps1
A:\AI\Riverview-Development\Start-RiverviewControlBoard-Registry.ps1 -Detailed
```

It enumerates registry worker/session/work-order collections each refresh and displays unmatched Windows and Camrui v4 JSON reports separately as legacy/unverified rows. Use `-Detailed` for long blockers and evidence. The existing `A:\AI\Riverview-Development\Start-RiverviewControlBoard-v4.ps1` remains unchanged as rollback/fallback. Rollback is to remove only the new `Start-RiverviewControlBoard-Registry.ps1` launcher and continue using v4; no live Codex session needs restarting. The existing seven-source mapping is specific to migration; neither registration nor the monitor has a fixed live worker count.

For future sessions, use `scripts/Start-RiverviewCodexSession.ps1` / the Linux wrapper with `RIVERVIEW_WORK_REGISTRY_PATH` set to the canonical registry file. Startup registers a worker/session; an existing assignment is linked when its canonical work-order ID is passed. A dispatcher that delivers a later assignment to a running session must create/update the canonical work order and invoke the documented `acknowledge-work-order` callback automatically; this callback is observational and does not replace scheduler authorization. The current user-directed Codex chat assignment path has no durable dispatch callback to integrate, and Windows↔Camrui currently has no verified common filesystem path. Until those integration points are supplied, subsequent chat assignments and cross-host live registrations must use the registry client explicitly; they must not be inferred from process activity or by editing status JSON.

**Known commissioning boundary:** registry assignment completion is not commissioning approval or proof of production capability. C4's record remains blocked by its current external provider/grant/Steward prerequisites; the dynamic board labels production capability and commissioning as not established by this observational registry. Existing source and issue #120 remain authoritative for those explicit blockers.

## Verification and limitations

Automated tests cover parallel independent sessions and work orders, concurrent writes, stale and disconnected sessions, completed and blocked tasks, and local AI job records. Dashboard route and static UI tests check auth/read-only behavior, enumeration, and backward compatibility with the existing worker API. Cross-runtime compatibility is the shared JSON contract and filesystem behavior; a Linux host is still needed for a live Windows/Linux shared-filesystem acceptance run. Seven session imports are pending source records and an explicit mapping.

The registry concurrency contract is also exercised by independent Python
processes writing through separate `WorkRegistry` instances to one temporary
file. This verifies process-local filesystem lock-directory coordination on
the test OS. It does not establish cross-host lock correctness for an arbitrary
network filesystem; Windows/Linux interoperability on the selected shared
storage remains a separate acceptance gate.
