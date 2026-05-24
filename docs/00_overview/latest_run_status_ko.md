# Latest Run Status

Status: local validation status note
Updated: 2026-05-24

## 1. 현재 커밋된 상태

현재 repository에 커밋된 것은 다음이다.

```yaml
committed:
  docs: true
  configs: true
  schemas: true
  runner: true
  core_modules: true
  raw_run_artifacts_under_runs: false
```

`.local/runs/` 아래의 원본 실행 산출물은 로컬 검토용이며 git 추적 대상이 아니다. 공개 repo에는 재현 가능한 scaffold, schema, config, runner, claim boundary만 올린다. 커밋 산출물과 로컬 전용 산출물의 경계는 [local artifact boundary](local_artifact_boundary_ko.md)에 따로 정리한다.

## 2. 로컬에서 확인된 실행 상태

최근 로컬 실행 기준 상태는 다음과 같다.

```yaml
dry_run_available: true
real_cuda_smoke_available: true
real_task_image_smoke_available: true
controlled_tiny_real_task_validation_available: true
broad_real_task_validation_available: false
trained_lora_evaluation_available: false
tiny_trained_lora_smoke_available: true
answer_only_lora_label_mask_smoke_available: true
ocr_detector_roi_path_smoke_available: true
ocr_detector_n16_stability_smoke_available: true
ocr_detector_n32_cyclic_stability_smoke_available: true
measured_sequential_specialist_swap_smoke_available: true
measured_full_specialist_joint_residency_available: false
actual_peft_attach_smoke_available: true

local_only_reference_runs:
  - .local/runs/20260524T090102Z-3090_tiny_scored_validation
  - .local/runs/20260524T090206Z-3090_tiny_scored_validation
  - .local/runs/20260524T090316Z-3090_tiny_scored_validation
  - .local/runs/20260524T090422Z-specialist_swap_smoke
  - .local/runs/20260524T090446Z-actual_peft_smoke
  - .local/runs/20260524T095906Z-tiny_lora_train
  - .local/runs/20260524T095934Z-3090_tiny_scored_ocr_detector
  - .local/runs/20260524T095934Z-3090_tiny_scored_trained_lora_matrix_smoke
  - .local/runs/20260524T105236Z-tiny_lora_train
  - .local/runs/20260524T105259Z-3090_tiny_scored_trained_lora_matrix_smoke
  - .local/runs/20260524T105330Z-3090_tiny_scored_ocr_detector
  - .local/runs/20260524T105933Z-3090_tiny_scored_ocr_detector
  - .local/runs/20260524T080046Z-3090_two_track_pilot
  - .local/runs/20260524T072015Z-3090_two_track_pilot
  - .local/runs/20260524T062952Z-3090_two_track_pilot
```

최신 local-only run 묶음은 RTX 3090에서 Qwen3-VL-4B local snapshot을 실제 CUDA로 로드하고, `tiny_scored_manifest`의 controlled image task에서 ROI source별 C0-C7 matrix, normalized answer match score, p95 memory/token fields를 기록한 M-B~M-F initial measured validation pass다. 같은 커밋에서 sequential specialist swap baseline smoke와 actual PEFT attach smoke도 기록했다.

Git에 남긴 최신 요약문은 [docs/20_results/2026-05-24_scored_roi_swap_peft_validation_ko.md](../20_results/2026-05-24_scored_roi_swap_peft_validation_ko.md)이다.

```yaml
latest_scored_roi_validation:
  status: "initial_measured_validation_pass"
  final_milestone_closure: false
  runner_commit: "294b603"
  schema_version: "3090.combined_validation_result.v0.4"
  source_semantics_version: "v0.3"
  data_mode: "tiny_scored_manifest"
  samples_per_roi_source: 16
  matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
  roi_source_runs:
    center_crop: "20260524T090102Z-3090_tiny_scored_validation"
    oracle_box: "20260524T090206Z-3090_tiny_scored_validation"
    ocr_box_or_layout_box: "20260524T090316Z-3090_tiny_scored_validation"
  roi_source_naming_note: "ocr_box_or_layout_box is a legacy controlled layout proxy name, not an external OCR detector."
  c4_center_crop_score: 0.3125
  c4_oracle_box_score: 0.9375
  c4_ocr_layout_score: 0.9375
  c4_visual_token_count_mean: 296.0
  c3_visual_token_count_mean: 768.0
  c4_visual_token_reduction_vs_c3: 0.614583
  c6_low_res_score: 0.125
  c6_low_res_visual_tokens: 100.0
  c7_ocr_layout_score: 0.9375
  c7_visual_tokens: 296.0
  c7_controlled_fallback_peak_mb_all_samples_mean: 8962.519687
  c7_controlled_fallback_rate: 1.0
  task_score_source: "normalized_answer_match"
  actual_task_score_available_rate: 1.0
  specialist_swap_run: "20260524T090422Z-specialist_swap_smoke"
  actual_peft_run: "20260524T090446Z-actual_peft_smoke"
```

