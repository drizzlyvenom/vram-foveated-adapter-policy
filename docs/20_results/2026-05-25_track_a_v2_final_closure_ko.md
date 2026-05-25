# Track A v2 Final Milestone Closure

Status: M0-M11 closed as diagnostic / certification scaffold
Date: 2026-05-25
Promotion gate: false

## 요약

`docs/30_paper_notes/track_a_v2_validation_milestones_ko.md`를 기준 문서로 두고 Track A v2 마일스톤을 당일 폐쇄했다. 폐쇄의 의미는 모든 항목에 대해 실행 산출물과 pass/fail/claim boundary를 남겼다는 뜻이며, paper-ready 성능 claim을 열었다는 뜻은 아니다.

```yaml
main_axis: "Simula-compiled taxonomy LoRA bank"
teacher_model: "google/gemma-4-26B-A4B-it"
gemma_runtime_attempted: true
gemma_runtime_status: "llama.cpp loaded model but exited with 3221226505; deterministic fallback annotations used"
adapter_sensitive_manifest_samples: 256
actual_lora_taxonomies: ["document", "chart"]
multi_adapter_bank_run: "20260525T030429Z-multi_lora_bank_smoke"
promotion_gate: false
```

## 마일스톤 상태

| Milestone | Status | Evidence |
|---|---|---|
| M0 Reframe lock | closed | README/paper notes Track A v2 정렬, `VFA_Milestone.md`는 `Legacy/handoff/` 보존 |
| M1 Schema and registry | closed | `schemas/track_a_v2/`, `scripts/check_track_a_v2_schemas.py` pass |
| M2 Adapter-sensitive dataset | closed | `.local/data/track_a_v2_adapter_sensitive/manifest.jsonl`, 256 samples |
| M3 Simula teacher/compiler | closed_with_fallback | Gemma GGUF/mmproj attempted, fallback annotations + curriculum manifest generated |
| M4 Base difficulty audit | closed_as_proxy | `.local/runs/track_a_v2_base_audit/base_audit_result.json`, holdout proxy score 0.455146 |
| M5 Single LoRA learns | closed | document/chart actual LoRA training, holdout scores 0.71875 and 0.75 |
| M6 Correct beats wrong | closed_as_mixed_evidence | correct scores actual, base/wrong/random proxy; no broad claim |
| M7 AdapterCard certification | closed | `configs/track_a_v2/adapter_cards/*.yaml` |
| M8 Taxonomy router | closed_as_path | taxonomy router result generated; utility claim remains closed |
| M9 Multi-adapter bank serving | closed | bank delta 22.5 MB, attach latency 518.369 ms |
| M10 Compatibility/collapse audit | closed_as_smoke | correct-minus-wrong 0.0, compatibility edge recorded |
| M11 Paper-ready table | closed_negative | final table available, paper-ready claim remains false |

## 핵심 수치

```yaml
dataset:
  samples: 256
  train: 128
  holdout: 128
  taxonomies: 4

single_lora:
  document:
    run_id: "20260525T030210Z-tiny_lora_train"
    train_score: 0.71875
    holdout_score: 0.71875
  chart:
    run_id: "20260525T030309Z-tiny_lora_train"
    train_score: 0.75
    holdout_score: 0.75

multi_adapter_bank:
  run_id: "20260525T030429Z-multi_lora_bank_smoke"
  adapter_bank_allocated_delta_mb: 22.5
  correct_score_mean: 0.75
  wrong_score_mean: 0.75
  correct_minus_wrong_score_mean: 0.0
```

## Claim Boundary

Safe:

- Track A v2 schema, manifest, teacher-compiler, LoRA train, certification-card, router, and bank-smoke paths exist.
- Gemma 4 26B GGUF/mmproj execution was attempted locally through llama.cpp.
- Two taxonomy LoRA adapters were actually trained/evaluated on the adapter-sensitive manifest.

Not yet:

- Gemma teacher produced valid model JSON.
- Correct-vs-wrong/random margin is fully actual measured evidence.
- Multi-adapter routing improves accuracy.
- Paper-ready Track A performance claim.
