# Stage 1 데이터셋 후보

Status: Stage 1 준비 메모  
Purpose: RTX 3090에서 foveation-only validation을 시작하기 위한 작은 공개 데이터셋 후보를 고른다.

## 1. 선택 기준

Stage 1은 LoRA나 LeWM을 붙이기 전 단계다. 목표는 최고 정확도가 아니라 다음 항목을 실제 VLM profiler에서 분리 측정하는 것이다.

```text
low-res only vs full high-res vs low-res + ROI crop
visual token count
peak VRAM
latency
OOM boundary
ROI miss / crop distraction
```

따라서 데이터셋은 아래 조건을 우선한다.

- 이미지 안의 작은 국소 증거를 읽어야 한다.
- 질문과 정답이 있다.
- 이미지 해상도가 어느 정도 커서 full high-res 비용이 드러난다.
- 가능하면 ROI 힌트나 OCR token, UI element bound가 있다.
- 처음에는 50-100개 샘플만 뽑아도 의미가 있다.

## 2. 우선 후보

| Priority | Dataset | HF link | Stage 1 role | Notes |
|---|---|---|---|---|
| 1 | DocVQA validation | https://hf.co/datasets/lmms-lab/DocVQA | 문서/도표 기반 local evidence | validation split에 answers가 있다. 문서와 도표가 섞여 있어 설계도/매뉴얼 프레이밍과 잘 맞는다. |
| 1 | TextVQA validation | https://hf.co/datasets/lmms-lab/textvqa | OCR/local text evidence | OCR tokens가 있어 text-guided ROI heuristic을 만들기 쉽다. |
| 1 | RICO-ScreenQA test | https://hf.co/datasets/rootsautomation/RICO-ScreenQA | oracle ROI sanity check | `ground_truth.ui_elements.bounds`가 있어 ROI upper bound 실험에 좋다. 물리 장치는 아니지만 local evidence 검증에는 매우 유용하다. |
| 2 | ChartQA test | https://hf.co/datasets/lmms-lab/ChartQA | chart/axis/legend reading | 차트 숫자와 축 라벨 읽기에 좋다. ROI annotation은 별도 heuristic이 필요하다. |
| 2 | InfographicVQA mini | https://hf.co/datasets/kenza-ily/infographicvqa_disco | infographic OCR stress test | 작은 mini subset이지만 split/config 접근은 추가 확인이 필요하다. |

## 3. 첫 pilot 조합

처음부터 여러 데이터셋을 크게 받지 않는다. 아래처럼 작은 smoke set만 구성한다.

```yaml
stage1_smoke_set:
  docvqa_validation: 30
  textvqa_validation: 30
  rico_screenqa_test: 20
  chartqa_test: 20
```

이 조합이면 문서, 자연 이미지 OCR, UI bound, 차트까지 넓게 커버하면서도 RTX 3090에서 빠르게 profiler를 돌릴 수 있다.

## 4. ROI 전략

Stage 1에서 사용할 ROI 전략은 모델 구조를 늘리지 않는 간단한 방식으로 제한한다.

```text
S1-A: low_res_only
S1-B: full_high_res
S1-C: grid_roi
S1-D: ocr_or_text_hint_roi
S1-E: oracle_roi_if_available
```

RICO-ScreenQA는 `ground_truth.ui_elements.bounds`로 oracle ROI를 만들 수 있다. TextVQA는 `ocr_tokens`를 사용해 text-guided heuristic을 만들 수 있다. DocVQA와 ChartQA는 우선 grid/center/edge heuristic으로 시작하고, 필요하면 일부 샘플만 manual oracle ROI를 추가한다.

## 5. Claim boundary

Stage 1에서 말할 수 있는 것:

```text
- 실제 VLM profiler에서 full high-res 대비 ROI path의 token/VRAM/latency 방향성을 확인했다.
- ROI가 맞을 때 low-res failure를 회복할 수 있는지 확인했다.
- ROI가 틀릴 때 crop distraction이나 evidence miss가 얼마나 생기는지 기록했다.
```

Stage 1에서 아직 말하면 안 되는 것:

```text
- LoRA routing이 정확하다는 주장
- adapter residency 정책이 실제로 최적인지에 대한 주장
- LeWM/JEPA feature가 routing을 개선했다는 주장
- 전체 architecture end-to-end 우위 주장
```
