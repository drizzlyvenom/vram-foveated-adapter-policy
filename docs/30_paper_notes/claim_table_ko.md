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
| OCR detector ROI가 n=32 requested C0-C7 smoke를 통과했다. | P1 OCR detector n=32 cyclic run | 32개 고유 샘플/repeats=3 및 external benchmark 아님 |

## Safe After New Runs

| Claim | Required Evidence |
|---|---|
| ROI source 결과가 repeats=3 또는 32개 이상 고유 샘플에서도 같은 방향이다. | `run_roi_source_stability.py --execute` 결과 |
| trained adapter의 actual PEFT full C-matrix 비교가 가능하다. | 최소 C0/C3/C4/C5/C6/C7 actual_loaded_adapter run |

## Not Yet

| Unsafe Claim | Why Not |
|---|---|
| 일반 benchmark에서도 score retention이 유지된다. | 외부 benchmark subset이 아직 없음 |
| trained LoRA가 정확도를 유지하거나 향상한다. | answer-only training smoke는 있으나 held-out 평가가 아직 없음 |
| tiny trained LoRA가 일반화된다. | 현재는 4-step controlled training smoke와 같은 tiny set load smoke |
| actual OCR detector ROI가 안정적으로 oracle을 대체한다. | 현재는 n=32 requested / 20 unique controlled tiny cyclic smoke |
| `layout_proxy_box`가 실제 OCR detector다. | controlled manifest box |
| 여러 다른 full specialist VLM의 joint residency를 실측했다. | 현재는 estimate 또는 sequential proxy |
| production p95/p99 latency가 검증됐다. | 단일-user local pilot |

## Preferred Wording

```text
On a controlled tiny scored diagnostic set, ROI source quality dominates task-score retention under the same foveated visual-token budget.
```

```text
The current layout proxy is a controlled box source, not an external OCR detector. We reserve ocr_detector_box for boxes produced by an optional OCR detector pipeline.
```
