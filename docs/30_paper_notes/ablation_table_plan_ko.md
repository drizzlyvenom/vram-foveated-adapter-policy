# Ablation Table Plan

Status: table plan

## Table 1. ROI Source Comparison

목적: Track B의 핵심 문장, 즉 ROI 품질이 visual-token saving과 score retention 사이의 병목이라는 점을 보인다.

| ROI source | Role | Score | Target evidence hit | Visual tokens | Normal peak MB | Fallback rate |
|---|---|---:|---:|---:|---:|---:|
| center_crop | cheap baseline | measured | measured | measured | measured | measured |
| oracle_box | upper bound | measured | measured | measured | measured | measured |
| layout_proxy_box | controlled proxy | measured | measured | measured | measured | measured |
| ocr_detector_box | practical detector | measured | measured | measured | measured | measured |

`ocr_detector_box`는 `scripts/prepare_ocr_detector_manifest.py`가 생성한 detector fields가 있을 때만 넣는다.

## Table 2. Resident / Adapter Baseline

목적: Track A의 reload cost와 adapter attach/accounting cost를 나란히 둔다.

| Path | Memory source | Latency source | Delta / resident MB | Latency ms | Claim |
|---|---|---|---:|---:|---|
| sequential full-model reload | actual load/unload smoke | measured | base model load | measured | baseline |
| proxy LoRA bank | adapter cards | estimate | estimated | estimated | accounting scaffold |
| actual PEFT attach | actual loaded adapter | measured smoke | measured delta | measured attach | untrained smoke |
| actual PEFT C3/C4 matrix | actual loaded adapter | measured matrix smoke | measured | measured | no accuracy gain |
| tiny trained LoRA path | saved adapter under `.local/adapters` | measured train/holdout + full matrix smoke | measured | measured | training-path smoke |

## Table 3. Combined C-Matrix

목적: C0/C3/C4/C5/C6/C7을 같은 schema로 정리한다.

| Cell | Meaning | Score | Visual tokens | Normal peak | Conditional fallback peak | All-sample fallback peak |
|---|---|---:|---:|---:|---:|---:|
| C0 | shared backbone + full image | measured | measured | measured | n/a | measured |
| C3 | taxonomy LoRA proxy + full image | measured | measured | measured | n/a | measured |
| C4 | taxonomy LoRA proxy + foveated ROI | measured | measured | measured | measured | measured |
| C5 | taxonomy LoRA proxy + oracle ROI | measured | measured | measured | measured | measured |
| C6 | low-res only | measured | measured | measured | n/a | measured |
| C7 | controlled fallback | measured | measured | measured | measured | measured |

## Execution Plan

```powershell
.venv\Scripts\python.exe scripts\run_roi_source_stability.py --config configs\3090\tiny_scored_roi_stability_64.yaml --manifest .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --max-samples 64 --repeats 3 --max-new-tokens 8 --execute --output .local\runs\roi_stability_64_repeats3_plan.json
```

위 명령은 기본적으로 실행하지 않고 plan JSON만 만든다. 실제 run은 `--execute`를 붙인다.
