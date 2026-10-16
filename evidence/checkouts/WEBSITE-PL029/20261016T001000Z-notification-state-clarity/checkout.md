# PL-NEW-029 isolated browser evidence

Revision: 1.0.0

- Fixture: isolated synthetic account-cookie dashboard with delivered, acknowledged, and pending decision notice data; no production service.
- Browser: Firefox 156.0.1, headless.
- Result: PASS, 33/33 checks true, no browser errors.
- Verified: dashboard rendering and person-seen state are separate, receipt acknowledgment and decision request status are separately labeled, attention-condition resolution is not presented as a decision outcome.
- Browser report and screenshots are checksummed in `artifacts.json`.
- Production acceptance: UNVERIFIED.
