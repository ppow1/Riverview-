# PL-NEW-019 isolated browser evidence

Revision: 1.0.0

- Fixture: synthetic account-cookie conversation with 40 long messages; no production service.
- Browser: Firefox 156.0.1, headless.
- Result: FAIL preserved: transcript was scrollable and last message visible, but composer overlay and page horizontal overflow were detected before the CSS correction.
- Browser report and screenshots are checksummed in `artifacts.json`.
- The run requested a 390px window; Firefox exposed a 500px minimum CSS viewport. No claim is made below 500px.
- Production acceptance: UNVERIFIED.
