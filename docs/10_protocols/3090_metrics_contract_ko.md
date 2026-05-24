# RTX 3090 Metrics Contract

Status: metric contract
Purpose: RouteTrace와 summary가 반드시 남겨야 하는 필드를 정의한다.

## 1. Memory breakdown

단일 `peak_vram_mb`만 기록하지 않는다. 최소한 다음을 분리한다.

```yaml
memory:
  base_after_load_allocated_mb: null
  base_after_load_reserved_mb: null
  adapter_bank_resident_mb: null
  active_adapter_resident_mb: null
  visual_incremental_peak_mb: null
  decode_incremental_peak_mb: null
  generate_extra_peak_over_prefill_mb: null
  decode_incremental_peak_source: generate_minus_prefill_proxy_not_true_decode_only
  total_peak_mb: null
  normal_path_peak_mb: null
  controlled_fallback_peak_mb: null
  emergency_fallback_peak_mb: null
```

## 2. Derived ratios

```yaml
derived:
  base_resident_ratio: base_after_load_allocated_mb / total_peak_mb
  resident_saving_vs_multi_specialist: 1 - shared_plus_lora_resident_mb / multi_specialist_resident_estimate_mb
  visual_token_reduction_vs_full: 1 - foveated_visual_tokens / full_visual_tokens
  incremental_visual_peak_reduction_vs_full: 1 - foveated_incremental_peak_mb / full_incremental_peak_mb
```

## 3. Visual evidence metrics

```yaml
visual:
  visual_policy: full_image | low_res_only | foveater_roi | oracle_roi | foveater_roi_controlled_fallback
  visual_token_count: null
  global_token_count: null
  roi_token_count: null
  roi_count: null
  roi_recall_at_1: null
  roi_recall_at_k: null
  roi_miss_rate: null
  wrong_crop_distraction: null
  kv_cache_estimate_mb: null
  kv_cache_estimate_source: heuristic_mb_per_visual_token | calibrated_model_formula
  kv_cache_mb_per_token: null
  kv_cache_calibrated: false
  prefill_latency_ms: null
```

## 4. Model residency metrics

```yaml
residency:
  model_residency_mode: shared_backbone | multi_specialist_estimate | sequential_specialist_swap
  shared_backbone_after_load_mb: null
  specialist_model_after_load_mb: null
  multi_specialist_resident_estimate_mb: null
  fits_in_24gb: null
  model_load_latency_ms: null
  model_swap_latency_ms: null
  lora_switch_latency_ms: null
  adapter_bank_resident_mb: null
  active_adapter_count: null
```

## 5. Quality metrics

```yaml
quality:
  task_score: null
  answer_correct: null
  score_retention_vs_oracle_lora: null
  score_retention_vs_full_specialist: null
  score_gain_vs_shared_backbone_only: null
  verifier_score: null
  verifier_pass: null
  confidence: null
  confidence_source: proxy_score_no_ground_truth | answer_match | model_logit | external_verifier | none
  task_score_source: synthetic_proxy | normalized_answer_match | benchmark_label | human_eval | external_verifier
  actual_task_score_available: false
  answer_type: text | number | label | yes_no | null
  expected_answer_count: null
  matched_expected_answer: null
```

## 6. Routing and compatibility metrics

```yaml
routing:
  router_type: none | oracle | taxonomy_card | taxonomy_cost | foveater_guided | future_jepa
  selected_adapter_ids: []
  selected_roi_id: null
  top1_route_hit: null
  top3_route_hit: null
  abstained: false
  wrong_route: false
  wrong_adapter_damage: null
  wrong_adapter_confidence_gain: null
  adapter_conflict_rate: null
  certified_bundle: null
```

## 7. Fallback tier metrics

```yaml
fallback:
  fallback_tier: none | tier0_in_budget | tier1_controlled_expensive | tier2_emergency
  fallback_evaluated: false
  fallback_executed: false
  fallback_success: false
  terminal_reason: null
  visited_actions: []
```

fallback peak summary는 다음 세 값을 구분한다.

```yaml
fallback_summary:
  controlled_fallback_peak_mb_conditional_mean:
    meaning: "tier1 controlled fallback이 실제 실행된 샘플만 평균"
  controlled_fallback_peak_mb_all_samples_mean:
    meaning: "fallback이 없는 샘플은 normal_path_peak_mb로 채워 전체 샘플 기준 평균"
  controlled_fallback_rate:
    meaning: "tier1 controlled fallback이 실제 실행된 샘플 비율"
```

기존 `controlled_fallback_peak_mb_mean`은 호환성을 위해 유지하되, 새 분석에서는 `controlled_fallback_peak_mb_conditional_mean`을 우선 읽는다.

