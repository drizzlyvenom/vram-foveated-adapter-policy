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
trained_lora_evaluation_available: true
tiny_trained_lora_smoke_available: true
answer_only_lora_label_mask_smoke_available: true
ocr_detector_roi_path_smoke_available: true
ocr_detector_n16_stability_smoke_available: true
ocr_detector_n32_cyclic_stability_smoke_available: true
ocr_detector_unique64_repeats3_stability_available: true
measured_sequential_specialist_swap_smoke_available: true
measured_full_specialist_joint_residency_available: false
actual_peft_attach_smoke_available: true
actual_peft_full_cmatrix_available: true
external_tiny_manifest_available: true
external_tiny_n32_validation_available: true
actual_peft_external_baseline_comparison_available: true
multi_trained_lora_bank_smoke_available: true
lightweight_backbone_sweep_available: true

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
  - .local/runs/20260524T114337Z-tiny_lora_train
  - .local/runs/20260524T114456Z-3090_tiny_scored_trained_lora_full_cmatrix
  - .local/runs/20260525T005611Z-3090_external_tiny_ocr_detector_n32
  - .local/runs/20260525T005917Z-3090_external_tiny_trained_lora_n32
  - .local/runs/20260525T010204Z-tiny_lora_train
  - .local/runs/20260525T010234Z-tiny_lora_train
  - .local/runs/20260525T010305Z-tiny_lora_train
  - .local/runs/20260525T010336Z-tiny_lora_train
  - .local/runs/20260525T010610Z-multi_lora_bank_smoke
  - .local/runs/20260525T011135Z-3090_qwen2_vl_2b_external_tiny_n32
  - .local/runs/roi_stability_64_repeats3_plan.json
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

64 unique follow-up에서는 manifest 자체를 64개 고유 controlled samples로 확장하고, `train=32` / `holdout=32` split을 기록했다. RapidOCR detector box는 64/64 생성됐고, ROI source stability는 `center_crop`, `oracle_box`, `layout_proxy_box`, `ocr_detector_box` 각각 repeats=3으로 실행했다. 이어서 answer-only tiny LoRA를 32 step으로 학습하고 train/holdout evaluation을 남겼으며, 최신 trained adapter를 actual PEFT로 로드한 C0/C3/C4/C5/C6/C7 matrix를 측정했다.

```yaml
unique64_stability_lora_peft:
  result_brief: "docs/20_results/2026-05-24_unique64_stability_lora_peft_ko.md"
  manifest_samples: 64
  manifest_domain_distribution:
    document_or_receipt: 16
    scene_text_or_ocr: 16
    ui_screen: 16
    chart_or_table: 16
  split:
    train: 32
    holdout: 32
  ocr_detector_available: "64/64"
  roi_stability_plan: ".local/runs/roi_stability_64_repeats3_plan.json"
  roi_stability_commands_completed: 12
  roi_stability_returncodes: [0]
  roi_stability_repeats: 3
  roi_stability_samples_per_run: 64
  roi_stability_cells: [C0, C3, C4, C5, C6, C7]
  roi_stability_c4_scores:
    center_crop: 0.359375
    oracle_box: 0.96875
    layout_proxy_box: 0.953125
    ocr_detector_box: 0.890625
  roi_stability_c6_low_res_score: 0.21875
  roi_stability_c4_visual_tokens: 296.0
  roi_stability_c3_visual_tokens: 768.0
  tiny_lora_train_holdout_run: "20260524T114337Z-tiny_lora_train"
  tiny_lora_train_steps: 32
  tiny_lora_train_samples: 32
  tiny_lora_holdout_samples: 32
  tiny_lora_train_score_mean: 0.875
  tiny_lora_holdout_score_mean: 0.9375
  tiny_lora_accuracy_gain_claim: false
  actual_peft_full_cmatrix_run: "20260524T114456Z-3090_tiny_scored_trained_lora_full_cmatrix"
  actual_peft_full_cmatrix_cells: [C0, C3, C4, C5, C6, C7]
  actual_peft_full_cmatrix_measurement_gate: true
  actual_peft_full_cmatrix_completion_gate: false
  actual_peft_full_cmatrix_completion_gate_reason: "C1/C2 omitted by design for minimum actual PEFT diagnostic matrix"
  actual_peft_c4_score: 0.90625
  actual_peft_c5_score: 0.96875
  actual_peft_c6_low_res_score: 0.21875
  actual_peft_adapter_memory_source: "actual_loaded_adapter"
```

