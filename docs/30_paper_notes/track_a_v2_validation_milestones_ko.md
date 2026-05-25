# Track A v2 검증 마일스톤

Status: previous proxy-tainted closure invalidated / no-proxy rerun required
Date: 2026-05-25
Last updated: 2026-05-25
Scope: Simula-compiled taxonomy LoRA bank / Track A 중심 재정렬
Recommended repo path: `docs/30_paper_notes/track_a_v2_validation_milestones_ko.md`

Proxy quarantine update: 2026-05-25

```yaml
closure_meaning: "이전 M0-M11 진단 폐쇄는 proxy/mixed/estimate/fallback evidence가 섞여 검증 근거에서 폐기한다."
quarantined_path: "trashbin/proxy_result_quarantine_2026-05-25/"
closure_status:
  M0: closed
  M1: closed
  M2: closed
  M3: invalidated_fallback
  M4: invalidated_proxy
  M5: retained_actual_only_brief_but_not_promotion
  M6: invalidated_mixed_proxy
  M7: invalidated_mixed_proxy
  M8: invalidated_due_proxy_certification
  M9: requires_actual_only_resummary
  M10: requires_actual_only_resummary
  M11: invalidated
promotion_gate: false
previous_result_brief: "quarantined: docs/20_results/2026-05-25_track_a_v2_final_closure_ko.md"
next_focus:
  - "no-proxy teacher/curriculum path"
  - "actual base/correct/wrong/random scoring only"
  - "actual adapter bank resummary without proxy-tainted configs"
```

---

## 0. 목적

Track A v2의 목표는 기존의 “LoRA attach가 된다” 수준을 넘어서, 아래 질문을 단계적으로 검증하는 것이다.

```text
오프라인 Simula 루프가 실패 trace를 taxonomy별 LoRA curriculum으로 컴파일하고,
이를 검증된 adapter bank로 묶어 여러 vision specialist를 shared backbone 위에 통합할 수 있는가?
```

Track B는 메인 contribution이 아니라, Track A 실험에서 visual evidence cost를 통제하기 위한 보조 모듈로 둔다.

```yaml
track_a_main:
  - Simula-compiled taxonomy LoRA bank
  - offline curriculum generation
  - adapter-sensitive LoRA training
  - certification by base/correct/wrong/random comparison
  - certified adapter card registry

track_b_support:
  - ROI / foveated evidence path
  - input-cost control
  - visual token budget normalization
```

---

## 1. 전체 검증 구조

Track A v2는 아래 순서로만 승격한다.

```text
M0. Reframe lock
M1. Schema and registry contract
M2. Adapter-sensitive dataset
M3. Simula teacher/compiler loop
M4. Base difficulty audit
M5. Single LoRA learns
M6. Correct LoRA beats wrong LoRA
M7. AdapterCard certification
M8. Taxonomy router selection
M9. Multi-adapter bank serving
M10. Compatibility / collapse audit
M11. Paper-ready Track A table
```

핵심 gate는 세 개다.

```yaml
Gate_1_single_lora_learns:
  asks: "LoRA가 실제로 output을 바꿔 task를 배울 수 있는가?"

Gate_2_correct_beats_wrong:
  asks: "correct LoRA가 wrong LoRA보다 의미 있게 나은가?"

Gate_3_router_selects_adapter:
  asks: "taxonomy router가 oracle adapter에 가까운 선택을 하는가?"
```

Gate 2를 통과하기 전에는 multi-LoRA routing utility claim을 열지 않는다.

---

## 2. M0 — Reframe Lock

### 목표

논문 중심축을 Track A로 고정한다.

```yaml
main_axis:
  - Simula-compiled taxonomy LoRA bank

support_axis:
  - Foveated / ROI evidence cost control
```

### 필요한 작업

```yaml
tasks:
  - README의 contribution 문구를 Track A 중심으로 조정
  - Track B는 support / related / input-cost control로 이동
  - 기존 ROI result는 버리지 않고 supporting evidence로 유지
  - paper outline을 Track A 중심으로 재작성
```

### 산출물

