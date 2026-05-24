# Combined Validation Matrix

Status: core experiment design
Purpose: verify resident specialist compression and visual evidence compression separately and jointly.

## 1. Why a matrix is needed

The previous ladder-style validation mixed many mechanisms into one sequence. The new plan uses a two-axis matrix:

```text
Axis M: model residency strategy
Axis V: visual evidence strategy
```

This makes it clear whether a gain comes from LoRA consolidation, FoveateR compression, or their combination.

## 2. Axis M: model residency strategy

| ID | Name | Description | Primary question |
|---|---|---|---|
| M0 | shared backbone only | one general VLM without specialist LoRA | baseline quality/memory |
| M1 | multiple full specialists | separate full models for document/OCR/UI/chart/etc. | expensive upper-bound baseline |
| M2 | shared backbone + oracle LoRA | correct specialist LoRA selected by label/oracle | adapter upper bound |
| M3 | shared backbone + taxonomy-routed LoRA | LoRA selected by taxonomy/card router | proposed runtime path |
| M4 | shared backbone + HydraLoRA/shared-factor bank | compressed adapter bank variant | adapter resident memory reduction |
| M5 | shared backbone + certified LoRA bundle | only compatibility-certified adapter bundles | collapse-control variant |

### Notes

- M1 may be simulated if multiple full specialist models cannot be loaded jointly on the target GPU.
- If M1 cannot be resident, record it as `resident_impossible=true` and measure sequential model swap latency.
- M2 is not a deployable policy; it is the upper bound for adapter specialization.
- M3 is the first deployable policy.
- M4 should not be tested before M2/M3 establish adapter usefulness.

## 3. Axis V: visual evidence strategy

| ID | Name | Description | Primary question |
|---|---|---|---|
| V0 | full/fixed image | full-resolution or fixed high-res image input | full visual context baseline |
| V1 | low-res only | only low-resolution global view | low-cost lower-bound |
| V2 | FoveateR ROI | low-res global + learned ROI glimpse | proposed foveation path |
| V3 | oracle ROI | low-res global + oracle/high-quality ROI | ROI upper bound |
| V4 | FoveateR ROI + controlled fallback | ROI path with in-budget retry/fullres fallback tier | robust deployment path |

### Notes

- V3 is needed to decide whether better ROI selection is worth pursuing.
- If V3 does not improve over V0 or V1, ROI research should be deprioritized.
- If V3 is strong but V2 is weak, the bottleneck is ROI policy quality.
- If V2 is strong, FoveateR is justified as a core component.

## 4. Minimum experiment grid

Start with this small grid:

| Experiment | Model strategy | Visual strategy | Purpose |
|---|---|---|---|
| E00 | M0 | V0 | shared backbone full-image baseline |
| E01 | M0 | V2 | FoveateR alone effect |
| E02 | M1 | V0 | multi-specialist full-model baseline |
| E03 | M2 | V0 | oracle LoRA specialist upper bound |
| E04 | M3 | V0 | taxonomy LoRA consolidation effect |
| E05 | M3 | V2 | proposed combined system |
| E06 | M3 | V3 | ROI upper bound with routed LoRA |
| E07 | M4 | V2 | compressed adapter bank + foveation |

This is enough to answer:

```text
- Does LoRA consolidation reduce resident memory vs multiple specialist models?
- Does FoveateR reduce visual tokens/KV cost?
- Does the combined system improve normal-path memory/latency?
- Does taxonomy routing approach oracle LoRA routing?
- Does FoveateR approach oracle ROI?
```

## 5. Primary metrics

### Resident compression metrics

```yaml
resident_vram:
  - multi_specialist_resident_mb
  - shared_backbone_resident_mb
  - adapter_bank_resident_mb
  - total_resident_reduction_ratio
  - resident_impossible_count

switching:
  - model_swap_latency_ms
  - lora_switch_latency_ms
  - mode_switch_speedup
```

### Visual evidence metrics

```yaml
visual_evidence:
  - visual_token_count
  - roi_token_count
  - kv_cache_estimate_mb
  - prefill_latency_ms
  - incremental_visual_peak_mb
  - roi_recall_at_k
  - roi_miss_rate
  - wrong_crop_distraction_rate
  - fullres_fallback_rate
```

### Quality metrics

```yaml
quality:
  - task_score
  - score_retention_vs_full_specialist
  - score_gain_vs_shared_backbone_only
  - score_drop_vs_oracle_lora
  - score_drop_vs_oracle_roi
```

### Safety metrics

```yaml
safety:
  - wrong_adapter_damage
  - wrong_adapter_confidence_gain
  - adapter_conflict_rate
  - verifier_false_pass_rate
  - verifier_false_reject_rate
  - quarantine_rate
```

## 6. Promotion gates

### Track A promotion gate

Shared-backbone LoRA consolidation is promoted when:

```text
resident_vram_reduction_ratio is substantial
AND score_retention_vs_full_specialist is acceptable
AND lora_switch_latency << model_swap_latency
AND wrong_adapter_damage is controlled
```

### Track B promotion gate

FoveateR visual evidence compression is promoted when:

```text
visual_token_count is significantly lower than full image
AND incremental_visual_peak_mb is lower
AND task_score is close to V0 or V3
AND ROI miss/fallback rate is acceptable
```

### Combined system promotion gate

The combined system is promoted when:

```text
M3/M4 + V2 improves normal-path resident+visual cost
AND task quality remains acceptable
AND emergency fallback peak is reported separately
```

## 7. Important reporting rule

Always report these separately:

```text
normal_path_peak_vram_mb
controlled_fallback_peak_vram_mb
emergency_peak_vram_mb
```

Do not let fullres or full-specialist emergency fallback hide the normal-path savings.
