# 2026-05-24 OCR Detector / Tiny Trained LoRA Smoke

## 요약

`a59c040` 작업면에서 OCR detector ROI와 tiny trained LoRA path를 짧은 real CUDA smoke로 확인했다. 목적은 `layout_proxy_box`를 실제 OCR detector output으로 한 번 교체하고, random PEFT attach를 넘어 학습된 LoRA adapter가 저장/로드되는 경로를 닫는 것이다.

이 결과는 controlled tiny set의 smoke다. 일반 benchmark 성능, trained LoRA accuracy gain, production latency는 아직 주장하지 않는다.

```yaml
status:
  ocr_detector_manifest: "rapidocr generated detector boxes for 20/20 samples"
  ocr_detector_matrix_smoke: "n=4 real CUDA C0-C7 pass completed"
  tiny_lora_training_smoke: "rank-4 q_proj/v_proj LoRA trained for 4 steps and saved"
  trained_lora_matrix_smoke: "C3/C4 actual PEFT path loaded the saved adapter"

claim_boundary:
  final_benchmark_superiority: false
  trained_lora_accuracy_gain: false
  production_p95_p99: false
  controlled_tiny_smoke: true
```

## 실행 정보

```yaml
ocr_manifest:
  command: "scripts/prepare_ocr_detector_manifest.py --engine rapidocr"
  output: ".local/data/tiny_scored_manifest/manifest_ocr_detector.jsonl"
  samples: 20
  detector_available: 20
  detector_missing: 0

ocr_detector_run:
  run_id: "20260524T095934Z-3090_tiny_scored_ocr_detector"
  measurement_mode: "real_cuda"
  data_mode: "tiny_scored_manifest"
  roi_source: "ocr_detector_box"
  samples: 4
  matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
  completion_gate: true
  measurement_gate: true
  promotion_gate: false

tiny_lora_train:
  run_id: "20260524T095906Z-tiny_lora_train"
  adapter_dir: ".local/adapters/20260524T095906Z-tiny_lora_train"
  latest_adapter_dir: ".local/adapters/tiny_lora_latest"
  train_steps: 4
  max_samples: 4
  rank: 4
  alpha: 8
  target_modules: ["q_proj", "v_proj"]

trained_lora_matrix_smoke:
  run_id: "20260524T095934Z-3090_tiny_scored_trained_lora_matrix_smoke"
  adapter_memory_source: "actual_loaded_adapter"
  adapter_execution_mode: "actual_peft"
  roi_source: "ocr_detector_box"
  matrix_cells: [C3, C4]
  completion_gate: false
  completion_gate_reason: "C3/C4-only incomplete matrix by design"
  measurement_gate: true
```

## OCR Detector Smoke

RapidOCR가 controlled tiny scored manifest 20개 이미지 모두에서 detector box를 생성했다. 이어서 `ocr_detector_box`를 ROI source로 사용한 n=4 real CUDA C0-C7 pass를 실행했다.

핵심 수치:

```yaml
C3_full_image:
  task_score_mean: 1.0
  visual_token_count_mean: 768.0
  normal_path_peak_mb_mean: 8962.84125

C4_ocr_detector_roi:
  task_score_mean: 1.0
  visual_token_count_mean: 296.0
  normal_path_peak_mb_mean: 8684.136
  controlled_fallback_rate: 0.25

C6_low_res_only:
  task_score_mean: 0.0
  visual_token_count_mean: 100.0
  normal_path_peak_mb_mean: 8593.007

C7_controlled_fallback:
  task_score_mean: 1.0
  visual_token_count_mean: 296.0
  normal_path_peak_mb_mean: 8684.136
  controlled_fallback_peak_mb_conditional_mean: 8962.83075
  controlled_fallback_peak_mb_all_samples_mean: 8962.83075
  controlled_fallback_rate: 1.0

visual_summary:
  c4_visual_token_reduction_vs_c3: 0.614583
  prefill_latency_reduction_vs_full: 0.762288
```

해석:

```yaml
safe:
  - "RapidOCR 기반 ocr_detector_box manifest 생성과 n=4 real CUDA matrix smoke가 동작했다."
  - "controlled tiny n=4 smoke에서 OCR detector ROI는 full-image score를 유지하면서 visual tokens를 768에서 296으로 줄였다."
  - "low-res only는 같은 n=4 smoke에서 score가 0.0으로 떨어졌다."
  - "C7 controlled fallback도 같은 C0-C7 smoke에 포함됐고, fallback path peak와 fallback rate가 기록됐다."

not_yet:
  - "OCR detector가 외부 benchmark에서도 oracle에 가깝다."
  - "이 n=4 smoke 자체만으로는 32개 고유 샘플 또는 repeats=3 반복 안정성이 검증됐다고 보지 않는다."
```

## Tiny Trained LoRA Smoke

`train_tiny_lora_smoke.py`로 OCR detector ROI evidence를 사용해 rank-4 LoRA를 4 step 학습하고 adapter를 저장했다.

```yaml
base_after_load_allocated_mb: 8464.481
peft_allocated_delta_mb: 5.625
peft_attach_latency_ms: 275.435
trainable_lora_parameters: 1474560
train_peak_allocated_mb: 9232.653
losses: [24.188007, 23.654936, 23.674713, 23.931889]
```

이후 `.local/adapters/tiny_lora_latest`를 `actual_peft.adapter_path`로 로드하는 C3/C4 matrix smoke를 실행했다.

```yaml
C3_trained_lora_full_image:
  task_score_mean: 1.0
  visual_token_count_mean: 768.0
  normal_path_peak_mb_mean: 8896.8105

C4_trained_lora_ocr_detector_roi:
  task_score_mean: 1.0
  visual_token_count_mean: 296.0
  normal_path_peak_mb_mean: 8617.761
  controlled_fallback_rate: 0.25

source_summary:
  adapter_memory_source: "actual_loaded_adapter"
  adapter_execution_mode: "actual_peft"
```

해석:

```yaml
safe:
  - "tiny controlled LoRA training smoke에서 adapter 학습, 저장, actual PEFT 로드 경로가 닫혔다."
  - "trained adapter path가 C3/C4 matrix smoke에서 actual_loaded_adapter로 기록됐다."
  - "trained LoRA matrix smoke의 completion_gate=false는 C3/C4-only incomplete matrix 설계 때문이며, measurement_gate는 true다."

not_yet:
  - "trained LoRA가 정확도를 향상했다."
  - "LoRA bank routing 또는 여러 trained adapter switch가 검증됐다."
  - "외부 benchmark에서 trained adapter 성능이 검증됐다."
```

## 재현 명령

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
.venv\Scripts\python.exe scripts\prepare_ocr_detector_manifest.py --input .local\data\tiny_scored_manifest\manifest.jsonl --output .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --engine rapidocr
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_ocr_detector.yaml --real-run --max-samples 4 --max-new-tokens 8
.venv\Scripts\python.exe scripts\train_tiny_lora_smoke.py --manifest .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --roi-source ocr_detector_box --max-samples 4 --max-steps 4 --rank 4 --alpha 8 --learning-rate 1e-4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_trained_lora_matrix_smoke.yaml --real-run --max-samples 4 --max-new-tokens 8
```
