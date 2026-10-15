# PL-NEW-016 isolated browser evidence

Revision: 1.0.0

- Fixture: synthetic same-origin account-cookie dashboard; no production service used.
- Browser: Firefox 156.0.1 headless.
- Result: PASS, all 21 browser checks true, no JavaScript/browser errors.
- Navigation checks: first document opens one reusable documentation context; return link selects the existing dashboard context; a second guide reuses the documentation context; exactly two tabs remain.
- Auth checks: protected API calls used the account cookie and omitted bearer authorization.
- Screenshots and machine report are checksummed in `artifacts.json`.
- Earlier failed iterations are retained in sibling directories `20261015T211000Z-documentation-navigation/` and `20261015T211500Z-documentation-navigation/`. The first caught a WebDriver handle-shape assumption; the second proved `rel=noreferrer` prevented named-context reuse. Neither is the passing result.
- Production acceptance: UNVERIFIED; this evidence is isolated only.
