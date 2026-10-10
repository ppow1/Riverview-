# Riverview~ RV-ENG-REV-003 revision-checkout correction

**Document Revision:** 1.0.4
**Task:** RV-ENG-REV-003
**Component:** ENG-REVISION-CONTROL
**Date:** 2026-10-10 UTC
**Status:** COMPLETED — baseline and staged-tree checkouts PASS
**Starting commit:** c24d7602d6d5fd411ed024a560dff42ca4427165

## Intake and finding

The repository checkout reported 58 `missing_revision` issues. Inspection showed
56 were versioned generated evidence whose adjacent `artifacts.json` sidecar
already recorded revision, checksum and size. Sidecars use both `artifacts` and
legacy `files` maps. The validator ignored both. The remaining true omissions
were `.gitignore` and the file-level revision header on
`docs/standards/ENGINEERING_RECORDS_STANDARD.md` (the standard itself already
identifies its normative Rev 1.0). All sidecar checksum/size values were verified
against current artifact bytes before changing the validator.

## Design and change

Teach `revision_control.py` to consume only exact evidence sidecar entries whose
revision, SHA-256, size, and optional basename agree with the bytes on disk; read
`manifest_revision` for `artifacts.json`; reject stale or malformed entries. A
legacy file with no prior revision may initialize at 1.0.0 only when exact prior
bytes are preserved in the backup manifest. Add regression tests for both sidecar
formats, tampering, and first-version preservation. Add metadata-only 1.0.0 file
revisions to the two identified legacy files without changing their behavior or
the Engineering Records Standard's Proposed status.

## Controlled-file preservation

Immediately preceding bytes of all changed existing files were captured and
read-back verified with `scripts/revision_control.py backup`. The task ID,
predecessor revision/checksum, backup path, and UTC timestamp are recorded in
`.riverview-backups/manifest.jsonl`. New task record starts at 1.0.0.

## Verification

Fifteen focused revision-control unit tests pass, including both supported
sidecar maps, checksum/size mismatch, malformed revision, native evidence
headers, and legacy initial revision with and without exact backup. The baseline
checkout check against `/tmp/rv-current-inventory.json` passes with zero issues.
The original 58 findings were 56 evidence entries correctly revisioned by their
`artifacts.json` sidecars and two actual file-level metadata omissions
(`.gitignore` and the Engineering Records Standard). During the first checker
update, a header-precedence regression temporarily classified 10 historical
text evidence records without sidecars as missing; preserving native text
headers ahead of sidecar lookup corrected that regression. Current tracked
baseline inventory contained 149 files. The staged-tree check after adding M1.2
implementation/evidence passed with zero issues across 160 files. After adding
this task's baseline/checker evidence, the final staged-tree check again passed
with zero issues across 164 files (exit 0). This includes the M1.2 source, task
records, and sidecar-versioned evidence. No evidence payload bytes were changed.
The complete 53-test checkout, including
15 revision-control and 6 PostgreSQL tests, passed on the committed M1.2 source;
see `evidence/checkouts/POSTGRES-LEDGER/20261010T1529Z-27a8c55/`. The baseline
snapshot and checker result are at
`evidence/checkouts/ENG-REVISION-CONTROL/20261010T1530Z-27a8c55/`.
