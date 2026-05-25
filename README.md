# VRAM-Constrained Adapter Policy

Status: Legacy archive
Date: 2026-05-25

이 레포지토리는 이제 **Legacy 보관용 작업 폴더**입니다. 새 실험과 논문용 검증은 새 레포지토리에서 다시 시작합니다.

이곳의 문서, 설정, 결과 브리프는 기존 방향성과 시행착오를 추적하기 위한 기록으로만 남깁니다. 특히 2026-05-25 기준으로 proxy/estimate/fallback이 한 번이라도 섞인 검증 결과는 폐기하고 `trashbin/proxy_result_quarantine_2026-05-25/`로 옮겼습니다. 따라서 이 레포지토리의 이전 검증 결과는 새 프로젝트의 성능 근거로 인용하지 않습니다.

원래 목표는 low-VRAM vision specialist를 하나의 shared VLM backbone 위에 통합하기 위한 연구 작업이었습니다. 마지막 작업 축은 **Track A v2: Simula-compiled taxonomy LoRA bank**였지만, 이 축도 새 레포지토리에서 no-proxy 기준으로 재설계해야 합니다.

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
- Track B는 no-proxy 재검증 전까지 결과 근거로 쓰지 않는다.
- 기존 proxy-tainted Track B/Track A closure 결과는 폐기한다.

## 현재 핵심 문서

- Track A v2 reframe: `docs/30_paper_notes/track_a_v2_reframe_ko.md`
- Track A v2 validation milestones: `docs/30_paper_notes/track_a_v2_validation_milestones_ko.md`
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

현재 검증 재실행 규칙은 단순합니다. validation evidence에 proxy, mixed proxy, estimate, deterministic fallback이 한 번이라도 들어가면 그 결과는 폐기합니다.

```powershell
.venv\Scripts\python.exe scripts\check_track_a_v2_schemas.py
.venv\Scripts\python.exe scripts\prepare_adapter_sensitive_manifest.py --samples-per-taxonomy-split 32 --output .local\data\track_a_v2_adapter_sensitive\manifest.jsonl
```

기존 `configs/3090/` 기반 결과와 이전 Track A v2 M0-M11 closure는 proxy-tainted 결과로 격리했다. no-proxy 검증 커맨드는 actual teacher, actual base/correct/wrong/random scoring, actual adapter switching만 남도록 다시 짠 뒤 사용한다.

## Claim Rule

항상 다음을 분리해서 말합니다.

```text
Track A v2 main claim:
  no-proxy teacher/curriculum/certification loop가 실제로 통과한 뒤에만 연다.

Resident specialist compression:
  실제 측정된 shared backbone, smaller/quantized backbone, adapter residency compression만 쓴다.

Track B support:
  no-proxy 재검증 전까지 결과 claim으로 쓰지 않는다.

Do not claim yet:
  quarantined proxy results, trained LoRA accuracy gain, multi-adapter routing utility,
  OCR ROI broad generalization, production p95/p99.
```
