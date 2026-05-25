# 64 Unique Manifest / OCR Stability / LoRA Holdout / Actual PEFT Full C-Matrix

Status: controlled RTX 3090 diagnostic pass
Date: 2026-05-24
Promotion gate: false

## 현재 방향성에서의 해석

이 결과는 64 unique manifest, repeats=3 OCR stability, train/holdout path, actual PEFT C-matrix를 닫은 diagnostic milestone이다. Track A v2에서는 `기존 controlled task가 path는 닫지만 adapter-sensitive utility는 아직 보이지 않는다`는 설계 입력으로 쓴다.

## Summary

P1에서 남아 있던 `20 unique + cyclic n=32` 한계를 64개 고유 controlled sample로 닫았다. 새 manifest는 4개 도메인별 16개, 총 64개이며 `train=32`, `holdout=32` split을 기록한다. RapidOCR detector box도 64/64 생성됐다.

이번 pass는 세 가지를 추가로 확인했다.

```yaml
unique_manifest:
  samples: 64
  domain_distribution:
    document_or_receipt: 16
    scene_text_or_ocr: 16
    ui_screen: 16
    chart_or_table: 16
  split:
    train: 32
    holdout: 32
  ocr_detector_available: "64/64"

roi_stability_repeats3:
  plan: ".local/runs/roi_stability_64_repeats3_plan.json"
  roi_sources: [center_crop, oracle_box, layout_proxy_box, ocr_detector_box]
  repeats: 3
  samples_per_run: 64
  cells: [C0, C3, C4, C5, C6, C7]
  commands_completed: 12
  returncodes: [0]

tiny_lora_train_holdout:
  run_id: "20260524T114337Z-tiny_lora_train"
  train_steps: 32
  train_samples: 32
  holdout_samples: 32
  label_mask_mode: "answer_only"
  train_score_mean: 0.875
  holdout_score_mean: 0.9375
  trained_lora_accuracy_gain_claim: false

actual_peft_full_cmatrix:
  run_id: "20260524T114456Z-3090_tiny_scored_trained_lora_full_cmatrix"
  cells: [C0, C3, C4, C5, C6, C7]
  adapter_memory_source: "actual_loaded_adapter"
  measurement_gate: true
  completion_gate: false
  completion_gate_note: "C1/C2 omitted by design for the minimum actual PEFT C-matrix"
```

## ROI Stability Aggregate

아래 값은 64개 고유 sample, repeats=3의 run-level mean을 다시 평균낸 것이다. `do_sample=false`와 같은 seed/manifest를 사용했기 때문에 repeat 간 score mean std는 모두 0으로 기록됐다. 이는 deterministic stability smoke이지 production p95/p99 serving 검증이 아니다.

| ROI source | Cell | Score mean | Repeat std | Visual tokens | Normal peak MB | Fallback rate |
|---|---:|---:|---:|---:|---:|---:|
| center_crop | C4 | 0.359375 | 0.000000 | 296.0 | 8684.136 | 0.25 |
| center_crop | C6 | 0.218750 | 0.000000 | 100.0 | 8593.007 | 0.00 |
| center_crop | C7 | 0.359375 | 0.000000 | 296.0 | 8684.136 | 1.00 |
| oracle_box | C4 | 0.968750 | 0.000000 | 296.0 | 8684.136 | 0.25 |
| oracle_box | C6 | 0.218750 | 0.000000 | 100.0 | 8593.007 | 0.00 |
| oracle_box | C7 | 0.968750 | 0.000000 | 296.0 | 8684.136 | 1.00 |
| layout_proxy_box | C4 | 0.953125 | 0.000000 | 296.0 | 8684.136 | 0.25 |
| layout_proxy_box | C6 | 0.218750 | 0.000000 | 100.0 | 8593.007 | 0.00 |
| layout_proxy_box | C7 | 0.953125 | 0.000000 | 296.0 | 8684.136 | 1.00 |
| ocr_detector_box | C4 | 0.890625 | 0.000000 | 296.0 | 8684.136 | 0.25 |
| ocr_detector_box | C6 | 0.218750 | 0.000000 | 100.0 | 8593.007 | 0.00 |
| ocr_detector_box | C7 | 0.890625 | 0.000000 | 296.0 | 8684.136 | 1.00 |

