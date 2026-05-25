# 소논문 Outline 초안

Status: Track A v2 working outline

## 1. 중심 문장

```text
Can an offline Simula loop compile failure traces into certified taxonomy LoRA adapters, so that multiple vision specialists can be consolidated onto a shared VLM backbone under a low-VRAM budget?
```

한국어로는 다음처럼 둔다.

```text
오프라인 Simula 루프가 실패 trace를 taxonomy별 LoRA curriculum으로 컴파일하고, 이를 AdapterCard certification으로 검증해 여러 vision specialist를 shared VLM backbone 위에 통합할 수 있는가?
```

## 2. 섹션 구조

```yaml
introduction:
  - 여러 vision specialist를 full VLM로 따로 유지할 때 생기는 resident memory와 swap cost 문제
  - 기존 Track B 결과가 많지만, 현재 논문축은 adapter bank consolidation임을 명시
  - 핵심 질문: failure trace를 adapter-sensitive LoRA curriculum으로 컴파일할 수 있는가

method:
  - Gemma 4 26B teacher: annotation, taxonomy labeling, curriculum/hard-negative proposal
  - Simula compiler: trace -> taxonomy -> train/holdout curriculum -> AdapterCard candidate
  - AdapterCard v2: taxonomy, training, serving, certification fields
  - certification gates: single LoRA learns, correct beats wrong/random, router selects adapter
  - Track B ROI path: controlled visual evidence cost module

diagnostic_setup:
  - RTX 3090 24GB
  - Qwen3-VL-4B local snapshot as reference/accounting anchor
  - existing controlled/external tiny result as diagnostic boundary
  - adapter-sensitive synthetic/heldout task design
  - normalized answer matching plus base/correct/wrong/random comparison

results:
  - existing result recap: Track B support and Track A path smoke
  - negative result: external n32 trained LoRA no gain
  - negative result: multi-LoRA bank wrong-adapter damage 0.0
  - new target table: AdapterCard certification gates

limitations:
  - controlled tiny set, not broad benchmark
  - Gemma teacher labels are candidates, not final ground truth
  - current LoRA results do not show accuracy gain
  - current taxonomy/tasks are not adapter-sensitive enough
  - ROI/OCR results are visual-cost support, not main novelty
  - Qwen3-VL-4B is a reference backbone, not a lightweight target sweep
  - production p95/p99 out of scope

next_work:
  - AdapterCard v2 schema
  - Simula curriculum manifest schema
  - adapter-sensitive manifest generator
  - base/correct/wrong/random certification runner
  - router gate only after correct beats wrong
```

## 2.1 Backbone 역할 분리

```yaml
backbone_roles:
  qwen3_vl_4b:
    role: "reference/accounting anchor"
    safe_claim: "two-track accounting and diagnostic effects can be measured on RTX 3090"
    unsafe_claim: "low-VRAM deployment target is solved"

  small_vlm_1b_3b:
    role: "future lightweight target sweep"
    required_before_claim:
      - external or held-out tiny subset
      - same ROI source taxonomy
      - same normal/fallback peak separation
```

## 3. 현재 abstract 재료

```text
We present a measurement-first plan for consolidating vision specialists on a shared VLM backbone under a low-VRAM budget. The central mechanism is an offline Simula loop that compiles failure traces into taxonomy-specific LoRA curricula. A Gemma 4 26B teacher proposes annotations, hard negatives, and expected answers, but adapter certification is decided by base/correct/wrong/random comparisons on held-out adapter-sensitive tasks. Existing RTX 3090 diagnostics show that the PEFT load path and multi-adapter bank path work, while current tasks do not yet produce trained-LoRA gain or wrong-adapter damage. We therefore use those negative results to motivate AdapterCard v2 certification and keep foveated ROI evidence as an input-cost control module rather than the main contribution.
```
