# M3.3 operations documentation port — verification checkout

Branch: `codex/m3.3-repository-knowledge` (PR #19, open/draft)
Base before this change: `9b6f1dc8acdf0038cda7d26b99886bab0acc2210`
Verification type: isolated engineering and read-only live host inspection; **not deployment commissioning**.

- Complete isolated PostgreSQL 16.15 suite: 143 passed; zero failures, errors, or skips.
- Disposable test cleanup: zero `rvtest_*` schemas and roles; cluster stopped and removed.
- Dashboard docs route: 12/12 passed.
- Canonical process graph: 13 workflows / 235 nodes passed.
- Compileall and source diff check: exit 0.
- Shared `riverview_dev` inspection: read-only; `0001_assignment_leases` present and checksum matches checked-in SQL.
- Active dashboard release observed: `7a9ff46e11edc54b1ffe46f63962754e6d2da765`; no release deployed by this checkout.
- Runtime services and data were preserved; no shared DB mutation or credential change.
- Exact-head PR CI: pending at time this record was prepared.

Logs in this directory contain results for the isolated suite, route tests, graph validation, compile, cleanup, and read-only service inspection. They do not establish acceptance of M1.4 or M3.3.
