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

from vfa_policy.foveation.ocr_detector import detect_ocr_roi, rel_box


DEFAULT_INPUT = ".local/data/tiny_scored_manifest/manifest.jsonl"
DEFAULT_OUTPUT = ".local/data/tiny_scored_manifest/manifest_ocr_detector.jsonl"


def _resolve(path_text: str | Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else (REPO_ROOT / path)


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
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input JSONL manifest.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSONL manifest with OCR detector boxes.")
    parser.add_argument("--engine", choices=["rapidocr", "pytesseract"], default="rapidocr")
    parser.add_argument("--min-confidence", type=float, default=None)
    parser.add_argument("--pad-px", type=int, default=32)
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Write unavailable detector metadata instead of failing when OCR cannot produce boxes.",
    )
    args = parser.parse_args()

    input_path = _resolve(args.input)
    output_path = _resolve(args.output)
    rows = _load_jsonl(input_path)
    enriched: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []

    for idx, row in enumerate(rows):
        updated = dict(row)
        image_path = _resolve(str(row["full_image_path"]))
        result = detect_ocr_roi(
            image_path,
            engine=str(args.engine),
            min_confidence=None if args.min_confidence is None else float(args.min_confidence),
            pad_px=int(args.pad_px),
        )
        updated["ocr_detector_engine"] = result.engine
        updated["ocr_detector_available"] = bool(result.available)
        updated["ocr_detector_text"] = result.text
        updated["ocr_detector_confidence_mean"] = result.confidence_mean
        updated["ocr_detector_error_type"] = result.error_type
        updated["ocr_detector_error_message"] = result.error_message
        updated["ocr_detector_source_image_path"] = _repo_relative(image_path)
        if result.available and result.box_xyxy:
            from PIL import Image

            with Image.open(image_path) as image:
                width, height = image.size
            updated["ocr_detector_roi_box_xyxy"] = list(result.box_xyxy)
            updated["ocr_detector_roi_box_rel_xyxy"] = rel_box(
                result.box_xyxy,
                width=width,
                height=height,
            )
        else:
            missing.append(
                {
                    "index": idx,
                    "sample_id": row.get("sample_id"),
                    "error_type": result.error_type,
                    "error_message": result.error_message,
                }
            )
        enriched.append(updated)

    if missing and not args.allow_missing:
        print(
            json.dumps(
                {
                    "ok": False,
                    "output": str(output_path),
                    "missing_count": len(missing),
                    "first_missing": missing[:3],
                    "next_action": "Install OCR dependencies or rerun with --allow-missing for diagnostic metadata only.",
                },
                ensure_ascii=False,
            )
        )
        return 2

    _write_jsonl(output_path, enriched)
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(output_path),
                "samples": len(enriched),
                "detector_available": len(enriched) - len(missing),
                "detector_missing": len(missing),
                "claim_boundary": "ocr_detector_box is an external OCR detector baseline only when ocr_detector_available is true.",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
