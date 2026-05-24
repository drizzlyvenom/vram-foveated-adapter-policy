# 2026-05-24 P1 Answer Mask / OCR Detector n=32 Stability

## 요약

`e433807` 작업면에서 리서치 P1 지적 중 세 항목을 확인했다. 첫째, tiny LoRA training은 answer-only label masking을 기본값으로 바꾸고 4-step smoke를 다시 실행했다. 둘째, 새 adapter를 C3/C4 actual PEFT matrix smoke에 로드해 경로가 깨지지 않았음을 확인했다. 셋째, OCR detector ROI를 n=32 C0-C7 real CUDA run으로 올려 measurement gate를 다시 통과시켰다.

이 결과는 여전히 controlled tiny diagnostic set의 P1 smoke다. trained LoRA accuracy gain, external benchmark generalization, production p95/p99는 주장하지 않는다.

```yaml
status:
  answer_only_lora_label_mask: "implemented and smoke-tested"
  tiny_lora_train_run: "20260524T105236Z-tiny_lora_train"
  trained_lora_matrix_smoke_run: "20260524T105259Z-3090_tiny_scored_trained_lora_matrix_smoke"
  ocr_detector_n16_run: "20260524T105330Z-3090_tiny_scored_ocr_detector"
  ocr_detector_n32_run: "20260524T105933Z-3090_tiny_scored_ocr_detector"
  ocr_detector_n32_sampling_note: "32 requested inferences over 20 unique manifest samples by cyclic indexing"
  fallback_summary_fields: "conditional and all-sample fields already present and populated"

claim_boundary:
  controlled_tiny_diagnostic: true
  trained_lora_accuracy_gain: false
  external_benchmark_claim: false
  production_p95_p99: false
```

## Answer-Only Tiny LoRA Smoke

`train_tiny_lora_smoke.py`는 이제 기본적으로 prompt/system/image token을 label `-100`으로 mask하고 assistant answer span만 supervised token으로 남긴다. 과거 동작 재현이 필요하면 `--label-mask-mode full_sequence_except_pad`를 명시할 수 있다.

```yaml
run_id: "20260524T105236Z-tiny_lora_train"
label_mask_mode: "answer_only"
supervised_token_count_mean: 6.0
input_token_count_mean: 327.0
prompt_token_count_mean: 321.0
train_steps: 4
trainable_lora_parameters: 1474560
peft_allocated_delta_mb: 5.625
train_peak_allocated_mb: 9232.653
losses: [0.061482, 0.0, 0.0, 0.000157]
```

해석:

```yaml
safe:
  - "tiny LoRA training script가 answer-only label mask를 적용하고 adapter를 저장했다."
  - "결과 JSON에 label_mask_mode와 supervised token count가 기록된다."

not_yet:
  - "trained LoRA가 정확도를 향상했다."
  - "20~50 step overfit/held-out split 평가가 끝났다."
```

## Trained Adapter Load Smoke

새 answer-only adapter를 `.local/adapters/tiny_lora_latest`로 저장한 뒤, 기존 C3/C4-only matrix smoke로 actual PEFT load path를 다시 확인했다.

```yaml
run_id: "20260524T105259Z-3090_tiny_scored_trained_lora_matrix_smoke"
matrix_cells: [C3, C4]
adapter_memory_source: "actual_loaded_adapter"
adapter_execution_mode: "actual_peft"
completion_gate: false
completion_gate_reason: "C3/C4-only incomplete matrix by design"
measurement_gate: true

C3_trained_lora_full_image:
  task_score_mean: 1.0
  visual_token_count_mean: 768.0
  normal_path_peak_mb_mean: 8896.8105

C4_trained_lora_ocr_detector_roi:
  task_score_mean: 1.0
  visual_token_count_mean: 296.0
  normal_path_peak_mb_mean: 8617.761
  controlled_fallback_rate: 0.25
```

## OCR Detector n=32 C0-C7 Stability Smoke

OCR detector ROI run을 n=4에서 n=16, 다시 n=32로 올렸다. 현재 committed brief의 대표 수치는 n=32 run을 사용한다. 단, manifest는 20개 샘플이므로 n=32는 20개 고유 샘플을 모두 한 번 사용한 뒤 앞쪽 12개를 순환 재사용한 32 inference 안정성 smoke다.

```yaml
run_id: "20260524T105933Z-3090_tiny_scored_ocr_detector"
samples_requested: 32
unique_manifest_samples: 20
sampling: "cyclic sample_for_index modulo manifest length"
matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
completion_gate: true
minimum_completion_gate: true
extended_completion_gate: true
measurement_gate: true
promotion_gate: false
task_score_source: "normalized_answer_match"
actual_task_score_available_rate: 1.0
```

핵심 수치:

| Cell | Visual policy | Score mean | Score std | Visual tokens | Normal peak MB mean | Fallback rate |
|---|---|---:|---:|---:|---:|---:|
| C3 | full_image | 0.9375 | 0.242061 | 768.0 | 8962.481406 | 0.0 |
| C4 | foveater_roi | 0.90625 | 0.291481 | 296.0 | 8684.136 | 0.25 |
| C6 | low_res_only | 0.1250 | 0.330719 | 100.0 | 8593.007 | 0.0 |
| C7 | foveater_roi_controlled_fallback | 0.90625 | 0.291481 | 296.0 | 8684.136 | 1.0 |

Fallback summary:

```yaml
C4_controlled_fallback:
  conditional_mean_mb: 8962.623375
  conditional_p95_mb: 8963.49435
  all_samples_mean_mb: 8753.757844
  all_samples_p95_mb: 8962.416
  fallback_rate: 0.25

C7_controlled_fallback:
  conditional_mean_mb: 8962.467844
  conditional_p95_mb: 8962.416
  all_samples_mean_mb: 8962.467844
  all_samples_p95_mb: 8962.416
  fallback_rate: 1.0
```

해석:

```yaml
safe:
  - "OCR detector ROI path는 n=32 requested inference controlled tiny diagnostic run에서 C0-C7 completion/measurement gate를 통과했다."
  - "C4는 C3 대비 visual tokens를 768에서 296으로 줄였고, score mean은 0.9375에서 0.90625로 낮아졌다."
  - "low-res only C6는 visual tokens 100으로 가장 낮지만 score mean 0.1250으로 크게 떨어졌다."
  - "controlled fallback conditional/all-sample peak fields가 summary에 채워졌다."

not_yet:
  - "32개 고유 샘플 또는 repeats=3 안정성이 끝났다."
  - "OCR detector ROI가 oracle을 안정적으로 대체한다."
  - "external benchmark에서도 같은 경향이 유지된다."
```

## 다음 단계

```yaml
needs_next:
  - "OCR detector repeats=3 stability run 또는 32개 이상 고유 샘플 manifest"
  - "answer-only LoRA 20~50 step train/hold-out split"
  - "trained adapter actual PEFT full C-matrix, 최소 C0/C3/C4/C5/C6/C7"
  - "external tiny benchmark subset"
```
