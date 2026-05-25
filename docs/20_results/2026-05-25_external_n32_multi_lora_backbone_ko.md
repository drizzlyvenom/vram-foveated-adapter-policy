# External n32 / Multi-LoRA Bank / Qwen2 Backbone Sweep

Status: controlled-to-external diagnostic milestone closure
Date: 2026-05-25
Promotion gate: false

## 현재 방향성에서의 해석

이 결과는 Track A v2 재설계의 직접 근거다. 외부 n=32에서 trained LoRA gain이 없고, multi-LoRA bank smoke에서 correct/wrong adapter 차이가 없었기 때문에 현재 dataset/taxonomy는 adapter-sensitive하지 않다고 본다. 다음 작업은 더 큰 benchmark 확장이 아니라 AdapterCard v2와 Simula curriculum으로 correct-vs-wrong margin이 생기는 task를 설계하는 것이다.

## Summary

오늘 pass는 `needs_next`에 남아 있던 항목들을 작은 실측 단위로 닫는다.

```yaml
external_manifest:
  output: ".local/data/external_tiny_manifest/manifest.jsonl"
  samples: 64
  sources:
    lmms-lab/textvqa: 16
    lmms-lab/DocVQA: 16
    lmms-lab/ChartQA: 16
    rootsautomation/RICO-ScreenQA: 16
  primary_n32_distribution:
    lmms-lab/textvqa: 8
    lmms-lab/DocVQA: 8
    lmms-lab/ChartQA: 8
    rootsautomation/RICO-ScreenQA: 8

ocr_detector_manifest:
  output: ".local/data/external_tiny_manifest/manifest_ocr_detector.jsonl"
  detector: RapidOCR
  available: "63/64"
  missing:
    - sample_id: "ext_textvqa_0005"
      reason: "No OCR boxes met min_confidence=0.5"
  primary_n32_output: ".local/data/external_tiny_manifest/manifest_ocr_detector_primary_n32.jsonl"
  primary_n32_samples: 32
```

실행은 세 갈래다.

```yaml
r5_external_n32_qwen3_reference:
  run_id: "20260525T005611Z-3090_external_tiny_ocr_detector_n32"
  model: "Qwen/Qwen3-VL-4B-Instruct"
  cells: [C0, C3, C4, C6, C7]
  samples: 32
  measurement_gate: true
  completion_gate: false
  completion_gate_reason: "partial external diagnostic matrix"

baseline_vs_trained_actual_peft:
  run_id: "20260525T005917Z-3090_external_tiny_trained_lora_n32"
  adapter_memory_source: "actual_loaded_adapter"
  peft_allocated_delta_mb: 5.625
  baseline_c0_score: 0.850260
  trained_adapter_c3_score: 0.850260
  trained_lora_accuracy_gain_claim: false

multi_lora_bank_smoke:
  run_id: "20260525T010610Z-multi_lora_bank_smoke"
  adapters: [document, scene_text, ui_screen, chart]
  samples: 32
  adapter_bank_allocated_delta_mb: 22.5
  correct_score_mean: 0.90625
  wrong_score_mean: 0.90625
  correct_minus_wrong_score_mean: 0.0
  production_routing_claim: false

qwen2_vl_2b_backbone_sweep:
  model: "Qwen/Qwen2-VL-2B-Instruct"
  run_id: "20260525T011135Z-3090_qwen2_vl_2b_external_tiny_n32"
  cells: [C0, C3, C4, C6]
  samples: 32
  measurement_gate: true
```

## External n32 Results

`Qwen/Qwen3-VL-4B-Instruct` reference에서 같은 외부 n=32 manifest를 사용했다.

| Cell | Score mean | Visual tokens | Normal peak MB | Fallback rate |
|---|---:|---:|---:|---:|
| C0 | 0.850260 | 590.25 | 8784.471 | 0.00 |
| C3 | 0.850260 | 590.25 | 8856.471 | 0.00 |
| C4 | 0.799913 | 296.00 | 8688.560 | 0.25 |
| C6 | 0.694501 | 100.00 | 8597.562 | 0.00 |
| C7 | 0.799913 | 296.00 | 8688.560 | 1.00 |

해석:

```text
외부 n=32에서도 OCR ROI C4는 full-image C0/C3보다 낮지만, low-res-only C6보다 높다.
이는 controlled tiny result의 방향과 맞지만, 작은 subset이므로 general benchmark claim은 열지 않는다.
```

