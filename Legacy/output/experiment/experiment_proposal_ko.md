# 실험 제안서

제목: VRAM 제약형 Foveated Adapter Policy의 최소 검증 프로토콜  
상태: v1, M4 작성 완료  
작성일: 2026-05-04

발표 사용 원칙:

```text
M5 발표 본문에서는 이 문서의 세부 프로토콜을 길게 설명하지 않는다.
본문에서는 "검증 방향"만 짧게 제시하고,
dataset split, baseline, ablation, logging schema는 Q&A 또는 후속 논의 카드로 사용한다.
```

## 1. 실험 목표

이 실험은 최고 정확도 모델을 찾는 실험이 아니다. 목표는 Budget-Conditioned Foveated Adapter Policy가 실제 배치 제약에서 어떤 비용을 줄이는지 분해해서 확인하는 것이다.

핵심 검증 대상:

- low-res global view와 ROI crop이 full high-resolution 입력 대비 visual token과 peak VRAM을 줄이는가?
- HydraLoRA shared-A 구조가 independent LoRA bank 대비 adapter resident memory를 줄이는가?
- Simula taxonomy tag가 runtime adapter routing의 supervision으로 쓸 만한가?
- 절약된 VRAM이 planner, world model, verifier, orchestration LLM의 co-residency 여유로 이어지는가?

1차 pilot은 "성능 우위 증명"보다 "측정 가능한 VRAM 절감 구조"를 확인하는 데 둔다.

## 2. 연구 질문

| ID | 질문 | 주요 측정값 |
| --- | --- | --- |
| RQ1 | full high-resolution 입력 대비 low-res global + ROI crop 구조가 visual token과 peak VRAM을 줄이는가? | visual token count, peak allocated VRAM, p95 latency |
| RQ2 | independent LoRA bank 대비 HydraLoRA shared-A 구조가 adapter resident memory를 줄이는가? | adapter resident memory, load/unload count, task score |
| RQ3 | Simula taxonomy tag가 adapter routing supervision으로 유효한가? | router top-k hit rate, wrong route rate, fallback success rate |
| RQ4 | 동일한 GPU budget에서 planner/world model/verifier co-residency를 더 잘 보장하는가? | orchestration reserve pass/fail, reserved VRAM, peak VRAM violation rate |

## 3. 데이터셋과 Split

1차 도메인은 후속 논의에서 확정한다. 후보는 PCB/circuit inspection, 설계도 기반 장치 점검, 또는 시각 기호가 많은 산업 도면이다. 중요한 조건은 "global context는 넓고, local evidence는 작고, domain skill이 ROI별로 달라질 수 있는" 데이터여야 한다는 점이다.

권장 split:

```text
synthetic_train:
  Simula taxonomy로 생성하거나 replay한 학습용 sample

real_holdout:
  synthetic 생성 과정과 완전히 분리한 실제 이미지 검증 set

ood_branch:
  학습 taxonomy에 없거나 조합이 다른 case

hard_negative:
  shortcut, pseudo marker, label leakage를 잡기 위한 반례 set

quarantine:
  critic 충돌, 낮은 confidence, 이상한 routing gain을 보인 sample
```

최소 annotation schema:

```text
sample_id
global_image
instruction
ROI boxes
evidence type
required_adapter_tags
target answer or target graph update
real/synthetic/OOD/hard-negative flag
failure label if applicable
```

## 4. 비교군

| ID | 비교군 | 목적 |
| --- | --- | --- |
| B0 | base VLM, low-res only | local evidence 없이 global view만 쓸 때의 하한선 |
| B1 | base VLM, full high-res | token/VRAM을 크게 쓰는 강한 기준선 |
| B2 | low-res global + K ROI crops, no LoRA | foveation 자체의 이득 분리 |
| B3 | ROI crops + monolithic LoRA | 단일 domain LoRA 기준선 |
| B4 | ROI crops + independent LoRA bank | adapter bank의 naive 기준선 |
| B5 | ROI crops + HydraLoRA shared-A bank | shared-A가 resident memory를 줄이는지 확인 |
| B6 | HydraLoRA + Simula taxonomy router | taxonomy supervision 효과 확인 |
| B7 | HydraLoRA + budget-conditioned top-k routing | 최종 제안 구조 |

