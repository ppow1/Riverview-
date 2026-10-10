# RV-M1.1-008 diagnostic package verification

**Document Revision:** 1.0.0  
**Task:** RV-M1.1-008  
**Component:** RUNTIME-BASELINE  
**Package source commit:** `e6b46c362326900c09f9e5c59d27d18137004847`  
**Date:** 2026-10-10 UTC

A fresh archive was built without modifying or replacing any prior staged package:

- Archive: `/home/admin1/riverview-M1.1-e6b46c3-20261010T1421Z.tar.gz`
- SHA-256: `f8edce0fe29e3c8edace87f93c467ae6d20831badfdad4733d03f8f5f3095c7b`
- Size: 593030 bytes; 123 regular-file members
- Unique extraction stage: `/home/admin1/riverview-M1.1-008.Xi8ZMaPZ`
- `scripts/verify_camrui_package.py`: manifest PASS; shell compatibility PASS for installer and rollback; both scripts LF-only with no BOM, CR or NUL.
- Extracted `PACKAGE_SHA256SUMS`: every listed file PASS.
- Extracted installer and rollback `sh -n`: PASS.

This commit adds diagnostic detail only; it is not the root-cause correction. The package must not be called corrected or accepted until the service-context reason is observed and repaired. Because no passwordless sudo authorization is configured, the single reviewed local commissioning invocation is:

```bash
sudo sh /home/admin1/riverview-M1.1-008.Xi8ZMaPZ/deploy/install_baseline.sh
```

The installer preserves the prior active link and unit in a new rollback record, installs a commit-addressed release, updates the active symlink, and starts the read-only diagnostic. Existing account, state, and credential are reused; the script does not reset database credentials or alter schemas. The command requires interactive sudo authentication. No password should be placed in chat or command arguments.
