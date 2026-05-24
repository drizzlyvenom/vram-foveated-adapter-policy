# VRAM-Constrained Foveated Adapter Policy

이 프로젝트는 low-VRAM vision inference를 두 개의 상호보완 트랙으로 검증하는 연구 작업 폴더입니다.

```text
Track A. Shared-backbone LoRA specialist consolidation
  여러 full specialist VLM
  -> 하나의 공유 VLM backbone + taxonomy-tagged resident LoRA bank

Track B. FoveateR-style visual evidence compression
  full high-resolution visual context
  -> low-resolution global view + high-resolution ROI glimpses
```

두 트랙은 서로 다른 병목을 줄입니다.

- Track A는 duplicated specialist backbone residency와 model swap latency를 줄인다.
- Track B는 visual token count, prefill cost, visual KV/cache growth를 줄인다.
- End-to-end peak VRAM 주장은 두 트랙을 함께 측정하되, normal path와 fallback/emergency peak를 분리해서 보고한다.

## 현재 핵심 문서

- 3090 validation guideline: `docs/00_overview/3090_two_track_validation_guideline_ko.md`
- docs index: `docs/README.md`
- latest local run status: `docs/00_overview/latest_run_status_ko.md`
- local artifact boundary: `docs/00_overview/local_artifact_boundary_ko.md`
- 3090 execution ladder: `docs/10_protocols/3090_execution_ladder_ko.md`
- 3090 metrics contract: `docs/10_protocols/3090_metrics_contract_ko.md`
- 3090 decision gates: `docs/10_protocols/3090_decision_gates_ko.md`
- result briefs: `docs/20_results/`
- 3090 pilot config: `configs/3090/two_track_pilot.yaml`
- 3090 tiny scored config: `configs/3090/tiny_scored_validation.yaml`
- 3090 OCR detector config: `configs/3090/tiny_scored_ocr_detector.yaml`
- 3090 actual PEFT matrix smoke config: `configs/3090/tiny_scored_actual_peft_matrix_smoke.yaml`
- 3090 adapter cards: `configs/3090/adapter_cards.yaml`
- 3090 result schemas: `schemas/3090/residency_trace.example.yaml`, `schemas/3090/combined_validation_result.example.yaml`
- paper notes: `docs/30_paper_notes/`

## 경로 구조

```text
configs/3090/      active RTX 3090 configs
docs/00_overview/  overview, latest status, local artifact boundary
docs/10_protocols/ validation ladder, metrics contract, decision gates
docs/20_results/   committed result briefs
schemas/3090/      trace/result schema examples
scripts/           manifest preparation and validation runners
src/vfa_policy/    accounting, foveation, consolidation modules
.local/            local-only data, runs, HF cache, workbench, trashbin
```

## Legacy 보관

이전 방향의 문서와 발표/정책 초안은 삭제하지 않고 `Legacy/`로 이동했습니다.

```text
Legacy/docs/
Legacy/output/
Legacy/pre_3090_two_track_docs/
Legacy/stage0_stage1_stage1plus/
Legacy/source_bundles/vfa_two_track_docs/
Legacy/source_bundles/vfa_3090_two_track_validation_docs/
```

기존 Stage 0/1/1+ 스크립트, 설정, 스키마, closure 문서와 발표/논문 산출물은 active 구조에서 제외하고 `Legacy/` 아래에 보관합니다.

## 실행 참고

3090 투트랙 검증 dry-run scaffold:

```powershell
python scripts\run_3090_two_track_validation.py --config configs\3090\two_track_pilot.yaml --dry-run
```

RTX 3090 real CUDA memory-accounting smoke:

```powershell
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\two_track_pilot.yaml --real-run --max-samples 4 --max-new-tokens 4
```

Real-task image smoke:

```powershell
python scripts\prepare_real_task_manifest.py --source picsum_highres --max-samples 4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\two_track_pilot.yaml --real-run --data-mode real_task_manifest --manifest .local\data\real_task_smoke\manifest.jsonl --max-samples 2 --max-new-tokens 4
```

Tiny scored ROI source comparison:

```powershell
.venv\Scripts\python.exe scripts\prepare_tiny_scored_manifest.py --max-samples 20
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_validation.yaml --real-run --max-samples 16 --roi-source center_crop --max-new-tokens 8
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_validation.yaml --real-run --max-samples 16 --roi-source oracle_box --max-new-tokens 8
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_validation.yaml --real-run --max-samples 16 --roi-source layout_proxy_box --max-new-tokens 8
```

Optional OCR detector ROI manifest:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
.venv\Scripts\python.exe scripts\prepare_ocr_detector_manifest.py --input .local\data\tiny_scored_manifest\manifest.jsonl --output .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --engine rapidocr
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_ocr_detector.yaml --real-run --max-samples 16 --max-new-tokens 8
```

Sequential specialist swap와 actual PEFT attach smoke:

```powershell
.venv\Scripts\python.exe scripts\run_specialist_swap_smoke.py --config configs\3090\tiny_scored_validation.yaml --repeats 3
.venv\Scripts\python.exe scripts\run_actual_peft_smoke.py --config configs\3090\tiny_scored_validation.yaml --rank 4 --alpha 8
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_actual_peft_matrix_smoke.yaml --real-run --max-samples 4 --max-new-tokens 8
```

Tiny trained LoRA smoke:

```powershell
.venv\Scripts\python.exe scripts\train_tiny_lora_smoke.py --manifest .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --roi-source ocr_detector_box --max-samples 4 --max-steps 4 --rank 4 --alpha 8 --learning-rate 1e-4 --label-mask-mode answer_only
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_trained_lora_matrix_smoke.yaml --real-run --max-samples 4 --max-new-tokens 8
```

ROI source stability plan:

```powershell
.venv\Scripts\python.exe scripts\run_roi_source_stability.py --max-samples 32 --repeats 3
```

주요 산출물은 실행별 `.local/runs/<run_id>/combined_validation_result.json`, `summary.csv`, `route_traces.jsonl`, `result_summary_ko.md`, `short_paper_ko.md`에 기록됩니다. `.local/runs/`, `.local/data/`, `.local/hf_cache/`는 로컬 전용이며 Git에는 result brief와 재현 명령만 남깁니다. 자세한 기준은 `docs/00_overview/local_artifact_boundary_ko.md`를 봅니다.

## Claim Rule

항상 다음을 분리해서 말합니다.

```text
Resident VRAM reduction:
  shared backbone, smaller/quantized backbone, adapter residency compression에서 온다.

Visual token / KV reduction:
  FoveateR-style ROI evidence compression에서 온다.

End-to-end peak reduction:
  Track A와 Track B를 함께 측정하고,
  normal path / controlled fallback / emergency peak를 따로 보고해야 한다.
```
