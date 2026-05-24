# 소논문 Outline 초안

Status: working outline

## 1. 중심 문장

```text
Low-VRAM vision inference has two separable bottlenecks: resident specialist model memory and visual evidence cost. An RTX 3090 pilot can measure these axes separately with shared-backbone adapter accounting and ROI-based visual evidence compression, while keeping benchmark and trained-adapter claims out of scope.
```

한국어로는 다음처럼 둔다.

```text
저 VRAM 비전 추론의 병목은 resident specialist model memory와 visual evidence cost로 나눌 수 있다. RTX 3090 pilot은 shared-backbone adapter accounting과 ROI evidence compression을 분리 계측하되, 일반 benchmark 우월성이나 trained adapter 성능 향상은 아직 주장하지 않는다.
```

## 2. 섹션 구조

```yaml
introduction:
  - low-VRAM vision inference의 두 병목 정의
  - resident memory와 visual token/KV/prefill 비용을 섞어 말하면 안 되는 이유

method:
  - Track A: full specialist VLM reload / joint residency estimate vs shared backbone + LoRA bank
  - Track B: full image vs low-res only vs foveated ROI vs oracle ROI
  - normal path, controlled fallback, emergency peak 분리

diagnostic_setup:
  - RTX 3090 24GB
  - Qwen3-VL-4B local snapshot
  - controlled tiny scored image set
  - normalized answer matching

results:
  - ROI source comparison
  - sequential specialist reload vs actual PEFT attach
  - combined C-matrix

limitations:
  - controlled tiny set, not broad benchmark
  - layout_proxy_box, not external OCR detector
  - untrained PEFT attach, not trained LoRA gain
  - production p95/p99 out of scope

next_work:
  - ocr_detector_box oracle-gap measurement
  - external tiny subset
  - trained LoRA path
```

## 3. 현재 abstract 재료

```text
We present a measurement-first pilot for low-VRAM vision inference on an RTX 3090. The design separates resident specialist compression from visual evidence compression. For resident compression, we compare sequential full-model reload and shared-backbone adapter accounting, including an actual PEFT attach smoke. For visual evidence compression, a controlled tiny scored set shows that ROI source quality dominates task-score retention under a fixed foveated token budget. Oracle/layout proxy ROI preserves full-image score on this diagnostic set while reducing visual tokens, whereas center crop and low-res-only baselines fail when target evidence is missed. These results support feasibility and instrumentation claims, not benchmark superiority or trained-LoRA accuracy gains.
```
