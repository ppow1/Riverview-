<!--
Riverview~ Controlled Document
File: docs/components/CHATGPT_DOORBELL_COOKBOOK.md
Component: CHATGPT-DOORBELL
File Revision: 1.0.0
Purpose: Safe diagnostics, fault isolation, recovery and escalation for the Ubuntu ChatGPT wake adapter
Changed: 2026-10-18 UTC | RV-C3-DOORBELL-DOD-001 | Add node-by-node recovery cookbook
Owner: Codex 3 / New-Core
Execution Model: Request-driven adapter with systemd-managed browser runtime
Observability: Owner-local JSON status and metadata-only journal; no live Steward runtime feed
Dependencies: Node.js, Chrome/Chromium, localhost CDP, authenticated dedicated profile, current Comms5 and Grace contracts
Inputs: Read-only status, service state, request/correlation metadata
Outputs: Diagnostic findings and documented recovery/resume point
Authority: Read-only diagnosis; service restart only under approved operations; never reads or publishes page contents
Contracts: docs/components/CHATGPT_DOORBELL.md; docs/components/CHATGPT_DOORBELL_STATUS.schema.json; process_graphs/chatgpt-doorbell/browser-runtime.json
Tests: tests/test_chatgpt_doorbell.py; tests/test_riverview_doorbell_bridge_node.cjs
History: Git and .riverview-backups/manifest.jsonl
-->
# ChatGPT Doorbell Troubleshooting and Recovery Cookbook

## Scope and safety

This is the Ubuntu `CHATGPT-DOORBELL` adapter cookbook. Its first stage is a
fixed wake message through one configured ChatGPT conversation. It does not
read assistant replies or establish mailbox completion. Never copy browser
cookies, passwords, bearer tokens, page text, conversation contents, or profile
files into an issue, log, or evidence record. Do not delete Chrome `Singleton*`
lock files or manually edit the profile. Ask the Steward to complete interactive
login/MFA in the dedicated Riverview Chrome profile. Comms5 and Grace stages
are owned by Codex 1 and Codex 2 respectively.

## Consolidated read-only diagnostic

Run from the deployed New-Core release as the service owner (`admin1`):

```bash
node tools/riverview_browser_runtime.cjs --status
systemctl --user status riverview-doorbell-browser.service --no-pager
journalctl --user -u riverview-doorbell-browser.service --no-pager -n 50
ss -ltn 'sport = :9225'
python3 scripts/process_graph.py check
```

The configured CDP port can be any value in `9225..9325`; read the status JSON
for the port and use that literal in `ss` if it differs. Do not attach to a
non-loopback listener. Do not put dashboard bearer credentials on a command
line. The status command is an owner-local snapshot, not a dashboard/live
Steward feed. Its schema is
[`CHATGPT_DOORBELL_STATUS.schema.json`](CHATGPT_DOORBELL_STATUS.schema.json).
`observed_at` is the observation time; treat it as stale after
`freshness.stale_after_seconds` (currently 60 seconds). Status is blocked while
authentication or downstream contracts are unresolved.

Expected safe output includes `component_id`, `component_version`, `status`,
`ready`, browser and CDP health, authentication heuristic, target resolution,
last trigger identities/status, coded last error, blockers, external dependency
state, workflow position/reason, process state, and profile-lock presence. It
must not contain URLs, DOM, page text, response text, cookies, or credentials.

## Node recovery table

The canonical graph is
[`browser-runtime.json`](../../process_graphs/chatgpt-doorbell/browser-runtime.json);
this table follows its node identities. “Resume” means re-run the indicated
read-only preflight first, then retry only with the original IDs and only when
the owning mailbox contract says it is safe.

