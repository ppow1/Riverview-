# Current GPU Inventory — Riverview

**Inventory date:** 2026-10-28 (America/New_York)  
**Source:** Steward-reported physical GPU placement and machine power state.  
**Scope:** Current physical GPU mapping; not a live telemetry report.

## Current GPU allocation

| Host | GPUs physically installed | Total nominal GPU VRAM | Reported state / purpose |
| --- | --- | ---: | --- |
| Development PC (`DESKTOP-JA3RPNQ`) | 1 × NVIDIA GeForce RTX 4090 (24 GB) | 24 GB | RTX 4090 returned to development machine for image/ComfyUI work |
| OctoMiner1 (`OCTOMINER1`) | 4 × NVIDIA Tesla P100 PCIe (16 GB each); 1 × NVIDIA GeForce RTX 3060 Ti (8 GB) | 72 GB | Four P100s retained for local large-model inference; 3060 Ti installed |
| OctoMiner2 (`OCTOMINER2`) | 1 × NVIDIA Tesla P100 PCIe (16 GB) | 16 GB | **Powered off** as of inventory date |

**Total physical inventory:** 6 GPUs; **112 GB nominal aggregate VRAM**, distributed across three hosts. Aggregate VRAM is not a single unified memory pool.

## Changes recorded on 2026-10-28

- RTX 4090 moved **from OctoMiner1 back to the development PC**.
- OctoMiner1 now has **four P100s and the RTX 3060 Ti**, with **no RTX 4090** installed.
- OctoMiner2 currently has **one P100** and is **powered off**.

## Operational notes

- This file is the dated **operator-reported hardware inventory**, not a guarantee that services are running or that GPUs have been verified by a fresh `nvidia-smi` reading.
- Avoid assigning the RTX 4090 to OctoMiner1 in deployment scripts, model-placement plans, or documentation until the physical allocation changes again.
- OctoMiner2 being powered off is a **host power state**, not a missing GPU.
- Update this file whenever GPU placement changes; retain dated change notes for provenance.
