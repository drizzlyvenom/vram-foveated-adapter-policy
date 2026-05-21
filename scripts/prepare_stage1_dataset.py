from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import requests
import yaml
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]

HF_DATASET_SERVER = "https://datasets-server.huggingface.co"
HF_DATASET_HOST = "datasets-server.huggingface.co"


def _resolve_under_repo(path_text: str) -> Path:
    path = (REPO_ROOT / path_text).resolve()
    if not path.is_relative_to(REPO_ROOT):
        raise ValueError(f"Refusing to write outside repository: {path_text}")
    return path


def _nested(row: dict[str, Any], dotted: str, default: Any = None) -> Any:
    current: Any = row
    for part in dotted.split("."):
        if isinstance(current, list):
            values = []
            for item in current:
                if isinstance(item, dict) and part in item:
                    values.append(item[part])
            current = values
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _safe_name(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)
    return text.strip("_")[:96] or "sample"


def _rows(source: dict[str, Any], timeout: int) -> list[dict[str, Any]]:
    params = {
        "dataset": source["dataset_id"],
        "config": source["config"],
        "split": source["split"],
        "offset": source.get("offset", 0),
        "length": source.get("length", 5),
    }
    url = f"{HF_DATASET_SERVER}/rows?{urlencode(params)}"
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    return payload.get("rows", [])


def _image_src(row: dict[str, Any], image_field: str) -> str:
    image_obj = row.get(image_field)
    if isinstance(image_obj, dict) and image_obj.get("src"):
        return image_obj["src"]
    raise ValueError(f"Row has no downloadable image src in field {image_field!r}")


def _answers(row: dict[str, Any], answer_field: str) -> list[str]:
    if answer_field == "ground_truth.full_answer":
        answers = []
        for item in row.get("ground_truth", []) or []:
            if isinstance(item, dict) and item.get("full_answer"):
                answers.append(str(item["full_answer"]))
        return answers
    value = _nested(row, answer_field)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v not in (None, "")]
    return [str(value)]


def _oracle_boxes(row: dict[str, Any]) -> list[list[float]]:
    boxes: list[list[float]] = []
    for truth in row.get("ground_truth", []) or []:
        for element in truth.get("ui_elements", []) or []:
            bounds = element.get("bounds")
            if isinstance(bounds, str):
                parts = [float(p) for p in bounds.split()]
            elif isinstance(bounds, list):
                parts = [float(p) for p in bounds]
            else:
                continue
            if len(parts) == 4:
                boxes.append(parts)
    return boxes


def _download_image(url: str, path: Path, timeout: int, user_agent: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != HF_DATASET_HOST or not parsed.path.startswith("/assets/"):
        raise ValueError(f"Refusing non-Hugging Face dataset asset URL: {url}")
    headers = {"User-Agent": user_agent}
    with requests.get(url, headers=headers, timeout=timeout, stream=True) as response:
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage1_foveation_smoke.yaml")
    args = parser.parse_args()

    config_path = (REPO_ROOT / args.config).resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dataset_cfg = config["dataset"]
    image_dir = _resolve_under_repo(dataset_cfg["image_dir"])
    manifest_path = _resolve_under_repo(dataset_cfg["manifest_path"])
    timeout = int(dataset_cfg.get("timeout_sec", 30))
    user_agent = dataset_cfg.get("user_agent", "vfa-stage1-smoke/0.1")

    records: list[dict[str, Any]] = []
    for source in config["sources"]:
        for item in _rows(source, timeout):
            row_idx = item["row_idx"]
            row = item["row"]
            image_src = _image_src(row, source.get("image_field", "image"))
            sample_id = f"{source['alias']}_{row_idx:05d}"
            suffix = ".png" if ".png?" in image_src.lower() else ".jpg"
            image_path = image_dir / f"{_safe_name(sample_id)}{suffix}"
            image_rel = image_path.relative_to(REPO_ROOT)

            if not image_path.exists():
                _download_image(image_src, image_path, timeout, user_agent)

            with Image.open(image_path) as img:
                width, height = img.size

            record = {
                "sample_id": sample_id,
                "dataset_id": source["dataset_id"],
                "dataset_alias": source["alias"],
                "config": source["config"],
                "split": source["split"],
                "row_idx": row_idx,
                "question": str(_nested(row, source["question_field"], "")),
                "answers": _answers(row, source["answer_field"]),
                "image_path": str(image_rel).replace("\\", "/"),
                "image_width": width,
                "image_height": height,
                "roi_source": source.get("roi_source"),
                "oracle_boxes_xyxy": _oracle_boxes(row),
            }
            records.append(record)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(json.dumps({"manifest": str(manifest_path), "samples": len(records)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
