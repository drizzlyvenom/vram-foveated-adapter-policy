# Paper Notes

이 폴더는 raw run 결과가 아니라 소논문 작성에 필요한 얇은 작업 노트를 둔다.

```yaml
files:
  paper_outline_ko.md:
    role: "현재 evidence boundary에 맞춘 소논문 구조"
  claim_table_ko.md:
    role: "쓸 수 있는 claim과 아직 금지할 claim 분리"
  ablation_table_plan_ko.md:
    role: "ROI/source, resident/adapter, C-matrix 표 설계"
```

원칙은 간단하다. controlled tiny set 결과는 diagnostic evidence로 쓰고, benchmark generalization이나 trained LoRA gain은 실제 후속 run이 생기기 전까지 쓰지 않는다.
