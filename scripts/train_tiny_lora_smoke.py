from __future__ import annotations

import argparse
import gc
import json
import shutil
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

from vfa_policy.foveation.real_task_manifest import (
    load_task_manifest,
    prepare_manifest_policy_evidence,
    sample_for_index,
)
from vfa_policy.logging_utils import ensure_run_dir, write_json
from vfa_policy.paths import resolve_repo_path


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


def _sync(torch_module: Any) -> None:
    if torch_module.cuda.is_available():
        torch_module.cuda.synchronize()


def _mb(value_bytes: int | float) -> float:
    return round(float(value_bytes) / (1024.0 * 1024.0), 3)


def _dtype_from_name(torch_module: Any, dtype_name: str) -> Any:
    normalized = dtype_name.lower()
    if normalized in {"float16", "fp16", "half"}:
        return torch_module.float16
    if normalized in {"bfloat16", "bf16"}:
        return torch_module.bfloat16
    return torch_module.float16


def _answer(sample: dict[str, Any]) -> str:
    expected = sample.get("expected_answers") or [sample.get("expected_answer")]
    if isinstance(expected, list) and expected:
        return str(expected[0])
    return str(expected or "")


def _messages(image_paths: list[Path], prompt: str, answer: str | None = None) -> list[dict[str, Any]]:
    content = [{"type": "image", "image": str(path)} for path in image_paths]
    content.append({"type": "text", "text": prompt})
    messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
    if answer is not None:
        messages.append({"role": "assistant", "content": [{"type": "text", "text": answer}]})
    return messages