```text
docs/30_paper_notes/track_a_v2_reframe_ko.md
docs/30_paper_notes/track_a_v2_validation_milestones_ko.md
docs/30_paper_notes/paper_outline_ko.md
```

### 통과 조건

```yaml
pass_if:
  - "README와 paper outline에서 Track A가 main contribution으로 표시됨"
  - "Track B가 visual evidence cost control로 제한됨"
  - "trained LoRA gain / routing utility claim은 아직 닫혀 있음"
```

---

## 3. M1 — Schema and Registry Contract

### 목표

LoRA를 weight 파일이 아니라 **AdapterCard v2 + certification record**로 관리한다.

### 필요한 스키마

```text
schemas/track_a_v2/adapter_card_v2.example.yaml
schemas/track_a_v2/curriculum_manifest.example.jsonl
schemas/track_a_v2/teacher_annotation.example.jsonl
schemas/track_a_v2/certification_result.example.yaml
schemas/track_a_v2/compatibility_edge.example.yaml
```

### AdapterCard v2 필수 필드

```yaml
AdapterCard:
  adapter_id: string
  base_backbone: string
  teacher_model: string

  taxonomy:
    domain: document | scene_text | ui_screen | chart
    evidence_type: small_text | field_value | table_cell | axis_label | ui_status | visual_symbol
    operation: read | locate | bind_label_to_value | compare | normalize_answer | structured_output
    failure_mode: missed_evidence | wrong_region | label_value_mismatch | distractor_confusion | low_res_ambiguity | wrong_adapter_confidence_gain

  training:
    curriculum_id: string
    source_trace_ids: list
    train_samples: int
    holdout_samples: int
    label_mask_mode: answer_only

  structure:
    rank: int
    alpha: int
    target_modules: list

  serving:
    adapter_memory_mb: float | null
    attach_latency_ms: float | null
    switch_latency_ms: float | null

  certification:
    base_score: float | null
    correct_adapter_score: float | null
    wrong_adapter_score: float | null
    random_adapter_score: float | null
    gain_vs_base: float | null
    margin_vs_wrong: float | null
    wrong_adapter_damage: float | null
    status: experimental | certified | rejected | quarantined
```

### 통과 조건

```yaml
pass_if:
  - "AdapterCard v2 example validates by schema or lightweight checker"
  - "curriculum manifest row can point to taxonomy and expected answer"
  - "certification result can be merged back into AdapterCard"
```

---

## 4. M2 — Adapter-Sensitive Dataset

### 목표

기존 tiny task보다 LoRA specialization이 드러나는 dataset을 만든다.

현재 negative result의 핵심 진단은 다음이다.

```text
현재 task와 taxonomy는 adapter-sensitive하지 않다.
```

따라서 새 dataset은 base model이 헷갈릴 수 있고, correct LoRA가 배울 수 있으며, wrong LoRA는 도움이 되지 않는 구조여야 한다.

### Dataset 설계

```yaml
adapter_sensitive_dataset:
  domains:
    - document
    - scene_text
    - ui_screen
    - chart

  task_types:
    - label_value_binding
    - table_cell_lookup
    - UI_status_binding
    - distractor_code_selection
    - small_text_reading

  hardening:
    - small font
    - low contrast
    - multiple distractor codes
    - similar labels
    - target outside center
    - domain-specific layout
    - code values not reusable across train/holdout
```

### 예시 taxonomy task

```yaml
document_field_bind:
  prompt: "Return the code next to WORK ORDER."
  visible_text:
    - "WORK ID: A12B"
    - "ORDER TYPE: C33X"
    - "WORK ORDER: W45Q"
  expected_answer: "W45Q"
  taxonomy:
    domain: document
    evidence_type: field_value
    operation: bind_label_to_value
    failure_mode: distractor_confusion

chart_table_cell:
  prompt: "Return the code in row Q2 and column East."
  taxonomy:
    domain: chart
    evidence_type: table_cell
    operation: locate
    failure_mode: label_value_mismatch

ui_status_bind:
  prompt: "Return the alert code beside the disabled button."
  taxonomy:
    domain: ui_screen
    evidence_type: ui_status
    operation: bind_label_to_value
    failure_mode: distractor_confusion
```

