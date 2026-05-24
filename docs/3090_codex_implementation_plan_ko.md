# Codex Implementation Plan for 3090 Two-Track Validation

Status: active implementation guide
Audience: Codex or a coding agent reading repository markdown files

## 1. Read order

Codex should read files in this order:

```text
1. README.md
2. CODEX_README.md
3. CODEX_GOAL_3090_TWO_TRACK.md
4. docs/3090_two_track_validation_guideline_ko.md
5. docs/3090_execution_ladder_ko.md
6. docs/3090_metrics_contract_ko.md
7. docs/3090_decision_gates_ko.md
8. docs/3090_codex_implementation_plan_ko.md
9. Legacy/stage0_stage1_stage1plus/docs/exploratory/stage1plus_protocol_closure_ko.md when historical context is needed
10. Legacy/stage0_stage1_stage1plus/docs/supporting/stage1_foveation_smoke_closure_ko.md when historical context is needed
```

## 2. 현재 구현 상태

Full training은 아직 구현하지 않는다. 현재 active repo는 3090 투트랙 dry-run scaffold와 R0 real CUDA memory-accounting smoke까지 닫힌 상태다.

### 완료된 항목

```yaml
completed:
  - README and CODEX_README point to the 3090 two-track structure
  - Legacy Stage 0/1/1+ artifacts are outside the active runner path
  - 3090 config and schema skeletons exist
  - memory accounting scaffold exists
  - validation matrix scaffold exists
  - dry-run runner exists
  - dry-run emits run_manifest, route_traces, summary, checks, and combined result
  - real CUDA mode loads the local Qwen3-VL-4B snapshot on RTX 3090
  - real CUDA mode records base-after-load allocated/reserved memory
  - real CUDA mode records visual/decode incremental peaks for full image, foveated ROI, and oracle ROI paths
  - real-task manifest mode prepares local full/low-res/ROI image evidence
  - runner emits Korean result summary and short-paper draft per run
```

Active files:

```text
configs/3090_two_track_pilot.yaml
configs/3090_adapter_cards.yaml
schemas/3090_residency_trace.example.yaml
schemas/3090_combined_validation_result.example.yaml
src/vfa_policy/core/memory_accounting.py
src/vfa_policy/core/real_measurement.py
src/vfa_policy/core/validation_matrix.py
src/vfa_policy/foveation/real_task_manifest.py
scripts/prepare_real_task_manifest.py
scripts/run_3090_two_track_validation.py
```

Dry-run command:

```powershell
python scripts\run_3090_two_track_validation.py --config configs\3090_two_track_pilot.yaml --dry-run
```

Real CUDA smoke command:

```powershell
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090_two_track_pilot.yaml --real-run --max-samples 4 --max-new-tokens 4
```

Real-task image smoke command:

```powershell
python scripts\prepare_real_task_manifest.py --source picsum_highres --max-samples 4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090_two_track_pilot.yaml --real-run --data-mode real_task_manifest --manifest data\real_task_smoke\manifest.jsonl --max-samples 2 --max-new-tokens 4
```

## 3. 다음 구현 pass

R0/R3 real-task image smoke 다음에는 ROI source와 실제 adapter weight 평가를 점진적으로 붙인다.

```yaml
next_pass_order:
  - replace center_crop ROI with oracle_box, OCR_box, or foveater_model
  - add real trained LoRA weights when available
  - measure adapter isolation and wrong-adapter damage with real adapters
  - replace LoRA switch latency proxy with measured switch timing when adapters are available
  - add sequential full-specialist swap timing baseline if feasible
  - keep promotion_gate false until stronger evidence is available
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
  - real CUDA smoke emits expected JSON/CSV/Markdown artifacts on RTX 3090
  - legacy Stage 0/1/1+ artifacts are archived under Legacy, not part of the active runner path
  - new claims are conservative
  - Stage 1+ is marked exploratory and preserved as historical evidence
```
