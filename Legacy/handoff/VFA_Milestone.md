# VFA Milestone Handoff for Codex

Recommended repo path: `docs/30_paper_notes/milestone_handoff_for_codex_ko.md`
Status: active handoff / milestone map, updated for Track A v2 reframe
Audience: Codex or any coding agent continuing the repository work
Latest pushed commit: `fde0e24 Close external diagnostic milestones`

---

## 0. Core Thesis

This repository now centers on **Track A v2: Simula-compiled taxonomy LoRA bank**.

```text
Track A v2. Simula-compiled taxonomy LoRA bank
  failure traces / wrong answers / low-confidence samples
  -> Gemma 4 26B teacher annotations
  -> Simula curriculum compiler
  -> adapter-sensitive LoRA candidates
  -> AdapterCard certification
  -> one shared VLM backbone + resident LoRA bank

Track B support. Visual evidence compression
  full high-resolution visual context
  -> low-resolution global view + high-resolution ROI glimpses
  -> controlled input budget for Track A certification
```

The previous two-track results are not discarded. They are reinterpreted as follows.

```yaml
Track_A_v2_main:
  - adapter-sensitive curriculum generation
  - LoRA certification with base/correct/wrong/random comparisons
  - shared-backbone specialist consolidation
  - duplicated specialist backbone residency
  - full model reload / swap latency

Track_B_supports:
  - visual token count
  - visual KV/cache pressure
  - prefill / visual evidence cost
  - incremental visual peak memory
```

Do **not** collapse these into one claim.
Track A v2 is the paper axis. Track B is an input-cost control module.

---

## 1. Claim Rules

```yaml
safe_now:
  - "The project has been reframed around Track A v2: Simula-compiled taxonomy LoRA bank."
  - "Gemma 4 26B is a teacher/annotator/curriculum generator, not the runtime low-VRAM backbone."
  - "Existing Track B/ROI results are supporting visual evidence cost-control diagnostics."
  - "External n=32 no-gain and multi-LoRA wrong-damage=0.0 are negative evidence that the current task/taxonomy is not adapter-sensitive."
  - "RTX 3090 real CUDA memory/token accounting path works."
  - "Manifest images flow into full/low-res/ROI evidence paths."
  - "Controlled tiny scored diagnostic validation is available."
  - "ROI source quality strongly affects task-score retention under the same foveated token budget."
  - "OCR detector ROI path works as a smoke/diagnostic path."
  - "Sequential full-model reload and actual PEFT attach have been measured as system baselines."
  - "Tiny LoRA train/save/load path works with answer-only label masking."
  - "64 unique controlled tiny manifest with train/holdout split is available."
  - "OCR detector ROI stability has been measured on 64 unique samples with repeats=3."
  - "Tiny LoRA train/holdout evaluation path works on the controlled tiny set."
  - "Trained tiny LoRA can be loaded as actual PEFT for C0/C3/C4/C5/C6/C7 diagnostic matrix."
  - "External tiny n=32 diagnostic subset has been measured."
  - "Actual PEFT trained adapter has been compared against an external n=32 baseline with no gain observed."
  - "Four separate trained LoRA adapters can be loaded as a multi-adapter bank and switched with set_adapter."
  - "Qwen2-VL-2B-Instruct has been measured as one lightweight backbone candidate."

not_yet:
  - "Simula compiler is implemented and certified"
  - "AdapterCard v2 certification gates have passed"
  - "trained LoRA improves accuracy"
  - "OCR detector ROI generalizes to external benchmarks"
  - "FoveateR learned policy replaces oracle/layout ROI"
  - "multi-trained-LoRA bank routing improves accuracy"
  - "production p95/p99 serving is validated"
  - "Qwen3-VL-4B is the final low-end deployment backbone"
```

Use these terms consistently.

```yaml
path_smoke:
  meaning: "code path executes and metrics are logged"

diagnostic_validation:
  meaning: "controlled tiny set shows a measurable effect"

promotion_claim:
  meaning: "method is good enough to become main runtime evidence"

promotion_gate:
  default: false
```

---

## 2. Completed Milestones

### M0. Research Reframe / Repo Structure

```yaml
status: closed
evidence:
  - README defines Track A v2 as the main thesis
  - Track B is limited to visual evidence cost control
  - docs/30_paper_notes/track_a_v2_reframe_ko.md records the reframe
  - docs split into overview / protocols / results / paper notes
  - raw run artifacts are local-only under `.local/runs/`
  - committed artifacts are result briefs only
```

Current active layout:

```text
configs/3090/
docs/00_overview/
docs/10_protocols/
docs/20_results/
docs/30_paper_notes/
schemas/3090/
scripts/
src/vfa_policy/
.local/   # local-only
Legacy/   # archived previous direction
```

---

### M1. C0-C7 Validation Matrix + Gates

