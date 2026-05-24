# Result Briefs

이 폴더는 `.local/runs/` 원본 산출물을 그대로 커밋하지 않고, 연구 판단과 외부 검토에 필요한 얇은 결과 브리핑만 남기는 공간이다. Git에 남는 결과 브리프와 로컬 전용 raw artifact의 관계는 [local artifact boundary](../00_overview/local_artifact_boundary_ko.md)에 정리한다.

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
  visual_token_reduction:
  c4_normal_peak_mb:
  c4_controlled_fallback_peak_mb_conditional_mean:
  c4_controlled_fallback_peak_mb_all_samples_mean:
  c4_controlled_fallback_rate:
score_semantics:
  task_score_source:
  proxy_task_score_mean:
  actual_task_score_available_rate:
source_semantics:
  actual_image_execution:
  image_sources:
  roi_sources:
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
```
