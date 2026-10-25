// Revision: 1.0.1
/* Reusable, read-only evidence disclosure for Work and Engineering Progress. */
(() => {
  "use strict";
  const adapter = window.RiverviewV2WorkEvidenceAdapter;
  if (!adapter) return;
  const text = (value) => value == null || value === "" ? "Unavailable in the current projection" : String(value);
  const element = (tag, value, className) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (value !== undefined) node.textContent = text(value);
    return node;
  };
  const recordTime = (value) => {
    if (!value) return "Not recorded";
    const date = new Date(value);
    return Number.isNaN(date.valueOf()) ? "Timestamp unavailable" : date.toLocaleString();
  };
  function appendField(list, label, value) {
    list.append(element("dt", label), element("dd", value));
  }
  function safeLink(parent, href, label) {
    if (!href) return;
    const link = element("a", label);
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    parent.append(link);
  }
  function renderAssignmentDetail(target, detail) {
    target.replaceChildren();
    if (!detail || detail.status !== "available" || !detail.assignment) {
      target.append(element("p", "Assignment evidence is unavailable; its source did not confirm this detail."));
      return;
    }
    const assignment = detail.assignment;
    const meta = element("dl", undefined, "work-evidence-fields");
    appendField(meta, "Assigned owner", assignment.owner);
    appendField(meta, "Workflow stage", assignment.workflow_step || assignment.workflow_id);
    appendField(meta, "Assignment updated", recordTime(assignment.updated_at));
    appendField(meta, "Process graph node", assignment.process_node_id);
    appendField(meta, "Correlation ID", assignment.correlation_id);
    target.append(meta);
    target.append(element("h4", "Related outputs"));
    const outputs = Array.isArray(detail.outputs) ? detail.outputs : [];
    if (!outputs.length) {
      target.append(element("p", detail.outputs_status === "no_recorded_outputs"
        ? (assignment.state === "running" || ["queued", "ready"].includes(assignment.state)
          ? "No deliverable recorded yet."
          : assignment.state === "completed" ? "Completed work has no output record supplied."
            : "No output record is available for this assignment.")
        : "Output status unavailable from the current projection."));
    } else {
      const list = document.createElement("ul");
      list.className = "work-output-list";
      for (const output of outputs) {
        const item = document.createElement("li");
        const label = output.name || "Recorded output (name unavailable)";
        item.append(element("strong", label));
        const provenance = [
          output.media_type || "type unavailable",
          output.producing_assignment ? `assignment ${output.producing_assignment}` : null,
          output.producing_attempt ? `attempt ${output.producing_attempt}` : null,
          output.capability || null,
          `recorded ${recordTime(output.recorded_at)}`,
          `verification: ${output.verification_status || "unknown"}`,
          `publication: ${output.publication_status || "not recorded"}`
        ].filter(Boolean).join(" · ");
        item.append(element("small", provenance));
        if (output.summary) item.append(element("p", output.summary));
        if (output.location_url && output.location_status === "recorded_not_verified") {
          safeLink(item, output.location_url, "Open recorded location (publication not independently verified)");
        } else {
          item.append(element("small", output.availability === "inaccessible"
            ? "Recorded output is inaccessible."
            : "Recorded metadata only; no authorized download route is available."));
        }
        list.append(item);
      }
      target.append(list);
      if (detail.outputs_truncated) {
        target.append(element("p", "Output history is bounded to the eight most recent worker attempts; older outputs are omitted."));
      }
    }
    const imageArtifacts = Array.isArray(detail.comfyui_artifacts) ? detail.comfyui_artifacts : [];
    if (imageArtifacts.length) {
      target.append(element("h4", "Verified downloadable images"));
      const list = document.createElement("ul");
      for (const artifact of imageArtifacts) {
        const item = document.createElement("li");
        const label = `${artifact.name} · ${artifact.bytes} bytes · SHA-256 ${artifact.sha256}`;
        const expectedPath = /^\/api\/v1\/assignments\/[A-Za-z0-9:._-]{1,128}\/artifacts\/[1-8]$/;
        if (typeof artifact.download_url === "string" && expectedPath.test(artifact.download_url)) {
          safeLink(item, artifact.download_url, `Download ${artifact.name}`);
        } else item.append(element("span", label));
        item.append(element("small", ` · verified ${artifact.verification || "ACCEPTED"}`));
        list.append(item);
      }
      target.append(list);
    }
    if (detail.attempts?.length) {
      target.append(element("h4", "Worker attempts"));
      const attempts = document.createElement("ul");
      for (const item of detail.attempts) {
        const worker = item.worker_id || "Worker not recorded";
        attempts.append(element("li", `${worker} · ${item.status || "status unavailable"} · started ${recordTime(item.started_at)}${item.finished_at ? ` · finished ${recordTime(item.finished_at)}` : ""}${item.failure_class ? ` · failure ${item.failure_class}` : ""}`));
      }
      target.append(attempts);
    } else target.append(element("p", "No worker attempt is recorded for this assignment."));
    target.append(element("h4", "Persisted assignment events"));
    if (detail.events?.length) {
      const events = document.createElement("ol");
      events.className = "work-evidence-events";
      for (const event of detail.events) {
        const line = document.createElement("li");
        line.append(element("strong", event.event_type || "Event"), element("time", recordTime(event.recorded_at)));
        const refs = [event.event_id && `Event ID ${event.event_id}`, Number.isSafeInteger(event.seq) && `Sequence ${event.seq}`, event.causation_id && `Caused by ${event.causation_id}`].filter(Boolean);
        if (refs.length) line.append(element("small", refs.join(" · ")));
        events.append(line);
      }
      target.append(events);
    } else target.append(element("p", "No assignment events are present in the current history page."));
    if (detail.verifications?.length) {
      target.append(element("h4", "Verification evidence"));
      const list = document.createElement("ul");
      for (const item of detail.verifications) list.append(element("li", `${item.decision || "Decision unavailable"} · ${item.evidence_count ?? "Evidence count unavailable"} references · ${recordTime(item.recorded_at)} · verification ${item.verification_id || "ID unavailable"}`));
      target.append(list);
    }
  }
  function createDetails(record, assignment = null, objectives = []) {
    const model = record?.objective_id
      ? adapter.objectiveModel(record, assignment)
      : adapter.assignmentModel(record || {}, objectives);
    const details = element("details", undefined, "work-evidence-details");
    details.append(element("summary", "Operational status, deliverables & evidence"));
    const fields = document.createElement("dl");
    fields.className = "work-evidence-fields";
    appendField(fields, "Lifecycle stage", model.stage);
    appendField(fields, "Status", model.status);
    if (model.kind === "objective") {
      appendField(fields, "Operational status", model.operationalStatus);
      appendField(fields, "Status evidence source", model.operationalSource);
      appendField(fields, "Status evidence time", model.operationalAt ? recordTime(model.operationalAt) : null);
      appendField(fields, "Status source event", model.operationalEventType);
      appendField(fields, "Status event ID", model.operationalEventId);
      appendField(fields, "Canonical lifecycle", record.status);
      appendField(fields, "Objective revision", record.revision);
      if (Array.isArray(record.related_outputs) && record.related_outputs.length) {
        appendField(fields, "Recorded output count", record.related_outputs.length);
        appendField(fields, "Primary recorded output", record.related_outputs[0].name);
        appendField(fields, "Output verification", "Unverified in objective summary; assignment detail has per-output verification status.");
        appendField(fields, "Output publication", "Not assumed from objective metadata.");
      } else if (Array.isArray(record.related_outputs)) {
        appendField(fields, "Recorded output", record.status === "COMPLETED"
          ? "No output record supplied in the objective projection." : "No deliverable recorded in the objective projection.");
      } else {
        appendField(fields, "Recorded output", "Output metadata is unavailable in this authorized projection.");
      }
    }
    appendField(fields, "Blocker / waiting reason", model.blocker);
    appendField(fields, "Dependencies", model.dependencyAvailability);
    appendField(fields, "Assignment owner", model.owner);
    if (model.kind === "assignment" && model.linkedObjectiveIds?.length) {
      appendField(fields, "Related objective IDs", model.linkedObjectiveIds.join(", "));
    } else if (model.kind === "objective" && model.assignmentId) {
      appendField(fields, "Related work order", model.assignmentId);
    }
    appendField(fields, "Last meaningful progress", model.progressEvent);
    appendField(fields, "Progress recorded at", recordTime(model.progressAt));
    appendField(fields, "Time since progress", model.progressAge);
    appendField(fields, "Evidence event ID", model.evidenceEventId);
    appendField(fields, "Evidence sequence", model.evidenceEventSeq);
    if (model.kind === "objective") {
      appendField(fields, "Latest lifecycle event", record.latest_event?.event_type);
      appendField(fields, "Latest lifecycle event time", record.latest_event?.occurred_at ? recordTime(record.latest_event.occurred_at) : null);
      appendField(fields, "Rework decision", record.rework?.decision);
      appendField(fields, "Rework rationale", record.rework?.rationale);
      appendField(fields, "Rework decision time", record.rework?.occurred_at ? recordTime(record.rework.occurred_at) : null);
      appendField(fields, "Dispatch failures · last", Number(record.dispatch_failures) > 0
        ? `${record.dispatch_failures} · ${record.last_dispatch_failure_at ? recordTime(record.last_dispatch_failure_at) : "time unavailable"}` : "None recorded");
      appendField(fields, "Verification failures · last", Number(record.verification_failures) > 0
        ? `${record.verification_failures} · ${record.last_verification_failure_at ? recordTime(record.last_verification_failure_at) : "time unavailable"}` : "None recorded");
      appendField(fields, "Independent verification", record.verification?.decision
        ? `${record.verification.decision}${record.verification.summary ? ` · ${record.verification.summary}` : ""}` : "No verification decision recorded");
      for (const diagnostic of (Array.isArray(record.grounding_diagnostics) ? record.grounding_diagnostics : [])) {
        const summary = [diagnostic?.diagnostic?.reason_code, diagnostic?.diagnostic?.stage,
          diagnostic?.diagnostic?.responsible_component].filter(Boolean).join(" · ");
        appendField(fields, "Grounding diagnostic", summary || "Diagnostic details unavailable");
      }
    }
    details.append(fields);
    const links = element("div", undefined, "work-evidence-links");
    if (model.objectiveHref) safeLink(links, model.objectiveHref, `Open objective ${model.id} API`);
    if (model.assignmentHref) safeLink(links, model.assignmentHref, `Open assignment ${model.assignmentId} API and event history`);
    if (links.childNodes.length) details.append(links);
    const evidence = element("div", undefined, "work-evidence-assignment-detail");
    details.append(evidence);
    let requested = false;
    details.addEventListener("toggle", async () => {
      if (!details.open || requested || !model.assignmentId) return;
      requested = true;
      evidence.replaceChildren(element("p", "Loading assignment evidence…"));
      try {
        const response = await fetch(`/api/v1/assignments/${encodeURIComponent(model.assignmentId)}`, {
          method: "GET", credentials: "same-origin", cache: "no-store", headers: {Accept: "application/json"}
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(response.status === 401 ? "Authentication required" : response.status === 403 ? "Not authorized to read this assignment" : `Source unavailable (HTTP ${response.status})`);
        renderAssignmentDetail(evidence, result);
      } catch (error) {
        requested = false;
        evidence.replaceChildren(element("p", `Assignment evidence unavailable: ${error.message}. Retry by closing and reopening this panel.`));
      }
    });
    return details;
  }
  window.RiverviewV2WorkEvidence = Object.freeze({createDetails, renderAssignmentDetail});
})();
