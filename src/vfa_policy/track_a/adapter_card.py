from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .taxonomy import validate_taxonomy


REQUIRED_TOP_LEVEL = {"adapter_id", "base_backbone", "teacher_model", "taxonomy", "training", "structure", "serving", "certification"}


def load_yaml(path: str | Path) -> Any:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def write_yaml(path: str | Path, obj: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding="utf-8")


def validate_adapter_card(card: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - set(card))
    if missing:
        errors.append(f"missing top-level fields: {missing}")
    errors.extend(validate_taxonomy(card.get("taxonomy") or {}))
    training = card.get("training") or {}
    if training.get("label_mask_mode") != "answer_only":
        errors.append("training.label_mask_mode must be answer_only")
    certification = card.get("certification") or {}
    if certification.get("status") not in {"experimental", "certified", "rejected", "quarantined"}:
        errors.append("certification.status must be experimental, certified, rejected, or quarantined")
    return errors


def certification_status(result: dict[str, Any], *, margin_threshold: float = 0.05) -> str:
    scores = result.get("scores") or result
    margin = scores.get("margin_vs_wrong")
    damage = scores.get("wrong_adapter_damage")
    if margin is None:
        return "experimental"
    try:
        margin_value = float(margin)
        damage_value = float(damage if damage is not None else margin_value)
    except (TypeError, ValueError):
        return "experimental"
    if margin_value >= margin_threshold and damage_value >= 0.0:
        return "certified"
    if margin_value <= 0:
        return "rejected"
    return "experimental"


def merge_certification(card: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    merged = dict(card)
    certification = dict(merged.get("certification") or {})
    scores = result.get("scores") or {}
    for field in (
        "base_score",
        "correct_adapter_score",
        "wrong_adapter_score",
        "random_adapter_score",
        "gain_vs_base",
        "margin_vs_wrong",
        "margin_vs_random",
        "wrong_adapter_damage",
    ):
        if field in scores:
            certification[field] = scores[field]
    certification["score_source"] = result.get("score_source", certification.get("score_source", "unknown"))
    certification["status"] = result.get("status") or certification_status(result)
    merged["certification"] = certification
    return merged
