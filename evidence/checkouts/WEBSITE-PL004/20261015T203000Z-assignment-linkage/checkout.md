<!-- Riverview~ controlled evidence
File: evidence/checkouts/WEBSITE-PL004/20261015T203000Z-assignment-linkage/checkout.md
Component: STEWARD-DASHBOARD / WEBSITE
File Revision: 1.0.0
Purpose: Record isolated assignment graph/node linkage browser verification
Authority: Synthetic browser fixture only; no production data or service access
Changed: 2026-10-15 UTC | RV-WEBSITE-PL004 | Verify populated and absent persisted assignment references
History: Git and artifacts.json checksum manifest
-->
# PL-NEW-004 isolated Firefox verification

Firefox 156.0.1 loaded the checked-out dashboard shell, CSS and JavaScript. A synthetic same-origin account cookie was required for read-only fixture requests. The populated assignment displayed its stored graph/node IDs and linked only the component cookbook route. A second assignment with null identity displayed explicit missing states; a script-scheme diagnostic value remained inert text. The browser error list was empty, fixture API requests carried the account cookie and omitted bearer Authorization, and all seven reported checks passed.

This proves isolated rendering and safe link behavior only. It does not verify a production assignment or establish current execution position.
