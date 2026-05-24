from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.consolidation.adapter_residency import (
    active_adapter_resident_mb,
    adapter_bank_resident_mb,
    load_adapter_cards,
    lora_switch_latency_ms,
    select_adapter_for_taxonomy,
)
from vfa_policy.consolidation.specialist_baseline import estimate_specialist_baseline
from vfa_policy.core.memory_accounting import (
    DECODE_INCREMENTAL_PEAK_PROXY_SOURCE,
    compute_resident_saving,
    estimate_multi_specialist_residency,
    record_after_model_load,
    record_peak_memory,
)
from vfa_policy.core.real_measurement import Qwen3VLRealProbe, RealVisualMeasurement
from vfa_policy.core.validation_matrix import (
    build_gate_report,
    load_matrix_cells,
    summarize_3090_traces,
)
from vfa_policy.foveation.roi_metrics import visual_estimate
from vfa_policy.foveation.real_task_manifest import (
    load_task_manifest,
    prepare_manifest_policy_images,
    sample_for_index,
)
from vfa_policy.logging_utils import append_jsonl, ensure_run_dir, write_json, write_summary_csv


TAXONOMY_SEQUENCE = ["document", "scene_text", "ui_screen", "chart"]


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
    name = config.get("run", {}).get("name", "3090_two_track_pilot")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{name}"


def _resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _quality_score(cell_id: str, sample_index: int, *, fallback_executed: bool, wrong_adapter: bool) -> float:
    base_by_cell = {
        "C0": 0.82,
        "C1": 0.79,
        "C2": 0.845,
        "C3": 0.815,
        "C4": 0.805,
        "C5": 0.835,
    }
    wobble = ((sample_index % 5) - 2) * 0.006
    score = base_by_cell.get(cell_id, 0.80) + wobble
    if fallback_executed:
        score += 0.018
    if wrong_adapter:
        score -= 0.055
    return round(max(0.0, min(1.0, score)), 6)


def _fallback_for(cell_id: str, sample_index: int, visual_policy: str) -> dict[str, Any]:
    if visual_policy == "foveater_roi_controlled_fallback":
        return {
            "fallback_tier": "tier1_controlled_expensive",
            "fallback_evaluated": True,
            "fallback_executed": True,
            "fallback_success": True,
            "terminal_reason": "controlled_fallback_cell",
            "visited_actions": ["fullres_same_shared_backbone"],
        }
    if cell_id == "C4" and visual_policy == "foveater_roi" and sample_index % 5 == 0:
        return {
            "fallback_tier": "tier1_controlled_expensive",
            "fallback_evaluated": True,
            "fallback_executed": True,
            "fallback_success": True,
            "terminal_reason": "low_verifier_score",
            "visited_actions": ["fullres_same_shared_backbone"],
        }
    if visual_policy == "foveater_roi" and sample_index % 10 == 0:
        return {
            "fallback_tier": "tier0_in_budget",
            "fallback_evaluated": True,
            "fallback_executed": True,
            "fallback_success": True,
            "terminal_reason": "roi_uncertainty",
            "visited_actions": ["larger_roi"],
        }
    if cell_id == "C4" and sample_index % 17 == 0:
        return {
            "fallback_tier": "tier1_controlled_expensive",
            "fallback_evaluated": True,
            "fallback_executed": True,
            "fallback_success": True,
            "terminal_reason": "low_verifier_score",
            "visited_actions": ["fullres_same_shared_backbone"],
        }
    return {
        "fallback_tier": "none",
        "fallback_evaluated": False,
        "fallback_executed": False,
        "fallback_success": False,
        "terminal_reason": None,
        "visited_actions": [],
    }


def _selected_adapter(
    *,
    adapter_cards: list[dict[str, Any]],
    taxonomy_label: str,
    model_axis: str,
    sample_index: int,
) -> tuple[dict[str, Any] | None, bool]:
    if model_axis == "M0_shared_backbone_only":
        return None, False
    if model_axis == "M2_shared_backbone_oracle_lora":
        return select_adapter_for_taxonomy(adapter_cards, taxonomy_label), True
    if model_axis == "M3_shared_backbone_taxonomy_lora" and sample_index % 13 == 0:
        wrong_label = TAXONOMY_SEQUENCE[(TAXONOMY_SEQUENCE.index(taxonomy_label) + 1) % len(TAXONOMY_SEQUENCE)]
        return select_adapter_for_taxonomy(adapter_cards, wrong_label), False
    return select_adapter_for_taxonomy(adapter_cards, taxonomy_label), True


def _prompt_for(taxonomy_label: str, visual_policy: str) -> str:
    return (
        "You are running a short RTX 3090 memory-accounting probe. "
        f"Inspect the {visual_policy} image evidence for the {taxonomy_label} route. "
        "Answer with one concise phrase naming the visible probe labels."
    )


def _prompt_for_sample(task_sample: dict[str, Any] | None, taxonomy_label: str, visual_policy: str) -> str:
    if task_sample and task_sample.get("prompt"):
        return str(task_sample["prompt"])
    return _prompt_for(taxonomy_label, visual_policy)


