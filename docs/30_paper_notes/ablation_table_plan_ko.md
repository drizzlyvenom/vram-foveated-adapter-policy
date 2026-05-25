# Ablation Table Plan

Status: Track A v2 table plan

## Table 1. AdapterCard Certification

목적: 각 LoRA를 단순 weight 파일이 아니라 certification 대상 adapter로 다룬다.

| Adapter | Taxonomy | Train samples | Holdout samples | Base score | Correct score | Wrong score | Random score | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| doc_field_bind_r4_v1 | document / field_value / bind_label_to_value / distractor_confusion | planned | planned | measured | measured | measured | measured | experimental |
| chart_cell_locate_r4_v1 | chart / table_cell / locate / label_value_mismatch | planned | planned | measured | measured | measured | measured | experimental |
| ui_status_bind_r4_v1 | ui_screen / ui_status / bind_label_to_value / distractor_confusion | planned | planned | measured | measured | measured | measured | experimental |

## Table 2. Gate Progress

목적: path smoke와 promotion claim을 분리한다.

| Gate | Required comparison | Pass metric | Current status | Claim opened |
|---|---|---|---|---|
| Single LoRA Learns | base vs correct LoRA | train/holdout gain or labeled overfit smoke | next | no |
| Correct Beats Wrong | correct vs wrong/random | margin vs wrong/random | next | no |
| Router Selects Adapter | routed vs oracle adapter | routed score near oracle, top1 > random | blocked until prior gate | no |
| Resident Cost | shared backbone + bank vs specialist estimate | memory/switch cost | path smoke available | limited accounting only |

## Table 3. Existing Diagnostic Boundary

목적: 기존 결과를 버리지 않고, 새 방향성에서 어떤 의미로 쓰는지 정리한다.

| Path | Memory source | Latency source | Delta / resident MB | Latency ms | Claim |
|---|---|---|---:|---:|---|
| sequential full-model reload | actual load/unload smoke | measured | base model load | measured | baseline |
| proxy LoRA bank | adapter cards | estimate | estimated | estimated | accounting scaffold |
| actual PEFT attach | actual loaded adapter | measured smoke | measured delta | measured attach | untrained smoke |
| actual PEFT C-matrix | actual loaded adapter | measured matrix smoke | measured | measured | path smoke, no gain claim |
| multi-LoRA bank | actual loaded adapters | measured smoke | measured bank delta | measured switch path | path smoke, no routing utility claim |

## Table 4. ROI Source Comparison

목적: Track B의 결과를 메인 novelty가 아니라 visual evidence cost control 표로 둔다.

| ROI source | Role | Score | Target evidence hit | Visual tokens | Normal peak MB | Fallback rate |
|---|---|---:|---:|---:|---:|---:|
| center_crop | cheap heuristic baseline | measured | measured | measured | measured | measured |
| oracle_box | upper bound | measured | measured | measured | measured | measured |
| layout_proxy_box | controlled proxy | measured | measured | measured | measured | measured |
| ocr_detector_box | practical detector | measured | measured | measured | measured | measured |

`ocr_detector_box`는 `scripts/prepare_ocr_detector_manifest.py`가 생성한 detector fields가 있을 때만 넣는다.

## Table 5. Combined C-Matrix

목적: C0/C3/C4/C5/C6/C7을 같은 schema로 정리하되, Track B support table로 둔다.

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

위 명령은 기존 Track B support table 재현용이다. 새 Track A v2 execution plan은 AdapterCard v2 schema, Simula curriculum manifest, base/correct/wrong/random certification runner가 생긴 뒤 추가한다.
