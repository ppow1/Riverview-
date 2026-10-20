// Riverview~ controlled asset; component STEWARD-DASHBOARD.
// Revision: 1.1.23
// Purpose: Build one bounded, privacy-filtered offline website/workflow diagnostic ZIP.
// Execution Model: Request-driven browser export initiated by an explicit user action
// Observability: ZIP manifest records per-category bytes and raster omissions
// Dependencies: Authenticated dashboard read APIs; browser DOM, Canvas, Web Crypto, Blob
// Authority: Read-only API calls under the current browser session; never exports credentials or message bodies.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Preserve diagnostic records and vector maps when raster assets approach ZIP bound
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Add member-aware hard-bound errors and raster-only budget fallback
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Keep page/workflow SVG and canonical data while PNG previews are omitted
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Record component byte totals and explicit raster omission status in manifest
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Reserve manifest space and report partial capture to the user
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Enumerate skipped detail-tile paths after raster budget exhaustion
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020 | Cap raster derivatives separately and reserve space for mandatory structured members
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-BOUND-20261020-CATALOG-READINESS | Wait for the documentation catalog before measuring its full-page capture
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Archive generated ZIPs to private GitHub Releases and retain a local fallback.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-GITHUB-ARCHIVE-20261020 | Validate archive receipt ID, size, digest and release target before displaying it.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Verify the server receipt SHA-256 against the generated ZIP and hand the same Blob to browser download.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Retain archive/link and local retry actions across independent archive and browser-download failures.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Keep the visible retry anchor separate from the off-screen automatic-download trigger.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Fall back to the dashboard's safe clipboard-copy pattern when Clipboard API access is denied.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Preserve a confirmed archive if browser Blob URL creation itself fails.
// Changed: 2026-10-20 UTC | RV-WEBSITE-SNAPSHOT-ARCHIVE-DOWNLOAD-20261020 | Keep archive confirmation bound to the internal authenticated endpoint call; expose no injectable archive callback.
// Contracts: docs/components/STATUS_DASHBOARD.md; docs/components/STATUS_DASHBOARD_COOKBOOK.md
// Tests: scripts/verify_diagnostic_snapshot_browser.py
// Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Allowlist diagnostic fields and index unresolved workflow references
// Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Preserve safe timestamps and report unresolved jump targets without omission
// Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Include sanitized document navigation timing in bounded browser diagnostics
// Changed: 2026-10-16 UTC | RV-WEBSITE-SNAPSHOT-041 | Capture long registered pages completely and add readable page detail tiles.
// Changed: 2026-10-16 UTC | RV-WEBSITE-PR67-SNAPSHOT-CSP-FIX | Rasterize through CSP-allowed data URLs and preserve unavailable page outcomes.
(() => {
  "use strict";
  const LIMITS = Object.freeze({interactions:120, requests:200, errors:50, packageBytes:96*1024*1024, manifestReserveBytes:4*1024*1024, structuredReserveBytes:16*1024*1024, rasterVisualBytes:76*1024*1024,
    imagePixels:24*1024*1024, imageSide:8192, pageTile:1800, pageTileOverlap:80, pageMaxHeight:50000,
    graphTile:1800, graphTileOverlap:120});
  const KEY = "rv.dashboard.diagnostic-history.v1";
  const safeJson = (value, fallback) => { if(!value)return fallback;try { return JSON.parse(value); } catch (_) { return fallback; } };
  let historyPersistenceAvailable=true;const history=(()=>{try{return safeJson(sessionStorage.getItem(KEY),{interactions:[],requests:[],errors:[]});}catch(_){historyPersistenceAvailable=false;return {interactions:[],requests:[],errors:[]};}})();
  for (const name of ["interactions","requests","errors"]) if (!Array.isArray(history[name])) history[name]=[];
  history.truncation=history.truncation||{};for(const name of ["interactions","requests","errors"])history.truncation[name]=(Number(history.truncation[name])||0)+Math.max(0,history[name].length-LIMITS[name]);
  let capabilityRegistry=null,lastInteractionId=null,lastInteractionAt=0;
  document.addEventListener("DOMContentLoaded",()=>window.RiverviewSnapshotApi?.("/api/v1/capabilities").then(value=>{capabilityRegistry=value;}).catch(()=>{}),{once:true});
  let suppressInteractions=false, mutationCounter=0;
  new MutationObserver(()=>{mutationCounter++;}).observe(document.documentElement,{subtree:true,childList:true,attributes:true,characterData:true});
  const save = () => { for(const name of ["interactions","requests","errors"])if(history[name].length>LIMITS[name]){history.truncation[name]=(Number(history.truncation[name])||0)+history[name].length-LIMITS[name];history[name]=history[name].slice(-LIMITS[name]);}try{sessionStorage.setItem(KEY,JSON.stringify(history));}catch(_){historyPersistenceAvailable=false;} };
  const pageNow = () => location.hash.slice(1).split("?")[0] || document.querySelector(".view.active")?.id?.replace(/^view-/,"") || "unknown";
  const safePath = (value) => String(value||"").split("?")[0].replace(/\b[0-9a-f]{8}-[0-9a-f-]{27,}\b/gi,"{id}").replace(/\/resident\/conversations\/[^/]+/g,"/resident/conversations/{id}").replace(/\/responses\/[^/]+/g,"/responses/{id}").replace(/\/graphs\/rv%3A[^/?]+/gi,"/graphs/{graph_id}").replace(/\/(assignments|objectives|users|enrollments|notifications)\/[^/]+/g,"/$1/{id}").slice(0,180);
  const safeCode = (value) => {const candidate=String(value||"");return /^(?:http_[1-5][0-9]{2}|request_failed|stream_[a-z0-9_.-]{1,48}|snapshot_[a-z0-9_.-]{1,48}|javascript_error|unhandled_promise_rejection)$/i.test(candidate)?candidate:"ui_error";};
  const safeRequest = (request) => ({
    method:["GET","HEAD","POST","PUT","DELETE"].includes(String(request.method||"").toUpperCase())?String(request.method).toUpperCase():"OTHER",
    path:safePath(request.path),status:Number.isInteger(Number(request.status))?Number(request.status):null,
    duration_ms:Number.isFinite(Number(request.duration_ms))?Math.max(0,Math.min(86400000,Math.round(Number(request.duration_ms)))):null,
    request_id:/^[a-z0-9._:-]{1,128}$/i.test(String(request.request_id||""))?String(request.request_id):null,
    transport:request.transport==="sse"?"sse":"http",failure_code:request.failure_code?safeCode(request.failure_code):null,
    interaction_id:/^[0-9a-f-]{36}$/i.test(String(request.interaction_id||""))?String(request.interaction_id):Date.now()-lastInteractionAt<15000?lastInteractionId:null,
    at:Number.isNaN(Date.parse(request.at))?new Date().toISOString():new Date(request.at).toISOString()
  });
  const navigationTiming = () => performance.getEntriesByType("navigation").slice(-5).map(entry=>{
    const duration=(end,start)=>Math.max(0,Math.round((Number(end)||0)-(Number(start)||0)));
    return {at:new Date().toISOString(),type:/^(navigate|reload|back_forward|prerender)$/.test(entry.type)?entry.type:"other",
      redirect_count:Math.max(0,Math.min(10,Number(entry.redirectCount)||0)),duration_ms:duration(entry.duration,0),
      dns_ms:duration(entry.domainLookupEnd,entry.domainLookupStart),connect_ms:duration(entry.connectEnd,entry.connectStart),
      tls_ms:entry.secureConnectionStart?duration(entry.connectEnd,entry.secureConnectionStart):0,
      request_ms:duration(entry.responseStart,entry.requestStart),response_ms:duration(entry.responseEnd,entry.responseStart),
      dom_interactive_ms:duration(entry.domInteractive,0),dom_content_loaded_ms:duration(entry.domContentLoadedEventEnd,0),
      load_event_ms:duration(entry.loadEventEnd,0),transfer_size_bytes:Math.max(0,Number(entry.transferSize)||0)};
  });
  const controlId = (element) => element?.dataset?.capabilityId || element?.id || element?.dataset?.view && `navigation.${element.dataset.view}` || element?.dataset?.go && "navigation.shortcut" || `${pageNow()}.${element?.tagName?.toLowerCase()||"unknown-control"}`;
  document.addEventListener("click",(event)=>{
    if(suppressInteractions)return;
    const target=event.target.closest("button,a[href],input,select,textarea,summary,[role='button'],[role='link'],[onclick],[tabindex]");if(!target)return;
    const before=pageNow(), beforeMutation=mutationCounter, id=controlId(target), at=new Date().toISOString(),interactionId=crypto.randomUUID();lastInteractionId=interactionId;lastInteractionAt=Date.now();
    const declared=capabilityRegistry?capabilityId(target,capabilityRegistry):target.dataset.capabilityId || null,interaction={interaction_id:interactionId,at,control_id:id,registered_control_id:declared,page_before:before,
      state_before:{disabled:Boolean(target.disabled),expanded:target.getAttribute("aria-expanded"),pressed:target.getAttribute("aria-pressed")}};history.interactions.push(interaction);save();
    setTimeout(()=>{if(!history.interactions.includes(interaction))return;
      interaction.page_after=pageNow();interaction.result={dom_mutations_observed:mutationCounter>beforeMutation,
        active_view:document.querySelector(".view.active")?.id?.replace(/^view-/,"")||null,
        disabled_after:Boolean(target.disabled),expanded_after:target.getAttribute("aria-expanded"),
        visible_status_regions:[...document.querySelectorAll('[role="status"],[aria-live]')].filter(x=>x.offsetParent!==null).length};save();},900);
  },true);
  addEventListener("error",(event)=>{history.errors.push({at:new Date().toISOString(),kind:"javascript_error",source:safePath(event.filename),line:Number(event.lineno)||null});save();});
  addEventListener("unhandledrejection",()=>{history.errors.push({at:new Date().toISOString(),kind:"unhandled_promise_rejection"});save();});
  window.RiverviewDiagnostics={
    recordRequest(request){history.requests.push(safeRequest(request||{}));save();},
    recordError(kind,path){history.errors.push({at:new Date().toISOString(),kind:safeCode(kind),path:safePath(path)});save();},
    snapshot(){save();return {interactions:history.interactions.map(item=>({interaction_id:item.interaction_id,at:item.at,control_id:item.control_id,registered_control_id:item.registered_control_id,page_before:item.page_before,page_after:item.page_after,state_before:item.state_before,result:item.result})),requests:history.requests.map(item=>safeRequest(item)),errors:history.errors.map(item=>({at:item.at,kind:safeCode(item.kind),source:item.source?safePath(item.source):undefined,path:item.path?safePath(item.path):undefined,line:Number.isInteger(item.line)?item.line:undefined})),navigation_timing:navigationTiming(),truncation:{...history.truncation},retention_status:historyPersistenceAvailable?"session_storage_available":"memory_only"};},
    suppress(value){suppressInteractions=Boolean(value);}
  };

  const esc = (value) => String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const xml = esc;
  const bytes = (value) => new TextEncoder().encode(value);
  const crcTable = (()=>{const table=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=(c&1)?0xedb88320^(c>>>1):c>>>1;table[n]=c>>>0;}return table;})();
  const crc32 = (data) => {let c=0xffffffff;for(const byte of data)c=crcTable[(c^byte)&255]^(c>>>8);return (c^0xffffffff)>>>0;};
  const u16=(n)=>new Uint8Array([n&255,(n>>>8)&255]);
  const u32=(n)=>new Uint8Array([n&255,(n>>>8)&255,(n>>>16)&255,(n>>>24)&255]);
  const join=(parts)=>{const total=parts.reduce((n,p)=>n+p.length,0),out=new Uint8Array(total);let at=0;for(const p of parts){out.set(p,at);at+=p.length;}return out;};
  class ZipStore {
    constructor(){this.files=[];this.size=0;this.visualBytes=0;this.visualOmissions=[];}
    data(content){return typeof content==="string"?bytes(content):content instanceof Uint8Array?content:new Uint8Array(content);}
    add(name,content){const data=this.data(content),attempted=this.size+data.length;if(attempted>LIMITS.packageBytes)throw new Error(`snapshot_package_bound_exceeded:${name}:${attempted}/${LIMITS.packageBytes}`);this.size=attempted;this.files.push({name,data});}
    visualCapacityAvailable(){return this.visualBytes<LIMITS.rasterVisualBytes&&this.size<LIMITS.packageBytes-LIMITS.manifestReserveBytes;}
    addVisual(name,content){const data=this.data(content),attempted=this.size+data.length,rasterAttempted=this.visualBytes+data.length;if(rasterAttempted>LIMITS.rasterVisualBytes||attempted>LIMITS.packageBytes-LIMITS.manifestReserveBytes){this.visualOmissions.push({path:name,size_bytes:data.length,reason:"package_visual_budget_exceeded"});return false;}this.size=attempted;this.visualBytes=rasterAttempted;this.files.push({name,data});return true;}
    omitUnrenderedVisual(name){this.visualOmissions.push({path:name,size_bytes:null,reason:"package_visual_budget_exhausted"});}
    finish(){const local=[],central=[];let offset=0;const now=new Date(),dosTime=(now.getHours()<<11)|(now.getMinutes()<<5)|(now.getSeconds()>>1),dosDate=((Math.max(1980,now.getFullYear())-1980)<<9)|((now.getMonth()+1)<<5)|now.getDate();
      for(const file of this.files){const name=bytes(file.name),crc=crc32(file.data),head=join([u32(0x04034b50),u16(20),u16(0x0800),u16(0),u16(dosTime),u16(dosDate),u32(crc),u32(file.data.length),u32(file.data.length),u16(name.length),u16(0),name]);local.push(head,file.data);central.push(join([u32(0x02014b50),u16(20),u16(20),u16(0x0800),u16(0),u16(dosTime),u16(dosDate),u32(crc),u32(file.data.length),u32(file.data.length),u16(name.length),u16(0),u16(0),u16(0),u16(0),u32(0),u32(offset),name]));offset+=head.length+file.data.length;}
      const directory=join(central),end=join([u32(0x06054b50),u16(0),u16(0),u16(this.files.length),u16(this.files.length),u32(directory.length),u32(offset),u16(0)]);return new Blob([...local,directory,end],{type:"application/zip"});
    }
  }
  const sha256 = async (data) => [...new Uint8Array(await crypto.subtle.digest("SHA-256",data))].map(v=>v.toString(16).padStart(2,"0")).join("");
  const safeName = (id) => String(id).replace(/[^a-z0-9._-]+/gi,"_");
  const wrapText = (text,max=43) => {const out=[];let line="";for(const word of String(text||"").split(/\s+/)){if(line&&line.length+word.length+1>max){out.push(line);line=word;}else line+=(line?" ":"")+word;}if(line)out.push(line);return out;};
  function renderWorkflowSVG(graph, allGraphs, clip=null){
    const nodes=graph.nodes||[],edges=graph.edges||[],nodeById=new Map(nodes.map(n=>[n.id,n])),graphById=new Map(allGraphs.map(g=>[g.graph_id,g]));
    const boxW=310,boxH=94,gapX=390,gapY=155,margin=45,columns=Math.min(4,Math.max(1,Math.ceil(Math.sqrt(nodes.length))));
    const pos=new Map(nodes.map((n,i)=>[n.id,{x:margin+(i%columns)*(boxW+gapX),y:margin+Math.floor(i/columns)*(boxH+gapY)}]));
    const externals=[...new Set(edges.filter(e=>!nodeById.has(e.to)).map(e=>e.to))];
    const localRows=Math.ceil(nodes.length/columns),extX=margin+columns*(boxW+gapX)+80;
    externals.forEach((id,i)=>pos.set(id,{x:extX,y:margin+i*(boxH+48)}));
    const width=Math.max(800,margin*2+columns*boxW+(columns-1)*gapX+(externals.length?boxW+180:0));
    const height=Math.max(500,margin*2+Math.max(localRows,externals.length)*(boxH+gapY));
    const view=clip||{x:0,y:0,w:width,h:height};
    const title=`${graph.component_id} / ${graph.workflow_id} · graph ${graph.graph_revision}`;
    const out=[`<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${view.w}" height="${view.h}" viewBox="${view.x} ${view.y} ${view.w} ${view.h}" role="img" aria-labelledby="title desc">`,
      `<title id="title">${xml(title)}</title><desc id="desc">${nodes.length} canonical workflow nodes and ${edges.length} canonical edges. External references are shown as target references.</desc>`,
      `<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#7893a5"/></marker><style>text{font-family:system-ui,sans-serif;fill:#e2ebf0}.bg{fill:#0c141c}.edge{fill:none;stroke:#557184;stroke-width:2;marker-end:url(#arrow)}.edge-diagnostic_branch{stroke:#c4a355;stroke-dasharray:7 5}.edge-recovery_route{stroke:#63b7a0;stroke-dasharray:4 4}.edge-prerequisite,.edge-documentation{stroke:#687e8d;stroke-dasharray:2 7}.edge-jump{stroke:#67b9d3;stroke-dasharray:8 4}.edge-escalation{stroke:#c7827f;stroke-dasharray:4 4}.edge-label{font-size:11px;fill:#9bb0bd}.node{fill:#172430;stroke:#476477;stroke-width:2}.decision{fill:#342f20;stroke:#b89a4d}.failure,.escalation{fill:#352522;stroke:#b66d61}.recovery,.verification{fill:#1b302c;stroke:#5e9b82}.jump{fill:#1a2d39;stroke:#67b9d3;stroke-dasharray:7 4}.external{fill:#142333;stroke:#e0bd6b;stroke-dasharray:5 4}.type{font-size:11px;fill:#9bb0bd;font-family:ui-monospace,monospace}.label{font-size:14px;fill:#e2ebf0}.id{font-size:9px;fill:#9bb0bd;font-family:ui-monospace,monospace}</style></defs>`,
      `<rect class="bg" x="${view.x}" y="${view.y}" width="${view.w}" height="${view.h}"/>`,
      `<text x="${margin}" y="34" font-size="24" font-weight="bold">${xml(title)}</text>`];
    for(const edge of edges){const a=pos.get(edge.from),b=pos.get(edge.to);if(!a||!b)continue;const x1=a.x+boxW,y1=a.y+boxH/2,x2=b.x,y2=b.y+boxH/2,bend=Math.max(35,Math.abs(x2-x1)*.38),d=`M ${x1} ${y1} C ${x1+bend} ${y1}, ${x2-bend} ${y2}, ${x2} ${y2}`;
      const label=[edge.type,edge.label].filter(Boolean).join(" · "),edgeClass=String(edge.type||"unknown").replace(/[^a-z0-9_-]/gi,"-");out.push(`<path class="edge edge-${edgeClass}" data-edge-from="${xml(edge.from)}" data-edge-to="${xml(edge.to)}" data-edge-type="${xml(edge.type)}" d="${d}"/>`);if(label)out.push(`<text class="edge-label" x="${(x1+x2)/2}" y="${(y1+y2)/2-12}" text-anchor="middle">${xml(label)}</text>`);}
    for(const item of nodes){const p=pos.get(item.id),cls=["node",item.type].join(" "),lines=wrapText(item.label,32);const shape=item.type==="decision"?`<polygon class="${cls}" points="${p.x+boxW/2},${p.y} ${p.x+boxW},${p.y+boxH/2} ${p.x+boxW/2},${p.y+boxH} ${p.x},${p.y+boxH/2}"/>`:`<rect class="${cls}" x="${p.x}" y="${p.y}" width="${boxW}" height="${boxH}" rx="${item.type==="entry"||item.type==="exit"?34:12}"/>`;
      out.push(`<g data-node-id="${xml(item.id)}" data-node-type="${xml(item.type)}" data-node-revision="${xml(item.node_revision)}">${shape}<text class="type" x="${p.x+15}" y="${p.y+20}">${xml(item.type.toUpperCase())} · r${xml(item.node_revision)}</text>`);lines.forEach((line,i)=>out.push(`<text class="label" x="${p.x+15}" y="${p.y+46+i*18}">${xml(line)}</text>`));out.push(`<text class="id" x="${p.x+15}" y="${p.y+boxH-5}" font-size="9">${xml(item.id)}</text></g>`);}
    for(const id of externals){const p=pos.get(id),targetGraphId=id.substring(0,id.lastIndexOf(":")),targetGraph=graphById.get(targetGraphId),target=targetGraph?.nodes?.find(n=>n.id===id);out.push(`<g data-external-target-id="${xml(id)}"><rect class="node external" x="${p.x}" y="${p.y}" width="${boxW}" height="${boxH}" rx="10"/><text class="type" x="${p.x+16}" y="${p.y+24}">EXTERNAL WORKFLOW TARGET REFERENCE</text>`);wrapText(target?.label||"Target label not in registry",34).slice(0,2).forEach((line,i)=>out.push(`<text class="label" x="${p.x+16}" y="${p.y+56+i*22}">${xml(line)}</text>`));out.push(`<text class="id" x="${p.x+16}" y="${p.y+boxH-12}">${xml(id)}</text></g>`);}
    out.push(`</svg>`);return {svg:out.join(""),width,height,columns,boxW,boxH,gapX,gapY,margin};
  }
  async function svgPng(svg,width,height,scale){const image=new Image();image.src=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;await Promise.race([image.decode(),new Promise((_,reject)=>setTimeout(()=>reject(new Error("svg_decode_timeout")),12000))]);const canvas=document.createElement("canvas");canvas.width=Math.max(1,Math.floor(width*scale));canvas.height=Math.max(1,Math.floor(height*scale));if(canvas.width>LIMITS.imageSide||canvas.height>LIMITS.imageSide||canvas.width*canvas.height>LIMITS.imagePixels)throw new Error("image_bound_exceeded");const ctx=canvas.getContext("2d");ctx.fillStyle="#111a28";ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);const png=await new Promise((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(new Error("png_encode_failed")),"image/png"));return new Uint8Array(await png.arrayBuffer());}
  function redactClone(node){
    node.querySelectorAll("input,textarea,[contenteditable='true']").forEach(el=>{el.value="";el.textContent="";el.removeAttribute("value");el.setAttribute("data-snapshot-redacted","form value");});
    node.querySelectorAll("select").forEach(el=>{el.selectedIndex=-1;el.querySelectorAll("option").forEach(option=>option.removeAttribute("selected"));el.setAttribute("data-snapshot-redacted","form selection");});
    node.querySelectorAll(".conversation-timeline,.message-detail-copy,.message-content,#work-order-source").forEach(el=>{el.replaceChildren(document.createTextNode("[conversation/request content withheld]"));el.setAttribute("data-snapshot-redacted","private conversation content");});
    node.querySelectorAll("#view-account .account-row,#view-account #enrollment-list,#view-account #account-list").forEach(el=>{el.replaceChildren(document.createTextNode("[account details withheld]"));el.setAttribute("data-snapshot-redacted","account details");});
    node.querySelectorAll("#view-grace-chat [data-message-id],#view-grace-chat [data-message-details],#view-grace-chat [data-message-copy],#view-grace-chat [data-message-work-order]").forEach(el=>["data-message-id","data-message-details","data-message-copy","data-message-work-order"].forEach(name=>el.removeAttribute(name)));
    node.querySelectorAll("#view-account [data-account],#view-account [data-enroll],#view-account [data-approval-role]").forEach(el=>["data-account","data-enroll","data-approval-role"].forEach(name=>el.removeAttribute(name)));
    node.querySelectorAll("a[href]").forEach(el=>el.removeAttribute("href"));
    node.querySelectorAll("form").forEach(form=>{const inert=node.ownerDocument.createElement("div");inert.className=form.className;inert.id=form.id;while(form.firstChild)inert.append(form.firstChild);form.replaceWith(inert);});
    node.querySelectorAll("script,iframe,object,embed").forEach(el=>el.remove());
    node.querySelectorAll("img[src],source[src]").forEach(el=>{if(!el.getAttribute("src").startsWith("data:image/"))el.remove();});
    node.querySelectorAll("dialog").forEach(el=>el.remove());
    return node;
  }
  function capabilityId(element,registry){const matched=(registry.controls||[]).filter(control=>{try{return element.matches(control.selector);}catch(_){return false;}});return matched[0]?.id||element.dataset.capabilityId||null;}
  function pageControls(page,registry){const selector="button,a[href],input,select,textarea,summary,[role='button'],[role='link'],[onclick],[tabindex]",root=document.querySelector(".shell");return [...root.querySelectorAll(selector)].filter(el=>page.contains(el)||el.closest(".rail")).map(el=>({control_id:capabilityId(el,registry),element_id:el.id||null,tag:el.tagName.toLowerCase(),accessible_name:(el.getAttribute("aria-label")||el.innerText||el.getAttribute("title")||el.name||el.type||"control").trim().slice(0,120),state:el.disabled?"disabled":el.getClientRects().length&&!el.hidden&&!el.closest("[hidden]")?"rendered":"available",aria_expanded:el.getAttribute("aria-expanded"),aria_pressed:el.getAttribute("aria-pressed")}));}
  function pageVisualSvg(pageMeta,page,width,height,style,clone){
    const root=document.querySelector(".shell"),rootRect=root.getBoundingClientRect(),selector="button,a[href],input,select,textarea,summary,[role='button'],[role='link'],[onclick],[tabindex]",serialized=new XMLSerializer().serializeToString(clone),out=[`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}"><title>${esc(pageMeta.title)} full-page rendered capture</title><desc>Sanitized rendering of the complete page content with stable control outlines. Sensitive values are withheld.</desc><foreignObject x="0" y="0" width="${width}" height="${height}"><div xmlns="http://www.w3.org/1999/xhtml" style="width:${width}px;height:${height}px;overflow:hidden"><style>${esc(style)}</style>${serialized}</div></foreignObject>`];
    // The embedded SVG foreignObject is the faithful, full-page render. Draw
    // only control outlines as a lightweight stable-ID overlay; re-rendering
    // every DOM node here is both redundant and prohibitively slow on graphs.
    for(const el of root.querySelectorAll(selector)){
      if(!(page.contains(el)||el.closest(".rail")))continue;
      const rect=el.getBoundingClientRect(),x=Math.max(0,rect.left-rootRect.left),y=Math.max(0,rect.top-rootRect.top);
      if(rect.width<=0||rect.height<=0||x>width||y>height)continue;
      const w=Math.min(rect.width,width-x),h=Math.min(rect.height,height-y),id=capabilityId(el,window.__snapshotRegistry||{controls:[]})||el.id||"unregistered-control";
      out.push(`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="none" stroke="#e0bd6b" stroke-width="1.5" stroke-dasharray="4 3" data-control-id="${esc(id)}"/>`);
    }
    out.push("</svg>");return out.join("");
  }
  function cropPageSvg(svg,width,y,height){const total=Number(svg.match(/viewBox="0 0 \d+ (\d+)"/)?.[1]);return svg.replace(`width="${width}" height="${total}" viewBox="0 0 ${width} ${total}"`,`width="${width}" height="${height}" viewBox="0 ${y} ${width} ${height}"`);}
  function localSnapshotLink(blob,filename){const url=URL.createObjectURL(blob),anchor=document.createElement("a");anchor.href=url;anchor.download=filename;anchor.textContent="Download ZIP";anchor.setAttribute("aria-label","Download local diagnostic snapshot ZIP");anchor.dataset.snapshotDownload="true";setTimeout(()=>URL.revokeObjectURL(url),30*60*1000);return anchor;}
  function requestLocalDownload(blob,filename){let link=null,anchor=null;try{link=localSnapshotLink(blob,filename);anchor=document.createElement("a");anchor.href=link.href;anchor.download=filename;anchor.dataset.snapshotDownload="true";anchor.style.cssText="position:fixed;left:-10000px;top:0";document.body.append(anchor);anchor.click();return {started:true,link};}catch(error){return {started:false,error,link};}finally{if(anchor)setTimeout(()=>anchor.remove(),1000);}}
  async function copyArchiveLink(url,button){try{if(!navigator.clipboard?.writeText)throw new Error("clipboard_unavailable");await navigator.clipboard.writeText(url);button.textContent="Copied GitHub Link";}catch(_){const box=document.createElement("textarea");box.value=url;box.readOnly=true;box.setAttribute("aria-hidden","true");box.style.cssText="position:fixed;left:-10000px;top:0";document.body.append(box);box.select();const copied=document.execCommand("copy");box.remove();button.textContent=copied?"Copied GitHub Link":"Copy unavailable · use link";} }
  async function presentSnapshot(blob,filename,captureComplete=true){
    const toast=document.querySelector("#toast");let archived=null,archiveError=null;
    try{archived=await archiveSnapshot(blob);}catch(error){archiveError=error;}
    const local=requestLocalDownload(blob,filename);
    if(toast){
      toast.replaceChildren();
      if(archived){
        toast.append(document.createTextNode(`Snapshot archived permanently${captureComplete===false?" · partial; see manifest":""}; browser download ${local.started?"requested":"could not be started"} · `));
        const release=document.createElement("a");release.href=archived.release_url;release.target="_blank";release.rel="noopener noreferrer";release.textContent="Open private GitHub release";toast.append(release,document.createTextNode(" · "));
        const copy=document.createElement("button");copy.type="button";copy.className="snapshot-copy-link";copy.textContent="Copy GitHub Link";copy.addEventListener("click",()=>copyArchiveLink(archived.release_url,copy));toast.append(copy);
        if(local.link)toast.append(document.createTextNode(" · "),local.link);
        if(!local.started)toast.append(document.createTextNode(local.link?" · Use Download ZIP to retry; the verified archive is retained.":" · Browser download is unavailable; the verified archive is retained."));
      }else{
        const code=String(archiveError?.message||"archive_unavailable").slice(0,64);
        toast.append(document.createTextNode(`GitHub archival failed (${code}); local browser download ${local.started?"requested":"could not be started"}. `));
        if(local.link)toast.append(local.link);
        if(!local.started)toast.append(document.createTextNode(local.link?" The ZIP remains available from Download ZIP; retry locally or archive later.":" Browser download is unavailable in this session."));
      }
      toast.classList.add("show");
    }
    return {archived:Boolean(archived),archive_error:archiveError?String(archiveError.message||"archive_unavailable"):null,local_download_requested:local.started};
  }
  async function archiveSnapshot(blob){
    const csrf=document.cookie.split(";").map(part=>part.trim()).find(part=>part.startsWith("rv_account_csrf="))?.slice("rv_account_csrf=".length);
    if(!csrf)throw new Error("steward_account_session_required");
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5*60*1000),started=performance.now();let status=0,requestId=null;
    try{
      const response=await fetch("/api/v1/snapshot/archive",{method:"POST",headers:{"Content-Type":"application/zip","Accept":"application/json","X-Riverview-CSRF":decodeURIComponent(csrf)},body:blob,credentials:"same-origin",cache:"no-store",signal:controller.signal});
      status=response.status;requestId=response.headers.get("X-Request-ID");const payload=await response.json().catch(()=>({}));
      window.RiverviewDiagnostics?.recordRequest({method:"POST",path:"/api/v1/snapshot/archive",status,duration_ms:Math.round(performance.now()-started),request_id:requestId});
      if(!response.ok)throw new Error(payload.error||`http_${status}`);
      const snapshotId=payload.snapshot_id,localDigest=await sha256(new Uint8Array(await blob.arrayBuffer()));if(!/^rvdiag-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{32}$/.test(snapshotId)||payload.asset_name!==`${snapshotId}.zip`||payload.archive_size_bytes!==blob.size||! /^[0-9a-f]{64}$/.test(payload.archive_sha256)||payload.archive_sha256!==localDigest)throw new Error("snapshot_archive_invalid_receipt");
      const url=new URL(payload.release_url);if(url.protocol!=="https:"||url.hostname!=="github.com"||!url.pathname.endsWith(`/releases/tag/${snapshotId}`))throw new Error("snapshot_archive_invalid_release_url");
      return payload;
    }catch(error){
      if(!status)window.RiverviewDiagnostics?.recordRequest({method:"POST",path:"/api/v1/snapshot/archive",status:0,duration_ms:Math.round(performance.now()-started),failure_code:String(error.message||"snapshot_archive_failed").replace(/[^a-z0-9_.-]/gi,"_").slice(0,64)});
      throw error;
    }finally{clearTimeout(timer);}
  }
  async function capturePage(pageMeta,registry,css){

    const nav=document.querySelector(pageMeta.navigation_selector);if(!nav||nav.hidden||nav.disabled||!nav.getClientRects().length)return {page_id:pageMeta.id,status:"inaccessible_by_current_permissions",omission:"registered navigation control is not available to this session",omissions:[]};
    if(!nav.matches("[data-view='"+CSS.escape(pageMeta.id)+"']")||document.querySelector(pageMeta.selector)?.hidden)nav.click();
    if(pageMeta.id==="documentation"){
      const catalogStarted=performance.now();let catalogReady=false;
      while(performance.now()-catalogStarted<15000){
        const state=document.querySelector("#documentation-catalog-state")?.textContent?.trim()||"";
        const cards=document.querySelectorAll("#documentation-catalog .documentation-catalog-card").length;
        if(/^\d+ of \d+ registered workflows/.test(state)&&cards>0){catalogReady=true;break;}
        if(state.startsWith("Workflow catalog unavailable ("))break;
        await new Promise(resolve=>setTimeout(resolve,50));
      }
      if(!catalogReady)return {page_id:pageMeta.id,status:"not_observed",omission:"documentation catalog did not finish loading before the bounded 15-second readiness deadline",omissions:[]};
    }
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    const waitStarted=performance.now();let quietSince=waitStarted,lastMutation=mutationCounter;while(performance.now()-quietSince<130&&performance.now()-waitStarted<900){await new Promise(resolve=>setTimeout(resolve,35));if(mutationCounter!==lastMutation){lastMutation=mutationCounter;quietSince=performance.now();}}
    const current=document.querySelector(pageMeta.selector);if(!current||current.hidden)return {page_id:pageMeta.id,status:"not_observed",omission:"page did not become visible after authorized navigation",omissions:[]};
    const rawClone=document.querySelector(".shell").cloneNode(true),omissions=[];const externalMedia=[...rawClone.querySelectorAll("img[src],source[src],iframe,object,embed")].filter(el=>!el.matches("img[src^='data:image/'],source[src^='data:image/']"));if(externalMedia.length)omissions.push({code:"offline_external_media_omitted",count:externalMedia.length});const clone=redactClone(rawClone);
    clone.querySelectorAll(".view").forEach(view=>{const active=view.id===current.id;view.hidden=!active;view.classList.toggle("active",active);});
    clone.querySelectorAll(".nav-item").forEach(item=>item.classList.toggle("selected",item.dataset.view===pageMeta.id));
    clone.querySelectorAll("#toast").forEach(el=>el.remove());
    clone.querySelectorAll("[data-stream-response]").forEach(el=>el.remove());
    const controls=pageControls(current,registry),width=Math.max(360,Math.min(window.innerWidth,1920));
    const scrolls=[...current.querySelectorAll("*")].filter(el=>el.scrollHeight>el.clientHeight+2&&/auto|scroll/.test(getComputedStyle(el).overflowY));const savedStyles=scrolls.map(el=>({el,style:el.getAttribute("style")}));for(const {el} of savedStyles){el.style.overflow="visible";el.style.height="auto";el.style.maxHeight="none";}
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    const root=document.querySelector(".shell"),rootRect=root.getBoundingClientRect(),contentBottom=Math.max(root.scrollHeight,...[...root.querySelectorAll("*")].map(el=>el.getBoundingClientRect().bottom-rootRect.top)),height=Math.max(760,Math.min(Math.ceil(contentBottom),LIMITS.pageMaxHeight));
    const unsafeCssRefs=[...css.matchAll(/url\(([^)]*)\)/gi)].filter(match=>!/^\s*['"]?(?:data:|#)/i.test(match[1])).length;
    const safeCss=css.replace(/@import\s+(?:url\()?[^;]+;?/gi,"").replace(/url\((?!\s*['"]?(?:data:|#))[^)]*\)/gi,"none");
    if(unsafeCssRefs)omissions.push({code:"external_stylesheet_resource_omitted",count:unsafeCssRefs});
    const style=`${safeCss}\nhtml,body{width:${width}px;min-height:${height}px;height:auto;overflow:visible}.shell{width:${width}px;min-height:${height}px;height:auto}.graph-canvas,.conversation-timeline,.readable-doc pre,.doc-table-wrap{height:auto!important;max-height:none!important;overflow:visible!important}.view[hidden]{display:none!important}.snapshot-banner{padding:12px 22px;background:#27364b;color:#e8eef8;font:14px Arial,sans-serif}`;
    const markup=`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=${width}"><title>${esc(pageMeta.title)} · Riverview diagnostic capture</title><style>${style}</style></head><body><div class="snapshot-banner">Offline diagnostic capture · page ${esc(pageMeta.id)} · captured ${esc(new Date().toISOString())} · user-visible values redacted by policy</div>${clone.outerHTML}</body></html>`;
    let svg;try{svg=pageVisualSvg(pageMeta,current,width,height,style,clone);}finally{for(const saved of savedStyles){if(saved.style===null)saved.el.removeAttribute("style");else saved.el.setAttribute("style",saved.style);}}
    return {page_id:pageMeta.id,title:pageMeta.title,status:"captured",width_css_px:width,height_css_px:height,content_extent_px:Math.ceil(contentBottom),captured_scroll_height_px:height,capture_truncated:contentBottom>LIMITS.pageMaxHeight,omissions,controls,
      representations:{json:`website/pages/${pageMeta.id}.json`,html:`website/pages/${pageMeta.id}.html`,svg:`website/pages/${pageMeta.id}.svg`,png:`website/pages/${pageMeta.id}.png`,detail_tiles:[]},_html:markup,_svg:svg,_png_scale:Math.min(1.5,Math.sqrt(LIMITS.imagePixels/(width*height)),LIMITS.imageSide/width,LIMITS.imageSide/height)};
  }
  function renderCapabilityCoverage(registry,pageOutcomes){
    const selector="button,a[href],input,select,textarea,summary,[role='button'],[role='link'],[onclick],[tabindex]",elements=[...document.querySelectorAll(selector)],captured=(pageOutcomes||[]).filter(x=>x.status==="captured"),observed=[];
    for(const page of captured)for(const control of page.controls||[])observed.push({...control,page_id:page.page_id});
    const registered=(registry.controls||[]).map(control=>{const matched=observed.filter(item=>item.control_id===control.id),element=elements.find(item=>{try{return item.matches(control.selector);}catch(_){return false;}}),available=Boolean(element&&!element.disabled&&!element.closest("[hidden]")&&element.getClientRects().length),status=matched.some(x=>x.state==="rendered")?"rendered":matched.length&&matched.every(x=>x.state==="disabled")?"disabled":matched.length?"available":available?"not_observed":"unavailable";return {id:control.id,registered:true,available,rendered_count:matched.filter(x=>x.state==="rendered").length,available_count:matched.filter(x=>x.state==="available").length,disabled_count:matched.filter(x=>x.state==="disabled").length,observed_page_ids:[...new Set(matched.map(x=>x.page_id))],status};});
    const uncovered=observed.filter(item=>!item.control_id).map(item=>({element_id:item.element_id,tag:item.tag,page_id:item.page_id,accessible_name:item.accessible_name,status:item.state}));
    return {registered_controls:registered,uncovered_rendered_controls:uncovered,counts:{registered:registered.length,rendered:registered.filter(x=>x.status==="rendered").length,disabled:registered.filter(x=>x.status==="disabled").length,available:registered.filter(x=>x.status==="available").length,available_not_observed:registered.filter(x=>x.status==="not_observed").length,unavailable:registered.filter(x=>x.status==="unavailable").length,uncovered:uncovered.length}};
  }
  async function download(api){
    const button=document.querySelector("#snapshot");if(button)button.disabled=true;const started=Date.now();
    try{
      const originalView=pageNow(),registry=await api("/api/v1/capabilities"),snapshot=await api("/api/v1/snapshot"),index=await api("/api/v1/snapshot/workflow-index");
      window.__snapshotRegistry=registry;
      if(registry.schema_version!=="rv.website.capabilities.v1"||!Array.isArray(registry.pages)||!Array.isArray(registry.controls))throw new Error("capability_registry_contract_invalid");
      const histories=window.RiverviewDiagnostics.snapshot(),css=await (await fetch("/assets/app.css",{credentials:"same-origin",cache:"no-store"})).text();
      const graphs=[],graphErrors=[...(index.errors||[])];
      if(index.status!=="available")graphErrors.push({code:"workflow_inventory_incomplete",status:index.status});
      for(const summary of index.items||[]){try{const result=await api(`/api/v1/graphs/${encodeURIComponent(summary.graph_id)}`);const graph={...result.graph},runtimeStatus=graph.execution_position||{status:"unavailable",reason:"The authenticated graph endpoint did not provide an execution-position projection."};delete graph.execution_position;graphs.push({summary,graph,runtimeStatus});}catch(error){graphErrors.push({graph_id:summary.graph_id,code:String(error.message||"graph_unavailable").slice(0,64)});}}
      const pages=[],pageOutcomes=[];RiverviewDiagnostics.suppress(true);
      for(const pageMeta of registry.pages){try{const cap=await capturePage(pageMeta,registry,css);if(cap.status!=="captured"){pageOutcomes.push({page_id:pageMeta.id,status:cap.status||"unavailable",omission:String(cap.omission||"page was not observable in the current session").slice(0,160)});continue;}const omissions=Array.isArray(cap.omissions)?cap.omissions:[],{_html,_svg,_png_scale,...record}=cap;record.omissions=omissions;record.visual_status=cap.capture_truncated||omissions.length?"incomplete":"pending";if(cap.capture_truncated)record.visual_omission=`rendered content exceeded the ${LIMITS.pageMaxHeight} CSS-pixel capture bound`;else if(omissions.length)record.visual_omission=omissions.map(x=>x.code).join(",");cap.omissions=omissions;cap._record=record;pageOutcomes.push(record);pages.push(cap);}catch(error){pageOutcomes.push({page_id:pageMeta.id,status:"failed",omission:String(error.message||"page_capture_failed").slice(0,100)});}}
      const originalPage=registry.pages.find(page=>page.id===originalView),originalNav=originalPage&&document.querySelector(originalPage.navigation_selector);if(originalNav&&!originalNav.hidden)originalNav.click();RiverviewDiagnostics.suppress(false);const coverage=renderCapabilityCoverage(registry,pageOutcomes);
      const zip=new ZipStore(),outcomes=[],relationships=[];zip.add("website/capabilities.json",JSON.stringify(registry,null,2));zip.add("diagnostics/operational-snapshot.json",JSON.stringify(snapshot,null,2));zip.add("diagnostics/browser-history.json",JSON.stringify({schema_version:"rv.website.browser-diagnostics.v1",retention:LIMITS,interactions:histories.interactions,requests:histories.requests,errors:histories.errors,navigation_timing:histories.navigation_timing,truncation:histories.truncation,retention_status:historyPersistenceAvailable?"session_storage_available":"memory_only",redaction:{headers:false,bodies:false,cookies:false,credentials:false,conversation_content:false}},null,2));zip.add("diagnostics/control-coverage.json",JSON.stringify(coverage,null,2));
      for(const page of pages){const pageRecord=pageOutcomes.find(x=>x.page_id===page.page_id);zip.add(page.representations.html,page._html);zip.add(page.representations.svg,page._svg);let pngAdded=false,visualIncomplete=false;try{if(zip.visualCapacityAvailable()){pngAdded=zip.addVisual(page.representations.png,await svgPng(page._svg,page.width_css_px,page.height_css_px,page._png_scale));}else zip.omitUnrenderedVisual(page.representations.png);if(!pngAdded)visualIncomplete=true;page.representations.png=pngAdded?page.representations.png:null;if(!pngAdded&&page.height_css_px>LIMITS.pageTile){const step=LIMITS.pageTile-LIMITS.pageTileOverlap;for(let y=0,row=1;y<page.height_css_px;y+=step,row++)zip.omitUnrenderedVisual(`website/pages/${page.page_id}/details/tile-${String(row).padStart(3,"0")}.png`);}if(pngAdded&&page.height_css_px>LIMITS.pageTile){const step=LIMITS.pageTile-LIMITS.pageTileOverlap;let stopTiles=false;for(let y=0,row=1;y<page.height_css_px;y+=step,row++){const height=Math.min(LIMITS.pageTile,page.height_css_px-y),tileName=`website/pages/${page.page_id}/details/tile-${String(row).padStart(3,"0")}.png`;if(stopTiles){zip.omitUnrenderedVisual(tileName);continue;}if(!zip.visualCapacityAvailable()){zip.omitUnrenderedVisual(tileName);visualIncomplete=true;stopTiles=true;continue;}const tileSvg=cropPageSvg(page._svg,page.width_css_px,y,height),tile=await svgPng(tileSvg,page.width_css_px,height,Math.min(1.5,LIMITS.imageSide/page.width_css_px,Math.sqrt(LIMITS.imagePixels/(page.width_css_px*height))));if(!zip.addVisual(tileName,tile)){visualIncomplete=true;stopTiles=true;continue;}page.representations.detail_tiles.push(tileName);}}if(!page.capture_truncated&&!page.omissions.length&&!visualIncomplete)pageRecord.visual_status="complete";else if(visualIncomplete){pageRecord.visual_status="incomplete";pageRecord.visual_omission="package_visual_budget_exceeded; sanitized HTML, SVG and page JSON retained";}pageRecord.detail_tiles=[...page.representations.detail_tiles];}catch(error){pageRecord.visual_status="incomplete";pageRecord.visual_omission=String(error.message||"page_png_failed").slice(0,120);}zip.add(page.representations.json,JSON.stringify({schema_version:"rv.website.page-capture.v1",captured_at:new Date().toISOString(),page_id:page.page_id,title:page.title,status:page.status,viewport:{width_css_px:page.width_css_px,height_css_px:page.height_css_px},content_extent_px:page.content_extent_px,capture_truncated:page.capture_truncated,omissions:page.omissions,captured_scroll_height_px:page.captured_scroll_height_px,controls:page.controls,representations:page.representations,visual_status:pageRecord.visual_status,visual_omission:pageRecord.visual_omission||null},null,2));}
      const graphMap=graphs.map(x=>x.graph),knownNodeIds=new Set(graphMap.flatMap(g=>(g.nodes||[]).map(n=>n.id))),incoming=new Map();for(const {graph} of graphs)for(const node of graph.nodes||[])if(node.type==="jump"&&node.jump_target_id){const targetGraphId=node.jump_target_id.substring(0,node.jump_target_id.lastIndexOf(":"));(incoming.get(targetGraphId)||incoming.set(targetGraphId,[]).get(targetGraphId)).push({source_graph_id:graph.graph_id,source_node_id:node.id,target_node_id:node.jump_target_id,resolved:knownNodeIds.has(node.jump_target_id)});}
      const indexItems=[];
      for(const {summary,graph,runtimeStatus} of graphs){const fileStem=safeName(graph.graph_id),base=`workflows/${fileStem}`,rendered=renderWorkflowSVG(graph,graphMap);const jsonName=`${base}.json`,statusName=`${base}.status.json`,svgName=`${base}.svg`,pngName=`${base}.png`;zip.add(jsonName,JSON.stringify(graph,null,2));zip.add(statusName,JSON.stringify({schema_version:"rv.website.workflow-runtime-status.v1",graph_id:graph.graph_id,observed_at:new Date().toISOString(),source:`GET /api/v1/graphs/${encodeURIComponent(graph.graph_id)} response.execution_position`,projection:runtimeStatus},null,2));zip.add(svgName,rendered.svg);let pngStatus="complete",pngAdded=false,tiles=[];
        try{const scale=Math.min(2,LIMITS.imageSide/rendered.width,LIMITS.imageSide/rendered.height,Math.sqrt(LIMITS.imagePixels/(rendered.width*rendered.height)));if(zip.visualCapacityAvailable())pngAdded=zip.addVisual(pngName,await svgPng(rendered.svg,rendered.width,rendered.height,scale));else zip.omitUnrenderedVisual(pngName);if(!pngAdded)pngStatus="omitted_package_visual_budget";
          if(pngAdded&&(scale<1.5||Math.max(rendered.width,rendered.height)>3600)){const step=LIMITS.graphTile-LIMITS.graphTileOverlap;let row=0;let stopTiles=false;for(let y=0;y<rendered.height;y+=step,row++){let col=0;for(let x=0;x<rendered.width;x+=step,col++){const clip={x:Math.max(0,x-(x?LIMITS.graphTileOverlap/2:0)),y:Math.max(0,y-(y?LIMITS.graphTileOverlap/2:0)),w:Math.min(LIMITS.graphTile,rendered.width-Math.max(0,x-(x?LIMITS.graphTileOverlap/2:0))),h:Math.min(LIMITS.graphTile,rendered.height-Math.max(0,y-(y?LIMITS.graphTileOverlap/2:0)))};const tileSvg=renderWorkflowSVG(graph,graphMap,clip).svg,name=`${base}/details/tile-${String(row+1).padStart(2,"0")}-${String(col+1).padStart(2,"0")}.png`;if(stopTiles){zip.omitUnrenderedVisual(name);continue;}if(!zip.visualCapacityAvailable()){zip.omitUnrenderedVisual(name);pngStatus="incomplete_package_visual_budget";stopTiles=true;continue;}const tile=await svgPng(tileSvg,clip.w,clip.h,2);if(!zip.addVisual(name,tile)){pngStatus="incomplete_package_visual_budget";stopTiles=true;continue;}tiles.push(name);}}if(!pngAdded&&(scale<1.5||Math.max(rendered.width,rendered.height)>3600)){const step=LIMITS.graphTile-LIMITS.graphTileOverlap;for(let y=0,row=0;y<rendered.height;y+=step,row++)for(let x=0,col=0;x<rendered.width;x+=step,col++)zip.omitUnrenderedVisual(`${base}/details/tile-${String(row+1).padStart(2,"0")}-${String(col+1).padStart(2,"0")}.png`);}}
        }catch(error){pngStatus="failed";graphErrors.push({graph_id:graph.graph_id,code:String(error.message||"workflow_png_failed").slice(0,120)});}
        const jumps=(graph.nodes||[]).filter(n=>n.type==="jump").map(n=>({source_node_id:n.id,target_node_id:n.jump_target_id,target_graph_id:n.jump_target_id?.substring(0,n.jump_target_id.lastIndexOf(":"))||null,resolved:knownNodeIds.has(n.jump_target_id)}));for(const jump of jumps)relationships.push({source_graph_id:graph.graph_id,...jump});
        const localNodeIds=new Set((graph.nodes||[]).map(n=>n.id)),unresolvedReferences=[];for(const node of graph.nodes||[])if(node.type==="jump"&&(!node.jump_target_id||!knownNodeIds.has(node.jump_target_id)))unresolvedReferences.push({kind:"jump_target",source_node_id:node.id,target_id:node.jump_target_id||null});for(const edge of graph.edges||[]){if(!localNodeIds.has(edge.from))unresolvedReferences.push({kind:"edge_source",source_node_id:edge.from,target_id:edge.from});if(!knownNodeIds.has(edge.to))unresolvedReferences.push({kind:"edge_target",source_node_id:edge.from,target_id:edge.to});}
        const outcome={graph_id:graph.graph_id,component_id:graph.component_id,workflow_id:graph.workflow_id,graph_revision:graph.graph_revision,source_file:summary.source_file,node_count:graph.nodes?.length||0,edge_count:graph.edges?.length||0,json:jsonName,status:statusName,runtime_status:runtimeStatus.status,svg:svgName,png:pngAdded?pngName:null,png_status:pngStatus,detail_tiles:tiles,incoming_jumps:incoming.get(graph.graph_id)||[],outbound_jumps:jumps,unresolved_references:unresolvedReferences};outcomes.push(outcome);indexItems.push(outcome);
      }
      const expectedWorkflows=index.items||[],workflowRecords=expectedWorkflows.map(summary=>{
        const exported=indexItems.find(item=>item.graph_id===summary.graph_id);
        if(exported)return {...exported,export_status:exported.png_status==="complete"?"complete":"incomplete"};
        const failure=graphErrors.find(item=>item.graph_id===summary.graph_id)||{code:"workflow_export_unavailable"};
        return {graph_id:summary.graph_id,component_id:summary.component_id,workflow_id:summary.workflow_id,graph_revision:summary.graph_revision,source_file:summary.source_file,node_count:summary.node_count,edge_count:summary.edge_count,export_status:"failed",error:failure.code};
      });
      const graphIndex={schema_version:"rv.website.workflow-index.v1",source:registry.workflow_surfaces.authoritative_repository_path,
        inventory_count:index.inventory_count||expectedWorkflows.length,exported_count:indexItems.length,
        node_count:indexItems.reduce((n,x)=>n+x.node_count,0),edge_count:indexItems.reduce((n,x)=>n+x.edge_count,0),
        expected_node_count:expectedWorkflows.reduce((n,x)=>n+(Number(x.node_count)||0),0),
        expected_edge_count:expectedWorkflows.reduce((n,x)=>n+(Number(x.edge_count)||0),0),
        exported_node_count:indexItems.reduce((n,x)=>n+x.node_count,0),exported_edge_count:indexItems.reduce((n,x)=>n+x.edge_count,0),
        workflows:workflowRecords,cross_workflow_relationships:relationships,
        unresolved_references:indexItems.flatMap(item=>item.unresolved_references.map(reference=>({graph_id:item.graph_id,...reference}))),
        unresolved_reference_count:indexItems.reduce((n,item)=>n+item.unresolved_references.length,0)};
      zip.add("workflows/workflow-index.json",JSON.stringify(graphIndex,null,2));
      for(const file of zip.files)if(file.name.startsWith("website/pages/")&&file.name.endsWith(".html")){} // Keep ordering deterministic; manifest is added last.
      const status=snapshot.projection||{},capturedPages=pageOutcomes.filter(x=>x.status==="captured"),pageVisualsComplete=capturedPages.length===registry.pages.length&&capturedPages.every(x=>x.visual_status==="complete"),workflowsComplete=workflowRecords.length===graphIndex.inventory_count&&workflowRecords.every(x=>x.export_status==="complete");
      const omissions=[...pageOutcomes.filter(x=>x.status!=="captured").map(x=>({page_id:x.page_id,reason:x.omission||x.status})),...pageOutcomes.filter(x=>x.visual_status==="incomplete").map(x=>({page_id:x.page_id,reason:x.visual_omission})),...graphErrors,...zip.visualOmissions.map(item=>({kind:"raster_visual",...item}))];
      const componentBytes={};for(const file of zip.files){const page=file.name.startsWith("website/pages/"),workflow=file.name.startsWith("workflows/"),category=page?(file.name.endsWith(".png")||file.name.includes("/details/")?"page_visuals":"page_records"):workflow?(file.name.endsWith(".png")||file.name.endsWith(".svg")||file.name.includes("/details/")?"workflow_visuals":"workflow_records"):file.name.startsWith("diagnostics/")?"diagnostics":file.name==="website/capabilities.json"?"capability_registry":"other";componentBytes[category]=(componentBytes[category]||0)+file.data.length;}
      const manifest={schema_version:"rv.website.diagnostic-snapshot.v1",capture_id:crypto.randomUUID(),captured_at:new Date().toISOString(),source_commit:status.source?.source_commit||"unknown",deployment_id:status.source?.deployment_id||"unconfigured",capability_registry:{id:registry.registry_id,revision:registry.revision,schema_version:registry.schema_version},schema_versions:{snapshot:"rv.website.diagnostic-snapshot.v1",capability_registry:registry.schema_version,page_capture:"rv.website.page-capture.v1",browser_diagnostics:"rv.website.browser-diagnostics.v1",workflow_index:"rv.website.workflow-index.v1",workflow_status:"rv.website.workflow-runtime-status.v1"},capture_duration_ms:Date.now()-started,package_bounds:{max_uncompressed_bytes:LIMITS.packageBytes,manifest_reserve_bytes:LIMITS.manifestReserveBytes,structured_reserve_bytes:LIMITS.structuredReserveBytes,raster_visual_budget_bytes:LIMITS.rasterVisualBytes,actual_uncompressed_bytes_excluding_manifest:zip.size,raster_visual_bytes:zip.visualBytes,component_bytes:componentBytes,omitted_raster_visual_count:zip.visualOmissions.length},expected:{pages:registry.pages.length,controls:registry.controls.length,workflows:graphIndex.inventory_count,nodes:graphIndex.expected_node_count,edges:graphIndex.expected_edge_count},exported:{pages:capturedPages.length,page_visuals:capturedPages.filter(x=>x.visual_status==="complete").length,controls:coverage.counts.registered,observed_controls:coverage.counts.rendered+coverage.counts.disabled,workflows:indexItems.length,workflow_visuals:indexItems.filter(x=>x.png_status==="complete").length,nodes:graphIndex.exported_node_count,edges:graphIndex.exported_edge_count},inventory:{registered_pages:registry.pages.length,captured_pages:capturedPages.length,workflow_inventory:graphIndex.inventory_count,workflows_exported:indexItems.length,registered_controls:coverage.counts.registered,observed_registered_controls:coverage.counts.rendered+coverage.counts.disabled,uncovered_rendered_controls:coverage.counts.uncovered,workflows:indexItems.length,nodes:graphIndex.exported_node_count,edges:graphIndex.exported_edge_count},capture_complete:pageVisualsComplete&&workflowsComplete&&index.status==="available"&&graphErrors.length===0,completeness:{pages:pageOutcomes,workflows:workflowRecords,control_coverage:coverage.counts,omissions},truncated:Object.values(histories.truncation||{}).some(n=>Number(n)>0)||pageOutcomes.some(x=>x.capture_truncated)||zip.visualOmissions.length>0,truncation:{browser_history:histories.truncation||{},page_visual_pages:pageOutcomes.filter(x=>x.capture_truncated).map(x=>x.page_id),package_limit_bytes:LIMITS.packageBytes},omissions,privacy:{authentication_material:"excluded",cookies:"excluded",authorization_headers:"excluded",passwords_and_form_values:"redacted",conversation_and_request_bodies:"excluded",account_detail_rows:"redacted",external_media:"omitted and listed by page",operational_data:"same bounded authorized projection used by dashboard"},offline_usage:"Open website/pages/*.html in a modern browser; read JSON/SVG/PNG files directly. Missing raster previews are listed in omissions; canonical graph JSON and SVG remain available. No live website, database, GitHub or Camrui connection is needed."};
      const manifestFiles=[];for(const file of zip.files){manifestFiles.push({path:file.name,size_bytes:file.data.length,sha256:await sha256(file.data)});}manifest.files=manifestFiles;zip.add("manifest.json",JSON.stringify(manifest,null,2));
      const blob=zip.finish(),filename=`riverview-diagnostic-${manifest.captured_at.replaceAll(":","-")}.zip`;
      await presentSnapshot(blob,filename,manifest.capture_complete);
      return {manifest,package_bytes:blob.size};
    }catch(error){RiverviewDiagnostics.suppress(false);const toast=document.querySelector("#toast");if(toast){toast.textContent=`Snapshot unavailable: ${String(error.message||"export_failed").slice(0,100)}`;toast.classList.add("show");setTimeout(()=>toast.classList.remove("show"),5000);}RiverviewDiagnostics.recordError("snapshot_export_failed","/api/v1/snapshot");throw error;}
    finally{if(button){button.disabled=false;button.focus({preventScroll:true});}}
  }
  window.RiverviewSnapshot={download};
  document.addEventListener("click",event=>{if(event.target.closest("#snapshot")){event.preventDefault();event.stopImmediatePropagation();const api=window.RiverviewSnapshotApi;if(typeof api!=="function")return;download(api).catch(()=>{});}},true);
})();
