# Measurement and Logging Protocol

Status: implementation guide  
Purpose: define the metrics and logs needed before model changes become meaningful.

## 1. Why this exists

The project claim is not simply that LoRA is small. The claim is that foveated visual evidence and adapter residency can reduce total runtime pressure under co-resident VRAM constraints. Therefore the logging system must separate:

```text
visual token / ROI cost
adapter resident memory
KV cache estimate
peak allocated memory
latency and load/unload overhead
routing and fallback behavior
verification and graph governance
```

## 2. Run-level metadata

Every run should create one `run_manifest.json`.

```json
{
  "run_id": "2026-05-pilot-001",
  "created_at": "ISO-8601 timestamp",
  "git_commit": "unknown",
  "config_path": "configs/pilot_minimal.yaml",
  "hardware": {
    "device_name": "RTX 3090",
    "total_vram_mb": 24576,
    "driver_or_runtime": "unknown",
    "backend": "costsim_replay|cuda|mps|mlx|llama_cpp|ollama|mock"
  },
  "model": {
    "backbone": "Compact 7B 4-bit VLM proxy",
    "precision": "fp16|bf16|int4|cost_model|unknown",
    "quantization": "4bit_proxy|none|unknown"
  },
  "dataset": {
    "name": "3090_costsim_grid",
    "split": "costsim_prior|synthetic_train|real_holdout|ood_branch|hard_negative|quarantine|unknown"
  },
  "evidence": {
    "measurement_source": "cost_model_3090",
    "source_summary_csv": "output/experiment/3090_pilot_costsim/02_simulation_run/results/summary.csv",
    "scientific_status": "feasibility_prior"
  }
}
```

## 3. Per-sample RouteTrace

Write one JSONL row per sample and per decision step.

```json
{
  "sample_id": "sample_0001",
  "step_id": 0,
  "stage": "0_3090_costsim_replay",
  "baseline_id": "S0-A",
  "split": "costsim_prior",
  "query": "inspect the component label",
  "evidence": {
    "measurement_source": "cost_model_3090",
    "source_run_id": "costsim-00001",
    "source_baseline": "B0",
    "scientific_status": "feasibility_prior"
  },
  "input": {
    "global_resolution": [336, 336],
    "roi_resolution": null,
    "roi_count": 0
  },
  "routing": {
    "router_type": "none",
    "selected_roi_id": null,
    "selected_adapter_ids": [],
    "confidence": null,
    "abstained": false,
    "fallback_used": false,
    "reason_codes": []
  },
  "memory": {
    "visual_token_count": 576,
    "visual_token_count_source": "costsim_patch_count",
    "peak_vram_mb": 9357.12,
    "avg_vram_mb": null,
    "reserved_vram_mb": 2048.0,
    "adapter_resident_mb": 0,
    "kv_cache_estimate_mb": null,
    "kv_cache_estimate_source": "not_modeled_in_stage0_costsim",
    "reserve_pass": true,
    "reserve_headroom_mb": 11634.88
  },
  "timing": {
    "total_latency_ms": 48.34,
    "global_encode_ms": null,
    "roi_encode_ms": null,
    "adapter_load_ms": 0,
    "adapter_evict_ms": 0,
    "generation_ms": null,
    "verification_ms": null
  },
  "quality": {
    "task_score": null,
    "answer_correct": null,
    "verifier_score": null,
    "verifier_pass": null,
    "confidence": null
  },
  "failure": {
    "main_failure_type": null,
    "notes": null
  }
}
```

## 4. Metric definitions

### 4.1 Visual token count

Definition:

```text
number of visual tokens passed into the transformer for the current sample or step
```

If the exact token count is unavailable, log an estimate and mark it:

```json
{"visual_token_count": 576, "visual_token_count_source": "estimated_patch_count"}
```

Suggested estimates:

```text
ViT-like patching: ceil(height / patch_size) * ceil(width / patch_size)
Multiple ROIs: low_res_tokens + sum(roi_tokens)
```

