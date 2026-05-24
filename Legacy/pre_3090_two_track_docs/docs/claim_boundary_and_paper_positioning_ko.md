# Claim Boundary and Paper Positioning

Status: writing guide
Purpose: keep the paper honest and focused.

## 1. Working title options

```text
Shared-Backbone Vision Specialist Consolidation via Resident LoRA Banks and Foveated Evidence
```

```text
Two-Track VRAM-Aware Vision Inference with LoRA Specialist Banks and FoveateR Evidence Compression
```

```text
Low-VRAM Vision Inference through Specialist LoRA Consolidation and Foveated Visual Context
```

## 2. Clean abstract skeleton

Use this as the paper's conceptual skeleton:

> Low-resource vision-language inference is constrained by both resident model memory and high-resolution visual context cost. We propose a two-track system. First, multiple full vision specialist models are consolidated into one shared VLM backbone with taxonomy-tagged LoRA specialists, reducing resident model memory and mode-switch latency. Second, full high-resolution visual context is replaced by a low-resolution global view and FoveateR-style high-resolution ROI glimpses, reducing visual tokens, prefill cost, and visual KV/cache growth. We evaluate the two tracks separately and jointly using a validation matrix that decomposes resident memory, adapter memory, visual token cost, fallback tiers, and task quality.

## 3. Safe claims

Safe after the right experiments:

```yaml
safe_claims:
  - "Shared backbone + LoRA specialists reduce resident memory relative to multiple full specialist models."
  - "LoRA switching can be cheaper than loading/swapping full specialist models."
  - "FoveateR-style ROI evidence reduces visual token count relative to full high-resolution visual context."
  - "Visual token reduction should be reported separately from resident backbone memory."
  - "The combined system targets both resident model footprint and visual evidence footprint."
```

## 4. Unsafe or premature claims

Do not claim yet:

```yaml
unsafe_claims:
  - "LoRA makes a single full VLM smaller."
  - "FoveateR reduces backbone resident memory."
  - "JEPA routing is better than taxonomy routing."
  - "Stage 1+ proves trained LoRA accuracy gains."
  - "Fallback loop recovers failures reliably."
  - "Taxonomy routing generalizes if dataset alias leakage is present."
```

## 5. Contribution structure

### Contribution 1: specialist consolidation

```text
We formulate resident specialist memory reduction as replacing K full specialist VLMs with one shared VLM backbone and a resident LoRA specialist bank.
```

### Contribution 2: foveated evidence compression

```text
We use FoveateR-style ROI glimpses to reduce high-resolution visual token and KV/cache cost while preserving task-relevant evidence.
```

### Contribution 3: decomposed validation

```text
We introduce a validation matrix and memory accounting protocol that separates resident model memory, adapter memory, visual token/KV cost, and fallback-tier peak memory.
```

### Contribution 4: compatibility certification

```text
We treat Simula as an offline adapter-card calibration and compatibility certification compiler, preventing unsafe arbitrary multi-LoRA composition at runtime.
```

## 6. Positioning against earlier Stage 1+

Stage 1+ should be described as:

```text
an exploratory protocol closure showing that RouteTrace, proxy adapter-card wiring, foveation measurement, and fallback/quarantine instrumentation can run under a single contract.
```

Do not describe Stage 1+ as:

```text
the final evidence for resident VRAM reduction or trained LoRA effectiveness.
```

## 7. Formula set for the paper

Resident memory:

\[
M_{multi}=\sum_{k=1}^{K}M(W_k)
\]

\[
M_{shared+LoRA}=M(W_0)+\sum_{i\in H}M(\Delta W_i)
\]

\[
ResidentSaving=1-\frac{M_{shared+LoRA}}{M_{multi}}
\]

Visual evidence tokens:

\[
T_{fov}=|\phi_g(I^g)|+\sum_{r\in R}|\phi_h(Crop(I,r))|
\]

\[
VisualSaving=1-\frac{T_{fov}}{T_{full}}
\]

Combined objective:

\[
\max_{\pi}\;\mathbb{E}
\left[
R_{task}
-
\lambda_M M_{resident}
-
\lambda_T T_{vis}
-
\lambda_L L
-
\lambda_C C_{collapse}
\right]
\]

## 8. One-sentence version

Use this when the project feels too broad:

> The project reduces low-resource VLM cost through two complementary levers: LoRA specialist consolidation for resident model memory, and FoveateR-style ROI evidence for visual token/KV memory.
