# Stage 1+ Local Environment

Status: setup note
Date: 2026-05-24
Scope: isolated `.venv` for RTX 3090 Stage 1+ experiments

## 1. 목적

Stage 1 smoke validation은 기존 전역 Python 환경에서도 재현된다. 그러나 Stage 1+에서 실제 VLM answer smoke를 시도하려면 최신 `torch`, `transformers`, `qwen-vl-utils` 계열이 필요하므로 프로젝트 내부 `.venv`로 격리한다.

## 2. 기본 방침

```text
.venv/는 git에 포함하지 않는다.
hf_cache/는 git에 포함하지 않는다.
requirements.txt는 Stage 0/1 lightweight 재현용으로 유지한다.
requirements-stage1plus.txt는 optional VLM 실험용으로 분리한다.
```

## 3. 설치 명령

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
.\.venv\Scripts\python -m pip install -r requirements-stage1plus.txt
```

확인된 설치:

```text
torch==2.12.0+cu126
torchvision==0.27.0+cu126
transformers==5.9.0
accelerate==1.13.0
datasets==4.8.5
qwen-vl-utils==0.0.14
```

## 4. Stage 1+ 기준 모델

```text
Qwen/Qwen3-VL-4B-Instruct
```

이 모델은 4B급 image-text-to-text 모델이며, Qwen3-VL 계열을 기준으로 Stage 1+ answer smoke와 이후 Stage 2-lite/3-lite 준비를 맞추기 위한 기본 후보로 둔다.

다운로드 위치:

```text
hf_cache/hub/models--Qwen--Qwen3-VL-4B-Instruct/
```

확인된 기준:

```text
model class: AutoModelForImageTextToText
parameters: about 4.44B
architecture: qwen3_vl
snapshot: ebb281ec70b05090aa6165b016eac8ec08e71b17
```

## 5. Smoke check

```powershell
$env:HF_HOME = (Resolve-Path .).Path + "\hf_cache"
.\.venv\Scripts\python scripts\check_stage1plus_env.py --config configs\stage1plus_vlm_smoke.yaml
```

확인된 결과:

```text
model: Qwen/Qwen3-VL-4B-Instruct
GPU: NVIDIA GeForce RTX 3090
run_id: 20260524T022243Z-stage1plus_vlm_smoke
load: 4.054 s
single image generation: 1.776 s
peak VRAM: 10255.845 MB
answer: "5:02"
```

이 결과는 environment smoke이며 benchmark 결과가 아니다.

## 6. 정리된 이전 캐시

초기 smoke에 사용한 `Qwen/Qwen2.5-VL-3B-Instruct` 캐시는 기준 모델에서 제외했으므로 다음 위치로 이동했다.

```text
trashbin/hf_cache_removed_2026-05-24/models--Qwen--Qwen2.5-VL-3B-Instruct/
```

## 7. 주의

Stage 1+의 첫 목표는 강한 benchmark score가 아니라 다음 항목을 확인하는 것이다.

```text
low-res answer smoke
ROI-crop answer smoke
full-res answer smoke
VRAM / latency / failure logging
```

모델 다운로드 파일과 Hugging Face cache는 로컬 검증 산출물이며 커밋하지 않는다.
