# Result Briefs

이 폴더는 `.local/runs/` 원본 산출물을 그대로 커밋하지 않고, 연구 판단과 외부 검토에 필요한 얇은 결과 브리핑만 남기는 공간이다. Git에 남는 결과 브리프와 로컬 전용 raw artifact의 관계는 [local artifact boundary](../00_overview/local_artifact_boundary_ko.md)에 정리한다.

2026-05-25 정리 기준을 바꿨다. 한 번이라도 proxy, mixed proxy, estimate, deterministic fallback을 사용한 검증 결과는 결과 근거에서 폐기하고 `trashbin/proxy_result_quarantine_2026-05-25/`로 옮긴다.

```yaml
current_interpretation:
  proxy_used_validation_results: "discarded_to_trashbin"
  retained_result_briefs: []
  claim_boundary: "no committed validation result brief is active after quarantine"
  next_use: "strict no-proxy validation only"
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
  - proxy-tainted validation results
```

원본 산출물은 로컬 `.local/runs/<run_id>/` 아래에 둔다. 단, source semantics에 proxy/estimate/fallback이 섞인 검증 결과는 Git 근거와 로컬 active run 목록에서 제외하고 trashbin으로 이동한다.

## Index

| Date | Brief | Run | Status |
|---|---|---|---|
| n/a | n/a | n/a | all previous validation result briefs quarantined |

## Quarantined Proxy Results

```yaml
trashbin_path: "trashbin/proxy_result_quarantine_2026-05-25/"
reason: "proxy/mixed/estimate/fallback evidence was used at least once"
scope:
  - "committed result briefs with proxy-tainted validation evidence"
  - "mixed-proxy Track A v2 AdapterCards"
  - "local raw 3090/proxy run directories"
  - "Track A v2 base audit, certification, router eval derived from proxy"
  - "remaining historical local run results from the same validation cycle"
```

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
  actual_task_score_available_rate:
  scoring_method:
source_semantics:
  actual_image_execution:
  image_sources:
  roi_sources:
  roi_contains_target_evidence:
  real_measurement_fields:
gates:
  completion:
  measurement:
  promotion:
claim_boundary:
  safe:
  not_yet:
notes:
  - raw artifacts are local-only under .local/runs/
  - reject the result if any proxy, mixed proxy, estimate, or fallback field affects validation evidence
```