2026-05-25 follow-up에서는 남아 있던 external n=32, baseline-vs-trained, multi-LoRA bank, lightweight backbone sweep를 작은 실측 단위로 닫았다. Git에 남기는 최신 요약문은 [docs/20_results/2026-05-25_external_n32_multi_lora_backbone_ko.md](../20_results/2026-05-25_external_n32_multi_lora_backbone_ko.md)이다.

```yaml
external_n32_multi_lora_backbone:
  result_brief: "docs/20_results/2026-05-25_external_n32_multi_lora_backbone_ko.md"
  external_manifest: ".local/data/external_tiny_manifest/manifest.jsonl"
  external_manifest_samples: 64
  external_manifest_sources:
    lmms-lab/textvqa: 16
    lmms-lab/DocVQA: 16
    lmms-lab/ChartQA: 16
    rootsautomation/RICO-ScreenQA: 16
  ocr_detector_available: "63/64"
  primary_n32_manifest: ".local/data/external_tiny_manifest/manifest_ocr_detector_primary_n32.jsonl"
  primary_n32_distribution:
    lmms-lab/textvqa: 8
    lmms-lab/DocVQA: 8
    lmms-lab/ChartQA: 8
    rootsautomation/RICO-ScreenQA: 8
  qwen3_reference_external_run: "20260525T005611Z-3090_external_tiny_ocr_detector_n32"
  qwen3_reference_scores:
    C0: 0.850260
    C3: 0.850260
    C4: 0.799913
    C6: 0.694501
    C7: 0.799913
  actual_peft_external_run: "20260525T005917Z-3090_external_tiny_trained_lora_n32"
  actual_peft_external_adapter_memory_source: "actual_loaded_adapter"
  actual_peft_external_delta_mb: 5.625
  trained_lora_gain_verdict: "no_gain_observed"
  multi_lora_bank_run: "20260525T010610Z-multi_lora_bank_smoke"
  multi_lora_bank_adapters: [document, scene_text, ui_screen, chart]
  multi_lora_bank_allocated_delta_mb: 22.5
  multi_lora_correct_score_mean: 0.90625
  multi_lora_wrong_score_mean: 0.90625
  multi_lora_wrong_adapter_damage_mean: 0.0
  qwen2_vl_2b_sweep_run: "20260525T011135Z-3090_qwen2_vl_2b_external_tiny_n32"
  qwen2_vl_2b_base_after_load_allocated_mb: 4213.307
  qwen2_vl_2b_scores:
    C0: 0.681858
    C3: 0.681858
    C4: 0.751997
    C6: 0.644618
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
  - tiny_trained_lora_train_holdout_evaluation
  - trained_lora_actual_peft_load_smoke
  - trained_lora_actual_peft_full_cmatrix_diagnostic
  - ocr_detector_unique64_repeats3_stability_diagnostic
  - external_tiny_n32_validation_diagnostic
  - trained_lora_external_baseline_comparison
  - multi_trained_lora_bank_path_smoke
  - lightweight_backbone_sweep_one_candidate
  - adapter_card_residency_estimate
  - multi_specialist_resident_estimate
  - sequential_specialist_swap_smoke
  - actual_peft_attach_smoke

not_yet_claimed:
  - trained_lora_accuracy_gain
  - measured_full_specialist_joint_residency
  - general_benchmark_accuracy
  - broad_ocr_detector_roi_generalization
  - broad_external_benchmark_ocr_detector_roi
  - trained_lora_generalization
  - multi_lora_routing_accuracy_gain
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
  - actual PEFT full C0/C3/C4/C5/C6/C7 diagnostic matrix when adapter_memory_source=actual_loaded_adapter
  - ocr_detector_box when ocr_detector_available=true in manifest_ocr_detector.jsonl
  - tiny trained LoRA adapter load smoke when adapter_path points to .local/adapters/tiny_lora_latest
  - tiny train/holdout normalized_answer_match score in controlled tiny manifest

estimate_or_proxy:
  - adapter_bank_resident_mb from adapter cards
  - active_adapter_resident_mb from adapter cards
  - multi_specialist_resident_estimate_mb
  - task_score in synthetic_proxy or real_task_manifest smoke runs without expected_answers
  - verifier_score
  - roi quality and roi recall under center_crop or synthetic_probe mode
  - layout_proxy_box and detector_proxy_box until an external detector writes ocr_detector_box fields
  - trained LoRA accuracy gain until a clear baseline comparison and external or stronger holdout evidence exists
  - generate_extra_peak_over_prefill_mb as generate-minus-prefill proxy
```

