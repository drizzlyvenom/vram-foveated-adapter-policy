from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=".local/data/track_a_v2_adapter_sensitive/manifest.jsonl")
    parser.add_argument("--taxonomies", default="document,chart")
    parser.add_argument("--max-steps", type=int, default=32)
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--eval-train-samples", type=int, default=32)
    parser.add_argument("--eval-holdout-samples", type=int, default=32)
    parser.add_argument("--roi-source", default="oracle_box")
    parser.add_argument("--visual-policy", default="oracle_roi")
    parser.add_argument("--brief", default="docs/20_results/2026-05-25_track_a_v2_single_lora_learns_ko.md")
    args = parser.parse_args()

    taxonomies = [item.strip() for item in args.taxonomies.split(",") if item.strip()]
    rows = []
    for taxonomy in taxonomies:
        latest_name = f"track_a_v2_{taxonomy}_latest"
        command = [
            sys.executable,
            "scripts/train_tiny_lora_smoke.py",
            "--manifest",
            args.manifest,
            "--taxonomy-label",
            taxonomy,
            "--roi-source",
            args.roi_source,
            "--visual-policy",
            args.visual_policy,
            "--max-samples",
            str(args.max_samples),
            "--max-steps",
            str(args.max_steps),
            "--eval-train-samples",
            str(args.eval_train_samples),
            "--eval-holdout-samples",
            str(args.eval_holdout_samples),
            "--eval-max-new-tokens",
            "8",
            "--rank",
            "4",
            "--alpha",
            "8",
            "--learning-rate",
            "1e-4",
            "--label-mask-mode",
            "answer_only",
            "--latest-name",
            latest_name,
        ]
        completed = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        row: dict[str, Any] = {"taxonomy": taxonomy, "returncode": completed.returncode, "latest_name": latest_name, "stdout_excerpt": completed.stdout[-4000:]}
        if completed.returncode == 0:
            parsed = json.loads(completed.stdout.strip().splitlines()[-1])
            result_path = Path(parsed["run_dir"]) / "tiny_lora_train_result.json"
            result = _read_json(result_path)
            row.update(
                {
                    "run_id": result["run_id"],
                    "adapter_dir": result["adapter_dir"],
                    "latest_adapter_dir": result["latest_adapter_dir"],
                    "train_score": result.get("evaluation", {}).get("train", {}).get("score_mean"),
                    "holdout_score": result.get("evaluation", {}).get("holdout", {}).get("score_mean"),
                    "loss_first": result.get("loss_first"),
                    "loss_last": result.get("loss_last"),
                }
            )
        rows.append(row)

    out_dir = REPO_ROOT / ".local" / "runs" / "track_a_v2_lora_summary"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema_version": "track_a_v2.single_lora_learns.v0.1",
        "taxonomies": taxonomies,
        "rows": rows,
        "all_completed": all(row["returncode"] == 0 for row in rows),
        "promotion_claim": False,
    }
    (out_dir / "single_lora_learns_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    brief = REPO_ROOT / args.brief
    lines = [
        "# Track A v2 Single LoRA Learns Brief",
        "",
        "```yaml",
        f"taxonomies: {taxonomies}",
        f"all_completed: {str(summary['all_completed']).lower()}",
        "promotion_claim: false",
        "```",
        "",
        "| Taxonomy | Run | Train score | Holdout score | Status |",
        "|---|---|---:|---:|---|",
    ]
    for row in rows:
        status = "completed" if row["returncode"] == 0 else "failed"
        lines.append(f"| {row['taxonomy']} | {row.get('run_id', 'n/a')} | {row.get('train_score')} | {row.get('holdout_score')} | {status} |")
    lines.extend(["", "이 결과는 Gate 1 path/evidence이며, accuracy gain claim은 certification 전까지 열지 않는다.", ""])
    brief.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["all_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
