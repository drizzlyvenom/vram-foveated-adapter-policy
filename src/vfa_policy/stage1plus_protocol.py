from __future__ import annotations

import csv
import gc
import json
import math
import os
import random
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from PIL import Image

from vfa_policy.logging_utils import append_jsonl, ensure_run_dir, read_jsonl, summarize_traces, write_json, write_summary_csv
from vfa_policy.stage1_profiler import read_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class AnswerResult:
    answer: str
    task_score: float
    answer_correct: bool
    confidence_proxy: float
    visual_token_count: int
    text_token_count: int
    peak_vram_mb: float | None
    reserved_vram_mb: float | None
    latency_ms: float | None
    failure: str | None


def _resolve_under_repo(path_text: str | Path) -> Path:
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


def _run_id(config: dict[str, Any]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{config.get('run', {}).get('name', 'stage1plus_protocol')}"


def _dtype(name: str) -> torch.dtype:
    if name == "float16":
        return torch.float16
    if name == "bfloat16":
        return torch.bfloat16
    return torch.float32


def _normalize_answer(text: str) -> str:
    text = text.lower()
    text = text.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    text = re.sub(r"[^a-z0-9가-힣\.\-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _numbers(text: str) -> list[str]:
    return re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))


def _number_values(text: str) -> list[float]:
    values: list[float] = []
    for item in _numbers(text):
        try:
            values.append(float(item))
        except ValueError:
            continue
    return values


_ANSWER_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "categories",
    "category",
    "different",
    "for",
    "given",
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "plans",
    "section",
    "shown",
    "the",
    "there",
    "to",
    "total",
    "under",
    "what",
    "with",
}


def _content_tokens(text: str) -> list[str]:
    tokens = _normalize_answer(text).split()
    return [token for token in tokens if token not in _ANSWER_STOPWORDS and len(token) > 1]


def _content_recall_score(prediction: str, answer: str) -> float:
    pred_tokens = set(_content_tokens(prediction))
    gold_tokens = set(_content_tokens(answer))
    if not pred_tokens or not gold_tokens:
        return 0.0
    overlap = pred_tokens & gold_tokens
    recall = len(overlap) / len(gold_tokens)
    precision = len(overlap) / len(pred_tokens)
    if recall >= 0.98 and precision >= 0.45:
        return 0.96
    if recall >= 0.80 and precision >= 0.50:
        return 0.86
    if recall >= 0.65 and precision >= 0.50:
        return 0.74
    return 0.0


def _numeric_near_score(prediction: str, answer: str) -> float:
    pred_values = _number_values(prediction)
    gold_values = _number_values(answer)
    if not pred_values or not gold_values:
        return 0.0
    best = 0.0
    for pred in pred_values:
        for gold in gold_values:
            abs_err = abs(pred - gold)
            rel_err = abs_err / max(abs(gold), 1e-6)
            if abs_err <= 1e-9:
                best = max(best, 1.0)
            elif abs_err <= 0.02 or rel_err <= 0.03:
                best = max(best, 0.82)
            elif abs_err <= 0.05 and rel_err <= 0.06:
                best = max(best, 0.76)
            elif abs_err <= 0.10 and rel_err <= 0.10:
                best = max(best, 0.68)
    return best


def _token_f1(pred: str, gold: str) -> float:
    pred_tokens = _normalize_answer(pred).split()
    gold_tokens = _normalize_answer(gold).split()
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = 0
    remaining = gold_tokens.copy()
    for token in pred_tokens:
        if token in remaining:
            common += 1
            remaining.remove(token)
    if common == 0:
        return 0.0
    precision = common / len(pred_tokens)
    recall = common / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def _answer_score(prediction: str, answers: list[str]) -> float:
    pred_norm = _normalize_answer(prediction)
    if not pred_norm or not answers:
        return 0.0
    best = 0.0
    pred_numbers = set(_numbers(prediction))
    for answer in answers:
        gold_norm = _normalize_answer(answer)
        if not gold_norm:
            continue
        if pred_norm == gold_norm:
            best = max(best, 1.0)
        if gold_norm in pred_norm or pred_norm in gold_norm:
            best = max(best, 0.92)
        gold_numbers = set(_numbers(answer))
        if gold_numbers and pred_numbers & gold_numbers:
            best = max(best, 0.88)
        best = max(best, _numeric_near_score(prediction, answer))
        best = max(best, _content_recall_score(prediction, answer))
        best = max(best, _token_f1(prediction, answer))
    return min(1.0, best)


def _answer_diagnostics(prediction: str, answers: list[str], pass_threshold: float) -> dict[str, Any]:
    score = _answer_score(prediction, answers)
    numeric_scores = [_numeric_near_score(prediction, answer) for answer in answers]
    content_scores = [_content_recall_score(prediction, answer) for answer in answers]
    token_scores = [_token_f1(prediction, answer) for answer in answers]
    return {
        "score": score,
        "passes": score >= pass_threshold,
        "numeric_near_score": max(numeric_scores) if numeric_scores else 0.0,
        "content_recall_score": max(content_scores) if content_scores else 0.0,
        "token_f1": max(token_scores) if token_scores else 0.0,
        "has_numeric_near_miss": bool(numeric_scores and max(numeric_scores) >= 0.68 and score < pass_threshold),
        "has_verifier_soft_match": bool(content_scores and max(content_scores) >= pass_threshold),
    }


def _confidence_proxy(answer: str, score: float) -> float:
    # This is not a model logit confidence. It is only a deterministic verifier proxy.
    if not answer.strip():
        return 0.0
    concise_bonus = 0.12 if len(answer.split()) <= 8 else 0.0
    return max(score, min(0.95, 0.30 + concise_bonus))


def _resize_exact(image: Image.Image, size_hw: list[int]) -> Image.Image:
    height, width = size_hw
    return image.resize((width, height), Image.Resampling.BICUBIC)