```yaml
status: closed
completed:
  - DEFAULT_CELLS includes C0-C7
  - MINIMUM_COMPLETION_CELLS = C0-C5
  - EXTENDED_COMPLETION_CELLS = C0-C7
  - completion_gate, measurement_gate, promotion_gate separated
  - minimum and extended completion gates are reported separately
```

Matrix meaning:

```yaml
C0: shared backbone + full image
C1: shared backbone + foveated ROI
C2: shared backbone + oracle LoRA + full image
C3: taxonomy LoRA proxy/adapter path + full image
C4: taxonomy LoRA proxy/adapter path + foveated ROI
C5: taxonomy LoRA proxy/adapter path + oracle ROI
C6: taxonomy LoRA proxy/adapter path + low-res only
C7: taxonomy LoRA proxy/adapter path + controlled fallback
```

---

### M2. Real CUDA / Real Image Source Semantics

```yaml
status: closed
completed:
  - `--data-mode` supports `synthetic_probe`, `real_task_manifest`, `tiny_scored_manifest`
  - `--manifest` connects JSONL manifest to runner
  - source semantics record:
      image_source
      roi_source
      selected_image_paths
      actual_image_execution
      real_measurement_fields
      estimate_or_proxy_fields
```

Important distinction:

```yaml
real_measurement:
  - base_after_load_allocated_mb
  - base_after_load_reserved_mb
  - visual_incremental_peak_mb
  - visual_token_count from Qwen image_grid_thw
  - prefill_latency_ms
  - generation_latency_ms

proxy_or_estimate:
  - adapter card memory unless actual_loaded_adapter
  - multi-specialist resident estimate
  - generate_extra_peak_over_prefill_mb
  - verifier score unless external verifier exists
```

---

### M3. Controlled Tiny Scored Validation

```yaml
status: closed_for_diagnostic
data:
  type: "controlled tiny scored image set"
  score_source: "normalized_answer_match"
  broad_benchmark: false
```

Key diagnostic result:

```yaml
C3_full_image:
  task_score_mean: 1.0 in latest unique64 diagnostic
  visual_tokens: 768

C4_foveated_ROI_with_good_ROI:
  task_score_mean: 0.890625 to 0.96875 depending on ROI source/run
  visual_tokens: 296

C6_low_res_only:
  task_score_mean: 0.21875 in latest unique64 diagnostic
  visual_tokens: 100
```

Interpretation:

```text
Low-res only is cheap but loses evidence.
Full image is strong but token-heavy.
Good ROI preserves much of the full-image score while reducing visual tokens.
```

---

### M4. ROI Source Comparison

```yaml
status: controlled_tiny_closed
roi_sources:
  center_crop:
    role: cheap heuristic baseline
    result: fails when target evidence is outside crop

  oracle_box:
    role: upper bound

  layout_proxy_box:
    role: controlled target-aware proxy

  ocr_detector_box:
    role: external OCR detector output
    current_status: 64 unique repeats=3 controlled diagnostic
```

Current OCR detector state:

```yaml
detector: RapidOCR default, pytesseract fallback
manifest_generation: 64/64 boxes generated in latest controlled set
unique64_repeats3_run:
  plan: ".local/runs/roi_stability_64_repeats3_plan.json"
  samples_per_run: 64
  unique_manifest_samples: 64
  repeats: 3
  roi_sources: [center_crop, oracle_box, layout_proxy_box, ocr_detector_box]
  cells: [C0, C3, C4, C5, C6, C7]
  commands_completed: 12
  returncodes: [0]
  measurement_gate: true
```

Do not claim broad `ocr_detector_box` generalization yet. Current external evidence is a tiny n=32 diagnostic subset.

---

### M5. Fallback Metric Semantics

```yaml
status: closed
completed:
  - controlled fallback peak split into conditional and all-sample fields
  - fallback_rate is reported
  - normal path peak is not overwritten by fallback peak
```

Use these fields in tables:

```yaml
controlled_fallback_peak_mb_conditional_mean:
  meaning: mean over fallback-executed samples only

controlled_fallback_peak_mb_all_samples_mean:
  meaning: fallback-aware peak over all samples

controlled_fallback_rate:
  meaning: fraction of samples using controlled fallback
```

---

### M6. Sequential Specialist Swap Smoke

```yaml
status: closed_as_smoke
result:
  model_load_latency_ms_mean: about 4651 ms/load
  measured_sequential_swap_available: true
  measured_joint_residency_available: false
```

Safe claim:

```text
Sequential full-model reload is measured as a latency baseline.
```

Unsafe claim:

```text
Multiple different full specialist VLMs were jointly measured as resident.
```

---

### M7. Actual PEFT Attach / Tiny LoRA Save-Load Smoke

