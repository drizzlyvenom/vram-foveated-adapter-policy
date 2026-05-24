from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_adapter_cards(registry_path: str | Path) -> list[dict[str, Any]]:
    path = Path(registry_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return list(data.get("adapter_cards", []))


def adapter_bank_resident_mb(adapter_cards: list[dict[str, Any]]) -> float:
    total = 0.0
    for card in adapter_cards:
        total += float(card.get("serving", {}).get("adapter_memory_mb") or 0.0)
    return round(total, 3)


def active_adapter_resident_mb(adapter_cards: list[dict[str, Any]], adapter_id: str | None = None) -> float:
    if not adapter_cards:
        return 0.0
    if adapter_id is None:
        return float(adapter_cards[0].get("serving", {}).get("adapter_memory_mb") or 0.0)
    for card in adapter_cards:
        if card.get("adapter_id") == adapter_id:
            return round(float(card.get("serving", {}).get("adapter_memory_mb") or 0.0), 3)
    return 0.0


def lora_switch_latency_ms(adapter_cards: list[dict[str, Any]], adapter_id: str | None = None) -> float | None:
    if not adapter_cards:
        return None
    if adapter_id is None:
        values = [float(card.get("serving", {}).get("estimated_latency_ms") or 0.0) for card in adapter_cards]
        return round(sum(values) / len(values), 3)
    for card in adapter_cards:
        if card.get("adapter_id") == adapter_id:
            return round(float(card.get("serving", {}).get("estimated_latency_ms") or 0.0), 3)
    return None


def select_adapter_for_taxonomy(adapter_cards: list[dict[str, Any]], taxonomy_label: str) -> dict[str, Any] | None:
    if not adapter_cards:
        return None
    best_card = None
    best_score = -1.0
    for card in adapter_cards:
        domain = card.get("taxonomy", {}).get("domain", {})
        score = float(domain.get(taxonomy_label, 0.0))
        if score > best_score:
            best_card = card
            best_score = score
    return best_card or adapter_cards[0]