| Workflow node | Input → expected output | Observable state / failure | First read-only diagnostic | Safe recovery and resume | Escalation owner |
|---|---|---|---|---|---|
| `request-eligible` | Durable Comms5 request → request and correlation UUIDs | No durable source is connected in this release | Read Comms5 capability contract through its approved capability operation | Do not fabricate a request; wait for Codex 1 contract and caller wiring | Codex 1 |
| `trigger-received` / `request-identity` | Caller envelope → same validated IDs | `RIV-PLY-0002`, `RIV-PLY-0014` | Inspect caller metadata and local metadata-only status | Preserve original IDs; correct caller contract before retry | Codex 3; mailbox owner for expiry |
| `binding-check` | Current designated ID + local config → exact equality | `RIV-PLY-0011` or binding mismatch | `node tools/riverview_doorbell_bridge.cjs --preflight` | Steward confirms authoritative binding; update config through approved bootstrap; resume at binding check | Steward / Codex 3 |
| `browser-readiness` | User unit, Chrome, profile → available | `RIV-PLY-0012`/`0013`; stopped unit; profile lock | `systemctl --user status riverview-doorbell-browser.service --no-pager` | Inspect journal and process ownership. Do not remove lock files. Authorized operator may restart this unit only; resume at readiness | Codex 3 operations |
| `cdp-established` | Local listener → bounded localhost CDP socket | `RIV-PLY-0003`/`0009`; listener absent or timeout | `ss -ltn 'sport = :9225'`; then runtime `--preflight` | Confirm only loopback bind and healthy browser service; recover/restart the doorbell unit under change control; resume at CDP check | Codex 3 operations |
| `authenticated-composer` / `steward-login` | Exact page route → composer controls available | `RIV-PLY-0004`; `login_required` or `unknown` | Runtime `--status` (does not read page text) | Steward signs in and completes MFA interactively in dedicated profile; rerun status. Never extract credentials | Steward |
| `target-resolution` | Configured conversation UUID → exactly one matching tab | `RIV-PLY-0005` missing / `0006` duplicate | `node tools/riverview_doorbell_bridge.cjs --preflight` | Steward opens the exact configured conversation; close duplicate tabs through normal UI; never select a different/newest chat; resume at exact match | Steward / Codex 3 |
| `fixed-wake` | Allowlisted fixed string → send control invoked | `RIV-PLY-0007`/`0008`; action unavailable | Read-only preflight | Restore the exact conversation and composer using UI; do not type alternate text; resume at fixed wake only after readiness | Codex 3 |
| `submit-verification` | Click invocation → composer transition verified | `RIV-PLY-0009`, timeout/ambiguous result | Inspect latest metadata-only `last_trigger` and service journal | Do not blindly send again after ambiguity. Ask Comms5 owner to inspect same request state; only retry same IDs if outcome and expiry allow | Codex 3 + Codex 1 |
| `metadata-result` | Verified local submission → IDs + safe evidence | Failure record contains IDs and stable error class only | Runtime `--status`; inspect owner-only journal metadata | Preserve request lineage. Browser evidence is not mailbox evidence; continue only after Comms5 is commissioned | Codex 3 |
| `chatgpt-mailbox-access` / `comms5-missing` | Fixed wake → Comms5 mailbox access | Current capability contract lacks mailbox lifecycle operations; issue #96 | Use the approved Comms5 capabilities call; do not guess legacy operation names | Stop; Codex 1 defines and implements operations. Resume only after contract/version verification | Codex 1 |
| `request-claimed` | Eligible request → acknowledged/claimed lease | No operation commissioned; no claim evidence | Query the Comms5 owner’s documented read-only request status once available | Do not create a duplicate claim or request; preserve identities and lease semantics | Codex 1 |
| `correlated-response` | Active claim + response → completed request | No response operation commissioned | Owner’s documented request status / audit interface once available | Codex 1 resolves; never treat visible ChatGPT output as a submitted response | Codex 1 |
| `grace-consumes` / `workflow-complete` | Completed correlated response → Grace continuation evidence | Grace handoff not verified for this flow | Use Codex 2’s established Grace read-only interface once contract is provided | Do not add a duplicate response path; resume at Grace consumption with same lineage | Codex 2; acceptance jointly Codex 1/2 |
| `retry-or-block`, `bounded-retry`, `blocked-wait`, `restart-recovery` | Stable IDs + owning retry policy → bounded retry or recorded block | Repeated code, ambiguous send, expiry, or stale status | Runtime `--status` plus request owner’s durable state | Restart only the doorbell unit when authorized. Re-read durable state before retry; never mint new IDs for a retry | Codex 3 / relevant owner |

## Safe recovery sequence

1. Capture the JSON status and the relevant journal lines locally; redact any
   accidental secret before sharing. Normal bridge output is metadata-only.
2. Identify the first failing graph node and its `RIV-PLY-*` code. Do not start
   at a downstream node without evidence that its prerequisite completed.
3. Check the dedicated unit and localhost listener. Ensure the profile belongs
   to `admin1` and no second Chrome process is using it.
4. Resolve auth/MFA and exact target only through normal ChatGPT UI with the
   Steward. Run preflight again.
5. For an ambiguous or timed-out submission, stop retries until the durable
   owner can establish whether the same request was claimed. Preserve both IDs.
6. For Comms5 or Grace gaps, record the blocker against issue #96 / Codex 2 and
   wait for the owner’s versioned interface contract. The browser bridge cannot
   resolve those blockers.
7. After approved recovery, verify the same node and identity advance; retain
   command, UTC time, exit code, and safe status evidence.

## Startup, shutdown, restart and rollback

The checked-in systemd user unit is intended for `admin1`'s graphical session;
it is not installed or enabled by this documentation task. Startup is through
`graphical-session.target`; systemd restarts Chrome after unexpected exit.
To stop or restart, use the approved change procedure for this unit only. Before
restart, preserve current status and journal evidence and check the durable
request owner’s state. Rollback disables this unit, restores its previous unit
and config backups, and leaves all other Riverview services untouched. Never
remove profile files or locks as a recovery shortcut.
