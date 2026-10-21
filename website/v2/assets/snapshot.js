/*
Riverview~ Controlled Source
File: website/v2/assets/snapshot.js
Component: RIVERVIEW-V2-WORKSPACE-SHELL
Revision: 1.0.6
Purpose: Create a bounded V2 snapshot; same-origin dashboard mode uses shared archive API
Execution Model: Explicit browser click; standalone local preview or authenticated same-origin archive
Observability: Visible completion/error message and package manifest
Dependencies: Browser DOM, Web Crypto, Blob, TextEncoder, URL
Inputs/Outputs: V2 view, shared dashboard projections; GitHub archive and identical local ZIP
Authority: Same-origin authenticated Steward snapshot API in /v2 mode; standalone mode remains local-only
Changed: 2026-10-20 UTC | RV-WEB-V2-SNAPSHOT-001 | Mark source commit unavailable instead of guessing
Changed: 2026-10-20 UTC | RV-WEB-SNAPSHOT-V1-V2-INTEGRATION-001 | Add authenticated same-origin archive mode and retain local-only standalone preview
Changed: 2026-10-20 UTC | RV-WEB-SNAPSHOT-V1-V2-FINAL-001 | Preserve latest V2 communication diagnostics in both integrated and standalone snapshot manifests
Changed: 2026-10-21 UTC | RV-V2-SNAPSHOT-FIREFOX-DOWNLOAD-20261020 | Use an offscreen rendered download anchor and defer cleanup for Firefox
Contracts: docs/components/RIVERVIEW_V2_WORKSPACE_SHELL.md
Tests: tests/test_v2_workspace_shell.py, scripts/verify_v2_workspace_snapshot_chrome.py
History: Git and revision/backup manifest
*/
(() => {
  "use strict";
  const LIMIT_BYTES = 2 * 1024 * 1024;
  const CONTENT_LIMIT = 512 * 1024;
  const errors = [];
  const safePath = (value) => {
    try {
      const url = new URL(value, location.href);
      return url.origin === location.origin ? url.pathname.slice(0, 180) : "external-resource";
    } catch (_) { return "unavailable"; }
  };
  addEventListener("error", (event) => {
    const resource = event.target instanceof Element;
    errors.push({ at: new Date().toISOString(), kind: resource ? "resource-load-error" : "javascript-error",
      path: resource ? safePath(event.target.currentSrc || event.target.src || event.target.href || "") : safePath(event.filename || "") });
    if (errors.length > 30) errors.shift();
  }, true);
  addEventListener("unhandledrejection", () => {
    errors.push({ at: new Date().toISOString(), kind: "unhandled-promise-rejection", path: null });
    if (errors.length > 30) errors.shift();
  });

  const encoder = new TextEncoder();
  const bytes = (value) => encoder.encode(value);
  const concat = (parts) => {
    const out = new Uint8Array(parts.reduce((total, part) => total + part.length, 0));
    let offset = 0;
    for (const part of parts) { out.set(part, offset); offset += part.length; }
    return out;
  };
  const u16 = (value) => new Uint8Array([value & 255, value >>> 8 & 255]);
  const u32 = (value) => new Uint8Array([value & 255, value >>> 8 & 255, value >>> 16 & 255, value >>> 24 & 255]);
  const crcTable = (() => {
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) c = (c & 1) ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      table[n] = c >>> 0;
    }
    return table;
  })();
  const crc32 = (data) => {
    let crc = 0xffffffff;
    for (const byte of data) crc = crcTable[(crc ^ byte) & 255] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  };
  const sha256 = async (data) => {
    if (crypto.subtle) return [...new Uint8Array(await crypto.subtle.digest("SHA-256", data))]
      .map((byte) => byte.toString(16).padStart(2, "0")).join("");
    const constants = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    const input = new Uint8Array(data), bitLength = input.length * 8, paddedLength = Math.ceil((input.length + 9) / 64) * 64;
    const padded = new Uint8Array(paddedLength); padded.set(input); padded[input.length] = 0x80;
    const view = new DataView(padded.buffer); view.setUint32(paddedLength - 8, Math.floor(bitLength / 0x100000000)); view.setUint32(paddedLength - 4, bitLength >>> 0);
    const h = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19], w = new Uint32Array(64);
    const rotate = (x,n) => (x >>> n) | (x << (32 - n));
    for (let offset = 0; offset < paddedLength; offset += 64) {
      for (let i = 0; i < 16; i++) w[i] = view.getUint32(offset + i * 4);
      for (let i = 16; i < 64; i++) { const a = w[i-15], b = w[i-2], s0 = rotate(a,7)^rotate(a,18)^(a>>>3), s1 = rotate(b,17)^rotate(b,19)^(b>>>10); w[i] = (w[i-16]+s0+w[i-7]+s1)>>>0; }
      let [a,b,c,d,e,f,g,hh] = h;
      for (let i = 0; i < 64; i++) { const s1=rotate(e,6)^rotate(e,11)^rotate(e,25), ch=(e&f)^(~e&g), t1=(hh+s1+ch+constants[i]+w[i])>>>0, s0=rotate(a,2)^rotate(a,13)^rotate(a,22), maj=(a&b)^(a&c)^(b&c), t2=(s0+maj)>>>0; hh=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0; }
      [a,b,c,d,e,f,g,hh].forEach((v,i)=>{h[i]=(h[i]+v)>>>0;});
    }
    return h.map((word)=>word.toString(16).padStart(8,"0")).join("");
  };

  const makeZip = (members) => {
    let offset = 0;
    const local = [];
    const central = [];
    const now = new Date();
    const dosTime = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >>> 1);
    const dosDate = ((Math.max(1980, now.getFullYear()) - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
    for (const member of members) {
      const name = bytes(member.name);
      const data = member.data;
      const crc = crc32(data);
      const header = concat([u32(0x04034b50), u16(20), u16(0x0800), u16(0), u16(dosTime), u16(dosDate),
        u32(crc), u32(data.length), u32(data.length), u16(name.length), u16(0), name]);
      local.push(header, data);
      central.push(concat([u32(0x02014b50), u16(20), u16(20), u16(0x0800), u16(0), u16(dosTime), u16(dosDate),
        u32(crc), u32(data.length), u32(data.length), u16(name.length), u16(0), u16(0), u16(0), u16(0), u32(0), u32(offset), name]));
      offset += header.length + data.length;
    }
    const directory = concat(central);
    const end = concat([u32(0x06054b50), u16(0), u16(0), u16(members.length), u16(members.length),
      u32(directory.length), u32(offset), u16(0)]);
    const blob = new Blob([...local, directory, end], { type: "application/zip" });
    if (blob.size > LIMIT_BYTES) throw new Error("snapshot exceeds 2 MiB package limit");
    return blob;
  };

  const getState = () => {
    const selected = document.querySelector("#selected-resident");
    const residentName = selected?.querySelector("b")?.textContent?.trim() || "unavailable";
    const residentRole = selected?.querySelector("small")?.textContent?.trim() || "unavailable";
    const shell = document.querySelector(".app-shell");
    const view = document.querySelector("#primary-nav [aria-current='page']")?.dataset.view || "unknown";
    const viewText = (document.querySelector("#view-content")?.innerText || "").slice(0, CONTENT_LIMIT);
    return {
      schema: "riverview-v2-browser-snapshot/2",
      captured_at: new Date().toISOString(),
      product: "Riverview V2 workspace preview",
      build_version: "v2-workspace-shell/1.2",
      source_commit: null,
      source_commit_status: "not supplied by the preview server",
      route: location.pathname,
      current_view: view,
      selected_context: { resident_name: residentName, resident_role: residentRole, source: "rendered preview context" },
      appearance: { selected_theme: document.querySelector("#theme-select")?.value || "unknown", effective_theme: document.documentElement.dataset.theme || "unknown" },
      sidebars: { navigation: shell?.dataset.leftState || "unknown", context: shell?.dataset.rightState || "unknown" },
      browser: { user_agent: navigator.userAgent.slice(0, 240), language: navigator.language.slice(0, 32),
        viewport_css_px: { width: innerWidth, height: innerHeight }, device_pixel_ratio: Math.min(4, devicePixelRatio || 1) },
      data_connection: { mode: "fixture-only", live_backend_connected: false, details: "V2 preview reads local fixture data; no Riverview API is connected." },
      communication_diagnostics: {
        grace_chat: { status: "not_connected", handoff_available: Boolean(document.getElementById("grace-chat-handoff")), history_owner: "authenticated V1 Dashboard", messages_captured: false },
        comms5: { status: "unverified", outbound_count: null, inbound_count: null, inspectable_messages: false, correlation_ids: "unavailable", reason: "No authorized Comms5 event feed is connected to V2." }
      },
      rendered_view_text: viewText,
      browser_errors: errors.slice(-20),
      network_diagnostics: { status: "not instrumented", detail: "The fixture-only V2 preview makes no API requests. Resource timing is not a network-success/failure signal." },
      server_diagnostics: { status: "not available", detail: "The static preview exposes no server diagnostics endpoint." },
      omissions: ["No live Grace/CME/account data", "No conversation or message contents", "No server logs or runtime Git commit", "No pixel screenshot; browser DOM and rendered text are captured"],
      privacy: { credentials: "excluded", cookies: "excluded", storage: "excluded except the selected theme value above", "arbitrary page markup": "excluded" }
    };
  };
  const downloadZip=(zip,filename)=>{const url=URL.createObjectURL(zip),link=document.createElement("a");link.href=url;link.download=filename;link.setAttribute("aria-hidden","true");link.style.cssText="position:fixed;left:-10000px;top:0";document.body.append(link);try{link.click();}catch(error){link.remove();URL.revokeObjectURL(url);throw error;}setTimeout(()=>link.remove(),1000);setTimeout(()=>URL.revokeObjectURL(url),30000);return true;};
  const archive=async(blob,identity)=>{
    const csrf=document.cookie.split(";").map(x=>x.trim()).find(x=>x.startsWith("rv_account_csrf="))?.slice("rv_account_csrf=".length);if(!csrf)throw new Error("steward_account_session_required");
    const response=await fetch("/api/v1/snapshot/archive",{method:"POST",credentials:"same-origin",cache:"no-store",headers:{"Content-Type":"application/zip","Accept":"application/json","X-Riverview-CSRF":decodeURIComponent(csrf)},body:blob});
    const payload=await response.json().catch(()=>({}));if(!response.ok)throw new Error(payload.error||`archive_http_${response.status}`);
    const digest=await sha256(new Uint8Array(await blob.arrayBuffer()));if(payload.dashboard_version!==identity.dashboard_version||payload.capture_id!==identity.capture_id||payload.asset_name!==identity.asset_name||payload.archive_size_bytes!==blob.size||payload.archive_sha256!==digest)throw new Error("snapshot_archive_invalid_receipt");
    const url=new URL(payload.release_url);if(url.protocol!=="https:"||url.hostname!=="github.com")throw new Error("snapshot_archive_invalid_release_url");return payload;
  };
  const button = document.getElementById("snapshot-action");
  const status = document.getElementById("snapshot-status");
  button.disabled = false;
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "Preparing bounded V2 snapshot…";
    try {
      let state = getState(), payloads, identity = null, archived = null;
      if (location.pathname === "/v2/" || location.pathname === "/v2") {
        status.textContent = "Reading authenticated Riverview diagnostics…";
        const getJson = async (path) => { const response = await fetch(path, {credentials:"same-origin",cache:"no-store",headers:{Accept:"application/json"}}); if(!response.ok) throw new Error(`dashboard_http_${response.status}`); return response.json(); };
        const [dashboardStatus, operational] = await Promise.all([getJson("/api/v1/status"), getJson("/api/v1/snapshot")]);
        state = {...state, product:"Riverview V2 dashboard", source_commit:dashboardStatus.source?.source_commit||"unknown", source_commit_status:dashboardStatus.source?.source_commit?"reported by dashboard":"unavailable", data_connection:{mode:"authenticated-dashboard",live_backend_connected:true}};
        const capturedAt = new Date().toISOString(), captureId = crypto.randomUUID();
        payloads = [
          {name:"website/v2/workspace-state.json",data:bytes(JSON.stringify(state,null,2)+"\n")},
          {name:"website/v2/rendered-view.txt",data:bytes(`# Riverview V2 rendered view\nCaptured: ${capturedAt}\nRoute: ${state.route}\nView: ${state.current_view}\n\n${state.rendered_view_text}\n`)},
          {name:"diagnostics/dashboard-status.json",data:bytes(JSON.stringify(dashboardStatus,null,2)+"\n")},
          {name:"diagnostics/operational-snapshot.json",data:bytes(JSON.stringify(operational,null,2)+"\n")},
          {name:"README.txt",data:bytes("Riverview V2 diagnostic snapshot. Read manifest.json first. V2 interface data is separated from shared authenticated dashboard diagnostics.\n")}
        ];
        const files=[]; for(const item of payloads) files.push({path:item.name,size_bytes:item.data.length,sha256:await sha256(item.data)});
        const manifest={schema_version:"rv.website.diagnostic-snapshot.v1",dashboard_version:"v2",capture_id:captureId,captured_at:capturedAt,source_commit:state.source_commit,deployment_id:dashboardStatus.source?.deployment_id||"unconfigured",files,privacy:{authentication_material:"excluded",cookies:"excluded",authorization_headers:"excluded",passwords_and_form_values:"redacted",conversation_and_request_bodies:"excluded",account_detail_rows:"redacted"},capture:{v2_interface_diagnostics:"website/v2/workspace-state.json",shared_system_diagnostics:["diagnostics/dashboard-status.json","diagnostics/operational-snapshot.json"]}};
        payloads.push({name:"manifest.json",data:bytes(JSON.stringify(manifest,null,2)+"\n")});
        const zip=makeZip(payloads.map(item=>({name:item.name,data:item.data}))); identity={dashboard_version:"v2",capture_id:captureId,asset_name:`riverview-v2-${capturedAt.replace(/:/g,"-")}-${captureId}.zip`};
        try { archived=await archive(zip,identity); } catch(error) { console.warn("V2 snapshot archive failed",String(error?.message||"archive_failed")); }
        let local=false;try{local=downloadZip(zip,identity.asset_name);}catch(_){local=false;}
        if(archived){status.textContent=`V2 snapshot archived; local ZIP download ${local?"requested":"could not be started"}. `; const link=document.createElement("a");link.href=archived.release_url;link.target="_blank";link.rel="noopener noreferrer";link.textContent="Open private GitHub release";status.append(link);const copy=document.createElement("button");copy.type="button";copy.textContent="Copy GitHub Link";copy.addEventListener("click",async()=>{try{await navigator.clipboard.writeText(archived.release_url);copy.textContent="Copied";}catch(_){copy.textContent="Copy unavailable; use release link";}});status.append(document.createTextNode(" · "),copy);}
        else status.textContent=`GitHub archival failed; local ZIP download ${local?"requested":"unavailable"}.`;
        document.dispatchEvent(new CustomEvent("rvv2:snapshot-complete",{detail:{size:zip.size,filename:identity.asset_name,archived:Boolean(archived)}}));
      } else {
        const stateBytes = bytes(JSON.stringify(state, null, 2) + "\n");
        const viewBytes = bytes(`# Riverview V2 rendered view\nCaptured: ${state.captured_at}\nRoute: ${state.route}\nView: ${state.current_view}\n\n${state.rendered_view_text}\n`);
        const readmeBytes = bytes("Riverview V2 local preview snapshot\n\nThis package represents the active V2 browser view and its local fixture context. It does not contain live or server data. Read manifest.json first.\n");
        const members = [{ name: "workspace-state.json", data: stateBytes }, { name: "rendered-view.txt", data: viewBytes }, { name: "README.txt", data: readmeBytes }];
        const fileEntries = []; for (const payload of members) fileEntries.push({ name: payload.name, data: payload.data, size_bytes: payload.data.length, sha256: await sha256(payload.data) });
        const manifest = { schema: "riverview-v2-snapshot-manifest/1", created_at: state.captured_at, package_limit_bytes: LIMIT_BYTES, package_bytes_before_manifest: members.reduce((sum,item)=>sum+item.data.length,0), members:fileEntries, package_sha256:"Not embedded; compute SHA-256 over the downloaded ZIP to identify this complete package." };
        const zip=makeZip([...members,{name:"manifest.json",data:bytes(JSON.stringify(manifest,null,2)+"\n")}]); downloadZip(zip,`riverview-v2-snapshot-${state.captured_at.replace(/[-:]/g,"").replace(/\.\d{3}/,"")}.zip`);
        status.textContent=`V2 snapshot downloaded (${zip.size.toLocaleString()} bytes). No server upload was attempted.`;
        document.dispatchEvent(new CustomEvent("rvv2:snapshot-complete",{detail:{size:zip.size,filename:"standalone-v2-snapshot.zip",archived:false}}));
      }
    } catch (error) {
      status.textContent = "Snapshot could not be created. No data was uploaded.";
      document.dispatchEvent(new CustomEvent("rvv2:snapshot-error", { detail: { reason: String(error?.message || "snapshot_error").slice(0, 120) } }));
    } finally { button.disabled = false; }
  });
})();
