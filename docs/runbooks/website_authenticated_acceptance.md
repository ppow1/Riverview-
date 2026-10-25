# Riverview authenticated website acceptance

Document Revision: 1.0.3

## Personas and authority

`scripts/seed_website_test_personas.py --apply` creates reserved `@riverview.invalid` accounts using Riverview's normal password hash and `viewer`, `operator`, or `steward` roles. `engineering` is a distinct test identity with the existing `operator` website role; it receives no InstitutionalAuthority grant. The test Steward is not linked to `steward:camrui`. The script runs as root, writes generated passwords once to `/etc/riverview/website-acceptance/personas.json` mode 0600, and refuses to reset or adopt an existing unmarked account. Account creation is audited. Do not print or copy the credential file.

An unlinked test Steward can test authenticated notification preferences. It cannot open Grace conversations, exercise cancellation, or receive new engineering grants. Those require an independently approved test principal/grant and disposable objectives. Linux sudo and the website role do not provide those authorities.

## Running checks

Use the installed systemd oneshot units for on-demand runs. They reuse the deployed runner, protected systemd credentials, and production V2 origin; no manual website login or Steward browser session is needed.

```sh
# Lightweight availability and release identity check
sudo systemctl start riverview-website-acceptance@light.service

# Full authenticated production browser acceptance
sudo systemctl start riverview-website-acceptance@full.service
```

`light` checks actual LAN HTTPS V2 availability and release identity. `full` uses native Chrome/ChromeDriver (Firefox fallback) against `/v2/`, signs into each seeded account through the normal account API, verifies role enforcement and logout, reads notification preferences through the live API and page, and writes the same stored values back for persistence readback. It never submits a Grace message or cancels a production objective.

After a run, inspect the unit result and machine-readable report. A zero service exit means the runner completed; **the report's `overall` field is the acceptance result**. In particular, `WARNING` may have service exit 0 and is not full acceptance.

```sh
sudo systemctl show riverview-website-acceptance@full.service \
  -p Result -p ExecMainStatus -p ExecMainStartTimestamp -p ExecMainExitTimestamp --no-pager
python3 - <<'PY'
import json
from collections import Counter
path = "/var/lib/riverview-website-acceptance/latest.json"
report = json.load(open(path))
print("report:", path)
print("overall:", report["overall"], "timestamp:", report["timestamp"])
print("checks:", dict(Counter(c["status"] for c in report["checks"])))
for check in report["checks"]:
    if check["status"] in {"FAIL", "WARNING", "SKIPPED"}:
        print(check["status"], check["check"], check.get("reason", ""))
PY
```

The same latest report is displayed in the V2 **Website verification** panel and at `https://192.168.1.155/v2/verification/latest.json` from the LAN. This IP URL is the verified production route; its rows identify `PASS`, `FAIL`, `WARNING`, and `SKIPPED` with reasons. For runner output, use `sudo journalctl -u riverview-website-acceptance@full.service --since today --no-pager`. Never print or copy the protected persona credential file.

Verified on 2026-10-24 from the production host: the light unit completed with result `success`, exit 0, and report `PASS` (2 checks); the full unit completed with result `success`, exit 0, and report `WARNING` (37 PASS, 0 FAIL, 3 SKIPPED). The full report was written to `/var/lib/riverview-website-acceptance/latest.json` and served through the V2 report endpoint. The three intentional skips are Grace conversation authority for the test identity, absence of disposable production cancellation data, and a durable Snapshot archive write.

The installed `riverview-website-acceptance-light.timer` runs every 15 minutes. `riverview-website-acceptance-full.timer` runs every four hours. Timestamped results are in `/var/lib/riverview-website-acceptance/latest.json` and are exposed in the V2 overview and at `/v2/verification/latest.json`. Reports contain check names and statuses only, not credentials, settings values, conversation content, or topic identifiers. The deployment procedure obtains the ChromeDriver build matching installed native Chrome from Google's Chrome for Testing metadata and validates the archive before installation. The runner verifies browser/driver major versions on each full run.