def _prepare_training_inputs(processor: Any, image_paths: list[Path], prompt: str, answer: str, device: str) -> Any:
    import torch
    from qwen_vl_utils import process_vision_info

    messages = _messages(image_paths, prompt, answer)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    labels = inputs["input_ids"].clone()
    pad_token_id = getattr(processor.tokenizer, "pad_token_id", None)
    if pad_token_id is not None:
        labels[labels == pad_token_id] = -100
    inputs["labels"] = labels
    return inputs.to(device)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/3090/tiny_scored_validation.yaml")
    parser.add_argument("--manifest", default=".local/data/tiny_scored_manifest/manifest_ocr_detector.jsonl")
    parser.add_argument("--roi-source", default="ocr_detector_box")
    parser.add_argument("--visual-policy", default="foveater_roi")
    parser.add_argument("--max-samples", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=4)
    parser.add_argument("--rank", type=int, default=4)
    parser.add_argument("--alpha", type=int, default=8)
    parser.add_argument("--target-modules", default="q_proj,v_proj")
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--output-dir", default=".local/adapters")
    parser.add_argument("--latest-name", default="tiny_lora_latest")
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; tiny LoRA training requires the RTX 3090 CUDA device.")

    config_path = resolve_repo_path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model_path = resolve_repo_path(config.get("model", {}).get("local_snapshot_path", ""))
    manifest_samples = load_task_manifest(args.manifest, repo_root=REPO_ROOT)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-tiny_lora_train")
    run_dir = ensure_run_dir(run_id, ".local/runs")
    adapter_dir = resolve_repo_path(args.output_dir) / run_id
    latest_dir = resolve_repo_path(args.output_dir) / args.latest_name
    dtype = _dtype_from_name(torch, str(config.get("model", {}).get("dtype", "float16")))
    target_modules = [item.strip() for item in args.target_modules.split(",") if item.strip()]

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
    model.config.use_cache = False
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    _sync(torch)
    base_after_load_allocated_mb = _mb(torch.cuda.memory_allocated())
    base_load_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)

    lora_config = LoraConfig(
        r=int(args.rank),
        lora_alpha=int(args.alpha),
        target_modules=target_modules,
        lora_dropout=0.0,
        bias="none",
        task_type="CAUSAL_LM",
    )
    attach_started = time.perf_counter()
    model = get_peft_model(model, lora_config)
    model.train()
    _sync(torch)
    after_attach_allocated_mb = _mb(torch.cuda.memory_allocated())
    attach_latency_ms = round((time.perf_counter() - attach_started) * 1000.0, 3)
    trainable_params = int(sum(param.numel() for param in model.parameters() if param.requires_grad))
    optimizer = torch.optim.AdamW((param for param in model.parameters() if param.requires_grad), lr=float(args.learning_rate))

    losses: list[float] = []
    torch.cuda.reset_peak_memory_stats()
    for step in range(int(args.max_steps)):
        sample = sample_for_index(manifest_samples, step % int(args.max_samples))
        if sample is None:
            raise RuntimeError("No manifest sample available for training.")
        evidence = prepare_manifest_policy_evidence(
            sample=sample,
            sample_index=step,
            visual_policy=str(args.visual_policy),
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            roi_source_override=str(args.roi_source),
        )
        inputs = _prepare_training_inputs(
            processor,
            evidence["image_paths"],
            str(sample.get("prompt") or "Answer the image question."),
            _answer(sample),
            "cuda:0",
        )
        optimizer.zero_grad(set_to_none=True)
        outputs = model(**inputs)
        loss = outputs.loss
        loss.backward()
        optimizer.step()
        _sync(torch)
        losses.append(round(float(loss.detach().cpu()), 6))
        del outputs
        del inputs
        torch.cuda.empty_cache()

    train_peak_allocated_mb = _mb(torch.cuda.max_memory_allocated())
    adapter_dir.mkdir(parents=True, exist_ok=True)
    latest_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(adapter_dir)
    processor.save_pretrained(adapter_dir / "processor")
    if latest_dir.exists():
        for child in latest_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    model.save_pretrained(latest_dir)
    (latest_dir / "source_run_id.txt").write_text(run_id + "\n", encoding="utf-8")

    del model
    gc.collect()
    torch.cuda.empty_cache()
    _sync(torch)

    result = {
        "schema_version": "3090.tiny_lora_train.v0.1",
        "run_id": run_id,
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "manifest_path": str(resolve_repo_path(args.manifest).relative_to(REPO_ROOT)),
        "adapter_dir": str(adapter_dir.relative_to(REPO_ROOT)),
        "latest_adapter_dir": str(latest_dir.relative_to(REPO_ROOT)),
        "hardware": {"gpu": torch.cuda.get_device_name(0)},
        "model": str(config.get("model", {}).get("shared_backbone_id")),
        "roi_source": str(args.roi_source),
        "visual_policy": str(args.visual_policy),
        "max_samples": int(args.max_samples),
        "train_steps": int(args.max_steps),
        "rank": int(args.rank),
        "alpha": int(args.alpha),
        "target_modules": target_modules,
        "learning_rate": float(args.learning_rate),
        "base_load_latency_ms": base_load_latency_ms,
        "base_after_load_allocated_mb": base_after_load_allocated_mb,
        "peft_attach_latency_ms": attach_latency_ms,
        "peft_allocated_delta_mb": round(after_attach_allocated_mb - base_after_load_allocated_mb, 3),
        "train_peak_allocated_mb": train_peak_allocated_mb,
        "trainable_lora_parameters": trainable_params,
        "losses": losses,
        "loss_first": losses[0] if losses else None,
        "loss_last": losses[-1] if losses else None,
        "claim_boundary": {
            "trained_adapter_saved": True,
            "tiny_controlled_training_smoke": True,
            "benchmark_generalization_claim": False,
            "trained_lora_accuracy_gain_claim": False,
        },
    }
    write_json(run_dir / "tiny_lora_train_result.json", result)
    (run_dir / "result_summary_ko.md").write_text(
        "\n".join(
            [
                "# Tiny LoRA Training Smoke",
                "",
                f"- run_id: `{run_id}`",
                f"- adapter_dir: `{result['adapter_dir']}`",
                f"- latest_adapter_dir: `{result['latest_adapter_dir']}`",
                f"- train_steps: `{result['train_steps']}`",
                f"- trainable_lora_parameters: `{result['trainable_lora_parameters']}`",
                f"- loss_first: `{result['loss_first']}`",
                f"- loss_last: `{result['loss_last']}`",
                f"- train_peak_allocated_mb: `{result['train_peak_allocated_mb']}`",
                "",
                "이 run은 controlled tiny set에서 adapter 학습/저장 경로를 닫는 smoke다.",
                "일반 benchmark 성능 향상 claim에는 사용하지 않는다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"run_dir": str(run_dir), "adapter_dir": result["adapter_dir"], "losses": losses}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