이 상태는 controlled tiny set에서의 실측 pass를 의미한다. 일반 benchmark 우월성, trained LoRA accuracy gain, 실제 OCR detector ROI, full specialist joint residency는 아직 검증된 상태가 아니다.

추가로 `a59c040` 작업면에서 RapidOCR 기반 `ocr_detector_box`와 tiny trained LoRA smoke를 실행했다. `ocr_detector_box` manifest는 20/20 detector boxes를 생성했고, n=4 real CUDA C0-C7 smoke에서 measurement gate를 통과했다. rank-4 q_proj/v_proj LoRA는 4 step 학습되어 `.local/adapters/tiny_lora_latest`에 저장됐고, C3/C4 matrix smoke에서 `adapter_memory_source=actual_loaded_adapter`로 로드됐다. 이는 학습/저장/로드 경로 smoke이며, trained LoRA accuracy gain claim은 여전히 열지 않는다.

```yaml
latest_ocr_detector_and_trained_lora_smoke:
  ocr_manifest_output: ".local/data/tiny_scored_manifest/manifest_ocr_detector.jsonl"
  ocr_detector_available: "20/20"
  ocr_detector_run: "20260524T095934Z-3090_tiny_scored_ocr_detector"
  ocr_detector_samples: 4
  ocr_detector_completion_gate: true
  ocr_detector_measurement_gate: true
  ocr_detector_c4_task_score_mean: 1.0
  ocr_detector_c4_visual_tokens: 296.0
  ocr_detector_c3_visual_tokens: 768.0
  ocr_detector_c6_low_res_task_score_mean: 0.0
  ocr_detector_c6_low_res_visual_tokens: 100.0
  ocr_detector_c7_task_score_mean: 1.0
  ocr_detector_c7_controlled_fallback_peak_mb_all_samples_mean: 8962.83075
  ocr_detector_c7_controlled_fallback_rate: 1.0
  tiny_lora_train_run: "20260524T095906Z-tiny_lora_train"
  latest_adapter_dir: ".local/adapters/tiny_lora_latest"
  tiny_lora_train_steps: 4
  tiny_lora_trainable_parameters: 1474560
  trained_lora_matrix_run: "20260524T095934Z-3090_tiny_scored_trained_lora_matrix_smoke"
  trained_lora_matrix_cells: [C3, C4]
  trained_lora_matrix_completion_gate: false
  trained_lora_matrix_completion_gate_reason: "C3/C4-only incomplete matrix by design"
  trained_lora_matrix_measurement_gate: true
  trained_lora_adapter_memory_source: "actual_loaded_adapter"
  trained_lora_accuracy_gain_claim: false
```

P1 follow-up에서는 answer-only label masking을 기본값으로 바꾸고, 새 tiny LoRA smoke와 C3/C4 actual PEFT load smoke를 다시 실행했다. 또한 OCR detector ROI를 n=16, 이후 n=32 requested C0-C7 run으로 올려 completion/measurement gate를 확인했다.

```yaml
p1_answer_mask_and_ocr_stability:
  result_brief: "docs/20_results/2026-05-24_p1_answer_mask_ocr_stability_ko.md"
  answer_only_lora_train_run: "20260524T105236Z-tiny_lora_train"
  answer_only_label_mask: true
  supervised_token_count_mean: 6.0
  answer_only_lora_losses: [0.061482, 0.0, 0.0, 0.000157]
  answer_only_trained_lora_matrix_run: "20260524T105259Z-3090_tiny_scored_trained_lora_matrix_smoke"
  answer_only_trained_lora_matrix_cells: [C3, C4]
  answer_only_trained_lora_matrix_measurement_gate: true
  ocr_detector_n16_run: "20260524T105330Z-3090_tiny_scored_ocr_detector"
  ocr_detector_n16_samples: 16
  ocr_detector_n16_completion_gate: true
  ocr_detector_n16_extended_completion_gate: true
  ocr_detector_n16_measurement_gate: true
  ocr_detector_n32_run: "20260524T105933Z-3090_tiny_scored_ocr_detector"
  ocr_detector_n32_requested_samples: 32
  ocr_detector_n32_unique_manifest_samples: 20
  ocr_detector_n32_sampling: "cyclic sample_for_index modulo manifest length"
  ocr_detector_n32_completion_gate: true
  ocr_detector_n32_extended_completion_gate: true
  ocr_detector_n32_measurement_gate: true
  ocr_detector_n32_c3_score: 0.9375
  ocr_detector_n32_c4_score: 0.90625
  ocr_detector_n32_c6_low_res_score: 0.125
  ocr_detector_n32_c7_score: 0.90625
  ocr_detector_n32_c4_visual_tokens: 296.0
  ocr_detector_n32_c3_visual_tokens: 768.0
  ocr_detector_n32_c4_controlled_fallback_all_samples_mean_mb: 8753.757844
  ocr_detector_n32_c7_controlled_fallback_all_samples_mean_mb: 8962.467844
  ocr_detector_n16_c3_score: 0.9375
  ocr_detector_n16_c4_score: 0.875
  ocr_detector_n16_c6_low_res_score: 0.125
  ocr_detector_n16_c7_score: 0.875
  ocr_detector_n16_c4_visual_tokens: 296.0
  ocr_detector_n16_c3_visual_tokens: 768.0
  ocr_detector_n16_c4_controlled_fallback_all_samples_mean_mb: 8753.809687
  ocr_detector_n16_c7_controlled_fallback_all_samples_mean_mb: 8962.519687
```

