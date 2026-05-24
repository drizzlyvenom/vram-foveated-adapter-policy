# RTX 3090 실행 Ladder

Status: execution ladder
Purpose: 3090에서 어떤 순서로 검증할지 정의한다.

## Ladder overview

```text
R0. Memory accounting smoke
R1. Multi-specialist residency baseline
R2. Shared backbone + LoRA bank baseline
R3. FoveateR-style visual evidence compression
R4. Combined two-track pilot
R5. Compatibility and collapse instrumentation
```

## R0. Memory accounting smoke

### Goal

모델을 바꾸기 전에 memory metric이 제대로 분리되는지 확인한다.

### Required measurements

```yaml
base_after_load_allocated_mb: required
base_after_load_reserved_mb: required
visual_incremental_peak_mb: required
decode_incremental_peak_mb: optional
total_peak_mb: required
```

### Pass condition

```yaml
pass_if:
  - base_after_load memory is recorded
  - total peak is recorded
  - incremental visual peak can be computed
  - measurement source is marked
```

### Failure meaning

R0가 실패하면 모델 구조를 수정하지 않는다. 먼저 profiler/logging을 고친다.

## R1. Multi-specialist residency baseline

### Goal

여러 full specialist VLM을 사용하는 baseline의 resident memory와 swap latency를 측정하거나 추정한다.

### Baselines

```yaml
M1_joint_estimate:
  description: sum of resident memory for specialist models

M1_sequential_swap:
  description: load one specialist, unload, load another specialist
```

### Metrics

```yaml
metrics:
  - specialist_model_count
  - per_model_after_load_allocated_mb
  - joint_resident_estimate_mb
  - fits_in_24gb
  - model_load_latency_ms
  - model_swap_latency_ms
```

### Pass condition

```yaml
pass_if:
  - at least one specialist model memory is measured
  - joint estimate is computed
  - sequential load/swap latency is logged
```

## R2. Shared backbone + LoRA bank baseline

### Goal

하나의 shared backbone과 LoRA bank가 resident memory와 mode switch cost를 줄이는지 확인한다.

### Baselines

```yaml
M0_shared_backbone_only: base model only
M2_shared_backbone_oracle_lora: selected specialist adapter by oracle label
M3_shared_backbone_taxonomy_lora: selected specialist adapter by taxonomy router
M4_hydralora_estimate: shared-factor adapter memory estimate
```

### Metrics

```yaml
metrics:
  - shared_backbone_after_load_allocated_mb
  - adapter_bank_resident_mb
  - active_adapter_count
  - lora_switch_latency_ms
  - resident_saving_vs_multi_specialist
  - task_score_retention_vs_oracle
  - wrong_adapter_damage
```

### Pass condition

```yaml
pass_if:
  - shared_backbone_plus_adapter_bank memory is below multi-specialist estimate
  - LoRA switch/proxy switch is cheaper than model reload/swap
  - wrong adapter damage is measured, even if proxy-only
```

## R3. FoveateR-style visual evidence compression

### Goal

full high-resolution visual context 대신 low-res global + ROI glimpse가 visual token/KV/prefill 비용을 줄이는지 확인한다.

### Baselines

```yaml
V0_full_fixed_image: full image / full high-res visual context
V1_low_res_only: low-cost lower bound
V2_foveater_roi: FoveateR-style ROI glimpse
V3_oracle_roi: upper bound
V4_foveater_roi_controlled_fallback: practical robust path
```

### Metrics

```yaml
metrics:
  - visual_token_count
  - roi_token_count
  - kv_cache_estimate_mb
  - prefill_latency_ms
  - visual_incremental_peak_mb
  - roi_recall
  - roi_miss_rate
  - wrong_crop_distraction_rate
  - fullres_fallback_rate
```

### Pass condition

```yaml
pass_if:
  - V2 visual tokens < V0 visual tokens
  - V2 incremental visual peak <= V0 incremental visual peak
  - answer score drop is bounded or fallback is logged
  - V3 oracle ROI upper bound is measured when possible
```

## R4. Combined two-track pilot

### Goal

Track A와 Track B를 같이 적용했을 때 normal path가 resident memory와 visual evidence cost 양쪽에서 이득을 보이는지 확인한다.

### Minimum matrix

```text
C0 = M0 + V0
C1 = M0 + V2
C2 = M2 + V0
C3 = M3 + V0
C4 = M3 + V2
C5 = M3 + V3
```

### Metrics

```yaml
metrics:
  - normal_path_peak_mb
  - resident_saving_vs_multi_specialist
  - visual_token_reduction_vs_full_image
  - prefill_latency_reduction_vs_full_image
  - score_retention_vs_oracle_lora_or_full_specialist
  - fallback_tier_distribution
```

### Pass condition

```yaml
pass_if:
  - C4 reduces visual tokens vs C3
  - C4 uses shared backbone + adapter bank memory rather than multi-specialist residency
  - C4 normal path is under 3090 budget
  - fallback tiers are reported separately
```

## R5. Compatibility and collapse instrumentation

### Goal

작은 LoRA 여러 개를 쓸 때 routing/collapse 위험을 기록한다.

### Metrics

```yaml
metrics:
  - wrong_adapter_damage
  - wrong_adapter_confidence_gain
  - adapter_conflict_rate
  - certified_bundle_hit
  - quarantine_count
  - reject_count
```

### Pass condition

```yaml
pass_if:
  - wrong adapter tests are logged
  - unsafe routes are not silently committed
  - terminal model errors are reject/unresolved, not quarantine
```