```yaml
status: path_closed_plus_controlled_train_holdout
completed:
  - actual PEFT attach smoke
  - PEFT memory delta measured
  - tiny LoRA train/save/load path
  - actual_loaded_adapter source semantics
  - answer-only label masking implemented
  - 32-step tiny LoRA train/holdout evaluation
  - actual PEFT C0/C3/C4/C5/C6/C7 diagnostic matrix
```

Known current result:

```yaml
rank: 4
target_modules: [q_proj, v_proj]
trainable_lora_parameters: 1474560
peft_allocated_delta_mb: about 5.625
```

Tiny LoRA training status:

```yaml
label_mask_mode: answer_only
supervised_token_count_mean: about 6
train_steps: 32 in latest controlled train/holdout run
train_samples: 32
holdout_samples: 32
train_score_mean: 0.875
holdout_score_mean: 0.9375
accuracy_gain_claim: false
```

---

## 3. Current Best Evidence Summary

Use this as the short internal summary.

```text
Track A v2 is now the main paper axis:
offline Simula compiles failure traces into adapter-sensitive curricula,
Gemma 4 26B acts as teacher/annotator,
and AdapterCard certification compares base/correct/wrong/random adapters.

The strongest current Track A evidence is path smoke plus negative evidence:
full-model reload latency, actual PEFT attach/load memory, trained-tiny-LoRA
actual PEFT C0/C3/C4/C5/C6/C7 diagnostic matrix, and multi-adapter bank load/switch are measured.
External baseline-vs-trained comparison showed no trained-LoRA accuracy gain.
Multi-adapter bank load/switch path is measured, but correct/wrong adapter separation is not validated.

The strongest current Track B evidence is diagnostic support:
under controlled tiny scored tasks, ROI quality determines whether visual-token savings preserve task score.
Good ROI paths reduce visual tokens from 768 to 296 while keeping scores near full-image levels.
Low-res-only reduces tokens further but loses task evidence.
```

```yaml
track_a_v2_interpretation:
  path_smoke: closed
  adapter_sensitive_utility: not_yet
  next_step: "design Simula/Gemma teacher curriculum and AdapterCard v2 gates"
```

---

## 4. Milestones After Unique64 Pass

### R1. Expand Manifest to Unique Samples

```yaml
status: closed_for_controlled_unique64
completed:
  - generated 64 unique controlled samples
  - recorded train/holdout split
  - kept domains balanced
  - varied position, difficulty, and ROI failure modes

distribution:
  document_or_receipt: 16
  scene_text_or_ocr: 16
  ui_screen: 16
  chart_or_table: 16
split:
  train: 32
  holdout: 32
```

When expanding, vary:

```yaml
position:
  - center
  - top_left
  - top_right
  - bottom_left
  - bottom_right
  - near_edge

difficulty:
  - large_text_no_distractor
  - medium_text_few_distractors
  - small_text_many_distractors

roi_failure_modes:
  - center_crop_should_work
  - center_crop_should_fail
  - ocr_union_should_work
  - ocr_union_too_large_or_distracted
```

---

### R2. OCR Detector Repeats=3 Stability

```yaml
status: closed_for_controlled_unique64_repeats3
run:
  plan: ".local/runs/roi_stability_64_repeats3_plan.json"
  roi_sources:
    - center_crop
    - oracle_box
    - layout_proxy_box
    - ocr_detector_box
  repeats: 3
  samples_per_run: 64
  cells:
    - C0
    - C3
    - C4
    - C5
    - C6
    - C7
  commands_completed: 12
  returncodes: [0]

key_c4_scores:
  center_crop: 0.359375
  oracle_box: 0.96875
  layout_proxy_box: 0.953125
  ocr_detector_box: 0.890625

key_c6_low_res_score: 0.21875
```

---

### R3. Tiny LoRA Train/Holdout Evaluation

```yaml
status: closed_for_controlled_train_holdout_path
run_id: "20260524T114337Z-tiny_lora_train"
train_steps: 32
split:
  train: 32
  holdout: 32
train_score_mean: 0.875
holdout_score_mean: 0.9375
adapter_memory_delta_mb: about 5.625
label_mask_mode: answer_only
```

Do not open `trained_lora_accuracy_gain` until there is a clearly defined baseline-vs-trained comparison and stronger held-out or external evidence.

---

### R4. Actual PEFT Full C-Matrix

```yaml
status: closed_for_minimum_actual_peft_diagnostic
run_id: "20260524T114456Z-3090_tiny_scored_trained_lora_full_cmatrix"
cells: [C0, C3, C4, C5, C6, C7]
adapter_memory_source: actual_loaded_adapter
measurement_gate: true
completion_gate: false
completion_gate_reason: "C1/C2 omitted by design for minimum actual PEFT diagnostic matrix"
key_scores:
  C0: 1.0
  C3: 1.0
  C4: 0.90625
  C5: 0.96875
  C6: 0.21875
  C7: 0.90625
```

