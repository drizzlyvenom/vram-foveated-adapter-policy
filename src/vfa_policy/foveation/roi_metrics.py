from __future__ import annotations

from typing import Any

from vfa_policy.core.memory_accounting import estimate_kv_cache_mb


VISUAL_ESTIMATES = {
    "full_image": {
        "visual_token_count": 609,
        "global_token_count": 0,
        "roi_token_count": 609,
        "roi_count": 0,
        "visual_incremental_peak_mb": 440.0,
        "prefill_latency_ms": 285.0,
        "roi_recall_at_1": None,
        "roi_recall_at_k": None,
        "roi_miss_rate": None,
        "wrong_crop_distraction": False,
    },
    "low_res_only": {
        "visual_token_count": 85,
        "global_token_count": 85,
        "roi_token_count": 0,
        "roi_count": 0,
        "visual_incremental_peak_mb": 95.0,
        "prefill_latency_ms": 85.0,
        "roi_recall_at_1": 0.0,
        "roi_recall_at_k": 0.0,
        "roi_miss_rate": 1.0,
        "wrong_crop_distraction": False,
    },
    "foveater_roi": {
        "visual_token_count": 430,
        "global_token_count": 85,
        "roi_token_count": 345,
        "roi_count": 1,
        "visual_incremental_peak_mb": 310.0,
        "prefill_latency_ms": 210.0,
        "roi_recall_at_1": 0.85,
        "roi_recall_at_k": 0.92,
        "roi_miss_rate": 0.15,
        "wrong_crop_distraction": False,
    },
    "oracle_roi": {
        "visual_token_count": 430,
        "global_token_count": 85,
        "roi_token_count": 345,
        "roi_count": 1,
        "visual_incremental_peak_mb": 300.0,
        "prefill_latency_ms": 205.0,
        "roi_recall_at_1": 1.0,
        "roi_recall_at_k": 1.0,
        "roi_miss_rate": 0.0,
        "wrong_crop_distraction": False,
    },
    "foveater_roi_controlled_fallback": {
        "visual_token_count": 430,
        "global_token_count": 85,
        "roi_token_count": 345,
        "roi_count": 1,
        "visual_incremental_peak_mb": 310.0,
        "prefill_latency_ms": 210.0,
        "roi_recall_at_1": 0.85,
        "roi_recall_at_k": 0.92,
        "roi_miss_rate": 0.15,
        "wrong_crop_distraction": False,
    },
}


def visual_estimate(visual_policy: str, *, full_reference_tokens: int = 609) -> dict[str, Any]:
    estimate = dict(VISUAL_ESTIMATES.get(visual_policy, VISUAL_ESTIMATES["full_image"]))
    estimate["policy"] = visual_policy
    estimate["full_image_visual_token_count_reference"] = full_reference_tokens
    if full_reference_tokens:
        estimate["visual_token_reduction_vs_full"] = round(
            1.0 - (float(estimate["visual_token_count"]) / float(full_reference_tokens)),
            6,
        )
    else:
        estimate["visual_token_reduction_vs_full"] = None
    estimate["kv_cache_estimate_mb"] = estimate_kv_cache_mb(estimate.get("visual_token_count"))
    return estimate
