<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/M4.1-DB-BOUNDARY/20261011T080600Z-apply-required/checkout.md
Component: INSTITUTIONAL-AUTHORITY
File Revision: 1.0.0
Purpose: Record final M4.1 privilege preflight correction and complete regression results
Authority: Disposable socket-only PostgreSQL 16.15; shared Camrui schema unchanged
Source: Changes tested on working tree based on e73844acfb921ea0573361c03c48ff603efb29a5; exact changed-file hashes in source-files.sha256
History: artifacts.json SHA-256 manifest
-->
# M4.1 boundary preflight completeness

## Corrected failure path

After `db_boundary.py` 1.0.6 fixed owner schema USAGE, the first committed
version's live dry-run still reported `apply_required=false` because that field
only considered role creation and table ownership. The live boundary remained
unmodified. Source 1.0.8 now checks all allowed schema/table access conditions
in dry-run and detects an absent owner role safely. The report returns
`apply_required=true` if runtime access, manager access, owner usage/create,
table owner, or allowlisted manager DML differs from the intended contract.

The isolated test revokes owner `USAGE` after ownership transfer, confirms the
read-only preflight reports repair required, reapplies, then proves FK-backed
credential/grant/event writes work through the manager. Owner and manager
`CREATE` remain denied; runtime remains denied; manager has no owner membership.

## Verification

- Focused boundary integration module: **3/3 passed** on PostgreSQL 16.15.
- Complete suite: **147/147 passed**, zero skips/failures/errors, 64.355 s.
  See `full-suite.log`.
- Fixture cleanup: **0** test schemas and **0** test roles; the private cluster
  was stopped. See `fixture-cleanup.txt`.
- Canonical graph synchronization: **13 graphs, 255 nodes, PASS**.
- Controlled source revision/predecessor audit: **PASS**, zero findings.
- Python compileall: **PASS**.
- No shared database was modified by these isolated tests.

The final source was based on `e73844acfb921ea0573361c03c48ff603efb29a5` with
the working-tree changes pinned in `source-files.sha256`. Exact-head CI and a
new root-owned dry-run of the corrected provisioner are pending. The previous
CI run 38123498035 passed for the owner-USAGE correction before this additional
preflight fix; it does not cover source 1.0.8.

No live grant has been applied by this evidence run. Steward bootstrap remains
absent; runtime denial, registry authorization, and service integration checks
are still required before claiming M4.1 commissioning.
