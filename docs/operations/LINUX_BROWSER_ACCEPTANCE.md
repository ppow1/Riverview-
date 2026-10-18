<!--
Riverview~ Controlled Document
File: docs/operations/LINUX_BROWSER_ACCEPTANCE.md
Component: LINUX-BROWSER-ACCEPTANCE
File Revision: 1.0.1
Purpose: Operate the bounded Linux Chromium acceptance harness and request it in Engineering work orders
Authority: Read-only browser verification; production writes and authenticated sessions are out of scope
Changed: 2026-10-18 UTC | RV-LINUX-BROWSER-ACCEPTANCE-001 | Initial Camrui browser acceptance procedure
-->
# Linux browser acceptance on Camrui

This harness uses Python Playwright with its pinned Chromium build. It is a separate Linux check; Windows browser results do not establish Linux behavior. Riverview's existing Firefox/GeckoDriver verification scripts remain available for their focused checks. The CueMastery C212 reference is a documentation-only workflow smoke, and its current tree has no Playwright test harness. Estate's existing browser integration is a persistent authenticated Chrome DevTools Protocol adapter; it is intentionally not reused as a test runner or supplied with a browser profile.

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
- Missing shared library: inspect the Playwright launch error, then use the controlled OS dependency procedure; do not install packages from inside the test runner.
- `non_loopback_target_requires_readonly_opt_in`: use loopback for a local checkout, or provide `--allow-remote-readonly` only for an approved staging target.
- `target_must_be_http_origin_without_credentials_path_or_query`: pass only the base origin; use `--smoke-path` for the page path.
- Browser console/page/request failures: inspect the private screenshot, error JSON, and failure trace. Do not copy authenticated state into the runner or retry a test that attempted a non-GET request without first fixing its scope.

The test process starts no application server and restarts no service. The disposable static fixture command above binds only to `127.0.0.1`; interrupt it with Ctrl-C after the run.
