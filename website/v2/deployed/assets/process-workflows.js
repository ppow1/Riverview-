// Riverview~ controlled asset; component STEWARD-DASHBOARD.
// File: src/riverview_core/status_dashboard/static/workflow.js
// Revision: 1.1.0
// Purpose: Render, fit, zoom, pan and navigate canonical process workflows.
// Execution Model: Browser request-driven; loaded only by the authenticated workflow view.
// Observability: Displays graph revision, node identities, references and explicit live-position state.
// Dependencies: status_dashboard API v1.1; process_graphs canonical registry.
// Authority: No graph edits or operational commands; live position requires an exact persisted node ID.
// Changed: 2026-10-10 UTC | RV-M3.1-003 | Initial canonical workflow browser view.
// Changed: 2026-10-13 UTC | RV-WORKFLOW-ACCOUNT-SESSION | Use same-origin account cookies as well as recovery bearer token.
// Changed: 2026-10-15 UTC | RV-WEBSITE-PL027 | Focus cross-workflow destinations and preserve a return path to the source jump node.
// Changed: 2026-10-15 UTC | RV-WEBSITE-PL027 | Keep source return navigation visible when a destination graph or node cannot be loaded.
// Changed: 2026-10-16 UTC | RV-WEBSITE-PL-NEW-042 | Add initial fit, zoom, pan, reset and fullscreen workflow navigation.
// Contracts: docs/components/STATUS_DASHBOARD_API.schema.json; process_graphs/README.md
// Tests: tests/test_status_dashboard.py; Camrui browser acceptance evidence.
// History: Git and .riverview-backups/manifest.jsonl
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const ns = "http://www.w3.org/2000/svg";
  const state = {graphs: [], selected: null, navigation: [], viewport: {scale:1,x:0,y:0,autoFit:true}, drag:null, loading:false};
  const token = () => sessionStorage.getItem("rv.dashboard.token") || "";
  const get = async (path) => {
    const headers = {Accept:"application/json"};
    if (token()) headers.Authorization = `Bearer ${token()}`;
    const response = await fetch(path, {headers,cache:"no-store",credentials:"same-origin"});
    if (!response.ok) throw new Error(`http_${response.status}`);
    return response.json();
  };
  function updateViewerControls(enabled=Boolean($("graph-canvas").querySelector("svg"))) {
    for(const id of ["graph-fit","graph-zoom-out","graph-zoom-in","graph-reset","graph-fullscreen"])if($(id))$(id).disabled=!enabled;
  }
  function applyViewport() {
    const host=$("graph-canvas"),svg=host.querySelector("svg");if(!svg)return;
    const width=Number(svg.getAttribute("width")),height=Number(svg.getAttribute("height"));
    svg.style.width=`${width}px`;svg.style.height=`${height}px`;
    svg.style.transform=`translate(${state.viewport.x}px,${state.viewport.y}px) scale(${state.viewport.scale})`;
  }
  function fitWorkflow() {
    const host=$("graph-canvas"),svg=host.querySelector("svg");if(!svg||host.clientWidth<80||host.clientHeight<80)return;
    const width=Number(svg.getAttribute("width")),height=Number(svg.getAttribute("height")),pad=22;
    state.viewport.scale=Math.min(1,(host.clientWidth-pad*2)/width,(host.clientHeight-pad*2)/height);
    state.viewport.x=(host.clientWidth-width*state.viewport.scale)/2;
    state.viewport.y=(host.clientHeight-height*state.viewport.scale)/2;
    state.viewport.autoFit=true;applyViewport();
  }
  function resetWorkflowView() { state.viewport={scale:1,x:0,y:0,autoFit:false};applyViewport(); }
  function zoomAt(factor,x,y) {
    const host=$("graph-canvas"),svg=host.querySelector("svg");if(!svg)return;
    const rect=host.getBoundingClientRect(),px=x??rect.width/2,py=y??rect.height/2,old=state.viewport.scale,next=Math.max(.12,Math.min(4,old*factor));
    state.viewport.x=px-(px-state.viewport.x)*next/old;state.viewport.y=py-(py-state.viewport.y)*next/old;
    state.viewport.scale=next;state.viewport.autoFit=false;applyViewport();
  }
  function setFullscreenLabel() {
    const button=$("graph-fullscreen");if(!button)return;
    const active=document.fullscreenElement===$("graph-canvas");button.textContent=active?"Exit full screen":"Full screen";button.setAttribute("aria-pressed",String(active));
  }
  function node(name, attrs = {}) {
    const item = document.createElementNS(ns, name);
    for (const [key, value] of Object.entries(attrs)) item.setAttribute(key, String(value));
    return item;
  }
  function choose(graphId, focusNodeId = null) {
    const target = state.graphs.find((item) => item.graph_id === graphId);
    if (!target) return;
    $("graph-select").value = graphId;
    loadGraph(graphId, focusNodeId);
  }
  function openJump(graphId, targetNodeId, sourceNodeId) {
    if (!state.selected || !state.graphs.some((item) => item.graph_id === graphId)) return;
    state.navigation.push({graphId:state.selected.graph_id,nodeId:sourceNodeId});
    choose(graphId, targetNodeId);
  }
  function returnFromJump() {
    const previous = state.navigation.pop();
    if (previous) choose(previous.graphId, previous.nodeId);
  }
  function returnButton() {
    const previous = state.navigation[state.navigation.length-1];
    if (!previous) return null;
    const row=document.createElement("div");row.className="row";
    const label=document.createElement("span");
    const source=state.graphs.find((item)=>item.graph_id===previous.graphId);
    label.textContent=`Return to ${source?`${source.component_id} — ${source.workflow_id}`:previous.graphId}`;
    const button=document.createElement("button");button.className="secondary";
    button.textContent="Back to source node";button.addEventListener("click",returnFromJump);
    row.append(label,button);return row;
  }
  function showNodeDetail(item) {
    const panel = $("graph-node-detail");
    panel.replaceChildren();
    const title = document.createElement("strong"); title.textContent = `${item.type} · ${item.label}`; panel.append(title);
    for (const [label, value] of [["Stable node ID",item.id],["Node revision",item.node_revision]]) {
      const row = document.createElement("div"); row.className = "graph-detail-row";
      const name = document.createElement("span"); name.textContent = `${label}: `;
      const code = document.createElement("code"); code.textContent = value;
      row.append(name,code); panel.append(row);
    }
    for (const [label, refs] of [["Source",item.source_references],["Documentation",item.documentation_references],["Evidence",item.verification_evidence]]) {
      if (!refs?.length) continue;
      const row = document.createElement("div"); row.className = "graph-detail-row";
      const name = document.createElement("span"); name.textContent = `${label}: `; row.append(name);
      refs.forEach((ref,index) => {
        if (index) row.append(document.createTextNode(" · "));
        if (ref.startsWith("docs/components/") && ref.endsWith(".md")) {
          const link = document.createElement("a"); link.href = `/${ref}`; link.textContent = ref; row.append(link);
        } else {
          const code = document.createElement("code"); code.textContent = ref; row.append(code);
        }
      });
      panel.append(row);
    }
  }
  function renderGraph(graph, position, focusNodeId = null) {
    const host = $("graph-canvas"); host.replaceChildren();
    const nodes = graph.nodes || [], edges = graph.edges || [];
    const map = new Map(nodes.map((item,index) => [item.id,{item,index}]));
    const columns = Math.min(4, Math.max(1,Math.ceil(Math.sqrt(nodes.length))));
    const cardW=310, cardH=94, gapX=390, gapY=155, marginX=45, marginY=54;
    const rows=Math.ceil(nodes.length/columns), width=marginX*2+(columns-1)*gapX+cardW, height=marginY*2+(rows-1)*gapY+cardH;
    const xy = new Map(nodes.map((item,index) => [item.id,{x:marginX+(index%columns)*gapX,y:marginY+Math.floor(index/columns)*gapY}]));
    const svg=node("svg",{viewBox:`0 0 ${width} ${height}`,width,height,role:"img","aria-label":`${graph.component_id} ${graph.workflow_id} process graph`});svg.style.transformOrigin="top left";
    const title=node("title"); title.textContent=`${graph.component_id} / ${graph.workflow_id} · graph revision ${graph.graph_revision}`; svg.append(title);
    const defs=node("defs"), marker=node("marker",{id:"rv-arrow",viewBox:"0 0 10 10",refX:9,refY:5,markerWidth:7,markerHeight:7,orient:"auto-start-reverse"});
    marker.append(node("path",{d:"M 0 0 L 10 5 L 0 10 z",class:"graph-arrow"}));defs.append(marker);svg.append(defs);
    const edgeLayer=node("g",{class:"graph-edges"});
    for (const edge of edges) {
      const from=xy.get(edge.from), to=xy.get(edge.to);
      if (!from || !to) continue;
      const x1=from.x+cardW, y1=from.y+cardH/2, x2=to.x, y2=to.y+cardH/2;
      const bend=Math.max(35,Math.abs(x2-x1)*.38);
      const path=node("path",{d:`M ${x1} ${y1} C ${x1+bend} ${y1}, ${x2-bend} ${y2}, ${x2} ${y2}`,
        class:`graph-edge edge-${String(edge.type).replace(/[^a-z0-9_-]/gi,"-")}`,"marker-end":"url(#rv-arrow)"});
      const description=node("title"); description.textContent=`${edge.type}${edge.label ? `: ${edge.label}` : ""}`;path.append(description);edgeLayer.append(path);
    }
    svg.append(edgeLayer);
    for (const item of nodes) {
      const pos=xy.get(item.id), group=node("g",{class:`graph-node graph-${item.type}${position?.status==="current"&&position.node_id===item.id?" graph-live-current":""}`,"data-node-id":item.id,tabindex:0,role:"button","aria-label":`${item.type}: ${item.label}`});
      const rectAttrs={x:pos.x,y:pos.y,width:cardW,height:cardH,rx:12,class:"graph-node-shape"};
      if (item.type === "decision") {
        group.append(node("polygon",{points:`${pos.x+cardW/2},${pos.y} ${pos.x+cardW},${pos.y+cardH/2} ${pos.x+cardW/2},${pos.y+cardH} ${pos.x},${pos.y+cardH/2}`,class:"graph-node-shape"}));
      } else if (item.type === "entry" || item.type === "exit") {
        group.append(node("rect",{...rectAttrs,rx:34}));
      } else group.append(node("rect",rectAttrs));
      const typeLabel=node("text",{x:pos.x+15,y:pos.y+20,class:"graph-node-type"});typeLabel.textContent=`${item.type.toUpperCase()} · r${item.node_revision}`;group.append(typeLabel);
      const text=node("text",{x:pos.x+15,y:pos.y+46,class:"graph-node-label"});
      const words=item.label.split(/\s+/);let line="",lineNo=0;
      for (const word of words) { const next=line ? `${line} ${word}` : word;if(next.length>32&&line){const t=node("tspan",{x:pos.x+15,dy:lineNo?18:0});t.textContent=line;text.append(t);line=word;lineNo++;}else line=next; }
      const final=node("tspan",{x:pos.x+15,dy:lineNo?18:0});final.textContent=line;text.append(final);group.append(text);
      const activate=()=>showNodeDetail(item);group.addEventListener("click",activate);group.addEventListener("keydown",(event)=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();activate();}});svg.append(group);
    }
    host.append(svg);
    state.viewport={scale:1,x:0,y:0,autoFit:true};updateViewerControls(true);requestAnimationFrame(()=>fitWorkflow());
    if (focusNodeId) {
      const focusedItem = nodes.find((item) => item.id === focusNodeId);
      const focusedElement = [...svg.querySelectorAll(".graph-node")].find((item) => item.getAttribute("data-node-id") === focusNodeId);
      if (focusedItem && focusedElement) {
        focusedElement.classList.add("graph-node-selected");
        showNodeDetail(focusedItem);
        focusedElement.focus({preventScroll:true});
        focusedElement.scrollIntoView({block:"center",inline:"center"});
      }
    }
    $("graph-revision").textContent=`${graph.component_id} · ${graph.workflow_id} · graph ${graph.graph_revision} · ${nodes.length} nodes / ${edges.length} edges`;
    if(position?.status==="current") $("graph-execution-position").textContent=`Observed live execution position: ${position.state} at ${position.node_id} (assignment ${position.assignment_id}).`;
    else $("graph-execution-position").textContent=`Live execution position: ${position?.status || "unknown"} — ${position?.reason || "No authoritative node mapping was returned; no node is highlighted."}`;
    const jumps=nodes.filter((item)=>item.type==="jump");
    const jumpHost=$("graph-jumps");jumpHost.replaceChildren();
    const returnRow=returnButton();if(returnRow)jumpHost.append(returnRow);
    if(!jumps.length){const empty=document.createElement("p");empty.className="muted";empty.textContent="This workflow has no cross-workflow jump points.";jumpHost.append(empty);return;}
    for(const jump of jumps){const row=document.createElement("div");row.className="row";const label=document.createElement("span");label.textContent=`${jump.label} → ${jump.jump_target_id}`;const button=document.createElement("button");button.className="secondary";button.textContent="Open destination workflow and node";const destinationId=jump.jump_target_id.slice(0,jump.jump_target_id.lastIndexOf(":"));button.disabled=!state.graphs.some((g)=>g.graph_id===destinationId);button.addEventListener("click",()=>openJump(destinationId,jump.jump_target_id,jump.id));row.append(label,button);jumpHost.append(row);}
  }
  async function loadGraph(graphId, focusNodeId = null) {
    if (!graphId) return;
    $("graph-canvas").textContent="Loading canonical workflow…";
    try {
      const result=await get(`/api/v1/graphs/${encodeURIComponent(graphId)}`);
      if(focusNodeId&&!(result.graph.nodes||[]).some((item)=>item.id===focusNodeId))throw new Error("workflow_target_node_missing");
      state.selected=result.graph;renderGraph(result.graph,result.graph.execution_position,focusNodeId);
    }
    catch(error){
      $("graph-canvas").textContent=`Workflow data unavailable (${error.message}).`;
      updateViewerControls(false);
      $("graph-revision").textContent="Canonical registry unavailable";
      $("graph-execution-position").textContent="Live execution position: unavailable.";
      const jumpHost=$("graph-jumps");jumpHost.replaceChildren();const back=returnButton();if(back)jumpHost.append(back);
    }
  }
  $("graph-fit")?.addEventListener("click",fitWorkflow);
  $("graph-zoom-in")?.addEventListener("click",()=>zoomAt(1.25));
  $("graph-zoom-out")?.addEventListener("click",()=>zoomAt(.8));
  $("graph-reset")?.addEventListener("click",resetWorkflowView);
  $("graph-fullscreen")?.addEventListener("click",async()=>{const host=$("graph-canvas");try{if(document.fullscreenElement===host)await document.exitFullscreen();else await host.requestFullscreen();}catch(_){return;}});
  document.addEventListener("fullscreenchange",()=>{setFullscreenLabel();if(state.viewport.autoFit)requestAnimationFrame(fitWorkflow);});
  const canvas=$("graph-canvas");
  canvas.addEventListener("wheel",event=>{if(!canvas.querySelector("svg"))return;event.preventDefault();const rect=canvas.getBoundingClientRect();zoomAt(event.deltaY<0?1.12:.89,event.clientX-rect.left,event.clientY-rect.top);},{passive:false});
  canvas.addEventListener("pointerdown",event=>{if(!canvas.querySelector("svg")||event.target.closest?.(".graph-node"))return;state.drag={pointerId:event.pointerId,x:event.clientX,y:event.clientY};canvas.setPointerCapture(event.pointerId);event.preventDefault();});
  canvas.addEventListener("pointermove",event=>{if(!state.drag||state.drag.pointerId!==event.pointerId)return;state.viewport.x+=event.clientX-state.drag.x;state.viewport.y+=event.clientY-state.drag.y;state.drag.x=event.clientX;state.drag.y=event.clientY;state.viewport.autoFit=false;applyViewport();});
  const endPan=event=>{if(state.drag?.pointerId===event.pointerId){state.drag=null;if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);}};
  canvas.addEventListener("pointerup",endPan);canvas.addEventListener("pointercancel",endPan);
  if(typeof ResizeObserver!=="undefined")new ResizeObserver(()=>{if(state.viewport.autoFit)fitWorkflow();else applyViewport();}).observe(canvas);
  async function initialize() {
    if (state.loading) return;
    state.loading=true;
    try {
      const result=await get("/api/v1/graphs");state.graphs=result.items||[];
      const select=$("graph-select");select.replaceChildren();
      for(const graph of state.graphs){const option=document.createElement("option");option.value=graph.graph_id;option.textContent=`${graph.component_id} — ${graph.workflow_id}`;select.append(option);}
      if(!state.graphs.length){select.disabled=true;$("graph-revision").textContent="No canonical workflows registered.";return;}
      select.disabled=false;select.addEventListener("change",()=>{state.navigation=[];loadGraph(select.value);});
      await loadGraph(select.value);
    } catch(error){$("graph-select").disabled=true;$("graph-revision").textContent=`Graph registry unavailable (${error.message}).`;}
    finally { state.loading=false; }
  }
  window.addEventListener("rvv2:view",event=>{if(event.detail?.view==="process-workflows"){if(!state.graphs.length)initialize();requestAnimationFrame(()=>requestAnimationFrame(()=>{if(state.viewport.autoFit)fitWorkflow();}));}});
  window.addEventListener("storage",event=>{if(event.key==="rv.dashboard.token"&&event.newValue)initialize();});
  // The graph API is read-only; same-origin account authentication is used by the V2 dashboard.

})();