def _real_visual_measurement(
    *,
    real_probe: Qwen3VLRealProbe | None,
    cache: dict[tuple[str, int], RealVisualMeasurement],
    visual_policy: str,
    sample_index: int,
    taxonomy_label: str,
    max_new_tokens: int,
    task_sample: dict[str, Any] | None = None,
    image_paths: list[Path] | None = None,
) -> RealVisualMeasurement | None:
    if real_probe is None:
        return None
    sample_key = str(task_sample.get("sample_id")) if task_sample else f"sample_{sample_index:04d}"
    key = (visual_policy, sample_index, sample_key)
    if key not in cache:
        cache[key] = real_probe.measure_visual_policy(
            visual_policy=visual_policy,
            prompt=_prompt_for_sample(task_sample, taxonomy_label, visual_policy),
            max_new_tokens=max_new_tokens,
            image_paths_override=image_paths,
        )
    return cache[key]


def _data_mode(config: dict[str, Any]) -> str:
    return str(config.get("data", {}).get("mode") or "synthetic_probe")


def _roi_source(config: dict[str, Any], *, dry_run: bool) -> str:
    configured = config.get("data", {}).get("roi_source")
    if configured:
        return str(configured)
    return "dry_run_estimate" if dry_run else "synthetic_probe"


def _adapter_execution_mode(config: dict[str, Any], selected_adapter_id: str | None) -> str:
    if not selected_adapter_id:
        return "shared_backbone_only"
    return str(config.get("adapter_bank", {}).get("execution_mode") or "proxy_card_accounting")


def _specialist_baseline_config(config: dict[str, Any]) -> dict[str, Any]:
    return dict(config.get("model_residency_axis", {}).get("M1_multi_specialist_baseline", {}))


def _task_validation_level(data_mode: str, actual_task_score_available: bool) -> str:
    if data_mode == "real_task_manifest":
        return "real_task_validation" if actual_task_score_available else "real_task_image_smoke"
    if data_mode == "stage1_smoke_manifest":
        return "stage1_image_smoke"
    return "smoke_or_proxy"


