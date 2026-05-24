# Core Two-Track Research Plan

Status: core reframe
Purpose: make the repository intuitive again by separating resident model memory from visual evidence memory.

## 1. Core problem

Low-resource vision inference is not limited by one memory source.

A VLM runtime has at least four major cost sources:

```text
1. resident backbone/model memory
2. resident specialist/adaptation memory
3. visual token, prefill, and KV/cache memory
4. runtime activation, routing, verifier, and fallback overhead
```

The original sketch targeted all of these at once:

```text
visual token ↓
resident VRAM memory ↓
KV cache ↓
peak VRAM ↓
```

The earlier repository direction became confusing because it mixed all mechanisms into one loop. The new direction keeps two first-class tracks.

## 2. Track A: resident specialist compression

### Goal

Replace multiple full specialist vision models with:

```text
one shared VLM backbone + taxonomy-tagged resident LoRA bank
```

### What this reduces

```text
- resident memory from multiple specialist backbones
- model load/swap latency
- duplicated parameters across specialist models
```

### What this does not reduce by itself

```text
- full high-resolution visual tokens
- KV/cache growth from large visual context
- prefill cost of processing full images
```

### Canonical comparison

```text
M1: multiple full specialist VLMs
M3: shared VLM backbone + taxonomy-routed LoRA specialists
```

## 3. Track B: visual evidence compression

### Goal

Replace full high-resolution visual context with:

```text
low-resolution global view + FoveateR-style high-resolution ROI glimpses
```

### What this reduces

```text
- visual token count
- image prefill cost
- visual KV/cache contribution
- attention/activation cost from high-res visual context
```

### What this does not reduce by itself

```text
- resident memory of the main VLM backbone
- duplicated specialist model weights
```

### Canonical comparison

```text
V0: full/fixed high-resolution image
V2: low-res global + FoveateR ROI glimpse
```

## 4. Combined system

The final proposed system is:

```text
input image + query
  -> low-resolution global observation
  -> taxonomy router selects specialist LoRA
  -> FoveateR-style policy selects high-resolution ROI evidence
  -> shared VLM backbone runs with selected LoRA and compact visual evidence
  -> verifier decides commit / in-budget retry / controlled fallback
```

In compact form:

```text
Shared Backbone + Resident LoRA Bank + Foveated ROI Evidence
```

## 5. Clean role assignment

| Component | Core role | Not its role |
|---|---|---|
| Shared backbone | avoid multiple resident specialist backbones | solve all visual token cost |
| LoRA bank | specialize the shared backbone cheaply | shrink the shared backbone by itself |
| Taxonomy router | choose specialist adapter/card | localize pixels precisely |
| FoveateR | select high-value ROI evidence | replace specialist routing |
| Verifier | prevent bad evidence/adapter commits | be a full research agent |
| Simula | offline card calibration and compatibility certification | runtime world model in v1 |
| LeWM/JEPA | future outcome prediction/uncertainty | core dependency in v1 |

## 6. Revised contribution statement

Use this as the repository's new conceptual center:

> We study low-VRAM vision inference with a two-track design. Track A consolidates multiple full vision specialist models into a single shared VLM backbone with taxonomy-tagged LoRA specialists, reducing resident model memory and mode-switch latency. Track B uses FoveateR-style visual evidence compression to reduce visual token count, prefill cost, and visual KV/cache growth. The combined system targets both resident model footprint and high-resolution visual evidence cost.

## 7. Immediate research questions

```text
RQ1. Can shared backbone + LoRA specialists match full specialist models while using much less resident VRAM?
RQ2. Can LoRA mode switching replace full model swap latency?
RQ3. Can FoveateR-style ROI glimpses reduce visual token/KV cost without destroying task accuracy?
RQ4. Does combining Track A and Track B reduce normal-path peak VRAM and latency more than either track alone?
RQ5. Can offline compatibility certification prevent multi-LoRA collapse when adapters are made fine-grained?
```

## 8. What to do with Stage 1 and Stage 1+

Stage 1 and Stage 1+ are not discarded.

They are reclassified:

```text
Stage 1:
  supporting foveation smoke test

Stage 1+:
  exploratory protocol closure for RouteTrace, proxy routing, and fallback/quarantine instrumentation
```

Do not use Stage 1+ as final proof of the new core thesis.
