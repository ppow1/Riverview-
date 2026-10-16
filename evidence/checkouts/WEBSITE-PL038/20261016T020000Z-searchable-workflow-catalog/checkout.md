# RV-WEBSITE-PL038 isolated verification

- Date: 2026-10-16 UTC
- Browser: Mozilla Firefox 156.0.1
- Mode: isolated loopback API fixture with synthetic `rv_account_session` cookie
- Result: 35/35 browser checks passed; no browser errors.
- Security assertion: 23 protected API requests included the account cookie and omitted the Authorization header.
- Catalog assertions: registry index/detail loaded; workflow, failure/recovery node, documentation path, source provenance and declared test reference rendered; search narrowed to the matching recovery node.
- Other regression assertions: documentation and dashboard windows reused; chat transcript/layout, notification lifecycle, task title, worker paging, navigation rail and activity cursors passed.
- Focused tests: `PYTHONPATH=.:src pytest -q -rs tests/test_status_dashboard.py tests/test_process_graph.py` — 46 passed, 8 PostgreSQL-dependent skips (`RIVERVIEW_TEST_PG_DSN` unset).
- Process graph validation: PASS, 19 workflows / 458 nodes.
- Production acceptance: unverified; this is synthetic isolated evidence.

Failed attempts are preserved in sibling timestamped directories. `artifacts.json` contains checksums for this passing run.