def _trace_for_cell(
    *,
    run_id: str,
    sample_index: int,
    cell,
    config: dict[str, Any],
    adapter_cards: list[dict[str, Any]],
    after_load,
    multi_specialist_estimate_mb: float | None,
    real_probe: Qwen3VLRealProbe | None = None,
    real_measurement_cache: dict[tuple[str, int, str], RealVisualMeasurement] | None = None,
    task_sample: dict[str, Any] | None = None,
    max_new_tokens: int = 4,
) -> dict[str, Any]:
    taxonomy_label = (
        str(task_sample.get("taxonomy_label"))
        if task_sample and task_sample.get("taxonomy_label")
        else TAXONOMY_SEQUENCE[sample_index % len(TAXONOMY_SEQUENCE)]
    )
    selected_adapter, top1_hit = _selected_adapter(
        adapter_cards=adapter_cards,
        taxonomy_label=taxonomy_label,
        model_axis=cell.model_axis,
        sample_index=sample_index,
    )
    selected_adapter_id = selected_adapter.get("adapter_id") if selected_adapter else None
    uses_lora_bank = cell.model_axis in {
        "M2_shared_backbone_oracle_lora",
        "M3_shared_backbone_taxonomy_lora",
        "M4_hydralora_estimate",
    }
    dry_run = real_probe is None
    data_mode = _data_mode(config)
    roi_source = _roi_source(config, dry_run=dry_run)
    adapter_execution_mode = _adapter_execution_mode(config, selected_adapter_id)
    specialist_baseline = _specialist_baseline_config(config)

    bank_mb = adapter_bank_resident_mb(adapter_cards) if uses_lora_bank else 0.0
    active_mb = active_adapter_resident_mb(adapter_cards, selected_adapter_id) if selected_adapter_id else 0.0
    lora_switch_ms = lora_switch_latency_ms(adapter_cards, selected_adapter_id) if selected_adapter_id else None
    real_measurement_cache = real_measurement_cache if real_measurement_cache is not None else {}
    image_paths_override = None
    if task_sample and real_probe:
        image_paths_override, roi_source = prepare_manifest_policy_images(
            sample=task_sample,
            sample_index=sample_index,
            visual_policy=cell.visual_policy,
            run_dir=real_probe.run_dir,
            repo_root=REPO_ROOT,
        )
    real_measurement = _real_visual_measurement(
        real_probe=real_probe,
        cache=real_measurement_cache,
        visual_policy=cell.visual_policy,
        sample_index=sample_index,
        taxonomy_label=taxonomy_label,
        max_new_tokens=max_new_tokens,
        task_sample=task_sample,
        image_paths=image_paths_override,
    )
    visual = dict(real_measurement.visual) if real_measurement else visual_estimate(cell.visual_policy)
    if real_measurement:
        full_reference_tokens = None
        if cell.visual_policy == "full_image":
            full_reference_tokens = visual.get("visual_token_count")
        else:
            sample_key = str(task_sample.get("sample_id")) if task_sample else f"sample_{sample_index:04d}"
            full_cached = real_measurement_cache.get(("full_image", sample_index, sample_key))
            if full_cached:
                full_reference_tokens = full_cached.visual.get("visual_token_count")
        if full_reference_tokens:
            visual["full_image_visual_token_count_reference"] = full_reference_tokens
            visual["visual_token_reduction_vs_full"] = round(
                1.0 - (float(visual.get("visual_token_count") or 0.0) / float(full_reference_tokens)),
                6,
            )
    fallback = _fallback_for(cell.id, sample_index, cell.visual_policy)
    if fallback["fallback_tier"] == "tier1_controlled_expensive":
        full_measurement = _real_visual_measurement(
            real_probe=real_probe,
            cache=real_measurement_cache,
            visual_policy="full_image",
            sample_index=sample_index,
            taxonomy_label=taxonomy_label,
            max_new_tokens=max_new_tokens,
            task_sample=task_sample,
            image_paths=(
                prepare_manifest_policy_images(
                    sample=task_sample,
                    sample_index=sample_index,
                    visual_policy="full_image",
                    run_dir=real_probe.run_dir,
                    repo_root=REPO_ROOT,
                )[0]
                if task_sample and real_probe
                else None
            ),
        )
        if full_measurement:
            controlled_extra = max(
                0.0,
                float(full_measurement.memory["visual_incremental_peak_mb"])
                - float(real_measurement.memory["visual_incremental_peak_mb"] if real_measurement else 0.0),
            )
        else:
            controlled_extra = 130.0
    else:
        controlled_extra = None
    emergency_extra = None
    visual_incremental_peak_mb = (
        float(real_measurement.memory["visual_incremental_peak_mb"])
        if real_measurement
        else float(visual["visual_incremental_peak_mb"])
    )
    decode_incremental_peak_mb = (
        float(real_measurement.memory["decode_incremental_peak_mb"]) if real_measurement else 160.0
    )
    generate_extra_peak_over_prefill_mb = (
        float(real_measurement.memory["generate_extra_peak_over_prefill_mb"])
        if real_measurement
        else decode_incremental_peak_mb
    )
    measurement_source = (
        str(real_measurement.memory["measurement_source"]) if real_measurement else "dry_run_config_estimate"
    )
    decode_incremental_peak_source = (
        str(real_measurement.memory.get("decode_incremental_peak_source", DECODE_INCREMENTAL_PEAK_PROXY_SOURCE))
        if real_measurement
        else "dry_run_generate_extra_proxy"
    )
    memory = record_peak_memory(
        after_load=after_load,
        adapter_bank_resident_mb=bank_mb,
        active_adapter_resident_mb=active_mb,
        visual_incremental_peak_mb=visual_incremental_peak_mb,
        decode_incremental_peak_mb=decode_incremental_peak_mb,
        generate_extra_peak_over_prefill_mb=generate_extra_peak_over_prefill_mb,
        controlled_fallback_extra_mb=controlled_extra,
        emergency_fallback_extra_mb=emergency_extra,
        measurement_source=measurement_source,
        decode_incremental_peak_source=decode_incremental_peak_source,
    ).to_dict()
    if real_measurement:
        memory.update(
            {
                "actual_cuda_prefill_peak_mb": real_measurement.memory["prefill_peak_abs_mb"],
                "actual_cuda_generate_peak_mb": real_measurement.memory["generate_peak_abs_mb"],
                "generate_incremental_peak_mb": real_measurement.memory["generate_incremental_peak_mb"],
                "generate_extra_peak_over_prefill_mb": real_measurement.memory[
                    "generate_extra_peak_over_prefill_mb"
                ],
                "prefill_baseline_allocated_mb": real_measurement.memory["prefill_baseline_allocated_mb"],
                "generate_baseline_allocated_mb": real_measurement.memory["generate_baseline_allocated_mb"],
            }
        )

    shared_plus_lora_mb = after_load.allocated_mb + bank_mb
    resident_saving = compute_resident_saving(shared_plus_lora_mb, multi_specialist_estimate_mb)
    wrong_adapter = bool(selected_adapter_id and not top1_hit)
    fallback_executed = bool(fallback["fallback_executed"])
    task_score = _quality_score(cell.id, sample_index, fallback_executed=fallback_executed, wrong_adapter=wrong_adapter)
    verifier_pass = task_score >= 0.78

    failure_type = None
    terminal_action = None
    if wrong_adapter:
        failure_type = "wrong_adapter_damage"
        terminal_action = "quarantine"
    elif not verifier_pass:
        failure_type = "verifier_false_reject"
        terminal_action = "reject"

    model_swap_ms = 4000.0
    model_load_ms = real_probe.load_result.model_load_latency_ms if real_probe else model_swap_ms
    mode_switch_ms = lora_switch_ms if lora_switch_ms is not None else model_swap_ms
    sample_id = (
        str(task_sample.get("sample_id"))
        if task_sample and task_sample.get("sample_id")
        else f"sample_{sample_index:04d}"
    )
    actual_task_score_available = False
    task_validation_level = _task_validation_level(data_mode, actual_task_score_available)
    return {
        "schema_version": "3090.route_trace.v0.1",
        "run_id": run_id,
        "sample_id": sample_id,
        "stage": "R0_R4_cuda_combined_pilot" if real_probe else "R4_combined_two_track_pilot",
        "measurement_mode": "real_cuda" if real_probe else "dry_run_proxy",
        "data_mode": data_mode,
        "matrix_cell": cell.id,
        "model_axis": cell.model_axis,
        "visual_axis": cell.visual_axis,
        "model_residency_mode": cell.model_residency_mode,
        "visual_policy": cell.visual_policy,
        "model_residency": {
            "mode": cell.model_residency_mode,
            "shared_backbone_id": config.get("model", {}).get("shared_backbone_id"),
            "base_after_load_allocated_mb": memory["base_after_load_allocated_mb"],
            "base_after_load_reserved_mb": memory["base_after_load_reserved_mb"],
            "adapter_bank_resident_mb": bank_mb,
            "active_adapter_resident_mb": active_mb,
            "multi_specialist_resident_estimate_mb": multi_specialist_estimate_mb,
            "resident_saving_vs_multi_specialist": resident_saving,
            "model_load_latency_ms": model_load_ms,
            "model_swap_latency_ms": model_swap_ms,
            "lora_switch_latency_ms": lora_switch_ms,
            "adapter_execution_mode": adapter_execution_mode,
            "resident_estimate_method": specialist_baseline.get(
                "resident_estimate_method",
                "same_backbone_after_load_times_count",
            ),
            "measured_sequential_swap_available": bool(
                specialist_baseline.get("measured_sequential_swap_available", False)
            ),
            "measured_joint_residency_available": bool(
                specialist_baseline.get("measured_joint_residency_available", False)
            ),
        },
        "visual_evidence": visual,
        "memory": memory,
        "visual": visual,
        "residency": {
            "model_residency_mode": cell.model_residency_mode,
            "shared_backbone_after_load_mb": after_load.allocated_mb,
            "specialist_model_after_load_mb": after_load.allocated_mb,
            "multi_specialist_resident_estimate_mb": multi_specialist_estimate_mb,
            "fits_in_24gb": bool(
                multi_specialist_estimate_mb is not None
                and multi_specialist_estimate_mb <= config.get("hardware", {}).get("vram_budget_mb", 24576)
            ),
            "model_load_latency_ms": model_load_ms,
            "shared_backbone_load_latency_ms": model_load_ms,
            "model_swap_latency_ms": model_swap_ms,
            "mode_switch_latency_ms": mode_switch_ms,
            "lora_switch_latency_ms": lora_switch_ms,
            "adapter_bank_resident_mb": bank_mb,
            "active_adapter_count": 1 if selected_adapter_id else 0,
            "resident_estimate_method": specialist_baseline.get(
                "resident_estimate_method",
                "same_backbone_after_load_times_count",
            ),
            "measured_sequential_swap_available": bool(
                specialist_baseline.get("measured_sequential_swap_available", False)
            ),
            "measured_joint_residency_available": bool(
                specialist_baseline.get("measured_joint_residency_available", False)
            ),
        },
        "quality": {
            "task_score": task_score,
            "proxy_task_score": task_score,
            "task_score_source": "synthetic_proxy",
            "actual_task_score_available": actual_task_score_available,
            "answer_correct": task_score >= 0.80,
            "score_retention_vs_oracle_lora": round(task_score / 0.845, 6),
            "score_retention_vs_full_specialist": None,
            "score_gain_vs_shared_backbone_only": None,
            "verifier_score": task_score,
            "verifier_pass": verifier_pass,
            "confidence": task_score,
            "confidence_source": "proxy_score_no_ground_truth",
            "answer_preview": real_measurement.answer_text[:500] if real_measurement else None,
        },
        "source": {
            "memory_source": measurement_source,
            "visual_token_source": visual.get("visual_token_count_source"),
            "quality_source": "synthetic_proxy",
            "adapter_memory_source": "adapter_card_estimate",
            "adapter_execution_mode": adapter_execution_mode,
            "roi_source": roi_source,
            "data_mode": data_mode,
            "specialist_baseline_source": specialist_baseline.get(
                "resident_estimate_method",
                "same_backbone_after_load_times_count",
            ),
            "task_validation_level": task_validation_level,
            "source_dataset": task_sample.get("source_dataset") if task_sample else None,
        },
        "routing": {
            "router_type": "none" if selected_adapter_id is None else ("oracle" if cell.model_axis.endswith("oracle_lora") else "taxonomy_card"),
            "selected_adapter_ids": [selected_adapter_id] if selected_adapter_id else [],
            "selected_roi_id": "roi_0" if cell.visual_policy in {"foveater_roi", "oracle_roi"} else None,
            "top1_route_hit": top1_hit if selected_adapter_id else None,
            "top3_route_hit": True if selected_adapter_id else None,
            "abstained": False,
            "wrong_route": wrong_adapter,
            "wrong_adapter_damage": 0.055 if wrong_adapter else None,
            "wrong_adapter_confidence_gain": None,
            "adapter_conflict_rate": selected_adapter.get("certification", {}).get("conflict_rate") if selected_adapter else None,
            "certified_bundle": selected_adapter.get("certification", {}).get("status") if selected_adapter else None,
        },
        "fallback": fallback,
        "failure": {
            "main_failure_type": failure_type,
            "terminal_action": terminal_action,
            "notes": None,
        },
    }


