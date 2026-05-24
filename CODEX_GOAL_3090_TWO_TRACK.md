# Codex Goal: 3090 Two-Track Validation Redesign

Status: active 3090 validation goal and `/goal` entrypoint.
Current state: documentation, dry-run scaffold, and R0 real CUDA memory-accounting smoke are implemented; next step is repeated R1/R2/R3/R4/R5 validation with stronger task evidence.

## Operational instruction

When this document is used as `/goal`, treat the active repository as a fresh 3090 two-track validation project.

- Active path: 3090 two-track docs, configs, schemas, runner, and core modules.
- Legacy path: all pre-3090, Stage 0/1/1+, presentation, paper, policy, and local workbench artifacts.
- Do not resurrect legacy scripts or claims unless the user explicitly asks for historical context.
- Do not make performance claims from dry-run/proxy outputs.
- Next technical objective: repeat real CUDA accounting on task data, then replace proxy adapter evidence with actual trained LoRA weights when available.

## Goal

Reframe the repository around a **two-track low-VRAM vision inference validation**:

1. **Resident specialist compression**
   Replace multiple full specialist VLMs with one shared VLM backbone plus taxonomy-tagged LoRA specialist adapters.

2. **Visual evidence compression**
   Replace full high-resolution visual context with a low-resolution global view plus FoveateR-style high-resolution ROI glimpses.

The repository should stop treating Stage 1+ as final evidence for peak VRAM reduction. Stage 1+ remains useful as protocol closure and instrumentation evidence, but the core validation must now separately measure:

- resident model memory,
- adapter bank memory,
- visual token / KV / prefill cost,
- normal-path peak VRAM,
- controlled-fallback peak VRAM,
- emergency-fallback peak VRAM.

## Legacy preservation

Existing Stage 0, Stage 1, and Stage 1+ artifacts are preserved under `Legacy/stage0_stage1_stage1plus/`.

- Stage 0: prior cost simulation / logging contract.
- Stage 1: foveation-only smoke / visual-path support evidence.
- Stage 1+: exploratory protocol closure for unified RouteTrace, proxy routing, fallback/quarantine instrumentation.

They are historical evidence, not the active runner path.

## Core thesis

Low-resource vision inference has two distinct memory bottlenecks:

```text
Track A: Resident specialist compression
multiple full specialist VLMs
→ one shared VLM backbone + taxonomy-tagged LoRA bank

Track B: Visual evidence compression
full high-resolution visual context
→ low-res global view + FoveateR-style ROI glimpses
```

LoRA banks reduce specialist model residency and model-swap latency.
FoveateR-style ROI glimpses reduce visual tokens, KV/cache pressure, prefill cost, and visual-path activation cost.

Neither track alone fully solves low-VRAM vision inference.

## Active files

These docs should remain active:

```text
docs/3090_two_track_validation_guideline_ko.md
docs/3090_execution_ladder_ko.md
docs/3090_metrics_contract_ko.md
docs/3090_decision_gates_ko.md
docs/3090_codex_implementation_plan_ko.md
docs/latest_run_status_ko.md
```

These config/schema files should remain active:

```text
configs/3090_two_track_pilot.yaml
configs/3090_adapter_cards.yaml
schemas/3090_residency_trace.example.yaml
schemas/3090_combined_validation_result.example.yaml
```

README status:

- The two-track thesis is near the top.
- LeWM, JEPA outcome routing, graph memory, and complex fallback loops are not in the active core path.
- Foveation reduces visual token/KV/prefill cost, not resident backbone memory.
- LoRA consolidation reduces resident specialist footprint, not full high-resolution visual token cost.

## Active code scaffolds

The active runner path is the 3090 two-track scaffold. Legacy Stage 0/1/1+ files are preserved under `Legacy/stage0_stage1_stage1plus/`.