1차 pilot에서는 B0, B1, B2, B4, B5, B7을 우선 돌리고, 시간이 부족하면 B3와 B6은 2차로 미룬다.

## 5. Ablation

최소 ablation:

- ROI count `K`: 1, 3, 5 등으로 조절한다.
- LoRA rank `r`: adapter 품질과 resident memory의 trade-off를 본다.
- expert count `N`: adapter bank가 커질수록 routing과 memory가 어떻게 변하는지 본다.
- top-k routing: 한 번에 몇 개의 adapter 후보를 올릴지 조절한다.
- taxonomy supervision on/off: Simula tag가 실제 routing에 도움이 되는지 확인한다.
- fallback on/off: ROI miss가 있을 때 회복 가능한지 본다.
- graph write on/off: graph memory가 다음 ROI 선택에 주는 영향을 분리한다.

## 6. Metrics

성능:

- task accuracy
- macro F1
- OCR accuracy, 해당 도메인에서 필요할 경우
- graph-edge F1
- conflict resolution rate
- OOD accuracy

효율:

- visual token count
- peak allocated VRAM
- average allocated VRAM
- reserved VRAM
- adapter resident memory
- KV cache estimate
- p50/p95 latency
- adapter load/unload count
- orchestration reserve pass/fail

라우팅:

- router accuracy
- top-k hit rate
- wrong route rate
- gate entropy
- expert utilization
- collapse rate
- abstention rate
- fallback success rate

## 7. Logging and Hardware

실험 로그에는 최소한 다음 항목을 남긴다.

```text
hardware:
  GPU name
  total VRAM
  driver/CUDA or runtime version

model:
  backbone name
  precision or quantization
  LoRA rank
  adapter count
  top-k

run:
  seed
  batch size
  input resolution
  ROI count
  split name

memory:
  peak allocated VRAM
  average allocated VRAM
  reserved VRAM
  adapter resident memory
  KV cache estimate

timing:
  p50 latency
  p95 latency
  adapter load/unload count
```

VRAM 측정은 가능하면 inference step별로 남긴다. 최소 단위는 "global pass", "ROI pass", "adapter load", "adapter evict", "graph write"다.

## 8. Success Criteria

1차 pilot 성공 기준:

- B1 full high-res 대비 B7의 peak allocated VRAM이 의미 있게 감소한다.
- B4 independent LoRA bank 대비 B5/B7의 adapter resident memory가 감소한다.
- B7의 task score가 B1 또는 B4와 큰 차이 없이 유지된다.
- orchestration reserve pass rate가 B7에서 개선된다.
- real_holdout에서 synthetic_train 대비 성능 붕괴가 크지 않다.
- hard_negative에서 taxonomy shortcut 또는 label leakage 징후가 발견되면 quarantine rule로 분리된다.

정량 기준은 도메인과 실험 자원이 확정된 뒤 수치화한다. 이 문서에서는 우선 측정해야 할 항목과 비교 구조를 고정한다.

## 9. Failure Analysis

| 실패 유형 | 관찰되는 증상 | 확인할 로그 |
| --- | --- | --- |
| ROI miss | 중요한 영역을 보지 못해 답이 틀림 | ROI recall, fallback trigger, second scout result |
| wrong adapter route | ROI는 맞지만 잘못된 LoRA를 선택함 | router top-k hit rate, adapter tag, wrong route label |
| adapter conflict | 여러 adapter가 서로 다른 증거를 냄 | expert utilization, conflict log, graph quarantine |
| graph false write | 낮은 confidence evidence가 graph에 commit됨 | calibration score, verifier result, rollback count |
| synthetic shortcut | synthetic에서는 높고 real_holdout에서 낮음 | split별 score, hard_negative score |
| latency spike | VRAM은 줄었지만 load/unload로 지연이 튐 | p95 latency, load/unload count, residency action |

## 10. 1차 Pilot 산출물

1차 pilot이 끝나면 다음 표를 만들 수 있어야 한다.

```text
baseline/model
task score
visual token count
peak allocated VRAM
adapter resident memory
p95 latency
orchestration reserve pass/fail
main failure type
```

이 표가 나오면 발표 자료에는 핵심 결과만 압축하고, 논문화 단계에서는 ablation과 failure analysis를 확장한다. M5 발표 단계에서는 이 표를 "후속 검증 계획"의 근거로만 사용한다.
