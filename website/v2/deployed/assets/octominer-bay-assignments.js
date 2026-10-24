/*
Riverview~ Controlled Data
File: website/v2/deployed/assets/octominer-bay-assignments.js
Component: RIVERVIEW-OCTO1-REPORTED-PHYSICAL-BAY-ASSIGNMENTS
Purpose: Store Steward-reported GPU-to-physical-bay assignments separately from chassis layout coordinates
Authority: Steward-reported inventory; not independently verified against live hardware
*/
window.RV_OCTO1_BAY_ASSIGNMENTS = Object.freeze({
  provenance: "Steward-reported assignment; physical installation and bay mapping are not independently verified.",
  bays: Object.freeze({
    "1": Object.freeze({ type: "p100", gpu: "Tesla P100", memory: "16 GB" }),
    "2": Object.freeze({ type: "p100", gpu: "Tesla P100", memory: "16 GB" }),
    "3": Object.freeze({ type: "p100", gpu: "Tesla P100", memory: "16 GB" }),
    "4": Object.freeze({ type: "p100", gpu: "Tesla P100", memory: "16 GB" }),
    "10": Object.freeze({ type: "rtx3060ti", gpu: "RTX 3060 Ti", memory: "8 GB" }),
    "12": Object.freeze({ type: "rtx4090", gpu: "RTX 4090", memory: "24 GB" })
  }),
  pendingInstallation: Object.freeze({ gpu: "Tesla P100", memory: "16 GB", bay: null, state: "awaiting installation" })
});
