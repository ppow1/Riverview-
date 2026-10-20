# RIVERVIEW~ CONTROLLED ACCEPTANCE RECORD

**File:** `evidence/checkouts/STEWARD-DASHBOARD/20261020T-snapshot-github-archive/checkout.md`  
**Component:** STEWARD-DASHBOARD  
**Revision:** 1.0.0  
**Task:** RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020  
**Owner:** C2  
**Classification:** L3 dashboard feature / authenticated external archival integration  
**Scope:** Dashboard-generated bounded ZIP archival to a configured private GitHub Release, with browser-local fallback. No deployment or external provider credentials used.

## Definition of Ready

- Starting commit: `cb7ee02fc883d468e8f20fb22ec8840acc7fd4f8`.
- Isolated branch: `codex/snapshot-github-archive-20261020` in `/tmp/rv-snapshot-github-archive-20261020`.
- Related snapshot-size repair was copied into this integration branch from `/tmp/rv-snapshot-bound-20261020`; that checkout was not modified by this archival work.
- Existing dashboard API bearer is not Steward authority. The new endpoint requires a CSRF-validated Steward account-cookie session.
- GitHub repository identity and credential were not provided. Runtime configuration remains optional and fail-closed; the dashboard retains local download when unconfigured.
- No production dashboard, GitHub repository, or real credential was accessed.

## Implementation

- Added `snapshot_archive.py`: validates ZIP structure/CRC, stored members, 96 MiB uncompressed bound, manifest file set, member SHA-256/size, and required redaction assertions. Creates a uniquely tagged draft Release, uploads the ZIP asset, publishes the Release, and best-effort removes its exact draft/tag on upload failure. It stages no files on disk.
- Added `POST /api/v1/snapshot/archive`, bounded to one concurrent upload and authenticated by the existing Steward account/CSRF mechanism. It returns only Release URL, timestamped ID, asset name, size, digest, and permanent-retention metadata.
- Updated the browser exporter to archive first, show a private Release link and temporary local-copy link on success, and display a safe error plus auto-download the existing local ZIP on failure.
- Added an optional systemd drop-in example using `LoadCredential=snapshot-github-token`; the active unit was not changed.
- Integrated the existing 76 MiB raster/16 MiB structured/4 MiB manifest package policy and documentation-catalog readiness correction without editing the other checkout.
- Updated the dashboard API schema, component/cookbook documentation, and canonical process graph.

## Exact checkout evidence

See `acceptance.json` for exact command strings, exit codes, archive hashes, sizes, failed-attempt record, and environment limits.

- Python archive/dashboard suite: **54 passed, 10 skipped**, exit 0.
- Final normal browser acceptance: **PASS**, exit 0; complete 24,782 CSS-pixel documentation capture, all 15 detail tiles, all structured diagnostic members, ZIP integrity and manifest checks. ZIP SHA-256 `465868d8596ce9e2b493245a997c8d42fa4ee59e1e663e845651b9488633bb61` (71,763,017 bytes). The fixture had no Steward CSRF cookie; it verified the clear fallback error and local download without posting the ZIP.
- Final oversized visual stress: **PASS**, exit 0; 17 listed raster omissions absent from the ZIP, all structured/canonical members preserved, completeness truthfully false. ZIP SHA-256 `8f303efa9595ad9ff32c267579c4b8051c579884e6207eaedc5158894393305a` (83,137,423 bytes).
- GitHub create/upload/publish and failed-upload cleanup were verified through a fake REST transport; no live GitHub request was made.
- Process graph: 22 graphs / 599 nodes, `check` PASS. Syntax, compilation, JSON parsing, and whitespace checks passed.
- One earlier normal fixture attempt failed from a synthetic `/api/v1/events` polling UI error; a subsequent normal attempt and final attempt passed. The failure is retained in `acceptance.json`.

## Security, rollback, and readiness

The GitHub token is read only from the systemd credential directory, with no-follow regular-file checks and restrictive permissions. It is never sent to browser code, included in release metadata, or logged. The target repository must pass GitHub's private-repository check. Metadata contains only capture ID, source/deployment revision, timestamp, ZIP size and SHA-256. No snapshot ZIP was committed or retained as a permanent development/server file.

Modified-file predecessors are retrievable under `.riverview-backups/` and listed in `.riverview-backups/manifest.jsonl`; restoration uses the manifest backup path and verifies its recorded SHA-256 before replacing the file. To roll back this candidate, restore the listed predecessor for each changed file and remove the new `snapshot_archive.py`, optional drop-in example, and acceptance artifacts. The active dashboard unit has not been changed or restarted.

**Integration status:** source and synthetic checkout ready for review. Live archival acceptance and deployment remain NOT VERIFIED until Steward identifies/provisions the dedicated private repository and protected GitHub credential, then separately authorizes the drop-in installation and dashboard release/restart.
