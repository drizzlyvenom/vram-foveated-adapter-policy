# Paper Notes

이 폴더는 raw run 결과가 아니라 소논문 작성에 필요한 얇은 작업 노트를 둔다.

```yaml
files:
  paper_outline_ko.md:
    role: "Track A v2 중심축에 맞춘 소논문 구조"
  claim_table_ko.md:
    role: "Track A v2에서 쓸 수 있는 claim과 아직 금지할 claim 분리"
  ablation_table_plan_ko.md:
    role: "AdapterCard certification 중심 표 설계, ROI/C-matrix는 보조 표로 분리"
  track_a_v2_reframe_ko.md:
    role: "Simula/Gemma teacher 기반 Track A v2 중심축 재정렬"
  track_a_v2_validation_milestones_ko.md:
    role: "proxy-tainted M0-M11 폐기 기록과 no-proxy 재검증 gate"
```

원칙은 간단하다. Track A를 중심축으로 두되, proxy/estimate/fallback이 섞인 검증 결과는 쓰지 않는다. 기존 M0-M11 closure와 Track B result briefs는 `trashbin/proxy_result_quarantine_2026-05-25/`로 격리했으며, Gemma teacher JSON success, fully actual correct-vs-wrong/random certification, router utility, paper-ready performance claim은 no-proxy 후속 run 전까지 쓰지 않는다.
