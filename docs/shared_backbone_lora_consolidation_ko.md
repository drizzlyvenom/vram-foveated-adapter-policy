# Shared-Backbone LoRA Specialist Consolidation

Status: core Track A
Purpose: validate the original research goal: replace multiple full specialist VLMs with one shared backbone and resident LoRA specialists.

## 1. Core hypothesis

Multiple full specialist VLMs are memory-expensive because each specialist repeats most of the same backbone parameters.

A shared-backbone LoRA bank should reduce resident memory:

```text
full document VLM
full OCR VLM
full UI VLM
full chart VLM

-> one shared VLM backbone
   + document LoRA
   + OCR LoRA
   + UI LoRA
   + chart LoRA
```

## 2. What this track proves

This track should prove or disprove:

```text
- one shared backbone can host multiple specialist behaviors
- resident VRAM is lower than multiple full specialist backbones
- LoRA mode switching is faster than full model swapping
- taxonomy/card routing can select useful specialists
- wrong specialist adapters do not cause uncontrolled collapse
```

## 3. What this track does not prove

It does not prove:

```text
- full high-resolution visual token cost is reduced
- ROI selection works
- KV/cache cost is solved
- FoveateR is unnecessary
```

Those belong to Track B.

## 4. Baselines

| ID | Name | Description |
|---|---|---|
| M0 | shared backbone only | general VLM, no specialist adapter |
| M1 | multiple full specialists | one full model per domain/task |
| M2 | shared backbone + oracle LoRA | correct LoRA chosen by gold label |
| M3 | shared backbone + taxonomy-routed LoRA | LoRA chosen by router from allowed features |
| M4 | shared backbone + HydraLoRA/shared factor | compressed adapter bank variant |
| M5 | shared backbone + certified bundles | only compatibility-certified combinations |

## 5. Specialist domains

Initial specialist set:

```yaml
specialists:
  document_field:
    examples: [DocVQA, forms, receipts]
  scene_text_ocr:
    examples: [TextVQA, signs, labels]
  ui_grounding:
    examples: [RICO, mobile UI, counters]
  chart_value:
    examples: [ChartQA, plots, tables]
```

The exact domains may change, but the first pilot should stay small.

## 6. Adapter card requirements

Each adapter must have a card:

```yaml
adapter_id: "doc_field_lora_r8"
base_model: "shared-vlm-name"
slot: "V"
structure:
  type: "independent_lora"
  rank: 8
  target_modules: ["q_proj", "o_proj"]
  target_layers: "middle"
taxonomy:
  domain:
    document: 0.95
    scene_text: 0.40
  evidence_type:
    document_field: 0.90
    small_text: 0.55
capability_probe:
  extraction_score: 0.0
  hard_negative_score: 0.0
  general_regression: 0.0
serving:
  resident_status: "hot|warm|cold"
  adapter_memory_mb: 0.0
  load_cost_ms: 0.0
  switch_cost_ms: 0.0
certification:
  status: "experimental|certified|quarantined"
  conflict_rate: 0.0
  calibration_score: 0.0
```

## 7. Router requirements

Allowed inputs:

```yaml
allowed_router_features:
  - query text
  - low-resolution image embedding or statistics
  - adapter card taxonomy vector
  - adapter cost profile
  - route confidence/margin
```

Forbidden inputs:

```yaml
forbidden_router_features:
  - dataset_alias
  - required_adapter_id
  - oracle ROI
  - gold domain label at inference
```

## 8. Main metrics

```yaml
memory:
  - multi_specialist_resident_mb
  - shared_backbone_resident_mb
  - adapter_bank_resident_mb
  - resident_vram_reduction_ratio

latency:
  - full_model_load_ms
  - full_model_swap_ms
  - lora_switch_ms
  - mode_switch_speedup

quality:
  - shared_backbone_only_score
  - oracle_lora_score
  - routed_lora_score
  - score_retention_vs_full_specialist
  - score_gain_vs_shared_backbone

safety:
  - wrong_adapter_damage
  - wrong_adapter_confidence_gain
  - adapter_conflict_rate
  - quarantine_rate
```

## 9. Pass/fail criteria

A first pass does not need to beat full specialists.

A reasonable early gate:

```yaml
early_pass:
  resident_vram_reduction_ratio: ">= 0.30 against multi-specialist baseline or simulated baseline"
  lora_switch_speedup: ">= 5x faster than full model swap"
  routed_lora_score: ">= shared_backbone_only_score"
  score_retention_vs_oracle_lora: ">= 0.80"
  wrong_adapter_damage: "measured and bounded"
```

## 10. Claim boundary

Safe claim after this track passes:

```text
A shared backbone with LoRA specialists can reduce resident specialist memory compared with multiple full specialist VLMs under the measured setup.
```

Unsafe claim:

```text
LoRA alone makes a single full VLM fit on low-end hardware.
```

LoRA reduces duplicated specialist residency. It does not shrink the shared backbone unless paired with quantization, a smaller base model, pruning, offloading, or distillation.