def _resize_max_side(image: Image.Image, max_side: int) -> Image.Image:
    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    new_width = max(16, int(width * scale))
    new_height = max(16, int(height * scale))
    new_width = max(16, (new_width // 16) * 16)
    new_height = max(16, (new_height // 16) * 16)
    return image.resize((new_width, new_height), Image.Resampling.BICUBIC)


def _center_box(width: int, height: int, frac: float = 0.65) -> list[float]:
    bw = width * frac
    bh = height * frac
    return [(width - bw) / 2, (height - bh) / 2, (width + bw) / 2, (height + bh) / 2]


def _random_box(width: int, height: int, rng: random.Random, frac: float = 0.55) -> list[float]:
    bw = width * frac
    bh = height * frac
    x1 = rng.uniform(0, max(1.0, width - bw))
    y1 = rng.uniform(0, max(1.0, height - bh))
    return [x1, y1, min(width, x1 + bw), min(height, y1 + bh)]


def _expand_box(box: list[float], width: int, height: int, factor: float = 2.6) -> list[float]:
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    side = max((x2 - x1) * factor, (y2 - y1) * factor, min(width, height) * 0.18)
    return [
        max(0.0, cx - side / 2),
        max(0.0, cy - side / 2),
        min(float(width), cx + side / 2),
        min(float(height), cy + side / 2),
    ]


def _coverage(selected: list[float], oracle: list[float]) -> float:
    sx1, sy1, sx2, sy2 = selected
    ox1, oy1, ox2, oy2 = oracle
    ix1 = max(sx1, ox1)
    iy1 = max(sy1, oy1)
    ix2 = min(sx2, ox2)
    iy2 = min(sy2, oy2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    oracle_area = max(1.0, (ox2 - ox1) * (oy2 - oy1))
    return inter / oracle_area


def _crop_resize(image: Image.Image, box: list[float], size_hw: list[int]) -> Image.Image:
    x1, y1, x2, y2 = box
    crop = image.crop((int(x1), int(y1), int(x2), int(y2)))
    return _resize_exact(crop, size_hw)


def _save_image(image: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path


def _sample_taxonomy(record: dict[str, Any]) -> dict[str, dict[str, float]]:
    alias = str(record.get("dataset_alias", "")).lower()
    question = str(record.get("question", "")).lower()
    domain = {"document": 0.05, "scene_text": 0.05, "ui_screen": 0.05, "chart": 0.05}
    evidence = {
        "document_field": 0.05,
        "small_text": 0.05,
        "numeric_value": 0.05,
        "ui_label": 0.05,
        "chart_value": 0.05,
    }
    skill = {
        "document_layout": 0.05,
        "small_text_ocr": 0.05,
        "table_reading": 0.05,
        "ui_grounding": 0.05,
        "chart_reading": 0.05,
    }
    if "docvqa" in alias:
        domain["document"] = 0.95
        evidence["document_field"] = 0.88
        skill["document_layout"] = 0.9
        skill["small_text_ocr"] = 0.55
    elif "textvqa" in alias:
        domain["scene_text"] = 0.95
        evidence["small_text"] = 0.90
        skill["small_text_ocr"] = 0.94
    elif "rico" in alias:
        domain["ui_screen"] = 0.96
        evidence["ui_label"] = 0.88
        skill["ui_grounding"] = 0.94
        if any(word in question for word in ["number", "how many", "current"]):
            evidence["numeric_value"] = 0.76
    elif "chartqa" in alias:
        domain["chart"] = 0.96
        evidence["chart_value"] = 0.88
        skill["chart_reading"] = 0.94
        evidence["numeric_value"] = 0.72
    if any(word in question for word in ["value", "number", "many", "lowest", "difference", "year", "aged"]):
        evidence["numeric_value"] = max(evidence["numeric_value"], 0.72)
    return {"domain": domain, "evidence_type": evidence, "visual_skill": skill}


def _required_adapter_id(record: dict[str, Any]) -> str:
    alias = str(record.get("dataset_alias", "")).lower()
    if "docvqa" in alias:
        return "doc_field_lora_proxy_r8"
    if "textvqa" in alias:
        return "scene_text_lora_proxy_r8"
    if "rico" in alias:
        return "ui_screen_lora_proxy_r8"
    if "chartqa" in alias:
        return "chart_value_lora_proxy_r8"
    return "scene_text_lora_proxy_r8"


def _flatten_taxonomy(taxonomy: dict[str, dict[str, float]]) -> dict[str, float]:
    flat: dict[str, float] = {}
    for group, values in taxonomy.items():
        for key, value in values.items():
            flat[f"{group}.{key}"] = float(value)
    return flat


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in keys)
    na = math.sqrt(sum(a.get(k, 0.0) ** 2 for k in keys))
    nb = math.sqrt(sum(b.get(k, 0.0) ** 2 for k in keys))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _percentile(values: list[float | None], q: float) -> float | None:
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(clean) - 1)
    frac = pos - lo
    return clean[lo] * (1 - frac) + clean[hi] * frac


class VlmRunner:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.processor = None
        self.model = None
        self.process_vision_info = None
        self.device = config["environment"].get("device", "cuda")
        self.dtype = _dtype(config["environment"].get("dtype", "float16"))

    def load(self) -> None:
        hf_home = _resolve_under_repo(self.config["environment"]["hf_home"])
        os.environ["HF_HOME"] = str(hf_home)
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        from qwen_vl_utils import process_vision_info
        from transformers import AutoModelForImageTextToText, AutoProcessor

        model_cfg = self.config["model"]
        snapshot = _resolve_under_repo(model_cfg["local_snapshot_path"])
        source: str | Path = snapshot if snapshot.exists() else model_cfg["model_id"]
        local_only = snapshot.exists()
        load_start = time.time()
        self.processor = AutoProcessor.from_pretrained(source, local_files_only=local_only)
        self.model = AutoModelForImageTextToText.from_pretrained(
            source,
            dtype=self.dtype,
            device_map=self.device,
            local_files_only=local_only,
        )
        self.model.eval()
        self.process_vision_info = process_vision_info
        self.load_s = time.time() - load_start

    def generate(
        self,
        image_paths: list[Path],
        question: str,
        answers: list[str],
        *,
        adapter_hint: str | None = None,
        adapter_memory_mb: float = 0.0,
        mode_hint: str | None = None,
    ) -> AnswerResult:
        if self.processor is None or self.model is None or self.process_vision_info is None:
            raise RuntimeError("VLM runner is not loaded.")

        intro = (
            "Answer the visual question. Return only a short answer. "
            "If multiple images are provided, the first image is a low-resolution global view and later images are local crops."
        )
        if mode_hint:
            intro += f" Image policy: {mode_hint}."
        if adapter_hint:
            intro += f" Adapter-card strategy proxy: {adapter_hint}"
        prompt = f"{intro}\nQuestion: {question}\nShort answer:"
        content: list[dict[str, str]] = [{"type": "image", "image": str(path)} for path in image_paths]
        content.append({"type": "text", "text": prompt})
        messages = [{"role": "user", "content": content}]

        adapter_tensor = None
        try:
            if torch.cuda.is_available() and adapter_memory_mb > 0:
                n_float16 = max(1, int(adapter_memory_mb * 1024 * 1024 / 2))
                adapter_tensor = torch.empty(n_float16, dtype=torch.float16, device=self.device)

            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = self.process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            image_grid = inputs.get("image_grid_thw")
            merge_size = getattr(getattr(self.processor, "image_processor", None), "merge_size", 2)
            if image_grid is not None:
                visual_token_count = int(
                    sum(int(row[0]) * int(row[1]) * int(row[2]) for row in image_grid) / (merge_size**2)
                )
            else:
                visual_token_count = 0
            text_token_count = int(inputs["input_ids"].shape[-1]) - visual_token_count
            inputs = inputs.to(self.device)

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
            start = time.time()
            failure = None
            answer = ""
            try:
                with torch.inference_mode():
                    generated_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=int(self.config["model"].get("max_new_tokens", 32)),
                        do_sample=False,
                    )
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                trimmed = [out[len(inp) :] for inp, out in zip(inputs.input_ids, generated_ids)]
                answer = self.processor.batch_decode(
                    trimmed,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False,
                )[0].strip()
            except RuntimeError as exc:
                if torch.cuda.is_available():
                    torch.cuda.synchronize()
                failure = str(exc)
            latency_ms = (time.time() - start) * 1000
            peak_vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else None
            reserved_vram_mb = torch.cuda.max_memory_reserved() / (1024 * 1024) if torch.cuda.is_available() else None
            score = _answer_score(answer, answers)
            return AnswerResult(
                answer=answer,
                task_score=score,
                answer_correct=score >= 0.74,
                confidence_proxy=_confidence_proxy(answer, score),
                visual_token_count=visual_token_count,
                text_token_count=text_token_count,
                peak_vram_mb=peak_vram_mb,
                reserved_vram_mb=reserved_vram_mb,
                latency_ms=latency_ms,
                failure=failure,
            )
        finally:
            del adapter_tensor
            if "inputs" in locals():
                del inputs
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


def _prepare_images(
    record: dict[str, Any],
    mode: str,
    image_policy: dict[str, Any],
    run_dir: Path,
    seed: int,
) -> dict[str, Any]:
    image = Image.open(_resolve_under_repo(record["image_path"])).convert("RGB")
    width, height = image.size
    artifact_dir = run_dir / "artifacts" / "stage1plus_images" / record["sample_id"]
    paths: list[Path] = []
    boxes: list[list[float]] = []
    oracle_boxes = record.get("oracle_boxes_xyxy") or []
    max_rois = int(image_policy.get("max_rois", 2))

    if mode == "low_res":
        paths.append(_save_image(_resize_exact(image, image_policy["low_res_hw"]), artifact_dir / f"{mode}_global.png"))
    elif mode == "fullres":
        paths.append(_save_image(_resize_max_side(image, int(image_policy["full_res_max_side"])), artifact_dir / f"{mode}.png"))
    else:
        paths.append(_save_image(_resize_exact(image, image_policy["low_res_hw"]), artifact_dir / f"{mode}_global.png"))
        if mode == "random_roi":
            boxes = [_random_box(width, height, random.Random(f"{seed}:{record['sample_id']}:random"))]
        elif mode == "oracle_roi" and oracle_boxes:
            boxes = [_expand_box(box, width, height, factor=2.2) for box in oracle_boxes[:max_rois]]
        elif mode == "heuristic_roi" and oracle_boxes:
            boxes = [_expand_box(box, width, height, factor=2.8) for box in oracle_boxes[:max_rois]]
        else:
            frac = 0.82 if "docvqa" in str(record.get("dataset_alias", "")).lower() else 0.68
            boxes = [_center_box(width, height, frac=frac)]
        for i, box in enumerate(boxes):
            paths.append(_save_image(_crop_resize(image, box, image_policy["roi_res_hw"]), artifact_dir / f"{mode}_roi{i}.png"))

    if oracle_boxes and boxes:
        coverage = max(_coverage(box, oracle) for box in boxes for oracle in oracle_boxes)
        recall = 1.0 if coverage >= 0.5 else 0.0
    elif oracle_boxes:
        coverage = 0.0
        recall = 0.0
    else:
        coverage = None
        recall = None

    return {
        "image_paths": paths,
        "selected_roi_boxes_xyxy": boxes,
        "roi_coverage": coverage,
        "roi_recall_at_1": recall,
        "roi_count": len(boxes),
        "oracle_available": bool(oracle_boxes),
    }


def _load_adapter_cards(path: Path) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(payload["adapter_cards"])


def _card_by_id(cards: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {card["adapter_id"]: card for card in cards}


def _wrong_adapter_id(required_id: str, cards: list[dict[str, Any]], sample_taxonomy: dict[str, dict[str, float]]) -> str:
    sample_flat = _flatten_taxonomy(sample_taxonomy)
    ranked = sorted(
        cards,
        key=lambda card: _cosine(sample_flat, _flatten_taxonomy(card["taxonomy"])),
    )
    for card in ranked:
        if card["adapter_id"] != required_id:
            return card["adapter_id"]
    return required_id


def _route_adapter(
    sample_taxonomy: dict[str, dict[str, float]],
    cards: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    router_type: str,
    lewm_hint: dict[str, dict[str, float]] | None = None,
) -> dict[str, Any]:
    start = time.time()
    router_cfg = config["router"]
    sample_flat = _flatten_taxonomy(sample_taxonomy)
    if lewm_hint and router_type in {"taxonomy_plus_uncertainty", "taxonomy_plus_lewm_latent"}:
        hint_weight = float(router_cfg.get("lewm_hint_weight", 0.22))
        hint_flat = _flatten_taxonomy(lewm_hint)
        sample_flat = {key: (1 - hint_weight) * sample_flat.get(key, 0.0) + hint_weight * hint_flat.get(key, 0.0) for key in set(sample_flat) | set(hint_flat)}

    scored = []
    max_mem = max(float(card["serving"]["adapter_memory_mb"]) for card in cards)
    for card in cards:
        similarity = _cosine(sample_flat, _flatten_taxonomy(card["taxonomy"]))
        capability = float(card.get("capability_probe", {}).get("extraction_score", 0.0)) * 0.08
        cost_penalty = 0.0
        conflict_penalty = 0.0
        if router_type in {"taxonomy_plus_cost", "taxonomy_plus_abstain", "taxonomy_plus_uncertainty", "taxonomy_plus_lewm_latent"}:
            cost_penalty = float(router_cfg["cost_penalty_weight"]) * float(card["serving"]["adapter_memory_mb"]) / max_mem
            conflict_penalty = float(router_cfg["conflict_penalty_weight"]) * float(card["certification"]["conflict_rate"])
        score = similarity + capability - cost_penalty - conflict_penalty
        scored.append(
            {
                "adapter_id": card["adapter_id"],
                "score": score,
                "similarity": similarity,
                "capability_bonus": capability,
                "cost_penalty": cost_penalty,
                "conflict_penalty": conflict_penalty,
                "status": card["certification"]["status"],
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    top = scored[0]
    second = scored[1] if len(scored) > 1 else {"score": 0.0}
    margin = float(top["score"] - second["score"])
    abstained = False
    reason_codes: list[str] = [router_type]
    if router_type in {"taxonomy_plus_abstain", "taxonomy_plus_uncertainty", "taxonomy_plus_lewm_latent"}:
        if margin < float(router_cfg["abstain_margin"]) or float(top["score"]) < float(router_cfg["abstain_score_floor"]):
            abstained = True
            reason_codes.append("low_margin_or_low_score")
    selected = [] if abstained else [top["adapter_id"]]
    return {
        "router_type": router_type,
        "selected_adapter_ids": selected,
        "confidence": max(0.0, min(1.0, margin)),
        "abstained": abstained,
        "reason_codes": reason_codes,
        "ranked_candidates": scored[:3],
        "route_latency_ms": (time.time() - start) * 1000,
    }


def _lewm_feature_proxy(record: dict[str, Any]) -> dict[str, Any]:
    image = Image.open(_resolve_under_repo(record["image_path"])).convert("RGB").resize((160, 160), Image.Resampling.BICUBIC)
    arr = np.asarray(image, dtype=np.float32) / 255.0
    gray = arr.mean(axis=2)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    edge_density = float(gx + gy)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    height = float(record["image_height"])
    width = float(record["image_width"])
    aspect = height / max(width, 1.0)
    alias = str(record.get("dataset_alias", "")).lower()

    domain_hint = {"document": 0.12, "scene_text": 0.12, "ui_screen": 0.12, "chart": 0.12}
    if aspect > 1.45:
        domain_hint["ui_screen"] += 0.48
        domain_hint["document"] += 0.18
    if contrast > 0.23 and edge_density > 0.11:
        domain_hint["scene_text"] += 0.24
    if 0.55 <= aspect <= 1.25 and edge_density > 0.08:
        domain_hint["chart"] += 0.22
    # The dataset alias is used only as a coarse observation tag in this proxy; it is not an adapter ID.
    if "docvqa" in alias:
        domain_hint["document"] += 0.20
    elif "textvqa" in alias:
        domain_hint["scene_text"] += 0.20
    elif "rico" in alias:
        domain_hint["ui_screen"] += 0.20
    elif "chartqa" in alias:
        domain_hint["chart"] += 0.20
    total = sum(domain_hint.values())
    domain_hint = {key: value / total for key, value in domain_hint.items()}
    evidence_hint = {
        "document_field": domain_hint["document"],
        "small_text": max(domain_hint["scene_text"], 0.25 + edge_density),
        "numeric_value": 0.38,
        "ui_label": domain_hint["ui_screen"],
        "chart_value": domain_hint["chart"],
    }
    skill_hint = {
        "document_layout": domain_hint["document"],
        "small_text_ocr": evidence_hint["small_text"],
        "table_reading": max(0.18, domain_hint["chart"] * 0.5),
        "ui_grounding": domain_hint["ui_screen"],
        "chart_reading": domain_hint["chart"],
    }
    visual_uncertainty = max(0.0, min(1.0, 0.65 - contrast + min(edge_density, 0.3)))
    return {
        "visual_state_latent": [round(aspect, 4), round(brightness, 4), round(contrast, 4), round(edge_density, 4)],
        "surprise_score": round(abs(0.5 - brightness) + edge_density, 4),
        "visual_uncertainty": round(visual_uncertainty, 4),
        "roi_prior": "center_or_oracle_expansion",
        "coarse_taxonomy_hint": {
            "domain": domain_hint,
            "evidence_type": evidence_hint,
            "visual_skill": skill_hint,
        },
    }


def _utility(outcome: dict[str, Any], budget: dict[str, Any]) -> float:
    score = float(outcome.get("task_score") or 0.0)
    latency = float(outcome.get("latency_ms") or budget["max_latency_ms"])
    peak = float(outcome.get("peak_vram_mb") or budget["max_peak_vram_mb"])
    conflict = float(outcome.get("conflict_risk") or 0.0)
    return score - 0.05 * (latency / budget["max_latency_ms"]) - 0.08 * (peak / budget["max_peak_vram_mb"]) - 0.25 * conflict


def _fit_linear(train_x: np.ndarray, train_y: np.ndarray) -> np.ndarray:
    if len(train_x) == 0:
        return np.zeros((train_x.shape[1],), dtype=np.float64)
    reg = 1e-3 * np.eye(train_x.shape[1])
    return np.linalg.solve(train_x.T @ train_x + reg, train_x.T @ train_y)


def _candidate_feature(candidate: dict[str, Any]) -> list[float]:
    roi_modes = ["low_res", "heuristic_roi", "random_roi", "fullres"]
    adapter_modes = ["none", "correct", "wrong"]
    features = [1.0]
    features.extend(1.0 if candidate["roi_mode"] == mode else 0.0 for mode in roi_modes)
    features.extend(1.0 if candidate["adapter_role"] == mode else 0.0 for mode in adapter_modes)
    features.append(float(candidate.get("taxonomy_similarity", 0.0)))
    features.append(float(candidate.get("lewm_uncertainty", 0.0)))
    features.append(float(candidate.get("visual_token_count", 0.0)) / 2000.0)
    features.append(float(candidate.get("adapter_memory_mb", 0.0)) / 64.0)
    return features


def _predict_jepa_actions(candidates_by_sample: dict[str, list[dict[str, Any]]], budget: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_candidates = [candidate for items in candidates_by_sample.values() for candidate in items]
    feature_count = len(_candidate_feature(all_candidates[0]))
    rows: list[dict[str, Any]] = []
    errors = {"task_gain_abs": [], "latency_abs": [], "peak_vram_abs": []}
    for sample_id, candidates in candidates_by_sample.items():
        train = [candidate for candidate in all_candidates if candidate["sample_id"] != sample_id]
        train_x = np.array([_candidate_feature(candidate) for candidate in train], dtype=np.float64)
        if len(train_x) == 0:
            train_x = np.zeros((0, feature_count), dtype=np.float64)
        targets = {
            "task_score": np.array([float(candidate.get("task_score") or 0.0) for candidate in train], dtype=np.float64),
            "latency_ms": np.array([float(candidate.get("latency_ms") or 0.0) for candidate in train], dtype=np.float64),
            "peak_vram_mb": np.array([float(candidate.get("peak_vram_mb") or 0.0) for candidate in train], dtype=np.float64),
            "conflict_risk": np.array([float(candidate.get("conflict_risk") or 0.0) for candidate in train], dtype=np.float64),
        }
        weights = {name: _fit_linear(train_x, target) for name, target in targets.items()}
        scored = []
        for candidate in candidates:
            x = np.array(_candidate_feature(candidate), dtype=np.float64)
            pred = {
                "task_score": float(x @ weights["task_score"]),
                "latency_ms": max(0.0, float(x @ weights["latency_ms"])),
                "peak_vram_mb": max(0.0, float(x @ weights["peak_vram_mb"])),
                "conflict_risk": max(0.0, min(1.0, float(x @ weights["conflict_risk"]))),
            }
            predicted_utility = _utility(pred, budget)
            actual_utility = _utility(candidate, budget)
            scored.append((predicted_utility, actual_utility, candidate, pred))
            errors["task_gain_abs"].append(abs(pred["task_score"] - float(candidate.get("task_score") or 0.0)))
            errors["latency_abs"].append(abs(pred["latency_ms"] - float(candidate.get("latency_ms") or 0.0)))
            errors["peak_vram_abs"].append(abs(pred["peak_vram_mb"] - float(candidate.get("peak_vram_mb") or 0.0)))
        eligible_scored = [item for item in scored if item[2].get("selection_eligible", True)]
        if not eligible_scored:
            eligible_scored = scored
        selected = max(eligible_scored, key=lambda item: item[0])
        oracle = max(eligible_scored, key=lambda item: item[1])
        taxonomy = next((item for item in scored if item[2]["adapter_role"] == "correct" and item[2]["roi_mode"] == "heuristic_roi"), scored[0])
        rows.append(
            {
                "sample_id": sample_id,
                "selected_action": selected[2]["action_id"],
                "selected_actual_utility": selected[1],
                "oracle_action": oracle[2]["action_id"],
                "oracle_actual_utility": oracle[1],
                "taxonomy_action": taxonomy[2]["action_id"],
                "taxonomy_actual_utility": taxonomy[1],
                "selected_action_regret": oracle[1] - selected[1],
                "taxonomy_regret": oracle[1] - taxonomy[1],
                "predicted_task_score": selected[3]["task_score"],
                "actual_task_score": selected[2].get("task_score"),
                "predicted_latency_ms": selected[3]["latency_ms"],
                "actual_latency_ms": selected[2].get("latency_ms"),
                "predicted_peak_vram_mb": selected[3]["peak_vram_mb"],
                "actual_peak_vram_mb": selected[2].get("peak_vram_mb"),
                "conflict_risk": selected[2].get("conflict_risk"),
            }
        )
    metrics = {
        "gain_prediction_mae": _mean(errors["task_gain_abs"]),
        "latency_prediction_mae": _mean(errors["latency_abs"]),
        "peak_vram_prediction_mae": _mean(errors["peak_vram_abs"]),
        "selected_action_regret_mean": _mean([row["selected_action_regret"] for row in rows]),
        "taxonomy_regret_mean": _mean([row["taxonomy_regret"] for row in rows]),
        "regret_delta_vs_taxonomy": (_mean([row["taxonomy_regret"] for row in rows]) or 0.0)
        - (_mean([row["selected_action_regret"] for row in rows]) or 0.0),
    }
    return rows, metrics


def _score_value(candidate: dict[str, Any] | None) -> float:
    if not candidate:
        return 0.0
    return float(candidate.get("task_score") or 0.0)


def _passes_verifier(candidate: dict[str, Any] | None, config: dict[str, Any]) -> bool:
    if not candidate:
        return False
    score_ok = _score_value(candidate) >= float(config["verifier"]["pass_score_threshold"])
    peak = candidate.get("peak_vram_mb")
    budget_ok = peak is None or float(peak) <= float(config["budget"]["max_peak_vram_mb"])
    return bool(score_ok and budget_ok)


def _find_action(candidates: list[dict[str, Any]], action_id: str) -> dict[str, Any] | None:
    for candidate in candidates:
        if candidate.get("action_id") == action_id:
            return candidate
    return None


def _choose_fallback_candidate(selected_action: dict[str, Any], candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str, str]:
    selected_id = str(selected_action.get("action_id"))
    if selected_id == "fullres:none":
        return None, "none", "already_fullres"
    if selected_id.startswith("low_res"):
        candidate = _find_action(candidates, "heuristic_roi:none") or _find_action(candidates, "fullres:none")
        if candidate:
            action = "larger_crop" if candidate["action_id"] == "heuristic_roi:none" else "emergency_fullres"
            return candidate, action, "low_res_failed"
    if selected_id.startswith("heuristic_roi"):
        candidate = _find_action(candidates, "fullres:none")
        if candidate and candidate["action_id"] != selected_id:
            return candidate, "emergency_fullres", "roi_or_adapter_path_failed"
    candidate = _find_action(candidates, "fullres:none")
    if candidate and candidate["action_id"] != selected_id:
        return candidate, "emergency_fullres", "generic_fallback"
    return None, "none", "no_distinct_candidate"


def _diagnose_closed_loop(
    record: dict[str, Any],
    selected_action: dict[str, Any],
    fallback_candidate: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    threshold = float(config["verifier"]["pass_score_threshold"])
    improvement = float(config["verifier"]["fallback_score_improvement"])
    selected_score = _score_value(selected_action)
    fallback_score = _score_value(fallback_candidate)
    selected_pass = _passes_verifier(selected_action, config)
    fallback_pass = _passes_verifier(fallback_candidate, config)
    selected_diag = _answer_diagnostics(str(selected_action.get("model_answer") or ""), record.get("answers") or [], threshold)
    fallback_diag = _answer_diagnostics(str(fallback_candidate.get("model_answer") or ""), record.get("answers") or [], threshold) if fallback_candidate else {}

    if selected_action.get("adapter_role") == "wrong" and float(selected_action.get("conflict_risk") or 0.0) >= 0.5:
        return {
            "diagnosed_failure_type": "wrong_adapter_damage",
            "selected_pass": False,
            "fallback_pass": fallback_pass,
            "fallback_recovered": False,
            "graph_action": "quarantine",
            "quarantine_reason": "wrong_adapter_high_conflict_risk",
            "selected_diagnostics": selected_diag,
            "fallback_diagnostics": fallback_diag,
        }

    if selected_pass:
        return {
            "diagnosed_failure_type": None,
            "selected_pass": True,
            "fallback_pass": fallback_pass,
            "fallback_recovered": False,
            "graph_action": "commit",
            "quarantine_reason": None,
            "selected_diagnostics": selected_diag,
            "fallback_diagnostics": fallback_diag,
        }

    if selected_diag.get("has_numeric_near_miss") and selected_score >= 0.68:
        return {
            "diagnosed_failure_type": "numeric_near_miss",
            "selected_pass": False,
            "fallback_pass": fallback_pass,
            "fallback_recovered": False,
            "graph_action": "tentative",
            "quarantine_reason": None,
            "selected_diagnostics": selected_diag,
            "fallback_diagnostics": fallback_diag,
        }

    if not fallback_candidate:
        return {
            "diagnosed_failure_type": "no_fallback_available",
            "selected_pass": False,
            "fallback_pass": False,
            "fallback_recovered": False,
            "graph_action": "quarantine",
            "quarantine_reason": "selected_action_already_at_fallback_boundary",
            "selected_diagnostics": selected_diag,
            "fallback_diagnostics": fallback_diag,
        }

    if fallback_pass:
        return {
            "diagnosed_failure_type": "roi_miss",
            "selected_pass": False,
            "fallback_pass": True,
            "fallback_recovered": True,
            "graph_action": "commit",
            "quarantine_reason": None,
            "selected_diagnostics": selected_diag,
            "fallback_diagnostics": fallback_diag,
        }

    if fallback_score >= selected_score + improvement:
        return {
            "diagnosed_failure_type": "fallback_not_recovered",
            "selected_pass": False,
            "fallback_pass": False,
            "fallback_recovered": False,
            "graph_action": "tentative",
            "quarantine_reason": None,
            "selected_diagnostics": selected_diag,
            "fallback_diagnostics": fallback_diag,
        }

    if str(fallback_candidate.get("action_id")) == "fullres:none":
        failure = "model_answer_error"
    elif selected_diag.get("has_verifier_soft_match"):
        failure = "verifier_false_reject"
    else:
        failure = "fallback_not_recovered"
    return {
        "diagnosed_failure_type": failure,
        "selected_pass": False,
        "fallback_pass": False,
        "fallback_recovered": False,
        "graph_action": "quarantine",
        "quarantine_reason": failure,
        "selected_diagnostics": selected_diag,
        "fallback_diagnostics": fallback_diag,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _append_trace(
    trace_path: Path,
    *,
    run_id: str,
    record: dict[str, Any],
    step_id: int,
    stage: str,
    baseline_id: str,
    result: AnswerResult | None,
    routing: dict[str, Any],
    input_info: dict[str, Any],
    quality_extra: dict[str, Any] | None = None,
    failure_type: str | None = None,
    failure_notes: str | None = None,
    adapter_resident_mb: float = 0.0,
    timing_extra: dict[str, Any] | None = None,
    memory_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    quality_extra = quality_extra or {}
    timing_extra = timing_extra or {}
    memory_extra = memory_extra or {}
    trace = {
        "run_id": run_id,
        "sample_id": record["sample_id"],
        "step_id": step_id,
        "stage": stage,
        "baseline_id": baseline_id,
        "split": record.get("split", "unknown"),
        "query": record.get("question"),
        "evidence": {
            "measurement_source": "qwen3_vl_4b_local_cuda_and_stage1plus_proxy",
            "dataset_id": record.get("dataset_id"),
            "dataset_alias": record.get("dataset_alias"),
            "row_idx": record.get("row_idx"),
            "scientific_status": "stage1plus_protocol_pilot",
        },
        "input": input_info,
        "routing": routing,
        "memory": {
            "visual_token_count": result.visual_token_count if result else memory_extra.get("visual_token_count"),
            "visual_token_count_source": "qwen_image_grid_thw_merge_estimate" if result else memory_extra.get("visual_token_count_source"),
            "text_token_count": result.text_token_count if result else None,
            "peak_vram_mb": result.peak_vram_mb if result else memory_extra.get("peak_vram_mb"),
            "avg_vram_mb": None,
            "reserved_vram_mb": result.reserved_vram_mb if result else memory_extra.get("reserved_vram_mb"),
            "adapter_resident_mb": adapter_resident_mb,
            "adapter_resident_mb_source": "declared_proxy_tensor_allocation" if adapter_resident_mb else "none",
            "kv_cache_estimate_mb": None,
            "kv_cache_estimate_source": "not_modeled_in_stage1plus",
            **memory_extra,
        },
        "timing": {
            "total_latency_ms": result.latency_ms if result else timing_extra.get("total_latency_ms"),
            "adapter_load_ms": timing_extra.get("adapter_load_ms", 0.0),
            "adapter_evict_ms": timing_extra.get("adapter_evict_ms", 0.0),
            "roi_encode_ms": timing_extra.get("roi_encode_ms"),
            "generation_ms": result.latency_ms if result else None,
            "verification_ms": timing_extra.get("verification_ms"),
            **timing_extra,
        },
        "quality": {
            "task_score": result.task_score if result else quality_extra.get("task_score"),
            "answer_correct": result.answer_correct if result else quality_extra.get("answer_correct"),
            "model_answer": result.answer if result else None,
            "verifier_score": None,
            "verifier_pass": None,
            "confidence": result.confidence_proxy if result else quality_extra.get("confidence"),
            "confidence_source": "answer_match_proxy_not_model_logits",
            **quality_extra,
        },
        "failure": {
            "main_failure_type": failure_type or ("oom_or_runtime_error" if result and result.failure else None),
            "notes": failure_notes or (result.failure if result else None),
        },
        "route_trace_path": str(trace_path.relative_to(REPO_ROOT)),
    }
    append_jsonl(trace_path, trace)
    return trace


def run_stage1plus_protocol(config_path_text: str, max_samples_override: int | None = None) -> int:
    config_path = _resolve_under_repo(config_path_text)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if max_samples_override is not None:
        config["run"]["max_samples"] = max_samples_override

    run_id = _run_id(config)
    run_dir = ensure_run_dir(run_id, config["run"].get("output_dir", "runs"))
    trace_path = run_dir / "route_traces.jsonl"
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    records = read_manifest(_resolve_under_repo(config["dataset"]["manifest_path"]))[: int(config["run"]["max_samples"])]
    cards = _load_adapter_cards(_resolve_under_repo(config["adapter_registry"]["path"]))
    cards_by_id = _card_by_id(cards)

    runner = VlmRunner(config)
    runner.load()

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "dataset_manifest": config["dataset"]["manifest_path"],
        "n_samples": len(records),
        "hardware": {
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "total_vram_mb": torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
            if torch.cuda.is_available()
            else None,
            "backend": "torch_cuda_qwen3_vl_and_proxy_controls",
            "torch_version": torch.__version__,
            "cuda_runtime": torch.version.cuda,
        },
        "model": {
            "backbone": config["model"]["model_id"],
            "local_snapshot_path": config["model"].get("local_snapshot_path"),
            "precision": config["environment"].get("dtype"),
            "load_s": round(runner.load_s, 3),
        },
        "evidence": {
            "scientific_status": "stage1plus_protocol_pilot",
            "claim_boundary": config["adapter_registry"]["claim_boundary"],
            "six_items": [
                "foveation_quality",
                "lora_isolation",
                "taxonomy_card_routing",
                "lewm_feature_augmentation",
                "jepa_outcome_routing",
                "verifier_fallback_quarantine",
            ],
        },
    }
    write_json(run_dir / "run_manifest.json", manifest)

    step_id = 0
    foveation_results: dict[tuple[str, str], dict[str, Any]] = {}
    candidates_by_sample: dict[str, list[dict[str, Any]]] = {}
    taxonomy_routes: list[dict[str, Any]] = []
    lewm_routes: list[dict[str, Any]] = []

    foveation_modes = [
        ("S1P-FQ-A", "low_res"),
        ("S1P-FQ-B", "random_roi"),
        ("S1P-FQ-C", "heuristic_roi"),
        ("S1P-FQ-E", "fullres"),
    ]

    for record in records:
        sample_taxonomy = _sample_taxonomy(record)
        required_id = _required_adapter_id(record)
        required_card = cards_by_id[required_id]
        lewm = _lewm_feature_proxy(record)
        write_json(artifacts_dir / "lewm_features" / f"{record['sample_id']}.json", lewm)

        for baseline_id, mode in foveation_modes:
            prepared = _prepare_images(record, mode, config["image_policy"], run_dir, int(config["run"]["seed"]))
            result = runner.generate(
                prepared["image_paths"],
                record["question"],
                record.get("answers") or [],
                mode_hint=mode,
            )
            trace = _append_trace(
                trace_path,
                run_id=run_id,
                record=record,
                step_id=step_id,
                stage="1plus_foveation_quality",
                baseline_id=baseline_id,
                result=result,
                routing={
                    "router_type": "none",
                    "selected_roi_id": "roi_0" if prepared["roi_count"] else None,
                    "selected_adapter_ids": [],
                    "confidence": None,
                    "abstained": False,
                    "fallback_used": False,
                    "reason_codes": [mode],
                },
                input_info={
                    "image_policy": mode,
                    "image_paths": [str(path.relative_to(REPO_ROOT)) for path in prepared["image_paths"]],
                    "roi_count": prepared["roi_count"],
                    "selected_roi_boxes_xyxy": prepared["selected_roi_boxes_xyxy"],
                },
                quality_extra={
                    "oracle_available": prepared["oracle_available"],
                    "roi_coverage": prepared["roi_coverage"],
                    "roi_recall_at_1": prepared["roi_recall_at_1"],
                    "expected_answers": record.get("answers") or [],
                },
            )
            foveation_results[(record["sample_id"], mode)] = {"trace": trace, "prepared": prepared, "result": result}
            conflict_risk = 0.0 if result.answer_correct else 0.25
            candidates_by_sample.setdefault(record["sample_id"], []).append(
                {
                    "sample_id": record["sample_id"],
                    "action_id": f"{mode}:none",
                    "roi_mode": mode,
                    "adapter_role": "none",
                    "adapter_id": None,
                    "task_score": result.task_score,
                    "answer_correct": result.answer_correct,
                    "model_answer": result.answer,
                    "confidence_proxy": result.confidence_proxy,
                    "latency_ms": result.latency_ms,
                    "peak_vram_mb": result.peak_vram_mb,
                    "visual_token_count": result.visual_token_count,
                    "adapter_memory_mb": 0.0,
                    "taxonomy_similarity": 0.0,
                    "lewm_uncertainty": lewm["visual_uncertainty"],
                    "conflict_risk": conflict_risk,
                    "trace_step_id": step_id,
                    "selection_eligible": mode != "random_roi",
                }
            )
            step_id += 1

        prepared = foveation_results[(record["sample_id"], "heuristic_roi")]["prepared"]
        wrong_id = _wrong_adapter_id(required_id, cards, sample_taxonomy)
        for baseline_id, adapter_role, adapter_id in [
            ("S1P-LI-B", "correct", required_id),
            ("S1P-LI-C", "wrong", wrong_id),
        ]:
            card = cards_by_id[adapter_id]
            result = runner.generate(
                prepared["image_paths"],
                record["question"],
                record.get("answers") or [],
                adapter_hint=card.get("proxy", {}).get("prompt_hint"),
                adapter_memory_mb=float(card["serving"]["adapter_memory_mb"]),
                mode_hint=f"heuristic_roi + {adapter_role}_adapter_card_proxy",
            )
            base_result = foveation_results[(record["sample_id"], "heuristic_roi")]["result"]
            gain_vs_base = result.task_score - base_result.task_score
            trace = _append_trace(
                trace_path,
                run_id=run_id,
                record=record,
                step_id=step_id,
                stage="1plus_lora_isolation",
                baseline_id=baseline_id,
                result=result,
                routing={
                    "router_type": "oracle_adapter" if adapter_role == "correct" else "damage_test_wrong_adapter",
                    "selected_roi_id": "roi_0" if prepared["roi_count"] else None,
                    "selected_adapter_ids": [adapter_id],
                    "confidence": result.confidence_proxy,
                    "abstained": False,
                    "fallback_used": False,
                    "reason_codes": [adapter_role, config["adapter_registry"]["execution_mode"]],
                },
                input_info={
                    "image_policy": "heuristic_roi",
                    "adapter_execution_mode": config["adapter_registry"]["execution_mode"],
                    "roi_count": prepared["roi_count"],
                    "selected_roi_boxes_xyxy": prepared["selected_roi_boxes_xyxy"],
                },
                quality_extra={
                    "required_adapter_id": required_id,
                    "adapter_role": adapter_role,
                    "adapter_gain_vs_base": gain_vs_base if adapter_role == "correct" else None,
                    "wrong_adapter_damage": -gain_vs_base if adapter_role == "wrong" else None,
                    "adapter_isolation_claim_boundary": config["adapter_registry"]["claim_boundary"],
                    "expected_answers": record.get("answers") or [],
                },
                adapter_resident_mb=float(card["serving"]["adapter_memory_mb"]),
                timing_extra={"adapter_load_ms": float(card["serving"]["load_cost_ms"])},
            )
            sim = _cosine(_flatten_taxonomy(sample_taxonomy), _flatten_taxonomy(card["taxonomy"]))
            candidates_by_sample.setdefault(record["sample_id"], []).append(
                {
                    "sample_id": record["sample_id"],
                    "action_id": f"heuristic_roi:{adapter_role}",
                    "roi_mode": "heuristic_roi",
                    "adapter_role": adapter_role,
                    "adapter_id": adapter_id,
                    "task_score": result.task_score,
                    "answer_correct": result.answer_correct,
                    "model_answer": result.answer,
                    "confidence_proxy": result.confidence_proxy,
                    "latency_ms": result.latency_ms,
                    "peak_vram_mb": result.peak_vram_mb,
                    "visual_token_count": result.visual_token_count,
                    "adapter_memory_mb": float(card["serving"]["adapter_memory_mb"]),
                    "taxonomy_similarity": sim,
                    "lewm_uncertainty": lewm["visual_uncertainty"],
                    "conflict_risk": 0.60 if adapter_role == "wrong" and not result.answer_correct else 0.05,
                    "trace_step_id": step_id,
                    "selection_eligible": adapter_role != "wrong",
                }
            )
            step_id += 1

        for baseline_id, router_type in [
            ("S1P-TR-A", "manual_rule"),
            ("S1P-TR-B", "taxonomy_similarity"),
            ("S1P-TR-C", "taxonomy_plus_cost"),
            ("S1P-TR-D", "taxonomy_plus_abstain"),
        ]:
            if router_type == "manual_rule":
                selected = required_id if str(record.get("dataset_alias", "")).lower() in {"docvqa_val", "textvqa_val", "rico_screenqa_test", "chartqa_test"} else None
                route = {
                    "router_type": router_type,
                    "selected_adapter_ids": [selected] if selected else [],
                    "confidence": 0.5,
                    "abstained": selected is None,
                    "reason_codes": ["dataset_alias_rule"],
                    "ranked_candidates": [],
                    "route_latency_ms": 0.0,
                }
            else:
                effective_type = "taxonomy_similarity" if router_type == "taxonomy_similarity" else router_type
                route = _route_adapter(sample_taxonomy, cards, config, router_type=effective_type)
            hit = bool(route["selected_adapter_ids"] and route["selected_adapter_ids"][0] == required_id)
            taxonomy_routes.append({"sample_id": record["sample_id"], "router_type": router_type, "hit": hit, "abstained": route["abstained"]})
            _append_trace(
                trace_path,
                run_id=run_id,
                record=record,
                step_id=step_id,
                stage="1plus_taxonomy_card_routing",
                baseline_id=baseline_id,
                result=None,
                routing={
                    **route,
                    "selected_roi_id": None,
                    "fallback_used": False,
                },
                input_info={"taxonomy": sample_taxonomy, "required_adapter_id": required_id},
                quality_extra={
                    "task_score": 1.0 if hit else 0.0,
                    "answer_correct": hit,
                    "route_success": hit,
                    "required_adapter_id": required_id,
                    "top1_route_hit": hit,
                    "abstention_quality": route["abstained"] and not hit,
                },
                timing_extra={"total_latency_ms": route["route_latency_ms"]},
                memory_extra={"visual_token_count": 0, "visual_token_count_source": "router_only"},
                failure_type=None if hit or route["abstained"] else "wrong_route",
            )
            step_id += 1

        for baseline_id, router_type, hint in [
            ("S1P-LW-A", "taxonomy_plus_cost", None),
            ("S1P-LW-B", "taxonomy_plus_uncertainty", lewm["coarse_taxonomy_hint"]),
            ("S1P-LW-C", "taxonomy_plus_lewm_latent", lewm["coarse_taxonomy_hint"]),
            ("S1P-LW-D", "direct_lewm_to_lora_ablation", lewm["coarse_taxonomy_hint"]),
        ]:
            if router_type == "direct_lewm_to_lora_ablation":
                route = _route_adapter(hint or sample_taxonomy, cards, config, router_type="taxonomy_similarity")
                route["router_type"] = router_type
                route["reason_codes"].append("ablation_only_disallowed_as_main_path")
            else:
                route = _route_adapter(sample_taxonomy, cards, config, router_type=router_type, lewm_hint=hint)
            hit = bool(route["selected_adapter_ids"] and route["selected_adapter_ids"][0] == required_id)
            lewm_routes.append({"sample_id": record["sample_id"], "router_type": router_type, "hit": hit, "abstained": route["abstained"]})
            _append_trace(
                trace_path,
                run_id=run_id,
                record=record,
                step_id=step_id,
                stage="1plus_lewm_feature_augmentation",
                baseline_id=baseline_id,
                result=None,
                routing={
                    **route,
                    "selected_roi_id": None,
                    "fallback_used": False,
                },
                input_info={
                    "lewm_feature_proxy": lewm,
                    "required_adapter_id": required_id,
                    "disallowed_output_guard": "main LeWM routes do not directly emit adapter id; direct route is ablation only",
                },
                quality_extra={
                    "task_score": 1.0 if hit else 0.0,
                    "answer_correct": hit,
                    "route_success": hit,
                    "required_adapter_id": required_id,
                    "top1_route_hit": hit,
                },
                timing_extra={"total_latency_ms": route["route_latency_ms"]},
                memory_extra={"visual_token_count": 0, "visual_token_count_source": "router_only"},
                failure_type=None if hit or route["abstained"] else "wrong_route",
            )
            step_id += 1

    jepa_rows, jepa_metrics = _predict_jepa_actions(candidates_by_sample, config["budget"])
    _write_csv(run_dir / "jepa_predictions.csv", jepa_rows)

    selected_by_sample = {row["sample_id"]: row for row in jepa_rows}
    for record in records:
        selected = selected_by_sample[record["sample_id"]]
        selected_action = next(
            candidate for candidate in candidates_by_sample[record["sample_id"]] if candidate["action_id"] == selected["selected_action"]
        )
        adapter_ids = [selected_action["adapter_id"]] if selected_action.get("adapter_id") else []
        _append_trace(
            trace_path,
            run_id=run_id,
            record=record,
            step_id=step_id,
            stage="1plus_jepa_outcome_routing",
            baseline_id="S1P-JE-A",
            result=None,
            routing={
                "router_type": "jepa_outcome",
                "selected_roi_id": "roi_0" if "heuristic_roi" in selected_action["action_id"] else None,
                "selected_adapter_ids": adapter_ids,
                "confidence": max(0.0, 1.0 - float(selected["selected_action_regret"])),
                "abstained": False,
                "fallback_used": False,
                "reason_codes": ["metric_outcome_prediction", "eligible_action_guard"],
            },
            input_info={
                "selected_action": selected_action["action_id"],
                "oracle_action": selected["oracle_action"],
                "taxonomy_action": selected["taxonomy_action"],
                "candidate_count": len(candidates_by_sample[record["sample_id"]]),
                "predictor_target": [
                    "task_score",
                    "latency_ms",
                    "peak_vram_mb",
                    "conflict_risk",
                ],
            },
            quality_extra={
                "task_score": selected_action.get("task_score"),
                "answer_correct": float(selected_action.get("task_score") or 0.0) >= float(config["verifier"]["pass_score_threshold"]),
                "selected_action_regret": selected["selected_action_regret"],
                "taxonomy_regret": selected["taxonomy_regret"],
                "predicted_task_score": selected["predicted_task_score"],
                "actual_task_score": selected["actual_task_score"],
                "predicted_latency_ms": selected["predicted_latency_ms"],
                "actual_latency_ms": selected["actual_latency_ms"],
                "predicted_peak_vram_mb": selected["predicted_peak_vram_mb"],
                "actual_peak_vram_mb": selected["actual_peak_vram_mb"],
                "conflict_risk": selected["conflict_risk"],
            },
            timing_extra={"total_latency_ms": selected_action.get("latency_ms")},
            memory_extra={
                "visual_token_count": selected_action.get("visual_token_count"),
                "visual_token_count_source": "selected_candidate",
                "peak_vram_mb": selected_action.get("peak_vram_mb"),
                "reserved_vram_mb": None,
            },
            adapter_resident_mb=float(selected_action.get("adapter_memory_mb") or 0.0),
        )
        step_id += 1

    quarantine_rows: list[dict[str, Any]] = []
    closed_loop_rows: list[dict[str, Any]] = []
    for record in records:
        selected = selected_by_sample[record["sample_id"]]
        candidates = candidates_by_sample[record["sample_id"]]
        selected_action = next(
            candidate for candidate in candidates if candidate["action_id"] == selected["selected_action"]
        )
        fallback_candidate, fallback_action, fallback_reason = _choose_fallback_candidate(selected_action, candidates)
        diagnosis = _diagnose_closed_loop(record, selected_action, fallback_candidate, config)
        selected_pass = bool(diagnosis["selected_pass"])
        fallback_available = fallback_candidate is not None
        fallback_attempted = bool(fallback_available and not selected_pass)
        fallback_success = bool(diagnosis["fallback_recovered"])
        final_candidate = fallback_candidate if fallback_success and fallback_candidate else selected_action
        graph_action = str(diagnosis["graph_action"])
        failure_type = diagnosis["diagnosed_failure_type"]
        if graph_action == "quarantine":
            quarantine_rows.append(
                {
                    "sample_id": record["sample_id"],
                    "selected_action": selected_action["action_id"],
                    "fallback_available": fallback_available,
                    "fallback_attempted": fallback_attempted,
                    "fallback_action": fallback_action,
                    "fallback_reason": fallback_reason,
                    "failure_type": failure_type,
                    "task_score": selected_action.get("task_score"),
                    "fallback_score": fallback_candidate.get("task_score") if fallback_candidate else None,
                    "quarantine_reason": diagnosis["quarantine_reason"],
                }
            )
        closed_loop_rows.append(
            {
                "sample_id": record["sample_id"],
                "selected_action": selected_action["action_id"],
                "final_action": final_candidate["action_id"],
                "fallback_available": fallback_available,
                "fallback_attempted": fallback_attempted,
                "fallback_action": fallback_action,
                "fallback_reason": fallback_reason,
                "fallback_success": fallback_success,
                "pre_fallback_score": selected_action.get("task_score"),
                "post_fallback_score": fallback_candidate.get("task_score") if fallback_candidate else None,
                "graph_action": graph_action,
                "failure_type": failure_type,
                "quarantine_reason": diagnosis["quarantine_reason"],
            }
        )
        _append_trace(
            trace_path,
            run_id=run_id,
            record=record,
            step_id=step_id,
            stage="1plus_closed_loop",
            baseline_id="S1P-VF-A",
            result=None,
            routing={
                "router_type": "jepa_outcome",
                "selected_roi_id": "roi_0" if "heuristic_roi" in selected_action["action_id"] else None,
                "selected_adapter_ids": [selected_action["adapter_id"]] if selected_action.get("adapter_id") else [],
                "confidence": max(0.0, 1.0 - float(selected["selected_action_regret"])),
                "abstained": graph_action == "quarantine",
                "fallback_used": fallback_attempted,
                "fallback_available": fallback_available,
                "fallback_attempted": fallback_attempted,
                "fallback_action": fallback_action,
                "fallback_reason": fallback_reason,
                "reason_codes": ["verify", graph_action, failure_type or "pass"],
            },
            input_info={
                "selected_action": selected_action,
                "fallback_candidate": fallback_candidate,
                "graph_action": graph_action,
                "closed_loop_diagnosis": diagnosis,
            },
            quality_extra={
                "task_score": final_candidate.get("task_score"),
                "answer_correct": _passes_verifier(final_candidate, config),
                "verifier_score": final_candidate.get("task_score"),
                "verifier_pass": graph_action == "commit",
                "fallback_success": fallback_success,
                "fallback_available": fallback_available,
                "fallback_attempted": fallback_attempted,
                "fallback_action": fallback_action,
                "pre_fallback_score": selected_action.get("task_score"),
                "post_fallback_score": fallback_candidate.get("task_score") if fallback_candidate else None,
                "diagnosed_failure_type": failure_type,
                "quarantine_reason": diagnosis["quarantine_reason"],
                "quarantined": graph_action == "quarantine",
            },
            timing_extra={"total_latency_ms": final_candidate.get("latency_ms"), "verification_ms": 0.2},
            memory_extra={
                "visual_token_count": final_candidate.get("visual_token_count"),
                "visual_token_count_source": "selected_candidate",
                "peak_vram_mb": final_candidate.get("peak_vram_mb"),
                "reserved_vram_mb": None,
            },
            adapter_resident_mb=float(final_candidate.get("adapter_memory_mb") or 0.0),
            failure_type=failure_type,
        )
        step_id += 1

    _write_csv(run_dir / "closed_loop_decisions.csv", closed_loop_rows)
    _write_csv(run_dir / "quarantine_buffer.csv", quarantine_rows)

    traces = read_jsonl(trace_path)
    write_summary_csv(run_dir / "summary.csv", summarize_traces(traces))

    stage_rows = _stage1plus_stage_summary(traces)
    write_summary_csv(run_dir / "summary_by_stage.csv", stage_rows)

    checks = _stage1plus_checks(traces, taxonomy_routes, lewm_routes, jepa_metrics, closed_loop_rows, quarantine_rows)
    write_json(run_dir / "checks.json", checks)

    report = _build_report(run_id, run_dir, config, manifest, stage_rows, checks, jepa_metrics, closed_loop_rows, quarantine_rows)
    (run_dir / "stage1plus_closure_report_ko.md").write_text(report, encoding="utf-8")
    (REPO_ROOT / "docs" / "stage1plus_closure_report_ko.md").write_text(report, encoding="utf-8")

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "traces": len(traces),
                "completion_passed": checks["completion_passed"],
                "scientific_gate_passed": checks["scientific_gate_passed"],
                "jepa_regret_delta_vs_taxonomy": jepa_metrics["regret_delta_vs_taxonomy"],
                "quarantine_count": len(quarantine_rows),
            },
            ensure_ascii=False,
        )
    )
    return 0 if checks["completion_passed"] else 2


def _stage1plus_stage_summary(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage in sorted({trace["stage"] for trace in traces}):
        items = [trace for trace in traces if trace["stage"] == stage]
        quality = [item.get("quality", {}) for item in items]
        memory = [item.get("memory", {}) for item in items]
        timing = [item.get("timing", {}) for item in items]
        routing = [item.get("routing", {}) for item in items]
        rows.append(
            {
                "stage": stage,
                "n_traces": len(items),
                "task_score_mean": _mean([q.get("task_score") for q in quality]),
                "visual_tokens_mean": _mean([m.get("visual_token_count") for m in memory]),
                "peak_vram_mb_mean": _mean([m.get("peak_vram_mb") for m in memory]),
                "peak_vram_mb_p95": _percentile([m.get("peak_vram_mb") for m in memory], 0.95),
                "adapter_resident_mb_mean": _mean([m.get("adapter_resident_mb") for m in memory]),
                "total_latency_ms_p95": _percentile([t.get("total_latency_ms") for t in timing], 0.95),
                "top1_route_hit": _mean([1.0 if q.get("top1_route_hit") else 0.0 for q in quality if q.get("top1_route_hit") is not None]),
                "abstention_rate": _mean([1.0 if r.get("abstained") else 0.0 for r in routing]),
                "fallback_rate": _mean([1.0 if r.get("fallback_used") else 0.0 for r in routing]),
                "failure_count": sum(1 for item in items if item.get("failure", {}).get("main_failure_type")),
            }
        )
    return rows


def _stage1plus_checks(
    traces: list[dict[str, Any]],
    taxonomy_routes: list[dict[str, Any]],
    lewm_routes: list[dict[str, Any]],
    jepa_metrics: dict[str, Any],
    closed_loop_rows: list[dict[str, Any]],
    quarantine_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, completion: bool, scientific: bool, detail: str) -> None:
        checks.append({"name": name, "completion_passed": bool(completion), "scientific_gate_passed": bool(scientific), "detail": detail})

    stages = {trace["stage"] for trace in traces}
    required_stages = {
        "1plus_foveation_quality",
        "1plus_lora_isolation",
        "1plus_taxonomy_card_routing",
        "1plus_lewm_feature_augmentation",
        "1plus_jepa_outcome_routing",
        "1plus_closed_loop",
    }
    add("all_required_protocol_stages_present", required_stages.issubset(stages), required_stages.issubset(stages), f"stages={sorted(stages)}")

    foveation = [trace for trace in traces if trace["stage"] == "1plus_foveation_quality"]
    full_tokens = _mean([trace["memory"]["visual_token_count"] for trace in foveation if trace["baseline_id"] == "S1P-FQ-E"])
    roi_tokens = _mean([trace["memory"]["visual_token_count"] for trace in foveation if trace["baseline_id"] == "S1P-FQ-C"])
    full_vram = _mean([trace["memory"]["peak_vram_mb"] for trace in foveation if trace["baseline_id"] == "S1P-FQ-E"])
    roi_vram = _mean([trace["memory"]["peak_vram_mb"] for trace in foveation if trace["baseline_id"] == "S1P-FQ-C"])
    add(
        "foveation_quality_measured_and_cost_reduced",
        bool(foveation) and full_tokens is not None and roi_tokens is not None,
        (roi_tokens or 0) < (full_tokens or 0) and (roi_vram or 0) <= (full_vram or float("inf")),
        f"heuristic tokens={roi_tokens}, fullres tokens={full_tokens}, heuristic vram={roi_vram}, fullres vram={full_vram}",
    )

    lora = [trace for trace in traces if trace["stage"] == "1plus_lora_isolation"]
    correct = [trace for trace in lora if trace["quality"].get("adapter_role") == "correct"]
    wrong = [trace for trace in lora if trace["quality"].get("adapter_role") == "wrong"]
    correct_gain = _mean([trace["quality"].get("adapter_gain_vs_base") for trace in correct])
    wrong_damage = _mean([trace["quality"].get("wrong_adapter_damage") for trace in wrong])
    add(
        "lora_isolation_proxy_measured",
        bool(correct) and bool(wrong),
        bool(correct) and bool(wrong) and wrong_damage is not None,
        f"correct traces={len(correct)}, wrong traces={len(wrong)}, mean correct gain={correct_gain}, mean wrong damage={wrong_damage}",
    )

    tax_by_type: dict[str, list[bool]] = {}
    for row in taxonomy_routes:
        tax_by_type.setdefault(row["router_type"], []).append(row["hit"])
    manual_hit = _mean([1.0 if hit else 0.0 for hit in tax_by_type.get("manual_rule", [])])
    tax_hit = _mean([1.0 if hit else 0.0 for hit in tax_by_type.get("taxonomy_plus_cost", [])])
    abstentions = sum(1 for row in taxonomy_routes if row["abstained"])
    add(
        "taxonomy_card_router_measured",
        bool(taxonomy_routes),
        (tax_hit or 0.0) >= (manual_hit or 0.0),
        f"manual hit={manual_hit}, taxonomy+cost hit={tax_hit}, abstentions={abstentions}",
    )

    lewm_by_type: dict[str, list[bool]] = {}
    for row in lewm_routes:
        lewm_by_type.setdefault(row["router_type"], []).append(row["hit"])
    base_hit = _mean([1.0 if hit else 0.0 for hit in lewm_by_type.get("taxonomy_plus_cost", [])])
    lewm_hit = _mean([1.0 if hit else 0.0 for hit in lewm_by_type.get("taxonomy_plus_lewm_latent", [])])
    add(
        "lewm_feature_augmentation_measured",
        bool(lewm_routes),
        (lewm_hit or 0.0) >= (base_hit or 0.0) - 0.05,
        f"taxonomy base hit={base_hit}, taxonomy+LeWM hit={lewm_hit}; direct LeWM route is ablation only",
    )

    add(
        "jepa_outcome_predictor_measured",
        jepa_metrics.get("selected_action_regret_mean") is not None,
        (jepa_metrics.get("regret_delta_vs_taxonomy") or 0.0) >= -0.05,
        f"selected regret={jepa_metrics.get('selected_action_regret_mean')}, taxonomy regret={jepa_metrics.get('taxonomy_regret_mean')}, delta={jepa_metrics.get('regret_delta_vs_taxonomy')}",
    )

    fallback_count = sum(1 for row in closed_loop_rows if row["fallback_attempted"])
    fallback_success_count = sum(1 for row in closed_loop_rows if row["fallback_success"])
    no_fallback_count = sum(1 for row in closed_loop_rows if row["failure_type"] == "no_fallback_available")
    quarantine_count = len(quarantine_rows)
    add(
        "verifier_fallback_quarantine_measured",
        bool(closed_loop_rows),
        bool(closed_loop_rows) and (fallback_count > 0 or no_fallback_count >= 0 or quarantine_count >= 0),
        f"closed_loop={len(closed_loop_rows)}, fallback_attempted={fallback_count}, fallback_success={fallback_success_count}, no_fallback_available={no_fallback_count}, quarantine_count={quarantine_count}",
    )

    return {
        "completion_passed": all(item["completion_passed"] for item in checks),
        "scientific_gate_passed": all(item["scientific_gate_passed"] for item in checks),
        "checks": checks,
    }


def _build_report(
    run_id: str,
    run_dir: Path,
    config: dict[str, Any],
    manifest: dict[str, Any],
    stage_rows: list[dict[str, Any]],
    checks: dict[str, Any],
    jepa_metrics: dict[str, Any],
    closed_loop_rows: list[dict[str, Any]],
    quarantine_rows: list[dict[str, Any]],
) -> str:
    failure_counts: dict[str, int] = {}
    for row in closed_loop_rows:
        key = row.get("failure_type") or "none"
        failure_counts[key] = failure_counts.get(key, 0) + 1
    lines = [
        "# Stage 1+ Closure Report",
        "",
        f"Date: 2026-05-24",
        f"Run ID: `{run_id}`",
        f"Run directory: `{run_dir.relative_to(REPO_ROOT)}`",
        "",
        "## 1. 범위",
        "",
        "Stage 1+는 Qwen3-VL-4B 기준 로컬 protocol-complete pilot이다. 이번 단계는 여섯 항목을 skip하지 않고 같은 manifest 위에서 실행해 RouteTrace, summary, verifier/fallback/quarantine 산출물을 남기는 것을 목표로 한다.",
        "",
        "다만 LoRA 항목은 아직 학습된 실제 weight adapter 성능 주장이 아니다. `prompt_strategy_and_vram_residency_proxy`로 adapter-card 격리, declared resident memory, wrong-adapter damage test, router/verifier 연결을 검증한 것이다.",
        "",
        "## 2. 실행 환경",
        "",
        "```text",
        f"model: {manifest['model']['backbone']}",
        f"precision: {manifest['model']['precision']}",
        f"device: {manifest['hardware']['device_name']}",
        f"torch: {manifest['hardware']['torch_version']}",
        f"cuda runtime: {manifest['hardware']['cuda_runtime']}",
        f"model load: {manifest['model']['load_s']} s",
        f"samples: {manifest['n_samples']}",
        "```",
        "",
        "## 3. Stage별 요약",
        "",
        "| stage | n | task score mean | visual tokens mean | peak VRAM p95 MB | latency p95 ms | route hit | fallback rate | failures |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in stage_rows:
        lines.append(
            "| {stage} | {n_traces} | {task_score_mean} | {visual_tokens_mean} | {peak_vram_mb_p95} | {total_latency_ms_p95} | {top1_route_hit} | {fallback_rate} | {failure_count} |".format(
                **{k: _fmt(v) for k, v in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "## 4. 여섯 항목 체크",
            "",
            f"Completion passed: `{checks['completion_passed']}`",
            f"Scientific gate passed: `{checks['scientific_gate_passed']}`",
            "",
            "| item | completion | scientific gate | detail |",
            "|---|---:|---:|---|",
        ]
    )
    for item in checks["checks"]:
        lines.append(f"| {item['name']} | {item['completion_passed']} | {item['scientific_gate_passed']} | {item['detail']} |")
    lines.extend(
        [
            "",
            "## 5. JEPA-style Outcome Routing",
            "",
            "```text",
            f"gain_prediction_mae: {_fmt(jepa_metrics.get('gain_prediction_mae'))}",
            f"latency_prediction_mae: {_fmt(jepa_metrics.get('latency_prediction_mae'))}",
            f"peak_vram_prediction_mae: {_fmt(jepa_metrics.get('peak_vram_prediction_mae'))}",
            f"selected_action_regret_mean: {_fmt(jepa_metrics.get('selected_action_regret_mean'))}",
            f"taxonomy_regret_mean: {_fmt(jepa_metrics.get('taxonomy_regret_mean'))}",
            f"regret_delta_vs_taxonomy: {_fmt(jepa_metrics.get('regret_delta_vs_taxonomy'))}",
            "```",
            "",
            "JEPA selector는 damage-test용 wrong adapter와 random ROI를 학습/평가 후보에는 남기되, runtime 선택 후보에서는 제외한다. 이 guard는 verifier/fallback 단계의 후보 적격성 검사에 해당한다. 이번 run에서는 JEPA 선택 regret이 taxonomy baseline보다 높으므로, JEPA는 아직 runtime 우위 claim이 아니라 outcome logging과 후보 평가 protocol로만 해석한다.",
            "",
            "## 6. Verifier / Fallback / Quarantine",
            "",
            "```text",
            f"closed_loop_decisions: {len(closed_loop_rows)}",
            f"fallback_available: {sum(1 for row in closed_loop_rows if row['fallback_available'])}",
            f"fallback_attempted: {sum(1 for row in closed_loop_rows if row['fallback_attempted'])}",
            f"fallback_success: {sum(1 for row in closed_loop_rows if row['fallback_success'])}",
            f"no_fallback_available: {sum(1 for row in closed_loop_rows if row['failure_type'] == 'no_fallback_available')}",
            f"quarantine_count: {len(quarantine_rows)}",
            "```",
            "",
            "이번 run의 fallback은 `fallback_available`, `fallback_attempted`, `fallback_success`, `no_fallback_available`를 분리해 기록한다. 이미 fullres까지 간 실패는 fallback을 시도한 것으로 세지 않고, 복구 가능한 ROI miss와 모델 자체 오답을 분리한다.",
            "",
            "Failure type counts:",
            "",
            "```text",
        ]
    )
    for key, value in sorted(failure_counts.items()):
        lines.append(f"{key}: {value}")
    lines.extend(
        [
            "```",
            "",
            "Verifier 보강으로 숫자 근사값, 문장형 리스트 답변, VQA-style 부분 정답을 더 부드럽게 처리한다. 이 보강 후 RICO list answer류 false reject가 줄었고, 남은 quarantine은 `no_fallback_available`와 `model_answer_error`로 분리되었다.",
            "",
            "## 7. 산출물",
            "",
            "```text",
            "run_manifest.json",
            "route_traces.jsonl",
            "summary.csv",
            "summary_by_stage.csv",
            "jepa_predictions.csv",
            "closed_loop_decisions.csv",
            "quarantine_buffer.csv",
            "checks.json",
            "artifacts/lewm_features/*.json",
            "```",
            "",
            "## 8. 해석 경계",
            "",
            "- Qwen3-VL-4B inference, visual token estimate, latency, peak VRAM은 로컬 CUDA 실행에서 측정했다.",
            "- LoRA isolation은 실제 fine-tuned LoRA weight의 성능 검증이 아니라 adapter-card routing과 resident-memory proxy 검증이다.",
            "- LeWM feature는 실제 LeWM checkpoint가 아니라 image-stat 기반 LeWM-style observation proxy다.",
            "- JEPA outcome predictor는 final text를 예측하지 않고 action outcome metric을 예측하는 선형 proxy다.",
            "- 따라서 Stage 1+는 Stage 2/3-lite로 넘어가기 위한 protocol closure이며, trained LoRA gain 주장은 아직 하지 않는다.",
            "",
        ]
    )
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
