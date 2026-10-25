/* Riverview V2 notification preferences: same-origin, authenticated API only. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const status = $("notification-settings-status");
  const form = $("notification-settings-form");
  if (!form || !status) return;
  let loaded = false;

  function csrfToken() {
    const item = document.cookie.split(";").map((part) => part.trim())
      .find((part) => part.startsWith("rv_account_csrf="));
    if (!item) return "";
    try { return decodeURIComponent(item.slice("rv_account_csrf=".length)); } catch (_) { return ""; }
  }
  async function api(method, body) {
    const headers = {Accept: "application/json"};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (method !== "GET") {
      const csrf = csrfToken();
      if (csrf) headers["X-Riverview-CSRF"] = csrf;
    }
    const response = await fetch("/api/v1/notification-settings", {
      method, headers, credentials: "same-origin", cache: "no-store",
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `http_${response.status}`);
    return result;
  }
  function display(settings) {
    $("notification-settings-level").value = settings.level;
    $("notification-quiet-enabled").checked = settings.quiet_hours.enabled;
    $("notification-quiet-start").value = settings.quiet_hours.start;
    $("notification-quiet-end").value = settings.quiet_hours.end;
    $("notification-quiet-timezone").value = settings.quiet_hours.timezone;
    status.textContent = `Saved on server ${new Date(settings.updated_at).toLocaleString()}. Critical alerts bypass Paused and quiet hours.`;
    loaded = true;
  }
  async function refresh() {
    status.textContent = "Loading settings from Riverview…";
    try { display(await api("GET")); }
    catch (error) {
      loaded = false;
      status.textContent = error.message === "notification_settings_steward_required" ?
        "Sign in with an authorized Steward account to view these settings." :
        `Settings could not be loaded (${String(error.message).replace(/[^a-z0-9_.-]/gi, "_")}).`;
    }
  }
  window.RiverviewV2NotificationSettings = {render() { if (!loaded) refresh(); }};
  $("notification-settings-refresh").addEventListener("click", refresh);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!loaded) return;
    const button = $("notification-settings-save");
    button.disabled = true;
    status.textContent = "Saving settings…";
    try {
      display(await api("PUT", {level: $("notification-settings-level").value,
        quiet_hours: {enabled: $("notification-quiet-enabled").checked,
          start: $("notification-quiet-start").value, end: $("notification-quiet-end").value,
          timezone: $("notification-quiet-timezone").value.trim()}}));
    } catch (error) {
      status.textContent = `Settings were not confirmed (${String(error.message).replace(/[^a-z0-9_.-]/gi, "_")}). Refresh to check the server state.`;
    } finally { button.disabled = false; }
  });
})();