### 최소 규모

```yaml
minimum:
  train_per_taxonomy: 32
  holdout_per_taxonomy: 32
  taxonomies: 4
  total_train: 128
  total_holdout: 128

better:
  train_per_taxonomy: 64
  holdout_per_taxonomy: 64
```

### 산출물

```text
.local/data/track_a_v2_adapter_sensitive/manifest.jsonl
.local/data/track_a_v2_adapter_sensitive/train.jsonl
.local/data/track_a_v2_adapter_sensitive/holdout.jsonl
docs/20_results/YYYY-MM-DD_adapter_sensitive_dataset_brief_ko.md
```

### 통과 조건

```yaml
pass_if:
  - "각 taxonomy가 train/holdout 모두 보유"
  - "center_crop, OCR ROI, oracle ROI source 기록"
  - "base model score가 너무 높지 않음"
  - "base holdout score가 0.95 이상이면 task가 너무 쉬운 것으로 보고 hardening 필요"
```

---

## 5. M3 — Simula Teacher / Compiler Loop

### 목표

Gemma 4 26B 또는 teacher model을 runtime model이 아니라 offline compiler로 사용한다.

### Teacher 역할

```yaml
teacher_role:
  - failure annotator
  - taxonomy labeler
  - curriculum generator
  - hard negative generator
  - expected answer / rationale proposer

not_teacher_role:
  - runtime backbone
  - final certification authority
```

### 입력

```yaml
simula_inputs:
  - route_traces.jsonl
  - failed answers
  - low confidence samples
  - wrong adapter records
  - ROI miss records
  - base model errors
```

### 출력

```yaml
simula_outputs:
  - curriculum_manifest.jsonl
  - teacher_annotations.jsonl
  - adapter_candidate_plan.yaml
  - certification_eval_plan.yaml
```

### 산출물

```text
scripts/compile_simula_curriculum.py
src/vfa_policy/track_a/simula_compiler.py
docs/20_results/YYYY-MM-DD_simula_curriculum_compile_brief_ko.md
```

### 통과 조건

```yaml
pass_if:
  - "teacher annotation row contains taxonomy v2"
  - "curriculum row contains answer and hard negatives"
  - "teacher label is marked as candidate, not final truth"
  - "certification plan uses base/correct/wrong/random comparison"
```

---

## 6. M4 — Base Difficulty Audit

### 목표

LoRA를 학습하기 전에 base model이 충분히 어려워하는지 확인한다.

### 실행

```yaml
run:
  model: shared backbone
  adapter: none
  dataset:
    - adapter_sensitive_train
    - adapter_sensitive_holdout

metrics:
  - base_train_score
  - base_holdout_score
  - per_taxonomy_score
  - error_type_distribution
```

### 통과 조건

```yaml
pass_if:
  base_holdout_score:
    lower_bound: 0.30
    upper_bound: 0.85

too_easy_if:
  base_holdout_score: ">= 0.90"

too_hard_if:
  base_holdout_score: "< 0.20"
```

### 이유

```text
base가 이미 너무 잘하면 LoRA gain이 안 보인다.
base가 너무 못하면 LoRA가 짧은 학습으로 회복하기 어렵다.
```

---

## 7. M5 — Gate 1: Single LoRA Learns

### 목표

각 taxonomy별 LoRA가 실제로 output을 바꿔 학습할 수 있는지 확인한다.

### 비교

```yaml
compare:
  - base_no_adapter
  - correct_lora
  - random_untrained_lora
```

### 실행 단위

```yaml
per_taxonomy:
  - document / field_value / bind_label_to_value / distractor_confusion
  - chart / table_cell / locate / label_value_mismatch
  - ui_screen / ui_status / bind_label_to_value / distractor_confusion
  - scene_text / small_text / read / low_res_ambiguity
```

### 통과 조건

```yaml
pass_if:
  correct_lora_train_score: "> base_train_score"
  correct_lora_holdout_score: ">= base_holdout_score"

acceptable_initially:
  - "train overfit is allowed"
  - "holdout no-gain is allowed only for first path smoke"
```