## 3. 현재 claim level

```yaml
current_claim_level:
  - scaffold
  - memory_accounting_smoke
  - real_task_image_smoke
  - controlled_tiny_real_task_validation
  - ocr_detector_roi_path_smoke
  - tiny_trained_lora_training_smoke
  - trained_lora_actual_peft_load_smoke
  - adapter_card_residency_estimate
  - multi_specialist_resident_estimate
  - sequential_specialist_swap_smoke
  - actual_peft_attach_smoke

not_yet_claimed:
  - trained_lora_accuracy_gain
  - measured_full_specialist_joint_residency
  - general_benchmark_accuracy
  - ocr_detector_roi_generalization
  - external_benchmark_ocr_detector_roi
  - trained_lora_generalization
  - production_latency_or_p99
  - final_milestone_closure_beyond_controlled_tiny_set
```

## 4. Proxy와 real measurement 구분

현재 run에는 real CUDA measurement와 proxy/estimate가 섞여 있다. 해석할 때는 다음을 우선한다.

```yaml
real_measurement:
  - base_after_load_allocated_mb
  - base_after_load_reserved_mb
  - visual_incremental_peak_mb in real CUDA mode
  - visual_token_count from qwen3_vl_image_grid_thw in real CUDA mode
  - real_task_manifest image path execution in real CUDA mode
  - source_semantics fields showing manifest image path and selected evidence paths
  - normalized_answer_match task score in tiny_scored_manifest runs
  - sequential specialist proxy load/unload latency in run_specialist_swap_smoke.py
  - actual PEFT attach memory delta and forward path in run_actual_peft_smoke.py
  - actual PEFT attach memory delta in C3/C4 matrix smoke only when adapter_memory_source=actual_loaded_adapter
  - ocr_detector_box when ocr_detector_available=true in manifest_ocr_detector.jsonl
  - tiny trained LoRA adapter load smoke when adapter_path points to .local/adapters/tiny_lora_latest

estimate_or_proxy:
  - adapter_bank_resident_mb from adapter cards
  - active_adapter_resident_mb from adapter cards
  - multi_specialist_resident_estimate_mb
  - task_score in synthetic_proxy or real_task_manifest smoke runs without expected_answers
  - verifier_score
  - roi quality and roi recall under center_crop or synthetic_probe mode
  - layout_proxy_box and detector_proxy_box until an external detector writes ocr_detector_box fields
  - trained LoRA accuracy gain until external or held-out evaluation is run
  - generate_extra_peak_over_prefill_mb as generate-minus-prefill proxy
```

### 4.1 아직 조심해야 할 부분

리서치 메모에서 지적한 주의점 중 현재 작업면에 남아 있는 것은 다음이다.

```yaml
still_cautious:
  - "OCR detector는 RapidOCR manifest 20/20 생성과 n=32 requested C0-C7 cyclic smoke까지 완료됐지만, 32개 고유 샘플 또는 repeats=3 안정성은 아직 아니다."
  - "tiny trained LoRA는 answer-only loss mask 학습/저장/로드 smoke가 완료됐지만, held-out 평가는 아직 아니다."
  - "trained LoRA matrix smoke는 의도적으로 C3/C4만 돌렸으므로 actual PEFT full C-matrix 검증으로 해석하지 않는다."
  - "C6/C7은 현재 DEFAULT_CELLS와 결과 산출물에 포함되어 있으나, 외부 benchmark claim으로 승격된 것은 아니다."
```