```text
src/vfa_policy/core/memory_accounting.py
src/vfa_policy/core/validation_matrix.py
src/vfa_policy/consolidation/specialist_baseline.py
src/vfa_policy/consolidation/adapter_residency.py
src/vfa_policy/foveation/roi_metrics.py
src/vfa_policy/foveation/real_task_manifest.py
scripts/prepare_real_task_manifest.py
scripts/run_3090_two_track_validation.py
```

The current scaffold emits dry-run JSON/CSV, real CUDA smoke artifacts, and real-task image smoke artifacts from a local manifest.

## Validation matrix

Implement or document the following axes.

### Model residency axis

```text
M0: shared backbone only
M1: multiple full specialist models, resident estimate or sequential swap baseline
M2: shared backbone + oracle LoRA specialist
M3: shared backbone + taxonomy-routed LoRA specialist
M4: shared backbone + HydraLoRA/shared-factor adapter bank estimate
```

### Visual evidence axis

```text
V0: full fixed image / full high-resolution context
V1: low-res only
V2: FoveateR-style ROI glimpse
V3: oracle ROI upper bound
V4: FoveateR ROI + controlled fallback
```

### Minimum combined pilot cells

```text
C0 = M0 + V0
C1 = M0 + V2
C2 = M2 + V0
C3 = M3 + V0
C4 = M3 + V2
C5 = M3 + V3
```

## Required memory fields

Every relevant run should record:

```yaml
base_after_load_allocated_mb: null
base_after_load_reserved_mb: null
adapter_bank_resident_mb: null
visual_incremental_peak_mb: null
decode_incremental_peak_mb: null
total_peak_mb: null
normal_path_peak_mb: null
controlled_fallback_peak_mb: null
emergency_fallback_peak_mb: null
visual_token_count: null
kv_cache_estimate_mb: null
prefill_latency_ms: null
mode_switch_latency_ms: null
lora_switch_latency_ms: null
model_load_latency_ms: null
```

Do not report a single `peak_vram_mb` as the only memory result.

## 3090 claim boundary

The RTX 3090 pilot can support:

- feasibility evidence,
- resident memory accounting,
- shared-backbone vs multi-specialist residency comparison,
- LoRA-bank routing/residency prototype,
- FoveateR-style visual token/KV reduction evidence,
- fallback budget-tier instrumentation.

The RTX 3090 pilot should not claim:

- final large-scale benchmark superiority,
- full FoveateR RL training success,
- many-user serving p99 performance,
- large LoRA bank production stability,
- actual LoRA gain before trained LoRA weights are evaluated.

## Fallback policy

Replace complex fallback-loop claims with budget tiers:

```yaml
tier_0_in_budget:
  - second_roi
  - larger_roi
  - base_only_same_roi
  - same_shared_backbone

tier_1_controlled_expensive:
  - fullres_same_shared_backbone
  - alternative_certified_lora

tier_2_emergency:
  - full_specialist_model
  - human_review
```

Report normal-path peak, controlled-fallback peak, and emergency peak separately.

Terminal model errors should be `reject` or `unresolved`, not `quarantine`. Quarantine should be reserved for unsafe adapters, unsafe routes, verifier false pass, graph false commit risk, adapter conflict, or wrong-adapter confidence gain.

## Acceptance criteria

Codex work is acceptable if:

1. README clearly explains the two-track thesis.
2. Existing Stage 1+ is reclassified as exploratory protocol closure.
3. The 3090 validation docs exist and are internally consistent.
4. Config and schema skeletons exist.
5. Memory accounting separates resident model memory from incremental visual/KV cost.
6. Fallback is represented as budget tiers.
7. LeWM/JEPA/graph memory are not in the core path.
8. Legacy reproduction artifacts are preserved outside the active runner path.

## Non-goals for this pass

Do not implement full LoRA training.
Do not implement full FoveateR RL training.
Do not delete existing reports.
Do not make new performance claims.
Do not require hardware beyond a single RTX 3090 for the initial pilot.
