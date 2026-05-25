# 2026-05-24 Real-Task Image Smoke

## 현재 방향성에서의 해석

이 결과는 실제 이미지가 full/low-res/ROI evidence path로 들어가고 CUDA memory/token accounting이 기록되는지 확인한 smoke다. Track A v2에서는 visual evidence cost control 보조 결과이며, adapter utility나 routing claim은 포함하지 않는다.

## 요약

RTX 3090 단일 장비에서 Qwen3-VL-4B local snapshot을 실제 CUDA로 로드하고, `real_task_manifest`의 고해상도 실제 이미지에 대해 full image, low-res, foveated ROI, oracle ROI, controlled fallback 경로를 같은 C-matrix로 측정했다.

원본 산출물은 로컬 `.local/runs/20260524T062952Z-3090_two_track_pilot/` 아래에만 보관한다. Git에는 본 요약만 남긴다.

## 실행 정보

```yaml
run_id: "20260524T062952Z-3090_two_track_pilot"
commit_after_integration: "10789fc"
hardware: "NVIDIA GeForce RTX 3090"
model: "Qwen/Qwen3-VL-4B-Instruct"
measurement_mode: "real_cuda"
data_mode: "real_task_manifest"
roi_source: "center_crop"
samples: 2
matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
raw_artifacts_committed: false
```

재현 명령:

```powershell
python scripts\prepare_real_task_manifest.py --source picsum_highres --max-samples 4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\two_track_pilot.yaml --real-run --data-mode real_task_manifest --manifest .local\data\real_task_smoke\manifest.jsonl --max-samples 2 --max-new-tokens 4
```

## 핵심 결과

| Cell | Path | Visual tokens mean | Normal peak MB mean | Note |
|---|---|---:|---:|---|
| C0 | shared backbone + full image | 768.0 | 8889.4315 | full visual context |
| C3 | taxonomy LoRA proxy + full image | 768.0 | 8961.4315 | adapter card estimate 포함 |
| C4 | taxonomy LoRA proxy + foveated ROI | 296.0 | 8681.853 | center-crop ROI |
| C6 | taxonomy LoRA proxy + low-res only | 100.0 | 8591.346 | lowest visual evidence cost |
| C7 | taxonomy LoRA proxy + controlled fallback | 296.0 | 8681.853 | controlled fallback peak 별도 기록 |

```yaml
c4_visual_token_reduction_vs_c3: 0.614583
c4_prefill_latency_reduction_vs_full: 0.804347
c4_normal_path_peak_mb_mean: 8681.853
c4_controlled_fallback_peak_mb_mean: 8962.613
shared_backbone_plus_lora_bank_resident_mb: 8536.481
multi_specialist_resident_estimate_mb: 33857.924
```

## Gate 상태

```yaml
completion_gate: true
measurement_gate: true
promotion_gate: false

track_promotion_gates:
  resident_track_promotion_gate: false
  foveation_track_promotion_gate: false
  combined_track_promotion_gate: false
```

`promotion_gate=false`인 이유는 정상이다. 현재 run은 실제 이미지 기반 memory/token smoke지만, 실제 task accuracy와 actual LoRA execution은 아직 없다.

## 해석 가능한 Claim

```yaml
safe:
  - "RTX 3090에서 Qwen3-VL-4B real CUDA memory accounting 경로가 동작한다."
  - "real_task_manifest 기반 실제 이미지가 runner에 들어가고, full/low/ROI evidence path를 같은 schema로 기록한다."
  - "해당 high-res image smoke에서 C4 foveated ROI path는 C3 full-image path 대비 visual token을 줄였다."
  - "normal path peak와 controlled fallback peak가 분리 기록된다."

not_yet:
  - "실제 task accuracy가 유지된다."
  - "실제 trained LoRA가 성능을 유지하거나 향상한다."
  - "center_crop ROI가 task-relevant ROI를 안정적으로 찾는다."
  - "multi-specialist baseline을 실측으로 이겼다."
  - "production p95/p99 latency가 검증됐다."
```

## 관찰

COCO val 소형 이미지를 처음 사용했을 때는 full-image token 수가 이미 작아서 ROI path의 이득이 잘 보이지 않았다. 고해상도 실제 이미지 smoke로 바꾸자 full-image token mean이 768.0, foveated ROI token mean이 296.0으로 분리되었다. 따라서 다음 R3 실험은 “고해상도 입력 또는 문서/도면처럼 token pressure가 큰 입력”에서 진행하는 편이 맞다.

## 다음 작업

```yaml
next:
  - center_crop ROI를 oracle_box 또는 OCR_box로 교체한다.
  - benchmark/human-eval 가능한 실제 task score를 붙인다.
  - actual_peft 또는 merged_lora adapter execution mode를 추가한다.
  - measured sequential specialist swap latency를 기록한다.
```
