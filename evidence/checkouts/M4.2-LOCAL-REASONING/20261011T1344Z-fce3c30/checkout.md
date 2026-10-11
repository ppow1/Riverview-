<!-- Riverview~ Controlled Evidence
File: evidence/checkouts/M4.2-LOCAL-REASONING/20261011T1344Z-fce3c30/checkout.md
Component: RESIDENT-REASONING
Document Revision: 1.0.0
Purpose: Record current local reasoning adapter contract and model attempt results
Authority: Plan proposals cannot authorize execution
Tests: provider-contract-tests.log; full-suite.log
History: artifacts.json SHA-256 manifest
-->
# Local resident reasoning provider checkpoint

The source base is `fce3c30e568dfb29ce7733ec05ff9b94b620974c` with the working-tree adapter at File Revision 1.0.7. Six isolated provider contract tests passed with `ResourceWarning` treated as an error. The complete PostgreSQL-backed suite passed 196/196 with zero skipped, failed, or errored tests. Tracemalloc locates the remaining suite ResourceWarning in the pre-existing M4.3 `tests/test_local_inference.py` threaded HTTP fixture when it replaces its server; the current M4.2 contract tests use no sockets.

An actual bounded Qwen3-0.6B request did not produce an accepted typed plan and returned sanitized `UNAVAILABLE`. No resident reasoning call, authority-state write, persistent model service, shared database change, or M3.3 service change occurred. This is not operational reasoning verification.
