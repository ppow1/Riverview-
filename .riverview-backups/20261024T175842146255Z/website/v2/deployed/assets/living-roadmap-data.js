/* Presentation index derived from the canonical V2 roadmap and verified Issue #268 deliveries. */
(() => {
  "use strict";
  const repo = "https://github.com/ppow1/Riverview-";
  const origin = "https://github.com/ppow1/Riverview";
  const items = [
    {
      id: "grace-autonomy", title: "Grace Autonomy", workstream: "Grace Autonomy",
      summary: "Reasoning and execution loop; owned by its separate workstream.",
      detail: "This roadmap has no authoritative live integration for Grace's supervisory loop, GPU activity, or current execution state. Status is Unknown here. Open Grace chat or Engineering Progress for the existing authorized views.",
      priority: "P0", status: "unknown", stage: "Active Work · separate workstream; live state unavailable",
      tags: ["grace", "autonomy", "separate-workstream"],
      links: [{label:"Open Grace chat", href:"#grace"},{label:"Engineering Progress", href:"#work"},
        {label:"Roadmap source", href:`${repo}/blob/b240cb7dab3a94197a4c8f8eda11aee3a5a981d7/docs/visualization/RIVERVIEW_DEVELOPMENT_ROADMAP.md`}]
    },
    {
      id: "website-visualization", title: "Website Visualization", workstream: "Website Visualization",
      summary: "Steward-facing navigation, operational visibility, and evidence in V2.",
      detail: "The V2 roadmap shell, authenticated acceptance, operational inbox, and Work evidence panels are deployed. This workstream page is a first interactive view over the existing roadmap document and objective API; it is not a new execution authority.",
      priority: "P0", status: "in_progress", stage: "Active Work · V2 interface",
      tags: ["website", "visualization", "v2"],
      links: [{label:"Work & execution status", href:"#work"},{label:"Notifications & events", href:"#communications"},
        {label:"Issue #268", href:`${repo}/issues/268`}]
    },
    {
      id: "operational-inbox", title: "V2 Operational Inbox", workstream: "Website Visualization",
      summary: "Unified notifications, attention, and operational event visibility.",
      detail: "Delivered by PR #273. Uses existing authenticated feeds and keeps each source's status visible.",
      priority: "P1", status: "completed", stage: "Complete",
      tags: ["website", "notifications", "events"],
      links: [{label:"Open Communications", href:"#communications"},{label:"PR #273", href:`${repo}/pull/273`}]
    },
    {
      id: "work-evidence", title: "Work Blockers and Evidence", workstream: "Website Visualization",
      summary: "Lifecycle, recorded blockers, assignment ownership, progress time, and evidence links.",
      detail: "Delivered by PR #274. Exact objective/assignment relationships are used. Dependency edges are not available from the current projection and are labeled unavailable.",
      priority: "P1", status: "completed", stage: "Complete",
      tags: ["website", "work", "evidence"],
      links: [{label:"Open Work", href:"#work"},{label:"PR #274", href:`${repo}/pull/274`}]
    },
    {
      id: "institutional-proposals", title: "Institutional Proposals in V2", workstream: "Website Visualization",
      summary: "Bring the existing proposal registry and decision evidence into V2.",
      detail: "Listed as a high-priority V2 migration in the committed development roadmap and parity matrix. No Planning Lot, elaboration, Design/Specification, Ready Bench, or Active Work lifecycle record is linked here; this is not execution authorization.",
      priority: "P1", status: "unknown", stage: "Roadmap candidate · lifecycle stage not recorded",
      tags: ["website", "proposals", "governance"],
      links: [{label:"V1/V2 parity matrix", href:`${repo}/blob/b240cb7dab3a94197a4c8f8eda11aee3a5a981d7/docs/runbooks/riverview_v1_v2_parity.md`},
        {label:"Development roadmap", href:`${repo}/blob/b240cb7dab3a94197a4c8f8eda11aee3a5a981d7/docs/visualization/RIVERVIEW_DEVELOPMENT_ROADMAP.md`}]
    },
    {
      id: "master-roadmap-source", title: "Canonical Master Roadmap", workstream: "Grace Autonomy",
      summary: "103 versioned waypoints exist in the original repository; PostgreSQL is documented as the live status authority.",
      detail: "The V2 Dashboard has no integration to the source roadmap database. The repository JSON is a versioned Git snapshot (RV-MASTER-2026-08-20-RECONCILIATION), not live execution state. The source README and Ready Bench board currently conflict, so this view does not import its statuses.",
      priority: "unassigned", status: "unknown", stage: "Source not integrated",
      tags: ["grace", "roadmap", "source-gap"],
      links: [{label:"Master roadmap JSON", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/roadmap/RIVERVIEW_MASTER_ROADMAP.json`},
        {label:"Roadmap source README", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/roadmap/README.md`}]
    },
    {
      id: "ready-bench-rb0001", title: "Operator Model Override (RB-0001)", workstream: "Grace Autonomy",
      summary: "Steward-committed design waiting behind the current Jessica execution path.",
      detail: "The board file lists READY and a Steward commitment, but the master roadmap README says the Ready Bench is intentionally empty and PostgreSQL is the live status authority. V2 cannot reconcile these sources. Treat the current stage/status as Unknown until that authority is connected; do not infer execution readiness. Priority is not assigned in the source board.",
      priority: "unassigned", status: "unknown", stage: "Ready Bench · source reconciliation required",
      tags: ["grace", "ready-bench", "model-operations"],
      links: [{label:"Ready Bench source", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/boards/ready_bench.md`},
        {label:"Work packages and specification", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/ready_bench/RB-0001-operator-model-override.md`}]
    },
    {
      id: "parking-lot-web", title: "Web Operator UI Stabilization (PL-0008)", workstream: "Website Visualization",
      summary: "Captured idea; it remains parked until its stated promotion condition is met.",
      detail: "The canonical Parking Lot marks this item CAPTURED. Capture preserves the idea and does not commit Riverview to implementation. This roadmap does not promote it.",
      priority: "unassigned", sourcePriority: "High", status: "parked", stage: "Parking Lot",
      tags: ["website", "parking-lot", "architecture"],
      links: [{label:"Parking Lot source", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/boards/parking_lot.md`},
        {label:"Governing lifecycle", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/PARKING_LOT_AND_READY_BENCH.md`},
        {label:"Entry detail", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/parking_lot/PL-0008-web-operator-ui-stabilization-and-rearchitecture.md`}]
    },
    {
      id: "elaboration-hermes", title: "Hermes resident modeling and skill governance (PL-0005/0006)", workstream: "Grace Autonomy",
      summary: "Steward-approved for elaboration; current design progress is not connected to V2.",
      detail: "The canonical Parking Lot records PROMOTED_FOR_ELABORATION. That authorizes bounded discussion/specification only; it is not Ready Bench promotion or execution permission. The source priorities are Strategic and High, not P0–P3.",
      priority: "unassigned", sourcePriority: "Strategic / High", status: "unknown", stage: "Steward-approved elaboration · progress unavailable",
      tags: ["grace", "elaboration", "parking-lot"],
      links: [{label:"Parking Lot source", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/boards/parking_lot.md`},
        {label:"Governing lifecycle", href:`${origin}/blob/4590f2fb5e6813d409b3faf8e37a151778aea1f6/docs/operations/PARKING_LOT_AND_READY_BENCH.md`}]
    },
    {
      id: "future-interfaces", title: "Command chair, Stream Deck, mobile, and Quest/XR", workstream: "Website Visualization",
      summary: "Later roadmap directions for shared operational data across physical interfaces.",
      detail: "The canonical development roadmap labels these later. This is a future roadmap direction, not a Parking Lot/Ready Bench entry or authorization to execute. No live GPU or supervisory-loop monitoring is claimed.",
      priority: "P3", status: "unknown", stage: "Later roadmap · lifecycle stage not recorded",
      tags: ["website", "mobile", "stream-deck", "quest-xr"],
      links: [{label:"Development roadmap", href:`${repo}/blob/b240cb7dab3a94197a4c8f8eda11aee3a5a981d7/docs/visualization/RIVERVIEW_DEVELOPMENT_ROADMAP.md`},
        {label:"Command Center artwork tracking", href:"https://github.com/ppow1/Riverview-/issues/271"}]
    },
    {
      id: "mobile-acceptance", title: "Responsive V2 task-flow acceptance", workstream: "Website Visualization",
      summary: "Verify real V2 work and settings flows at mobile widths before considering a separate mobile app.",
      detail: "This is recorded in the committed roadmap under Next. Its V2 lifecycle stage and execution authorization are not connected in this prototype.",
      priority: "P2", status: "unknown", stage: "Roadmap Next · lifecycle stage not recorded",
      tags: ["website", "mobile", "acceptance"],
      links: [{label:"Development roadmap", href:`${repo}/blob/b240cb7dab3a94197a4c8f8eda11aee3a5a981d7/docs/visualization/RIVERVIEW_DEVELOPMENT_ROADMAP.md`},
        {label:"V1/V2 parity matrix", href:`${repo}/blob/b240cb7dab3a94197a4c8f8eda11aee3a5a981d7/docs/runbooks/riverview_v1_v2_parity.md`}]
    }
  ];
  window.RiverviewV2LivingRoadmapData = Object.freeze({items: Object.freeze(items), sourceCommit:"4590f2fb5e6813d409b3faf8e37a151778aea1f6"});
  if (typeof module !== "undefined" && module.exports) module.exports = window.RiverviewV2LivingRoadmapData;
})();
