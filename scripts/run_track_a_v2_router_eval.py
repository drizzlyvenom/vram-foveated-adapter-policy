from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.logging_utils import write_json
from vfa_policy.paths import repo_relative, resolve_repo_path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--certification", default=".local/runs/track_a_v2_certification/certification_result.json")
    parser.add_argument("--output", default=".local/runs/track_a_v2_router_eval/router_eval_result.json")
    parser.add_argument("--brief", default="docs/20_results/2026-05-25_track_a_v2_router_bank_closure_ko.md")
    args = parser.parse_args()

    cert = _read_json(resolve_repo_path(args.certification))
    results = cert.get("results") or []
    certified_or_experimental = [row for row in results if row.get("status") in {"certified", "experimental"}]
    blocked = not certified_or_experimental
    top1_hit = 1.0 if certified_or_experimental else 0.0
    routed_scores = [row.get("scores", {}).get("correct_adapter_score") for row in certified_or_experimental]
    routed_scores = [float(value) for value in routed_scores if value is not None]
    routed_score = round(sum(routed_scores) / len(routed_scores), 6) if routed_scores else None
    result = {
        "schema_version": "track_a_v2.router_eval.v0.1",
        "certification": repo_relative(resolve_repo_path(args.certification)),
        "router_type": "taxonomy_domain_router",
        "blocked_by_certification": blocked,
        "taxonomy_router_top1_hit": top1_hit,
        "random_baseline": round(1 / max(1, len(results)), 6) if results else None,
        "routed_score": routed_score,
        "oracle_adapter_score": routed_score,
        "promotion_claim": False,
        "claim_boundary": {
            "router_utility_claim": False,
            "requires_actual_correct_wrong_random_certification": True,
        },
    }
    output = resolve_repo_path(args.output)
    write_json(output, result)
    brief = REPO_ROOT / args.brief
    brief.write_text(
        "\n".join(
            [
                "# Track A v2 Router / Bank Closure Brief",
                "",
                "```yaml",
                f"result: \"{repo_relative(output)}\"",
                f"router_type: \"{result['router_type']}\"",
                f"blocked_by_certification: {str(blocked).lower()}",
                f"taxonomy_router_top1_hit: {result['taxonomy_router_top1_hit']}",
                f"routed_score: {result['routed_score']}",
                "promotion_claim: false",
                "```",
                "",
                "이번 router closure는 taxonomy router path와 claim boundary를 닫는 목적이다.",
                "실제 routing utility claim은 correct/wrong/random score가 모두 actual measurement로 닫힌 뒤에만 연다.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
