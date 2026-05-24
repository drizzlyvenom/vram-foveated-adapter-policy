from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .schemas import RouteTrace


def _parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> int | None:
    parsed = _parse_float(value)
    if parsed is None:
        return None
    return int(parsed)


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _parse_resolution(value: str | None) -> list[int] | None:
    if not value:
        return None
    text = str(value).lower().replace(" ", "")
    if "x" not in text:
        return None
    left, right = text.split("x", 1)
    try:
        return [int(left), int(right)]
    except ValueError:
        return None


def _source_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_stage(config: dict[str, Any], run_id: str, repo_root: Path | None = None) -> list[dict[str, Any]]:
    repo_root = repo_root or Path.cwd()
    source_cfg = config.get("source", {})
    source_path = repo_root / source_cfg.get("summary_csv", "")
    allow_missing = bool(source_cfg.get("allow_missing_source", False))

    if not source_path.exists():
        if allow_missing:
            return []
        raise FileNotFoundError(f"Stage 0 CostSim source not found: {source_path}")

    rows = _source_rows(source_path)
    stage_cfg = config["stages"][0]
    stage_id = stage_cfg.get("stage_id", "0_3090_costsim_replay")
    split = config.get("dataset", {}).get("split", "costsim_prior")
    measurement_source = source_cfg.get("measurement_source", "cost_model_3090")
    preserve_source_columns = bool(config.get("logging", {}).get("preserve_source_columns", True))

    baseline_map = {
        baseline["source_baseline"]: baseline
        for baseline in stage_cfg.get("baselines", [])
        if baseline.get("source_baseline")
    }

    traces: list[dict[str, Any]] = []
    step_id_by_baseline: dict[str, int] = {}

    for source_row in rows:
        source_baseline = source_row.get("baseline")
        baseline_cfg = baseline_map.get(source_baseline)
        if baseline_cfg is None:
            continue

        baseline_id = baseline_cfg["baseline_id"]
        step_id = step_id_by_baseline.get(baseline_id, 0)
        step_id_by_baseline[baseline_id] = step_id + 1

        source_run_id = source_row.get("run_id") or f"{source_baseline}-{step_id:05d}"
        roi_count = _parse_int(source_row.get("roi_count_effective")) or 0
        policy_trace = source_row.get("policy_trace")
        reason_codes = [] if not policy_trace or policy_trace == "n/a" else [policy_trace]

        evidence: dict[str, Any] = {
            "measurement_source": measurement_source,
            "source_run_id": source_run_id,
            "source_baseline": source_baseline,
            "source_model_profile": source_row.get("model_profile"),
            "source_model_name": source_row.get("model_name"),
            "scientific_status": "feasibility_prior",
            "policy_trace": policy_trace,
        }
        if preserve_source_columns:
            evidence["source_metrics"] = dict(source_row)

        trace = RouteTrace(
            run_id=run_id,
            sample_id=source_run_id,
            step_id=step_id,
            stage=stage_id,
            baseline_id=baseline_id,
            split=split,
            query=f"CostSim replay for {source_baseline}",
            evidence=evidence,
            input={
                "global_resolution": _parse_resolution(source_row.get("global_res")),
                "full_resolution": _parse_resolution(source_row.get("full_res")),
                "roi_resolution": _parse_resolution(source_row.get("roi_res")),
                "roi_count": roi_count,
                "roi_mode": baseline_cfg.get("roi_mode"),
            },
            routing={
                "router_type": baseline_cfg.get("adapter_mode", "none"),
                "selected_roi_id": None,
                "selected_adapter_ids": [],
                "confidence": None,
                "abstained": False,
                "fallback_used": False,
                "reason_codes": reason_codes,
                "active_top_k_requested": _parse_int(source_row.get("active_top_k_requested")),
                "active_top_k_effective": _parse_int(source_row.get("active_top_k_effective")),
                "load_count": _parse_int(source_row.get("load_count")) or 0,
                "evict_count": _parse_int(source_row.get("evict_count")) or 0,
                "hold_count": _parse_int(source_row.get("hold_count")) or 0,
            },
            memory={
                "visual_token_count": _parse_int(source_row.get("visual_tokens")),
                "visual_token_count_source": "costsim_patch_count",
                "visual_memory_mb": _parse_float(source_row.get("visual_memory_mb")),
                "peak_vram_mb": _parse_float(source_row.get("estimated_peak_memory_mb")),
                "avg_vram_mb": None,
                "reserved_vram_mb": _parse_float(source_row.get("reserve_target_mb")),
                "adapter_resident_mb": _parse_float(source_row.get("resident_adapter_memory_mb")),
                "temporary_load_buffer_mb": _parse_float(source_row.get("temporary_load_buffer_mb")),
                "kv_cache_estimate_mb": None,
                "kv_cache_estimate_source": "not_modeled_in_stage0_costsim",
                "reserve_pass": _parse_bool(source_row.get("reserve_pass")),
                "reserve_headroom_mb": _parse_float(source_row.get("reserve_headroom_mb")),
                "base_model_memory_mb": _parse_float(source_row.get("base_model_memory_mb")),
            },
            timing={
                "total_latency_ms": _parse_float(source_row.get("latency_proxy_ms")),
                "latency_source": "costsim_proxy",
                "global_encode_ms": None,
                "roi_encode_ms": None,
                "adapter_load_ms": None,
                "adapter_evict_ms": None,
                "generation_ms": None,
                "verification_ms": None,
            },
            quality={
                "task_score": None,
                "answer_correct": None,
                "verifier_score": None,
                "verifier_pass": None,
                "confidence": None,
            },
            failure={
                "main_failure_type": None,
                "notes": None,
            },
        ).to_dict()
        traces.append(trace)

    configured = set(baseline_map)
    found = {trace["evidence"]["source_baseline"] for trace in traces}
    missing = sorted(configured - found)
    if missing:
        raise ValueError(f"No CostSim rows found for configured source baselines: {missing}")

    return traces