### 4.2 KV cache estimate

If exact KV memory is unavailable, estimate:

```text
kv_cache_bytes ≈ 2 * num_layers * seq_len * num_kv_heads * head_dim * bytes_per_element
```

Where `2` accounts for K and V.

Always label the estimate source:

```json
{"kv_cache_estimate_source": "formula|runtime|unavailable"}
```

### 4.3 Adapter resident memory

Definition:

```text
sum of memory occupied by adapter weights currently resident on the accelerator
```

For LoRA on a linear layer:

```text
params = rank * (d_in + d_out)
bytes = params * bytes_per_param
```

Log both declared and measured values when possible:

```json
{
  "adapter_resident_mb_declared": 12.4,
  "adapter_resident_mb_measured": null
}
```

### 4.4 Peak allocated VRAM

Use backend-specific APIs when available:

```text
CUDA/PyTorch: torch.cuda.max_memory_allocated()
MPS/PyTorch: torch.mps.current_allocated_memory() where available
MLX/llama.cpp/Ollama: use process-level or tool-specific statistics if exposed
Mock backend: log null and keep pipeline functional
CostSim replay: replay the existing estimate and label it with `measurement_source = cost_model_3090`
```

Reset peak stats per run or per sample if backend supports it.

### 4.5 Latency

Record at least:

```yaml
latency_components:
  - total_latency_ms
  - global_encode_ms
  - roi_encode_ms
  - adapter_load_ms
  - adapter_evict_ms
  - generation_ms
  - verification_ms
```

Report p50, p95, and p99 at the end of a run.

### 4.6 Routing metrics

```yaml
routing_metrics:
  top1_route_hit:
    definition: selected adapter matches required_adapter_tags exactly or by approved taxonomy mapping
  top3_route_hit:
    definition: correct adapter appears in top-3 candidates
  wrong_route_rate:
    definition: selected adapter is incompatible with required evidence type or certified tag
  abstention_rate:
    definition: router chooses no adapter or fallback due to uncertainty
  abstention_quality:
    definition: fraction of abstentions that occur on genuinely ambiguous or unsafe samples
  resident_hit_rate:
    definition: selected adapter was already hot/warm resident and did not require cold load
```

### 4.7 Collapse indicators

```yaml
collapse_indicators:
  wrong_adapter_confidence_gain:
    definition: confidence(wrong_lora) - confidence(base_or_correct)
  adapter_route_oscillation:
    definition: adapter changes repeatedly across adjacent ROI/steps without evidence improvement
  false_commit:
    definition: graph update committed despite verifier failure or later contradiction
  repeated_fallback_loop:
    definition: fallback invoked more than configured max count for same sample
  peak_vram_violation:
    definition: max measured memory exceeds configured budget
```

## 5. Summary table

Every run should emit `summary.csv` with:

```text
run_id,stage,baseline_id,split,n_samples,task_score_mean,task_score_std,visual_tokens_mean,peak_vram_mb_mean,peak_vram_mb_p95,adapter_resident_mb_mean,kv_cache_mb_mean,total_latency_ms_p50,total_latency_ms_p95,total_latency_ms_p99,top1_route_hit,wrong_route_rate,abstention_rate,fallback_success_rate,main_failure_type
```

## 6. Minimal file layout

```text
runs/
  <run_id>/
    run_manifest.json
    route_traces.jsonl
    summary.csv
    failures.csv
    artifacts/
      optional_plots_or_debug_images
```

## 7. Acceptance criteria for Codex

Codex should implement logging before model complexity.

Minimum acceptable implementation:

```text
- Can create run_manifest.json
- Can write route_traces.jsonl
- Can aggregate summary.csv
- Can replay or distill the existing RTX 3090 CostSim result with no actual model
- Can run Stage 0 configs without crashing
- Labels Stage 0 values as cost-model estimates, not real VLM profiler measurements
```
