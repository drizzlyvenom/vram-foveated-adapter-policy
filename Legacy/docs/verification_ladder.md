# Verification Ladder

Status: pilot guide  
Purpose: verify one connection at a time. Do not start with the full architecture.

## 0. Principle

A failed end-to-end run is not informative unless the failure can be localized. This ladder decomposes the architecture into stages. A later stage should not be implemented as the main path until the previous stage has passed its gates.

```text
Stage 0: RTX 3090 CostSim replay and metering contract
Stage 1: Foveation-only
Stage 2: LoRA isolation
Stage 3: Taxonomy-card router
Stage 4: LeWM feature augmentation
Stage 5: JEPA outcome predictor
Stage 6: Closed-loop verifier and fallback
```

Each stage must emit RouteTrace logs.

---

## Stage 0: RTX 3090 CostSim replay and metering contract

### Goal

Confirm that the repository can reproduce the already-completed RTX 3090 cost-simulation evidence inside the new logging contract.

This stage should not spend time creating a fresh scientific mock result. The project already has a 3090 feasibility run, so Stage 0 is now a replay/distillation step:

```text
existing 3090 CostSim CSVs -> RouteTrace JSONL -> summary.csv -> directionality checks
```

The scientific claim is limited to cost-model feasibility. Real VLM profiler measurements begin in Stage 1.

### Baselines

| ID | Source baseline | Mode | Purpose |
|---|---|---|---|
| S0-A | B0 | low_res_only_3090_prior | lower-cost baseline from the 3090 CostSim |
| S0-B | B1 | full_high_res_3090_prior | upper-cost / high-token baseline from the 3090 CostSim |
| S0-C | B2 | foveated_roi_3090_prior | ROI token-reduction baseline |
| S0-D | B4-lite | independent_adapter_bank_3090_prior | naive resident-adapter pressure baseline |
| S0-E | B5-lite | shared_adapter_bank_3090_prior | shared-bank resident-memory baseline |
| S0-F | B7-lite | budget_policy_3090_prior | budget-aware residency policy baseline |

### Source artifacts

```yaml
stage0_sources:
  summary_csv: output/experiment/3090_pilot_costsim/02_simulation_run/results/summary.csv
  aggregate_summary_csv: output/experiment/3090_pilot_costsim/02_simulation_run/results/aggregate_summary.csv
  primary_case_summary_csv: output/experiment/3090_pilot_costsim/02_simulation_run/results/primary_case_summary.csv
  source_status: existing_cost_model_feasibility_result
```

### Required logs

```yaml
required_logs:
  - sample_id
  - split
  - baseline_id
  - source_baseline
  - measurement_source
  - input_resolution
  - visual_token_count
  - peak_vram_mb
  - avg_vram_mb
  - reserved_vram_mb
  - kv_cache_estimate_mb
  - total_latency_ms
  - route_trace_path
```

### Pass gate

```text
- The existing 3090 CostSim rows are replayed or distilled without manual editing.
- RouteTrace JSONL is valid and preserves the source baseline mapping.
- summary.csv can be generated automatically from RouteTrace JSONL.
- Directionality checks match the 3090 prior: full_high_res costs more than low_res_only, ROI reduces visual tokens versus full_high_res, and budget_policy reduces resident adapter pressure versus independent all-resident baselines.
- Every cost and memory number is labeled as cost_model_3090, not as a real VLM profiler measurement.
```

### Optional 3090-only checks before new equipment arrives

These checks are still Stage 0 because they do not add new architecture.

```text
- Re-run the cost simulator with the same config and verify identical aggregate conclusions.
- Add a tiny CUDA availability and memory-reset sanity check on the RTX 3090.
- Add adapter-residency arithmetic checks for LoRA rank/slot/card metadata without loading a real VLM.
- Add a dry-run plot or table that compares B0/B1/B2/B4-lite/B5-lite/B7-lite under the new summary schema.
```

### Out-of-scope for Stage 0

```text
- Real VLM inference profiling
- online LoRA training
- LeWM or JEPA feature routing
- direct latent-to-LoRA routing
- claims about measured runtime accuracy or measured real latency
```

