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
real_task_validation_available: true
trained_lora_evaluation_available: false
measured_multi_specialist_swap_available: true
actual_peft_attach_smoke_available: true

local_only_reference_runs:
  - .local/runs/20260524T090102Z-3090_tiny_scored_validation
  - .local/runs/20260524T090206Z-3090_tiny_scored_validation
  - .local/runs/20260524T090316Z-3090_tiny_scored_validation
  - .local/runs/20260524T090422Z-specialist_swap_smoke
  - .local/runs/20260524T090446Z-actual_peft_smoke
  - .local/runs/20260524T080046Z-3090_two_track_pilot
  - .local/runs/20260524T072015Z-3090_two_track_pilot
  - .local/runs/20260524T062952Z-3090_two_track_pilot
```

최신 local-only run 묶음은 RTX 3090에서 Qwen3-VL-4B local snapshot을 실제 CUDA로 로드하고, `tiny_scored_manifest`의 controlled image task에서 ROI source별 C0-C7 matrix, normalized answer match score, p95 memory/token fields를 기록한 M-B~M-F validation이다. 같은 커밋에서 sequential specialist swap과 actual PEFT attach smoke도 기록했다.

Git에 남긴 최신 요약문은 [docs/20_results/2026-05-24_scored_roi_swap_peft_validation_ko.md](../20_results/2026-05-24_scored_roi_swap_peft_validation_ko.md)이다.

```yaml
latest_scored_roi_validation:
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
  c4_center_crop_score: 0.3125
  c4_oracle_box_score: 0.9375
  c4_ocr_layout_score: 0.9375
  c4_visual_token_count_mean: 296.0
  c3_visual_token_count_mean: 768.0
  c4_visual_token_reduction_vs_c3: 0.614583
  task_score_source: "normalized_answer_match"
  actual_task_score_available_rate: 1.0
  specialist_swap_run: "20260524T090422Z-specialist_swap_smoke"
  actual_peft_run: "20260524T090446Z-actual_peft_smoke"
```

## 3. 현재 claim level

```yaml
current_claim_level:
  - scaffold
  - memory_accounting_smoke
  - real_task_image_smoke
  - controlled_tiny_real_task_validation
  - adapter_card_residency_estimate
  - multi_specialist_resident_estimate
  - sequential_specialist_swap_smoke
  - actual_peft_attach_smoke

not_yet_claimed:
  - trained_lora_accuracy_gain
  - measured_full_specialist_joint_residency
  - general_benchmark_accuracy
  - actual_ocr_detector_roi
  - production_latency_or_p99
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

estimate_or_proxy:
  - adapter_bank_resident_mb from adapter cards
  - active_adapter_resident_mb from adapter cards
  - multi_specialist_resident_estimate_mb
  - task_score in synthetic_proxy or real_task_manifest smoke runs without expected_answers
  - verifier_score
  - roi quality and roi recall under center_crop or synthetic_probe mode
  - generate_extra_peak_over_prefill_mb as generate-minus-prefill proxy
```

## 5. 다음 승격 조건

다음 단계는 방어 문구를 더 붙이는 것이 아니라, proxy를 실제 실험으로 하나씩 교체하는 것이다.

```yaml
next_promotion_steps:
  - replace layout_box proxy with actual OCR/layout detector ROI
  - replace controlled tiny scored images with external benchmark or human-evaluated task set
  - evaluate trained LoRA weights, not random PEFT attach
  - measure LoRA bank switch latency across multiple actual adapters
  - measure full specialist joint residency only on larger hardware, or keep it as an explicit estimate
```
