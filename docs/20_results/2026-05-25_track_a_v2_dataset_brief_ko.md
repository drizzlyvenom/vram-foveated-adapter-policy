# Track A v2 Adapter-Sensitive Dataset Brief

## 요약

Track A v2 certification을 위해 taxonomy별 adapter-sensitive synthetic manifest를 생성했다.

```yaml
manifest: ".local/data/track_a_v2_adapter_sensitive/manifest.jsonl"
samples: 256
train_samples: 128
holdout_samples: 128
promotion_claim: false
```

## Claim Boundary

- safe: manifest/schema/input generation path is available
- not_yet: trained LoRA gain, router utility, broad benchmark generalization
