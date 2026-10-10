# RV-M1.1-007 failed commissioning attempt and partial-state inspection

**Document Revision:** 1.0.0
**Task:** RV-M1.1-007
**Environment:** Camrui (`admin1-Default-string`), Ubuntu 24.04.3
**Failed package source:** `b15b093642f65f6de36c1b977571ae2b79f04850`
**Failure source:** Steward-provided installer output; no credential input was recorded.

The user-reported exception was `io.UnsupportedOperation: File or stream is not seekable` at `scripts/provision_pgpass.py` line 36, opening `/dev/tty` in `r+` mode. The same exception was reproduced locally under a pseudo-terminal with Python 3.12.3 and no password input.

Read-only post-failure inspection observed:

- `riverview` OS account exists with UID 997 and `/usr/sbin/nologin`.
- `/etc/riverview` exists as root:root mode 0700; `/etc/riverview/pgpass` is absent.
- `/opt/riverview/releases/b15b093642f65f6de36c1b977571ae2b79f04850` exists as root:root mode 0700. Non-root traversal was denied, so contents were not inspected.
- `/var/lib/riverview`, `/opt/riverview-core`, and `/etc/systemd/system/riverview-baseline.service` are absent.
- PostgreSQL 16/main is active.

No password or passfile contents were read, logged, or changed. No database object or unrelated service was modified. The prompt failed before creating the passfile or later deployment resources. The installer can safely reuse the existing account and root-owned release after confirming its file manifest; the corrected path normalizes only access bits after checksum verification. The previously staged package remains byte-for-byte intact; its 71 manifest entries were rechecked successfully.
