# Codex Execution Plan

Status: handoff guide  
Audience: Codex or coding assistant  
Goal: add repo-ready verification docs and a minimal Stage 0 replay scaffold without implementing the full research architecture.

## 0. First instruction to Codex

Copy this bundle into the repository root. Then implement only the smallest scaffold needed to replay or distill the existing RTX 3090 cost-simulation result into the project logging contract.

Do not implement the full Simula-JEPA-HydraLoRA architecture yet.

Do not spend Stage 0 effort generating a new scientific mock result. The repository already has a 3090 cost-simulation pilot; Stage 0 now verifies reproducible logging, source mapping, and directionality checks.

## 1. Files to add immediately

Add these files exactly:

```text
docs/architecture_contract.md
docs/verification_ladder.md
docs/measurement_and_logging.md
docs/failure_analysis_playbook.md
schemas/adapter_card.example.yaml
schemas/route_trace.example.yaml
configs/pilot_minimal.yaml
```

Then add a short link section to `README.md`:

```markdown
## Verification pilot docs

- `docs/architecture_contract.md`: module interface contracts
- `docs/verification_ladder.md`: staged validation plan
- `docs/measurement_and_logging.md`: logging and metric definitions
- `docs/failure_analysis_playbook.md`: diagnosis and mitigation guide
- `configs/pilot_minimal.yaml`: RTX 3090 CostSim replay config for Stage 0
```

## 2. Minimal code scaffold to create

Create this tree:

```text
src/vfa_policy/
  __init__.py
  schemas.py
  logging_utils.py
  costsim_replay.py
scripts/
  run_pilot.py
  summarize_run.py
```

No heavy ML dependency is required for the first pass.

## 3. Expected behavior

Running:

```bash
python scripts/run_pilot.py --config configs/pilot_minimal.yaml
```

should create:

```text
runs/<run_id>/
  run_manifest.json
  route_traces.jsonl
  summary.csv
```

Running:

```bash
python scripts/summarize_run.py runs/<run_id>/route_traces.jsonl
```

should print and rewrite `summary.csv`.

## 4. Stage 0 source mapping

The default Stage 0 config points at the existing local 3090 CostSim result:

```text
output/experiment/3090_pilot_costsim/02_simulation_run/results/summary.csv
```

Map source baselines into the Stage 0 logging contract:

| Stage 0 ID | Source baseline | Meaning |
|---|---|---|
| S0-A | B0 | low-res only 3090 prior |
| S0-B | B1 | full high-res 3090 prior |
| S0-C | B2 | foveated ROI 3090 prior |
| S0-D | B4-lite | independent adapter bank 3090 prior |
| S0-E | B5-lite | shared adapter bank 3090 prior |
| S0-F | B7-lite | budget policy 3090 prior |

Each replayed row must preserve:

```text
source_run_id
source_baseline
measurement_source = cost_model_3090
scientific_status = feasibility_prior
```

## 5. Implementation details

### 5.1 `schemas.py`

Use dataclasses or pydantic if already available. If not, use the standard library.

Define:

```python
@dataclass
class AdapterCard:
    adapter_id: str
    base_model: str
    slot: str
    taxonomy: dict
    capability_probe: dict
    serving: dict
    certification: dict

@dataclass
class RouteTrace:
    sample_id: str
    step_id: int
    stage: str
    baseline_id: str
    split: str
    evidence: dict
    input: dict
    routing: dict
    memory: dict
    timing: dict
    quality: dict
    failure: dict
```

### 5.2 `logging_utils.py`

Functions:

```python
def ensure_run_dir(run_id: str) -> Path: ...
def write_json(path: Path, obj: dict) -> None: ...
def append_jsonl(path: Path, obj: dict) -> None: ...
def read_jsonl(path: Path) -> list[dict]: ...
def summarize_traces(traces: list[dict]) -> list[dict]: ...
def write_summary_csv(path: Path, rows: list[dict]) -> None: ...
```

### 5.3 `costsim_replay.py`

Implement a deterministic replay/distillation backend. It should not call a real model.

Inputs:

```python
run_stage(config: dict) -> list[RouteTrace]
```

Behavior:

```text
1. Read the source 3090 CostSim summary CSV from config.
2. Filter rows for configured source baselines.
3. Convert each source row into a RouteTrace-compatible dict.
4. Preserve useful source columns in evidence or source_metrics.
5. Label every memory and latency value as cost_model_3090.
6. Fail loudly if the source file is missing and allow_missing_source is false.
```

Suggested field mapping:

```text
run_id -> evidence.source_run_id
baseline -> evidence.source_baseline
global_res -> input.global_resolution
roi_res -> input.roi_resolution
roi_count_effective -> input.roi_count
visual_tokens -> memory.visual_token_count
estimated_peak_memory_mb -> memory.peak_vram_mb
resident_adapter_memory_mb -> memory.adapter_resident_mb
reserve_target_mb -> memory.reserved_vram_mb
reserve_pass -> memory.reserve_pass
reserve_headroom_mb -> memory.reserve_headroom_mb
latency_proxy_ms -> timing.total_latency_ms
policy_trace -> routing.reason_codes or evidence.policy_trace
```

### 5.4 `run_pilot.py`

Steps:

```text
1. Load YAML config.
2. Create run_id.
3. Write run_manifest.json with measurement_source = cost_model_3090.
4. Call costsim_replay for Stage 0.
5. Append traces to route_traces.jsonl.
6. Aggregate summary.csv.
7. Run directionality checks.
8. Print path to run directory.
```

### 5.5 `summarize_run.py`

Steps:

```text
1. Read route_traces.jsonl.
2. Group by stage, baseline_id, split.
3. Compute mean visual tokens, mean/p95 peak VRAM, p50/p95/p99 latency, mean task score if present.
4. Write summary.csv.
5. Print a compact table.
```

## 6. Acceptance tests

Codex should add simple tests or manual checks:

```bash
python scripts/run_pilot.py --config configs/pilot_minimal.yaml
python scripts/summarize_run.py runs/<latest_run>/route_traces.jsonl
```

Acceptance criteria:

```text
- No import errors.
- run_manifest.json exists.
- route_traces.jsonl has at least one row per configured source baseline that exists in the 3090 CSV.
- summary.csv exists.
- Full high-res 3090 prior has larger visual_token_count and peak_vram than low-res 3090 prior.
- Foveated ROI 3090 prior reduces visual_token_count versus full high-res 3090 prior.
- Budget-policy 3090 prior reduces resident adapter pressure or reserve failures versus naive all-resident adapter baselines.
- All Stage 0 values are labeled as cost-model estimates, not real VLM profiler measurements.
- No actual model download is required.
```

## 7. Follow-up tasks after Stage 0 passes

Only after Stage 0 logging passes:

```text
1. Add ROI annotation loader.
2. Add real visual token estimator.
3. Add Stage 1 foveation-only runner on the available RTX 3090.
4. Add AdapterCard registry loader.
5. Add Stage 2 LoRA isolation config.
6. Add Stage 3 taxonomy router.
```

## 8. Hard guardrails

Do not add in the first implementation:

```text
- online LoRA training
- token-level adapter switching
- direct LeWM latent -> LoRA ID routing
- unconstrained multi-LoRA fusion
- graph memory commit as final truth
- mandatory CUDA dependency
- claims that Stage 0 is a measured real VLM profiler result
```

The first implementation must run as a replay/logging-contract check.
