# Repository Reorganization Plan

Status: practical refactor guide
Purpose: separate core two-track research from exploratory Stage 1+ code.

## 1. README changes

Update the README top-level objective to say:

```text
This project studies low-VRAM vision inference through two complementary tracks:
1. shared-backbone LoRA specialist consolidation
2. FoveateR-style visual evidence compression
```

The README should no longer present LeWM/JEPA/fallback as equal core pillars.

## 2. Documentation structure

Recommended docs:

```text
docs/
  core_two_track_research_plan_ko.md
  combined_validation_matrix_ko.md
  resident_memory_accounting_protocol_ko.md
  shared_backbone_lora_consolidation_ko.md
  foveater_visual_evidence_compression_ko.md
  lora_compatibility_certification_ko.md
  fallback_budget_tiers_ko.md
  claim_boundary_and_paper_positioning_ko.md
  exploratory/
    stage1plus_protocol_closure_ko.md
  supporting/
    stage1_foveation_smoke_closure_ko.md
```

Existing docs do not need to be deleted. They can be moved or linked.

## 3. Code namespace plan

Recommended structure:

```text
src/vfa_policy/
  core/
    memory_accounting.py
    validation_matrix.py
    trace_schema.py

  consolidation/
    specialist_baseline.py
    shared_backbone_lora.py
    adapter_residency.py
    mode_switch.py

  foveation/
    foveater_policy.py
    roi_metrics.py
    visual_token_accounting.py

  adapters/
    card.py
    bank.py
    compatibility.py
    hydralora_memory.py

  routing/
    taxonomy_router.py
    leakage_free_features.py

  fallback/
    budget_tiers.py
    verifier.py
    quarantine.py

  exploratory/
    stage1plus_protocol.py
    lewm_proxy.py
    jepa_proxy.py
```

## 4. What to move to exploratory

Move or mark as exploratory:

```text
- stage1plus_protocol.py
- LeWM proxy code
- JEPA proxy code
- complex fallback/quarantine prototype
```

Keep them accessible because they prove logging/protocol closure.

## 5. What to make core

Core modules should focus on:

```text
- memory accounting
- specialist consolidation baselines
- adapter card registry
- taxonomy router
- LoRA compatibility certification
- FoveateR ROI evidence accounting
```

## 6. Config plan

Add config skeletons:

```text
configs/two_track_validation.yaml
configs/resident_memory_accounting.yaml
configs/specialist_consolidation.yaml
configs/foveater_validation.yaml
configs/compatibility_certification.yaml
```

## 7. Suggested commits

### Commit 1: documentation reframe

```text
- Update README
- Add new docs listed above
- Mark Stage 1+ as exploratory protocol closure
```

### Commit 2: memory accounting core

```text
- Add memory accounting fields
- Add after-load and incremental peak measurements
- Add normal/fallback/emergency peak fields
```

### Commit 3: validation matrix skeleton

```text
- Add two-axis validation config
- Add runner skeleton that enumerates MxV experiments
- Keep actual model execution optional
```

### Commit 4: adapter registry and compatibility

```text
- Add adapter card loader/schema
- Add compatibility matrix schema
- Add certified bundle policy
```

### Commit 5: foveation core module

```text
- Move ROI token accounting into foveation module
- Add FoveateR/oracle/fullres/lowres evaluation interface
```

## 8. Do not do during reframe

Avoid these until the core is stable:

```text
- direct LeWM-to-LoRA routing
- JEPA as runtime primary selector
- graph memory implementation
- runtime LoRA training
- arbitrary multi-LoRA composition
```
