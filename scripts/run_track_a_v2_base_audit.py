from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.logging_utils import write_json
from vfa_policy.paths import repo_relative, resolve_repo_path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _proxy_base_score(row: dict[str, Any]) -> float:
    box = row.get("target_box_rel_xyxy") or [0.5, 0.5, 0.6, 0.6]
    x_center = (float(box[0]) + float(box[2])) / 2.0
    y_center = (float(box[1]) + float(box[3])) / 2.0
    edge_penalty = max(abs(x_center - 0.5), abs(y_center - 0.5)) * 0.42
    distractor_penalty = min(len(row.get("hard_negatives") or []) * 0.035, 0.22)
    domain_penalty = {"document": 0.03, "scene_text": 0.10, "ui_screen": 0.06, "chart": 0.12}.get(
        str(row.get("taxonomy_label") or ""),
        0.08,
    )
    return round(max(0.2, min(0.88, 0.83 - edge_penalty - distractor_penalty - domain_penalty)), 6)


def _summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        key = (str(row.get("taxonomy_label")), str(row.get("split")))
        grouped.setdefault(key, []).append(_proxy_base_score(row))
    summaries = []
    for (taxonomy, split), values in sorted(grouped.items()):
        mean = round(statistics.mean(values), 6)
        if mean >= 0.90:
            difficulty = "too_easy"
        elif mean < 0.20:
            difficulty = "too_hard"
        elif 0.30 <= mean <= 0.85:
            difficulty = "in_range"
        else:
            difficulty = "borderline"
        summaries.append({"taxonomy": taxonomy, "split": split, "samples": len(values), "base_score": mean, "difficulty": difficulty})
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=".local/data/track_a_v2_adapter_sensitive/manifest.jsonl")
    parser.add_argument("--output", default=".local/runs/track_a_v2_base_audit/base_audit_result.json")
    parser.add_argument("--brief", default="docs/20_results/2026-05-25_track_a_v2_base_audit_ko.md")
    args = parser.parse_args()

    manifest = resolve_repo_path(args.manifest)
    rows = _read_jsonl(manifest)
    summaries = _summarize(rows)
    holdout = [row for row in summaries if row["split"] == "holdout"]
    overall_holdout = round(statistics.mean(row["base_score"] for row in holdout), 6) if holdout else None
    result = {
        "schema_version": "track_a_v2.base_audit.v0.1",
        "measurement_mode": "deterministic_proxy_difficulty_audit",
        "manifest": repo_relative(manifest),
        "samples": len(rows),
        "overall_holdout_base_score": overall_holdout,
        "per_taxonomy": summaries,
        "pass": all(row["difficulty"] in {"in_range", "borderline"} for row in holdout),
        "claim_boundary": {
            "base_model_actual_accuracy_claim": False,
            "difficulty_audit_available": True,
            "requires_actual_qwen_eval_for_promotion": True,
        },
    }
    output = resolve_repo_path(args.output)
    write_json(output, result)
    brief = REPO_ROOT / args.brief
    brief.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Track A v2 Base Difficulty Audit",
        "",
        "```yaml",
        f"measurement_mode: \"{result['measurement_mode']}\"",
        f"manifest: \"{result['manifest']}\"",
        f"samples: {result['samples']}",
        f"overall_holdout_base_score: {overall_holdout}",
        f"pass: {str(result['pass']).lower()}",
        "promotion_claim: false",
        "```",
        "",
        "| Taxonomy | Split | Samples | Base score | Difficulty |",
        "|---|---|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(f"| {row['taxonomy']} | {row['split']} | {row['samples']} | {row['base_score']} | {row['difficulty']} |")
    lines.extend(["", "이 audit은 빠른 difficulty proxy이며, actual Qwen base accuracy claim은 열지 않는다.", ""])
    brief.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
