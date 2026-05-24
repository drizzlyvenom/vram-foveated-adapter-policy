# FoveateR-Style Visual Evidence Compression

Status: core Track B
Purpose: reduce visual token, prefill, and KV/cache cost using low-resolution global context plus high-resolution ROI glimpses.

## 1. Core hypothesis

Full high-resolution visual context is wasteful when only a small region contains task-critical evidence.

A FoveateR-style policy should reduce visual evidence cost:

```text
full high-resolution image tokens

-> low-resolution global tokens
   + one or more high-resolution ROI glimpses
```

## 2. What this track proves

This track should prove or disprove:

```text
- ROI-based evidence can reduce visual token count
- visual token reduction lowers prefill/KV/activation cost
- task accuracy remains close to full image or oracle ROI
- FoveateR ROI approaches oracle ROI quality
- fallback rate remains acceptable
```

## 3. What this track does not prove

It does not prove:

```text
- shared backbone resident memory is reduced
- multiple specialist models are consolidated
- LoRA specialists are effective
```

Those belong to Track A.

## 4. Visual evidence baselines

| ID | Name | Description |
|---|---|---|
| V0 | full/fixed image | high-resolution or fixed-resolution full image |
| V1 | low-res only | low-resolution global image only |
| V2 | FoveateR ROI | low-res global + learned ROI glimpse |
| V3 | oracle ROI | low-res global + oracle/annotation ROI |
| V4 | FoveateR ROI + controlled fallback | ROI path with retry/fullres budget tier |

## 5. ROI metrics

```yaml
roi_metrics:
  - roi_recall_at_1
  - roi_recall_at_k
  - roi_coverage
  - roi_miss_rate
  - wrong_crop_distraction_rate
  - oracle_roi_gap
  - fullres_fallback_rate
```

Definitions:

```text
roi_miss:
  selected ROI does not cover task-critical evidence

wrong_crop_distraction:
  ROI path performs worse than low-res/no-crop because irrelevant crop distracts the model

oracle_roi_gap:
  task_score(oracle ROI) - task_score(FoveateR ROI)
```

## 6. Visual token accounting

Full image:

\[
T_{full}=|\phi_h(I)|
\]

Foveated path:

\[
T_{fov}=|\phi_g(I^g)|+\sum_{r\in R}|\phi_h(Crop(I,r))|
\]

Token saving:

\[
Saving_T=1-\frac{T_{fov}}{T_{full}}
\]

## 7. KV/cache claim boundary

KV/cache cost depends on the tokens actually passed to the model.

Use this statement:

```text
FoveateR reduces the visual-token contribution to prefill and KV/cache cost by replacing full high-resolution context with a smaller set of low-resolution global and high-resolution ROI tokens.
```

Avoid this statement:

```text
FoveateR reduces backbone resident memory.
```

## 8. FoveateR promotion gate

FoveateR should stay core if:

```yaml
foveater_promotion_gate:
  visual_token_saving: "substantial vs V0"
  oracle_roi_gap: "small enough to justify learned ROI"
  task_score: "close to full image or oracle ROI"
  roi_miss_rate: "bounded"
  wrong_crop_distraction_rate: "bounded"
  fullres_fallback_rate: "low enough for target device"
```

If oracle ROI is useful but FoveateR ROI is poor, keep ROI as a research target but do not claim deployment readiness.

If oracle ROI itself is not useful, demote foveation for that task family.

## 9. Integration with LoRA specialists

The combined path is:

```text
low-res global image + query
  -> taxonomy router selects LoRA specialist
  -> FoveateR selects ROI evidence
  -> shared backbone runs with selected LoRA and compact visual evidence
```

Do not make FoveateR responsible for selecting LoRA IDs.

Do not make taxonomy router responsible for precise pixel localization.

## 10. Fallback policy

FoveateR must be paired with budget-tier fallback:

```yaml
fallback_if:
  - ROI confidence low
  - verifier rejects answer
  - ROI coverage estimate low
  - route margin low

fallback_options:
  tier_0:
    - second ROI
    - larger ROI
  tier_1:
    - full image on shared backbone
  tier_2:
    - emergency specialist model or human review
```

Report normal path and fallback path separately.
