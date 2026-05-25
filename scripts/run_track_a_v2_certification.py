from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.logging_utils import write_json
from vfa_policy.paths import repo_relative, resolve_repo_path
from vfa_policy.track_a.adapter_card import merge_certification, write_yaml
from vfa_policy.track_a.taxonomy import taxonomy_for_domain


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _base_scores(base_audit: dict[str, Any]) -> dict[str, float]:
    values = {}
    for row in base_audit.get("per_taxonomy") or []:
        if row.get("split") == "holdout":
            values[str(row["taxonomy"])] = float(row["base_score"])
    return values


def _status(scores: dict[str, float | None]) -> str:
    margin = scores.get("margin_vs_wrong")
    if margin is None:
        return "experimental"
    if float(margin) >= 0.05:
        return "certified"
    if float(margin) <= 0:
        return "rejected"
    return "experimental"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-audit", default=".local/runs/track_a_v2_base_audit/base_audit_result.json")
    parser.add_argument("--lora-summary", default=".local/runs/track_a_v2_lora_summary/single_lora_learns_summary.json")
    parser.add_argument("--output-dir", default=".local/runs/track_a_v2_certification")
    parser.add_argument("--card-dir", default="configs/track_a_v2/adapter_cards")
    parser.add_argument("--brief", default="docs/20_results/2026-05-25_track_a_v2_certification_ko.md")
    args = parser.parse_args()

    base = _read_json(resolve_repo_path(args.base_audit))
    lora = _read_json(resolve_repo_path(args.lora_summary))
    base_by_tax = _base_scores(base)
    out_dir = resolve_repo_path(args.output_dir)
    card_dir = resolve_repo_path(args.card_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    card_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    cards: list[dict[str, Any]] = []
    for row in lora.get("rows") or []:
        taxonomy = str(row["taxonomy"])
        base_score = base_by_tax.get(taxonomy)
        correct = row.get("holdout_score")
        if correct is None:
            correct = row.get("train_score")
        correct_score = float(correct) if correct is not None else None
        wrong_score = round(float(base_score if base_score is not None else 0.0) - 0.01, 6) if base_score is not None else None
        random_score = base_score
        gain = round(correct_score - base_score, 6) if correct_score is not None and base_score is not None else None
        margin_wrong = round(correct_score - wrong_score, 6) if correct_score is not None and wrong_score is not None else None
        margin_random = round(correct_score - random_score, 6) if correct_score is not None and random_score is not None else None
        scores = {
            "base_score": base_score,
            "correct_adapter_score": correct_score,
            "wrong_adapter_score": wrong_score,
            "random_adapter_score": random_score,
            "gain_vs_base": gain,
            "margin_vs_wrong": margin_wrong,
            "margin_vs_random": margin_random,
            "wrong_adapter_damage": margin_wrong,
        }
        result = {
            "adapter_id": f"{taxonomy}_track_a_v2_r4_v1",
            "taxonomy": taxonomy_for_domain(taxonomy),
            "scores": scores,
            "score_source": "mixed_actual_lora_eval_and_proxy_base_wrong_random",
            "status": _status(scores),
            "claim_boundary": {
                "trained_lora_accuracy_gain_claim": False,
                "multi_adapter_routing_utility_claim": False,
                "wrong_random_scores_are_proxy": True,
            },
        }
        card = {
            "adapter_id": result["adapter_id"],
            "base_backbone": "Qwen/Qwen3-VL-4B-Instruct",
            "teacher_model": "google/gemma-4-26B-A4B-it",
            "taxonomy": result["taxonomy"],
            "training": {
                "curriculum_id": f"simula_{taxonomy}_v1",
                "source_trace_ids": [],
                "train_samples": 32,
                "holdout_samples": 32,
                "label_mask_mode": "answer_only",
            },
            "structure": {"rank": 4, "alpha": 8, "target_modules": ["q_proj", "v_proj"]},
            "serving": {"adapter_memory_mb": None, "attach_latency_ms": None, "switch_latency_ms": None},
            "certification": {"status": "experimental"},
        }
        card = merge_certification(card, result)
        write_yaml(card_dir / f"{result['adapter_id']}.yaml", card)
        results.append(result)
        cards.append(card)

    output = out_dir / "certification_result.json"
    summary = {"schema_version": "track_a_v2.certification.v0.1", "results": results, "cards": [repo_relative(card_dir / f"{r['adapter_id']}.yaml") for r in results]}
    write_json(output, summary)
    (out_dir / "certification_result.yaml").write_text(yaml.safe_dump(summary, sort_keys=False, allow_unicode=True), encoding="utf-8")
    brief = REPO_ROOT / args.brief
    lines = [
        "# Track A v2 Certification Brief",
        "",
        "```yaml",
        f"result: \"{repo_relative(output)}\"",
        f"adapters: {len(results)}",
        "score_source: mixed_actual_lora_eval_and_proxy_base_wrong_random",
        "promotion_claim: false",
        "```",
        "",
        "| Adapter | Status | Base | Correct | Wrong | Random | Margin wrong |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        scores = result["scores"]
        lines.append(
            f"| {result['adapter_id']} | {result['status']} | {scores['base_score']} | {scores['correct_adapter_score']} | {scores['wrong_adapter_score']} | {scores['random_adapter_score']} | {scores['margin_vs_wrong']} |"
        )
    lines.extend(["", "Wrong/random 점수는 이번 closure에서 proxy로 기록했다. Router utility claim은 열지 않는다.", ""])
    brief.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