## Baseline vs Trained Adapter

같은 외부 n=32에서 `tiny_lora_latest`를 actual PEFT adapter로 로드했다.

| Cell | Score mean | Visual tokens | Normal peak MB | Adapter delta MB |
|---|---:|---:|---:|---:|
| C0 | 0.850260 | 590.25 | 8785.609 | 0.000 |
| C3 | 0.850260 | 590.25 | 8791.234 | 5.625 |
| C4 | 0.799913 | 296.00 | 8622.185 | 5.625 |
| C6 | 0.694501 | 100.00 | 8531.187 | 5.625 |
| C7 | 0.799913 | 296.00 | 8622.185 | 5.625 |

결론:

```yaml
trained_lora_gain:
  external_n32_baseline_c0: 0.850260
  external_n32_trained_c3: 0.850260
  verdict: "no accuracy-gain claim"
```

## Multi-LoRA Bank Smoke

controlled 64 manifest에서 도메인별 adapter 4개를 따로 학습했다.

| Adapter | Train samples | Holdout samples | Train score | Holdout score |
|---|---:|---:|---:|---:|
| document | 8 | 8 | 1.000 | 0.875 |
| scene_text | 8 | 8 | 0.875 | 1.000 |
| ui_screen | 8 | 8 | 0.750 | 0.750 |
| chart | 8 | 8 | 1.000 | 1.000 |

이후 네 adapter를 한 모델에 함께 로드하고 `set_adapter`로 correct/wrong adapter를 바꿔가며 holdout 32개를 평가했다.

| Metric | Value |
|---|---:|
| Adapter bank allocated delta MB | 22.500 |
| Correct adapter score mean | 0.906250 |
| Wrong adapter score mean | 0.906250 |
| Correct minus wrong score mean | 0.000000 |

결론:

```text
multi-trained-LoRA bank load와 adapter switching path는 동작한다.
하지만 현재 tiny controlled task에서는 wrong-adapter damage가 관측되지 않았다.
따라서 routing utility 또는 accuracy gain claim은 열지 않는다.
```

## Qwen2-VL-2B Backbone Sweep

`Qwen/Qwen2-VL-2B-Instruct`를 로컬 HF cache에 내려받아 같은 외부 n=32 manifest에서 C0/C3/C4/C6를 측정했다.

| Cell | Score mean | Visual tokens | Normal peak MB |
|---|---:|---:|---:|
| C0 | 0.681858 | 784.594 | 4493.501 |
| C3 | 0.681858 | 784.594 | 4565.501 |
| C4 | 0.751997 | 400.000 | 4435.708 |
| C6 | 0.644618 | 144.000 | 4348.564 |

기준 비교:

```yaml
qwen3_vl_4b_reference:
  base_after_load_allocated_mb: 8464.481
  external_n32_c0_score: 0.850260
  external_n32_c4_score: 0.799913

qwen2_vl_2b_candidate:
  base_after_load_allocated_mb: 4213.307
  external_n32_c0_score: 0.681858
  external_n32_c4_score: 0.751997
```

주의:

```text
Qwen2-VL-2B는 resident memory가 크게 낮다.
다만 tokenization/processor 차이 때문에 visual token 수는 Qwen3-VL-4B와 직접 동일 단위로 해석하지 않는다.
작은 n=32 subset의 score ordering도 final backbone selection claim이 아니다.
```

## Claim Boundary

```yaml
safe_now:
  - "외부 tiny manifest 64개와 balanced primary n=32 검증 subset이 생성됐다."
  - "RapidOCR detector box는 외부 64개 중 63개에서 생성됐다."
  - "Qwen3-VL-4B reference에서 외부 n=32 C0/C3/C4/C6/C7 diagnostic이 측정됐다."
  - "actual PEFT trained adapter를 외부 n=32 baseline과 비교했고, accuracy gain은 관측되지 않았다."
  - "도메인별 실제 LoRA 4개를 학습하고 multi-adapter bank load/switch smoke를 실행했다."
  - "Qwen2-VL-2B-Instruct를 1개 lightweight candidate로 external n=32 sweep에 넣었다."

not_yet:
  - "trained LoRA improves accuracy"
  - "multi-adapter routing improves accuracy"
  - "OCR detector ROI generalizes on broad benchmarks"
  - "Qwen2-VL-2B is the final low-end backbone"
  - "production p95/p99 serving is validated"
```
