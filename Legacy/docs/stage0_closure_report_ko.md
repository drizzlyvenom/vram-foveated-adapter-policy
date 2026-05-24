# Stage 0 Closure Report

Status: closed  
Date: 2026-05-21  
Scope: RTX 3090 CostSim replay and logging-contract validation

## 1. 목적

Stage 0은 새 모델 실험이 아니라, 기존 RTX 3090 cost simulation 결과를 새 검증 로그 계약으로 옮기는 단계다.

검증 대상:

```text
existing 3090 CostSim CSV
-> RouteTrace JSONL
-> summary.csv
-> directionality checks
```

이 단계의 claim은 cost-model feasibility와 logging reproducibility에 한정한다. 실제 VLM profiler 측정은 Stage 1에서 시작한다.

## 2. 실행 명령

```powershell
python scripts\run_pilot.py --config configs\pilot_minimal.yaml
python scripts\summarize_run.py runs\<run_id>\route_traces.jsonl
```

확인된 실행 예:

```text
run_id: 20260521T071035Z-stage0_3090_costsim_replay
RouteTrace rows: 4032
checks_passed: true
```

`runs/`는 로컬 검증 산출물이므로 git에는 포함하지 않는다.

## 3. 요약 결과

| Stage 0 ID | Source | n | visual tokens mean | peak VRAM mean MB | adapter resident mean MB | reserve pass rate |
|---|---:|---:|---:|---:|---:|---:|
| S0-A | B0 | 18 | 800.0 | 12662.67 | 0.0 | 1.00 |
| S0-B | B1 | 18 | 7346.0 | 16721.19 | 0.0 | 0.72 |
| S0-C | B2 | 108 | 3200.0 | 14150.67 | 0.0 | 0.91 |
| S0-D | B4-lite | 1296 | 3200.0 | 16946.67 | 2700.0 | 0.69 |
| S0-E | B5-lite | 1296 | 3200.0 | 15141.67 | 895.0 | 0.85 |
| S0-F | B7-lite | 1296 | 2993.78 | 14451.19 | 310.42 | 1.00 |

## 4. 통과한 directionality checks

```text
S0-B full high-res visual tokens > S0-A low-res
S0-B full high-res peak VRAM > S0-A low-res
S0-C foveated ROI visual tokens < S0-B full high-res
S0-F budget policy adapter residency < S0-D independent adapter bank
S0-F budget policy reserve failures <= S0-D independent adapter bank
```

세부 수치:

```text
S0-B tokens 7346.0 vs S0-A tokens 800.0
S0-B peak 16721.19 MB vs S0-A peak 12662.67 MB
S0-C tokens 3200.0 vs S0-B tokens 7346.0
S0-F adapter resident 310.42 MB vs S0-D 2700.0 MB
S0-F reserve failures 0 vs S0-D 396
```

## 5. Stage 0 claim boundary

말할 수 있는 것:

```text
- 기존 3090 cost simulation 결과를 새 logging contract로 재현 가능하게 옮겼다.
- full high-res, foveated ROI, adapter bank, budget policy의 비용 방향성이 기존 3090 prior와 일치한다.
- B7-lite budget policy는 cost model상 resident adapter pressure와 reserve failure를 크게 줄인다.
```

아직 말하면 안 되는 것:

```text
- 실제 VLM profiler에서 같은 peak VRAM이 측정되었다.
- 실제 추론 정확도가 개선되었다.
- LoRA routing이 task-level로 검증되었다.
- LeWM/JEPA feature가 routing을 개선했다.
```

## 6. 다음 단계

Stage 1에서는 RTX 3090에서 실제 VLM profiler를 사용해 foveation-only validation을 시작한다.

첫 목표:

```text
low-res only
full high-res
low-res + ROI crop
```

측정:

```text
visual token count
peak allocated VRAM
p50/p95/p99 latency
OOM boundary
ROI miss / crop distraction
```
