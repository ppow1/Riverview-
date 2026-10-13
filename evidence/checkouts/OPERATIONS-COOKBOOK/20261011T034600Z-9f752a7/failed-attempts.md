<!-- Evidence file revision: 1.0.0; SHA-256 and artifact identity are in artifacts.json. -->
# RV-OPS-COOKBOOK-001 — Failed verification attempts and corrections

All failures below were retained as engineering findings. The installed `16/main` cluster, shared `riverview` database, and persistent services were not involved in failed PostgreSQL test attempts.

| Attempt | Failure observed | Cause | Correction and retest |
|---|---|---|---|
| Dashboard test import | `ModuleNotFoundError: No module named 'riverview_core'` | `PYTHONPATH=src` omitted from the unittest command | Re-ran with repository package path. |
| Dashboard test suite | Documentation-heading assertion failed; seven PostgreSQL cases skipped because no test DSN was supplied | Assertion expected literal `<h1>`; renderer correctly adds an `id` attribute. PostgreSQL tests were not eligible without an isolated DSN. | Asserted the stable generated heading id; executed suite against a fresh isolated PostgreSQL cluster. |
| First full isolated suite | 41 PostgreSQL-related errors: Unix socket `Permission denied` | Client lacked traversal/connect access through the test socket path; socket was created as `postgres:postgres` while harness ran as `admin1`. | Changed only the disposable test cluster socket permissions and kept the socket under its private parent. |
| Second full isolated suite | PostgreSQL tests failed with `FATAL: role "admin1" does not exist` | New isolated cluster has only default PostgreSQL roles; no harness role had yet been provisioned. | Created a test-only `admin1` superuser inside that disposable cluster. The production cluster was not changed. |
| Live guide link inspection | Rendered guide showed zero clickable component-cookbook links | `markdown._inline()` stripped a URL character after the closing parenthesis had already been removed; valid `.md` destinations became invalid. | Fixed parsing, added positive internal-link and negative unsafe-scheme tests, redeployed, and browser-verified all 16 links at HTTP 200. |

Final rerun: 118 tests passed, zero failures/errors/skips, on the isolated PostgreSQL 16.15 cluster. It reported zero remaining `rvtest_%` schemas and was stopped after verification.
