from __future__ import annotations

import argparse
import gc
import json
import re
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
)
from vfa_policy.logging_utils import append_jsonl, ensure_run_dir, write_json
from vfa_policy.paths import repo_relative, resolve_repo_path


DEFAULT_ADAPTERS = {
    "document": ".local/adapters/tiny_lora_document_latest",
    "scene_text": ".local/adapters/tiny_lora_scene_text_latest",
    "ui_screen": ".local/adapters/tiny_lora_ui_screen_latest",
    "chart": ".local/adapters/tiny_lora_chart_latest",
}

TASK_FAMILY_TO_ADAPTER = {
    "document_or_receipt": "document",
    "scene_text_or_ocr": "scene_text",
    "ui_screen": "ui_screen",
    "chart_or_table": "chart",
}

ADAPTER_ORDER = ["document", "scene_text", "ui_screen", "chart"]


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


def _dtype_from_name(torch_module: Any, dtype_name: str) -> Any:
    normalized = dtype_name.lower()
    if normalized in {"float16", "fp16", "half"}:
        return torch_module.float16
    if normalized in {"bfloat16", "bf16"}:
        return torch_module.bfloat16
    return torch_module.float16


def _normalize_answer_text(value: Any) -> str:
    text = str(value or "").upper()
    text = re.sub(r"[^A-Z0-9.+\\-]+", " ", text)
    return " ".join(text.split())


def _expected_answers(sample: dict[str, Any]) -> list[str]:
    expected = sample.get("expected_answers")
    if expected is None and sample.get("expected_answer") is not None:
        expected = [sample.get("expected_answer")]
    if isinstance(expected, str):
        return [expected]
    if isinstance(expected, list):
        return [str(item) for item in expected if item not in (None, "")]
    return []


def _score_answer(sample: dict[str, Any], answer_text: str | None) -> dict[str, Any]:
    expected = _expected_answers(sample)
    if not expected or answer_text is None:
        return {"score": None, "correct": None, "matched_expected_answer": None}

    normalized_answer = _normalize_answer_text(answer_text)
    answer_tokens = set(normalized_answer.split())
    best_score = 0.0
    matched = None
    for expected_text in expected:
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


def _messages(image_paths: list[Path], prompt: str) -> list[dict[str, Any]]:
    content = [{"type": "image", "image": str(path)} for path in image_paths]
    content.append({"type": "text", "text": prompt})
    return [{"role": "user", "content": content}]


def _prepare_inputs(processor: Any, image_paths: list[Path], prompt: str, device: str) -> Any:
    from qwen_vl_utils import process_vision_info

    messages = _messages(image_paths, prompt)
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


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _split_samples(samples: list[dict[str, Any]], split_name: str) -> list[dict[str, Any]]:
    if split_name.lower() in {"all", "none"}:
        return list(samples)
    return [sample for sample in samples if str(sample.get("split") or "").lower() == split_name.lower()]


def _correct_adapter(sample: dict[str, Any]) -> str:
    taxonomy = str(sample.get("taxonomy_label") or "")
    if taxonomy in ADAPTER_ORDER:
        return taxonomy
    return TASK_FAMILY_TO_ADAPTER.get(str(sample.get("task_family") or ""), "document")


def _wrong_adapter(adapter_name: str) -> str:
    index = ADAPTER_ORDER.index(adapter_name)
    return ADAPTER_ORDER[(index + 1) % len(ADAPTER_ORDER)]


