# RTX 3090 Track A v2 검증 가이드라인

Status: Track A v2 validation redesign guide
Target hardware: RTX 3090 24GB
Purpose: Simula-compiled taxonomy LoRA bank가 저 VRAM vision specialist consolidation의 중심축이 될 수 있는지 검증한다.

## 1. 핵심 결론

이 프로젝트의 1차 목표는 더 이상 “Foveation만으로 peak VRAM을 크게 줄인다”가 아니다. 또한 Track B의 ROI 결과를 논문 메인 기여로 키우지도 않는다.

현재 중심축은 다음이다.

```text
Track A v2. Simula-compiled taxonomy LoRA bank
failure traces / wrong answers / wrong-adapter records
→ Gemma 4 26B teacher annotations
→ Simula curriculum compiler
→ adapter-sensitive LoRA candidates
→ base/correct/wrong/random certification
→ shared-backbone resident LoRA bank

Track B support. Visual evidence cost control
full high-resolution visual context
→ low-res global view + FoveateR-style ROI glimpses
→ controlled visual budget for Track A certification
```

Track A v2는 여러 specialist model의 resident weight 문제와 specialist switching 문제를 LoRA bank certification 문제로 바꾼다. Track B는 visual token, KV/cache, prefill, activation cost를 낮추는 보조 입력 경로로 남긴다.

즉, 논문 질문은 “ROI가 좋은가?”가 아니라 “offline Simula loop가 adapter-sensitive LoRA bank를 컴파일하고 검증할 수 있는가?”다.

## 2. 왜 검증 구조를 바꾸는가

기존 Stage 1+와 3090 결과는 Qwen3-VL-4B를 RTX 3090에서 실제로 돌려 RouteTrace, ROI source taxonomy, C0-C7 matrix, OCR detector path, actual PEFT load path를 닫은 점에서 의미가 있다. 그러나 외부 n=32와 multi-LoRA bank smoke에서 trained LoRA gain과 wrong-adapter damage가 관측되지 않았으므로, 현재 task/taxonomy는 adapter-sensitive하지 않다고 해석해야 한다.

따라서 기존 산출물은 다음으로 재분류한다.

```yaml
existing_results_status:
  keep_as:
    - protocol_closure
    - unified_route_trace_validation
    - ROI/input-cost instrumentation
    - fallback_quarantine_logging
    - actual PEFT load and multi-adapter bank smoke
    - negative evidence that current tasks are not adapter-sensitive
  do_not_use_as:
    - final_peak_vram_reduction_evidence
    - trained_lora_gain_evidence
    - multi_adapter_routing_utility_evidence
    - production_serving_evidence
```

## 3. 3090에서 가능한 검증

```yaml
possible_on_3090:
  - AdapterCard v2 schema and registry validation
  - Simula curriculum manifest dry-run and small train/holdout generation
  - single LoRA learns gate on adapter-sensitive synthetic/heldout tasks
  - correct-vs-wrong-vs-random adapter certification
  - taxonomy router top1/oracle comparison
  - base_after_load memory accounting
  - shared backbone vs multi-specialist residency estimate
  - model swap latency vs LoRA switch latency smoke
  - low-res/fullres/FoveateR-style ROI visual token comparison
  - incremental visual peak measurement
  - small LoRA or proxy adapter residency accounting
  - taxonomy router path validation
  - fallback budget-tier logging
```

## 4. 3090에서 어려운 검증

```yaml
hard_on_3090:
  - full-scale FoveateR RL training
  - many full VLMs simultaneously resident
  - production multi-user p99 serving
  - large LoRA bank compatibility matrix with real trained adapters
  - treating Gemma 4 26B as the runtime low-VRAM model
  - 7B/13B fullres VLM experiments without quantization/offload
```

이 항목들은 후속 장비나 별도 scale-up 단계로 넘긴다.

## 5. 새 중심 claim

논문이나 README에서 사용할 안전한 claim은 다음이다.

```text
We study whether an offline Simula loop can compile failure traces into certified taxonomy LoRA adapters for consolidating vision specialists on a shared VLM backbone. A Gemma 4 26B teacher proposes annotations and curricula, while certification is decided by base/correct/wrong/random adapter comparisons on held-out adapter-sensitive tasks. Foveated ROI evidence is used as an input-cost control module, not as the main contribution.
```

한국어로는 다음처럼 쓴다.

```text
우리는 offline Simula 루프가 실패 trace를 taxonomy별 LoRA curriculum으로 컴파일하고, 이를 검증된 AdapterCard 기반 LoRA bank로 묶어 shared VLM backbone 위에 여러 vision specialist를 통합할 수 있는지 검증한다. Gemma 4 26B는 teacher로 annotation과 curriculum 후보를 만들고, 최종 검증은 held-out adapter-sensitive task에서 base/correct/wrong/random adapter 비교로 닫는다. Foveated ROI evidence는 메인 기여가 아니라 입력 비용 통제 모듈이다.
```

## 6. 기존 산출물의 위치

```yaml
stage0_costsim:
  status: prior_feasibility
  use_for: cost model and logging contract

stage1_foveation_smoke:
  status: supporting_visual_cost_control
  use_for: controlled input budget for adapter certification

stage1plus_protocol:
  status: exploratory_protocol_closure
  use_for: RouteTrace, proxy router, fallback/quarantine instrumentation

external_n32_multi_lora:
  status: negative_adapter_sensitivity_evidence
  use_for: motivate adapter-sensitive task redesign

lewm_jepa_graph_memory:
  status: future_or_ablation
  use_for: later outcome-prediction or memory extension
```

## 7. 최우선 수정 원칙

1. README와 paper notes에서 Track A v2를 최상단에 둔다.
2. Stage 1+와 Track B 결과는 supporting input-cost evidence로 표기한다.
3. Gemma 4 26B는 teacher이며 runtime/certification authority가 아니라고 적는다.
4. Simula는 offline LoRA curriculum/compiler loop로 둔다.
5. memory metric은 resident memory와 visual incremental memory를 분리한다.
6. LoRA claim은 single-learns, correct-beats-wrong, router-selects-adapter gate를 통과하기 전까지 닫는다.
7. LeWM/JEPA는 core path가 아니라 future/ablation이다.
