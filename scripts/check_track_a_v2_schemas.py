from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.track_a.adapter_card import load_yaml, merge_certification, validate_adapter_card
from vfa_policy.track_a.taxonomy import validate_taxonomy


def _read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    schema_dir = REPO_ROOT / "schemas" / "track_a_v2"
    card = load_yaml(schema_dir / "adapter_card_v2.example.yaml")
    cert = load_yaml(schema_dir / "certification_result.example.yaml")
    errors = validate_adapter_card(card)
    for row in _read_jsonl(schema_dir / "curriculum_manifest.example.jsonl"):
        errors.extend(validate_taxonomy(row.get("taxonomy") or {}))
    for row in _read_jsonl(schema_dir / "teacher_annotation.example.jsonl"):
        errors.extend(validate_taxonomy(row.get("taxonomy") or {}))
        if row.get("label_is_final_truth") is not False:
            errors.append("teacher annotation must mark label_is_final_truth=false")
    merged = merge_certification(card, cert)
    errors.extend(validate_adapter_card(merged))
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"ok": True, "checked": str(schema_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
