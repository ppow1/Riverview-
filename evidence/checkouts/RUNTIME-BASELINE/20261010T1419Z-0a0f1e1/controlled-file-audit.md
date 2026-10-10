# RV-M1.1-008 controlled-file checkout audit

**Document Revision:** 1.0.0  
**Task:** RV-M1.1-008  
**Component:** ENG-REVISION-CONTROL  
**Date:** 2026-10-10 UTC

`python3 scripts/revision_control.py check --baseline /tmp/rv-m1.1-008-baseline.json` returned FAIL with preexisting missing-revision findings for 27 files (legacy `.gitignore`, the Engineering Records Standard, and older evidence artifacts). The findings are outside the files changed for this task and were already present in the captured pre-change inventory. No baseline or standards were edited to suppress the findings.

An affected-file check using the same revision and backup-verification functions passed for every modified existing controlled file:

| File | Prior | Current | Predecessor checksum/backup | Result |
| --- | --- | --- | --- | --- |
| `scripts/runtime_baseline.py` | 1.0.0 | 1.0.1 | Verified | PASS |
| `tests/test_runtime_baseline.py` | 1.0.2 | 1.0.3 | Verified | PASS |
| `docs/components/RUNTIME_BASELINE_COOKBOOK.md` | 1.0.3 | 1.0.4 | Verified | PASS |
| `docs/development/JOURNAL.md` | 1.0.6 | 1.0.8 | Both immediate predecessors verified | PASS |

New revision and checkout records declare revision 1.0.0. The repository-wide revision checkout is **NOT PASS** until the legacy missing-revision findings are addressed under the governing migration process. This task does not claim repository-wide controlled-file compliance.
