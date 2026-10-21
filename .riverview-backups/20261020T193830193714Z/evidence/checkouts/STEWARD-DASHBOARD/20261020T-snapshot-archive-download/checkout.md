<!-- Riverview~ Controlled engineering checkout record.
File: evidence/checkouts/STEWARD-DASHBOARD/20261020T-snapshot-archive-download/checkout.md
Component: STEWARD-DASHBOARD
File Revision: 1.0.0
Task ID: RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020
Owner: C2
Changed: 2026-10-20 UTC | Record synthetic acceptance for the archive and local browser-download workflow.
History: artifacts.json records exact artifact hashes; protected predecessors are in .riverview-backups/manifest.jsonl.
-->
# Snapshot archive plus local handoff checkout

## Definition of Ready

- **Task:** `RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020`.
- **Owner:** C2. **Component:** `STEWARD-DASHBOARD`.
- **Classification:** dashboard client workflow change with controlled tests, documentation, and process graph updates.
- **Scope:** reuse the current snapshot generator and private archive endpoint; deliver the same generated Blob to GitHub and the browser. Preserve local retry. No provider, server endpoint, service, database, or unrelated dashboard changes.
- **Dependencies:** the current authenticated snapshot APIs, CSRF-protected archive endpoint, protected server-side GitHub credential, Firefox/geckodriver, browser Web Crypto and Blob/download APIs.
- **Execution model:** request-driven explicit Steward action. One bounded capture, one archive request, and one browser download handoff.
- **Acceptance criteria and exact synthetic test reports:** [`acceptance.json`](acceptance.json).

## Design and preservation

The browser computes SHA-256 over the generated ZIP and requires the confirmed endpoint receipt to return the same byte count and digest before rendering archive success. The same Blob URL backs automatic download and the visible `Download ZIP` retry link. The UI retains the validated Release URL and a `Copy GitHub Link` action. Upload failures and digest mismatches retain a local download; browser download-start errors retain the confirmed Release result and retry action. Existing auth, CSRF, redaction, manifest, and package-bound controls remain in use.

Exact predecessor bytes and SHA-256 values were preserved before controlled edits. Backup mappings and restoration paths are recorded in `.riverview-backups/manifest.jsonl`; use `python3 scripts/revision_control.py check --baseline <baseline-inventory.json>` to verify those references. No production service was changed or restarted.

## Demonstrated functionality

Four synthetic Firefox reports cover successful archive plus download and matching hashes, archive failure with local download, a mismatched archive receipt digest, and the oversized package bound. All four passed. The success report confirms the ZIP appeared in Firefox's configured downloads directory, passed CRC/manifest verification, and has the same size and SHA-256 as the exact request body. The report also verifies release-link visibility, functional copy action, local retry visibility, and archive preservation if browser download start throws.

The focused server regression suite passed **67 tests** with **16 environment-dependent skips**. Process graph validation and controlled revision/backup validation passed. Raw ZIP packages were not retained in the checkout; only JSON reports and hashes are recorded.

## Eight-deliverable status

1. **Code and contracts — PASS for this change.** Exact source, endpoint, client/server authority boundary, digest, retry behavior, and failure cases are documented and tested.
2. **Functionality — PARTIAL.** Synthetic end-to-end Firefox and server tests pass. A real deployed Steward session and real private GitHub Release are intentionally not exercised here.
3. **Versioned documentation — PASS for this change.** The component specification and cookbook were updated with handoff, permission, failure, retry, digest, and browser-observation limitations.
4. **Troubleshooting/recovery cookbook — PASS for this change.** Archive failure, local retry, mismatch, and browser download-start failure recovery are documented.
5. **Versioned flowcharts — PASS.** The canonical dashboard workflow and generated Mermaid view include receipt validation and recovery branches; `process_graph.py check` passes.
6. **Steward live operational visualization — PARTIAL.** Existing dashboard remains the operational surface, but this revised client flow is not deployed; no production status is inferred from fixture output.
7. **Operational autonomy/blockers — PARTIAL / not applicable as unattended work.** Snapshot creation remains explicit user action. Blockers are integration review/merge and separately authorized deployment, followed by a real authenticated account and private archive acceptance. No hidden worker or background loop was introduced.
8. **Canonical process graph — PASS.** Stable nodes/edges updated and generated views validate together.

### Blocker register

| ID | Type | Signal / owner | Authority and recovery |
| --- | --- | --- | --- |
| `SNAPSHOT-ARCHIVE-PR-REVIEW` | approval | Draft PR exact-head CI and review; owner C2 | Steward/maintainer review and merge authorization; no code action required before review. |
| `SNAPSHOT-ARCHIVE-PRODUCTION-ACCEPTANCE` | dependency / approval | New client not deployed; C2 + Steward | Separate deployment authorization, authenticated production account, configured private-repository credential; perform one controlled archive/download verification and rollback if it fails. |

## Rollback and continuation

Rollback is a normal Git revert of the isolated PR commit. Because no production configuration, database, credentials, or service was changed, no live rollback action is required. Resume at exact-head CI/review; after separate deployment authorization, verify real browser download visibility, archive receipt digest equality, ZIP integrity, privacy declarations, and local retry.