## 8. Failure labels

Use these labels consistently.

```yaml
failure_types:
  roi_miss: important ROI was not selected
  wrong_crop_distraction: crop hurt answer quality
  wrong_adapter_damage: wrong adapter reduced quality
  wrong_adapter_confidence_gain: wrong adapter increased confidence while wrong
  adapter_conflict: adapter bundle produced conflicting behavior
  budget_violation: memory or latency budget exceeded
  verifier_false_pass: verifier accepted bad evidence
  verifier_false_reject: verifier rejected acceptable evidence
  terminal_model_error: model failed even at fallback boundary
  no_fallback_available: no distinct fallback exists
  unresolved: failure is not attributable to route or adapter
```

`terminal_model_error`, `no_fallback_available`, and `unresolved` should usually produce `reject`, not `quarantine`.

## 9. Source semantics

각 trace는 어떤 값이 실측이고, 어떤 값이 proxy 또는 estimate인지 반드시 분리한다.

```yaml
source:
  memory_source: qwen3_vl_4b_local_cuda_prefill_generate | dry_run_config_estimate
  visual_token_source: qwen3_vl_image_grid_thw | dry_run_visual_estimate
  quality_source: synthetic_proxy | normalized_answer_match | benchmark_label | human_eval | external_verifier
  task_score_source: synthetic_proxy | normalized_answer_match | benchmark_label | human_eval | external_verifier
  adapter_memory_source: adapter_card_estimate | measured_adapter_residency
  adapter_execution_mode: shared_backbone_only | proxy_card_accounting | actual_peft | merged_lora
  roi_source: synthetic_probe | center_crop | oracle_box | ocr_box_or_layout_box | foveater_model
  data_mode: synthetic_probe | stage1_smoke_manifest | real_task_manifest | tiny_scored_manifest
  image_source: dry_run_config_estimate | synthetic_probe_generated_images | manifest.full_image_path | manifest.metadata_only_dry_run
  actual_image_execution: false
  manifest_sample_id: null
  manifest_full_image_path: null
  source_dataset: null
  source_url: null
  task_family: null
  answer_type: null
  prepared_full_image_path: null
  prepared_low_res_path: null
  prepared_roi_path: null
  selected_image_paths: []
  roi_box_rel_xyxy: null
  roi_box_xyxy: null
  target_box_rel_xyxy: null
  target_box_xyxy: null
  roi_target_iou: null
  roi_contains_target_evidence: null
  evidence_preparation: null
  task_validation_level: smoke_or_proxy | stage1_image_smoke | real_task_image_smoke | real_task_validation
  source_semantics_version: v0.3
  real_measurement_fields: []
  estimate_or_proxy_fields: []
```

`decode_incremental_peak_mb`는 호환성을 위해 유지하지만, 현재 구현에서는 순수 decode-only가 아니다.
실제 의미상 `generate_extra_peak_over_prefill_mb`를 우선 읽는다.

`actual_image_execution=true`는 manifest metadata를 단순히 읽었다는 뜻이 아니라, 해당 row의 `full_image_path`에서 실제 이미지를 열고 full/low-res/ROI evidence image를 만들어 real CUDA probe에 전달했다는 뜻이다.
반대로 quality score가 `synthetic_proxy`이면, 같은 run에서 실제 이미지와 실제 CUDA memory를 썼더라도 task accuracy claim으로 승격하지 않는다.

## 10. Summary CSV required columns

```text
run_id
stage
matrix_cell
model_residency_mode
visual_policy
n_samples
task_score_mean
task_score_std
proxy_task_score_mean
task_score_source
actual_task_score_available_rate
normal_path_peak_mb_mean
normal_path_peak_mb_p95
controlled_fallback_peak_mb_mean
controlled_fallback_peak_mb_conditional_mean
controlled_fallback_peak_mb_conditional_p95
controlled_fallback_peak_mb_all_samples_mean
controlled_fallback_peak_mb_all_samples_p95
controlled_fallback_rate
fallback_rate
emergency_peak_mb_mean
base_after_load_allocated_mb_mean
adapter_bank_resident_mb_mean
visual_incremental_peak_mb_mean
visual_incremental_peak_mb_p95
visual_token_count_mean
visual_token_count_p95
kv_cache_estimate_mb_mean
prefill_latency_ms_p95
mode_switch_latency_ms_p95
lora_switch_latency_ms_p95
fallback_tier0_rate
fallback_tier1_rate
fallback_tier2_rate
wrong_adapter_damage_rate
quarantine_count
reject_count
```
