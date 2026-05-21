# Failure Analysis Playbook

Status: diagnostic guide  
Purpose: decide what to fix after each failed stage.

## 1. Failure taxonomy

Use the following labels in `RouteTrace.failure.main_failure_type`.

```yaml
failure_types:
  roi_miss:
    meaning: important region was not selected or not visible enough
  wrong_crop_distraction:
    meaning: crop added irrelevant high-res evidence and reduced answer quality
  adapter_no_gain:
    meaning: correct adapter gives no meaningful improvement over base
  wrong_adapter_damage:
    meaning: wrong adapter hurts performance
  wrong_adapter_confidence_gain:
    meaning: wrong adapter makes the model more confident while wrong
  wrong_route:
    meaning: router selected an incompatible adapter
  adapter_conflict:
    meaning: multiple adapters or slots produce conflicting evidence
  budget_violation:
    meaning: peak VRAM or latency exceeds configured budget
  adapter_thrashing:
    meaning: repeated load/unload causes latency spikes
  verifier_false_pass:
    meaning: verifier accepts bad evidence
  verifier_false_reject:
    meaning: verifier rejects correct evidence too often
  graph_false_commit:
    meaning: graph memory commits unverified or contradictory evidence
  synthetic_shortcut:
    meaning: synthetic_train succeeds but real_holdout or hard_negative fails
  ood_collapse:
    meaning: learned taxonomy or router fails on OOD branch
```

## 2. Diagnosis matrix

| Symptom | Likely cause | Check logs | First fix |
|---|---|---|---|
| Learned ROI worse than random ROI | ROI proposal not grounded | roi_recall_at_k, critical_evidence_miss_rate | improve ROI heuristic, add oracle upper bound, add fallback |
| Random crop worse than no crop | crop distraction | wrong_crop_distraction_rate | add crop relevance filter or verifier |
| Correct LoRA gives no gain | adapter not specialized or wrong layer/rank | adapter_gain_vs_base, probe scores | retrain or re-tag adapter; test different target layers |
| Wrong LoRA increases confidence | collapse risk | wrong_adapter_confidence_gain | quarantine adapter, add confidence penalty, add verifier gate |
| Router picks wrong adapter | card mismatch or weak taxonomy | top1_route_hit, taxonomy mismatch | recalibrate AdapterCard with probes |
| p95/p99 latency spikes | load/unload thrashing | adapter_load_ms, resident_hit_rate | add hysteresis, hot pool, max swaps per sample |
| VRAM not reduced | visual token path still too large | visual_token_count, kv_cache_estimate | reduce ROI count/resolution; avoid fullres fallback loops |
| Graph commits wrong evidence | verifier too weak | verifier_score, rollback_rate | make graph update tentative; require second evidence source |
| Synthetic good, real bad | shortcut/leakage | split-wise score, hard_negative score | quarantine synthetic pattern; add real_holdout calibration |
| LeWM features worsen routing | latent mismatch | route_hit_delta, adapter_churn | use LeWM only for ROI/uncertainty, not adapter selection |
| JEPA router worse than taxonomy | outcome predictor uncalibrated | selected_action_regret, prediction MAE | keep JEPA offline; collect more action-outcome tuples |

## 3. Stage-specific debugging

### Stage 0 failure

Do not modify model architecture. Fix replay, source mapping, and logging first.

Checklist:

```text
- Is the existing RTX 3090 CostSim source file present, or is the missing source explicitly reported?
- Is run_manifest.json created?
- Is route_traces.jsonl valid JSONL?
- Is summary.csv generated automatically?
- Are source baselines B0/B1/B2/B4-lite/B5-lite/B7-lite mapped to S0-* consistently?
- Are cost-model fields labeled as cost-model estimates rather than real profiler measurements?
- Are memory fields null because the 3090 CostSim did not model them, or because code forgot them?
```

### Stage 1 failure: foveation

Ask:

```text
- Does oracle ROI improve over low-res?
- If oracle ROI does not improve, is the task actually local-evidence dependent?
- Does random ROI hurt? If yes, crop relevance matters.
- Does learned ROI have high recall but low precision? That may be acceptable if fallback/verifier handles it.
```

Fix order:

```text
1. Confirm oracle ROI upper bound.
2. Improve ROI recall.
3. Add fallback for ROI miss.
4. Only then add adapters.
```

### Stage 2 failure: adapter isolation

Ask:

```text
- Does the adapter improve any certified subset?
- Is the adapter attached to the right slot: V, X, or L?
- Is target layer scope too broad or too narrow?
- Does adapter degrade general examples?
- Does wrong adapter increase confidence?
```

Fix order:

```text
1. Restrict adapter scope.
2. Re-run capability probes.
3. Update AdapterCard taxonomy and certification status.
4. Quarantine unsafe adapters.
```

### Stage 3 failure: taxonomy router

Ask:

```text
- Are AdapterCard taxonomy vectors too sparse or too generic?
- Does cost penalty dominate task relevance?
- Does router lack abstain?
- Are required_adapter_tags annotated consistently?
```

Fix order:

```text
1. Add probe-derived capability scores.
2. Add abstain threshold.
3. Add top-3 evaluation before top-1 hard selection.
4. Add cost penalty only after relevance works.
```

### Stage 4 failure: LeWM feature

Ask:

```text
- Is LeWM latent aligned with visual uncertainty or taxonomy?
- Does it improve hard cases but hurt easy cases?
- Does it increase adapter churn?
```

Fix order:

```text
1. Use LeWM features only for ROI proposal or uncertainty.
2. Add gating: use LeWM adapter feature only when route uncertainty is high.
3. Keep direct LeWM-to-LoRA as ablation only.
```

### Stage 5 failure: JEPA predictor

Ask:

```text
- Is the predictor trained on enough action-outcome tuples?
- Are targets too noisy?
- Is it predicting text instead of metrics/latent outcome?
- Is regret worse than taxonomy baseline?
```

Fix order:

```text
1. Predict simple cost metrics first: latency, peak_vram.
2. Add verifier_pass and conflict_risk.
3. Add task_gain only after enough rollout data.
4. Use uncertainty to abstain.
```

### Stage 6 failure: closed loop

Ask:

```text
- Does fallback actually recover failures?
- Are bad samples quarantined or reintroduced into training?
- Does graph memory overcommit?
- Is p99 latency dominated by emergency fullres fallback?
```

Fix order:

```text
1. Make graph updates tentative by default.
2. Limit fallback depth.
3. Add quarantine buffer.
4. Report p99 and peak violation rate separately.
```

## 4. Quarantine rules

A sample, adapter, or route should be quarantined when any of the following is true:

```yaml
quarantine_rules:
  sample:
    - verifier_pass == false and router_confidence > high_threshold
    - hard_negative is answered correctly for the wrong reason
    - graph conflict repeats after fallback
  adapter:
    - wrong_adapter_confidence_gain > threshold
    - conflict_rate > threshold
    - general_regression > threshold
  route:
    - repeated fallback loop
    - peak_vram_violation
    - adapter thrashing
```

Quarantined items should not silently enter synthetic_train. They should be reviewed or used as hard negatives.

## 5. Minimum failure report

For every failed stage, generate:

```text
stage
baseline_id
main_failure_type
n_affected_samples
top_5_sample_ids
mean_task_score_delta
mean_peak_vram_delta
mean_latency_delta
recommended_next_fix
```
