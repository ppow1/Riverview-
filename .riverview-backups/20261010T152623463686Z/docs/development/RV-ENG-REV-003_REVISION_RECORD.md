# Riverview~ RV-ENG-REV-003 revision-checkout correction

**Document Revision:** 1.0.1
**Task:** RV-ENG-REV-003
**Component:** ENG-REVISION-CONTROL
**Date:** 2026-10-10 UTC
**Status:** IMPLEMENTED — baseline checkout PASS; staged-tree checkout pending
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
At this check the tracked checkout inventory contained 149 files and zero
missing revisions. The 10 previously flagged files were legacy text evidence
with native `Document Revision: 1.0.0` headers; the validator incorrectly forced
all evidence through sidecars. The remaining 48 of the original 58 were already
correctly versioned by sidecars. No evidence artifact bytes were changed. Final
staged-tree check remains pending because new M1.2 files are not yet tracked.
