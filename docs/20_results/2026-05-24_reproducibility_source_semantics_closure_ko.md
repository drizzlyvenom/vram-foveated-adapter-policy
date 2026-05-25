# 2026-05-24 Reproducibility + Source Semantics Closure

## 현재 방향성에서의 해석

이 결과는 새 Track A v2 실험이 따라야 할 source semantics와 재현성 경계를 정리한 기반 문서다. 성능 claim이 아니라, teacher annotation, Simula manifest, AdapterCard certification에서도 같은 `real vs proxy` 분리를 유지해야 한다는 근거로 쓴다.

## 요약

`ba2029a` 기준 main 작업면에서 real-task image smoke 재현 명령을 다시 실행했고, RTX 3090 real CUDA run이 정상 완료되었다. 이번 closure의 목적은 새 성능 claim을 추가하는 것이 아니라, **현재 repo의 공개 파일만으로 같은 검증 경로를 재실행할 수 있음**과 **trace/result가 실제 측정값과 proxy/estimate 값을 더 명확히 분리해 기록함**을 확인하는 것이다.

원본 산출물은 로컬 `.local/runs/20260524T072015Z-3090_two_track_pilot/` 아래에만 보관한다. Git에는 본 요약과 재현 명령, 핵심 source semantics만 남긴다.

## 실행 정보

```yaml
run_id: "20260524T072015Z-3090_two_track_pilot"
runner_commit: "ba2029a"
hardware: "NVIDIA GeForce RTX 3090"
model: "Qwen/Qwen3-VL-4B-Instruct"
measurement_mode: "real_cuda"
data_mode: "real_task_manifest"
schema_version: "3090.combined_validation_result.v0.2"
source_semantics_version: "v0.2"
roi_source: "center_crop"
samples: 2
matrix_cells: [C0, C1, C2, C3, C4, C5, C6, C7]
raw_artifacts_committed: false
```

재현 명령:

```powershell
python scripts\prepare_real_task_manifest.py --source picsum_highres --max-samples 4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\two_track_pilot.yaml --real-run --data-mode real_task_manifest --manifest .local\data\real_task_smoke\manifest.jsonl --max-samples 2 --max-new-tokens 4
```

## 핵심 결과

| Cell | Path | Visual tokens mean | Normal peak MB mean | Controlled fallback MB mean | Note |
|---|---|---:|---:|---:|---|
| C0 | shared backbone + full image | 768.0 | 8889.4315 | N/A | full visual context |
| C3 | taxonomy LoRA proxy + full image | 768.0 | 8961.4315 | N/A | adapter card estimate 포함 |
| C4 | taxonomy LoRA proxy + foveated ROI | 296.0 | 8681.853 | 8962.613 | center-crop ROI |
| C6 | taxonomy LoRA proxy + low-res only | 100.0 | 8591.346 | N/A | lowest visual evidence cost |
| C7 | taxonomy LoRA proxy + controlled fallback | 296.0 | 8681.853 | 8961.4245 | controlled fallback path |

```yaml
c4_visual_token_reduction_vs_c3: 0.614583
c4_prefill_latency_reduction_vs_full: 0.829276
shared_backbone_plus_lora_bank_resident_mb: 8536.481
multi_specialist_resident_estimate_mb: 33857.924
resident_saving_vs_multi_specialist_estimate: 0.747873
```

## Source Semantics 확인

이번 run의 `combined_validation_result.json`에는 다음 source summary가 남았다.

```yaml
actual_image_execution: true
image_sources:
  - "manifest.full_image_path"
roi_sources:
  - "center_crop"
source_datasets:
  - "Lorem Picsum high-resolution real image smoke"
task_validation_level: "real_task_image_smoke"
task_score_source: "synthetic_proxy"
adapter_execution_mode: "proxy_card_accounting"
adapter_memory_source: "adapter_card_estimate"
```

C4 trace 예시는 다음을 기록한다.

```yaml
sample_id: "picsum_highres_1"
image_source: "manifest.full_image_path"
manifest_full_image_path: ".local/data/real_task_smoke/images/picsum_highres_1.jpg"
selected_image_paths:
  - role: "low_res_global"
  - role: "roi_crop"
roi_box_xyxy: [288, 192, 1312, 1008]
actual_image_execution: true
```

실제 측정 필드와 proxy/estimate 필드는 분리된다.

```yaml
real_measurement_fields:
  - base_after_load_allocated_mb
  - base_after_load_reserved_mb
  - visual_incremental_peak_mb
  - visual_token_count
  - prefill_latency_ms
  - generation_latency_ms

estimate_or_proxy_fields:
  - active_adapter_resident_mb
  - adapter_bank_resident_mb
  - generate_extra_peak_over_prefill_mb
  - multi_specialist_resident_estimate_mb
  - task_score
  - verifier_score
```

## Gate 상태

```yaml
completion_gate: true
measurement_gate: true
promotion_gate: false

track_promotion_gates:
  resident_track_promotion_gate: false
  foveation_track_promotion_gate: false
  combined_track_promotion_gate: false
```

`promotion_gate=false`는 정상이다. 이번 closure는 실제 이미지와 실제 CUDA memory/token 계측은 확인했지만, trained LoRA execution, measured specialist swap, 실제 task accuracy는 아직 없다.

## 해석 가능한 Claim

```yaml
safe:
  - "main의 active runner/config/schema로 real-task image smoke가 재현된다."
  - "manifest.full_image_path 기반 실제 이미지가 full/low-res/ROI evidence path로 들어간다."
  - "trace와 combined result가 실제 측정 필드와 proxy/estimate 필드를 분리해 기록한다."
  - "이번 high-res smoke에서 C4 foveated ROI path는 C3 full-image path 대비 visual token을 줄였다."

not_yet:
  - "실제 task accuracy가 유지된다."
  - "actual PEFT 또는 merged LoRA adapter execution이 검증됐다."
  - "center_crop ROI가 task-relevant ROI를 안정적으로 찾는다."
  - "multi-specialist baseline을 실측으로 이겼다."
  - "production p95/p99 latency가 검증됐다."
```

## 다음 작업

```yaml
next:
  - oracle_box ROI source를 추가해 center_crop 대비 upper-bound gap을 측정한다.
  - tiny scored manifest를 추가해 synthetic task_score proxy를 benchmark/human-evaluable score로 교체한다.
  - sequential specialist swap latency를 별도 smoke로 측정한다.
  - actual_peft 또는 merged_lora adapter execution mode를 추가한다.
```