### Stop condition

If the 3090 CostSim source cannot be mapped into the logging contract, do not proceed to foveation or LoRA. Fix the replay and labeling first.

---

## Stage 1: Foveation-only validation

### Goal

Check whether ROI selection gives useful local evidence before adding any adapter.

### Baselines

| ID | ROI mode | Adapter | Purpose |
|---|---|---|---|
| S1-A | none | none | low-res baseline |
| S1-B | random_roi | none | crop distraction baseline |
| S1-C | learned_or_heuristic_roi | none | proposed foveation path |
| S1-D | oracle_roi | none | ROI upper bound, if annotations exist |
| S1-E | full_high_res | none | expensive reference |

### Metrics

```yaml
roi_metrics:
  - roi_recall_at_1
  - roi_recall_at_k
  - critical_evidence_miss_rate
  - wrong_crop_distraction_rate
  - visual_token_saved_vs_fullres
  - task_score_delta_vs_lowres
  - p95_latency_delta_vs_fullres
```

### Pass gate

```text
- Learned/heuristic ROI beats random ROI on task score or evidence recall.
- Wrong crop distraction is measured and not silently ignored.
- ROI path reduces visual token count or peak VRAM versus full_high_res.
```

### Stop condition

If learned ROI is not better than random ROI, do not attach LoRA routing yet. Improve ROI proposal or fallback first.

---

## Stage 2: LoRA isolation

### Goal

Verify that each adapter is useful and safe in isolation before routing it dynamically.

### Baselines

| ID | ROI | Adapter | Purpose |
|---|---|---|---|
| S2-A | learned_or_oracle | none | base ROI-only baseline |
| S2-B | learned_or_oracle | correct_lora | adapter upper bound |
| S2-C | learned_or_oracle | wrong_lora | damage test |
| S2-D | wrong_roi | correct_lora | ROI/adapter dependency test |
| S2-E | full_high_res | correct_lora | expensive adapter reference |

### Metrics

```yaml
adapter_metrics:
  - adapter_gain_vs_base
  - correct_lora_margin
  - wrong_adapter_damage
  - wrong_adapter_confidence_gain
  - general_regression
  - adapter_latency_overhead_ms
  - adapter_memory_mb
```

### Pass gate

```text
- Correct LoRA gives a measurable gain on its certified task or evidence type.
- Wrong LoRA does not consistently increase wrong-answer confidence.
- Adapter overhead is logged separately from ROI and generation overhead.
```

### Stop condition

If wrong adapters make the model confidently wrong, implement verifier/quarantine gates before routing.

---

## Stage 3: Taxonomy-card router

### Goal

Route using query/task taxonomy and AdapterCard metadata only. Do not use LeWM latent yet.

### Router input

```yaml
router_input:
  - query
  - instruction
  - coarse_task_label_optional
  - AdapterCard taxonomy vectors
  - AdapterCard capability probes
  - AdapterCard serving costs
  - certification status
```

### Baselines

| ID | Router | Purpose |
|---|---|---|
| S3-A | oracle_adapter | upper bound |
| S3-B | manual_rule | simple baseline |
| S3-C | taxonomy_similarity | first proposed router |
| S3-D | taxonomy_plus_cost | budget-aware router |
| S3-E | taxonomy_plus_abstain | safe router |

### Metrics

```yaml
routing_metrics:
  - top1_route_hit
  - top3_route_hit
  - wrong_route_rate
  - abstention_rate
  - abstention_quality
  - fallback_success_rate
  - route_latency_ms
  - resident_hit_rate
```

### Pass gate

```text
- Taxonomy router improves over manual/random routing.
- Abstain action is available and used on low-confidence samples.
- Wrong routes are logged with adapter_id, taxonomy mismatch, and failure type.
```

### Stop condition

If taxonomy routing cannot beat a simple rule baseline, improve AdapterCard calibration and probe scores before adding LeWM/JEPA.

---

## Stage 4: LeWM feature augmentation

### Goal

Use LeWM or vision world model features only as auxiliary inputs to the taxonomy router.

