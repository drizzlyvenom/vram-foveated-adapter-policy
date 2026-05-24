# Codex Implementation Plan for 3090 Two-Track Validation

Status: implementation guide
Audience: Codex or a coding agent reading repository markdown files

## 1. Read order

Codex should read files in this order:

```text
1. README.md
2. CODEX_GOAL_3090_TWO_TRACK.md if present
3. docs/3090_two_track_validation_guideline_ko.md
4. docs/3090_execution_ladder_ko.md
5. docs/3090_metrics_contract_ko.md
6. docs/3090_decision_gates_ko.md
7. docs/3090_codex_implementation_plan_ko.md
8. existing docs/stage1plus_closure_report_ko.md
9. existing docs/stage1_closure_report_ko.md
```

## 2. First implementation pass

Do not implement full training. First pass should be documentation and dry-run scaffolding.

### Step 1: README reframe

Update README so the top-level thesis is the two-track design:

```text
Track A: Resident specialist compression
Track B: Visual evidence compression
```

Move LeWM/JEPA/graph memory to exploratory/future status.

### Step 2: config and schema

Add:

```text
configs/3090_two_track_pilot.yaml
schemas/3090_residency_trace.example.yaml
schemas/3090_combined_validation_result.example.yaml
```

### Step 3: memory accounting skeleton

Add:

```text
src/vfa_policy/core/memory_accounting.py
```

Functions:

```python
record_after_model_load()
record_peak_memory()
compute_incremental_peak()
estimate_multi_specialist_residency()
compute_resident_saving()
```

The first version can run without a model by accepting numeric inputs from config.

### Step 4: validation matrix skeleton

Add:

```text
src/vfa_policy/core/validation_matrix.py
```

It should define matrix cells:

```text
C0 = M0 + V0
C1 = M0 + V2
C2 = M2 + V0
C3 = M3 + V0
C4 = M3 + V2
C5 = M3 + V3
```

### Step 5: runner skeleton

Add:

```text
scripts/run_3090_two_track_validation.py
```

The dry run should emit:

```text
runs/<run_id>/run_manifest.json
runs/<run_id>/route_traces.jsonl
runs/<run_id>/summary.csv
runs/<run_id>/combined_validation_result.json
```

## 3. Second implementation pass

After dry-run works, attach real measurement gradually.

```yaml
pass_2_order:
  - measure base_after_load memory for Qwen3-VL-4B
  - measure full image vs low-res vs ROI visual tokens
  - add adapter bank resident memory proxy
  - add LoRA switch latency proxy
  - add model swap latency baseline if feasible
```

## 4. What not to touch yet

```yaml
do_not_implement_yet:
  - full LoRA training
  - full FoveateR RL training
  - JEPA outcome predictor promotion
  - LeWM-to-LoRA routing
  - graph memory commit logic
  - production serving scheduler
```

## 5. Required artifact semantics

### `combined_validation_result.json`

Should include:

```yaml
run_id: string
hardware: object
matrix_cells: list
resident_summary: object
visual_summary: object
fallback_summary: object
claim_boundary: object
gates: object
```

### `route_traces.jsonl`

Each line should include:

```yaml
schema_version: "3090.route_trace.v0.1"
matrix_cell: C0 | C1 | C2 | C3 | C4 | C5
model_residency_mode: string
visual_policy: string
memory: object
visual: object
residency: object
quality: object
routing: object
fallback: object
failure: object
```

## 6. Acceptance criteria for implementation

```yaml
acceptance:
  - docs exist and are linked from README
  - dry-run script runs without GPU
  - dry-run emits expected JSON/CSV artifacts
  - no existing Stage 0/1/1+ scripts are broken
  - new claims are conservative
  - Stage 1+ is marked exploratory, not deleted
```
