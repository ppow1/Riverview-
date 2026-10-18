<!--
Riverview~ Controlled Development Record
File: docs/development/RV-C3-GRACE-ENGINEERING-E2E-001_LIFECYCLE_AMENDMENT.md
Component: RESIDENT-ORCHESTRATION / INSTITUTIONAL-PROPOSALS
Document Revision: 1.0.0
Purpose: Record restoration data for later revisions of C3 acceptance and evidence records
Authority: Development-only; no production or operational authorization
Changed: 2026-10-18 UTC | RV-C3-GRACE-ENGINEERING-E2E-001 | Complete recoverability metadata after evidence sidecar correction
Contracts: docs/standards/DEVELOPMENT_LIFECYCLE_STANDARD.md; docs/standards/ENGINEERING_RECORDS_STANDARD.md
Tests: evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/
History: Git and .riverview-backups/manifest.jsonl
-->
# C3 evidence record restoration amendment

**Task:** RV-C3-GRACE-ENGINEERING-E2E-001.  
**Tested source commit:** `3a2e9b9fdec0b5c5a7ed6264147af300f93ca6cf`.  
This amendment completes the restoration metadata for evidence-record versions created while correcting the nested evidence sidecar. The prior versions are retained under `.riverview-backups/`; their abbreviated helper rows remain append-only in the manifest.

| File | Predecessor → current | SHA-256 of predecessor | Git blob of predecessor | Saved predecessor | Restore procedure |
|---|---|---|---|---|---|
| `docs/development/RV-C3-GRACE-ENGINEERING-E2E-001_ACCEPTANCE_RECORD.md` | 1.0.1 → 1.0.2 | `bf72ca447ca7ac00748c89ee0572f63e722603c4e657d4fcd87498299c7d61da` | `bffc8bb0e81ceb4ab7a9b3a59cb2686ebe5508dd` | `.riverview-backups/20261018T181017636571Z/docs/development/RV-C3-GRACE-ENGINEERING-E2E-001_ACCEPTANCE_RECORD.md` | `install -m 0644 <saved-predecessor> docs/development/RV-C3-GRACE-ENGINEERING-E2E-001_ACCEPTANCE_RECORD.md`; verify SHA-256. |
| `docs/development/RV-C3-GRACE-ENGINEERING-E2E-001_LIFECYCLE_SUPPLEMENT.md` | 1.0.0 → 1.0.1 | `793f218690ae994f7ba7bb37115e9c22a3705a1acf483927d75babfe4433bf8a` | `5241e6379ccb529a6b2a8a462a221a20c343fec5` | `.riverview-backups/20261018T181017889611Z/docs/development/RV-C3-GRACE-ENGINEERING-E2E-001_LIFECYCLE_SUPPLEMENT.md` | `install -m 0644 <saved-predecessor> docs/development/RV-C3-GRACE-ENGINEERING-E2E-001_LIFECYCLE_SUPPLEMENT.md`; verify SHA-256. |
| `evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/checkout.md` | 1.0.1 → 1.0.2 | `32fe6fc2df42101728f62f68aef711e23670c5ea7b415429e24af02a07d1da7f` | `475bbed6b7f4488b6848a90d37403b1b92cb7a6a` | `.riverview-backups/20261018T181018107488Z/evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/checkout.md` | `install -m 0644 <saved-predecessor> evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/checkout.md`; verify SHA-256. |
| `evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/artifacts.json` | manifest 1.0.1 → 1.0.2 | `065aae6c3706da357f54bf8c928febe05c79b0e63ca22f985c703009c7c063f4` | `9872fe5baeba76ac65c114c6ca9e6355f3a6f343` | `.riverview-backups/20261018T180948518006Z/evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/artifacts.json` | `install -m 0644 <saved-predecessor> evidence/checkouts/RV-C3-ENGINEERING-E2E/20261018T1753Z-3a2e9b9/artifacts.json`; verify SHA-256. |

The source commit identifies the unchanged candidate implementation against which the evidence was produced. Each blob ID identifies the exact evidence predecessor bytes; each SHA-256 is verified against its saved backup. Restoration means restoring only the listed file and verifying its hash. The lifecycle supplement records the earlier evidence-file versions; the acceptance record contains the two original test-file predecessors and their recovery instructions.