리서치 메모의 4번 항목을 현재 repo 기준으로 다시 대조하면 다음과 같다.

```yaml
research_caution_review:
  ocr_detector_stability:
    status: "advanced_to_n32_cyclic"
    action: "needs_next에는 repeats=3 또는 32개 이상 고유 샘플 manifest로 축소 유지"
  tiny_lora_label_mask:
    status: "implemented_and_smoked"
    action: "held-out evaluation은 needs_next에 유지"
  trained_lora_matrix_completion_gate_false:
    status: "clarified"
    action: "C3/C4-only incomplete matrix by design; measurement_gate=true"
  ocr_detector_roi_claim_name:
    status: "cleaned"
    action: "ocr_detector_roi_path_smoke와 ocr_detector_roi_generalization으로 분리"
  default_cells_c6_c7:
    status: "resolved"
    action: "DEFAULT_CELLS와 extended gate 모두 C0-C7 포함 확인"
```

반복 지적을 current repo 기준으로 다시 판정하면 다음과 같다.

```yaml
repeated_issue_audit:
  default_cells_c6_c7:
    verdict: "stale"
    current_evidence: "src/vfa_policy/core/validation_matrix.py DEFAULT_CELLS includes C0-C7"
  smoke_vs_promotion_claims:
    verdict: "real_risk"
    current_action: "path smoke, diagnostic measurement, promotion claim을 문서에서 분리"
  controlled_tiny_overclaim:
    verdict: "real_risk"
    current_action: "controlled tiny scored diagnostic set으로만 표현"
  roi_source_claim_drift:
    verdict: "real_risk"
    current_action: "center/oracle/layout_proxy/ocr_detector source taxonomy 유지"
  peft_path_vs_lora_gain:
    verdict: "real_risk"
    current_action: "actual PEFT load path와 accuracy gain을 분리"
  partial_matrix_gate:
    verdict: "real_risk"
    current_action: "partial matrix는 measurement smoke로 보고 full completion과 분리"
  qwen3_reference_backbone:
    verdict: "paper_scope_risk"
    current_action: "Qwen3-VL-4B는 reference/accounting anchor로 두고 lightweight sweep은 next work로 유지"
```

## 5. 다음 승격 조건

다음 단계는 방어 문구를 더 붙이는 것이 아니라, proxy를 실제 실험으로 하나씩 교체하는 것이다.

```yaml
next_promotion_steps:
  - repeat ocr_detector_box run with repeats=3 or 32+ unique samples
  - replace controlled tiny scored images with external benchmark or human-evaluated task set
  - evaluate trained LoRA weights on held-out or external samples, not only tiny training smoke
  - measure LoRA bank switch latency across multiple actual adapters
  - measure full specialist joint residency only on larger hardware, or keep it as an explicit estimate
```

리서치 메모의 `다음에 뭘 더 검증하면 좋을까` 항목은 아래 queue로 정리한다.

```yaml
next_validation_queue:
  - "ocr_detector_box repeats=3 또는 32개 이상 고유 샘플 manifest로 C0-C7 재실행"
  - "answer-only LoRA를 20~50 step으로 늘리고 tiny train/held-out split 분리"
  - "trained adapter를 actual_loaded_adapter로 로드한 full C-matrix 실행, 최소 C0/C3/C4/C5/C6/C7"
  - "외부 tiny benchmark subset 또는 사람이 검수한 hold-out image task로 score source 교체"
  - "accuracy gain claim은 held-out trained LoRA 평가가 통과한 뒤에만 개방"
```

## 6. 최종 체크리스트

```yaml
closed_for_current_milestone:
  - two-track research axis
  - active docs structure
  - local artifact boundary
  - result brief workflow
  - real CUDA memory/token accounting
  - DEFAULT_CELLS C0-C7 and minimum/extended completion gates
  - tiny scored normalized answer match
  - ROI source comparison
  - RapidOCR detector smoke
  - sequential specialist swap smoke
  - actual PEFT attach smoke
  - tiny trained LoRA save/load smoke
  - C6 low-res and C7 controlled fallback reporting in result briefs
  - answer-only LoRA label mask smoke
  - OCR detector n=16 C0-C7 stability smoke
  - OCR detector n=32 cyclic C0-C7 stability smoke

needs_next:
  - ocr_detector_box repeats=3 or 32+ unique-sample stability run
  - answer-only LoRA 20~50 step train/held-out evaluation
  - actual PEFT full C-matrix beyond C3/C4
  - external tiny benchmark subset
  - held-out trained LoRA evaluation before any accuracy-gain claim
```