def _adapter_paths(args: argparse.Namespace) -> dict[str, Path]:
    values = {
        "document": args.document_adapter,
        "scene_text": args.scene_text_adapter,
        "ui_screen": args.ui_screen_adapter,
        "chart": args.chart_adapter,
    }
    return {name: resolve_repo_path(path) for name, path in values.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/3090/tiny_scored_validation.yaml")
    parser.add_argument("--manifest", default=".local/data/tiny_scored_manifest/manifest_ocr_detector.jsonl")
    parser.add_argument("--roi-source", default="ocr_detector_box")
    parser.add_argument("--visual-policy", default="foveater_roi")
    parser.add_argument("--split", default="holdout")
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--document-adapter", default=DEFAULT_ADAPTERS["document"])
    parser.add_argument("--scene-text-adapter", default=DEFAULT_ADAPTERS["scene_text"])
    parser.add_argument("--ui-screen-adapter", default=DEFAULT_ADAPTERS["ui_screen"])
    parser.add_argument("--chart-adapter", default=DEFAULT_ADAPTERS["chart"])
    args = parser.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoProcessor

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; multi-LoRA bank smoke requires the RTX 3090 CUDA device.")

    config_path = resolve_repo_path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model_path = resolve_repo_path(config.get("model", {}).get("local_snapshot_path", ""))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-multi_lora_bank_smoke")
    run_dir = ensure_run_dir(run_id, ".local/runs")
    row_path = run_dir / "multi_lora_bank_rows.jsonl"

    adapter_paths = _adapter_paths(args)
    for name, path in adapter_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Adapter path for {name} does not exist: {path}")

    samples = _split_samples(load_task_manifest(args.manifest, repo_root=REPO_ROOT), str(args.split))
    samples = samples[: int(args.max_samples)]
    if not samples:
        raise RuntimeError("No samples selected for multi-LoRA bank smoke.")

    dtype = _dtype_from_name(torch, str(config.get("model", {}).get("dtype", "float16")))
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
        base_model = AutoModelForImageTextToText.from_pretrained(model_path, **load_kwargs)
    except TypeError:
        load_kwargs.pop("dtype", None)
        load_kwargs["torch_dtype"] = dtype
        base_model = AutoModelForImageTextToText.from_pretrained(model_path, **load_kwargs)
    torch.cuda.synchronize()
    base_after_load_allocated_mb = _mb(torch.cuda.memory_allocated())
    base_load_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)

    attach_started = time.perf_counter()
    model = PeftModel.from_pretrained(
        base_model,
        adapter_paths["document"],
        adapter_name="document",
        is_trainable=False,
    )
    for adapter_name in ["scene_text", "ui_screen", "chart"]:
        model.load_adapter(
            adapter_paths[adapter_name],
            adapter_name=adapter_name,
            is_trainable=False,
        )
    model.eval()
    torch.cuda.synchronize()
    after_bank_load_allocated_mb = _mb(torch.cuda.memory_allocated())
    bank_attach_latency_ms = round((time.perf_counter() - attach_started) * 1000.0, 3)

    rows: list[dict[str, Any]] = []
    for sample_index, sample in enumerate(samples):
        evidence = prepare_manifest_policy_evidence(
            sample=sample,
            sample_index=sample_index,
            visual_policy=str(args.visual_policy),
            run_dir=run_dir,
            repo_root=REPO_ROOT,
            roi_source_override=str(args.roi_source),
        )
        inputs = _prepare_inputs(
            processor,
            evidence["image_paths"],
            str(sample.get("prompt") or "Answer the image question."),
            "cuda:0",
        )
        correct_adapter = _correct_adapter(sample)
        wrong_adapter = _wrong_adapter(correct_adapter)
        sample_rows: list[dict[str, Any]] = []
        for condition, adapter_name in [("correct", correct_adapter), ("wrong", wrong_adapter)]:
            model.set_adapter(adapter_name)
            with torch.inference_mode():
                generated = model.generate(
                    **inputs,
                    max_new_tokens=int(args.max_new_tokens),
                    do_sample=False,
                )
            torch.cuda.synchronize()
            answer_text = processor.batch_decode(generated, skip_special_tokens=True)[0]
            scored = _score_answer(sample, answer_text)
            sample_rows.append(
                {
                    "sample_index": sample_index,
                    "sample_id": sample.get("sample_id"),
                    "task_family": sample.get("task_family"),
                    "taxonomy_label": sample.get("taxonomy_label"),
                    "condition": condition,
                    "adapter_name": adapter_name,
                    "expected_answers": _expected_answers(sample),
                    "answer_text": answer_text,
                    **scored,
                }
            )
            del generated
        correct_score = sample_rows[0].get("score")
        wrong_score = sample_rows[1].get("score")
        damage = None
        if correct_score is not None and wrong_score is not None:
            damage = round(float(correct_score) - float(wrong_score), 6)
        for row in sample_rows:
            row["correct_minus_wrong_score"] = damage
            rows.append(row)
            append_jsonl(row_path, row)
        del inputs
        torch.cuda.empty_cache()

    correct_scores = [float(row["score"]) for row in rows if row["condition"] == "correct" and row.get("score") is not None]
    wrong_scores = [float(row["score"]) for row in rows if row["condition"] == "wrong" and row.get("score") is not None]
    paired_damages = [
        float(row["correct_minus_wrong_score"])
        for row in rows
        if row["condition"] == "correct" and row.get("correct_minus_wrong_score") is not None
    ]
    result = {
        "schema_version": "3090.multi_lora_bank_smoke.v0.1",
        "run_id": run_id,
        "git_commit": _git_commit(),
        "config_path": repo_relative(config_path),
        "manifest_path": repo_relative(resolve_repo_path(args.manifest)),
        "split": str(args.split),
        "samples": len(samples),
        "roi_source": str(args.roi_source),
        "visual_policy": str(args.visual_policy),
        "adapter_paths": {name: repo_relative(path) for name, path in adapter_paths.items()},
        "base_load_latency_ms": base_load_latency_ms,
        "bank_attach_latency_ms": bank_attach_latency_ms,
        "base_after_load_allocated_mb": base_after_load_allocated_mb,
        "after_bank_load_allocated_mb": after_bank_load_allocated_mb,
        "adapter_bank_allocated_delta_mb": round(after_bank_load_allocated_mb - base_after_load_allocated_mb, 3),
        "correct_score_mean": _mean(correct_scores),
        "wrong_score_mean": _mean(wrong_scores),
        "correct_minus_wrong_score_mean": _mean(paired_damages),
        "claim_boundary": {
            "multi_trained_lora_bank_loaded": True,
            "routing_path_smoke": True,
            "wrong_adapter_damage_measured": True,
            "accuracy_gain_claim": False,
            "production_routing_claim": False,
        },
    }
    write_json(run_dir / "multi_lora_bank_result.json", result)
    (run_dir / "result_summary_ko.md").write_text(
        "\n".join(
            [
                "# Multi LoRA Bank Smoke",
                "",
                f"- run_id: `{run_id}`",
                f"- samples: `{result['samples']}`",
                f"- correct_score_mean: `{result['correct_score_mean']}`",
                f"- wrong_score_mean: `{result['wrong_score_mean']}`",
                f"- correct_minus_wrong_score_mean: `{result['correct_minus_wrong_score_mean']}`",
                f"- adapter_bank_allocated_delta_mb: `{result['adapter_bank_allocated_delta_mb']}`",
                f"- bank_attach_latency_ms: `{result['bank_attach_latency_ms']}`",
                "",
                "이 run은 여러 실제 LoRA adapter를 한 모델에 로드하고 set_adapter 경로를 확인하는 smoke다.",
                "production routing 또는 accuracy gain claim으로 승격하지 않는다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    del model
    gc.collect()
    torch.cuda.empty_cache()
    print(json.dumps({"run_dir": str(run_dir), **result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
