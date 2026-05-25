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

현재 Track A v2에서는 promotion gate를 더 엄격하게 둔다. path가 실행되는 것과 LoRA가 실제로 도움이 되는 것은 분리한다.

```yaml
track_a_v2_promotion_order:
  gate_1_single_lora_learns:
    meaning: "correct LoRA가 adapter-sensitive task에서 base보다 output을 개선하거나 적어도 train overfit을 보인다"
  gate_2_correct_beats_wrong:
    meaning: "correct adapter가 wrong/random adapter보다 heldout에서 유의하게 낫다"
  gate_3_router_selects_adapter:
    meaning: "oracle이 아니라 router가 adapter를 골라도 oracle adapter 성능에 가까워진다"
```

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

### A1 AdapterCard v2 gate

```yaml
completion_gate:
  - AdapterCard v2 fields are present
  - taxonomy has domain/evidence_type/operation/failure_mode
  - training and certification sections are separated

measurement_gate:
  - adapter memory and attach/switch latency fields are nullable but named
  - base/correct/wrong/random certification slots are present

promotion_gate:
  - not applicable until A3/A4 scores exist
```

### A2 Simula curriculum manifest gate

```yaml
completion_gate:
  - curriculum manifest is generated
  - teacher annotations are recorded with teacher_model
  - train/holdout split is explicit
  - hard negatives are present or explicitly unavailable

measurement_gate:
  - generated examples map to AdapterCard taxonomy
  - expected answers are present

promotion_gate:
  - not applicable; this is a compiler/input gate
```

### A3 Single LoRA learns gate

```yaml
completion_gate:
  - base and correct LoRA are both evaluated
  - train and holdout scores are both recorded

measurement_gate:
  - correct_lora_train_score > base_train_score
  - holdout score and loss are logged even when no gain appears

promotion_gate:
  - correct_lora_holdout_score >= base_holdout_score or a planned overfit-only smoke is explicitly labeled
```

### A4 Correct beats wrong/random gate

```yaml
completion_gate:
  - base/correct/wrong/random adapters are evaluated on the same heldout split

measurement_gate:
  - margin_vs_wrong is computed
  - wrong_adapter_damage is computed

promotion_gate:
  - correct_adapter_score > wrong_adapter_score + configured_margin
  - correct_adapter_score > random_adapter_score + configured_margin
```

### A5 Router selects adapter gate

```yaml
completion_gate:
  - oracle adapter and routed adapter scores are both available
  - router top1 hit is logged

measurement_gate:
  - routed_score is compared with oracle_adapter_score
  - wrong route cases are labeled

promotion_gate:
  - routed_score is close to oracle_adapter_score
  - router top1 hit beats random baseline
```

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
| Track A v2 reframe | Simula/Gemma teacher loop is the new paper axis | current results already prove LoRA utility |
| AdapterCard v2 | adapter certification fields are defined | adapter is certified before scores exist |
| Single LoRA learns | correct LoRA can affect adapter-sensitive task output if gate passes | trained LoRA improves accuracy in general |
| Correct vs wrong/random | taxonomy creates adapter-specific utility if margin appears | multi-adapter routing improves accuracy before margin |
| Router gate | routed adapter can be promoted only after oracle/correct gap is bounded | oracle adapter score is a routing result |
| Track B ROI results | ROI path controls visual evidence cost | Track B is the main novelty |
| Stage 1 smoke | foveated path can reduce token/path cost in a smoke profiler | final VLM peak VRAM solved |
| Stage 1+ Qwen3-VL protocol | unified trace and proxy routing are measurable | trained LoRA improves accuracy |
| R1/R2 resident comparison | shared backbone + adapter bank residency can be measured | LoRA alone shrinks a single full backbone |
| R3 FoveateR ROI | visual tokens/KV/prefill can be reduced | resident backbone memory reduced |
| Combined C4 | diagnostic normal path works under 3090 budget | production p99 serving solved |
