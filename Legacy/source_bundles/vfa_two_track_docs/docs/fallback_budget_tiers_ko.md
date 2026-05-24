# Fallback Budget Tiers

Status: runtime safety contract
Purpose: prevent fallback from hiding normal-path memory savings or causing uncontrolled loops.

## 1. Why fallback must be tiered

Fallback is necessary because ROI or adapter routing can fail.

But if every failure immediately calls full-resolution input or a full specialist model, then fallback destroys the low-VRAM claim.

Therefore, fallback must be reported by budget tier.

## 2. Tier definitions

### Tier 0: in-budget retry

Same resident backbone and same normal memory budget.

Examples:

```text
- second ROI
- larger ROI
- base-only same ROI
- alternative certified LoRA if already resident
```

### Tier 1: controlled expensive fallback

More expensive, but still within the shared-backbone runtime.

Examples:

```text
- full image on shared backbone
- larger visual context
- certified alternative LoRA requiring warm load
```

### Tier 2: emergency fallback

Outside the normal low-VRAM path.

Examples:

```text
- full specialist model
- remote/cloud model
- human review
```

Tier 2 must be reported separately.

## 3. Required reporting

Report separately:

```yaml
normal_path_peak_vram_mb:
  includes: "Tier 0 only"

controlled_fallback_peak_vram_mb:
  includes: "Tier 0 + Tier 1"

emergency_peak_vram_mb:
  includes: "Tier 2"

fallback_rate_by_tier:
  tier0: float
  tier1: float
  tier2: float
```

## 4. Fallback semantics

Use precise names:

```yaml
fallback_available:
  meaning: "a valid fallback candidate exists"

fallback_evaluated:
  meaning: "a precomputed or counterfactual fallback candidate was compared"

fallback_executed:
  meaning: "a new runtime call was actually executed after failure"

fallback_success:
  meaning: "fallback passes verifier and improves final decision"
```

Do not call a counterfactual comparison `fallback_attempted` unless an actual runtime fallback call was made.

## 5. Terminal failure vs quarantine

If the selected path already used the strongest allowed fallback and still failed, use:

```yaml
graph_action: "reject"
diagnosed_failure_type: "terminal_model_error" or "no_fallback_available"
```

Do not automatically quarantine the adapter or route.

Quarantine is reserved for unsafe behavior:

```yaml
quarantine_if:
  - wrong_adapter_damage
  - wrong_adapter_confidence_gain
  - adapter_conflict
  - verifier_false_pass
  - graph_false_commit_risk
```

## 6. Closed-loop state

Every closed-loop decision should log:

```yaml
closed_loop_state:
  selected_action: string
  final_action: string
  fallback_tier: 0|1|2|null
  fallback_available: bool
  fallback_evaluated: bool
  fallback_executed: bool
  fallback_success: bool
  fallback_depth: int
  max_fallback_depth: int
  visited_actions: list
  terminal_reason: string|null
  graph_action: commit|tentative|reject|quarantine
  quarantine_reason: string|null
```

## 7. Recommended first implementation

Start simple:

```text
max_fallback_depth = 1
Tier 0: second/larger ROI
Tier 1: full image on shared backbone
Tier 2: do not execute automatically; only log emergency eligibility
```

This prevents the fallback loop from becoming the main system.