### 산출물

```text
.local/adapters/track_a_v2/<adapter_id>/
docs/20_results/YYYY-MM-DD_single_lora_learns_ko.md
```

---

## 8. M6 — Gate 2: Correct Beats Wrong

### 목표

taxonomy가 실제로 adapter selection에 의미가 있는지 확인한다.

### 비교

```yaml
compare:
  - base_no_adapter
  - correct_lora
  - wrong_domain_lora
  - wrong_operation_lora
  - random_untrained_lora
```

### 핵심 metric

```yaml
metrics:
  - correct_lora_holdout_score
  - wrong_lora_holdout_score
  - random_lora_holdout_score
  - margin_vs_wrong
  - wrong_adapter_damage
  - wrong_adapter_confidence_gain
```

### 통과 조건

```yaml
pass_if:
  margin_vs_wrong: ">= 0.05"

strong_pass_if:
  margin_vs_wrong: ">= 0.10"
  gain_vs_base: "> 0"

fail_if:
  margin_vs_wrong: "<= 0"
```

### 해석

```yaml
if_pass:
  - "taxonomy is adapter-sensitive"
  - "correct-vs-wrong adapter distinction exists"

if_fail:
  - "taxonomy too coarse"
  - "dataset not adapter-sensitive"
  - "LoRA training too weak"
  - "base model already solves task"
```

---

## 9. M7 — AdapterCard Certification

### 목표

Gate 1/2 결과를 AdapterCard v2에 반영한다.

### Certification status

```yaml
certification_status:
  certified:
    requires:
      - margin_vs_wrong >= 0.05
      - wrong_adapter_damage bounded
      - memory and attach latency measured

  experimental:
    requires:
      - training and loading path works
      - but margin not yet enough

  rejected:
    if:
      - correct adapter no better than wrong
      - adapter destabilizes output
      - wrong_adapter_confidence_gain high

  quarantined:
    if:
      - unsafe wrong confidence
      - repeated verifier false pass
```

### 산출물

```text
configs/track_a_v2/adapter_cards/*.yaml
docs/20_results/YYYY-MM-DD_adapter_certification_ko.md
```

---

## 10. M8 — Gate 3: Taxonomy Router Selects Adapter

### 목표

runtime에서 taxonomy router가 adapter를 고를 수 있는지 확인한다.

### Router 입력

```yaml
allowed_features:
  - question text
  - low-res global evidence
  - taxonomy v2 prediction
  - adapter card metadata
  - cost profile

forbidden_features:
  - oracle adapter id
  - dataset label leakage
  - expected answer
```

### 비교

```yaml
compare:
  - oracle_adapter
  - taxonomy_router
  - random_adapter
  - base_no_adapter
```

### 통과 조건

```yaml
pass_if:
  taxonomy_router_top1_hit: "> random_baseline"
  routed_score: "close_to_oracle_adapter"
  wrong_adapter_damage: "measured_and_bounded"

close_to_oracle_adapter:
  tolerance: "score drop <= 0.05"
```

### 산출물

```text
scripts/run_track_a_v2_router_eval.py
docs/20_results/YYYY-MM-DD_taxonomy_router_eval_ko.md
```

---

## 11. M9 — Multi-Adapter Bank Serving

### 목표

여러 certified adapter를 resident bank로 로드하고 switching cost를 측정한다.

### 실행

```yaml
bank:
  - document_adapter
  - scene_text_adapter
  - ui_screen_adapter
  - chart_adapter

measure:
  - adapter_bank_allocated_delta_mb
  - active_adapter_delta_mb
  - set_adapter_latency_mean_ms
  - set_adapter_latency_p95_ms
  - set_adapter_latency_p99_ms
  - full_model_reload_latency_ms
```

### 비교

```yaml
compare:
  - full model reload
  - single adapter attach
  - multi-adapter bank resident
  - set_adapter switch
```

### 통과 조건

```yaml
pass_if:
  adapter_bank_memory: "<< multi specialist model estimate"
  set_adapter_latency_p95_ms: "<< full model reload latency"
```