def _combined_result(
    *,
    run_id: str,
    config: dict[str, Any],
    traces: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    resident_baseline: dict[str, Any],
    gates: dict[str, Any],
) -> dict[str, Any]:
    def by_cell(cell_id: str) -> dict[str, Any]:
        return next((row for row in summary_rows if row.get("matrix_cell") == cell_id), {})

    c0 = by_cell("C0")
    c3 = by_cell("C3")
    c4 = by_cell("C4")
    cell_rows = []
    for row in summary_rows:
        cell_rows.append(
            {
                "id": row.get("matrix_cell"),
                "model_axis": next((t.get("model_axis") for t in traces if t.get("matrix_cell") == row.get("matrix_cell")), None),
                "visual_axis": next((t.get("visual_axis") for t in traces if t.get("matrix_cell") == row.get("matrix_cell")), None),
                "n_samples": row.get("n_samples"),
                "task_score_mean": row.get("task_score_mean"),
                "normal_path_peak_mb_mean": row.get("normal_path_peak_mb_mean"),
                "visual_token_count_mean": row.get("visual_token_count_mean"),
            }
        )

    tier0 = sum(1 for trace in traces if trace.get("fallback", {}).get("fallback_tier") == "tier0_in_budget")
    tier1 = sum(1 for trace in traces if trace.get("fallback", {}).get("fallback_tier") == "tier1_controlled_expensive")
    tier2 = sum(1 for trace in traces if trace.get("fallback", {}).get("fallback_tier") == "tier2_emergency")
    total = len(traces) or 1

    return {
        "schema_version": "3090.combined_validation_result.v0.1",
        "run_id": run_id,
        "measurement_mode": "real_cuda" if any(t.get("measurement_mode") == "real_cuda" for t in traces) else "dry_run_proxy",
        "data_mode": _data_mode(config),
        "hardware": {
            "gpu": config.get("hardware", {}).get("target_gpu"),
            "vram_budget_mb": config.get("hardware", {}).get("vram_budget_mb"),
            "normal_path_budget_mb": config.get("hardware", {}).get("normal_path_budget_mb"),
        },
        "claim_boundary": {
            "final_performance_claim": config.get("claim_boundary", {}).get("allow_final_performance_claim", False),
            "trained_lora_gain_claim": config.get("claim_boundary", {}).get("allow_trained_lora_gain_claim", False),
            "production_serving_claim": config.get("claim_boundary", {}).get("allow_production_p99_claim", False),
            "feasibility_claim": config.get("claim_boundary", {}).get("allow_feasibility_claim", True),
        },
        "matrix_cells": cell_rows,
        "resident_summary": {
            "multi_specialist_resident_estimate_mb": resident_baseline.get("multi_specialist_resident_estimate_mb"),
            "resident_estimate_method": resident_baseline.get("resident_estimate_method"),
            "measured_sequential_swap_available": resident_baseline.get("measured_sequential_swap_available"),
            "measured_joint_residency_available": resident_baseline.get("measured_joint_residency_available"),
            "shared_backbone_plus_lora_bank_resident_mb": (
                (c4.get("base_after_load_allocated_mb_mean") or 0.0)
                + (c4.get("adapter_bank_resident_mb_mean") or 0.0)
            ),
            "resident_saving_vs_multi_specialist": resident_baseline.get("resident_saving_vs_multi_specialist"),
            "lora_switch_latency_ms_p95": c4.get("lora_switch_latency_ms_p95"),
            "model_swap_latency_ms_p95": resident_baseline.get("model_swap_latency_ms"),
        },
        "visual_summary": {
            "full_visual_token_count_mean": c0.get("visual_token_count_mean"),
            "foveated_visual_token_count_mean": c4.get("visual_token_count_mean"),
            "roi_source": next((t.get("source", {}).get("roi_source") for t in traces), None),
            "visual_token_reduction_vs_full": (
                round(1.0 - (c4.get("visual_token_count_mean") / c0.get("visual_token_count_mean")), 6)
                if c0.get("visual_token_count_mean") and c4.get("visual_token_count_mean")
                else None
            ),
            "c4_visual_token_reduction_vs_c3": (
                round(1.0 - (c4.get("visual_token_count_mean") / c3.get("visual_token_count_mean")), 6)
                if c3.get("visual_token_count_mean") and c4.get("visual_token_count_mean")
                else None
            ),
            "prefill_latency_reduction_vs_full": (
                round(1.0 - (c4.get("prefill_latency_ms_p95") / c0.get("prefill_latency_ms_p95")), 6)
                if c0.get("prefill_latency_ms_p95") and c4.get("prefill_latency_ms_p95")
                else None
            ),
        },
        "fallback_summary": {
            "tier0_rate": round(tier0 / total, 6),
            "tier1_rate": round(tier1 / total, 6),
            "tier2_rate": round(tier2 / total, 6),
            "normal_path_peak_mb_mean": c4.get("normal_path_peak_mb_mean"),
            "controlled_fallback_peak_mb_mean": c4.get("controlled_fallback_peak_mb_mean"),
            "emergency_peak_mb_mean": c4.get("emergency_peak_mb_mean"),
        },
        "source_summary": {
            "memory_source": next((t.get("source", {}).get("memory_source") for t in traces), None),
            "visual_token_source": next((t.get("source", {}).get("visual_token_source") for t in traces), None),
            "quality_source": "synthetic_proxy",
            "adapter_memory_source": "adapter_card_estimate",
            "adapter_execution_mode": config.get("adapter_bank", {}).get("execution_mode", "proxy_card_accounting"),
            "data_mode": _data_mode(config),
            "roi_source": next((t.get("source", {}).get("roi_source") for t in traces), None),
        },
        "gates": gates,
    }


