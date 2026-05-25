# Docs Index

이 폴더는 active RTX 3090 / Track A v2 validation 문서를 목적별로 나눈다. 현재 논문 중심축은 `Simula-compiled taxonomy LoRA bank`이지만, 2026-05-25 기준으로 proxy/estimate/fallback이 섞인 검증 결과는 모두 폐기하고 `trashbin/proxy_result_quarantine_2026-05-25/`로 옮겼다.

```text
docs/
  00_overview/   프로젝트 상태, claim boundary, 로컬 산출물 경계
  10_protocols/ Track A v2 certification ladder, metric contract, decision gate
  20_results/   raw runs 대신 커밋하는 결과 브리프와 현재 해석
  30_paper_notes/ Track A v2 reframe, 소논문 outline, claim table, ablation/table plan
```

현재 active 문서는 다음 경로를 기준으로 참조한다.

```yaml
overview:
  - docs/00_overview/3090_two_track_validation_guideline_ko.md
  - docs/00_overview/latest_run_status_ko.md
  - docs/00_overview/local_artifact_boundary_ko.md

protocols:
  - docs/10_protocols/3090_execution_ladder_ko.md
  - docs/10_protocols/3090_metrics_contract_ko.md
  - docs/10_protocols/3090_decision_gates_ko.md
  - schemas/track_a_v2/
  - configs/track_a_v2/

results:
  - docs/20_results/README.md

paper_notes:
  - docs/30_paper_notes/README.md
  - docs/30_paper_notes/track_a_v2_reframe_ko.md
  - docs/30_paper_notes/track_a_v2_validation_milestones_ko.md
  - docs/30_paper_notes/paper_outline_ko.md
  - docs/30_paper_notes/claim_table_ko.md
  - docs/30_paper_notes/ablation_table_plan_ko.md
```

원본 실행 산출물은 `.local/runs/`에 두고 Git에는 올리지 않는다. 단, proxy/estimate/fallback이 한 번이라도 섞인 검증 결과는 active 결과로 보존하지 않는다.

현재 문서 해석의 우선순위는 다음이다.

```yaml
current_direction:
  main_axis: "Track A v2 / Simula-compiled taxonomy LoRA bank"
  teacher: "Gemma 4 26B as offline annotator and curriculum generator"
  compiler: "Simula as offline LoRA curriculum compiler"
  support_axis: "Track B must be rerun under no-proxy result rules before it can be cited"
  latest_closure: "previous M0-M11 diagnostic closure invalidated by proxy-tainted evidence"
  quarantine: "trashbin/proxy_result_quarantine_2026-05-25/"
  next_focus:
    - "actual-only base/correct/wrong/random certification"
    - "Gemma teacher only after valid model JSON, no deterministic fallback"
    - "no-proxy Track A rerun"
  closed_claims:
    - trained LoRA accuracy gain
    - multi-adapter routing utility
    - OCR ROI broad benchmark generalization
```
