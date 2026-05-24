from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _resolve_under_repo(path_text: str) -> Path:
    path = (REPO_ROOT / path_text).resolve()
    if not path.is_relative_to(REPO_ROOT):
        raise ValueError(f"Refusing path outside repository: {path_text}")
    return path


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


def _dtype(name: str) -> torch.dtype:
    if name == "float16":
        return torch.float16
    if name == "bfloat16":
        return torch.bfloat16
    return torch.float32


def _ensure_run_dir(name: str, output_dir: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = _resolve_under_repo(output_dir) / f"{stamp}-{name}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage1plus_vlm_smoke.yaml")
    args = parser.parse_args()

    config_path = _resolve_under_repo(args.config)
    config: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    hf_home = _resolve_under_repo(config["environment"]["hf_home"])
    os.environ["HF_HOME"] = str(hf_home)
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from qwen_vl_utils import process_vision_info
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if config["environment"].get("device", "cuda") == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available.")

    model_id = config["model"]["model_id"]
    snapshot_text = config["model"].get("local_snapshot_path")
    snapshot = _resolve_under_repo(snapshot_text) if snapshot_text else None
    model_source: str | Path = snapshot if snapshot and snapshot.exists() else model_id
    local_files_only = bool(snapshot and snapshot.exists())
    dtype = _dtype(config["environment"].get("dtype", "float16"))
    image_path = _resolve_under_repo(config["sample"]["image_path"])
    prompt = config["sample"]["prompt"]

    run_dir = _ensure_run_dir(config["run"]["name"], config["run"].get("output_dir", "runs"))

    load_start = time.time()
    processor = AutoProcessor.from_pretrained(model_source, local_files_only=local_files_only)
    model = AutoModelForImageTextToText.from_pretrained(
        model_source,
        dtype=dtype,
        device_map=config["environment"].get("device", "cuda"),
        local_files_only=local_files_only,
    )
    model.eval()
    load_s = time.time() - load_start

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": str(image_path)},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt")
    inputs = inputs.to(config["environment"].get("device", "cuda"))

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    infer_start = time.time()
    with torch.inference_mode():
        generated_ids = model.generate(**inputs, max_new_tokens=int(config["model"].get("max_new_tokens", 16)))
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    latency_s = time.time() - infer_start

    trimmed = [out[len(inp) :] for inp, out in zip(inputs.input_ids, generated_ids)]
    answer = processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
    peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else None

    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "model_id": model_id,
        "image_path": str(image_path.relative_to(REPO_ROOT)),
        "prompt": prompt,
        "answer": answer,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_runtime": torch.version.cuda,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "load_s": round(load_s, 3),
        "latency_s": round(latency_s, 3),
        "peak_vram_mb": round(peak_vram_mb, 3) if peak_vram_mb is not None else None,
        "claim_boundary": "Environment smoke only; not a benchmark result.",
    }
    (run_dir / "stage1plus_vlm_smoke.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_dir": str(run_dir), **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
