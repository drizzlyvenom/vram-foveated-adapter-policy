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

`runs/` 아래의 원본 실행 산출물은 로컬 검토용이며 git 추적 대상이 아니다. 공개 repo에는 재현 가능한 scaffold, schema, config, runner, claim boundary만 올린다. 커밋 산출물과 로컬 전용 산출물의 경계는 [local artifact boundary](local_artifact_boundary_ko.md)에 따로 정리한다.

## 2. 로컬에서 확인된 실행 상태

최근 로컬 실행 기준 상태는 다음과 같다.

```yaml
dry_run_available: true
real_cuda_smoke_available: true
real_task_image_smoke_available: true
real_task_validation_available: false
trained_lora_evaluation_available: false
measured_multi_specialist_swap_available: false

local_only_reference_runs:
  - runs/20260524T062952Z-3090_two_track_pilot
```

이 local-only run은 RTX 3090에서 Qwen3-VL-4B local snapshot을 실제 CUDA로 로드하고, `real_task_manifest`의 고해상도 실제 이미지에서 full/low-res/ROI visual path의 token, prefill, CUDA peak를 기록한 smoke다.

Git에 남긴 요약문은 [docs/results/2026-05-24_real_task_image_smoke_ko.md](results/2026-05-24_real_task_image_smoke_ko.md)이다.

```yaml
latest_real_task_image_smoke:
  run_id: "20260524T062952Z-3090_two_track_pilot"
  samples: 2
  matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
  c0_full_visual_tokens_mean: 768.0
  c4_foveated_visual_tokens_mean: 296.0
  c4_visual_token_reduction_vs_c3: 0.614583
  c4_normal_path_peak_mb_mean: 8681.853
  c4_controlled_fallback_peak_mb_mean: 8962.613
  roi_source: "center_crop"
  task_score_source: "synthetic_proxy"
```

## 3. 현재 claim level

```yaml
current_claim_level:
  - scaffold
  - memory_accounting_smoke
  - real_task_image_smoke
  - adapter_card_residency_estimate
  - multi_specialist_resident_estimate

not_yet_claimed:
  - real_task_validation
  - trained_lora_accuracy_gain
  - measured_full_specialist_joint_residency
  - measured_sequential_specialist_swap
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

estimate_or_proxy:
  - adapter_bank_resident_mb from adapter cards
  - active_adapter_resident_mb from adapter cards
  - multi_specialist_resident_estimate_mb
  - task_score and verifier_score
  - roi quality and roi recall under center_crop or synthetic_probe mode
  - generate_extra_peak_over_prefill_mb as generate-minus-prefill proxy
```

## 5. 다음 승격 조건

다음 단계는 방어 문구를 더 붙이는 것이 아니라, proxy를 실제 실험으로 하나씩 교체하는 것이다.

```yaml
next_promotion_steps:
  - replace center_crop ROI with oracle_box, OCR_box, or foveater_model
  - add actual_peft or merged_lora adapter execution mode
  - measure sequential specialist swap latency
  - replace synthetic quality proxy with benchmark or human-evaluated task score
```
