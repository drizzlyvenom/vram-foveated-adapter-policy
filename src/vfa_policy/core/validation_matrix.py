from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import pstdev
from typing import Any, Iterable

from vfa_policy.core.memory_accounting import mean_numeric, p95_numeric


MODEL_MODE_BY_AXIS = {
    "M0_shared_backbone_only": "shared_backbone_only",
    "M1_multi_specialist_baseline": "multi_specialist_estimate",
    "M2_shared_backbone_oracle_lora": "shared_backbone_oracle_lora",
    "M3_shared_backbone_taxonomy_lora": "shared_backbone_taxonomy_lora",
    "M4_hydralora_estimate": "shared_backbone_hydralora_estimate",
}

VISUAL_POLICY_BY_AXIS = {
    "V0_full_fixed_image": "full_image",
    "V1_low_res_only": "low_res_only",
    "V2_foveater_roi": "foveater_roi",
    "V3_oracle_roi": "oracle_roi",
    "V4_foveater_roi_controlled_fallback": "foveater_roi_controlled_fallback",
}

DEFAULT_CELLS = [
    ("C0", "M0_shared_backbone_only", "V0_full_fixed_image"),
    ("C1", "M0_shared_backbone_only", "V2_foveater_roi"),
    ("C2", "M2_shared_backbone_oracle_lora", "V0_full_fixed_image"),
    ("C3", "M3_shared_backbone_taxonomy_lora", "V0_full_fixed_image"),
    ("C4", "M3_shared_backbone_taxonomy_lora", "V2_foveater_roi"),
    ("C5", "M3_shared_backbone_taxonomy_lora", "V3_oracle_roi"),
]


@dataclass(frozen=True)
class MatrixCell:
    id: str
    model_axis: str
    visual_axis: str

    @property
    def model_residency_mode(self) -> str:
        return MODEL_MODE_BY_AXIS.get(self.model_axis, self.model_axis)

    @property
    def visual_policy(self) -> str:
        return VISUAL_POLICY_BY_AXIS.get(self.visual_axis, self.visual_axis)

    def to_dict(self) -> dict[str, str]:
        row = asdict(self)
        row["model_residency_mode"] = self.model_residency_mode
        row["visual_policy"] = self.visual_policy
        return row


SUMMARY_COLUMNS = [
    "run_id",
    "stage",
    "matrix_cell",
    "model_residency_mode",
    "visual_policy",
    "n_samples",
    "task_score_mean",
    "task_score_std",
    "normal_path_peak_mb_mean",
    "controlled_fallback_peak_mb_mean",
    "emergency_peak_mb_mean",
    "base_after_load_allocated_mb_mean",
    "adapter_bank_resident_mb_mean",
    "visual_incremental_peak_mb_mean",
    "visual_token_count_mean",
    "kv_cache_estimate_mb_mean",
    "prefill_latency_ms_p95",
    "mode_switch_latency_ms_p95",
    "lora_switch_latency_ms_p95",
    "fallback_tier0_rate",
    "fallback_tier1_rate",
    "fallback_tier2_rate",
    "wrong_adapter_damage_rate",
    "quarantine_count",
    "reject_count",
]


def load_matrix_cells(config: dict[str, Any]) -> list[MatrixCell]:
    cells = config.get("combined_matrix", {}).get("cells") or []
    if not cells:
        cells = [{"id": cell_id, "model": model, "visual": visual} for cell_id, model, visual in DEFAULT_CELLS]
    loaded: list[MatrixCell] = []
    for cell in cells:
        loaded.append(
            MatrixCell(
                id=str(cell["id"]),
                model_axis=str(cell["model"]),
                visual_axis=str(cell["visual"]),
            )
        )
    return loaded


