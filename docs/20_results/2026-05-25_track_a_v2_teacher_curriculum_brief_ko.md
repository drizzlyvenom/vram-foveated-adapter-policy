# Track A v2 Gemma Teacher / Simula Curriculum Brief

## 요약

Gemma teacher annotation row와 manifest truth를 합쳐 Simula-style curriculum manifest를 생성했다.

```yaml
curriculum_manifest: ".local/data/track_a_v2_adapter_sensitive/curriculum_manifest.jsonl"
samples: 256
teacher_representative_rows: 4
rule_expanded_rows: 252
adapters: 4
teacher_label_is_final_truth: false
gemma_runtime_attempted: true
gemma_runtime_ok_rows: 0
gemma_runtime_fallback_rows: 4
promotion_claim: false
```

## Claim Boundary

- safe: teacher/curriculum compile path is available
- not_yet: Gemma teacher JSON output, teacher labels are final truth, adapter utility, router utility
