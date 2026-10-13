# M4.1 operations cookbook dashboard rendering regression

- Task: `RV-M4.1-DB-RESTORE-COOKBOOK`
- Source commit: `e314952c5b517a8bd3188d45487f9b12dc567ae3`
- Branch: `codex/m4.1-db-privilege-boundary`; PR #20 open/draft/unmerged
- Focused test: `PYTHONPATH=src pytest -q tests/test_status_dashboard.py -k component_cookbook_is_rendered_as_readable_safe_html` — PASS, 1 passed.
- The route serves the revised consolidated operations cookbook as escaped/readable HTML, including the observed PostgreSQL backup permission failure, exact safe diagnostics, protected destination/checksum, and no source metadata comments.
- Graph: 12 workflows / 227 nodes; revision audit: zero issues; compileall: exit 0.
- Exact-head GitHub controlled-checkout run 38119850300 passed all suite, graph and revision jobs.
- The backup/restore itself is recorded separately at `evidence/checkouts/M4.1-DB-BOUNDARY/20261011T070500Z-backup-restore/`; no live service/package change was made for this docs verification.
