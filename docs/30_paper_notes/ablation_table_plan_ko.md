# Ablation Table Plan

Status: no-proxy rerun table plan

2026-05-25 기준으로 기존 table의 proxy/mixed/estimate/fallback 결과값은 폐기했다. 아래 표는 새 no-proxy run이 채워야 할 자리만 남긴다.

## Table 1. AdapterCard Certification

목적: 각 LoRA를 단순 weight 파일이 아니라 certification 대상 adapter로 다룬다.

| Adapter | Taxonomy | Train samples | Holdout samples | Base score | Correct score | Wrong score | Random score | Status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| document_track_a_v2_r4_v1 | document / field_value / bind_label_to_value / distractor_confusion | planned | planned | actual only | actual only | actual only | actual only | rerun required |
| chart_track_a_v2_r4_v1 | chart / table_cell / locate / label_value_mismatch | planned | planned | actual only | actual only | actual only | actual only | rerun required |
| scene_text_track_a_v2_r4_v1 | scene_text / small_text / read / tiny_text_blur | 32 planned | 32 planned | planned | planned | planned | planned | next |
| ui_status_bind_r4_v1 | ui_screen / ui_status / bind_label_to_value / distractor_confusion | 32 planned | 32 planned | planned | planned | planned | planned | next |

## Table 2. Gate Progress

목적: path smoke와 promotion claim을 분리한다.

| Gate | Required comparison | Pass metric | Current status | Claim opened |
|---|---|---|---|---|
| Single LoRA Learns | base vs correct LoRA | train/holdout gain or labeled overfit smoke | no-proxy rerun required | no |
| Correct Beats Wrong | correct vs wrong/random | margin vs wrong/random | no-proxy rerun required | no |
| Router Selects Adapter | routed vs oracle adapter | routed score near oracle, top1 > random | blocked until no-proxy certification | no |
| Resident Cost | shared backbone + bank vs actual baseline | memory/switch cost | no-proxy rerun required | no |

## Table 3. Existing Diagnostic Boundary

목적: 기존 결과를 버리지 않고, 새 방향성에서 어떤 의미로 쓰는지 정리한다.

2026-05-25 이후 proxy-tainted 기존 결과는 모두 trashbin으로 격리했다. 이 표는 재작성 전까지 claim 근거가 아니다.

| Path | Memory source | Latency source | Delta / resident MB | Latency ms | Claim |
|---|---|---|---:|---:|---|
| sequential full-model reload | actual load/unload smoke | measured | base model load | measured | baseline |
| actual PEFT attach | actual loaded adapter | measured smoke | measured delta | measured attach | rerun under no-proxy rules |
| actual PEFT C-matrix | actual loaded adapter | measured matrix smoke | measured | measured | rerun under no-proxy rules |
| multi-LoRA bank | actual loaded adapters | measured smoke | measured bank delta | measured switch path | actual-only resummary required |

## Table 4. ROI Source Comparison

목적: Track B의 결과를 메인 novelty가 아니라 visual evidence cost control 표로 둔다.

| ROI source | Role | Score | Target evidence hit | Visual tokens | Normal peak MB | Fallback rate |
|---|---|---:|---:|---:|---:|---:|
| center_crop | cheap heuristic baseline | measured | measured | measured | measured | measured |
| oracle_box | upper bound | measured | measured | measured | measured | measured |
| ocr_detector_box | practical detector | measured | measured | measured | measured | measured |

`ocr_detector_box`는 `scripts/prepare_ocr_detector_manifest.py`가 생성한 detector fields가 있을 때만 넣는다.

## Table 5. Combined C-Matrix

목적: C0/C3/C4/C5/C6/C7을 같은 schema로 정리하되, Track B support table로 둔다.

| Cell | Meaning | Score | Visual tokens | Normal peak | Conditional fallback peak | All-sample fallback peak |
|---|---|---:|---:|---:|---:|---:|
| C0 | shared backbone + full image | measured | measured | measured | n/a | measured |
| C3 | taxonomy LoRA + full image | actual only | actual only | actual only | n/a | actual only |
| C4 | taxonomy LoRA + foveated ROI | actual only | actual only | actual only | actual only | actual only |
| C5 | taxonomy LoRA + oracle ROI | actual only | actual only | actual only | actual only | actual only |
| C6 | low-res only | measured | measured | measured | n/a | measured |
| C7 | controlled fallback | measured | measured | measured | measured | measured |

## Execution Plan

기존 proxy-tainted 명령은 실행 계획에서 제거한다. 지금 남기는 것은 schema와 manifest scaffold smoke뿐이다.

```powershell
.venv\Scripts\python.exe scripts\check_track_a_v2_schemas.py
.venv\Scripts\python.exe scripts\prepare_adapter_sensitive_manifest.py --samples-per-taxonomy-split 32 --output .local\data\track_a_v2_adapter_sensitive\manifest.jsonl
```

주의: teacher output이 실패했을 때 deterministic fallback을 허용하는 실행은 더 이상 검증 결과로 보존하지 않는다. 논문용 utility claim은 fully actual 비교가 생긴 뒤에만 연다.
