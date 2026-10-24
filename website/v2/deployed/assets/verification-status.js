// Revision: 1.0.0
/* V2 summary reads the LAN-only redacted acceptance projection. */
(() => {
  "use strict";
  const node = document.getElementById("website-verification-state");
  if (!node) return;
  fetch("/v2/verification/latest.json", {cache:"no-store", credentials:"same-origin"})
    .then((response) => { if (!response.ok) throw new Error("report_unavailable"); return response.json(); })
    .then((report) => {
      if (report.schema_version !== "rv.website-acceptance.v1" || !Array.isArray(report.checks)) throw new Error("report_invalid");
      const counts = Object.fromEntries(["PASS","FAIL","WARNING","SKIPPED"].map((status) =>
        [status, report.checks.filter((check) => check.status === status).length]));
      node.textContent = `${report.overall} · ${new Date(report.timestamp).toLocaleString()} · ${counts.PASS} passed, ${counts.FAIL} failed, ${counts.WARNING} warnings, ${counts.SKIPPED} skipped.`;
    })
    .catch(() => { node.textContent = "No automated acceptance report is available."; });
})();