### 4.1 아직 조심해야 할 부분

리서치 메모에서 지적한 주의점 중 현재 작업면에 남아 있는 것은 다음이다.

```yaml
still_cautious:
  - "OCR detector는 64 unique repeats=3 controlled diagnostic까지 완료됐지만, external benchmark generalization은 아직 아니다."
  - "tiny trained LoRA는 answer-only train/holdout 평가와 actual PEFT full C-matrix가 완료됐지만, baseline 대비 accuracy gain claim은 아직 아니다."
  - "actual PEFT full C-matrix는 C0/C3/C4/C5/C6/C7 최소 diagnostic이며, C1/C2까지 포함한 extended completion matrix는 아니다."
  - "C6/C7은 현재 DEFAULT_CELLS와 결과 산출물에 포함되어 있으나, 외부 benchmark claim으로 승격된 것은 아니다."
```

리서치 메모의 4번 항목을 현재 repo 기준으로 다시 대조하면 다음과 같다.

```yaml
research_caution_review:
  ocr_detector_stability:
    status: "closed_for_controlled_unique64_repeats3"
    action: "external benchmark 또는 human-evaluated subset으로만 다음 승격"
  tiny_lora_label_mask:
    status: "implemented_smoked_and_holdout_evaluated"
    action: "accuracy gain은 baseline 대비 검정 전까지 닫아둠"
  trained_lora_matrix_completion_gate_false:
    status: "minimum_actual_peft_full_cmatrix_completed"
    action: "C0/C3/C4/C5/C6/C7 measurement_gate=true; C1/C2 제외로 completion_gate=false"
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
  - expand the external benchmark or human-evaluated task set beyond the current tiny n=32 diagnostic
  - keep trained LoRA accuracy-gain claim closed until baseline improvement appears on stronger held-out/external evidence
  - design adapter-specific tasks where wrong-adapter damage should be observable
  - measure full specialist joint residency only on larger hardware, or keep it as an explicit estimate
```

리서치 메모의 `다음에 뭘 더 검증하면 좋을까` 항목은 아래 queue로 정리한다.

```yaml
next_validation_queue:
  - "외부 tiny benchmark는 n=32 diagnostic으로 닫혔고, 다음은 더 큰/사람 검수 subset 확장"
  - "trained LoRA accuracy gain claim은 현재 no-gain이므로 계속 닫아둠"
  - "multi-trained-LoRA bank path는 닫혔지만 wrong-adapter damage가 0.0이라 utility claim은 닫아둠"
  - "Qwen2-VL-2B 1개 후보 sweep은 닫혔고, 다음은 quantized 후보 또는 추가 1B~3B 후보"
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
  - 64 unique controlled tiny manifest with train/holdout split
  - OCR detector 64/64 manifest generation
  - ROI source stability repeats=3 over 64 unique samples
  - answer-only LoRA 32-step train/holdout evaluation
  - trained adapter actual PEFT C0/C3/C4/C5/C6/C7 diagnostic matrix
  - external tiny manifest 64 samples
  - external OCR detector primary n=32 balanced manifest
  - external n=32 Qwen3 reference diagnostic
  - external n=32 actual PEFT baseline-vs-trained comparison
  - four domain-specific trained LoRA adapters
  - multi-trained-LoRA bank load/switch smoke
  - Qwen2-VL-2B lightweight backbone sweep

needs_next:
  - stronger external or human-evaluated subset beyond n=32
  - adapter-specific task design that exposes wrong-adapter damage
  - quantized or additional 1B~3B backbone candidates
  - production p95/p99 only after serving harness exists
```