공통 기준선은 모든 ROI source에서 같다.

| Cell | Meaning | Score mean | Visual tokens | Normal peak MB |
|---|---|---:|---:|---:|
| C0 | shared backbone + full image | 1.000000 | 768.0 | 8890.456 |
| C3 | taxonomy LoRA proxy + full image | 1.000000 | 768.0 | 8962.456 |

## Actual PEFT Full C-Matrix

`tiny_lora_latest`를 실제 PEFT adapter로 로드한 6-cell matrix다. C1/C2는 의도적으로 제외했기 때문에 completion gate는 false이고, measurement gate만 해석한다.

| Cell | Score mean | Score std | Visual tokens | Normal peak MB | Fallback rate | Wrong adapter damage | Reject count |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 | 1.000000 | 0.000000 | 768.0 | 8890.477 | 0.00 | 0.000000 | 0 |
| C3 | 1.000000 | 0.000000 | 768.0 | 8896.102 | 0.00 | 0.078125 | 0 |
| C4 | 0.906250 | 0.291481 | 296.0 | 8617.761 | 0.25 | 0.078125 | 6 |
| C5 | 0.968750 | 0.173993 | 296.0 | 8617.761 | 0.00 | 0.078125 | 2 |
| C6 | 0.218750 | 0.413399 | 100.0 | 8526.632 | 0.00 | 0.078125 | 46 |
| C7 | 0.906250 | 0.291481 | 296.0 | 8617.761 | 1.00 | 0.078125 | 6 |

## Interpretation

현재 controlled tiny set에서는 ROI source 품질 차이가 그대로 유지된다. `center_crop`은 off-center evidence에서 무너지고, `oracle_box`와 `layout_proxy_box`는 full-image에 가까운 score를 유지한다. `ocr_detector_box`는 같은 visual token budget에서 0.890625를 기록해 path stability는 확인됐지만, oracle 대체 또는 외부 benchmark generalization claim으로 승격하지 않는다.

LoRA 쪽은 answer-only mask, 32-step train, train/holdout scoring, actual PEFT full C-matrix load path까지 닫혔다. 다만 이 결과는 controlled tiny set의 학습/평가 경로 확인이다. baseline 대비 trained LoRA accuracy gain, multi-adapter routing generalization, external benchmark 성능 claim은 아직 열지 않는다.

## Reproduction Commands

```powershell
.venv\Scripts\python.exe scripts\prepare_tiny_scored_manifest.py --max-samples 64
.venv\Scripts\python.exe scripts\prepare_ocr_detector_manifest.py --input .local\data\tiny_scored_manifest\manifest.jsonl --output .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --engine rapidocr
.venv\Scripts\python.exe scripts\train_tiny_lora_smoke.py --manifest .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --roi-source ocr_detector_box --max-samples 32 --max-steps 32 --eval-train-samples 32 --eval-holdout-samples 32 --eval-max-new-tokens 8 --rank 4 --alpha 8 --learning-rate 1e-4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_trained_lora_full_cmatrix.yaml --real-run --max-samples 64 --max-new-tokens 8
.venv\Scripts\python.exe scripts\run_roi_source_stability.py --config configs\3090\tiny_scored_roi_stability_64.yaml --manifest .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --max-samples 64 --repeats 3 --max-new-tokens 8 --execute --output .local\runs\roi_stability_64_repeats3_plan.json
```

## Claim Boundary

```yaml
safe_now:
  - "64개 고유 controlled tiny manifest와 train/holdout split이 생성됐다."
  - "RapidOCR 기반 ocr_detector_box가 64/64 sample에서 생성됐다."
  - "ROI source comparison이 64 unique, repeats=3, C0/C3/C4/C5/C6/C7로 완료됐다."
  - "answer-only tiny LoRA train/holdout evaluation path가 동작한다."
  - "trained tiny LoRA를 actual_loaded_adapter로 로드한 C0/C3/C4/C5/C6/C7 matrix가 측정됐다."

not_yet:
  - "trained LoRA가 baseline보다 정확도를 개선한다."
  - "ocr_detector_box가 external benchmark에서 oracle을 대체한다."
  - "multi-trained-LoRA bank routing이 검증됐다."
  - "production p95/p99 serving latency가 검증됐다."
  - "Qwen3-VL-4B가 final low-end deployment backbone이다."
```
