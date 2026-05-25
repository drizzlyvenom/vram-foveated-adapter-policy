# Claim Table

Status: proxy-tainted results quarantined

## Safe Now

| Claim | Evidence | Boundary |
|---|---|---|
| 현재 논문 중심축은 Track A v2, 즉 Simula-compiled taxonomy LoRA bank다. | `track_a_v2_reframe_ko.md`, 최신 README/overview 갱신 | planning/reframe claim |
| Gemma 4 26B는 teacher/annotator/curriculum generator로 둘 수 있다. | Track A v2 reframe | valid JSON teacher output 없이는 검증 근거 아님 |
| Track A v2 schema와 runner scaffold가 존재한다. | `schemas/track_a_v2/`, `src/vfa_policy/track_a/`, Track A v2 scripts | scaffold claim only |
| proxy-tainted 검증 결과는 폐기했다. | `trashbin/proxy_result_quarantine_2026-05-25/` | 삭제 전 확인용 격리 |
| 현재 active result brief는 없다. | `docs/20_results/README.md` | no-proxy 재검증 전까지 결과 claim 없음 |

## Safe After New Runs

| Claim | Required Evidence |
|---|---|
| single LoRA가 adapter-sensitive task를 학습한다. | base vs correct LoRA train/holdout 비교 |
| taxonomy LoRA가 실제 adapter-specific utility를 가진다. | correct adapter가 wrong/random adapter보다 heldout에서 margin 확보 |
| router가 adapter를 고를 수 있다. | routed score가 oracle adapter score에 가까우며 top1 hit가 random baseline 초과 |
| Simula compiler가 유효하다. | failure trace -> curriculum -> AdapterCard -> certification까지 재현 가능한 run |
| controlled result가 넓은 외부 benchmark에서도 유지된다. | 현재 n=32보다 큰 external 또는 human-evaluated subset |
| trained LoRA accuracy gain을 주장할 수 있다. | 명확한 baseline 대비 held-out/external improvement |
| multi-adapter routing utility를 주장할 수 있다. | adapter-specific task에서 wrong-adapter damage와 correct-adapter recovery가 관측됨 |
| Gemma teacher annotation을 실제 teacher evidence로 쓸 수 있다. | llama.cpp 또는 대체 backend에서 valid JSON teacher output 확보 |

## Not Yet

| Unsafe Claim | Why Not |
|---|---|
| Track B가 현재 메인 논문 기여다. | 새 방향성에서는 Track B를 visual evidence cost control 보조 모듈로 제한 |
| Gemma teacher label이 최종 ground truth다. | teacher annotation은 candidate supervision이며 certification은 별도 heldout gate로 닫아야 함 |
| Simula compiler가 adapter utility를 이미 증명했다. | compiler path는 구현됐지만 Gemma는 fallback이고 certification 일부가 proxy |
| 일반 benchmark에서도 score retention이 유지된다. | 현재는 외부 n=32 tiny diagnostic뿐이라 broad benchmark가 아님 |
| trained LoRA가 baseline보다 정확도를 향상한다. | 외부 n=32 baseline 비교에서 gain이 관측되지 않음 |
| tiny trained LoRA가 일반화된다. | 현재는 controlled tiny set holdout 평가 |
| actual OCR detector ROI가 안정적으로 oracle을 대체한다. | 외부 n=32 diagnostic은 있으나 broad benchmark/generalization은 아직 아님 |
| `layout_proxy_box`가 실제 OCR detector다. | controlled manifest box |
| 여러 다른 full specialist VLM의 joint residency를 실측했다. | 현재는 estimate 또는 sequential proxy |
| multi-adapter routing이 정확도를 올린다. | actual bank smoke에서 correct/wrong adapter score 차이가 0.0 |
| Qwen2-VL-2B가 최종 low-end backbone이다. | 1개 후보의 tiny n=32 sweep만 있음 |
| production p95/p99 latency가 검증됐다. | 단일-user local pilot |

## Preferred Wording

```text
On a controlled tiny scored diagnostic set, ROI source quality dominates task-score retention under the same foveated visual-token budget.
```

```text
The current layout proxy is a controlled box source, not an external OCR detector. We reserve ocr_detector_box for boxes produced by an optional OCR detector pipeline.
```

```text
The current negative LoRA results are evidence that the previous tasks were not adapter-sensitive enough; they do not falsify the Track A v2 adapter-bank direction.
```
