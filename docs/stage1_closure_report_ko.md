# Stage 1 Closure Report

Status: closed as smoke validation
Date: 2026-05-21
Scope: RTX 3090 foveation-only profiler

## 1. 목적

Stage 1은 LoRA, LeWM, JEPA를 붙이기 전 단계에서 foveation-only 경로가 실제 GPU profiler에서도 비용을 줄이는지 확인한다.

이번 실행은 최신 VLM 전체 추론 평가가 아니라, 현재 RTX 3090 환경에서 안정적으로 실행 가능한 patch-token Transformer profiler를 사용한 smoke validation이다.

검증 대상:

```text
low-res only
random ROI
heuristic ROI
oracle ROI if bounds exist
full high-res
```

이 단계의 claim은 foveated visual token path의 비용 방향성과 ROI-bound sanity check에 한정한다. VLM answer accuracy와 LoRA routing 성능은 아직 측정하지 않는다.

## 2. 데이터셋

로컬 manifest:

```text
data/stage1_smoke/manifest.jsonl
```

샘플 구성:

| Dataset | Split | Samples | Role |
|---|---|---:|---|
| lmms-lab/DocVQA | validation | 5 | document/chart local evidence |
| lmms-lab/textvqa | validation | 5 | OCR/local text evidence |
| rootsautomation/RICO-ScreenQA | test | 5 | oracle ROI bound sanity check |
| lmms-lab/ChartQA | test | 5 | chart/axis/legend reading |

다운로드된 이미지와 manifest는 로컬 검증 산출물이므로 git에는 포함하지 않는다.

## 3. 실행 환경

확인된 실행:

```text
run_id: 20260521T072841Z-stage1_foveation_smoke
GPU: NVIDIA GeForce RTX 3090
VRAM: 24575 MB
Torch: 1.13.1+cu117
Profiler backbone: patch_transformer_smoke
Precision: float16
Patch size: 16
Embed dim: 192
Depth: 2
Heads: 4
RouteTrace rows: 85
checks_passed: true
```

실행 명령:

```powershell
python scripts\prepare_stage1_dataset.py --config configs\stage1_foveation_smoke.yaml
python scripts\run_stage1_foveation.py --config configs\stage1_foveation_smoke.yaml
```

## 4. 결과 요약

Aggregate summary:

| Baseline | Samples | Visual tokens mean | Peak VRAM mean MB | Peak VRAM p95 MB | Latency p50 ms | Latency p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| S1-A low_res_only | 20 | 441.0 | 4.68 | 4.68 | 2.04 | 2.74 |
| S1-B random_roi | 20 | 882.0 | 10.91 | 10.91 | 2.23 | 3.25 |
| S1-C heuristic_roi | 20 | 882.0 | 10.91 | 10.91 | 2.43 | 5.17 |
| S1-D oracle_roi_if_available | 5 | 882.0 | 10.91 | 10.91 | 2.20 | 2.30 |
| S1-E full_high_res | 20 | 3123.25 | 99.37 | 211.52 | 6.77 | 10.87 |

Key deltas:

```text
S1-C heuristic ROI vs S1-E full high-res
visual token reduction: 71.76%
peak VRAM reduction: 89.02%
p95 latency reduction: 52.48%
```

## 5. 통과한 checks

```text
S1-C visual tokens 882.0 < S1-E visual tokens 3123.25
S1-C peak VRAM 10.91 MB < S1-E peak VRAM 99.37 MB
S1-E peak VRAM 99.37 MB > S1-A peak VRAM 4.68 MB
S1-C bound-subset ROI recall 1.0 >= S1-B random ROI recall 0.4
S1-D oracle ROI bound-subset recall 1.0
S1-B random crop distraction measured with bound-subset recall 0.4
```

## 6. 해석

이번 smoke run은 Stage 1 pass gate의 비용 측면을 통과한다.

말할 수 있는 것:

```text
- 실제 RTX 3090 profiler에서 full high-res path가 low/ROI path보다 더 많은 token, VRAM, latency를 요구했다.
- low-res + ROI path는 full high-res 대비 평균 visual token과 peak VRAM을 크게 줄였다.
- bounds가 있는 RICO subset에서 evidence-aware ROI는 random crop보다 높은 ROI recall을 보였다.
- wrong crop distraction은 random ROI recall로 측정되었고, 무시되지 않았다.
```

아직 말하면 안 되는 것:

```text
- 실제 VLM answer accuracy가 개선되었다.
- DocVQA/TextVQA/ChartQA에서 자동 ROI가 정답 근거를 항상 찾는다.
- LoRA routing이나 adapter residency가 Stage 1에서 검증되었다.
- 이 smoke profiler의 절대 VRAM MB가 큰 VLM의 절대 VRAM 사용량을 대표한다.
```

## 7. 다음 단계

Stage 2로 넘어가기 전에 선택 가능한 보강:

```text
1. Stage 1 sample 수를 늘려 p95/p99를 안정화한다.
2. TextVQA/DocVQA에 OCR box 또는 manual oracle ROI를 일부 추가한다.
3. Qwen3-VL, InternVL, LLaVA 계열 중 3090에서 안정적으로 도는 VLM을 별도 environment에서 붙여 answer accuracy를 추가 측정한다.
```

현재 기준으로는 Stage 1 smoke validation을 닫고 Stage 2 LoRA isolation 준비로 넘어갈 수 있다.
