# =============================================================================
# RIVERVIEW~ CONTROLLED DOCUMENT
# File: docs/components/WORK_REGISTRY.md
# Component: UNIVERSAL-WORK-REGISTRY
# File Revision: 1.0.0
# Purpose: Specify the shared observational worker, session, and work-order registry
# Authority: Registration is observability; existing schedulers and authority grants govern execution
# Changed: 2026-10-18 UTC | RV-UNIVERSAL-WORK-REGISTRY-001 | Document schema, integrations, import, and limits
# History: Git and revision/backup manifest
# =============================================================================
# Universal Work Registry

## Purpose and boundary

The registry is one versioned, file-backed observation store shared by all worker types. `WorkRegistry` persists workers, sessions, and work orders under the `rv.work-registry.v1` contract in `WORK_REGISTRY.schema.json`. It does not dispatch work, allocate resources, make admission decisions, or grant authority. Existing schedulers, ResourcePlanner, AuthorityRegistry, and Engineering work-order engine remain authoritative for their own functions.

Worker identity is persistent. A worker can own multiple sessions; sessions remain historical after completion or disconnect. A session can accumulate sequential work orders. A work order can also exist before a live session is observed: its `session_id` and `worker_id` are null, while `owner_label` and `ownership_state=proposed` preserve a proposal without inventing an executor identity. Statuses include explicit `unknown`; snapshots derive stale from heartbeat age, while an ended crashed session can be marked `disconnected`. Activity is caller reported and heartbeat does not imply model reasoning.

Persistence uses an exclusive lock directory and atomic same-directory replace. All cooperating Windows, Linux, and Python clients must point at the same registry path on storage with working atomic rename and lock-directory semantics. The default path is per-user and is not a shared deployment; configure `RIVERVIEW_WORK_REGISTRY_PATH` for a deliberately shared development location. The implementation has no network service or database dependency.

## Registration interfaces

- `scripts/Start-RiverviewCodexSession.ps1` and `scripts/start-riverview-codex-session.sh` launch Codex only when explicitly invoked. Defaults preserve the existing Codex configuration. Optional model, reasoning-effort, and full-permission flags are passed only when requested; full permissions map to Codex `danger-full-access` and `ask-for-approval=never`.
- `scripts/register_work.py` is the lightweight Python interface for local AI services, Riverview residents, Engineering, browser-testing, verification, and other workers. Local AI job metadata supports model identity, endpoint reference, dynamic slot, queue state, timestamps, and task correlation. It accepts references and status only; prompts, secrets, credentials, and reasoning traces are not registry fields.
- `scripts/import_work_registry.py` imports legacy monitoring JSON only with an explicit mapping file. Missing identity or timestamps remain unknown. The importer never modifies its source and skips records already imported.
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

No source containing the seven requested Windows/Camrui Codex session identities was found in the audited repository or `_control` folder. The explicit import-map format is:

```json
{
  "schema_version": "rv.work-registry.import-map.v1",
  "records": [
    {"source":"path/to/legacy-monitoring.json", "worker_id":"worker-id", "session_id":"session-id", "hostname":"known-host", "os":"Windows"}
  ]
}
```

Only identities that actually occur in the source should be mapped. Omit absent timestamps rather than guessing them. Run `python scripts/import_work_registry.py <map.json> --registry <path>` to import. The importer leaves missing start and heartbeat times unknown and never changes source files. The current control board is preserved; the issue #120 inventory is supplemental and explicitly marked as initial. A separate validation and operator review should precede changing any existing board.

## Verification and limitations

Automated tests cover parallel independent sessions and work orders, concurrent writes, stale and disconnected sessions, completed and blocked tasks, and local AI job records. Dashboard route and static UI tests check auth/read-only behavior, enumeration, and backward compatibility with the existing worker API. Cross-runtime compatibility is the shared JSON contract and filesystem behavior; a Linux host is still needed for a live Windows/Linux shared-filesystem acceptance run. Seven session imports are pending source records and an explicit mapping.
