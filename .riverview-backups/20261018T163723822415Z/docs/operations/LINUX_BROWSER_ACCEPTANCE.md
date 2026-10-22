<!--
Riverview~ Controlled Document
File: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
Component: LINUX-BROWSER-ACCEPTANCE
File Revision: 1.0.6
Purpose: Operate the bounded Linux Chromium acceptance harness and request it in Engineering work orders
Authority: Read-only browser verification; production writes and authenticated sessions are out of scope
Changed: 2026-10-18 UTC | RV-C2-STAGING-GRACE-BROWSER-003 | Add authenticated read-only Grace staging bridge
-->
# Linux browser acceptance on Camrui

This harness uses Python Playwright with its pinned Chromium build. It is a separate Linux check; Windows browser results do not establish Linux behavior. Riverview's existing Firefox/GeckoDriver verification scripts remain available for their focused checks. The [CueMastery C212 smoke](https://github.com/ppow1/CueMastery/blob/main/docs/c212_prairie_estate_mcp_smoke_test.md) is documentation-only, its current tree has no Playwright test harness, and its [persona audit](https://github.com/ppow1/CueMastery/blob/main/docs/runbooks/cuemastery_test_persona_audit.md) explicitly defers HTTP/browser verification. The [seeded persona runbook](https://github.com/ppow1/CueMastery/blob/main/docs/runbooks/cuemastery_seeded_test_personas.md) describes durable test accounts, so this smoke uses a disposable static fixture instead of creating identities. Estate's [browser adapter](https://github.com/ppow1/theestate/blob/main/tools/chatgpt_mailbox_worker_browser.cjs) is a persistent authenticated Chrome DevTools Protocol integration; its [acceptance report](https://github.com/ppow1/theestate/blob/main/collaboration/workstreams/WP-4233/browser_acceptance_report.md) distinguishes direct tool invocation from browser evidence. Neither is reused as a test runner or supplied with a browser profile.

## Install the isolated runner

Run from the Riverview checkout on Camrui as the account that will own the test artifacts:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --requirement browser-tests/requirements.txt
.venv/bin/python -m playwright install chromium
```

If Chromium reports missing shared libraries, an operator may install the documented system dependencies with `.venv/bin/python -m playwright install-deps chromium` and then rerun the browser install. That command changes OS packages and needs a separately controlled host-maintenance window; it is not run automatically by the test harness.

## Run the non-destructive smoke

Start a local non-production Riverview dashboard or disposable fixture, then run:

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory browser-tests/fixtures
```

In another terminal:

```bash
scripts/run_linux_browser_acceptance.py \
  --base-url http://127.0.0.1:8766 \
  --smoke-path / \
  --expect-heading "Riverview read-only browser fixture"
```

The runner defaults to loopback and rejects URL credentials, path prefixes, query strings, fragments, and non-HTTP schemes. The browser runs headlessly with an isolated context and no saved profile. Requests other than `GET` are aborted and reported. It does not sign in, submit forms, create work, write files on the target, or call application mutation APIs. Remote targets require `--allow-remote-readonly`; use that only for an explicitly authorized staging target. Production browser acceptance needs its own explicit approval and must not be inferred from this smoke test.

The run writes a mode-0700 evidence directory under `${XDG_STATE_HOME:-~/.local/state}/riverview/browser-acceptance/` unless `--output` names a new directory. It contains a run summary, sanitized browser error report, screenshots, Playwright test output, and traces retained on failure. Evidence may contain rendered page content; keep it private and review/redact it before sharing. No cookies, authorization headers, request bodies, or URL query strings are recorded in the custom reports.

## Exercise the Grace workflow boundary in isolation

`browser-tests/fixtures/grace-workflow.html` is a clearly labeled synthetic UI fixture. The Playwright test intercepts its `/__synthetic__/` API calls in the browser and returns test-only responses; there is no backing Riverview server, database, resident, credential, approval, CME, or worker. It demonstrates the visible sequence **request → proposal pending approval → synthetic approval gate → work-order record → status report**. The test asserts that work-order creation is unavailable before the approval step and that the resulting work order remains pending actual execution authorization. Nothing is dispatched or executed.

With the disposable static fixture server running as above, run the expanded harness:

```bash
scripts/run_linux_browser_acceptance.py \
  --base-url http://127.0.0.1:8766 \
  --smoke-path /grace-workflow.html \
  --expect-heading "Talk with Grace — isolated workflow demonstration"
```

The synthetic test-only “Steward” control demonstrates a UI gate, not institutional authority. It is not a real Steward identity or approval. This test proves the fixture interaction and browser harness only. Actual Grace conversation persistence, proposal API behavior, authenticated Steward approval/promotion, Engineering objective or work-order persistence, status from CME, and execution require a deployed or isolated application stack with its real contracts and a disposable database. Production endpoints, live credentials, real approvals, and live execution are not used or implied. Keep tests that use the static smoke runner read-only; the synthetic workflow test’s narrowly intercepted requests are fulfilled in memory and never reach a server.

## Optional authenticated Grace staging inspection

`--grace-staging-readonly` connects the harness to the actual dashboard UI only when the operator explicitly supplies an isolated target, an exact-host cookie-only Playwright state, the displayed test-account label, and the UUID of an already-seeded harmless conversation. No credential is created or inferred. The browser state must be a regular file owned by the current user, mode `0600` or stricter, at most 1 MiB, with cookies scoped to the exact target host and no local-storage entries. Never use a production or personal Steward browser state.

For remote targets use HTTPS, a hostname explicitly labeled `staging` (or a reserved `.test` host), and `--allow-remote-readonly`. For loopback use a disposable local dashboard and set `RIVERVIEW_GRACE_STAGING_CONFIRMATION=I_CONFIRM_DISPOSABLE_GRACE_STAGING`. In either case `RIVERVIEW_GRACE_STAGING_ORIGIN` must exactly match `--base-url`. `RIVERVIEW_GRACE_STAGING_TEST_ACCOUNT_LABEL` must match the staged dashboard's displayed Steward test account, `RIVERVIEW_GRACE_STAGING_CONVERSATION_ID` must identify a pre-existing seeded conversation, and `RIVERVIEW_GRACE_STAGING_SEED_MESSAGE_TEXT` must exactly match a harmless user message in it. The account must already have the existing conversation access required to read it; this procedure provisions no role or grant.

```bash
export RIVERVIEW_GRACE_STAGING_ORIGIN='https://<operator-designated-staging-host>'
export RIVERVIEW_GRACE_STAGING_STORAGE_STATE='/secure/path/staging-cookie-state.json'
export RIVERVIEW_GRACE_STAGING_TEST_ACCOUNT_LABEL='<exact displayed test account label>'
export RIVERVIEW_GRACE_STAGING_CONVERSATION_ID='<pre-seeded conversation UUID>'
export RIVERVIEW_GRACE_STAGING_SEED_MESSAGE_TEXT='<exact harmless seeded message text>'
scripts/run_linux_browser_acceptance.py \
  --grace-staging-readonly --allow-remote-readonly \
  --base-url "$RIVERVIEW_GRACE_STAGING_ORIGIN" --smoke-path /
```

The staging test opens the preselected conversation and acts only on the exact configured harmless message, opens its **Create Engineering work order** dialog, checks the exact-grant and “does not approve execution” explanation, closes the dialog without submitting, then reads the existing objective/status projection. It never sends a chat message, approves/promotes a proposal, submits an objective, dispatches CME work, or executes an assignment. During this mode all cross-origin requests and all non-GET/HEAD requests are blocked except the same-origin, empty-body `POST /api/v1/resident/conversation-session` needed to establish the existing authenticated browser session. Playwright tracing and automatic screenshots are disabled for staging. On a successful run the test emits one screenshot after redacting the account label, conversation, message and objective details. If the test fails, no staging screenshot or trace is retained. JSON evidence remains private in the mode-0700 evidence directory.

This bridge can verify the actual UI, existing seeded conversation, rendered approval boundary, and read-only status when supplied with an isolated staged dashboard and test session. It does **not** prove a newly submitted request, proposal persistence, real Steward approval, work-order creation, CME status for that new work, or execution. Those require separately authorized nonproduction fixtures and the existing exact authority contracts. No staging URL, cookie state, test-account label, or seeded conversation was configured during this task, so the authenticated browser stage remains unexecuted.

## Request browser verification in an Engineering work order

Add explicit, persisted acceptance criteria to the authorized Engineering work order. For example:

> Linux browser acceptance requested on Camrui: against the approved local/staging origin `<origin>`, run `scripts/run_linux_browser_acceptance.py --base-url <origin> --smoke-path <read-only-path> --expect-heading "<exact heading>"`. Accept only exit code 0, the visible expected heading, and zero browser errors or blocked mutations. Preserve the run summary and screenshot; retain and review a trace if the test fails. Do not authenticate or mutate target state.

Include these details in the acceptance criteria:

1. A disposable/local or Steward-approved staging base origin and a read-only path.
2. The exact smoke expectation, such as the accessible heading text or a named page state.
3. The command/scenario: `scripts/run_linux_browser_acceptance.py --base-url <approved-origin> --smoke-path <read-only-path> --expect-heading <exact-heading>`.
4. The required evidence: exit code 0, one passing Chromium smoke, screenshot, `browser-errors.json` with zero errors/blocked mutations, and the run summary. A trace is expected when a test fails.
5. A statement that the test must not authenticate, mutate application state, or target production unless separately authorized.

The Engineering executor must treat the URL and assertion as bounded test inputs, not as permission to alter the target. The current source-change worker runs fixed offline pytest targets and does not invoke a browser against a deployed dashboard. This request therefore means a separate, explicitly authorized Linux browser acceptance step after the work-order build, with evidence linked to the same work-order record. Automatic dispatch, typed browser targets, and durable ingestion of browser evidence are not implemented by this harness; do not report the work order independently verified until its existing verifier accepts its required criteria.

## Recovery and troubleshooting

- `browser_venv_missing`: create `.venv` and install the pinned requirements above.
- `Executable doesn't exist`: run `.venv/bin/python -m playwright install chromium` for this exact Playwright version.
- A failing synthetic workflow test: confirm it targets `/grace-workflow.html`; all `/__synthetic__/` calls must be intercepted and fulfilled in the test. An unhandled endpoint is a test failure, not a reason to point the fixture at production.
- `browser_target_rejected` in `--grace-staging-readonly` mode: verify the exact staging origin, staging hostname or loopback confirmation, host-bound cookie-only state file permissions, displayed test-account label, and pre-seeded conversation UUID. Never resolve this error by supplying a production profile or broader cookie domain.
- Staging Grace test skipped: staging mode was not explicitly configured. This is the default; do not remove the opt-in gate.
- Missing shared library: inspect the Playwright launch error, then use the controlled OS dependency procedure; do not install packages from inside the test runner.
- `non_loopback_target_requires_readonly_opt_in`: use loopback for a local checkout, or provide `--allow-remote-readonly` only for an approved staging target.
- `target_must_be_http_origin_without_credentials_path_or_query`: pass only the base origin; use `--smoke-path` for the page path.
- Browser console/page/request failures: inspect the private screenshot, error JSON, and failure trace. Do not copy authenticated state into the runner or retry a test that attempted a non-GET request without first fixing its scope.

The test process starts no application server and restarts no service. The disposable static fixture command above binds only to `127.0.0.1`; interrupt it with Ctrl-C after the run.
