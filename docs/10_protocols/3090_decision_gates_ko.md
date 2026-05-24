# RTX 3090 Decision Gates

Status: pass/fail gate definition

## 1. Gate classes

검증 결과는 하나의 pass/fail로 판단하지 않는다.

```yaml
gates:
  completion_gate:
    meaning: script ran and required artifacts were produced
  measurement_gate:
    meaning: relevant metrics were measured with correct claim boundary
  promotion_gate:
    meaning: method is good enough to become part of the main runtime path
```

Stage 1+ 같은 exploratory run은 completion/measurement는 pass해도 promotion은 fail일 수 있다.

completion gate는 두 층으로 나눈다.

```yaml
minimum_completion_gate:
  required_cells: [C0, C1, C2, C3, C4, C5]
  role: "기본 two-track matrix가 실행됐는지 확인"

extended_completion_gate:
  required_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
  role: "소논문 표에 넣을 low-res only와 controlled fallback path까지 포함됐는지 확인"
```

하위 호환을 위해 top-level `completion_gate`는 minimum gate와 같은 의미로 유지한다. 소논문용 결과 표에는 extended gate를 함께 보고한다.

부분 matrix smoke는 full completion으로 해석하지 않는다. `allow_incomplete_matrix=true`인 config는 요청된 subset이 제대로 측정됐는지 확인하는 measurement smoke이며, full C-matrix 검증과 따로 기록한다.

```yaml
full_matrix_completion_gate:
  required_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
  use_for: "paper table or milestone completion"

partial_matrix_measurement_gate:
  required_cells: "config.combined_matrix.cells"
  use_for: "actual PEFT attach/load path smoke or targeted diagnostic"
  safe_claim: "requested subset was measured with the stated adapter/source semantics"
  unsafe_claim: "full C-matrix is complete"
```

## 2. Resident compression gates

### R1 multi-specialist baseline gate

```yaml
completion_gate:
  - per-specialist memory measured or estimated
  - joint resident estimate computed
  - sequential load/swap latency logged

measurement_gate:
  - fits_in_24gb recorded
  - model load latency recorded

promotion_gate:
  - not applicable; this is a baseline
```

### R2 shared backbone + LoRA gate

```yaml
completion_gate:
  - shared backbone memory logged
  - adapter bank memory logged
  - at least one adapter selection path logged

measurement_gate:
  - resident_saving_vs_multi_specialist computed
  - lora_switch_latency compared with model_swap_latency
  - wrong_adapter_damage measured

promotion_gate:
  - resident_saving_vs_multi_specialist > 0
  - lora_switch_latency_ms < model_swap_latency_ms
  - score_retention_vs_oracle_lora >= configured threshold
```

## 3. Visual evidence compression gates

### R3 FoveateR-style ROI gate

```yaml
completion_gate:
  - full image baseline logged
  - low-res baseline logged
  - foveated ROI path logged
  - oracle ROI upper bound logged when available

measurement_gate:
  - visual_token_reduction_vs_full computed
  - incremental visual peak reduction computed or explicitly unavailable
  - ROI quality metrics logged

promotion_gate:
  - foveated_visual_tokens < full_visual_tokens
  - task_score_drop <= configured tolerance or controlled fallback recovers
  - fullres fallback rate is not excessive
```

## 4. Combined two-track gate

```yaml
completion_gate:
  - C0, C1, C2, C3, C4 are logged
  - C5 oracle ROI is logged when available
  - C6 low-res only and C7 controlled fallback are logged when the active config includes them

measurement_gate:
  - resident and visual metrics are separately computed
  - normal path peak is separated from fallback peak
  - source semantics record which fields are real measurements and which are proxy or estimate

promotion_gate:
  - C4 normal path is under 3090 memory budget
  - C4 reduces visual tokens vs C3
  - C4 uses less resident memory than multi-specialist estimate
  - C4 quality is within tolerance of oracle or full baseline
```

## 5. Fallback gates

Fallback is not a single loop success metric. It is a budget-tier accounting mechanism.

```yaml
fallback_gate:
  pass_if:
    - fallback_tier is recorded
    - normal_path_peak is not overwritten by emergency fallback peak
    - controlled fallback conditional mean and all-sample mean are separated
    - controlled_fallback_rate is reported
    - terminal model errors are not quarantined as unsafe adapter failures
    - tier2 emergency rate is reported separately
```

## 6. Stop conditions

Stop and redesign if any of the following happens.

```yaml
stop_conditions:
  - base_after_load memory is not measured
  - all claimed VRAM savings come only from token count estimates
  - foveated ROI hurts quality and fallback rate is high
  - taxonomy router uses dataset_alias or oracle labels in main path
  - JEPA/LeWM proxy is promoted despite worse regret than taxonomy baseline
  - terminal model errors are counted as adapter quarantine
```

## 7. Claim table

| Evidence | Safe claim | Unsafe claim |
|---|---|---|
| Stage 1 smoke | foveated path can reduce token/path cost in a smoke profiler | final VLM peak VRAM solved |
| Stage 1+ Qwen3-VL protocol | unified trace and proxy routing are measurable | trained LoRA improves accuracy |
| R1/R2 resident comparison | shared backbone + adapter bank reduces specialist residency | LoRA alone shrinks a single full backbone |
| R3 FoveateR ROI | visual tokens/KV/prefill can be reduced | resident backbone memory reduced |
| Combined C4 | two-track normal path works under 3090 budget | production p99 serving solved |
