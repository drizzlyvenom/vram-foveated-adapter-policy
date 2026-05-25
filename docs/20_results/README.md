# Result Briefs

이 폴더는 `.local/runs/` 원본 산출물을 그대로 커밋하지 않고, 연구 판단과 외부 검토에 필요한 얇은 결과 브리핑만 남기는 공간이다. Git에 남는 결과 브리프와 로컬 전용 raw artifact의 관계는 [local artifact boundary](../00_overview/local_artifact_boundary_ko.md)에 정리한다.

현재 Track A v2 방향성에서는 아래 결과들을 메인 성능 주장으로 승격하지 않는다. 결과 브리프는 다음처럼 읽는다.

```yaml
current_interpretation:
  roi_and_cmatrix_results: "Track B support / visual evidence cost control"
  actual_peft_and_multi_lora_results: "Track A path smoke"
  external_n32_no_gain: "negative evidence that current task/taxonomy is not adapter-sensitive"
  track_a_v2_m0_m11: "diagnostic closure with promotion gate false"
  next_use: "actual Gemma teacher recovery and fully measured certification input"
```

## 원칙

```yaml
commit:
  - result brief markdown
  - key metrics
  - claim boundary
  - commands needed to reproduce
  - next action

do_not_commit_by_default:
  - raw route_traces.jsonl
  - probe images
  - downloaded datasets
  - full runs directory
  - local model cache
```

원본 산출물은 로컬 `.local/runs/<run_id>/` 아래에 둔다. Git에는 `run_id`, 핵심 수치, gate 상태, source semantics, 해석 가능한 claim만 남긴다.

## Index

| Date | Brief | Run | Status |
|---|---|---|---|
| 2026-05-25 | [Track A v2 final milestone closure](2026-05-25_track_a_v2_final_closure_ko.md) | `20260525T030210Z`, `20260525T030309Z`, `20260525T030429Z` | M0-M11 diagnostic closure, docs synced, promotion gate false |
| 2026-05-25 | [Track A v2 router / bank closure](2026-05-25_track_a_v2_router_bank_closure_ko.md) | `track_a_v2_router_eval`, `20260525T030429Z` | router path + multi-adapter bank smoke |
| 2026-05-25 | [Track A v2 certification](2026-05-25_track_a_v2_certification_ko.md) | `track_a_v2_certification` | AdapterCard certification with mixed/proxy boundary |
| 2026-05-25 | [Track A v2 single LoRA learns](2026-05-25_track_a_v2_single_lora_learns_ko.md) | `20260525T030210Z`, `20260525T030309Z` | actual document/chart LoRA training |
| 2026-05-25 | [Track A v2 base audit](2026-05-25_track_a_v2_base_audit_ko.md) | `track_a_v2_base_audit` | deterministic difficulty proxy |
| 2026-05-25 | [Track A v2 Gemma teacher / curriculum](2026-05-25_track_a_v2_teacher_curriculum_brief_ko.md) | `20260525T030116Z`, `simula_curriculum_summary` | Gemma attempted, fallback curriculum compiled |
| 2026-05-25 | [Track A v2 adapter-sensitive dataset](2026-05-25_track_a_v2_dataset_brief_ko.md) | `.local/data/track_a_v2_adapter_sensitive` | 256-sample manifest |
| 2026-05-25 | [External n32 / multi-LoRA bank / Qwen2 backbone sweep](2026-05-25_external_n32_multi_lora_backbone_ko.md) | `20260525T005611Z`, `20260525T005917Z`, `20260525T010610Z`, `20260525T011135Z` | external n32 + multi-adapter + one lightweight backbone diagnostic |
| 2026-05-24 | [64 unique stability / LoRA holdout / actual PEFT full C-matrix](2026-05-24_unique64_stability_lora_peft_ko.md) | `20260524T114337Z`, `20260524T114456Z`, `roi_stability_64_repeats3_plan` | 64 unique + repeats=3 controlled diagnostic |
| 2026-05-24 | [P1 answer mask / OCR stability](2026-05-24_p1_answer_mask_ocr_stability_ko.md) | `20260524T105236Z`, `20260524T105933Z` | answer-only mask + n32 cyclic OCR smoke |
| 2026-05-24 | [OCR detector / tiny trained LoRA smoke](2026-05-24_ocr_detector_trained_lora_smoke_ko.md) | `20260524T095934Z`, `20260524T095906Z` | detector + trained adapter smoke |
| 2026-05-24 | [Scored ROI / swap / PEFT validation](2026-05-24_scored_roi_swap_peft_validation_ko.md) | `20260524T090102Z`, `20260524T090206Z`, `20260524T090316Z` | M-B~M-F initial measured pass |
| 2026-05-24 | [Metric/gate semantics closure](2026-05-24_metric_gate_semantics_closure_ko.md) | `20260524T080046Z-3090_two_track_pilot` | metric/gate semantics closure |
| 2026-05-24 | [Reproducibility + source semantics closure](2026-05-24_reproducibility_source_semantics_closure_ko.md) | `20260524T072015Z-3090_two_track_pilot` | reproducibility/source-semantics closure |
| 2026-05-24 | [Real-task image smoke](2026-05-24_real_task_image_smoke_ko.md) | `20260524T062952Z-3090_two_track_pilot` | memory/task-image smoke |

## Brief Template

```yaml
run_id:
commit:
mode:
data_mode:
samples:
matrix_cells:
key_metrics:
  c0_visual_tokens:
  c4_visual_tokens:
  c4_visual_tokens_p95:
  visual_token_reduction:
  c4_normal_peak_mb:
  c4_normal_peak_mb_p95:
  c4_controlled_fallback_peak_mb_conditional_mean:
  c4_controlled_fallback_peak_mb_conditional_p95:
  c4_controlled_fallback_peak_mb_all_samples_mean:
  c4_controlled_fallback_peak_mb_all_samples_p95:
  c4_controlled_fallback_rate:
score_semantics:
  task_score_source:
  proxy_task_score_mean:
  actual_task_score_available_rate:
  scoring_method:
source_semantics:
  actual_image_execution:
  image_sources:
  roi_sources:
  roi_contains_target_evidence:
  real_measurement_fields:
  estimate_or_proxy_fields:
gates:
  completion:
  measurement:
  promotion:
claim_boundary:
  safe:
  not_yet:
notes:
  - raw artifacts are local-only under .local/runs/
  - interpret old Track B numbers as support evidence under Track A v2
```
