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

from vfa_policy.core.real_measurement import make_probe_images
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


def _reset_peak(torch_module: Any) -> None:
    _sync(torch_module)
    torch_module.cuda.reset_peak_memory_stats()


def _dtype_from_name(torch_module: Any, dtype_name: str) -> Any:
    normalized = dtype_name.lower()
    if normalized in {"float16", "fp16", "half"}:
        return torch_module.float16
    if normalized in {"bfloat16", "bf16"}:
        return torch_module.bfloat16
    return torch_module.float16


def _count_trainable_parameters(model: Any) -> int:
    return int(sum(param.numel() for param in model.parameters() if param.requires_grad))


def _prepare_inputs(processor: Any, image_path: Path, prompt: str) -> Any:
    from qwen_vl_utils import process_vision_info

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
    return processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_TWO_TRACK_CONFIG)
    parser.add_argument("--output-dir", default=".local/runs")
    parser.add_argument("--rank", type=int, default=4)
    parser.add_argument("--alpha", type=int, default=8)
    parser.add_argument("--target-modules", default="q_proj,v_proj")
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    try:
        from peft import LoraConfig, get_peft_model
    except ImportError as exc:
        raise RuntimeError("peft is not installed. Install requirements.txt before actual PEFT smoke.") from exc

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; actual PEFT smoke requires RTX 3090 CUDA.")

    config_path = resolve_repo_path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model_path = resolve_repo_path(config.get("model", {}).get("local_snapshot_path", ""))
    dtype = _dtype_from_name(torch, str(config.get("model", {}).get("dtype", "float16")))
    target_modules = [item.strip() for item in args.target_modules.split(",") if item.strip()]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-actual_peft_smoke")
    run_dir = ensure_run_dir(run_id, args.output_dir)

    started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
    load_kwargs = {
        "trust_remote_code": True,
        "local_files_only": True,
        "device_map": {"": "cuda:0"},
        "dtype": dtype,
        "attn_implementation": "sdpa",
    }
    try:
        model = AutoModelForImageTextToText.from_pretrained(model_path, **load_kwargs)
    except TypeError:
        load_kwargs.pop("dtype", None)
        load_kwargs["torch_dtype"] = dtype
        model = AutoModelForImageTextToText.from_pretrained(model_path, **load_kwargs)
    model.eval()
    _sync(torch)
    base_load_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    base_allocated_mb = _mb(torch.cuda.memory_allocated())
    base_reserved_mb = _mb(torch.cuda.memory_reserved())

    lora_config = LoraConfig(
        r=int(args.rank),
        lora_alpha=int(args.alpha),
        target_modules=target_modules,
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
    )
    started = time.perf_counter()
    model = get_peft_model(model, lora_config)
    model.eval()
    _sync(torch)
    attach_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    after_attach_allocated_mb = _mb(torch.cuda.memory_allocated())
    after_attach_reserved_mb = _mb(torch.cuda.memory_reserved())
    trainable_params = _count_trainable_parameters(model)

    image_bank = make_probe_images(run_dir)
    cpu_inputs = _prepare_inputs(
        processor,
        image_bank["roi"],
        "Read the large labels in the image. Answer with one concise phrase.",
    )
    torch.cuda.empty_cache()
    _sync(torch)
    forward_baseline_mb = max(_mb(torch.cuda.memory_allocated()), after_attach_allocated_mb)
    _reset_peak(torch)
    started = time.perf_counter()
    with torch.inference_mode():
        cuda_inputs = cpu_inputs.to("cuda:0")
        outputs = model(**cuda_inputs, use_cache=True)
    _sync(torch)
    forward_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    forward_peak_mb = _mb(torch.cuda.max_memory_allocated())
    del outputs
    del cuda_inputs
    del cpu_inputs
    del model
    gc.collect()
    torch.cuda.empty_cache()
    _sync(torch)

    result = {
        "schema_version": "3090.actual_peft_smoke.v0.1",
        "run_id": run_id,
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "hardware": {"gpu": torch.cuda.get_device_name(0)},
        "adapter_execution_mode": "actual_peft",
        "adapter_memory_source": "actual_loaded_adapter",
        "target_modules": target_modules,
        "rank": int(args.rank),
        "alpha": int(args.alpha),
        "base_load_latency_ms": base_load_latency_ms,
        "base_after_load_allocated_mb": base_allocated_mb,
        "base_after_load_reserved_mb": base_reserved_mb,
        "peft_attach_latency_ms": attach_latency_ms,
        "after_peft_attach_allocated_mb": after_attach_allocated_mb,
        "after_peft_attach_reserved_mb": after_attach_reserved_mb,
        "peft_allocated_delta_mb": round(after_attach_allocated_mb - base_allocated_mb, 3),
        "peft_reserved_delta_mb": round(after_attach_reserved_mb - base_reserved_mb, 3),
        "trainable_lora_parameters": trainable_params,
        "forward_latency_ms": forward_latency_ms,
        "forward_peak_mb": forward_peak_mb,
        "forward_incremental_peak_mb": round(max(0.0, forward_peak_mb - forward_baseline_mb), 3),
        "claim_boundary": {
            "actual_peft_adapter_loaded": True,
            "trained_lora_gain_claim": False,
            "uses_random_untrained_adapter": True,
            "task_accuracy_claim": False,
        },
    }
    write_json(run_dir / "actual_peft_result.json", result)
    (run_dir / "result_summary_ko.md").write_text(
        "\n".join(
            [
                "# Actual PEFT Smoke",
                "",
                f"- run_id: `{run_id}`",
                f"- adapter_execution_mode: `{result['adapter_execution_mode']}`",
                f"- peft_allocated_delta_mb: `{result['peft_allocated_delta_mb']}`",
                f"- peft_attach_latency_ms: `{result['peft_attach_latency_ms']}`",
                f"- trainable_lora_parameters: `{result['trainable_lora_parameters']}`",
                "",
                "이 결과는 PEFT LoRA module attach와 forward path가 실제로 동작하는지 확인하는 smoke다.",
                "adapter는 훈련되지 않았으므로 성능 향상 claim에는 사용하지 않는다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_dir": str(run_dir), "peft_allocated_delta_mb": result["peft_allocated_delta_mb"], "peft_attach_latency_ms": result["peft_attach_latency_ms"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
