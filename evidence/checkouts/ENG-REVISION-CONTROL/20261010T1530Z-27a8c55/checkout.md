# Riverview~ RV-ENG-REV-003 staged-tree revision checkout

**Document Revision:** 1.0.0
**Task:** RV-ENG-REV-003
**Component:** ENG-REVISION-CONTROL
**Timestamp UTC:** 2026-10-10T15:30Z
**Source commit:** `27a8c555501588dd0fd2a5d488018ad0c295199a`
**Branch:** `codex/m1.1-runtime-commissioning`
**Target:** Camrui checkout; admin1; Ubuntu 24.04.3

The preserved baseline inventory is from the RV-ENG-REV-003 starting tree at
`c24d7602d6d5fd411ed024a560dff42ca4427165` (149 tracked files). It is retained
here with the checker JSON. Command:

```text
python3 scripts/revision_control.py check --baseline /tmp/rv-current-inventory.json
```

Initial result: exit 0, `passed=true`, zero issues. After this evidence bundle
was staged, the same checker was rerun against the preserved baseline; it again
returned exit 0 with zero issues across 164 files. The initial 58 findings were
resolved by validated sidecar support and metadata-only initialization of the two
actual omissions. No historical evidence payload was rewritten.

Fifteen focused revision-control tests pass. The full committed-source test log
is linked at
`../POSTGRES-LEDGER/20261010T1529Z-27a8c55/unittest.log` and includes all 15
revision-control cases. Backup path/hash records are in
`.riverview-backups/manifest.jsonl`.
