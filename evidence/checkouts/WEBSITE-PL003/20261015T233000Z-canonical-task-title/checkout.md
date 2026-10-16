# PL-NEW-003 isolated browser evidence

Revision: 1.0.0

- Fixture: isolated synthetic account-cookie dashboard and canonical graph response; no production service.
- Browser: Firefox 156.0.1, headless.
- Result: PASS, 31/31 checks true, no browser errors.
- Verified: the assignment row and detail resolve the human-readable canonical node label only by exact persisted graph/node IDs; assignment, graph and node IDs remain visible. Missing node references are explicitly unresolved.
- Report and screenshots are checksummed in `artifacts.json`.
- Production acceptance: UNVERIFIED.
