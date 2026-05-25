# Track A v2 Base Difficulty Audit

```yaml
measurement_mode: "deterministic_proxy_difficulty_audit"
manifest: ".local/data/track_a_v2_adapter_sensitive/manifest.jsonl"
samples: 256
overall_holdout_base_score: 0.455146
pass: true
promotion_claim: false
```

| Taxonomy | Split | Samples | Base score | Difficulty |
|---|---|---:|---:|---|
| chart | holdout | 32 | 0.412646 | in_range |
| chart | train | 32 | 0.412646 | in_range |
| document | holdout | 32 | 0.502646 | in_range |
| document | train | 32 | 0.502646 | in_range |
| scene_text | holdout | 32 | 0.432646 | in_range |
| scene_text | train | 32 | 0.432646 | in_range |
| ui_screen | holdout | 32 | 0.472646 | in_range |
| ui_screen | train | 32 | 0.472646 | in_range |

이 audit은 빠른 difficulty proxy이며, actual Qwen base accuracy claim은 열지 않는다.
