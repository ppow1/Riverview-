<!--
Riverview~ Controlled Document
File: docs/components/CHATGPT_DOORBELL.md
Component: CHATGPT-DOORBELL
File Revision: 1.0.1
Purpose: Contract, configuration, runtime, diagnostics and recovery for the Ubuntu ChatGPT wake adapter
Changed: 2026-10-17 UTC | RV-C3-DOORBELL-001 | Record Codex 1 Comms5 mailbox contract handoff
-->
# ChatGPT Doorbell

## Purpose and boundary

The New-Core doorbell uses the Riverview-owned Chrome profile to wake one exact
ChatGPT conversation after its caller has obtained a durable request and
correlation identity. It submits only this fixed text:

`Riverview doorbell v1: inspect the Riverview MCP mailbox.`

The browser is a wake mechanism. The bridge does not read assistant responses,
conversation history, cookies, or page text into its results. Typed mailbox
operations and PostgreSQL state belong to Comms5; response consumption belongs
to the existing Grace interface. This component does not create a mailbox,
implement Comms5 handlers, or add a second Grace response path.

## Execution and ownership

- **Component:** `CHATGPT-DOORBELL`.
- **Execution model:** request-driven wake adapter, with Chrome continuously
  available in the signed-in `admin1` graphical session.
- **Lifecycle owner:** `riverview-doorbell-browser.service`, a systemd user
  service attached to `graphical-session.target`.
- **Browser profile:** `${XDG_DATA_HOME:-$HOME/.local/share}/riverview/browser/profile`.
- **Private target configuration:**
  `${XDG_CONFIG_HOME:-$HOME/.config}/riverview/doorbell.json`, mode `0600`.
- **Local runtime/evidence:**
  `${XDG_STATE_HOME:-$HOME/.local/state}/riverview/`.
- **CDP:** one configured port in `9225..9325`, bound only to `127.0.0.1`.
- **Browser:** Google Chrome or Chromium found from the service user's PATH.

The exact conversation ID is configured from the current authoritative
Comms5 designated-reasoning binding and compared by the caller before each
wake. The page matcher accepts one and only one `chatgpt.com` page whose path
ends in `/c/<configured-id>`, including the project route shape. Zero or
multiple matches fail closed. It never selects the newest tab or another chat.

The profile is dedicated to Riverview and is not the operator's default Chrome
profile. Authentication uses ChatGPT's supported interactive login flow. The
bridge does not extract, store, or replay credentials. If login or MFA is
needed, the Steward completes it in this profile before readiness can pass.

## New-Core caller contract

`BrowserBridgeRunner.ring(request, designated_conversation_id)` accepts a
durable request ID, its correlation ID, a bounded timeout, and the current
designated conversation ID provided by its owning caller. It compares that
binding with the local config before invoking Node. The request ID and
correlation ID are returned unchanged. A successful browser result means only
that the allowlisted send control was clicked and the composer cleared.

The browser bridge uses a persistent metadata journal keyed by request and
correlation IDs. A verified success is idempotently returned on repeat calls.
Unverified attempts can be retried by the caller using the same identity and
the owning mailbox's retry/expiry rules. No new request is created by a retry.

### Comms5 compatibility and owner handoff

The live Comms5 5.0 capability catalog available during this implementation
contains no mailbox request, acknowledgment, claim, response submission, or
Grace response-consumption operations. Therefore the fixed wake is not yet
sufficient to complete the mailbox round trip. This is an external Comms5
contract gap, not a doorbell operation to emulate locally.

Codex 1 owns the missing Comms5 handlers. The required shared contract is:

1. Create one durable PostgreSQL reasoning request and return its request and
   correlation identities to the New-Core caller.
2. Let the designated ChatGPT Comms5 application discover only eligible River
   requests with bounded metadata and preserve both identities.
3. Acknowledge and exclusively claim the same unexpired request with bounded
   lease/reclaim semantics and idempotent retries.
4. Accept a bounded response correlated to the active claim and transition the
   request to completed atomically.
5. Expose the completed response through the existing New-Core-to-Grace
   consumption interface, retaining request/correlation lineage and making
   consumption retry-safe.

