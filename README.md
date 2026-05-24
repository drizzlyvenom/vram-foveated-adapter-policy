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

- Codex reframe guide: `CODEX_README.md`
- Core plan: `docs/core_two_track_research_plan_ko.md`
- Validation matrix: `docs/combined_validation_matrix_ko.md`
- Memory accounting: `docs/resident_memory_accounting_protocol_ko.md`
- Track A: `docs/shared_backbone_lora_consolidation_ko.md`
- Track B: `docs/foveater_visual_evidence_compression_ko.md`
- Compatibility certification: `docs/lora_compatibility_certification_ko.md`
- Fallback budget tiers: `docs/fallback_budget_tiers_ko.md`
- Claim boundary: `docs/claim_boundary_and_paper_positioning_ko.md`

## 보조 및 탐색 문서

```text
docs/supporting/
  stage1_foveation_smoke_closure_ko.md

docs/exploratory/
  stage1plus_protocol_closure_ko.md
```

Stage 1은 visual token / ROI cost accounting을 위한 supporting smoke evidence입니다.

Stage 1+는 RouteTrace, adapter-card proxy wiring, LeWM/JEPA proxy, fallback/quarantine instrumentation이 한 계약 안에서 실행된다는 exploratory protocol closure입니다. Stage 1+를 trained LoRA 효과, JEPA runtime 우위, fallback recovery 성능의 최종 증거로 사용하지 않습니다.

## Legacy 보관

이전 방향의 문서와 발표/정책 초안은 삭제하지 않고 `Legacy/`로 이동했습니다.

```text
Legacy/docs/
Legacy/output/
Legacy/source_bundles/vfa_two_track_docs/
```

기존 발표 자료, 논문 초안 PDF/TeX, PPTX, 최종 대본 등 비마크다운 산출물은 `output/` 아래에 남아 있습니다.

## 실행 참고

Stage 0/1/1+ 실행 스크립트와 설정은 아직 repo에 남아 있으며, 현재는 supporting/exploratory evidence 재현용입니다.

```powershell
python -m pip install -r requirements.txt
python scripts\run_pilot.py --config configs\pilot_minimal.yaml
python scripts\prepare_stage1_dataset.py --config configs\stage1_foveation_smoke.yaml
python scripts\run_stage1_foveation.py --config configs\stage1_foveation_smoke.yaml
```

Stage 1+ Qwen3-VL protocol pilot:

```powershell
.\.venv\Scripts\python scripts\run_stage1plus_protocol.py --config configs\stage1plus_protocol.yaml
```

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