def _fmt(value: Any, suffix: str = "") -> str:
    if value is None or value == "":
        return "N/A"
    try:
        return f"{float(value):.3f}{suffix}"
    except (TypeError, ValueError):
        return f"{value}{suffix}"


def _write_korean_reports(
    *,
    run_dir: Path,
    combined: dict[str, Any],
    summary_rows: list[dict[str, Any]],
    dry_run: bool,
) -> None:
    def row(cell_id: str) -> dict[str, Any]:
        return next((item for item in summary_rows if item.get("matrix_cell") == cell_id), {})

    c0 = row("C0")
    c4 = row("C4")
    measurement_label = "dry-run/proxy" if dry_run else "real CUDA"
    data_mode = str(combined.get("data_mode") or "synthetic_probe")
    result_summary = f"""# 3090 투트랙 검증 결과 요약

- run_id: `{combined.get("run_id")}`
- measurement mode: `{measurement_label}`
- data mode: `{data_mode}`
- completion_gate: `{combined.get("gates", {}).get("completion_gate")}`
- measurement_gate: `{combined.get("gates", {}).get("measurement_gate")}`
- promotion_gate: `{combined.get("gates", {}).get("promotion_gate")}`

## 핵심 수치

- C0 full-image visual token mean: {_fmt(c0.get("visual_token_count_mean"))}
- C4 foveated visual token mean: {_fmt(c4.get("visual_token_count_mean"))}
- C4 normal path peak mean: {_fmt(c4.get("normal_path_peak_mb_mean"), " MB")}
- C4 controlled fallback peak mean: {_fmt(c4.get("controlled_fallback_peak_mb_mean"), " MB")}
- shared backbone + LoRA bank resident estimate: {_fmt(combined.get("resident_summary", {}).get("shared_backbone_plus_lora_bank_resident_mb"), " MB")}
- multi-specialist resident estimate: {_fmt(combined.get("resident_summary", {}).get("multi_specialist_resident_estimate_mb"), " MB")}

## 해석 경계

이 결과는 RTX 3090 단일 장비에서 memory accounting과 feasibility를 확인하기 위한 파일입니다.
trained LoRA 성능 향상, 최종 benchmark superiority, production p99 serving claim은 주장하지 않습니다.
Foveation은 resident backbone memory가 아니라 visual token, prefill, KV/cache 계열 비용을 줄이는 축으로만 해석합니다.
현재 quality score는 실제 task accuracy가 아니라 synthetic proxy입니다. `data_mode={data_mode}`는 실제 이미지 smoke 여부를 나타내지만, 실제 task score가 없는 run은 final validation으로 승격하지 않습니다.
"""

    short_paper = f"""# 저 VRAM 비전 추론을 위한 공유 백본-어댑터 및 Foveated Evidence 투트랙 검증

## 초록

본 소논문은 RTX 3090 24GB 환경에서 low-VRAM vision inference 설계를 검증하기 위한 두 개의 독립 압축 축을 제안하고, 그 계측 프로토콜을 정리한다. 첫째, 여러 full specialist VLM을 동시에 상주시킬 때의 resident footprint를 하나의 shared VLM backbone과 taxonomy-tagged LoRA adapter bank로 대체한다. 둘째, full high-resolution visual context를 low-resolution global view와 high-resolution ROI glimpse로 나누어 visual evidence 비용을 줄인다. 본 결과는 feasibility/accounting 중심이며, 최종 성능 우월성은 주장하지 않는다.

## 문제 정의

비전 추론 시스템의 VRAM 병목은 하나의 숫자로 합치기 어렵다. 모델 백본이 상주하는 resident memory, 어댑터 bank memory, image evidence로 인한 prefill/activation peak, decode peak, fallback peak가 서로 다른 시점에 발생하기 때문이다. 따라서 본 검증은 `normal_path_peak_mb`, `controlled_fallback_peak_mb`, `emergency_fallback_peak_mb`를 분리해 기록한다.

## 투트랙 설계

Track A는 resident specialist compression이다. 여러 specialist backbone을 동시에 올리는 baseline은 resident estimate와 sequential swap latency로 기록하고, 제안 구조는 shared backbone과 LoRA bank resident estimate로 비교한다.

Track B는 visual evidence compression이다. full image, low-res only, foveated ROI, oracle ROI 경로를 같은 schema로 측정한다. 이 축은 resident backbone memory를 줄인다는 주장이 아니라 visual token count, KV/cache estimate, prefill latency, visual incremental peak를 줄이는지 확인하는 축이다.

## RTX 3090 검증 프로토콜

본 run은 `{measurement_label}` 모드, `{data_mode}` data mode로 실행되었다. 산출물은 `combined_validation_result.json`, `summary.csv`, `route_traces.jsonl`이다. 각 trace는 base-after-load memory, adapter resident estimate, visual incremental peak, generate-extra-over-prefill peak, fallback peak, route/failure label을 포함한다.

## 측정 결과

C0 full-image visual token mean은 {_fmt(c0.get("visual_token_count_mean"))}이고, C4 taxonomy LoRA + foveated ROI visual token mean은 {_fmt(c4.get("visual_token_count_mean"))}이다. C4 normal path peak mean은 {_fmt(c4.get("normal_path_peak_mb_mean"), " MB")}로 기록되었다. shared backbone + LoRA bank resident estimate는 {_fmt(combined.get("resident_summary", {}).get("shared_backbone_plus_lora_bank_resident_mb"), " MB")}이며, multi-specialist resident estimate는 {_fmt(combined.get("resident_summary", {}).get("multi_specialist_resident_estimate_mb"), " MB")}이다. 이 품질 수치는 실제 benchmark score가 아니라 synthetic proxy다.

## 실패 분석

failure label은 wrong adapter damage, ROI miss, fallback tier, reject/quarantine을 분리한다. terminal model error는 quarantine이 아니라 reject 또는 unresolved로 다루며, quarantine은 unsafe adapter, unsafe route, verifier false pass, adapter conflict처럼 구조적 위험이 있는 경우로 제한한다.

## Claim Boundary

본 결과는 RTX 3090에서 accounting이 가능한지, 그리고 두 병목을 분리해 측정할 수 있는지를 보이는 pilot evidence다. trained LoRA weight가 평가되기 전까지 LoRA 성능 향상을 주장하지 않는다. 또한 FoveateR-style ROI는 visual evidence cost 축의 절감으로만 해석하며 resident backbone memory 절감과 혼동하지 않는다.

## 한계와 다음 단계

다음 단계는 실제 trained LoRA weight를 붙인 adapter isolation 평가, 실제 task dataset 기반 ROI miss 분석, 그리고 fallback tier별 latency/peak 반복 측정이다. 이 단계가 닫혀야 성능 claim을 더 넓힐 수 있다.
"""

    (run_dir / "result_summary_ko.md").write_text(result_summary, encoding="utf-8")
    (run_dir / "short_paper_ko.md").write_text(short_paper, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/3090_two_track_pilot.yaml")
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run mode even if config changes later.")
    parser.add_argument("--real-run", action="store_true", help="Load the local Qwen3-VL snapshot and record CUDA memory.")
    parser.add_argument("--data-mode", choices=["synthetic_probe", "stage1_smoke_manifest", "real_task_manifest"])
    parser.add_argument("--manifest", help="JSONL manifest for stage1_smoke_manifest or real_task_manifest mode.")
    parser.add_argument("--max-new-tokens", type=int, default=4, help="Decode tokens used by the real CUDA probe.")
    args = parser.parse_args()
    if args.dry_run and args.real_run:
        parser.error("--dry-run and --real-run are mutually exclusive.")

    config_path = _resolve_repo_path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if args.dry_run:
        config.setdefault("run", {})["dry_run"] = True
    if args.real_run:
        config.setdefault("run", {})["dry_run"] = False
    if args.data_mode:
        config.setdefault("data", {})["mode"] = args.data_mode
    if args.manifest:
        config.setdefault("data", {})["manifest_path"] = args.manifest
    if args.max_samples is not None:
        config.setdefault("run", {})["max_samples"] = args.max_samples

    run_id = _run_id(config)
    run_dir = ensure_run_dir(run_id, config.get("run", {}).get("output_dir", "runs"))
    trace_path = run_dir / "route_traces.jsonl"
    dry_run = bool(config.get("run", {}).get("dry_run", True))
    data_mode = _data_mode(config)
    manifest_samples: list[dict[str, Any]] = []
    if data_mode in {"stage1_smoke_manifest", "real_task_manifest"}:
        manifest_path = config.get("data", {}).get("manifest_path")
        if not manifest_path:
            failure = {
                "run_id": run_id,
                "stage": "manifest_loading",
                "completion_gate": False,
                "measurement_gate": False,
                "promotion_gate": False,
                "error_type": "MissingManifestPath",
                "error_message": f"data.mode={data_mode} requires data.manifest_path or --manifest.",
                "next_action": "Run scripts/prepare_real_task_manifest.py or pass a manifest JSONL path.",
            }
            write_json(run_dir / "manifest_failure.json", failure)
            print(json.dumps({"run_dir": str(run_dir), **failure}, ensure_ascii=False))
            return 2
        try:
            manifest_samples = load_task_manifest(manifest_path, repo_root=REPO_ROOT)
        except Exception as exc:
            failure = {
                "run_id": run_id,
                "stage": "manifest_loading",
                "completion_gate": False,
                "measurement_gate": False,
                "promotion_gate": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "next_action": "Fix manifest paths/schema before running real task smoke.",
            }
            write_json(run_dir / "manifest_failure.json", failure)
            print(json.dumps({"run_dir": str(run_dir), **failure}, ensure_ascii=False))
            return 2

    adapter_registry = _resolve_repo_path(config.get("adapter_bank", {}).get("registry_path", "configs/3090_adapter_cards.yaml"))
    adapter_cards = load_adapter_cards(adapter_registry)
    real_probe: Qwen3VLRealProbe | None = None
    real_probe_load: dict[str, Any] | None = None
    if dry_run:
        after_load = record_after_model_load(measurement_source="dry_run_config_estimate")
    else:
        model_snapshot = _resolve_repo_path(config.get("model", {}).get("local_snapshot_path", ""))
        try:
            real_probe = Qwen3VLRealProbe(
                model_path=model_snapshot,
                dtype_name=str(config.get("model", {}).get("dtype", "float16")),
                run_dir=run_dir,
                max_new_tokens=args.max_new_tokens,
            )
            real_probe_load = real_probe.load_result.to_dict()
            after_load = record_after_model_load(
                allocated_mb=real_probe.load_result.allocated_mb,
                reserved_mb=real_probe.load_result.reserved_mb,
                measurement_source=real_probe.load_result.measurement_source,
            )
        except Exception as exc:
            failure = {
                "run_id": run_id,
                "stage": "R0_real_cuda_memory_accounting",
                "completion_gate": False,
                "measurement_gate": False,
                "promotion_gate": False,
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "next_action": "Fix model loading/profiler/logging before running R1-R5.",
            }
            write_json(run_dir / "r0_failure.json", failure)
            print(json.dumps({"run_dir": str(run_dir), **failure}, ensure_ascii=False))
            return 2
    specialist_count = len(
        config.get("model_residency_axis", {})
        .get("M1_multi_specialist_baseline", {})
        .get("specialist_models", [])
    )
    multi_specialist_estimate_mb = estimate_multi_specialist_residency(
        after_load.allocated_mb,
        specialist_count,
    )
    shared_plus_lora_mb = after_load.allocated_mb + adapter_bank_resident_mb(adapter_cards)
    resident_baseline = estimate_specialist_baseline(
        config=config,
        shared_backbone_after_load_mb=after_load.allocated_mb,
        shared_plus_lora_resident_mb=shared_plus_lora_mb,
    )

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "dry_run": dry_run,
        "data": config.get("data", {}),
        "manifest_sample_count": len(manifest_samples),
        "hardware": config.get("hardware", {}),
        "model": config.get("model", {}),
        "adapter_registry_path": str(adapter_registry.relative_to(REPO_ROOT)),
        "matrix_cells": [cell.to_dict() for cell in load_matrix_cells(config)],
        "claim_boundary": config.get("claim_boundary", {}),
        "scientific_status": "3090_two_track_dry_run_scaffold" if dry_run else "3090_two_track_real_cuda_accounting",
        "real_probe_load": real_probe_load,
    }
    write_json(run_dir / "run_manifest.json", manifest)

    traces: list[dict[str, Any]] = []
    real_measurement_cache: dict[tuple[str, int, str], RealVisualMeasurement] = {}
    max_samples = int(config.get("run", {}).get("max_samples", 20))
    for cell in load_matrix_cells(config):
        for sample_index in range(max_samples):
            task_sample = sample_for_index(manifest_samples, sample_index)
            trace = _trace_for_cell(
                run_id=run_id,
                sample_index=sample_index,
                cell=cell,
                config=config,
                adapter_cards=adapter_cards,
                after_load=after_load,
                multi_specialist_estimate_mb=multi_specialist_estimate_mb,
                real_probe=real_probe,
                real_measurement_cache=real_measurement_cache,
                task_sample=task_sample,
                max_new_tokens=args.max_new_tokens,
            )
            trace["route_trace_path"] = str(trace_path.relative_to(REPO_ROOT))
            traces.append(trace)
            append_jsonl(trace_path, trace)

    summary_rows = summarize_3090_traces(traces)
    write_summary_csv(run_dir / "summary.csv", summary_rows)

    gates = build_gate_report(
        traces=traces,
        summary_rows=summary_rows,
        normal_path_budget_mb=float(config.get("hardware", {}).get("normal_path_budget_mb", 22000)),
        dry_run=dry_run,
        allow_promotion=False,
        data_mode=_data_mode(config),
    )
    write_json(run_dir / "checks.json", gates)

    combined = _combined_result(
        run_id=run_id,
        config=config,
        traces=traces,
        summary_rows=summary_rows,
        resident_baseline=resident_baseline,
        gates=gates,
    )
    write_json(run_dir / "combined_validation_result.json", combined)
    _write_korean_reports(run_dir=run_dir, combined=combined, summary_rows=summary_rows, dry_run=dry_run)

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "traces": len(traces),
                "completion_gate": gates["completion_gate"],
                "measurement_gate": gates["measurement_gate"],
                "promotion_gate": gates["promotion_gate"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if gates["completion_gate"] and gates["measurement_gate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