---

### R5. External Tiny Benchmark Subset

```yaml
status: closed_for_external_n32_diagnostic
manifest:
  path: ".local/data/external_tiny_manifest/manifest.jsonl"
  samples: 64
  sources:
    lmms-lab/textvqa: 16
    lmms-lab/DocVQA: 16
    lmms-lab/ChartQA: 16
    rootsautomation/RICO-ScreenQA: 16
ocr_detector:
  manifest: ".local/data/external_tiny_manifest/manifest_ocr_detector.jsonl"
  available: "63/64"
  primary_n32_manifest: ".local/data/external_tiny_manifest/manifest_ocr_detector_primary_n32.jsonl"
  primary_n32_distribution:
    textvqa: 8
    docvqa: 8
    chartqa: 8
    screenqa: 8
qwen3_reference_run: "20260525T005611Z-3090_external_tiny_ocr_detector_n32"
qwen3_reference_scores:
  C0: 0.850260
  C3: 0.850260
  C4: 0.799913
  C6: 0.694501
  C7: 0.799913
actual_peft_external_run: "20260525T005917Z-3090_external_tiny_trained_lora_n32"
trained_lora_gain_verdict: "no_gain_observed"
```

---

### R6. Lightweight Backbone Sweep

```yaml
status: closed_for_one_lightweight_candidate
candidate: "Qwen/Qwen2-VL-2B-Instruct"
run_id: "20260525T011135Z-3090_qwen2_vl_2b_external_tiny_n32"
cells: [C0, C3, C4, C6]
samples: 32
base_after_load_allocated_mb: 4213.307
scores:
  C0: 0.681858
  C3: 0.681858
  C4: 0.751997
  C6: 0.644618
claim_boundary:
  final_low_end_backbone_claim: false
  next_candidates_optional: "quantized or additional 1B~3B candidates"
```

---

### R7. Multi-Trained-LoRA Bank Smoke

```yaml
status: closed_for_path_smoke
adapters:
  document: ".local/adapters/tiny_lora_document_latest"
  scene_text: ".local/adapters/tiny_lora_scene_text_latest"
  ui_screen: ".local/adapters/tiny_lora_ui_screen_latest"
  chart: ".local/adapters/tiny_lora_chart_latest"
run_id: "20260525T010610Z-multi_lora_bank_smoke"
samples: 32
adapter_bank_allocated_delta_mb: 22.5
correct_score_mean: 0.90625
wrong_score_mean: 0.90625
correct_minus_wrong_score_mean: 0.0
claim_boundary:
  path_smoke: true
  routing_accuracy_gain_claim: false
```

---

## 5. Immediate Codex To-Do Queue

```yaml
todo_next:
  - "Add AdapterCard v2 schema."
  - "Add Simula curriculum manifest schema."
  - "Design adapter-specific tasks where wrong-adapter damage is expected and measurable."
  - "Run base/correct/wrong/random certification before opening LoRA utility claims."
  - "Keep Track B as visual evidence cost control, not the main contribution."
  - "Do not open trained LoRA gain claim unless baseline improvement appears."
```

---

## 6. Anti-Goals

Do not implement these yet unless explicitly requested.

```yaml
do_not_do_yet:
  - production serving scheduler
  - JEPA / LeWM routing promotion
  - graph memory commit system
  - broad benchmark superiority claim
  - Track B as main novelty claim
  - Gemma teacher labels as final ground truth
  - trained LoRA gain claim without baseline improvement
  - multi-adapter routing utility claim without wrong-adapter damage
  - full specialist joint residency claim on 3090
```

---

## 7. Paper-Ready Milestone Criteria

The project becomes paper-draft-ready when the following are available.

```yaml
paper_ready_minimum:
  available_now:
    - Track A v2 reframe
    - 64 unique controlled manifest
    - ROI source comparison with repeats=3
    - tiny train/holdout LoRA evaluation
    - actual PEFT C0/C3/C4/C5/C6/C7 diagnostic matrix
    - external tiny n=32 diagnostic subset
    - external baseline-vs-trained actual PEFT comparison
    - multi-trained-LoRA bank path smoke
    - one lightweight backbone candidate sweep
    - sequential specialist reload baseline
    - claim table updated with safe/not-yet boundaries
  still_needed_for_stronger_claims:
    - AdapterCard v2 schema
    - Simula curriculum manifest schema
    - adapter-sensitive dataset with correct-vs-wrong margin
    - larger external or human-evaluated subset after adapter-sensitive design is stable
    - adapter-specific wrong-adapter damage evidence
    - production serving harness before p95/p99 claims
```

Until then, use wording like:

```text
Track A v2 diagnostic pilot for Simula-compiled taxonomy LoRA banks
```

not:

```text
general benchmark validation
production-ready low-VRAM serving
```
