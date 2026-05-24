from __future__ import annotations

from typing import Any

from vfa_policy.core.memory_accounting import compute_resident_saving, estimate_multi_specialist_residency


def specialist_count(config: dict[str, Any]) -> int:
    models = (
        config.get("model_residency_axis", {})
        .get("M1_multi_specialist_baseline", {})
        .get("specialist_models", [])
    )
    return len(models)


def estimate_specialist_baseline(
    *,
    config: dict[str, Any],
    shared_backbone_after_load_mb: float,
    shared_plus_lora_resident_mb: float,
    default_model_swap_latency_ms: float = 4000.0,
) -> dict[str, Any]:
    count = specialist_count(config)
    estimate = estimate_multi_specialist_residency(shared_backbone_after_load_mb, count)
    return {
        "specialist_model_count": count,
        "per_model_after_load_allocated_mb": shared_backbone_after_load_mb,
        "multi_specialist_resident_estimate_mb": estimate,
        "fits_in_24gb": bool(estimate is not None and estimate <= config.get("hardware", {}).get("vram_budget_mb", 24576)),
        "model_load_latency_ms": default_model_swap_latency_ms,
        "model_swap_latency_ms": default_model_swap_latency_ms,
        "resident_saving_vs_multi_specialist": compute_resident_saving(
            shared_plus_lora_resident_mb,
            estimate,
        ),
    }
