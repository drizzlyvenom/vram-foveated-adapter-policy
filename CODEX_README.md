# Codex Readme: Two-Track VRAM-Aware Vision Inference Reframe

Status: active 3090 validation guide
Audience: Codex or any implementation agent reading repository markdown only
Primary repository: `drizzlyvenom/vram-foveated-adapter-policy`

## 0. Read order

Read these documents in order before modifying code:

```text
1. CODEX_README.md
2. CODEX_GOAL_3090_TWO_TRACK.md
3. docs/3090_two_track_validation_guideline_ko.md
4. docs/3090_execution_ladder_ko.md
5. docs/3090_metrics_contract_ko.md
6. docs/3090_decision_gates_ko.md
7. docs/3090_codex_implementation_plan_ko.md
```

## 1. New core thesis

This repository should be reframed around a **two-track low-VRAM vision inference system**.

```text
Track A. Resident specialist compression
  Multiple full specialist VLMs
  -> one shared VLM backbone + taxonomy-tagged resident LoRA bank

Track B. Visual evidence compression
  Full high-resolution visual context
  -> low-resolution global view + FoveateR-style high-resolution ROI glimpses

Combined system
  shared backbone + resident LoRA bank + foveated visual evidence
```

The two tracks solve different bottlenecks:

```text
LoRA bank reduces:
  - multiple specialist backbone residency
  - model swap latency
  - adapter/mode switching cost

FoveateR reduces:
  - visual token count
  - prefill cost
  - KV/cache growth from visual context
  - ROI evidence bandwidth
```

Do not treat either track as a replacement for the other.

## 2. What changed from the earlier direction

Earlier documents mixed these topics into one broad policy:

```text
foveation
LoRA routing
HydraLoRA
LeWM feature augmentation
JEPA outcome routing
fallback loop
verification process
graph memory
```

This made the repository hard to reason about.

The new structure keeps only the two direct bottleneck reducers in the core:

```text
core:
  - shared backbone + LoRA specialist bank
  - FoveateR-style ROI evidence compression
  - resident memory accounting
  - visual token / KV accounting
  - compatibility certification

exploratory/future:
  - LeWM feature augmentation
  - JEPA outcome predictor
  - graph memory
  - long-term memory framing
  - complex multi-step fallback loop
```

## 3. Treat Stage 1 and Stage 1+ as Legacy evidence

Existing Stage 1 and Stage 1+ files are still valuable.
They are preserved under `Legacy/stage0_stage1_stage1plus/` and should not be treated as the active runner path.

Reclassify them as follows:

```text
Stage 1 foveation smoke:
  supporting evidence for visual token / ROI cost accounting

Stage 1+ protocol closure:
  exploratory evidence that RouteTrace, adapter-card proxy wiring,
  LeWM proxy, JEPA proxy, and fallback/quarantine instrumentation can run
```

Do **not** use Stage 1+ as evidence that:

```text
- trained LoRA improves accuracy
- JEPA routing is better than taxonomy routing
- fallback loop recovers failures
- foveation alone substantially reduces full model resident VRAM
```

## 4. Implementation status and priorities

### Done

```yaml
done:
  - active docs point to the 3090 two-track validation structure
  - legacy Stage 0/1/1+ artifacts are archived under Legacy
  - dry-run runner emits the required 3090 artifacts
  - memory accounting separates resident, visual incremental, normal, controlled fallback, and emergency peaks
```

### Next priority: R0 memory accounting

Attach real measurement to the existing dry-run fields:

```text
base_after_load_allocated_mb
base_after_load_reserved_mb
adapter_bank_resident_mb
visual_incremental_peak_mb
decode_incremental_peak_mb
kv_cache_estimate_mb
normal_path_peak_vram_mb
emergency_fallback_peak_vram_mb
```

### Next priority: real measurement matrix

Keep the current matrix and replace proxy values cell by cell:

```text
Model axis:
  M0 shared backbone only
  M1 multiple full specialist models
  M2 shared backbone + oracle LoRA
  M3 shared backbone + taxonomy-routed LoRA
  M4 shared backbone + HydraLoRA/shared-factor bank

Visual axis:
  V0 full/fixed image
  V1 low-res only
  V2 FoveateR ROI
  V3 oracle ROI
V4 FoveateR ROI + controlled fallback
```

### Safety and compatibility

Keep arbitrary multi-LoRA composition out of runtime.

Runtime should use:

```text
certified adapters
certified bundles
top-1 or top-k with explicit compatibility gates
```

Simula's narrowed role is:

```text
offline adapter card calibration + compatibility certification compiler
```

## 5. Non-goals for the immediate reframe

Do not implement these as core requirements yet:

```text
- direct LeWM latent -> LoRA ID routing
- JEPA as runtime primary router
- graph memory commit loop
- runtime online LoRA training
- token-level LoRA switching
- arbitrary adapter mixing without certification
```

They can remain as exploratory or future work.

## 6. Active runner

```powershell
python scripts\run_3090_two_track_validation.py --config configs\3090_two_track_pilot.yaml --dry-run
```

## 7. Strong rule for claims

Separate these claims at all times:

```text
Resident VRAM reduction:
  must come from replacing multiple specialist backbones,
  using a smaller/quantized shared backbone,
  or compressing adapter residency.

Visual token / KV reduction:
  must come from FoveateR-style ROI evidence compression,
  not from LoRA itself.

End-to-end peak reduction:
  requires both tracks to be measured together,
  with normal path and emergency fallback peak reported separately.
```
