<!--
Riverview~ Controlled Evidence Record
File Revision: 1.0.0
Component: EXTERNAL-REASONING-MCP-TRANSPORT
Task: RV-GRACE-CHATGPT-P0-C4-MCP
-->
# C4 exact-proposal MCP adapter working-tree verification

**Evidence class:** Isolated development worktree run before commit; no live provider.
**Branch:** `codex/c4-external-review-mcp-20261018`.
**Parent:** PR #119 head `97128626df967bc992696dca38eaa7116f3616e9`.
**Command:** `PYTHONPATH=src python3 -m pytest -q tests/test_external_reasoning_mcp.py`.
**Result:** 13 passed, 0 failed, 0 skipped. Synthetic OAuth identity and in-memory exchange fixture; no PostgreSQL or external network/client activity.
**Coverage:** Existing MCP HTTP/OAuth regressions plus bounded exact-subject list exposure, canonical digest validation, conflicting/malformed/oversized subject rejection, digest echo and correlation rejection, and legacy advisory compatibility.
**Additional checks:** `python3 -m py_compile src/riverview_core/resident_execution/external_reasoning_mcp.py scripts/run_external_reasoning_mcp.py tests/test_external_reasoning_mcp.py` and `git diff --check` passed.
**Limit:** This is C4 adapter evidence only. Full disposable PostgreSQL lifecycle/restart tests depend on C2/C3 integration. Graph and revision checks passed locally; exact-head CI remains pending.
