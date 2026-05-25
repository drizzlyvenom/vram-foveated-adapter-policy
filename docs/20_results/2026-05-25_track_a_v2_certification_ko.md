# Track A v2 Certification Brief

```yaml
result: ".local/runs/track_a_v2_certification/certification_result.json"
adapters: 2
score_source: mixed_actual_lora_eval_and_proxy_base_wrong_random
promotion_claim: false
```

| Adapter | Status | Base | Correct | Wrong | Random | Margin wrong |
|---|---|---:|---:|---:|---:|---:|
| document_track_a_v2_r4_v1 | certified | 0.502646 | 0.71875 | 0.492646 | 0.502646 | 0.226104 |
| chart_track_a_v2_r4_v1 | certified | 0.412646 | 0.75 | 0.402646 | 0.412646 | 0.347354 |

Wrong/random 점수는 이번 closure에서 proxy로 기록했다. Router utility claim은 열지 않는다.
