# Architecture Contract: Budget-Conditioned Foveated Adapter Policy

Status: draft contract for pilot implementation  
Scope: repo-level interface document  
Purpose: keep the sketch flexible while preventing the modules from drifting apart.

## 0. Design stance

This project should not begin as a full end-to-end Simula-JEPA-HydraLoRA implementation. The first pilot should prove that the interfaces, logging, and ablation matrix are measurable.

The architecture has five separable responsibilities:

```text
Observation      -> what is visible, uncertain, or worth inspecting
Taxonomy         -> what type of evidence/task/skill is likely needed
Adapter registry -> which resident or loadable LoRA modules are certified for that skill
Budget policy    -> what can be run under VRAM/latency/residency constraints
Verification     -> whether evidence is trustworthy enough to commit or should trigger fallback
```

The most important rule is:

```text
LeWM / JEPA latent state should not directly output a LoRA ID in the first pilot.
```

Instead:

```text
LeWM / vision encoder -> ObservationState
ObservationState -> taxonomy posterior / ROI candidates / uncertainty
taxonomy + AdapterCard registry -> candidate adapters
budget policy + certification -> AdapterPlan
execution -> EvidenceRecord
verifier -> commit / fallback / quarantine
```

## 1. Core contracts

### 1.1 ObservationState

Produced by a low-resolution VLM, vision encoder, LeWM-like world model, or a Stage 0 CostSim replay row.

```yaml
ObservationState:
  sample_id: string
  step_id: integer
  query: string
  low_res_shape: [height, width]
  low_res_visual_token_count: integer
  roi_candidates:
    - roi_id: string
      box_xyxy: [float, float, float, float]
      proposal_score: float
      source: enum[random, heuristic, learned, oracle, manual]
  uncertainty:
    visual_uncertainty: float
    route_uncertainty: float
    evidence_uncertainty: float
  taxonomy_hint:
    domain: map[string, float]
    evidence_type: map[string, float]
    visual_skill: map[string, float]
  budget_state:
    total_vram_mb: float
    reserved_vram_mb: float
    available_vram_mb: float
    current_kv_cache_mb: float
    resident_adapters: list[string]
    latency_budget_ms: float
```

Minimum pilot requirement:

```text
Stage 0 may fill roi_candidates and taxonomy_hint with replayed, null, or cost-model-only values.
The logging contract must still be respected.
```

### 1.2 AdapterCard

Produced offline by Simula, manual registration, probe evaluation, or a lightweight fixture generator.

```yaml
AdapterCard:
  adapter_id: string
  base_model: string
  slot: enum[V, X, L]
  structure:
    type: enum[independent_lora, hydralora_shared_a, prompt_adapter, none]
    rank: integer
    target_modules: list[string]
    target_layers: string
  taxonomy:
    domain: map[string, float]
    evidence_type: map[string, float]
    visual_skill: map[string, float]
    reasoning_style: map[string, float]
  capability_probe:
    metrics: map[string, float]
  serving:
    resident_status: enum[hot, warm, cold, unavailable]
    adapter_memory_mb: float
    estimated_latency_ms: float
    load_cost_ms: float
    evict_cost_ms: float
  certification:
    status: enum[certified, experimental, quarantined]
    conflict_rate: float
    calibration_score: float
    registry_version: string
```

An adapter without an AdapterCard should not be eligible for runtime routing.

### 1.3 AdapterPlan

Produced by the runtime router and budget policy.

```yaml
AdapterPlan:
  sample_id: string
  step_id: integer
  selected_roi_id: string | null
  selected_adapter_ids: list[string]
  adapter_scope: enum[request, roi, segment]
  residency_action: enum[load, keep, unload, hold, none]
  fallback_policy: enum[none, larger_crop, second_scout, emergency_fullres, human_review, abstain]
  expected:
    task_gain: float
    evidence_gain: float
    latency_ms: float
    peak_vram_mb: float
    conflict_risk: float
  router:
    router_type: enum[manual, taxonomy, taxonomy_lewm, jepa_outcome, oracle]
    confidence: float
    abstained: boolean
    reason_codes: list[string]
```

Pilot rule:

```text
Use at most one adapter per slot: V, X, L.
Start with top-1 routing. Top-k fusion is a later ablation.
```

### 1.4 EvidenceRecord

Produced after running the VLM/LLM with the selected ROI and adapter plan.

```yaml
EvidenceRecord:
  sample_id: string
  step_id: integer
  roi_id: string | null
  active_adapters: list[string]
  output_text: string
  extracted_evidence:
    evidence_type: string
    value: string | number | object | null
    confidence: float
  verifier:
    verifier_name: string
    verifier_score: float
    verifier_pass: boolean
    conflict_detected: boolean
  graph_update:
    action: enum[none, tentative, commit, rollback, quarantine]
    target_node: string | null
    target_edge: string | null
  runtime:
    visual_token_count: integer
    kv_cache_estimate_mb: float
    peak_vram_mb: float
    latency_ms: float
```

### 1.5 RouteTrace

One RouteTrace should be written per policy decision. It is the minimal unit for failure analysis.

```yaml
RouteTrace:
  sample_id: string
  split: enum[synthetic_train, real_holdout, ood_branch, hard_negative, quarantine, unknown]
  stage: enum[0_3090_costsim_replay, 1_foveation, 2_lora_isolation, 3_taxonomy_router, 4_lewm_feature, 5_jepa_outcome, 6_closed_loop]
  baseline_id: string
  observation_state_id: string
  adapter_plan_id: string
  evidence_record_id: string | null
  selected_adapter_ids: list[string]
  selected_roi_id: string | null
  fallback_used: boolean
  verifier_pass: boolean | null
  task_score: float | null
  route_success: boolean | null
  memory:
    visual_token_count: integer
    peak_vram_mb: float
    avg_vram_mb: float
    reserved_vram_mb: float
    adapter_resident_mb: float
    kv_cache_estimate_mb: float
  timing:
    total_latency_ms: float
    adapter_load_ms: float
    adapter_evict_ms: float
    roi_encode_ms: float
    generation_ms: float
```

## 2. Module responsibilities

### 2.1 LeWM / Vision world model

Allowed outputs in early pilot:

```text
- visual state latent
- ROI proposal prior
- surprise score
- uncertainty score
- coarse taxonomy hint
```

Disallowed outputs in early pilot:

```text
- final LoRA ID
- adapter fusion weight
- graph commit decision
- final answer
```

Rationale: physical/visual latent structure is not guaranteed to align with LoRA capability space. Direct latent-to-LoRA routing should be tested only as a later ablation.

### 2.2 Taxonomy router

Initial implementation:

```text
score(adapter) = taxonomy_similarity + capability_bonus - cost_penalty - conflict_penalty
```

The router must support an `abstain` action. When confidence is low, the safe action is usually more foveation, base-only execution, or verifier escalation rather than forcing a LoRA.

### 2.3 Budget policy

Budget policy should treat VRAM as a hard-ish deployment constraint rather than a cosmetic metric.

At minimum, the policy must reject plans that violate:

```yaml
budget_constraints:
  max_peak_vram_mb: configured value
  max_latency_ms: configured value
  max_active_adapters_per_slot: 1
  allow_token_level_switching: false
```

### 2.4 Verification

Verification is not only final answer checking. It must include:

```text
- ROI evidence adequacy
- adapter route sanity
- confidence calibration
- conflict detection
- graph commit gate
- fallback trigger
- quarantine trigger
```

## 3. Safe wording for KV cache claim

Avoid this claim:

```text
KV cache only occurs by taxonomy of tagged LoRA, not by full vision context.
```

Use this safer claim:

```text
The runtime should avoid carrying full high-resolution visual context through every reasoning step. It should restrict cached visual context to low-resolution global tokens, selected ROI tokens, and compact taxonomy/adapter control state.
```

## 4. Pilot implementation boundary

The first implementation should create:

```text
- schema loaders for AdapterCard and RouteTrace
- Stage 0 CostSim replay loader
- taxonomy router
- budget filter
- logging harness
- ablation runner for stages 0 to 3
```

Do not implement:

```text
- online LoRA training
- token-level adapter switching
- unconstrained top-k LoRA fusion
- direct LeWM-to-LoRA ID routing
- graph memory as final judge
```
