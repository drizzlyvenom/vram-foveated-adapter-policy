# Track A v2 Reframe

Status: active paper-axis reset
Date: 2026-05-25

Related active docs:

```yaml
synced_docs:
  - "../../README.md"
  - "../00_overview/3090_two_track_validation_guideline_ko.md"
  - "../10_protocols/3090_execution_ladder_ko.md"
  - "paper_outline_ko.md"
  - "claim_table_ko.md"
  - "ablation_table_plan_ko.md"
```

## 0. 결론

프로젝트를 엎지 않는다. 대신 논문 중심축을 다시 Track A로 둔다.

```text
Track A main:
  Simula-compiled taxonomy LoRA bank

Track B support:
  visual evidence cost control / ROI compression baseline
```

지금까지의 Track B 실험은 버리지 않는다. 다만 더 키우지 않고, Track A 실험에서 입력 비용을 통제하는 보조 모듈로 둔다.

## 1. 어디서 꼬였는가

초기 목표는 여러 vision specialist model을 하나의 shared backbone과 LoRA bank로 통합하는 것이었다.

```text
multiple specialist VLMs
  -> shared VLM backbone
  -> taxonomy-tagged resident LoRA bank
```

그런데 검증하기 쉬운 축은 Track B였다.

```text
full image
  -> low-res global view + high-res ROI
```

그래서 현재 repo에는 Track B evidence가 더 많이 쌓였다.

```yaml
track_b_evidence:
  - ROI source comparison
  - visual token reduction
  - C6 low-res failure
  - C7 fallback semantics
  - OCR detector ROI path
  - external n32 OCR ROI diagnostic
```

반대로 Track A는 path smoke와 negative result가 중심이다.

```yaml
track_a_current_evidence:
  positive:
    - actual PEFT attach/load works
    - answer-only tiny LoRA train/save/load works
    - actual PEFT C-matrix works
    - multi-adapter bank load/switch works
    - adapter memory delta is measurable
  negative:
    - external n32에서 trained LoRA gain 없음
    - correct adapter와 wrong adapter score 차이 없음
```

이 negative result는 실패가 아니라 진단이다.

```text
현재 task와 taxonomy는 adapter-sensitive하지 않다.
```

## 2. 새 중심축

새 논문 중심 질문은 다음으로 둔다.

```text
Can an offline Simula loop compile failure traces into certified taxonomy LoRA adapters,
so that multiple vision specialists can be consolidated onto a shared VLM backbone?
```

한국어로는 다음과 같다.

```text
오프라인 Simula 루프가 실패 trace를 taxonomy별 LoRA curriculum으로 컴파일하고,
이를 검증된 adapter bank로 묶어 여러 vision specialist를 shared backbone 위에 통합할 수 있는가?
```

## 3. Gemma 4 26B의 역할

Gemma 4 26B는 runtime model이 아니라 teacher다.

```yaml
teacher_model:
  id: "google/gemma-4-26B-A4B-it"
  role:
    - failure annotator
    - taxonomy labeler
    - curriculum generator
    - hard negative generator
    - answer/rationale proposer
  not_role:
    - runtime low-VRAM backbone
    - certification authority by itself
```

중요한 경계:

```text
Gemma가 만든 label을 그대로 최종 정답으로 쓰지 않는다.
Gemma는 후보 문제와 설명을 만들고, certification은 base/correct/wrong/random 비교와 heldout 검증으로 닫는다.
```

## 4. Simula의 역할

Simula는 거대한 world model이 아니라 offline LoRA compiler다.

```text
online traces / failed attempts
  -> Simula taxonomy assignment
  -> adapter-sensitive curriculum generation
  -> LoRA candidate training
  -> adapter certification
  -> AdapterCard registry update
```

### 4.1 입력

```yaml
simula_inputs:
  - route_traces.jsonl
  - failed answers
  - low confidence samples
  - wrong adapter records
  - ROI miss records
  - base model errors
```

### 4.2 처리

```yaml
simula_process:
  - classify failure_mode
  - assign taxonomy
  - generate adapter-sensitive examples
  - create train/holdout split
  - generate hard negatives
  - propose expected answers
  - write curriculum manifest
```

### 4.3 출력

```yaml
simula_outputs:
  - curriculum_manifest.jsonl
  - teacher_annotations.jsonl
  - adapter_candidate_plan.yaml
  - certification_eval_plan.yaml
```

## 5. Taxonomy v2

기존 taxonomy는 너무 coarse했다.

```yaml
old_taxonomy:
  - document
  - scene_text
  - ui_screen
  - chart
```

Track A v2에서는 최소 4축으로 나눈다.

```yaml
lora_taxonomy_v2:
  domain:
    - document
    - scene_text
    - ui_screen
    - chart

  evidence_type:
    - small_text
    - field_value
    - table_cell
    - axis_label
    - ui_status
    - visual_symbol

  operation:
    - read
    - locate
    - bind_label_to_value
    - compare
    - normalize_answer
    - structured_output

  failure_mode:
    - missed_evidence
    - wrong_region
    - label_value_mismatch
    - distractor_confusion
    - low_res_ambiguity
    - wrong_adapter_confidence_gain
```

예시:

```text
document / field_value / bind_label_to_value / distractor_confusion
chart / table_cell / locate / label_value_mismatch
ui_screen / ui_status / bind_label_to_value / distractor_confusion
scene_text / small_text / read / low_res_ambiguity
```

## 6. AdapterCard v2

각 LoRA는 weight가 아니라 certification card를 가져야 한다.

