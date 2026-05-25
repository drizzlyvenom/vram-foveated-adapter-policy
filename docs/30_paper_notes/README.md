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
    role: "AdapterCard/Simula/compiler 기준 Track A v2 M0-M11 진단 폐쇄와 남은 gate"
```

원칙은 간단하다. Track A를 중심축으로 두고, Track B는 visual evidence cost control 보조 모듈로만 쓴다. M0-M11은 진단 폐쇄로 닫혔지만, Gemma teacher JSON success, fully actual correct-vs-wrong/random certification, router utility, paper-ready performance claim은 실제 후속 run이 생기기 전까지 쓰지 않는다.