Accuracy claim은 M8이 통과해야만 연다.

---

## 12. M10 — Compatibility / Collapse Audit

### 목표

여러 LoRA가 동시에 있거나 routing될 때 collapse 위험을 측정한다.

### 측정

```yaml
collapse_metrics:
  - wrong_adapter_damage
  - wrong_adapter_confidence_gain
  - verifier_false_pass
  - score_drop_under_wrong_adapter
  - adapter_conflict_pair_count
```

### Pairwise compatibility

```yaml
compatibility_edge:
  adapter_i: string
  adapter_j: string
  same_domain: bool
  same_operation: bool
  behavioral_synergy: float
  conflict_score: float
  certified_together: bool
```

### 통과 조건

```yaml
pass_if:
  - high-risk adapter pairs are detected
  - unsafe pairs are not certified together
  - wrong adapter confidence gain is bounded
```

---

## 13. M11 — Paper-Ready Track A Evidence

### 최소 표

#### Table A1. Adapter-sensitive dataset audit

```text
taxonomy / base score / error type / task difficulty
```

#### Table A2. Correct vs wrong LoRA

```text
taxonomy / base / correct / wrong / random / margin
```

#### Table A3. AdapterCard certification

```text
adapter_id / taxonomy / memory / attach latency / gain / margin / status
```

#### Table A4. Router evaluation

```text
oracle / taxonomy router / random / base
```

#### Table A5. Resident bank system cost

```text
full model reload / single PEFT attach / multi-adapter bank / set_adapter switch
```

### Paper claim 열기 조건

```yaml
Track_A_claim_open_if:
  - Gate 1 passes for at least 2 taxonomies
  - Gate 2 passes for at least 2 taxonomies
  - AdapterCard certification exists
  - set_adapter latency and bank memory measured
  - router evaluation beats random
```

---

## 14. 현재 하지 말 것

```yaml
do_not_do_now:
  - JEPA / LeWM runtime routing
  - graph memory commit system
  - production serving scheduler
  - broad benchmark superiority claim
  - foveated vision novelty claim
  - Gemma teacher label as final truth
```

---

## 15. Closure Queue Result

```yaml
closed_commit_theme:
  name: "Track A v2 diagnostic milestone closure"

completed:
  - "schemas/track_a_v2/adapter_card_v2.example.yaml"
  - "schemas/track_a_v2/curriculum_manifest.example.jsonl"
  - "schemas/track_a_v2/teacher_annotation.example.jsonl"
  - "schemas/track_a_v2/certification_result.example.yaml"
  - "schemas/track_a_v2/compatibility_edge.example.yaml"
  - "src/vfa_policy/track_a/taxonomy.py"
  - "src/vfa_policy/track_a/adapter_card.py"
  - "scripts/prepare_adapter_sensitive_manifest.py"
  - "scripts/run_gemma_teacher_gguf.py"
  - "scripts/compile_simula_curriculum.py"
  - "scripts/run_track_a_v2_base_audit.py"
  - "scripts/train_track_a_v2_lora.py"
  - "scripts/run_track_a_v2_certification.py"
  - "scripts/run_track_a_v2_router_eval.py"
  - "README/docs wording synced with Track A v2 as main paper axis"

not_opened:
  - "Gemma teacher JSON success claim"
  - "fully actual correct-vs-wrong/random certification claim"
  - "router utility claim"
  - "paper-ready performance claim"
```

---

## 16. 최종 기준

Track A v2는 아래 문장을 실험적으로 뒷받침할 때 paper-ready가 된다.

```text
Offline Simula-style compilation can turn failure/taxonomy traces into adapter-sensitive LoRA curricula,
and certified LoRA adapters can be selected by taxonomy on a shared VLM backbone with measurable memory and switching advantages.
```

현재는 이 문장을 주장할 준비가 되지 않았다.
이전 M0-M11 진단 폐쇄 결과는 proxy-tainted evidence가 섞여 폐기했다. 다음 phase는 no-proxy evidence만으로 teacher/curriculum/certification을 다시 닫는 단계다.

