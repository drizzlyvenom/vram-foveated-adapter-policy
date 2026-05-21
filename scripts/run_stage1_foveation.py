from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.logging_utils import append_jsonl, ensure_run_dir, read_jsonl, summarize_traces, write_json, write_summary_csv
from vfa_policy.stage1_profiler import (
    PatchTransformerProfiler,
    count_tokens,
    load_rgb,
    make_segments,
    profile_segments,
    read_manifest,
    roi_plan,
    warmup,
)


def _resolve_under_repo(path_text: str) -> Path:
    path = (REPO_ROOT / path_text).resolve()
    if not path.is_relative_to(REPO_ROOT):
        raise ValueError(f"Refusing to read outside repository: {path_text}")
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


def _dtype(name: str) -> torch.dtype:
    if name == "float16":
        return torch.float16
    if name == "bfloat16":
        return torch.bfloat16
    return torch.float32


def _run_id(config: dict[str, Any]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{config.get('run', {}).get('name', 'stage1_foveation')}"


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


def _aggregate_by_baseline(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for trace in traces:
        grouped.setdefault(trace["baseline_id"], []).append(trace)

    rows = []
    for baseline_id, items in sorted(grouped.items()):
        memory = [item.get("memory", {}) for item in items]
        timing = [item.get("timing", {}) for item in items]
        quality = [item.get("quality", {}) for item in items]
        recall_values = [
            float(q["roi_recall_at_1"])
            for q in quality
            if q.get("roi_recall_at_1") is not None
        ]
        rows.append(
            {
                "baseline_id": baseline_id,
                "n_samples": len(items),
                "visual_tokens_mean": _mean([m.get("visual_token_count") for m in memory]),
                "peak_vram_mb_mean": _mean([m.get("peak_vram_mb") for m in memory]),
                "peak_vram_mb_p95": _percentile([m.get("peak_vram_mb") for m in memory], 0.95),
                "total_latency_ms_p50": _percentile([t.get("total_latency_ms") for t in timing], 0.50),
                "total_latency_ms_p95": _percentile([t.get("total_latency_ms") for t in timing], 0.95),
                "roi_recall_at_1_mean": _mean(recall_values),
                "runtime_failure_count": sum(1 for item in items if item.get("failure", {}).get("main_failure_type")),
            }
        )
    return rows


def _stage1_checks(baseline_rows: list[dict[str, Any]], traces: list[dict[str, Any]]) -> dict[str, Any]:
    by_baseline = {row["baseline_id"]: row for row in baseline_rows}
    full = by_baseline.get("S1-E", {})
    low = by_baseline.get("S1-A", {})
    heuristic = by_baseline.get("S1-C", {})
    random = by_baseline.get("S1-B", {})

    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add(
        "roi_path_reduces_visual_tokens_vs_fullres",
        (heuristic.get("visual_tokens_mean") or 0) < (full.get("visual_tokens_mean") or 0),
        f"S1-C={heuristic.get('visual_tokens_mean')} vs S1-E={full.get('visual_tokens_mean')}",
    )
    add(
        "roi_path_reduces_peak_vram_vs_fullres",
        (heuristic.get("peak_vram_mb_mean") or 0) < (full.get("peak_vram_mb_mean") or 0),
        f"S1-C={heuristic.get('peak_vram_mb_mean')} vs S1-E={full.get('peak_vram_mb_mean')}",
    )
    add(
        "fullres_costs_more_than_lowres",
        (full.get("peak_vram_mb_mean") or 0) > (low.get("peak_vram_mb_mean") or 0),
        f"S1-E={full.get('peak_vram_mb_mean')} vs S1-A={low.get('peak_vram_mb_mean')}",
    )

    def recall(baseline_id: str) -> float | None:
        vals = []
        for trace in traces:
            if trace.get("baseline_id") != baseline_id:
                continue
            quality = trace.get("quality", {})
            value = quality.get("roi_recall_at_1")
            if value is not None:
                vals.append(float(value))
        return sum(vals) / len(vals) if vals else None

    random_recall = recall("S1-B")
    heuristic_recall = recall("S1-C")
    oracle_recall = recall("S1-D")
    if random_recall is not None and heuristic_recall is not None:
        add(
            "heuristic_roi_beats_random_on_bound_subset",
            heuristic_recall >= random_recall,
            f"S1-C recall={heuristic_recall} vs S1-B recall={random_recall}",
        )
    if oracle_recall is not None:
        add(
            "oracle_roi_bound_subset_measured",
            oracle_recall >= 0.99,
            f"S1-D recall={oracle_recall}",
        )

    add(
        "wrong_crop_distraction_measured",
        random_recall is not None,
        f"S1-B bound-subset recall={random_recall}",
    )

    return {"passed": all(item["passed"] for item in checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage1_foveation_smoke.yaml")
    args = parser.parse_args()

    config_path = (REPO_ROOT / args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    profiler_cfg = config["profiler"]
    device = torch.device(profiler_cfg.get("device", "cuda"))
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available.")
    dtype = _dtype(profiler_cfg.get("dtype", "float16"))

    model_cfg = profiler_cfg["model"]
    model = PatchTransformerProfiler(
        patch_size=int(profiler_cfg["patch_size"]),
        embed_dim=int(model_cfg["embed_dim"]),
        depth=int(model_cfg["depth"]),
        heads=int(model_cfg["heads"]),
        mlp_ratio=int(model_cfg["mlp_ratio"]),
    ).to(device=device)
    if dtype in {torch.float16, torch.bfloat16}:
        model = model.to(dtype=dtype)
    model.eval()
    warmup(model, device, dtype, profiler_cfg["low_res"])

    run_id = _run_id(config)
    run_dir = ensure_run_dir(run_id, config.get("run", {}).get("output_dir", "runs"))
    trace_path = run_dir / "route_traces.jsonl"

    manifest_path = _resolve_under_repo(config["dataset"]["manifest_path"])
    records = read_manifest(manifest_path)

    run_manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "dataset_manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "hardware": {
            "device_name": torch.cuda.get_device_name(0) if device.type == "cuda" else str(device),
            "total_vram_mb": torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
            if device.type == "cuda"
            else None,
            "backend": "torch_cuda_patch_transformer" if device.type == "cuda" else "torch_cpu_patch_transformer",
            "torch_version": torch.__version__,
        },
        "model": {
            "backbone": model_cfg["name"],
            "precision": str(dtype).replace("torch.", ""),
            "patch_size": profiler_cfg["patch_size"],
            "embed_dim": model_cfg["embed_dim"],
            "depth": model_cfg["depth"],
            "heads": model_cfg["heads"],
        },
        "evidence": {
            "measurement_source": "real_gpu_patch_transformer_profiler",
            "scientific_status": "stage1_foveation_smoke",
            "claim_boundary": "Measures foveation cost and ROI-bound recall only; does not measure VLM answer accuracy.",
        },
    }
    write_json(run_dir / "run_manifest.json", run_manifest)

    seed = int(config.get("run", {}).get("seed", 42))
    step = 0
    traces: list[dict[str, Any]] = []
    for record in records:
        image = load_rgb(_resolve_under_repo(record["image_path"]))
        for baseline in profiler_cfg["baselines"]:
            if baseline.get("only_if_oracle_available") and not record.get("oracle_boxes_xyxy"):
                continue
            plan = roi_plan(record, baseline["roi_mode"], seed)
            segments = make_segments(
                image,
                plan,
                profiler_cfg["low_res"],
                profiler_cfg["roi_res"],
                int(profiler_cfg["full_res_max_side"]),
                int(profiler_cfg["patch_size"]),
            )
            visual_tokens = count_tokens(model, segments)
            result = profile_segments(model, segments, device, dtype)
            failure = result["failure"]
            trace = {
                "run_id": run_id,
                "sample_id": record["sample_id"],
                "step_id": step,
                "stage": "1_foveation",
                "baseline_id": baseline["baseline_id"],
                "split": record["split"],
                "query": record.get("question"),
                "evidence": {
                    "measurement_source": "real_gpu_patch_transformer_profiler",
                    "dataset_id": record["dataset_id"],
                    "dataset_alias": record["dataset_alias"],
                    "row_idx": record["row_idx"],
                    "scientific_status": "stage1_foveation_smoke",
                    "roi_source": record.get("roi_source"),
                    "answer_count": len(record.get("answers") or []),
                },
                "input": {
                    "global_resolution": profiler_cfg["low_res"],
                    "full_resolution": [segments[0].size[1], segments[0].size[0]] if baseline["roi_mode"] == "fullres" else None,
                    "roi_resolution": profiler_cfg["roi_res"] if plan.boxes_xyxy else None,
                    "roi_count": len(plan.boxes_xyxy),
                    "roi_mode": plan.mode,
                    "segment_count": len(segments),
                    "segment_sizes_hw": [[seg.size[1], seg.size[0]] for seg in segments],
                    "selected_roi_boxes_xyxy": plan.boxes_xyxy,
                },
                "routing": {
                    "router_type": "none",
                    "selected_roi_id": "roi_0" if plan.boxes_xyxy else None,
                    "selected_adapter_ids": [],
                    "confidence": None,
                    "abstained": False,
                    "fallback_used": False,
                    "reason_codes": [plan.mode],
                },
                "memory": {
                    "visual_token_count": visual_tokens,
                    "visual_token_count_source": "patch_transformer_patch_count",
                    "peak_vram_mb": result["peak_vram_mb"],
                    "avg_vram_mb": None,
                    "reserved_vram_mb": result["reserved_vram_mb"],
                    "adapter_resident_mb": 0.0,
                    "kv_cache_estimate_mb": None,
                    "kv_cache_estimate_source": "not_modeled_in_stage1_foveation",
                },
                "timing": {
                    "total_latency_ms": result["latency_ms"],
                    "global_encode_ms": None,
                    "roi_encode_ms": None,
                    "adapter_load_ms": 0.0,
                    "adapter_evict_ms": 0.0,
                    "generation_ms": None,
                    "verification_ms": None,
                },
                "quality": {
                    "task_score": None,
                    "answer_correct": None,
                    "verifier_score": None,
                    "verifier_pass": None,
                    "confidence": None,
                    "oracle_available": plan.oracle_available,
                    "oracle_coverage": plan.oracle_coverage,
                    "roi_recall_at_1": plan.roi_recall_at_1,
                    "output_norm": result["output_norm"],
                },
                "failure": {
                    "main_failure_type": "oom_or_runtime_error" if failure else None,
                    "notes": failure,
                },
                "route_trace_path": str(trace_path.relative_to(REPO_ROOT)),
            }
            append_jsonl(trace_path, trace)
            traces.append(trace)
            step += 1

    summary_rows = summarize_traces(read_jsonl(trace_path))
    write_summary_csv(run_dir / "summary.csv", summary_rows)
    baseline_rows = _aggregate_by_baseline(traces)
    write_summary_csv(run_dir / "summary_by_baseline.csv", baseline_rows)
    checks = _stage1_checks(baseline_rows, traces)
    write_json(run_dir / "checks.json", checks)

    print(json.dumps({"run_dir": str(run_dir), "traces": len(traces), "checks_passed": checks["passed"]}, ensure_ascii=False))
    return 0 if checks["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
