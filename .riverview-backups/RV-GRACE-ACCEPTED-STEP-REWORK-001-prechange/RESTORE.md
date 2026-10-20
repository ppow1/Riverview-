# RV-GRACE-ACCEPTED-STEP-REWORK-001 predecessor preservation

Source commit: `30515c07ed80adb31ab01f6a4abaff99a9190135`.

The exact pre-change bytes of `.riverview-backups/manifest.jsonl` are in `manifest.jsonl.predecessor` (SHA-256 `df8bd487db3c46dd3168c7b471478ac94407f911374fb82f86c5cfa556bd0125`). To restore this ledger, copy that file back to `.riverview-backups/manifest.jsonl`; do not restore unrelated application state. Other modified-file predecessors are preserved by `scripts/revision_control.py backup` records appended after this snapshot, keyed to the same task ID. Their restoration command is `cp .riverview-backups/<record backup path> <record path>`, then restore the corresponding `.riverview-revisions.json` predecessor before validation.