Comms5 must choose and document its own operation names, schemas, authorization
classes, response limits, lease/expiry behavior, errors, and Grace handoff.
Historical Comms4 names are reference material only; this adapter does not call
or define them. Codex 1/2 owned implementation files are outside this change.
The contract handoff is recorded as [New-Core issue #96](https://github.com/ppow1/Riverview-/issues/96).

## Bootstrap and service

Install Node.js and `node-ws` from Ubuntu packages and install Google Chrome for
Ubuntu using Google's supported Debian package. `node-ws` supplies the WebSocket
implementation on Ubuntu's Node.js 18 package; runtimes with a built-in global
WebSocket use that implementation instead.

From the deployed New-Core release, configure the exact conversation binding
and browser executable (the default search uses installed Chrome/Chromium):

```bash
PYTHONPATH=src python3 -m riverview_core.doorbell.bootstrap \
  --conversation-id 6a804df2-a580-83ea-addc-753a6dc93f75
```

That ID is the historical Riverview designated-reasoning binding. Before
commissioning, verify that the current Comms5 binding still resolves to it. The
bootstrap refuses to overwrite existing configuration. Use `--replace` only
after verifying a legitimate binding change.

Install the user unit at
`~/.config/systemd/user/riverview-doorbell-browser.service`, reload user
systemd, then enable it for `graphical-session.target`. It starts only the
configured profile, navigates to the configured conversation URL, and keeps
Chrome in the foreground so systemd can restart it after an unexpected exit.
The browser must run as `admin1` in the active graphical session; the
non-interactive `riverview` service account has no GUI session.

## Diagnostics and acceptance

Read-only preflight commands, from the deployed release:

```bash
node tools/riverview_browser_runtime.cjs --preflight
node tools/riverview_doorbell_bridge.cjs --preflight
systemctl --user status riverview-doorbell-browser.service --no-pager
```

The first reports binary existence, loopback CDP health, configured port, and
dedicated profile path. The second additionally reports authenticated-session,
exact-target, and fixed-action readiness. Reports never include URLs, page
text, DOM, cookies, or credentials.

Doorbell success requires a known durable request, unchanged request and
correlation IDs, exact target, authenticated composer, fixed text submission,
enabled allowlisted send control, and verified composer transition. End-to-end
acceptance additionally requires Comms5 request discovery/claim/response,
PostgreSQL completion, and Grace consumption evidence for that same lineage.
A successful browser click alone is not mailbox acceptance.

## Failure and recovery

| Failure | Meaning | Recovery |
| --- | --- | --- |
| `RIV-PLY-0002` | Invalid request envelope or timeout | Correct caller input; retain original IDs. |
| `RIV-PLY-0003` | Local CDP or bridge transport unavailable | Check the user service and localhost listener. |
| `RIV-PLY-0004` | ChatGPT session unavailable | Complete supported interactive login/MFA in the Riverview profile. |
| `RIV-PLY-0005` / `0006` | Exact target absent or duplicated | Restore the configured exact conversation; do not choose another tab. |
| `RIV-PLY-0007` / `0008` | Composer or fixed send control unavailable | Refresh/reopen the configured conversation and rerun preflight. |
| `RIV-PLY-0009` | Bounded CDP/request timeout | Check same request lineage and mailbox expiry before retry. |
| `RIV-PLY-0010` / `0011` | Missing or invalid config | Re-run bootstrap after verifying the active binding. |
| `RIV-PLY-0012` / `0013` | Browser lifecycle/executable failure | Check package path and `journalctl --user -u riverview-doorbell-browser.service`. |
| `RIV-PLY-0014` | Bridge result does not retain the caller's request/correlation lineage | Preserve the mailbox record and investigate the bridge; do not retry with new IDs. |
| `RIV-PLY-0015` | Node executable/module unavailable | Install supported Node.js and Ubuntu `node-ws`; rerun node unit tests. |
| `RIV-PLY-0016` | Existing config preserved | Verify binding, then explicitly use bootstrap `--replace` only for an approved change. |

Rollback disables only this user unit and restores its prior unit/config backup.
It does not touch Grace, CME, PostgreSQL, Comms4, or Comms5. Keep the historical
Windows bridge unchanged as the fallback until the Linux mailbox round trip is
independently verified.
