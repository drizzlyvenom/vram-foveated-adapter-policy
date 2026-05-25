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

from vfa_policy.paths import repo_relative, resolve_repo_path


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
    if not rows:
        raise ValueError(f"Manifest has no rows: {path}")
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _field_value(row: dict[str, Any], dotted: str) -> Any:
    value: Any = row
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _passes_requirements(row: dict[str, Any], fields: list[str]) -> bool:
    for field in fields:
        value = _field_value(row, field)
        if value in (None, False, "", []):
            return False
    return True


def _balanced_select(
    rows: list[dict[str, Any]],
    *,
    group_field: str,
    samples_per_group: int,
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    group_order: list[str] = []
    for row in rows:
        key = str(_field_value(row, group_field) or "unknown")
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        if len(groups[key]) < samples_per_group:
            groups[key].append(row)

    shortages = {key: samples_per_group - len(value) for key, value in groups.items() if len(value) < samples_per_group}
    if shortages:
        raise RuntimeError(f"Not enough rows for balanced subset: {shortages}")

    selected: list[dict[str, Any]] = []
    for index in range(samples_per_group):
        for key in group_order:
            selected.append(groups[key][index])
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--require-field", action="append", default=[])
    parser.add_argument("--group-field", default=None)
    parser.add_argument("--samples-per-group", type=int, default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--set-split", default=None)
    args = parser.parse_args()

    input_path = resolve_repo_path(args.input)
    output_path = resolve_repo_path(args.output)
    rows = [
        row
        for row in _load_jsonl(input_path)
        if _passes_requirements(row, list(args.require_field))
    ]
    if args.group_field and args.samples_per_group is not None:
        rows = _balanced_select(
            rows,
            group_field=str(args.group_field),
            samples_per_group=int(args.samples_per_group),
        )
    elif args.max_samples is not None:
        rows = rows[: int(args.max_samples)]

    if args.set_split:
        rows = [dict(row, split=str(args.set_split), eval_split=str(args.set_split)) for row in rows]

    _write_jsonl(output_path, rows)
    groups: dict[str, int] = {}
    if args.group_field:
        for row in rows:
            key = str(_field_value(row, str(args.group_field)) or "unknown")
            groups[key] = groups.get(key, 0) + 1
    print(
        json.dumps(
            {
                "ok": True,
                "input": repo_relative(input_path),
                "output": repo_relative(output_path),
                "samples": len(rows),
                "groups": groups,
                "required_fields": list(args.require_field),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
