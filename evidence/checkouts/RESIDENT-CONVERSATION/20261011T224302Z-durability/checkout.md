<!--
Riverview~ Controlled Evidence
File: evidence/checkouts/RESIDENT-CONVERSATION/20261011T224302Z-durability/checkout.md
Component: RESIDENT-CONVERSATION
File Revision: 1.0.0
Task: RV-M3.4-CHAT-DURABILITY-001
History: See artifacts.json and Git
-->
# Grace conversation durability regression checkout

**Recorded:** 2026-10-12 02:43 UTC (2026-10-11 America/New_York)  
**Task:** RV-M3.4-CHAT-DURABILITY-001  
**Host:** Camrui, Ubuntu 24.04.3  
**Branch/base:** `codex/m3.4-grace-web-conversation`, pre-change HEAD `ea6748729fabfa3b93e3abb457f4e0e46357be26`  
**Scope:** Isolated PostgreSQL regression and source correction; no shared runtime/database was changed in this checkout.

## Incident and cause

The saved commissioning record `grace-chat-20261011T212238Z/commissioning-summary.json` records an authenticated API history with six events, an independent PostgreSQL read with four, and the dashboard's conversation connection idle in transaction. Browser content was not copied into this checkout evidence.

`DashboardHTTPServer` dispatches up to 16 requests on separate threads. `ConversationStore` kept one psycopg connection for its event reads/writes and exact-grant checks; the supplied `AuthorityRegistry` also kept a shared connection for office binding reads. The locks in the old code serialized only sends for the same conversation. Independent conversations, history requests and authority checks could therefore interleave psycopg transaction contexts on a single connection. Before code changes, an isolated ten-request PostgreSQL stress replay against the old checkout reproduced `psycopg.transaction.OutOfOrderTransactionNesting` during authorization commit, followed by `ConversationUnavailable`; this demonstrates the transaction-context race. It did not recreate the exact numerical six-versus-four count, and no successful mismatched acknowledgment is claimed from the isolated run. The original count discrepancy and idle-in-transaction observation remain the live incident evidence.

## Correction

The conversation store now serializes each access to its shared database connection with a reentrant lock. Each guarded operation checks that the connection returns to `IDLE`; an unexpected open/failed transaction is rolled back and the request fails closed rather than returning a success. Exact office-binding reads on the service's shared `AuthorityRegistry` connection are serialized separately. Locks are released before inference, so separate conversations retain concurrent model execution. User events commit before inference; assistant/failure events commit before the API result is returned.

## Verification

- **Before-change fault reproduction:** isolated PostgreSQL 16.15; ten synchronized request threads; the old implementation raised `OutOfOrderTransactionNesting` from psycopg transaction exit. The cluster was throwaway and automatically dropped. This was a mechanism reproduction, not a claim that the exact 6/4 counts were reproduced.
- **Focused post-change integration:** `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='dbname=postgres' pg_virtualenv -t python3 -m unittest -v tests.test_resident_conversation` — 10 tests passed. Includes a fresh independent DB read from the provider boundary proving the user event committed before inference; fresh-connection visibility after successful and failed API acknowledgments; eight concurrent independent conversations with API/DB sequence equality; restart-recovered interruption; dashboard HTTP history after server restart; and no idle transaction on the service backend.
- **Complete post-change suite:** `PYTHONPATH=src RIVERVIEW_TEST_PG_DSN='dbname=postgres' pg_virtualenv -t python3 -m unittest discover -s tests -v` — 227 tests passed, zero failures, zero skips (102.268 seconds). Exact output is `full-suite.log`.
- **Process graphs:** `python3 scripts/process_graph.py check` — PASS, 17 graphs / 348 nodes. No process transition changed, so canonical graph regeneration was not needed.
- **Controlled revisions:** repository baseline audit — PASS, no issues. Exact output is `revision-audit.json`.
- **Compile:** `python3 -m compileall -q src/riverview_core/resident_execution/conversation.py tests/test_resident_conversation.py` — PASS.

## Deployment status

No candidate release has been staged or activated yet. The functioning dashboard remains at its previous deployment, commit `8556598b19a7da4aa191a600c767d79d24432afe`. The earlier database backup and additive migration evidence are preserved; live recommissioning still requires building and validating a corrected immutable candidate, taking/validating a current protected backup, and repeating external/browser checks with an independent database connection after each acknowledged response.

No credentials or conversation content are included in this evidence.
