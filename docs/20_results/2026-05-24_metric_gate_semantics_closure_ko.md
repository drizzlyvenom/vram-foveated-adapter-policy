# 2026-05-24 Metric/Gate Semantics Closure

## 현재 방향성에서의 해석

이 결과는 Track A v2의 메인 성능 근거가 아니라, 이후 AdapterCard certification runner가 써야 할 metric/gate semantics를 닫은 infrastructure evidence다. Track B 관련 C-matrix 값은 visual evidence cost control 보조 근거로만 읽는다.

## 요약

`a1a158a` 기준 main 작업면에서 M-A metric/gate semantics 변경을 적용한 뒤, RTX 3090 real CUDA smoke를 다시 실행했다. 이번 closure의 목적은 새 성능 claim을 추가하는 것이 아니라, C-matrix 결과가 **점수 출처**, **controlled fallback peak의 조건부/전체 샘플 의미**, **minimum/extended completion gate**를 분리해 기록하는지 확인하는 것이다.

원본 산출물은 로컬 `.local/runs/20260524T080046Z-3090_two_track_pilot/` 아래에만 보관한다. Git에는 본 요약과 재현 명령, 핵심 수치, claim boundary만 남긴다.

## 실행 정보

```yaml
run_id: "20260524T080046Z-3090_two_track_pilot"
runner_commit: "a1a158a"
hardware: "NVIDIA GeForce RTX 3090"
model: "Qwen/Qwen3-VL-4B-Instruct"
measurement_mode: "real_cuda"
data_mode: "real_task_manifest"
schema_version: "3090.combined_validation_result.v0.3"
source_semantics_version: "v0.2"
roi_source: "center_crop"
samples: 1
matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
raw_artifacts_committed: false
```

재현 명령:

```powershell
python scripts\prepare_real_task_manifest.py --source picsum_highres --max-samples 4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\two_track_pilot.yaml --real-run --data-mode real_task_manifest --manifest .local\data\real_task_smoke\manifest.jsonl --max-samples 1 --max-new-tokens 2
```

## 핵심 결과

| Cell | Path | Visual tokens mean | Normal peak MB mean | Controlled fallback conditional MB mean | Controlled fallback all-sample MB mean | Controlled fallback rate |
|---|---|---:|---:|---:|---:|---:|
| C4 | taxonomy LoRA proxy + foveated ROI | 296.0 | 8681.853 | 8962.613 | 8962.613 | 1.0 |
| C7 | taxonomy LoRA proxy + controlled fallback | 296.0 | 8681.853 | 8962.613 | 8962.613 | 1.0 |

```yaml
c0_full_visual_tokens_mean: 768.0
c4_foveated_visual_tokens_mean: 296.0
c4_visual_token_reduction_vs_c3: 0.614583
shared_backbone_plus_lora_bank_resident_mb: 8536.481
multi_specialist_resident_estimate_mb: 33857.924
resident_saving_vs_multi_specialist_estimate: 0.747873
```

## Score Semantics

현재 `task_score`는 실제 task accuracy가 아니라 synthetic proxy다. 따라서 `task_score_mean`만 보고 성능 우위를 주장하지 않도록, schema v0.3에서는 다음 필드를 명시적으로 남긴다.

```yaml
c4:
  task_score_mean: 0.756
  proxy_task_score_mean: 0.756
  task_score_source: "synthetic_proxy"
  actual_task_score_available_rate: 0.0

c7:
  task_score_mean: 0.751
  proxy_task_score_mean: 0.751
  task_score_source: "synthetic_proxy"
  actual_task_score_available_rate: 0.0
```

## Fallback Semantics

`controlled_fallback_peak_mb_conditional_mean`은 controlled fallback이 실제로 실행된 샘플만 평균낸 값이다. `controlled_fallback_peak_mb_all_samples_mean`은 fallback이 실행되지 않은 샘플까지 포함해 policy-level 평균 비용을 해석하기 위한 값이며, fallback 미실행 샘플은 normal path peak로 채운다.

이번 1-sample smoke에서는 C4와 C7에서 controlled fallback이 모두 실행되어 conditional mean과 all-sample mean이 같다.

```yaml
fallback_summary:
  normal_path_peak_mb_mean: 8681.853
  controlled_fallback_peak_mb_conditional_mean: 8962.613
  controlled_fallback_peak_mb_all_samples_mean: 8962.613
  controlled_fallback_rate: 1.0
  fallback_rate: 1.0
  c7_controlled_fallback_peak_mb_conditional_mean: 8962.613
  c7_controlled_fallback_peak_mb_all_samples_mean: 8962.613
  c7_controlled_fallback_rate: 1.0
```

## Gate 상태

```yaml
completion_gate: true
minimum_completion_gate: true
extended_completion_gate: true
measurement_gate: true
promotion_gate: false

minimum_required_cells: [C0, C1, C2, C3, C4, C5]
extended_required_cells: [C0, C1, C2, C3, C4, C5, C6, C7]

track_promotion_gates:
  resident_track_promotion_gate: false
  foveation_track_promotion_gate: false
  combined_track_promotion_gate: false
```

`promotion_gate=false`는 정상이다. 이번 closure는 metric semantics와 gate semantics를 닫는 단계이며, trained LoRA execution, measured specialist swap, 실제 task accuracy는 아직 없다.

## 해석 가능한 Claim

```yaml
safe:
  - "schema v0.3 결과가 task_score_source와 proxy_task_score_mean을 분리해 기록한다."
  - "controlled fallback peak가 conditional mean과 all-sample mean으로 분리 기록된다."
  - "minimum completion gate와 extended completion gate가 별도로 계산된다."
  - "RTX 3090 real CUDA smoke에서 C0-C7 extended matrix 산출물이 생성된다."

not_yet:
  - "실제 task accuracy가 유지된다."
  - "actual PEFT 또는 merged LoRA adapter execution이 검증됐다."
  - "multi-specialist baseline을 실측으로 이겼다."
  - "controlled fallback이 일반적으로 낮은 비용을 보장한다."
  - "production p95/p99 latency가 검증됐다."
```

## 다음 작업

```yaml
next:
  - actual task score가 붙는 tiny benchmark manifest를 추가한다.
  - oracle_box 또는 OCR_box ROI source로 center_crop proxy를 대체한다.
  - actual_peft 또는 merged_lora adapter execution mode를 추가한다.
  - sequential specialist swap latency를 측정해 resident compression baseline을 estimate에서 real measurement로 승격한다.
```
