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
from vfa_policy.track_a.taxonomy import taxonomy_key


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=".local/data/track_a_v2_adapter_sensitive/manifest.jsonl")
    parser.add_argument("--teacher", default=".local/data/track_a_v2_adapter_sensitive/teacher_annotations.jsonl")
    parser.add_argument("--output-dir", default=".local/data/track_a_v2_adapter_sensitive")
    parser.add_argument("--brief", default="docs/20_results/2026-05-25_track_a_v2_teacher_curriculum_brief_ko.md")
    args = parser.parse_args()

    manifest = resolve_repo_path(args.manifest)
    teacher_path = resolve_repo_path(args.teacher)
    output_dir = resolve_repo_path(args.output_dir)
    samples = _read_jsonl(manifest)
    teacher_rows = {row.get("sample_id"): row for row in _read_jsonl(teacher_path)}
    curriculum_rows: list[dict[str, Any]] = []
    expanded_teacher_rows: list[dict[str, Any]] = []

    for sample in samples:
        taxonomy = sample.get("taxonomy_v2") or {}
        teacher = teacher_rows.get(sample["sample_id"])
        if teacher is None:
            teacher = {
                "teacher_annotation_id": f"teacher_rule_{sample['sample_id']}",
                "teacher_model": "google/gemma-4-26B-A4B-it",
                "sample_id": sample["sample_id"],
                "annotation_source": "simula_rule_expansion",
                "taxonomy": taxonomy,
                "expected_answer_candidate": (sample.get("expected_answers") or [""])[0],
                "hard_negatives": sample.get("hard_negatives") or [],
                "rationale": "Rule-expanded from manifest truth after representative Gemma teacher annotations.",
                "label_is_final_truth": False,
            }
        expanded_teacher_rows.append(teacher)
        adapter_id = f"{taxonomy.get('domain')}_{taxonomy.get('evidence_type')}_{taxonomy.get('operation')}_r4_v1"
        curriculum_rows.append(
            {
                "curriculum_id": f"simula_{taxonomy.get('domain')}_{taxonomy.get('operation')}_v1",
                "sample_id": sample["sample_id"],
                "split": sample["split"],
                "teacher_annotation_id": teacher.get("teacher_annotation_id"),
                "adapter_id": adapter_id,
                "taxonomy": taxonomy,
                "taxonomy_key": taxonomy_key(taxonomy),
                "prompt": sample["prompt"],
                "expected_answers": sample.get("expected_answers") or [],
                "hard_negatives": teacher.get("hard_negatives") or sample.get("hard_negatives") or [],
                "full_image_path": sample["full_image_path"],
                "teacher_label_is_candidate": True,
            }
        )

    curriculum_path = output_dir / "curriculum_manifest.jsonl"
    expanded_teacher_path = output_dir / "teacher_annotations_expanded.jsonl"
    _write_jsonl(curriculum_path, curriculum_rows)
    _write_jsonl(expanded_teacher_path, expanded_teacher_rows)

    adapter_plan = {
        "adapters": sorted(
            {
                row["adapter_id"]: {
                    "adapter_id": row["adapter_id"],
                    "taxonomy": row["taxonomy"],
                    "rank": 4,
                    "alpha": 8,
                    "target_modules": ["q_proj", "v_proj"],
                }
                for row in curriculum_rows
            }.values(),
            key=lambda item: item["adapter_id"],
        )
    }
    cert_plan = {
        "comparisons": ["base_no_adapter", "correct_lora", "wrong_lora", "random_untrained_lora"],
        "margin_threshold": 0.05,
        "promotion_claim_default": False,
    }
    (output_dir / "adapter_candidate_plan.yaml").write_text(yaml.safe_dump(adapter_plan, sort_keys=False, allow_unicode=True), encoding="utf-8")
    (output_dir / "certification_eval_plan.yaml").write_text(yaml.safe_dump(cert_plan, sort_keys=False, allow_unicode=True), encoding="utf-8")

    summary = {
        "curriculum_manifest": repo_relative(curriculum_path),
        "teacher_annotations_expanded": repo_relative(expanded_teacher_path),
        "samples": len(curriculum_rows),
        "teacher_representative_rows": len(teacher_rows),
        "rule_expanded_rows": max(0, len(expanded_teacher_rows) - len(teacher_rows)),
        "adapters": len(adapter_plan["adapters"]),
    }
    write_json(output_dir / "simula_curriculum_summary.json", summary)
    brief = REPO_ROOT / args.brief
    brief.write_text(
        "\n".join(
            [
                "# Track A v2 Gemma Teacher / Simula Curriculum Brief",
                "",
                "## 요약",
                "",
                "Gemma teacher annotation row와 manifest truth를 합쳐 Simula-style curriculum manifest를 생성했다.",
                "",
                "```yaml",
                f"curriculum_manifest: \"{summary['curriculum_manifest']}\"",
                f"samples: {summary['samples']}",
                f"teacher_representative_rows: {summary['teacher_representative_rows']}",
                f"rule_expanded_rows: {summary['rule_expanded_rows']}",
                f"adapters: {summary['adapters']}",
                "teacher_label_is_final_truth: false",
                "promotion_claim: false",
                "```",
                "",
                "## Claim Boundary",
                "",
                "- safe: teacher/curriculum compile path is available",
                "- not_yet: teacher labels are final truth, adapter utility, router utility",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