```yaml
AdapterCard:
  adapter_id: "doc_field_bind_r4_v1"
  base_backbone: "Qwen3-VL-4B"
  teacher_model: "google/gemma-4-26B-A4B-it"

  taxonomy:
    domain: "document"
    evidence_type: "field_value"
    operation: "bind_label_to_value"
    failure_mode: "distractor_confusion"

  training:
    curriculum_id: "simula_doc_field_bind_v1"
    source_trace_ids: []
    train_samples: 128
    holdout_samples: 64
    label_mask_mode: "answer_only"

  structure:
    rank: 4
    alpha: 8
    target_modules: ["q_proj", "v_proj"]

  serving:
    adapter_memory_mb: null
    attach_latency_ms: null
    switch_latency_ms: null

  certification:
    base_score: null
    correct_adapter_score: null
    wrong_adapter_score: null
    random_adapter_score: null
    gain_vs_base: null
    margin_vs_wrong: null
    wrong_adapter_damage: null
    status: "experimental"
```

## 7. Adapter-Sensitive Dataset

다음 dataset은 OCR 자체보다 label-value binding을 어렵게 만들어야 한다.

```yaml
adapter_sensitive_dataset:
  goal:
    - base model이 종종 헷갈림
    - correct LoRA가 배울 수 있음
    - wrong LoRA는 도움이 되지 않음
    - taxonomy별 차이가 score로 드러남

  hardening:
    - small font
    - low contrast
    - multiple distractor codes
    - similar labels
    - target outside center
    - domain-specific layout
```

예시:

```yaml
document_field_bind:
  prompt: "Return the code next to WORK ORDER."
  visible_text:
    - "WORK ID: A12B"
    - "ORDER TYPE: C33X"
    - "WORK ORDER: W45Q"
  expected_answer: "W45Q"

chart_table_cell:
  prompt: "Return the code in row Q2 and column East."
  distractors:
    - nearby cells
    - similar row labels
    - similar column labels

ui_status_bind:
  prompt: "Return the alert code beside the disabled button."
  distractors:
    - multiple buttons
    - multiple status labels
    - multiple alert codes
```

## 8. Gates

Track A v2는 세 gate로 나눠 닫는다.

### Gate 1. Single LoRA Learns

```yaml
pass_if:
  correct_lora_train_score: "> base_train_score"
  correct_lora_holdout_score: ">= base_holdout_score"
```

처음에는 train overfit도 허용한다. adapter가 실제로 output을 바꾸는지 먼저 본다.

### Gate 2. Correct Beats Wrong

```yaml
pass_if:
  correct_lora_holdout_score: "> wrong_lora_holdout_score + 0.05"
```

이 gate가 핵심이다. 통과하지 못하면 taxonomy나 dataset이 adapter-sensitive하지 않은 것이다.

### Gate 3. Router Selects Adapter

```yaml
pass_if:
  taxonomy_router_top1_hit: "> random_baseline"
  routed_score: "close_to_oracle_adapter"
  wrong_adapter_damage: "measured_and_bounded"
```

이후에야 multi-LoRA routing utility claim을 열 수 있다.

## 9. Track B의 위치

Track B는 유지하되, 메인 contribution에서 내린다.

```yaml
track_b_role:
  keep: true
  expand_now: false
  use_as:
    - visual evidence cost control
    - ROI/input compression baseline
    - controlled input budget for Track A experiments
  do_not_claim:
    - foveated vision novelty
    - OCR ROI broad generalization
    - production-ready visual token reduction
```

Track B 문구는 다음 정도로 제한한다.

```text
We use a foveated evidence path as a controlled input-cost module for adapter certification.
```

## 10. 다음 작업

```yaml
next_commit_theme:
  name: "Track A v2 Simula compiler scaffold"
  tasks:
    - add AdapterCard v2 schema
    - add Simula curriculum manifest schema
    - add adapter-sensitive manifest generator
    - add base/correct/wrong/random certification runner
    - update README and paper outline around Track A v2
```

## 11. 새 논문 제목 후보

```text
Simula-Compiled LoRA Banks for Low-VRAM Vision Specialist Consolidation
```

또는:

```text
Offline-Certified Taxonomy LoRA Banks for Shared-Backbone Vision Specialists
```

한국어 작업 제목:

```text
저 VRAM 비전 전문가 통합을 위한 Simula-Compiled Taxonomy LoRA Bank
```

## 12. 새 contribution 구조

```yaml
contributions:
  C1:
    title: "Simula-compiled taxonomy LoRA bank"
    content:
      - "failure traces를 taxonomy별 adapter curriculum으로 변환"

  C2:
    title: "Offline adapter certification"
    content:
      - "base/correct/wrong/random adapter 비교"
      - "gain, margin, wrong-adapter damage 기록"

  C3:
    title: "VRAM-aware shared-backbone specialist consolidation"
    content:
      - "full specialist reload vs resident LoRA bank memory/switching cost 비교"

  C4_supporting:
    title: "Foveated evidence as input-cost control"
    content:
      - "Track B는 adapter certification의 visual evidence budget을 통제하는 보조 모듈"
```

## 13. 현재 표현 원칙

```yaml
say:
  - "Track A is the main research axis."
  - "Track B is a supporting input-cost control module."
  - "Current Track A results are path smoke plus negative evidence."
  - "The next goal is adapter-sensitive certification."

do_not_say:
  - "Track B is the main contribution."
  - "trained LoRA improves accuracy."
  - "multi-adapter routing improves accuracy."
  - "Gemma teacher labels are final ground truth."
```
