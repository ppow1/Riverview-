# RV-WEBSITE-PL038 post-PR-45 isolated verification

- Date: 2026-10-16 UTC
- Browser: Mozilla Firefox 156.0.1
- Mode: isolated loopback API fixture with synthetic `rv_account_session` cookie
- Result: 35/35 browser checks passed; no browser errors.
- Security assertion: protected API requests included the account cookie and omitted the Authorization header.
- Catalog assertions: graph index/detail loaded; workflow, failure/recovery, docs, source provenance and declared evidence rendered; query narrowed to the matching recovery node.
- Streaming compatibility: PR #40 SSE/deferred-response code was not modified. PR #45 same-source work-order retry behavior was preserved during integration reconciliation.
- Focused tests: `PYTHONPATH=.:src pytest -q -rs tests/test_status_dashboard.py tests/test_process_graph.py` — 47 passed, 8 PostgreSQL-dependent skips (`RIVERVIEW_TEST_PG_DSN` unset).
- Process graph validation: PASS, 19 workflows / 459 nodes.
- Production acceptance: unverified; this is synthetic isolated evidence.

`artifacts.json` contains checksums for this passing run.
- Revision audit: PASS with zero findings against PR #45 integration head `ef73c6d6410cd30e00ebda6d68ee76e5a35a10f6`.
