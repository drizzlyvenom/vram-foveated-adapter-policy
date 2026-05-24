from __future__ import annotations

import argparse
import gc
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.logging_utils import ensure_run_dir, write_json
from vfa_policy.paths import DEFAULT_TWO_TRACK_CONFIG, resolve_repo_path


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _mb(value_bytes: int | float) -> float:
    return round(float(value_bytes) / (1024.0 * 1024.0), 3)


def _sync(torch_module: Any) -> None:
    if torch_module.cuda.is_available():
        torch_module.cuda.synchronize()


def _load_model(torch_module: Any, model_path: Path, dtype_name: str) -> Any:
    from transformers import AutoModelForImageTextToText

    dtype = torch_module.float16 if dtype_name.lower() in {"float16", "fp16", "half"} else torch_module.bfloat16
    kwargs = {
        "trust_remote_code": True,
        "local_files_only": True,
        "device_map": {"": "cuda:0"},
        "dtype": dtype,
        "attn_implementation": "sdpa",
    }
    try:
        return AutoModelForImageTextToText.from_pretrained(model_path, **kwargs)
    except TypeError:
        kwargs.pop("dtype", None)
        kwargs["torch_dtype"] = dtype
        return AutoModelForImageTextToText.from_pretrained(model_path, **kwargs)


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_TWO_TRACK_CONFIG)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output-dir", default=".local/runs")
    args = parser.parse_args()

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; specialist swap smoke requires RTX 3090 CUDA.")

    config_path = resolve_repo_path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model_path = resolve_repo_path(config.get("model", {}).get("local_snapshot_path", ""))
    dtype_name = str(config.get("model", {}).get("dtype", "float16"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-specialist_swap_smoke")
    run_dir = ensure_run_dir(run_id, args.output_dir)

    trials = []
    for trial_index in range(int(args.repeats)):
        torch.cuda.empty_cache()
        _sync(torch)
        before_allocated = _mb(torch.cuda.memory_allocated())
        before_reserved = _mb(torch.cuda.memory_reserved())

        started = time.perf_counter()
        model = _load_model(torch, model_path, dtype_name)
        model.eval()
        _sync(torch)
        load_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        after_load_allocated = _mb(torch.cuda.memory_allocated())
        after_load_reserved = _mb(torch.cuda.memory_reserved())

        started = time.perf_counter()
        del model
        gc.collect()
        torch.cuda.empty_cache()
        _sync(torch)
        unload_empty_cache_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        after_unload_allocated = _mb(torch.cuda.memory_allocated())
        after_unload_reserved = _mb(torch.cuda.memory_reserved())

        trials.append(
            {
                "trial_index": trial_index,
                "before_load_allocated_mb": before_allocated,
                "before_load_reserved_mb": before_reserved,
                "after_load_allocated_mb": after_load_allocated,
                "after_load_reserved_mb": after_load_reserved,
                "model_load_latency_ms": load_latency_ms,
                "unload_empty_cache_latency_ms": unload_empty_cache_latency_ms,
                "after_unload_allocated_mb": after_unload_allocated,
                "after_unload_reserved_mb": after_unload_reserved,
                "residual_allocated_mb": after_unload_allocated,
                "residual_reserved_mb": after_unload_reserved,
            }
        )

    result = {
        "schema_version": "3090.specialist_swap_smoke.v0.1",
        "run_id": run_id,
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "model_path": str(model_path.relative_to(REPO_ROOT)) if model_path.is_relative_to(REPO_ROOT) else str(model_path),
        "hardware": {
            "gpu": torch.cuda.get_device_name(0),
        },
        "repeats": int(args.repeats),
        "measurement_mode": "real_cuda_model_load_unload",
        "trials": trials,
        "summary": {
            "model_load_latency_ms_mean": _mean([float(row["model_load_latency_ms"]) for row in trials]),
            "unload_empty_cache_latency_ms_mean": _mean(
                [float(row["unload_empty_cache_latency_ms"]) for row in trials]
            ),
            "after_load_allocated_mb_mean": _mean([float(row["after_load_allocated_mb"]) for row in trials]),
            "after_unload_allocated_mb_mean": _mean([float(row["after_unload_allocated_mb"]) for row in trials]),
            "after_unload_reserved_mb_mean": _mean([float(row["after_unload_reserved_mb"]) for row in trials]),
        },
        "claim_boundary": {
            "measured_sequential_swap_available": True,
            "measured_joint_residency_available": False,
            "uses_same_model_as_specialist_proxy": True,
            "final_performance_claim": False,
        },
    }
    write_json(run_dir / "specialist_swap_result.json", result)
    (run_dir / "result_summary_ko.md").write_text(
        "\n".join(
            [
                "# Specialist Swap Smoke",
                "",
                f"- run_id: `{run_id}`",
                f"- repeats: `{args.repeats}`",
                f"- model_load_latency_ms_mean: `{result['summary']['model_load_latency_ms_mean']}`",
                f"- unload_empty_cache_latency_ms_mean: `{result['summary']['unload_empty_cache_latency_ms_mean']}`",
                f"- after_unload_reserved_mb_mean: `{result['summary']['after_unload_reserved_mb_mean']}`",
                "",
                "이 결과는 같은 Qwen3-VL-4B snapshot을 specialist proxy로 반복 load/unload한 sequential swap 비용이다.",
                "여러 specialist를 동시에 resident로 둔 joint measurement는 아니다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_dir": str(run_dir), "repeats": args.repeats, **result["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
