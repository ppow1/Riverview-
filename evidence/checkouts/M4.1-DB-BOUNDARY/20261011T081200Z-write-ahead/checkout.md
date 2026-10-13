<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/M4.1-DB-BOUNDARY/20261011T081200Z-write-ahead/checkout.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Preserve verification for write-ahead Steward bootstrap capability
Authority: Private socket-only PostgreSQL 16.15; no live Steward identity mutation
Source: Working tree based on d3a0ed4fdec3061923964451ce2fccff18fadca7; source file hashes retained
History: artifacts.json SHA-256 manifest
-->
# M4.1 write-ahead Steward credential bootstrap

## Implementation

`AuthorityRegistry.bootstrap_steward` accepts an optional preallocated bearer
token, still requires effective root, stores only the SHA-256 digest, grants
only the fixed bootstrap authority set, and returns the token to its caller.
`scripts/bootstrap_authority_steward.py` is a fixed-path, no-argument,
root-only commissioning helper. It exclusively creates and fsyncs a 0600 token
file before the database transaction. It never prints credentials. It reuses
that file after an interrupted bootstrap and verifies an existing active
Steward by authorizing the exact `identity.manage` scope.

## Verification

- Focused institutional authority tests: **8/8 passed**.
- Complete applicable PostgreSQL-backed suite: **148/148 passed**, zero
  failures/errors/skips; 65.343 s. See `full-suite.log`.
- Fixture cleanup: zero `rvtest_*` schemas and zero test roles; private
  PostgreSQL cluster stopped. See `fixture-cleanup.txt`.
- Canonical graph: 13 graphs / 255 nodes, PASS.
- Controlled revision/predecessor audit: PASS, zero findings.
- `compileall`: PASS.
- Test uses only a disposable Unix-socket PostgreSQL 16.15 cluster. No live
  Steward identity or credential was created by these tests.

## Live commissioning boundary

The exact M4.1 ACL change is already live at the parent implementation commit
`d3a0ed4fdec3061923964451ce2fccff18fadca7`; its preflight and runtime denial
checks passed. This bootstrap addition is not in that deployment yet. The
Steward token file is still absent. Exact-head CI, root-owned source copy,
bootstrap execution, token mode/digest verification, post-restart authorization,
and independent service integration remain pending.

## Controlled source checksums

- `src/riverview_core/institutional_authority/registry.py`:
  `54ae06b5f0707b47a15912176738a0820bc9d46f35c8f37fe6fc99dcec2c8adc`
- `tests/test_institutional_authority.py`:
  `b51417ba4da5e2a52dd4f1aface1ec6a525d43a3a10d8bbb0e1039c06159f136`
- `scripts/bootstrap_authority_steward.py`:
  `7a11f04f165cc3c9bae5a3a7739739f378eec5bb97994b6f62514d3a2db7fd68`
- `docs/components/INSTITUTIONAL_AUTHORITY.md`:
  `606a72467e5413301f26a4f179ee34a416427a6e1022a04f762044f6ffd78963`
- `docs/components/INSTITUTIONAL_AUTHORITY_COOKBOOK.md`:
  `0d2f7a0e5b9d9c10a5ed7b728fcd724d1ceea94cf0b371482a47cbca414e5058`
- `docs/development/M4.1-001_REVISION_RECORD.md`:
  `fc9bfed02d8e2435e5b884bc357b5ebe788d45627af1fd0b833bf71b8cf11699`
