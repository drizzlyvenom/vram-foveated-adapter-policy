# 2026-05-24 Scored ROI / Swap / PEFT Validation

## 요약

`294b603` 기준 main 작업면에서 M-B~M-F 검증을 실행했다. 이번 목적은 기존 synthetic proxy score를 소논문 후보 근거로 쓰지 않고, 다음 proxy 항목을 실제 측정으로 교체하는 것이다.

```yaml
closed_milestones:
  M-B_ROI_source_comparison: true
  M-C_tiny_scored_task_validation: true
  M-D_sequential_specialist_swap: true
  M-E_actual_peft_smoke: true
  M-F_repeated_n16_pilot: true

claim_boundary:
  final_benchmark_superiority: false
  trained_lora_gain: false
  production_p95_p99: false
  controlled_tiny_validation: true
```

원본 산출물은 로컬 `.local/runs/` 아래에만 보관한다. Git에는 본 요약과 재현 명령, 핵심 수치, claim boundary만 남긴다.

## 실행 정보

```yaml
runner_commit: "294b603"
hardware: "NVIDIA GeForce RTX 3090"
model: "Qwen/Qwen3-VL-4B-Instruct"
schema_version: "3090.combined_validation_result.v0.4"
source_semantics_version: "v0.3"
measurement_mode: "real_cuda"
data_mode: "tiny_scored_manifest"
samples_per_roi_run: 16
matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
task_score_source: "normalized_answer_match"
actual_task_score_available_rate: 1.0
```

Local-only run ids:

```yaml
roi_source_runs:
  center_crop: "20260524T090102Z-3090_tiny_scored_validation"
  oracle_box: "20260524T090206Z-3090_tiny_scored_validation"
  ocr_box_or_layout_box: "20260524T090316Z-3090_tiny_scored_validation"

specialist_swap_run: "20260524T090422Z-specialist_swap_smoke"
actual_peft_run: "20260524T090446Z-actual_peft_smoke"
```

재현 명령:

```powershell
.venv\Scripts\python.exe scripts\prepare_tiny_scored_manifest.py --max-samples 20
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_validation.yaml --real-run --max-samples 16 --roi-source center_crop --max-new-tokens 8
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_validation.yaml --real-run --max-samples 16 --roi-source oracle_box --max-new-tokens 8
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_validation.yaml --real-run --max-samples 16 --roi-source ocr_box_or_layout_box --max-new-tokens 8
.venv\Scripts\python.exe scripts\run_specialist_swap_smoke.py --config configs\3090\tiny_scored_validation.yaml --repeats 3
.venv\Scripts\python.exe scripts\run_actual_peft_smoke.py --config configs\3090\tiny_scored_validation.yaml --rank 4 --alpha 8
```

## M-B/M-C: ROI Source Comparison + Tiny Actual Score

아래 점수는 synthetic proxy가 아니라 Qwen3-VL-4B가 생성한 답변을 `expected_answers`와 normalized exact/contains match로 채점한 값이다. 단, 데이터셋은 큰 공개 benchmark가 아니라 로컬에서 생성한 controlled tiny scored image set이다.

| ROI source | C4 foveated score | C4 target-evidence hit | C4 visual tokens | C4 normal peak MB mean | C4 normal peak MB p95 | C5 oracle score | C6 low-res score |
|---|---:|---:|---:|---:|---:|---:|---:|
| center_crop | 0.3125 | 0.1875 | 296.0 | 8684.136 | 8684.136 | 0.9375 | 0.1250 |
| oracle_box | 0.9375 | 1.0000 | 296.0 | 8684.136 | 8684.136 | 0.9375 | 0.1250 |
| ocr_box_or_layout_box | 0.9375 | 1.0000 | 296.0 | 8684.136 | 8684.136 | 0.9375 | 0.1250 |

Full image reference:

```yaml
C0_full_image:
  task_score_mean: 0.9375
  visual_token_count_mean: 768.0
  normal_path_peak_mb_mean: 8890.532812

C3_taxonomy_lora_proxy_full_image:
  task_score_mean: 0.9375
  visual_token_count_mean: 768.0
  normal_path_peak_mb_mean: 8962.532812

C4_token_reduction_vs_C3:
  center_crop: 0.614583
  oracle_box: 0.614583
  ocr_box_or_layout_box: 0.614583
```

해석:

