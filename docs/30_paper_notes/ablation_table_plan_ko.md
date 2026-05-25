# Ablation Table Plan

Status: Track A v2 table plan

## Table 1. AdapterCard Certification

목적: 각 LoRA를 단순 weight 파일이 아니라 certification 대상 adapter로 다룬다.

| Adapter | Taxonomy | Train samples | Holdout samples | Base score | Correct score | Wrong score | Random score | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| document_track_a_v2_r4_v1 | document / field_value / bind_label_to_value / distractor_confusion | 32 | 32 | 0.502646 proxy | 0.718750 actual | 0.492646 proxy | 0.502646 proxy | mixed evidence, claim closed |
| chart_track_a_v2_r4_v1 | chart / table_cell / locate / label_value_mismatch | 32 | 32 | 0.412646 proxy | 0.750000 actual | 0.402646 proxy | 0.412646 proxy | mixed evidence, claim closed |
| scene_text_track_a_v2_r4_v1 | scene_text / small_text / read / tiny_text_blur | 32 planned | 32 planned | planned | planned | planned | planned | next |
| ui_status_bind_r4_v1 | ui_screen / ui_status / bind_label_to_value / distractor_confusion | 32 planned | 32 planned | planned | planned | planned | planned | next |

## Table 2. Gate Progress

목적: path smoke와 promotion claim을 분리한다.

| Gate | Required comparison | Pass metric | Current status | Claim opened |
|---|---|---|---|---|
| Single LoRA Learns | base vs correct LoRA | train/holdout gain or labeled overfit smoke | document/chart path closed | no |
| Correct Beats Wrong | correct vs wrong/random | margin vs wrong/random | mixed/proxy only | no |
| Router Selects Adapter | routed vs oracle adapter | routed score near oracle, top1 > random | path closed, utility blocked | no |
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

위 명령은 기존 Track B support table 재현용이다. Track A v2 M0-M11 closure 재현은 아래 순서로 본다.

```powershell
.venv\Scripts\python.exe scripts\check_track_a_v2_schemas.py
.venv\Scripts\python.exe scripts\prepare_adapter_sensitive_manifest.py --samples-per-taxonomy-split 32 --output .local\data\track_a_v2_adapter_sensitive\manifest.jsonl
.venv\Scripts\python.exe scripts\run_gemma_teacher_gguf.py --manifest .local\data\track_a_v2_adapter_sensitive\manifest.jsonl --output .local\data\track_a_v2_adapter_sensitive\teacher_annotations.jsonl --max-per-taxonomy 1 --allow-deterministic-fallback
.venv\Scripts\python.exe scripts\compile_simula_curriculum.py --manifest .local\data\track_a_v2_adapter_sensitive\manifest.jsonl --teacher-annotations .local\data\track_a_v2_adapter_sensitive\teacher_annotations.jsonl --output .local\data\track_a_v2_adapter_sensitive\curriculum_manifest.jsonl
.venv\Scripts\python.exe scripts\train_track_a_v2_lora.py --curriculum .local\data\track_a_v2_adapter_sensitive\curriculum_manifest.jsonl --taxonomies document,chart --max-steps 32 --max-samples 32 --eval-train-samples 32 --eval-holdout-samples 32
.venv\Scripts\python.exe scripts\run_track_a_v2_certification.py --curriculum .local\data\track_a_v2_adapter_sensitive\curriculum_manifest.jsonl --lora-summary .local\runs\track_a_v2_lora_summary\single_lora_learns_summary.json --output .local\runs\track_a_v2_certification\certification_result.json
```

주의: 현재 certification table은 correct score만 actual LoRA evaluation이고, base/wrong/random은 mixed/proxy다. 논문용 utility claim은 fully actual 비교가 생긴 뒤에만 연다.
