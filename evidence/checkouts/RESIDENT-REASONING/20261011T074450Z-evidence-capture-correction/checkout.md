<!--
Riverview~ Controlled Evidence Record
File: evidence/checkouts/RESIDENT-REASONING/20261011T074450Z-evidence-capture-correction/checkout.md
Component: RESIDENT-REASONING
File Revision: 1.0.0
Purpose: Preserve an evidence-capture failure and correction
Authority: No shared PostgreSQL state accessed
Changed: 2026-10-11 UTC | RV-M4.2-EVIDENCE-CAPTURE-CORRECTION | Preserve manifest self-reference failure details
History: artifacts.json checksums
-->
# Evidence capture correction

A revision-audit output was initially redirected directly onto the evidence file that the audit itself was validating. The shell truncated that file before the checker read it, producing `missing_revision` for the report. This was a report-capture sequencing defect, not a source revision defect. The final passing report was generated to a temporary path and copied only after the audit exited, then rechecked byte-for-byte.
