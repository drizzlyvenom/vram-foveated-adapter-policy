from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image


def load_task_manifest(manifest_path: str | Path, *, repo_root: str | Path) -> list[dict[str, Any]]:
    path = Path(manifest_path)
    if not path.is_absolute():
        path = Path(repo_root) / path
    samples: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                sample = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid manifest JSON at {path}:{line_no}: {exc}") from exc
            if "full_image_path" not in sample:
                raise ValueError(f"Manifest sample at {path}:{line_no} is missing full_image_path.")
            samples.append(sample)
    if not samples:
        raise ValueError(f"Manifest has no samples: {path}")
    return samples


def sample_for_index(samples: list[dict[str, Any]], sample_index: int) -> dict[str, Any] | None:
    if not samples:
        return None
    return samples[sample_index % len(samples)]


def _repo_path(path_text: str, repo_root: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (Path(repo_root) / path).resolve()


def _repo_relative(path: str | Path, repo_root: str | Path) -> str:
    resolved = Path(path).resolve()
    root = Path(repo_root).resolve()
    try:
        return str(resolved.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")


def _safe_sample_id(sample: dict[str, Any], sample_index: int) -> str:
    raw = str(sample.get("sample_id") or f"sample_{sample_index:04d}")
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in raw)
    return safe[:80] or f"sample_{sample_index:04d}"


def _resize_exact(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.convert("RGB").resize(size, Image.Resampling.LANCZOS)


def _resize_max_side(image: Image.Image, max_side: int = 1024) -> Image.Image:
    image = image.convert("RGB")
    copy = image.copy()
    copy.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return copy


def _box_from_sample(sample: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int]:
    rel_box = sample.get("roi_box_rel_xyxy") or sample.get("oracle_roi_box_rel_xyxy")
    abs_box = sample.get("roi_box_xyxy") or sample.get("oracle_roi_box_xyxy")
    if rel_box:
        x0, y0, x1, y1 = [float(value) for value in rel_box]
        box = (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
    elif abs_box:
        box = tuple(int(float(value)) for value in abs_box)
    else:
        side = int(min(width, height) * 0.7)
        left = (width - side) // 2
        top = (height - side) // 2
        box = (left, top, left + side, top + side)
    x0, y0, x1, y1 = box
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    return x0, y0, x1, y1


def prepare_manifest_policy_images(
    *,
    sample: dict[str, Any],
    sample_index: int,
    visual_policy: str,
    run_dir: str | Path,
    repo_root: str | Path,
) -> tuple[list[Path], str]:
    evidence = prepare_manifest_policy_evidence(
        sample=sample,
        sample_index=sample_index,
        visual_policy=visual_policy,
        run_dir=run_dir,
        repo_root=repo_root,
    )
    return evidence["image_paths"], str(evidence["roi_source"])


def prepare_manifest_policy_evidence(
    *,
    sample: dict[str, Any],
    sample_index: int,
    visual_policy: str,
    run_dir: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    image_path = _repo_path(str(sample["full_image_path"]), repo_root)
    if not image_path.exists():
        raise FileNotFoundError(f"Manifest image does not exist: {image_path}")

    image = Image.open(image_path).convert("RGB")
    sample_id = _safe_sample_id(sample, sample_index)
    out_dir = Path(run_dir) / "real_task_images" / sample_id
    out_dir.mkdir(parents=True, exist_ok=True)

    full_path = out_dir / "full_1024.jpg"
    low_path = out_dir / "low_336.jpg"
    roi_path = out_dir / "roi_448.jpg"

    if not full_path.exists():
        _resize_max_side(image, 1024).save(full_path, quality=95)
    if not low_path.exists():
        _resize_exact(image, (336, 336)).save(low_path, quality=95)
    roi_box = _box_from_sample(sample, image.width, image.height)
    if not roi_path.exists():
        _resize_exact(image.crop(roi_box), (448, 448)).save(roi_path, quality=95)

    roi_source = str(sample.get("roi_source") or "center_crop")
    if visual_policy == "full_image":
        selected = [("full_resized", full_path)]
    elif visual_policy == "low_res_only":
        selected = [("low_res_global", low_path)]
    elif visual_policy in {"foveater_roi", "oracle_roi", "foveater_roi_controlled_fallback"}:
        selected = [("low_res_global", low_path), ("roi_crop", roi_path)]
    else:
        selected = [("full_resized", full_path)]

    source = {
        "image_source": "manifest.full_image_path",
        "manifest_sample_id": str(sample.get("sample_id") or sample_id),
        "manifest_full_image_path": _repo_relative(image_path, repo_root),
        "source_dataset": sample.get("source_dataset"),
        "source_url": sample.get("source_url"),
        "source_prompt_available": bool(sample.get("prompt")),
        "original_image_size_wh": [image.width, image.height],
        "prepared_full_image_path": _repo_relative(full_path, repo_root),
        "prepared_low_res_path": _repo_relative(low_path, repo_root),
        "prepared_roi_path": _repo_relative(roi_path, repo_root),
        "selected_image_paths": [
            {"role": role, "path": _repo_relative(path, repo_root)} for role, path in selected
        ],
        "roi_source": roi_source,
        "roi_box_rel_xyxy": sample.get("roi_box_rel_xyxy") or sample.get("oracle_roi_box_rel_xyxy"),
        "roi_box_xyxy": list(roi_box),
        "evidence_preparation": "manifest_image_resize_lowres_and_roi_crop",
    }
    return {
        "image_paths": [path for _, path in selected],
        "roi_source": roi_source,
        "source": source,
    }
