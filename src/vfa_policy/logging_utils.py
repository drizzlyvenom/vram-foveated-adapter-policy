from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable


def ensure_run_dir(run_id: str, output_dir: str | Path = "runs") -> Path:
    run_dir = (Path(output_dir) / run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: str | Path, obj: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: str | Path, obj: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _percentile(values: Iterable[Any], q: float) -> float | None:
    clean = sorted(v for v in (_num(v) for v in values) if v is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(clean) - 1)
    frac = pos - lo
    return clean[lo] * (1 - frac) + clean[hi] * frac


def _mean(values: Iterable[Any]) -> float | None:
    clean = [v for v in (_num(v) for v in values) if v is not None]
    if not clean:
        return None
    return mean(clean)


def _std(values: Iterable[Any]) -> float | None:
    clean = [v for v in (_num(v) for v in values) if v is not None]
    if len(clean) < 2:
        return None
    return pstdev(clean)


def _bool(value: Any) -> bool | None:
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


def summarize_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for trace in traces:
        evidence = trace.get("evidence", {})
        key = (
            trace.get("run_id") or "unknown",
            trace.get("stage") or "unknown",
            trace.get("baseline_id") or "unknown",
            trace.get("split") or "unknown",
        )
        if evidence.get("source_baseline"):
            key = (*key[:3], f"{key[3]}|{evidence['source_baseline']}")
        grouped[key].append(trace)

    rows: list[dict[str, Any]] = []
    for (run_id, stage, baseline_id, split_key), items in sorted(grouped.items()):
        split, _, source_baseline = split_key.partition("|")
        memory = [item.get("memory", {}) for item in items]
        timing = [item.get("timing", {}) for item in items]
        quality = [item.get("quality", {}) for item in items]
        reserve_pass_values = [_bool(m.get("reserve_pass")) for m in memory]
        reserve_pass_clean = [v for v in reserve_pass_values if v is not None]

        row = {
            "run_id": run_id,
            "stage": stage,
            "baseline_id": baseline_id,
            "source_baseline": source_baseline or "",
            "split": split,
            "n_samples": len(items),
            "task_score_mean": _mean(q.get("task_score") for q in quality),
            "task_score_std": _std(q.get("task_score") for q in quality),
            "visual_tokens_mean": _mean(m.get("visual_token_count") for m in memory),
            "peak_vram_mb_mean": _mean(m.get("peak_vram_mb") for m in memory),
            "peak_vram_mb_p95": _percentile((m.get("peak_vram_mb") for m in memory), 0.95),
            "adapter_resident_mb_mean": _mean(m.get("adapter_resident_mb") for m in memory),
            "kv_cache_mb_mean": _mean(m.get("kv_cache_estimate_mb") for m in memory),
            "total_latency_ms_p50": _percentile((t.get("total_latency_ms") for t in timing), 0.50),
            "total_latency_ms_p95": _percentile((t.get("total_latency_ms") for t in timing), 0.95),
            "total_latency_ms_p99": _percentile((t.get("total_latency_ms") for t in timing), 0.99),
            "reserve_pass_rate": (
                sum(1 for v in reserve_pass_clean if v) / len(reserve_pass_clean)
                if reserve_pass_clean
                else None
            ),
            "reserve_fail_count": sum(1 for v in reserve_pass_clean if not v),
            "top1_route_hit": None,
            "wrong_route_rate": None,
            "abstention_rate": None,
            "fallback_success_rate": None,
            "main_failure_type": "",
        }
        rows.append(row)
    return rows


def write_summary_csv(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