def _std(values: Iterable[Any]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if len(clean) < 2:
        return None
    return round(pstdev(clean), 6)


def _rate(items: list[dict[str, Any]], predicate) -> float:
    if not items:
        return 0.0
    return round(sum(1 for item in items if predicate(item)) / len(items), 6)


def summarize_3090_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for trace in traces:
        key = (
            str(trace.get("run_id") or "unknown"),
            str(trace.get("stage") or "R4_combined_two_track_pilot"),
            str(trace.get("matrix_cell") or "unknown"),
        )
        grouped.setdefault(key, []).append(trace)

    rows: list[dict[str, Any]] = []
    for (run_id, stage, matrix_cell), items in sorted(grouped.items()):
        first = items[0]
        memory = [item.get("memory", {}) for item in items]
        visual = [item.get("visual", {}) for item in items]
        quality = [item.get("quality", {}) for item in items]
        residency = [item.get("residency", {}) for item in items]
        routing = [item.get("routing", {}) for item in items]
        fallback = [item.get("fallback", {}) for item in items]
        failure = [item.get("failure", {}) for item in items]

        row = {
            "run_id": run_id,
            "stage": stage,
            "matrix_cell": matrix_cell,
            "model_residency_mode": first.get("model_residency_mode"),
            "visual_policy": first.get("visual_policy"),
            "n_samples": len(items),
            "task_score_mean": mean_numeric([q.get("task_score") for q in quality]),
            "task_score_std": _std(q.get("task_score") for q in quality),
            "normal_path_peak_mb_mean": mean_numeric([m.get("normal_path_peak_mb") for m in memory]),
            "controlled_fallback_peak_mb_mean": mean_numeric([m.get("controlled_fallback_peak_mb") for m in memory]),
            "emergency_peak_mb_mean": mean_numeric([m.get("emergency_fallback_peak_mb") for m in memory]),
            "base_after_load_allocated_mb_mean": mean_numeric(
                [m.get("base_after_load_allocated_mb") for m in memory]
            ),
            "adapter_bank_resident_mb_mean": mean_numeric([m.get("adapter_bank_resident_mb") for m in memory]),
            "visual_incremental_peak_mb_mean": mean_numeric(
                [m.get("visual_incremental_peak_mb") for m in memory]
            ),
            "visual_token_count_mean": mean_numeric([v.get("visual_token_count") for v in visual]),
            "kv_cache_estimate_mb_mean": mean_numeric([v.get("kv_cache_estimate_mb") for v in visual]),
            "prefill_latency_ms_p95": p95_numeric([v.get("prefill_latency_ms") for v in visual]),
            "mode_switch_latency_ms_p95": p95_numeric([r.get("mode_switch_latency_ms") for r in residency]),
            "lora_switch_latency_ms_p95": p95_numeric([r.get("lora_switch_latency_ms") for r in residency]),
            "fallback_tier0_rate": _rate(fallback, lambda row: row.get("fallback_tier") == "tier0_in_budget"),
            "fallback_tier1_rate": _rate(
                fallback, lambda row: row.get("fallback_tier") == "tier1_controlled_expensive"
            ),
            "fallback_tier2_rate": _rate(fallback, lambda row: row.get("fallback_tier") == "tier2_emergency"),
            "wrong_adapter_damage_rate": _rate(
                routing, lambda row: row.get("wrong_adapter_damage") not in (None, False, 0, 0.0)
            ),
            "quarantine_count": sum(1 for row in failure if row.get("terminal_action") == "quarantine"),
            "reject_count": sum(1 for row in failure if row.get("terminal_action") == "reject"),
        }
        rows.append({key: row.get(key) for key in SUMMARY_COLUMNS})
    return rows


def build_gate_report(
    *,
    traces: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
    normal_path_budget_mb: float,
    dry_run: bool,
    allow_promotion: bool = False,
    data_mode: str = "synthetic_probe",
) -> dict[str, Any]:
    cell_ids = {trace.get("matrix_cell") for trace in traces}
    c4 = next((row for row in summary_rows if row.get("matrix_cell") == "C4"), {})
    c3 = next((row for row in summary_rows if row.get("matrix_cell") == "C3"), {})

    completion_gate = all(cell in cell_ids for cell in {"C0", "C1", "C2", "C3", "C4", "C5"})
    measurement_gate = all(
        trace.get("memory", {}).get("base_after_load_allocated_mb") is not None
        and trace.get("memory", {}).get("normal_path_peak_mb") is not None
        and trace.get("visual", {}).get("visual_token_count") is not None
        for trace in traces
    )
    c4_under_budget = (c4.get("normal_path_peak_mb_mean") or float("inf")) < normal_path_budget_mb
    c4_reduces_visual = (c4.get("visual_token_count_mean") or float("inf")) < (
        c3.get("visual_token_count_mean") or 0.0
    )
    has_actual_task_score = all(
        bool(trace.get("quality", {}).get("actual_task_score_available"))
        for trace in traces
    )
    has_actual_adapter = any(
        trace.get("source", {}).get("adapter_execution_mode") in {"actual_peft", "merged_lora"}
        for trace in traces
    )
    has_measured_specialist_baseline = any(
        bool(trace.get("model_residency", {}).get("measured_sequential_swap_available"))
        or bool(trace.get("model_residency", {}).get("measured_joint_residency_available"))
        for trace in traces
    )
    non_synthetic_data = data_mode in {"stage1_smoke_manifest", "real_task_manifest"}
    real_task_data = data_mode == "real_task_manifest"

    resident_track_promotion_gate = bool(
        not dry_run
        and has_actual_adapter
        and has_measured_specialist_baseline
        and allow_promotion
    )
    foveation_track_promotion_gate = bool(
        not dry_run
        and real_task_data
        and has_actual_task_score
        and c4_reduces_visual
        and allow_promotion
    )
    combined_track_promotion_gate = bool(
        resident_track_promotion_gate
        and foveation_track_promotion_gate
        and c4_under_budget
        and allow_promotion
    )

    promotion_gate = combined_track_promotion_gate
    notes = []
    if dry_run:
        notes.append("Dry-run/proxy-only result. Do not claim final performance.")
    if not allow_promotion:
        notes.append("Promotion is disabled until trained LoRA and stronger evidence justify it.")
    if not non_synthetic_data:
        notes.append("Synthetic probe data can support memory smoke, not real task validation.")
    if not has_actual_adapter:
        notes.append("Adapter path is proxy accounting until actual PEFT or merged LoRA weights are evaluated.")
    if not has_measured_specialist_baseline:
        notes.append("Multi-specialist baseline is an estimate until sequential or joint residency is measured.")
    if not has_actual_task_score:
        notes.append("Quality score is synthetic proxy; do not use as task accuracy.")
    if not c4_under_budget:
        notes.append("C4 normal path did not clear the configured normal-path budget.")
    if not c4_reduces_visual:
        notes.append("C4 did not reduce visual tokens versus C3.")

    return {
        "completion_gate": completion_gate,
        "measurement_gate": measurement_gate,
        "promotion_gate": promotion_gate,
        "promotion_notes": notes,
        "checks": {
            "required_cells_present": sorted(cell_ids),
            "c4_under_normal_path_budget": c4_under_budget,
            "c4_visual_tokens_less_than_c3": c4_reduces_visual,
            "has_actual_adapter_execution": has_actual_adapter,
            "has_actual_task_score": has_actual_task_score,
            "has_measured_specialist_baseline": has_measured_specialist_baseline,
            "data_mode": data_mode,
            "normal_path_budget_mb": normal_path_budget_mb,
        },
        "track_promotion_gates": {
            "resident_track_promotion_gate": resident_track_promotion_gate,
            "foveation_track_promotion_gate": foveation_track_promotion_gate,
            "combined_track_promotion_gate": combined_track_promotion_gate,
        },
    }