### Allowed LeWM features

```yaml
lewm_features:
  - visual_state_latent
  - surprise_score
  - visual_uncertainty
  - roi_prior
  - coarse_taxonomy_hint
```

### Disallowed output

```text
LeWM must not directly output selected_adapter_id in this stage.
```

### Baselines

| ID | Router | Purpose |
|---|---|---|
| S4-A | taxonomy_only | Stage 3 winner |
| S4-B | taxonomy_plus_uncertainty | weak LeWM feature |
| S4-C | taxonomy_plus_lewm_latent | full feature version |
| S4-D | direct_lewm_to_lora_ablation | ablation only, not main path |

### Metrics

```yaml
lewm_metrics:
  - route_hit_delta_vs_taxonomy_only
  - wrong_route_delta
  - router_entropy_delta
  - adapter_churn_rate
  - uncertainty_calibration_error
  - hard_case_improvement
```

### Pass gate

```text
- LeWM features improve hard or visually ambiguous cases.
- LeWM features do not increase adapter churn on easy cases.
- Direct LeWM-to-LoRA, if tested, is reported only as an ablation.
```

### Stop condition

If LeWM features make routing less stable, keep LeWM for ROI/uncertainty only and do not feed it into adapter selection.

---

## Stage 5: JEPA outcome predictor

### Goal

Predict the outcome of candidate actions in latent/metric space rather than predicting final answer text.

### Predictor input

```yaml
jepa_input:
  - ObservationState
  - AdapterCard
  - candidate_action:
      roi_mode: none | learned | oracle | fullres
      adapter_id: string | null
      residency_action: load | keep | hold | unload | none
```

### Predictor target

```yaml
jepa_target:
  - task_gain
  - evidence_gain
  - verifier_pass_probability
  - latency_ms
  - peak_vram_mb
  - conflict_risk
  - fallback_probability
```

### Baselines

| ID | Policy | Purpose |
|---|---|---|
| S5-A | taxonomy_plus_cost | Stage 3/4 baseline |
| S5-B | learned_metric_regressor | non-JEPA baseline |
| S5-C | jepa_outcome_predictor | proposed extension |
| S5-D | oracle_best_action | regret upper bound |

### Metrics

```yaml
jepa_metrics:
  - gain_prediction_mae
  - latency_prediction_mae
  - peak_vram_prediction_mae
  - conflict_prediction_auc
  - selected_action_regret
  - low_confidence_abstain_quality
```

### Pass gate

```text
- JEPA outcome predictor reduces selected_action_regret versus taxonomy router.
- It predicts cost and conflict well enough to support budget decisions.
- It abstains or falls back on high-uncertainty samples.
```

### Stop condition

If JEPA prediction error is high, keep it offline for analysis and do not use it in runtime routing.

---

## Stage 6: Closed-loop verifier and fallback

### Goal

Close the loop: execute a plan, verify evidence, decide commit/fallback/quarantine, and log failure residuals for offline Simula.

### Closed-loop actions

```yaml
actions:
  - execute_adapter_plan
  - verify_evidence
  - tentative_graph_update
  - fallback_larger_crop
  - fallback_second_scout
  - emergency_fullres
  - quarantine_adapter_or_sample
  - abstain
```

### Metrics

```yaml
closed_loop_metrics:
  - verifier_disagreement_rate
  - fallback_success_rate
  - quarantine_trigger_rate
  - rollback_rate
  - graph_false_commit_rate
  - repeated_fallback_loop_rate
  - p99_latency
  - peak_vram_violation_rate
```

### Pass gate

```text
- Verifier prevents obvious false commits.
- Fallback improves at least a subset of ROI miss or wrong-route cases.
- Quarantine captures shortcut/leakage/conflict samples instead of letting them pollute training.
```

---

## Final pilot table

At the end of each stage, generate this table:

```text
stage baseline_id task_score visual_tokens peak_vram_mb adapter_resident_mb kv_cache_mb p95_latency_ms route_hit fallback_rate main_failure
```

Do not move to the next stage until the table can be generated automatically.
