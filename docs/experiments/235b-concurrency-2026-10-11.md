# Riverview 235B inference checkpoint

File revision: 1.0.0
Date: 2026-10-11
Task: RV-235B-CONCURRENCY-20261011
Status: Experimental; four-slot result pending.

Hardware: GPU0 P100 16GB; GPU1 RTX 4090 24GB; GPU2 RTX 3060 Ti 8GB; GPUs3-5 P100 16GB each. 15 GiB host RAM, no swap.

Model: Qwen3-VL-235B-A22B-Thinking-heretic IQ2_M, with Q8_0 multimodal projector. Runtime llama-server.service variant llama-235b-test.service, port 8097, GPU-only offload (-ngl 999), Q4 KV cache, -b 64 -ub 16, --fit off.

64K single slot: -c 65536 -np 1 --kv-unified-per-slot 65536. First 256-token request: 44.525 seconds, 11.793 generation tokens/sec, 22.896 seconds uncached prompt evaluation. Repeated same prompt: 19.611 seconds, 13.112 generation tokens/sec, 26 prompt tokens cached. Most wall-time gain due to prompt caching.

64K two slots: -c 65536 -np 2 --kv-unified-per-slot 32768. Both 256-token requests succeeded in 52.18 seconds wall time; 9.234 generation tokens/sec each, sum 18.468 tokens/sec during generation; end-to-end aggregate 9.812 output tokens/sec. Neither prompt had cached tokens. Model loading required roughly 9-10 minutes. GPU allocation after run ~80808 MiB used, 17448 MiB free; RTX 4090 free ~2353 MiB.

Repeat with two different prompts failed after 3.525 seconds; both HTTP connections closed. Journal at 2026-10-11 15:01:43 EDT: CUDA error invalid argument on GPU1 RTX 4090, ggml_cuda_kernel_launch, ggml_cuda_mul_mat_vec_q, service exit SIGABRT status 6. No kernel OOM entries were found. Exact CUDA defect not isolated. One successful concurrency run does not establish stability.

Pending: steward-requested 4K total context with four slots (-c 4096 -np 4 --kv-unified-per-slot 1024); four different engineering prompts and 256 output tokens each. Results not yet received.

Local diagnostic reports: A:\Riverview\runtime\diagnostics\235b\235b-concurrency-2slot-20261011-145640.txt and 235b-two-slot-fresh-20261011-150138.txt. Existing pre-two-slot service backup: /etc/systemd/system/llama-235b-test.service.pre-concurrency-20261011-144628.

Caveats: Sum of per-request generation rates and end-to-end output rate are different metrics. Raw machine reports are not uploaded in this checkpoint; exact llama.cpp source commit not captured. No runtime service changes made by this documentation checkpoint.
