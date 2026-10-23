# Issue #256 photoreal workflow acceptance

**Document Revision:** 1.0.0  
**Task:** RV-ISSUE-256-PHOTOREAL-WORKFLOW  
**Date:** 2026-10-23 UTC

## Selection and host capacity

- Host: OCTOMINER1, ComfyUI 0.9.2, RTX 4090 (physical GPU 1), 24,564 MiB VRAM.
- Before install, ComfyUI had only `sd_turbo.safetensors`; it used about 3,009 MiB on the 4090. The other P100 GPUs remained assigned to the existing 80B service. No model was installed on root storage.
- Selected checkpoint: RealVisXL V5.0 fp16, `RealVisXL_V5.0_fp16.safetensors`, from the model author's Hugging Face repository. The author describes the model as aimed at photorealism and Hugging Face declares `openrail++` in the [model card](https://huggingface.co/SG161222/RealVisXL_V5.0/blob/main/README.md).
- The 6.94 GB file's published SHA-256 is `6a35a7855770ae9820a3c931d4964c3817b6d9e3c6f9c4dabb5b3a94e5643b80` per the [publisher's file page](https://huggingface.co/SG161222/RealVisXL_V5.0/blob/main/RealVisXL_V5.0_fp16.safetensors). Installed file size is 6,938,065,488 bytes; downloaded bytes matched that SHA-256. The model volume had 26 GiB free beforehand and 19 GiB after installation. The 4090 had about 21.2 GiB free before generation; the model fit without changing GPU placement or stopping another GPU workload.

## Matched prompt comparison

Prompt: `A dog walking along a sidewalk, candid DSLR photograph, realistic fur, natural lighting, photographic detail, not a painting or illustration.`

| Workflow | Checkpoint and settings | Seed | Time | Output |
| --- | --- | ---: | ---: | --- |
| SD-Turbo | `sd_turbo.safetensors`, 512×512, 1 step, CFG 1, Euler / normal | 256 | 0.417 s end to end; ComfyUI reported 0.187 s | `/mnt/model-storage/riverview-comfyui/output/rv-issue256-sdturbo_00001_.png` |
| RealVisXL cold | `RealVisXL_V5.0_fp16.safetensors`, 1024×1024, 30 steps, CFG 5, DPM++ 2M / Karras | 256 | 48.384 s end to end, including first model load | `/mnt/model-storage/riverview-comfyui/output/riverview-comfyui_00018_.png` |
| RealVisXL warm | Same workflow and prompt; fresh uncached seed | 257 | 7.197 s end to end | `/mnt/model-storage/riverview-comfyui/output/riverview-comfyui_00019_.png` |

The same seed and prompt were used for the direct SD-Turbo and cold RealVisXL comparison. Warm latency used a new seed because ComfyUI re-used a cached output for a repeat with identical inputs.

The SD-Turbo image reads as a plausible photograph but is softer and less detailed at 512×512. RealVisXL shows stronger fur strands, face detail, and sidewalk/background texture at twice the linear resolution. This is a visual review of these two generated samples, not a general quality guarantee.

### GPU measurements

GPU telemetry was sampled about every 0.3 seconds from OCTOMINER1 while generating. Before the first render the 4090 used 3,009 MiB. During RealVisXL generation it reached 100% utilization and 9,923 MiB allocated (9.7 GiB); after the test it settled at 7,171 MiB with 0% utilization. The warm run reached 99% utilization. No P100 assignment or ComfyUI GPU pinning was changed.

## Artifact verification and download

- Direct ComfyUI output files were PNG, RGB, and the expected 512×512 or 1024×1024 dimensions. Their SHA-256 values were rechecked locally after copying from OCTOMINER1.
- A further warm generation through the existing `ManualImageGenerationService` used the registered `realvisxl-v5-photorealistic.v1` graph (seed 258). `ComfyUIOutputVerifier` returned `ACCEPTED`; the saved 1024×1024 PNG is at `/home/admin1/Pictures/riverview-comfyui/issue256/manual-verified/artifacts/921c4f17dc1c96ab6d321d477c80cf7c55b6f41754f2c0fda437ad089f6919a7/74774b3dfd40` with SHA-256 `6baa1114f0ff98fe82dd7b17132be340069bd324254a4eae2ebb23d5d11d7d6e`.
- The service download method returned 1,488,764 bytes whose SHA-256 exactly matched the verified stored artifact. The authenticated HTTP/UI download path is covered by the existing route/UI tests. A signed-in Steward session was not available for a live production UI submission, so that final authenticated browser interaction remains an operator acceptance step.

## Implementation

The workflow is added to the existing registry at `deploy/comfyui/workflows.json`. The catalog and V2 dropdown remain registry-driven; no workflow ID is hardcoded in the website. SD-Turbo remains registered and unchanged.
