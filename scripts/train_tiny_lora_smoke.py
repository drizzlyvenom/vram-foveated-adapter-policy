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


def _split_samples(samples: list[dict[str, Any]], split_name: str | None) -> list[dict[str, Any]]:
    if not split_name or split_name.lower() in {"all", "none"}:
        return list(samples)
    selected = [sample for sample in samples if str(sample.get("split") or "").lower() == split_name.lower()]
    return selected


def _limit_samples(samples: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    if limit is None or int(limit) <= 0:
        return list(samples)
    return list(samples[: int(limit)])


def _normalize_answer_text(value: Any) -> str:
    import re

    text = str(value or "").upper()
    text = re.sub(r"[^A-Z0-9.+\\-]+", " ", text)
    return " ".join(text.split())


def _score_answer(sample: dict[str, Any], answer_text: str | None) -> dict[str, Any]:
    expected = sample.get("expected_answers")
    if expected is None and sample.get("expected_answer") is not None:
        expected = [sample.get("expected_answer")]
    if isinstance(expected, str):
        expected = [expected]
    expected_list = [str(item) for item in (expected or []) if item not in (None, "")]
    if not expected_list or answer_text is None:
        return {"score": None, "correct": None, "matched_expected_answer": None}

    normalized_answer = _normalize_answer_text(answer_text)
    answer_tokens = set(normalized_answer.split())
    best_score = 0.0
    matched = None
    for expected_text in expected_list:
        normalized_expected = _normalize_answer_text(expected_text)
        if not normalized_expected:
            continue
        if normalized_expected in normalized_answer:
            return {"score": 1.0, "correct": True, "matched_expected_answer": expected_text}
        expected_tokens = set(normalized_expected.split())
        if expected_tokens:
            score = len(answer_tokens & expected_tokens) / len(expected_tokens)
            if score > best_score:
                best_score = score
    return {
        "score": round(float(best_score), 6),
        "correct": bool(best_score >= 0.999),
        "matched_expected_answer": matched,
    }


def _messages(image_paths: list[Path], prompt: str, answer: str | None = None) -> list[dict[str, Any]]:
    content = [{"type": "image", "image": str(path)} for path in image_paths]
    content.append({"type": "text", "text": prompt})
    messages: list[dict[str, Any]] = [{"role": "user", "content": content}]
    if answer is not None:
        messages.append({"role": "assistant", "content": [{"type": "text", "text": answer}]})
    return messages


def _mask_training_labels(
    input_ids: Any,
    *,
    prompt_token_count: int,
    pad_token_id: int | None,
    label_mask_mode: str,
) -> tuple[Any, dict[str, int | str]]:
    labels = input_ids.clone()
    input_token_count = int(labels.shape[-1])

    if label_mask_mode == "answer_only":
        labels[:, : min(prompt_token_count, input_token_count)] = -100
    elif label_mask_mode != "full_sequence_except_pad":
        raise ValueError(f"Unsupported label_mask_mode: {label_mask_mode}")

    if pad_token_id is not None:
        labels[labels == pad_token_id] = -100

    supervised_token_count = int((labels != -100).sum().item())
    if supervised_token_count <= 0:
        raise RuntimeError(
            "No supervised tokens remain after label masking; check chat template and answer text."
        )

    return labels, {
        "label_mask_mode": label_mask_mode,
        "input_token_count": input_token_count,
        "prompt_token_count": int(prompt_token_count),
        "supervised_token_count": supervised_token_count,
    }


def _prepare_training_inputs(
    processor: Any,
    image_paths: list[Path],
    prompt: str,
    answer: str,
    device: str,
    label_mask_mode: str,
) -> tuple[Any, dict[str, int | str]]:
    from qwen_vl_utils import process_vision_info

    messages = _messages(image_paths, prompt, answer)
    prompt_messages = _messages(image_paths, prompt, None)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    prompt_text = processor.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    prompt_inputs = processor(
        text=[prompt_text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    pad_token_id = getattr(processor.tokenizer, "pad_token_id", None)
    labels, mask_info = _mask_training_labels(
        inputs["input_ids"],
        prompt_token_count=int(prompt_inputs["input_ids"].shape[-1]),
        pad_token_id=pad_token_id,
        label_mask_mode=label_mask_mode,
    )
    inputs["labels"] = labels
    del prompt_inputs
    return inputs.to(device), mask_info


def _prepare_eval_inputs(
    processor: Any,
    image_paths: list[Path],
    prompt: str,
    device: str,
) -> Any:
    from qwen_vl_utils import process_vision_info

    messages = _messages(image_paths, prompt, None)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    return inputs.to(device)


def _mean_score(rows: list[dict[str, Any]]) -> float | None:
    values = [float(row["score"]) for row in rows if row.get("score") is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _evaluate_samples(
    *,
    model: Any,
    processor: Any,
    samples: list[dict[str, Any]],
    visual_policy: str,
    roi_source: str,
    run_dir: Path,
    max_new_tokens: int,
    torch_module: Any,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    model.eval()
    for sample_index, sample in enumerate(samples):
        evidence = prepare_manifest_policy_evidence(
            sample=sample,
            sample_index=sample_index,
            visual_policy=visual_policy,
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            roi_source_override=roi_source,
        )
        inputs = _prepare_eval_inputs(
            processor,
            evidence["image_paths"],
            str(sample.get("prompt") or "Answer the image question."),
            "cuda:0",
        )
        with torch_module.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=int(max_new_tokens),
                do_sample=False,
            )
        _sync(torch_module)
        answer_text = processor.batch_decode(generated, skip_special_tokens=True)[0]
        scored = _score_answer(sample, answer_text)
        rows.append(
            {
                "sample_id": sample.get("sample_id"),
                "split": sample.get("split"),
                "expected_answer": _answer(sample),
                "answer_text": answer_text,
                **scored,
            }
        )
        del generated
        del inputs
        torch_module.cuda.empty_cache()
    correct_values = [row.get("correct") for row in rows if row.get("correct") is not None]
    return {
        "samples": len(rows),
        "score_mean": _mean_score(rows),
        "correct_count": sum(1 for value in correct_values if bool(value)),
        "available_count": len(correct_values),
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/3090/tiny_scored_validation.yaml")
    parser.add_argument("--manifest", default=".local/data/tiny_scored_manifest/manifest_ocr_detector.jsonl")
    parser.add_argument("--roi-source", default="ocr_detector_box")
    parser.add_argument("--visual-policy", default="foveater_roi")
    parser.add_argument("--max-samples", type=int, default=4)
    parser.add_argument("--max-steps", type=int, default=4)
    parser.add_argument("--train-split", default="train")
    parser.add_argument("--holdout-split", default="holdout")
    parser.add_argument("--eval-train-samples", type=int, default=32)
    parser.add_argument("--eval-holdout-samples", type=int, default=32)
    parser.add_argument("--eval-max-new-tokens", type=int, default=8)
    parser.add_argument("--skip-eval", action="store_true")
    parser.add_argument("--rank", type=int, default=4)
    parser.add_argument("--alpha", type=int, default=8)
    parser.add_argument("--target-modules", default="q_proj,v_proj")
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--output-dir", default=".local/adapters")
    parser.add_argument("--latest-name", default="tiny_lora_latest")
    parser.add_argument(
        "--label-mask-mode",
        choices=["answer_only", "full_sequence_except_pad"],
        default="answer_only",
        help="Use answer_only for real training claims; full_sequence_except_pad is legacy smoke behavior.",
    )
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
    train_pool = _split_samples(manifest_samples, str(args.train_split))
    if not train_pool:
        train_pool = list(manifest_samples)
    holdout_pool = _split_samples(manifest_samples, str(args.holdout_split))
    train_samples = _limit_samples(train_pool, int(args.max_samples))
    if not train_samples:
        raise RuntimeError("No train samples are available after split filtering.")
    holdout_samples = _limit_samples(holdout_pool, int(args.eval_holdout_samples))
    train_eval_samples = _limit_samples(train_pool, int(args.eval_train_samples))
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
    mask_infos: list[dict[str, int | str]] = []
    torch.cuda.reset_peak_memory_stats()
    for step in range(int(args.max_steps)):
        sample = sample_for_index(train_samples, step)
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
        inputs, mask_info = _prepare_training_inputs(
            processor,
            evidence["image_paths"],
            str(sample.get("prompt") or "Answer the image question."),
            _answer(sample),
            "cuda:0",
            str(args.label_mask_mode),
        )
        mask_infos.append(mask_info)
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
    evaluation: dict[str, Any] = {
        "enabled": not bool(args.skip_eval),
        "train_split": str(args.train_split),
        "holdout_split": str(args.holdout_split),
        "train_pool_samples": len(train_pool),
        "holdout_pool_samples": len(holdout_pool),
    }
    if not args.skip_eval:
        evaluation["train"] = _evaluate_samples(
            model=model,
            processor=processor,
            samples=train_eval_samples,
            visual_policy=str(args.visual_policy),
            roi_source=str(args.roi_source),
            run_dir=run_dir,
            max_new_tokens=int(args.eval_max_new_tokens),
            torch_module=torch,
        )
        evaluation["holdout"] = _evaluate_samples(
            model=model,
            processor=processor,
            samples=holdout_samples,
            visual_policy=str(args.visual_policy),
            roi_source=str(args.roi_source),
            run_dir=run_dir,
            max_new_tokens=int(args.eval_max_new_tokens),
            torch_module=torch,
        )
        model.train()
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
        "manifest_sample_count": len(manifest_samples),
        "train_split": str(args.train_split),
        "holdout_split": str(args.holdout_split),
        "train_sample_count": len(train_samples),
        "holdout_sample_count": len(holdout_samples),
        "train_steps": int(args.max_steps),
        "rank": int(args.rank),
        "alpha": int(args.alpha),
        "target_modules": target_modules,
        "learning_rate": float(args.learning_rate),
        "label_mask_mode": str(args.label_mask_mode),
        "supervised_token_count_min": min((int(item["supervised_token_count"]) for item in mask_infos), default=None),
        "supervised_token_count_max": max((int(item["supervised_token_count"]) for item in mask_infos), default=None),
        "supervised_token_count_mean": (
            round(sum(int(item["supervised_token_count"]) for item in mask_infos) / len(mask_infos), 3)
            if mask_infos
            else None
        ),
        "input_token_count_mean": (
            round(sum(int(item["input_token_count"]) for item in mask_infos) / len(mask_infos), 3)
            if mask_infos
            else None
        ),
        "prompt_token_count_mean": (
            round(sum(int(item["prompt_token_count"]) for item in mask_infos) / len(mask_infos), 3)
            if mask_infos
            else None
        ),
        "base_load_latency_ms": base_load_latency_ms,
        "base_after_load_allocated_mb": base_after_load_allocated_mb,
        "peft_attach_latency_ms": attach_latency_ms,
        "peft_allocated_delta_mb": round(after_attach_allocated_mb - base_after_load_allocated_mb, 3),
        "train_peak_allocated_mb": train_peak_allocated_mb,
        "trainable_lora_parameters": trainable_params,
        "losses": losses,
        "loss_first": losses[0] if losses else None,
        "loss_last": losses[-1] if losses else None,
        "evaluation": evaluation,
        "claim_boundary": {
            "trained_adapter_saved": True,
            "tiny_controlled_training_smoke": True,
            "answer_only_label_mask": str(args.label_mask_mode) == "answer_only",
            "train_holdout_evaluation_available": not bool(args.skip_eval),
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
                f"- train_sample_count: `{result['train_sample_count']}`",
                f"- holdout_sample_count: `{result['holdout_sample_count']}`",
                f"- trainable_lora_parameters: `{result['trainable_lora_parameters']}`",
                f"- label_mask_mode: `{result['label_mask_mode']}`",
                f"- supervised_token_count_mean: `{result['supervised_token_count_mean']}`",
                f"- loss_first: `{result['loss_first']}`",
                f"- loss_last: `{result['loss_last']}`",
                f"- eval_train_score_mean: `{evaluation.get('train', {}).get('score_mean') if evaluation.get('train') else None}`",
                f"- eval_holdout_score_mean: `{evaluation.get('holdout', {}).get('score_mean') if evaluation.get('holdout') else None}`",
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
