# VRAM-Constrained Adapter Policy

이 프로젝트는 low-VRAM vision specialist를 하나의 shared VLM backbone 위에 통합하기 위한 연구 작업 폴더입니다. 현재 논문 중심축은 **Track A v2: Simula-compiled taxonomy LoRA bank**입니다. Track B의 foveated/ROI 경로는 버리지 않지만, 메인 기여가 아니라 adapter certification에서 visual evidence cost를 통제하는 보조 모듈로 둡니다.

```text
Track A v2. Simula-compiled taxonomy LoRA bank
  failure traces / low-confidence cases / wrong-adapter records
  -> Gemma 4 26B teacher annotations
  -> Simula curriculum compiler
  -> adapter-sensitive LoRA candidates
  -> AdapterCard-certified resident LoRA bank

Track B support. Visual evidence cost control
  full high-resolution visual context
  -> low-resolution global view + high-resolution ROI glimpses
  -> controlled input budget for Track A certification
```

현재 문서 해석 원칙은 다음입니다.

- Track A v2가 메인 연구축이다.
- Gemma 4 26B는 runtime model이 아니라 teacher/annotator/curriculum generator다.
- Simula는 runtime reasoner가 아니라 offline LoRA curriculum/compiler loop다.
- LoRA gain이나 routing utility는 `base / correct / wrong / random` certification gate를 통과하기 전까지 주장하지 않는다.
- Track B는 ROI/input compression baseline과 visual evidence budget control로만 쓴다.
- 기존 Track B 결과는 폐기하지 않고, adapter certification의 입력 비용 통제 근거로 재해석한다.

## 현재 핵심 문서

- Track A v2 reframe: `docs/30_paper_notes/track_a_v2_reframe_ko.md`
- Track A v2 validation milestones: `docs/30_paper_notes/track_a_v2_validation_milestones_ko.md`
- Track A v2 final closure brief: `docs/20_results/2026-05-25_track_a_v2_final_closure_ko.md`
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
- 3090 ROI stability 64-sample config: `configs/3090/tiny_scored_roi_stability_64.yaml`
- 3090 actual PEFT matrix smoke config: `configs/3090/tiny_scored_actual_peft_matrix_smoke.yaml`
- 3090 trained LoRA full C-matrix config: `configs/3090/tiny_scored_trained_lora_full_cmatrix.yaml`
- 3090 adapter cards: `configs/3090/adapter_cards.yaml`
- Track A v2 adapter cards: `configs/track_a_v2/adapter_cards/`
- 3090 result schemas: `schemas/3090/residency_trace.example.yaml`, `schemas/3090/combined_validation_result.example.yaml`
- Track A v2 schemas: `schemas/track_a_v2/`
- paper notes: `docs/30_paper_notes/`

## 경로 구조

```text
configs/3090/      active RTX 3090 configs
configs/track_a_v2/ Track A v2 AdapterCard and compatibility records
docs/00_overview/  overview, latest status, local artifact boundary
docs/10_protocols/ Track A v2 certification ladder, metrics contract, decision gates
docs/20_results/   committed result briefs and current interpretation notes
docs/30_paper_notes/ Track A v2 paper notes
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

기존 3090 diagnostic scaffold:

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
.venv\Scripts\python.exe scripts\prepare_tiny_scored_manifest.py --max-samples 64
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
.venv\Scripts\python.exe scripts\train_tiny_lora_smoke.py --manifest .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --roi-source ocr_detector_box --max-samples 32 --max-steps 32 --eval-train-samples 32 --eval-holdout-samples 32 --eval-max-new-tokens 8 --rank 4 --alpha 8 --learning-rate 1e-4 --label-mask-mode answer_only
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\tiny_scored_trained_lora_full_cmatrix.yaml --real-run --max-samples 64 --max-new-tokens 8
```

Track A v2 diagnostic closure path:

```powershell
.venv\Scripts\python.exe scripts\check_track_a_v2_schemas.py
.venv\Scripts\python.exe scripts\prepare_adapter_sensitive_manifest.py --samples-per-taxonomy-split 32 --output .local\data\track_a_v2_adapter_sensitive\manifest.jsonl
.venv\Scripts\python.exe scripts\run_gemma_teacher_gguf.py --manifest .local\data\track_a_v2_adapter_sensitive\manifest.jsonl --output .local\data\track_a_v2_adapter_sensitive\teacher_annotations.jsonl --max-per-taxonomy 1 --allow-deterministic-fallback
.venv\Scripts\python.exe scripts\compile_simula_curriculum.py --manifest .local\data\track_a_v2_adapter_sensitive\manifest.jsonl --teacher-annotations .local\data\track_a_v2_adapter_sensitive\teacher_annotations.jsonl --output .local\data\track_a_v2_adapter_sensitive\curriculum_manifest.jsonl
.venv\Scripts\python.exe scripts\run_track_a_v2_base_audit.py --curriculum .local\data\track_a_v2_adapter_sensitive\curriculum_manifest.jsonl --output .local\runs\track_a_v2_base_audit\base_audit_result.json
.venv\Scripts\python.exe scripts\train_track_a_v2_lora.py --curriculum .local\data\track_a_v2_adapter_sensitive\curriculum_manifest.jsonl --taxonomies document,chart --max-steps 32 --max-samples 32 --eval-train-samples 32 --eval-holdout-samples 32
.venv\Scripts\python.exe scripts\run_track_a_v2_certification.py --curriculum .local\data\track_a_v2_adapter_sensitive\curriculum_manifest.jsonl --lora-summary .local\runs\track_a_v2_lora_summary\single_lora_learns_summary.json --output .local\runs\track_a_v2_certification\certification_result.json
.venv\Scripts\python.exe scripts\run_track_a_v2_router_eval.py --certification .local\runs\track_a_v2_certification\certification_result.json --output .local\runs\track_a_v2_router_eval\router_eval_result.json
```

위 Track A v2 경로는 M0-M11 진단 폐쇄를 재현하는 scaffold다. 현재 Gemma teacher JSON, fully actual correct-vs-wrong/random margin, router utility, paper-ready 성능 claim은 열지 않는다.

ROI source stability plan:

```powershell
.venv\Scripts\python.exe scripts\run_roi_source_stability.py --config configs\3090\tiny_scored_roi_stability_64.yaml --manifest .local\data\tiny_scored_manifest\manifest_ocr_detector.jsonl --max-samples 64 --repeats 3 --max-new-tokens 8 --execute --output .local\runs\roi_stability_64_repeats3_plan.json
```

주요 산출물은 실행별 `.local/runs/<run_id>/combined_validation_result.json`, `summary.csv`, `route_traces.jsonl`, `result_summary_ko.md`, `short_paper_ko.md`에 기록됩니다. `.local/runs/`, `.local/data/`, `.local/hf_cache/`는 로컬 전용이며 Git에는 result brief와 재현 명령만 남깁니다. 자세한 기준은 `docs/00_overview/local_artifact_boundary_ko.md`를 봅니다.

## Claim Rule

항상 다음을 분리해서 말합니다.

```text
Track A v2 main claim:
  Simula/Gemma teacher loop가 failure traces를 adapter-sensitive curriculum으로 컴파일하고,
  AdapterCard certification을 통해 shared-backbone LoRA bank를 검증한다.

Resident specialist compression:
  shared backbone, smaller/quantized backbone, adapter residency compression에서 온다.

Track B support:
  FoveateR-style ROI evidence compression은 visual token/KV/prefill cost를 통제한다.

Do not claim yet:
  trained LoRA accuracy gain, multi-adapter routing utility,
  OCR ROI broad generalization, production p95/p99.
```
