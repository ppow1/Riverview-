# RV-M1.1-008 package verification checkpoint

**Document Revision:** 1.0.0  
**Task:** RV-M1.1-008  
**Component:** RUNTIME-BASELINE  
**Target:** Camrui, Ubuntu 24.04.3  
**Source commit:** `e386eaf8b573ba0f8a3d0ecf1f0cfc7df825a98f`  
**Date:** 2026-10-10 UTC

The newly built package includes the runtime path-reason diagnostics and the updated component contract (Rev 1.0.4). It was built into a unique path; the previous staged package and earlier diagnostic package were left unchanged.

- Archive: `/home/admin1/riverview-M1.1-e386eaf-20261010T1424Z.tar.gz`
- Archive SHA-256: `0baa2cf8ae02ec8ae49eb64f0600f0f16b2759c11fdf624df6b2236ca6eeb145`
- Archive verifier: manifest PASS; installer and rollback shell compatibility PASS; 0 CR, CRLF, BOM, or NUL bytes.
- Extracted to unique stage `/home/admin1/riverview-M1.1-008b.g3rwlz3A`; all 127 checksum entries PASS; both shell scripts pass `sh -n`.
- Code regression tests: 22 focused pass; complete checkout suite was 41 tests (38 pass, 3 PG tests skipped for absent test DSN). The code/test bytes are unchanged from tested source commit `e6b46c362326900c09f9e5c59d27d18137004847`; the intervening commit updates specification and records only.

This is a **diagnostic deployment package**, not an accepted root-cause repair. It preserves every security predicate and adds an enumerated reason to the sanitized report. Root-authorized commissioning is still required to observe that reason in the unit namespace. The reviewed operation is:

```bash
sudo sh /home/admin1/riverview-M1.1-008b.g3rwlz3A/deploy/install_baseline.sh
```

`sudo -n -l` found no noninteractive authorization; this command therefore needs interactive sudo authentication. It updates only the Riverview development deployment and starts its read-only diagnostic. No database credential reset, schema mutation, production action, or unrelated service change is in scope.
