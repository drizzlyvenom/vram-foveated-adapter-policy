from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.paths import repo_relative, resolve_repo_path


DATASETS_SERVER = "https://datasets-server.huggingface.co"
DEFAULT_OUTPUT_DIR = ".local/data/external_tiny_manifest"


SOURCES: list[dict[str, Any]] = [
    {
        "key": "textvqa",
        "dataset": "lmms-lab/textvqa",
        "config": "default",
        "split": "validation",
        "task_family": "scene_text_or_ocr",
        "taxonomy_label": "scene_text",
        "question_field": "question",
        "answer_field": "answers",
    },
    {
        "key": "docvqa",
        "dataset": "lmms-lab/DocVQA",
        "config": "DocVQA",
        "split": "validation",
        "task_family": "document_or_receipt",
        "taxonomy_label": "document",
        "question_field": "question",
        "answer_field": "answers",
    },
    {
        "key": "chartqa",
        "dataset": "lmms-lab/ChartQA",
        "config": "default",
        "split": "test",
        "task_family": "chart_or_table",
        "taxonomy_label": "chart",
        "question_field": "question",
        "answer_field": "answer",
    },
    {
        "key": "screenqa",
        "dataset": "rootsautomation/RICO-ScreenQA",
        "config": "default",
        "split": "validation",
        "task_family": "ui_screen",
        "taxonomy_label": "ui_screen",
        "question_field": "question",
        "answer_field": "ground_truth",
    },
]


def _api_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(
        f"{DATASETS_SERVER}{path}",
        params=params,
        timeout=60,
        headers={"User-Agent": "vfa-policy-external-tiny-manifest/0.1"},
    )
    response.raise_for_status()
    return dict(response.json())


def _rows(source: dict[str, Any], *, length: int) -> list[dict[str, Any]]:
    payload = _api_get(
        "/rows",
        {
            "dataset": source["dataset"],
            "config": source["config"],
            "split": source["split"],
            "offset": 0,
            "length": length,
        },
    )
    return [dict(item["row"]) for item in payload.get("rows", [])]


def _clean_text(value: Any) -> str:
    text = str(value or "").strip()
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return " ".join(text.split())


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.-")
    return safe[:96] or "sample"