## Local controlled-checkout fallback when Actions cannot start

Keep `.github/workflows/controlled-checkout.yml` enabled. If GitHub Actions cannot start because of free-quota, billing-policy, or service availability, do not keep retrying it and do not describe local results as a hosted check pass. Run the same test, graph, and revision-control commands locally on Camrui, then record the commit SHA, command results, reason Actions did not start, and any baseline-reproduced failures in the PR and issue #268.

The full test suite includes PostgreSQL tests that create temporary database roles. Give those privileges only to a disposable PostgreSQL 16 cluster, never to a shared or production database account. The example below binds an ephemeral cluster to loopback only; choose a free test port and a fresh temporary directory for each run. Create an isolated Python 3.12 virtual environment and install the exact dependencies pinned in the workflow (`psycopg[binary]==3.2.10`, `jsonschema==4.10.3`, `cryptography==41.0.7`, `PyJWT[crypto]==2.10.1`), then run:

```sh
RV_CI_VENV=/var/tmp/rv-controlled-checkout-venv
python3 -m venv "$RV_CI_VENV"
"$RV_CI_VENV/bin/python" -m pip install \
  'psycopg[binary]==3.2.10' 'jsonschema==4.10.3' \
  'cryptography==41.0.7' 'PyJWT[crypto]==2.10.1'
RV_CI_CLUSTER_DIR=$(mktemp -d /var/tmp/rv-controlled-checkout.XXXXXX)
sudo chown postgres:postgres "$RV_CI_CLUSTER_DIR"
sudo chmod 0700 "$RV_CI_CLUSTER_DIR"
sudo install -d -o postgres -g postgres -m 0700 "$RV_CI_CLUSTER_DIR/data"
sudo -u postgres /usr/lib/postgresql/16/bin/initdb -D "$RV_CI_CLUSTER_DIR/data" \
  --auth-local=trust --auth-host=trust --username=postgres --no-instructions
sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D "$RV_CI_CLUSTER_DIR/data" \
  -o '-h 127.0.0.1 -p 55439 -F' -l "$RV_CI_CLUSTER_DIR/server.log" -w start
sudo -u postgres createdb -h 127.0.0.1 -p 55439 riverview_test
RIVERVIEW_TEST_PG_DSN='postgresql://postgres@127.0.0.1:55439/riverview_test' \
  PYTHONPATH=src "$RV_CI_VENV/bin/python" \
  -m unittest discover -s tests -v
python3 scripts/process_graph.py check
python3 scripts/revision_control.py check \
  --baseline evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/baseline-inventory.json
sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D "$RV_CI_CLUSTER_DIR/data" -m fast -w stop
sudo python3 -c 'from pathlib import Path; import shutil,sys; p=Path(sys.argv[1]); assert p.parent == Path("/var/tmp") and p.name.startswith("rv-controlled-checkout.") and not p.is_symlink(); shutil.rmtree(p)' "$RV_CI_CLUSTER_DIR"
```

Remove only that run's stopped temporary cluster after preserving the command output in the PR/issue record. Keep the local result explicitly labeled as a local fallback. For the website itself, also run the candidate-bundle validator and the existing authenticated post-deployment acceptance/rollback procedure above; do not treat fixture-preview checks as authenticated production acceptance.

Failures are queued once per incident as `monitor_failed` in the existing `riverview_dev.cme_monitor_events` table. The current notification dispatcher applies its normal policy and NTFY transport. A recovery clears the active deduplication incident; a later failure opens a new incident.

## Deployment and rollback

Run unit tests and candidate-bundle checks before switching the existing Nginx V2 release alias. Keep the current release path and Nginx snippet backup. After switching, run full authenticated acceptance and inspect its result; if a required live check fails, restore the previous alias from the protected backup and reload Nginx. Do not replace the Dashboard `current` symlink or restart Grace/CME services for a static V2 release. Any check that requires InstitutionalAuthority or disposable objective creation remains `SKIPPED` until a purpose-built, separately authorized test principal and isolated test objective mechanism are available.
