# Docs Index

이 폴더는 active RTX 3090 two-track validation 문서를 목적별로 나눈다.

```text
docs/
  00_overview/   프로젝트 상태, claim boundary, 로컬 산출물 경계
  10_protocols/ 검증 ladder, metric contract, decision gate
  20_results/   raw runs 대신 커밋하는 결과 브리프
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

results:
  - docs/20_results/README.md
  - docs/20_results/2026-05-24_real_task_image_smoke_ko.md
  - docs/20_results/2026-05-24_reproducibility_source_semantics_closure_ko.md
```

원본 실행 산출물은 `.local/runs/`에 두고 Git에는 올리지 않는다. Git에는 재현 명령, 핵심 수치, gate 상태, source semantics, claim boundary를 담은 result brief만 남긴다.