## 17. 2026-05-25 Proxy Quarantine Record

```yaml
quarantined_outputs:
  trashbin_path: "trashbin/proxy_result_quarantine_2026-05-25/"
  reason: "proxy, mixed proxy, estimate, or deterministic fallback was used as validation evidence"
  result_briefs:
    - "docs/20_results/2026-05-24_metric_gate_semantics_closure_ko.md"
    - "docs/20_results/2026-05-24_ocr_detector_trained_lora_smoke_ko.md"
    - "docs/20_results/2026-05-24_p1_answer_mask_ocr_stability_ko.md"
    - "docs/20_results/2026-05-24_real_task_image_smoke_ko.md"
    - "docs/20_results/2026-05-24_reproducibility_source_semantics_closure_ko.md"
    - "docs/20_results/2026-05-24_scored_roi_swap_peft_validation_ko.md"
    - "docs/20_results/2026-05-24_unique64_stability_lora_peft_ko.md"
    - "docs/20_results/2026-05-25_external_n32_multi_lora_backbone_ko.md"
    - "docs/20_results/2026-05-25_track_a_v2_base_audit_ko.md"
    - "docs/20_results/2026-05-25_track_a_v2_certification_ko.md"
    - "docs/20_results/2026-05-25_track_a_v2_final_closure_ko.md"
    - "docs/20_results/2026-05-25_track_a_v2_router_bank_closure_ko.md"
    - "docs/20_results/2026-05-25_track_a_v2_teacher_curriculum_brief_ko.md"
  adapter_cards:
    - "configs/track_a_v2/adapter_cards/document_track_a_v2_r4_v1.yaml"
    - "configs/track_a_v2/adapter_cards/chart_track_a_v2_r4_v1.yaml"
  local_raw_runs:
    - ".local/runs/*-3090_*"
    - ".local/runs/*-specialist_swap_smoke"
    - ".local/runs/track_a_v2_base_audit"
    - ".local/runs/track_a_v2_certification"
    - ".local/runs/track_a_v2_router_eval"

retained_scaffold:
  schemas:
    - "schemas/track_a_v2/adapter_card_v2.example.yaml"
    - "schemas/track_a_v2/curriculum_manifest.example.jsonl"
    - "schemas/track_a_v2/teacher_annotation.example.jsonl"
    - "schemas/track_a_v2/certification_result.example.yaml"
    - "schemas/track_a_v2/compatibility_edge.example.yaml"
  scripts:
    - "scripts/setup_llama_cpp_windows.py"
    - "scripts/prepare_adapter_sensitive_manifest.py"
    - "scripts/run_gemma_teacher_gguf.py"
    - "scripts/compile_simula_curriculum.py"
    - "scripts/run_track_a_v2_base_audit.py"
    - "scripts/train_track_a_v2_lora.py"
    - "scripts/run_track_a_v2_certification.py"
    - "scripts/run_track_a_v2_router_eval.py"
  result_briefs:
    - "none"

important_boundary:
  gemma_teacher_json: "invalidated until valid model JSON exists without deterministic fallback"
  base_audit: "invalidated because it used deterministic proxy"
  certification: "invalidated because base/wrong/random were mixed proxy"
  router_utility_claim: false
  paper_ready_claim: false

docs_synced:
  - "README.md"
  - "docs/README.md"
  - "docs/00_overview/latest_run_status_ko.md"
  - "docs/20_results/README.md"
  - "docs/30_paper_notes/claim_table_ko.md"
  - "docs/30_paper_notes/ablation_table_plan_ko.md"
  - "docs/30_paper_notes/paper_outline_ko.md"
  - "docs/30_paper_notes/track_a_v2_reframe_ko.md"

needs_next:
  - "valid Gemma or replacement teacher JSON without deterministic fallback"
  - "actual base/correct/wrong/random certification scores only"
  - "actual adapter bank switching summary without proxy-tainted configs"
  - "router-selects-adapter utility only after actual correct-vs-wrong/random margin"
  - "production p95/p99 only after serving harness exists"
```
