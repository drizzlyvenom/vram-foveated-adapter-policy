# Stage 1+ Closure Report

Date: 2026-05-24
Run ID: `20260524T024426Z-stage1plus_protocol_qwen3_vl`
Run directory: `runs\20260524T024426Z-stage1plus_protocol_qwen3_vl`

## 1. 범위

Stage 1+는 Qwen3-VL-4B 기준 로컬 protocol-complete pilot이다. 이번 단계는 여섯 항목을 skip하지 않고 같은 manifest 위에서 실행해 RouteTrace, summary, verifier/fallback/quarantine 산출물을 남기는 것을 목표로 한다.

다만 LoRA 항목은 아직 학습된 실제 weight adapter 성능 주장이 아니다. `prompt_strategy_and_vram_residency_proxy`로 adapter-card 격리, declared resident memory, wrong-adapter damage test, router/verifier 연결을 검증한 것이다.

## 2. 실행 환경

```text
model: Qwen/Qwen3-VL-4B-Instruct
precision: float16
device: NVIDIA GeForce RTX 3090
torch: 2.12.0+cu126
cuda runtime: 12.6
model load: 4.028 s
samples: 20
```

## 3. Stage별 요약

| stage | n | task score mean | visual tokens mean | peak VRAM p95 MB | latency p95 ms | route hit | fallback rate | failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1plus_closed_loop | 20 | 0.8380 | 430.8000 | 8960.9450 | 677.3618 |  | 0.1000 | 3 |
| 1plus_foveation_quality | 80 | 0.8658 | 337.5000 | 8924.3995 | 669.1263 |  | 0.0000 | 0 |
| 1plus_jepa_outcome_routing | 20 | 0.8380 | 430.8000 | 8960.9450 | 677.3618 |  | 0.0000 | 0 |
| 1plus_lewm_feature_augmentation | 80 | 0.9750 | 0.0000 |  | 0.0000 | 0.9750 | 0.0000 | 2 |
| 1plus_lora_isolation | 40 | 0.8790 | 345.0000 | 8778.3021 | 660.1591 |  | 0.0000 | 0 |
| 1plus_taxonomy_card_routing | 80 | 1.0000 | 0.0000 |  | 0.0000 | 1.0000 | 0.0000 | 0 |

## 4. 여섯 항목 체크

Completion passed: `True`
Scientific gate passed: `True`

| item | completion | scientific gate | detail |
|---|---:|---:|---|
| all_required_protocol_stages_present | True | True | stages=['1plus_closed_loop', '1plus_foveation_quality', '1plus_jepa_outcome_routing', '1plus_lewm_feature_augmentation', '1plus_lora_isolation', '1plus_taxonomy_card_routing'] |
| foveation_quality_measured_and_cost_reduced | True | True | heuristic tokens=345.0, fullres tokens=609.0, heuristic vram=8643.064184570312, fullres vram=8816.975341796875 |
| lora_isolation_proxy_measured | True | True | correct traces=20, wrong traces=20, mean correct gain=0.0, mean wrong damage=0.0 |
| taxonomy_card_router_measured | True | True | manual hit=1.0, taxonomy+cost hit=1.0, abstentions=0 |
| lewm_feature_augmentation_measured | True | True | taxonomy base hit=1.0, taxonomy+LeWM hit=1.0; direct LeWM route is ablation only |
| jepa_outcome_predictor_measured | True | True | selected regret=0.05197857932051745, taxonomy regret=0.014014547270644773, delta=-0.03796403204987268 |
| verifier_fallback_quarantine_measured | True | True | closed_loop=20, fallback_attempted=2, fallback_success=0, no_fallback_available=1, quarantine_count=3 |

## 5. JEPA-style Outcome Routing

```text
gain_prediction_mae: 0.2175
latency_prediction_mae: 125.6050
peak_vram_prediction_mae: 3.8205
selected_action_regret_mean: 0.0520
taxonomy_regret_mean: 0.0140
regret_delta_vs_taxonomy: -0.0380
```

JEPA selector는 damage-test용 wrong adapter와 random ROI를 학습/평가 후보에는 남기되, runtime 선택 후보에서는 제외한다. 이 guard는 verifier/fallback 단계의 후보 적격성 검사에 해당한다. 이번 run에서는 JEPA 선택 regret이 taxonomy baseline보다 높으므로, JEPA는 아직 runtime 우위 claim이 아니라 outcome logging과 후보 평가 protocol로만 해석한다.

## 6. Verifier / Fallback / Quarantine

```text
closed_loop_decisions: 20
fallback_available: 14
fallback_attempted: 2
fallback_success: 0
no_fallback_available: 1
quarantine_count: 3
```

이번 run의 fallback은 `fallback_available`, `fallback_attempted`, `fallback_success`, `no_fallback_available`를 분리해 기록한다. 이미 fullres까지 간 실패는 fallback을 시도한 것으로 세지 않고, 복구 가능한 ROI miss와 모델 자체 오답을 분리한다.

Failure type counts:

```text
model_answer_error: 2
no_fallback_available: 1
none: 17
```

Verifier 보강으로 숫자 근사값, 문장형 리스트 답변, VQA-style 부분 정답을 더 부드럽게 처리한다. 이 보강 후 RICO list answer류 false reject가 줄었고, 남은 quarantine은 `no_fallback_available`와 `model_answer_error`로 분리되었다.

## 7. 산출물

```text
run_manifest.json
route_traces.jsonl
summary.csv
summary_by_stage.csv
jepa_predictions.csv
closed_loop_decisions.csv
quarantine_buffer.csv
checks.json
artifacts/lewm_features/*.json
```

## 8. 해석 경계

- Qwen3-VL-4B inference, visual token estimate, latency, peak VRAM은 로컬 CUDA 실행에서 측정했다.
- LoRA isolation은 실제 fine-tuned LoRA weight의 성능 검증이 아니라 adapter-card routing과 resident-memory proxy 검증이다.
- LeWM feature는 실제 LeWM checkpoint가 아니라 image-stat 기반 LeWM-style observation proxy다.
- JEPA outcome predictor는 final text를 예측하지 않고 action outcome metric을 예측하는 선형 proxy다.
- 따라서 Stage 1+는 Stage 2/3-lite로 넘어가기 위한 protocol closure이며, trained LoRA gain 주장은 아직 하지 않는다.
