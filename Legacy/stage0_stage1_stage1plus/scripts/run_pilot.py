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

from vfa_policy.costsim_replay import run_stage
from vfa_policy.logging_utils import append_jsonl, ensure_run_dir, read_jsonl, summarize_traces, write_json, write_summary_csv


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
    name = config.get("run", {}).get("name", "pilot")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{name}"


def _by_baseline(summary_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["baseline_id"]: row for row in summary_rows}


def _directionality_checks(summary_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = _by_baseline(summary_rows)
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    low = rows.get("S0-A", {})
    full = rows.get("S0-B", {})
    roi = rows.get("S0-C", {})
    independent = rows.get("S0-D", {})
    budget = rows.get("S0-F", {})

    add(
        "full_high_res_has_more_visual_tokens_than_low_res",
        (full.get("visual_tokens_mean") or 0) > (low.get("visual_tokens_mean") or 0),
        f"S0-B={full.get('visual_tokens_mean')} vs S0-A={low.get('visual_tokens_mean')}",
    )
    add(
        "full_high_res_has_more_peak_vram_than_low_res",
        (full.get("peak_vram_mb_mean") or 0) > (low.get("peak_vram_mb_mean") or 0),
        f"S0-B={full.get('peak_vram_mb_mean')} vs S0-A={low.get('peak_vram_mb_mean')}",
    )
    add(
        "foveated_roi_reduces_visual_tokens_vs_full_high_res",
        (roi.get("visual_tokens_mean") or 0) < (full.get("visual_tokens_mean") or 0),
        f"S0-C={roi.get('visual_tokens_mean')} vs S0-B={full.get('visual_tokens_mean')}",
    )
    add(
        "budget_policy_reduces_adapter_residency_vs_independent_bank",
        (budget.get("adapter_resident_mb_mean") or 0) < (independent.get("adapter_resident_mb_mean") or 0),
        f"S0-F={budget.get('adapter_resident_mb_mean')} vs S0-D={independent.get('adapter_resident_mb_mean')}",
    )
    add(
        "budget_policy_has_no_more_reserve_failures_than_independent_bank",
        (budget.get("reserve_fail_count") or 0) <= (independent.get("reserve_fail_count") or 0),
        f"S0-F={budget.get('reserve_fail_count')} vs S0-D={independent.get('reserve_fail_count')}",
    )

    return {
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/pilot_minimal.yaml")
    args = parser.parse_args()

    config_path = (REPO_ROOT / args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    run_id = _run_id(config)
    run_dir = ensure_run_dir(run_id, config.get("run", {}).get("output_dir", "runs"))
    trace_path = run_dir / "route_traces.jsonl"

    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(),
        "config_path": str(config_path.relative_to(REPO_ROOT)),
        "hardware": config.get("hardware", {}),
        "model": config.get("model", {}),
        "dataset": config.get("dataset", {}),
        "evidence": {
            "measurement_source": config.get("source", {}).get("measurement_source", "cost_model_3090"),
            "source_summary_csv": config.get("source", {}).get("summary_csv"),
            "scientific_status": "feasibility_prior",
        },
    }
    write_json(run_dir / "run_manifest.json", manifest)

    traces = run_stage(config, run_id=run_id, repo_root=REPO_ROOT)
    for trace in traces:
        trace["route_trace_path"] = str(trace_path.relative_to(REPO_ROOT))
        append_jsonl(trace_path, trace)

    summary_rows = summarize_traces(read_jsonl(trace_path))
    write_summary_csv(run_dir / "summary.csv", summary_rows)

    checks = _directionality_checks(summary_rows)
    write_json(run_dir / "checks.json", checks)

    print(json.dumps({"run_dir": str(run_dir), "traces": len(traces), "checks_passed": checks["passed"]}, ensure_ascii=False))
    return 0 if checks["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
