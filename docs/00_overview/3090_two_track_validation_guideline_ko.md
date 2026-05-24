# RTX 3090 투트랙 검증 가이드라인

Status: validation redesign guide
Target hardware: RTX 3090 24GB
Purpose: 저사양 VRAM 환경에서 비전 추론 구조가 성립하는지 검증한다.

## 1. 핵심 결론

이 프로젝트의 1차 목표는 더 이상 “Foveation만으로 peak VRAM을 크게 줄인다”가 아니다.
3090 검증은 다음 두 병목을 분리해 확인한다.

```text
Track A. Resident specialist compression
여러 full specialist VLM
→ 하나의 shared VLM backbone + taxonomy-tagged LoRA bank

Track B. Visual evidence compression
full high-resolution visual context
→ low-res global view + FoveateR-style ROI glimpses
```

Track A는 여러 specialist model의 resident weight 문제를 줄인다.
Track B는 visual token, KV/cache, prefill, activation cost를 줄인다.

둘 중 하나만으로는 저사양 기기에서 비전 모델을 안정적으로 돌리는 문제를 충분히 해결하기 어렵다.

## 2. 왜 검증 구조를 바꾸는가

기존 Stage 1+는 Qwen3-VL-4B를 RTX 3090에서 실제로 돌려 RouteTrace 계약을 닫은 점에서 의미가 있다. 그러나 foveation이 visual token을 줄여도 full backbone이 계속 resident인 한 peak VRAM 감소는 제한될 수 있다.

따라서 Stage 1+는 다음으로 재분류한다.

```yaml
stage1plus_status:
  keep_as:
    - protocol_closure
    - unified_route_trace_validation
    - foveation_and_proxy_routing_instrumentation
    - fallback_quarantine_logging
  do_not_use_as:
    - final_peak_vram_reduction_evidence
    - trained_lora_gain_evidence
    - production_serving_evidence
```

## 3. 3090에서 가능한 검증

```yaml
possible_on_3090:
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
  - 7B/13B fullres VLM experiments without quantization/offload
```

이 항목들은 후속 장비나 별도 scale-up 단계로 넘긴다.

## 5. 새 중심 claim

논문이나 README에서 사용할 안전한 claim은 다음이다.

```text
We separate low-VRAM vision inference into resident specialist compression and visual evidence compression. Shared-backbone LoRA banks reduce resident specialist footprint and model-switch latency, while FoveateR-style ROI glimpses reduce visual token, KV/cache, and prefill costs. The RTX 3090 pilot validates the accounting and feasibility of this two-track design, not final large-scale performance.
```

한국어로는 다음처럼 쓴다.

```text
우리는 저사양 VRAM 비전 추론을 두 병목으로 분해한다. shared-backbone LoRA bank는 여러 specialist model의 resident footprint와 mode-switch 비용을 줄이고, FoveateR-style ROI glimpse는 full high-resolution visual context로 인한 visual token/KV/prefill 비용을 줄인다. RTX 3090 pilot은 이 투트랙 구조의 계측 가능성과 feasibility를 검증하는 단계다.
```

## 6. 기존 산출물의 위치

```yaml
stage0_costsim:
  status: prior_feasibility
  use_for: cost model and logging contract

stage1_foveation_smoke:
  status: supporting_visual_path_evidence
  use_for: token and visual-path cost direction

stage1plus_protocol:
  status: exploratory_protocol_closure
  use_for: RouteTrace, proxy router, fallback/quarantine instrumentation

lewm_jepa_graph_memory:
  status: future_or_ablation
  use_for: later outcome-prediction or memory extension
```

## 7. 최우선 수정 원칙

1. README에서 투트랙 구조를 최상단에 둔다.
2. Stage 1+는 core evidence가 아니라 exploratory protocol closure로 표기한다.
3. memory metric은 resident memory와 visual incremental memory를 분리한다.
4. fallback은 복잡한 루프가 아니라 budget tier로 문서화한다.
5. LeWM/JEPA는 core path가 아니라 future/ablation이다.
