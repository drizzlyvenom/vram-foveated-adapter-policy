# Local Artifact Boundary

이 문서는 이 저장소에서 **Git에 커밋되는 공개 산출물**과 **로컬 작업 디렉터리에만 남기는 실행 산출물**을 구분하기 위한 기준 문서다. 외부 검토나 리서치 핸드오프에서 `.local/runs/`, `.local/data/`, `.local/hf_cache/`가 Git에 없다는 이유로 재현성 문제가 있다고 오해하지 않도록, 어떤 파일이 왜 커밋되지 않는지 명시한다.

## 1. 커밋되는 산출물

Git에 커밋되는 파일은 다른 사람이 저장소를 clone했을 때 검증 구조를 이해하고 같은 실험을 다시 실행할 수 있게 하는 최소 작업면이다.

```yaml
committed:
  docs:
    role: "protocol, claim boundary, result brief, latest status"
    examples:
      - "docs/00_overview/3090_two_track_validation_guideline_ko.md"
      - "docs/10_protocols/3090_execution_ladder_ko.md"
      - "docs/10_protocols/3090_metrics_contract_ko.md"
      - "docs/00_overview/latest_run_status_ko.md"
      - "docs/20_results/"
  configs:
    role: "active validation config and adapter cards"
  schemas:
    role: "expected trace/result shape"
  scripts:
    role: "manifest preparation and validation runner"
  src:
    role: "core accounting, foveation, consolidation, logging modules"
  Legacy:
    role: "historical reference only, not active validation path"
```

커밋되는 result brief는 raw run artifact를 대체하지 않는다. 대신 다음 정보를 얇게 남긴다.

```yaml
result_brief_contains:
  - run_id
  - reproduce_command
  - key_metrics
  - gate_status
  - source_semantics
  - safe_claims
  - not_yet_claims
```

## 2. 로컬 전용 산출물

아래 파일과 폴더는 실행 환경, 다운로드 데이터, 모델 캐시, 원본 로그 성격이 강해서 기본적으로 커밋하지 않는다.

```yaml
local_only:
  .local/runs/:
    contains:
      - "combined_validation_result.json"
      - "summary.csv"
      - "route_traces.jsonl"
      - "result_summary_ko.md"
      - "short_paper_ko.md"
      - "probe images"
    reason: "실행마다 커지고, raw trace와 이미지가 포함되며, Git diff 검토에 적합하지 않음"

  .local/data/:
    contains:
      - "downloaded image/task samples"
      - "real_task_smoke/manifest.jsonl"
    reason: "재현 명령으로 다시 생성 가능한 입력 데이터이며, 외부 데이터셋/이미지 라이선스와 용량 이슈가 있음"

  .local/hf_cache/:
    contains:
      - "local Hugging Face model snapshots"
    reason: "대용량 모델 캐시이며, GitHub에 올릴 대상이 아님"

  .venv/:
    reason: "개인 로컬 Python 환경"

  .local/workbench/:
    reason: "Codex handoff notes, 개인 작업 메모, 임시 지시문"

  .local/trashbin/:
    reason: "검토 전 임시 보관소"
```

따라서 `docs/20_results/*.md`의 run id가 `.local/runs/<run_id>/`를 가리키더라도, 그 원본 폴더가 GitHub에 없다는 것은 의도된 상태다.

## 3. 재현 방식

공개 저장소에서 재현할 때는 커밋된 config, script, schema를 사용하고, 필요한 로컬 입력은 명령으로 다시 만든다.

```powershell
python scripts\prepare_real_task_manifest.py --source picsum_highres --max-samples 4
.venv\Scripts\python.exe scripts\run_3090_two_track_validation.py --config configs\3090\two_track_pilot.yaml --real-run --data-mode real_task_manifest --manifest .local\data\real_task_smoke\manifest.jsonl --max-samples 2 --max-new-tokens 4
```

이 명령은 다음을 다시 생성한다.

```yaml
regenerated_local_artifacts:
  - ".local/data/real_task_smoke/manifest.jsonl"
  - ".local/data/real_task_smoke/images/"
  - ".local/runs/<new_run_id>/combined_validation_result.json"
  - ".local/runs/<new_run_id>/summary.csv"
  - ".local/runs/<new_run_id>/route_traces.jsonl"
```

단, 정확히 같은 CUDA peak 수치는 드라이버, PyTorch, 캐시 상태, GPU 부하에 따라 약간 달라질 수 있다. 재현성 판단은 동일한 matrix cell, source semantics, gate status, metric directionality가 유지되는지를 함께 본다.

## 4. Claim Boundary

현재 저장소의 공개 claim은 다음 수준에 머문다.

```yaml
safe_to_claim:
  - "RTX 3090에서 real CUDA memory-accounting runner가 동작한다."
  - "Qwen3-VL-4B local snapshot을 공유 backbone으로 로드하고 base-after-load memory를 기록한다."
  - "real_task_manifest 이미지가 full/low-res/ROI evidence path로 들어가며, 같은 C-matrix schema로 token/peak를 기록한다."
  - "result brief는 raw runs를 커밋하지 않고 핵심 수치와 claim boundary만 보존한다."

not_claimed_yet:
  - "trained LoRA가 실제 task accuracy를 향상한다."
  - "center_crop ROI가 task-relevant ROI를 안정적으로 찾는다."
  - "multi-specialist baseline을 실측으로 이겼다."
  - "production p95/p99 latency가 검증됐다."
```

## 5. 로컬 정리 원칙

로컬 작업 디렉터리가 복잡해질 때는 다음 순서로 정리한다.

```yaml
cleanup_policy:
  keep_at_root:
    - "configs/"
    - "docs/"
    - "schemas/"
    - "scripts/"
    - "src/"
    - ".local/data/"
    - ".local/runs/"
    - ".local/hf_cache/"
  move_to_local_workbench:
    - "Codex goal/readme handoff notes"
    - "private planning prompts"
  move_to_trashbin_first:
    - "empty scratch folders"
    - "ambiguous temporary outputs"
  move_to_Legacy:
    - "historical docs/configs/scripts that may still be useful as reference"
```

`.local/data/`, `.local/runs/`, `.local/hf_cache/`는 보기에는 무겁지만 현재 검증 명령이 직접 참조하는 활성 로컬 작업면이다. 루트에는 공개 작업면을 남기고, 로컬 실행 산출물은 `.local/` 아래에 모은다.
