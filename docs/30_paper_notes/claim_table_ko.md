# Claim Table

Status: claim boundary draft

## Safe Now

| Claim | Evidence | Boundary |
|---|---|---|
| RTX 3090에서 Qwen3-VL-4B real CUDA memory/token accounting 경로가 동작한다. | 2026-05-24 real CUDA runs | 단일 GPU pilot |
| manifest 기반 실제 이미지가 full/low-res/ROI evidence path로 들어간다. | source semantics closure | raw artifacts는 local-only |
| controlled tiny scored validation에서 ROI source 품질이 score retention을 좌우한다. | center/oracle/layout proxy n=16 | controlled diagnostic set |
| oracle/layout proxy ROI는 full-image score를 유지하면서 visual tokens를 줄였다. | scored ROI brief | layout proxy는 external OCR이 아님 |
| low-res only는 비용은 낮지만 score가 크게 떨어졌다. | C6 score | tiny set 기준 |
| sequential full-model reload와 actual PEFT attach memory/latency smoke를 측정했다. | swap smoke, actual PEFT smoke | trained LoRA gain 아님 |
| 실제 OCR detector ROI path가 smoke 수준에서 동작했다. | RapidOCR 20/20 manifest + n=4 C0-C7 smoke | oracle 대체/generalization 아님 |
| tiny trained LoRA 학습/저장/로드 경로가 닫혔다. | `train_tiny_lora_smoke.py` + C3/C4 actual PEFT load smoke | accuracy gain 아님 |
| actual PEFT load path가 C3/C4 matrix smoke에 반영됐다. | `adapter_memory_source=actual_loaded_adapter` | full C-matrix 아님 |
| answer-only label mask를 적용한 tiny LoRA smoke가 동작했다. | P1 answer-only run + supervised token count | held-out/accuracy gain 아님 |
| OCR detector ROI가 n=32 requested C0-C7 smoke를 통과했다. | P1 OCR detector n=32 cyclic run | 이후 64 unique repeats=3로 보강됨; external benchmark 아님 |
| 64개 고유 controlled tiny manifest와 train/holdout split이 생성됐다. | `prepare_tiny_scored_manifest.py --max-samples 64` | synthetic controlled set |
| OCR detector ROI stability가 64 unique, repeats=3에서 측정됐다. | `roi_stability_64_repeats3_plan.json`, 12/12 commands returncode 0 | external benchmark/generalization 아님 |
| tiny LoRA train/holdout evaluation 경로가 동작했다. | `20260524T114337Z-tiny_lora_train`, train 32 / holdout 32 | baseline 대비 gain claim 아님 |
| trained tiny LoRA의 actual PEFT full C-matrix가 측정됐다. | `20260524T114456Z-3090_tiny_scored_trained_lora_full_cmatrix` | C1/C2 제외 6-cell diagnostic |
| 외부 tiny manifest 64개와 balanced n=32 OCR detector subset이 생성됐다. | `prepare_external_tiny_manifest.py`, TextVQA/DocVQA/ChartQA/ScreenQA 각 16개 | tiny subset diagnostic |
| 외부 n=32에서 OCR ROI diagnostic이 측정됐다. | `20260525T005611Z-3090_external_tiny_ocr_detector_n32` | broad benchmark generalization 아님 |
| trained LoRA를 외부 n=32 baseline과 비교했다. | `20260525T005917Z-3090_external_tiny_trained_lora_n32`, C0=0.850260, C3=0.850260 | gain 없음, gain claim 닫힘 |
| 실제 domain-specific LoRA 4개를 multi-adapter bank로 로드하고 switching smoke를 실행했다. | `20260525T010610Z-multi_lora_bank_smoke`, bank delta 22.5MB | wrong-adapter damage 0.0, routing utility claim 아님 |
| Qwen2-VL-2B를 lightweight backbone 후보로 한 번 sweep했다. | `20260525T011135Z-3090_qwen2_vl_2b_external_tiny_n32` | final low-end backbone claim 아님 |

## Safe After New Runs

| Claim | Required Evidence |
|---|---|
| controlled result가 넓은 외부 benchmark에서도 유지된다. | 현재 n=32보다 큰 external 또는 human-evaluated subset |
| trained LoRA accuracy gain을 주장할 수 있다. | 명확한 baseline 대비 held-out/external improvement |
| multi-adapter routing utility를 주장할 수 있다. | adapter-specific task에서 wrong-adapter damage와 correct-adapter recovery가 관측됨 |

## Not Yet

| Unsafe Claim | Why Not |
|---|---|
| 일반 benchmark에서도 score retention이 유지된다. | 현재는 외부 n=32 tiny diagnostic뿐이라 broad benchmark가 아님 |
| trained LoRA가 baseline보다 정확도를 향상한다. | 외부 n=32 baseline 비교에서 gain이 관측되지 않음 |
| tiny trained LoRA가 일반화된다. | 현재는 controlled tiny set holdout 평가 |
| actual OCR detector ROI가 안정적으로 oracle을 대체한다. | 외부 n=32 diagnostic은 있으나 broad benchmark/generalization은 아직 아님 |
| `layout_proxy_box`가 실제 OCR detector다. | controlled manifest box |
| 여러 다른 full specialist VLM의 joint residency를 실측했다. | 현재는 estimate 또는 sequential proxy |
| multi-adapter routing이 정확도를 올린다. | actual bank smoke에서 correct/wrong adapter score 차이가 0.0 |
| Qwen2-VL-2B가 최종 low-end backbone이다. | 1개 후보의 tiny n=32 sweep만 있음 |
| production p95/p99 latency가 검증됐다. | 단일-user local pilot |

## Preferred Wording

```text
On a controlled tiny scored diagnostic set, ROI source quality dominates task-score retention under the same foveated visual-token budget.
```

```text
The current layout proxy is a controlled box source, not an external OCR detector. We reserve ocr_detector_box for boxes produced by an optional OCR detector pipeline.
```