```yaml
safe:
  - "동일한 visual token budget에서 ROI source가 target evidence를 포함하는지 여부가 actual task score를 크게 바꾼다."
  - "oracle_box와 ocr_box_or_layout_box는 이 controlled tiny set에서 full-image score를 유지하면서 visual tokens를 768에서 296으로 줄였다."
  - "low-res only는 visual token은 100으로 가장 낮지만 score가 0.125로 떨어졌다."

not_yet:
  - "일반 benchmark에서 같은 score retention이 유지된다."
  - "ocr_box_or_layout_box가 실제 OCR detector로 검증됐다."
  - "FoveateR learned policy가 oracle/layout ROI를 대체한다."
```

## M-D: Sequential Specialist Swap

`run_specialist_swap_smoke.py`는 같은 Qwen3-VL-4B snapshot을 specialist proxy로 3회 load/unload 반복했다. 이는 multi-specialist joint residency 실측이 아니라 sequential swap 비용 실측이다.

```yaml
run_id: "20260524T090422Z-specialist_swap_smoke"
repeats: 3
model_load_latency_ms_mean: 4651.17
unload_empty_cache_latency_ms_mean: 135.029
after_load_allocated_mb_mean: 8464.481
after_unload_allocated_mb_mean: 0.0
after_unload_reserved_mb_mean: 0.0
measured_sequential_swap_available: true
measured_joint_residency_available: false
```

해석:

```yaml
safe:
  - "RTX 3090에서 full VLM specialist proxy를 매번 reload하는 sequential swap 비용은 약 4.65초/load로 측정됐다."
  - "이 수치는 LoRA attach/switch 계측과 비교할 baseline latency로 사용할 수 있다."

not_yet:
  - "여러 서로 다른 specialist VLM의 동시 resident footprint를 실측했다."
  - "production serving latency를 검증했다."
```

## M-E: Actual PEFT Attach Smoke

`run_actual_peft_smoke.py`는 PEFT LoRA module을 실제로 Qwen3-VL-4B에 attach하고, 메모리 delta와 forward path를 측정했다. adapter는 훈련되지 않은 LoRA이므로 성능 향상 claim에는 사용하지 않는다.

```yaml
run_id: "20260524T090446Z-actual_peft_smoke"
adapter_execution_mode: "actual_peft"
adapter_memory_source: "actual_loaded_adapter"
target_modules: ["q_proj", "v_proj"]
rank: 4
alpha: 8
base_after_load_allocated_mb: 8464.481
peft_allocated_delta_mb: 5.625
peft_attach_latency_ms: 171.494
trainable_lora_parameters: 1474560
forward_incremental_peak_mb: 108.737
```

해석:

```yaml
safe:
  - "proxy card accounting과 별개로 actual PEFT attach path가 RTX 3090에서 동작한다."
  - "rank-4 q_proj/v_proj LoRA attach의 allocated delta는 이 smoke에서 약 5.625 MB로 측정됐다."

not_yet:
  - "trained LoRA가 task score를 유지하거나 향상한다."
  - "LoRA bank 전체의 switch/merge 정책이 검증됐다."
```

## M-F: n=16 반복 측정

이번 ROI source comparison은 각 ROI source별 n=16으로 실행했다. 아직 n=32, repeats=3까지는 확장하지 않았지만, 기존 n=1~2 smoke에서 한 단계 올라가 mean과 p95 필드를 같은 schema로 남겼다.

```yaml
repeated_pilot:
  samples_per_roi_source: 16
  roi_sources: [center_crop, oracle_box, ocr_box_or_layout_box]
  p95_fields_recorded:
    - visual_token_count_p95
    - normal_path_peak_mb_p95
    - visual_incremental_peak_mb_p95
    - controlled_fallback_peak_mb_conditional_p95
    - controlled_fallback_peak_mb_all_samples_p95
```

## 결론

이번 마일스톤에서 가장 중요한 변화는 `task_score_source=synthetic_proxy`를 `task_score_source=normalized_answer_match`로 교체했다는 점이다. 이 controlled tiny validation 안에서는 oracle/layout ROI가 full-image score를 유지하면서 C4 visual token을 C3 대비 약 61.46% 줄였고, center crop은 target evidence hit가 낮을 때 score가 크게 떨어졌다.

소논문에서 사용할 수 있는 가장 보수적인 문장은 다음이다.

```text
On a controlled tiny scored validation set, the RTX 3090 pilot replaces synthetic quality proxies with normalized answer matching. Under the same foveated visual-token budget, ROI source quality dominates task-score retention: oracle/layout ROI preserved the full-image score, while center-crop ROI failed when it missed target evidence. Separately, sequential full-model reload and actual PEFT attach were measured as latency and memory baselines, without claiming trained-LoRA accuracy gains.
```