def _unique_texts(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _clean_text(value)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _answers(source_key: str, row: dict[str, Any], answer_field: str) -> list[str]:
    raw = row.get(answer_field)
    if source_key == "screenqa":
        candidates: list[Any] = []
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                candidates.append(item.get("full_answer"))
                for element in item.get("ui_elements") or []:
                    if isinstance(element, dict):
                        candidates.append(element.get("text"))
        return _unique_texts(candidates)
    if isinstance(raw, list):
        return _unique_texts(raw)
    return _unique_texts([raw])


def _infer_answer_type(answers: list[str]) -> str:
    if answers and all(re.fullmatch(r"[-+]?\d+(?:\.\d+)?%?", answer.strip()) for answer in answers):
        return "number"
    return "text"


def _numeric_tolerance(answer_type: str, answers: list[str]) -> float | None:
    if answer_type != "number":
        return None
    if any("." in answer for answer in answers):
        return 0.05
    return 0.0


def _image_info(row: dict[str, Any]) -> dict[str, Any] | None:
    image = row.get("image")
    if isinstance(image, dict) and image.get("src"):
        return image
    return None


def _download_image(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=120, headers={"User-Agent": "vfa-policy-external-tiny-manifest/0.1"})
    response.raise_for_status()
    output_path.write_bytes(response.content)
    with Image.open(output_path) as image:
        image.convert("RGB").save(output_path, quality=95)


def _rel_box_from_abs(bounds: list[Any], *, width: int, height: int) -> list[float] | None:
    if len(bounds) != 4:
        return None
    x0, y0, x1, y1 = [float(item) for item in bounds]
    if x1 <= x0 or y1 <= y0:
        return None
    return [
        round(max(0.0, min(1.0, x0 / width)), 6),
        round(max(0.0, min(1.0, y0 / height)), 6),
        round(max(0.0, min(1.0, x1 / width)), 6),
        round(max(0.0, min(1.0, y1 / height)), 6),
    ]


def _screenqa_target_box(row: dict[str, Any], *, width: int, height: int) -> list[float] | None:
    ground_truth = row.get("ground_truth")
    if not isinstance(ground_truth, list):
        return None
    for item in ground_truth:
        if not isinstance(item, dict):
            continue
        for element in item.get("ui_elements") or []:
            if not isinstance(element, dict):
                continue
            bounds = element.get("bounds")
            if isinstance(bounds, list):
                rel = _rel_box_from_abs(bounds, width=width, height=height)
                if rel:
                    return rel
    return None


def _build_row(
    *,
    source: dict[str, Any],
    row: dict[str, Any],
    source_index: int,
    global_index: int,
    output_dir: Path,
    primary_count_per_source: int,
) -> dict[str, Any] | None:
    image = _image_info(row)
    answers = _answers(str(source["key"]), row, str(source["answer_field"]))
    question = _clean_text(row.get(str(source["question_field"])))
    if not image or not answers or not question:
        return None

    sample_id = _safe_id(f"ext_{source['key']}_{source_index:04d}")
    image_path = output_dir / "images" / f"{sample_id}.jpg"
    _download_image(str(image["src"]), image_path)
    with Image.open(image_path) as loaded:
        width, height = loaded.size

    answer_type = _infer_answer_type(answers)
    row_out: dict[str, Any] = {
        "sample_id": sample_id,
        "taxonomy_label": source["taxonomy_label"],
        "task_family": source["task_family"],
        "prompt": f"Answer the question using the image. Keep the answer short.\nQuestion: {question}",
        "question": question,
        "expected_answers": answers,
        "answer_type": answer_type,
        "split": "external_eval_primary" if source_index < primary_count_per_source else "external_eval_reserve",
        "eval_split": "primary_n32" if source_index < primary_count_per_source else "reserve_n32",
        "full_image_path": repo_relative(image_path),
        "roi_source": "center_crop",
        "source_dataset": source["dataset"],
        "source_dataset_config": source["config"],
        "source_dataset_split": source["split"],
        "source_row_index": source_index,
        "source_url": image.get("src"),
        "source_record": {
            "dataset": source["dataset"],
            "config": source["config"],
            "split": source["split"],
            "global_manifest_index": global_index,
        },
        "original_image_size_wh": [width, height],
        "center_crop_roi_box_rel_xyxy": [0.15, 0.15, 0.85, 0.85],
    }
    tolerance = _numeric_tolerance(answer_type, answers)
    if tolerance is not None:
        row_out["numeric_tolerance"] = tolerance

    target_box = None
    if source["key"] == "screenqa":
        target_box = _screenqa_target_box(row, width=width, height=height)
    if target_box:
        row_out["target_box_rel_xyxy"] = target_box
        row_out["oracle_roi_box_rel_xyxy"] = target_box
        row_out["layout_proxy_roi_box_rel_xyxy"] = target_box
        row_out["detector_proxy_roi_box_rel_xyxy"] = target_box
    return row_out


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--samples-per-source", type=int, default=16)
    parser.add_argument(
        "--primary-count-per-source",
        type=int,
        default=8,
        help="Rows per source that appear in the first balanced n=32 validation block.",
    )
    parser.add_argument("--fetch-multiplier", type=int, default=4)
    args = parser.parse_args()

    output_dir = resolve_repo_path(args.output_dir)
    source_rows: dict[str, list[dict[str, Any]]] = {}
    for source in SOURCES:
        selected: list[dict[str, Any]] = []
        candidates = _rows(source, length=int(args.samples_per_source) * int(args.fetch_multiplier))
        for candidate in candidates:
            built = _build_row(
                source=source,
                row=candidate,
                source_index=len(selected),
                global_index=0,
                output_dir=output_dir,
                primary_count_per_source=int(args.primary_count_per_source),
            )
            if built:
                selected.append(built)
            if len(selected) >= int(args.samples_per_source):
                break
        if len(selected) < int(args.samples_per_source):
            raise RuntimeError(
                f"{source['dataset']} yielded {len(selected)} usable rows, "
                f"but {args.samples_per_source} were requested."
            )
        source_rows[str(source["key"])] = selected

    ordered: list[dict[str, Any]] = []
    for index in range(int(args.samples_per_source)):
        for source in SOURCES:
            row = dict(source_rows[str(source["key"])][index])
            row["source_record"]["global_manifest_index"] = len(ordered)
            ordered.append(row)

    manifest_path = output_dir / "manifest.jsonl"
    _write_jsonl(manifest_path, ordered)

    summary = {
        "ok": True,
        "manifest_path": repo_relative(manifest_path),
        "samples": len(ordered),
        "samples_per_source": int(args.samples_per_source),
        "primary_n32_distribution": {
            source["key"]: sum(
                1
                for row in ordered[: int(args.primary_count_per_source) * len(SOURCES)]
                if row["source_dataset"] == source["dataset"]
            )
            for source in SOURCES
        },
        "sources": [
            {
                "key": source["key"],
                "dataset": source["dataset"],
                "config": source["config"],
                "split": source["split"],
            }
            for source in SOURCES
        ],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
