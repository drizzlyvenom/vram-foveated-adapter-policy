from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image


CENTER_CROP_REL_XYXY = [0.15, 0.15, 0.85, 0.85]
DETECTOR_REQUIRED_SOURCES = {"ocr_detector_box"}
ROI_SOURCE_ALIASES = {
    "center": "center_crop",
    "center_crop": "center_crop",
    "oracle": "oracle_box",
    "oracle_box": "oracle_box",
    "layout": "layout_proxy_box",
    "layout_box": "layout_proxy_box",
    "layout_proxy": "layout_proxy_box",
    "layout_proxy_box": "layout_proxy_box",
    "detector_proxy": "detector_proxy_box",
    "detector_proxy_box": "detector_proxy_box",
    "ocr_detector": "ocr_detector_box",
    "ocr_detector_box": "ocr_detector_box",
    # Backward-compatible names from the first tiny scored pass. These are not
    # external OCR detector outputs; they resolve to the controlled layout proxy.
    "ocr": "layout_proxy_box",
    "ocr_box": "layout_proxy_box",
    "ocr_box_or_layout_box": "layout_proxy_box",
}


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


def _box_from_rel(rel_box: list[Any], width: int, height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = [float(value) for value in rel_box]
    return (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))


def _center_crop_box(width: int, height: int) -> tuple[int, int, int, int]:
    return _box_from_rel(CENTER_CROP_REL_XYXY, width, height)


def _normalize_roi_source(value: Any) -> str:
    text = str(value or "center_crop").strip().lower()
    return ROI_SOURCE_ALIASES.get(text, text)


def _box_candidates(sample: dict[str, Any]) -> dict[str, tuple[Any, Any]]:
    layout_proxy_rel = (
        sample.get("layout_proxy_roi_box_rel_xyxy")
        or sample.get("detector_proxy_roi_box_rel_xyxy")
        or sample.get("layout_roi_box_rel_xyxy")
        or sample.get("ocr_roi_box_rel_xyxy")
    )
    layout_proxy_abs = (
        sample.get("layout_proxy_roi_box_xyxy")
        or sample.get("detector_proxy_roi_box_xyxy")
        or sample.get("layout_roi_box_xyxy")
        or sample.get("ocr_roi_box_xyxy")
    )
    detector_proxy_rel = sample.get("detector_proxy_roi_box_rel_xyxy") or layout_proxy_rel
    detector_proxy_abs = sample.get("detector_proxy_roi_box_xyxy") or layout_proxy_abs
    return {
        "center_crop": (
            sample.get("center_crop_roi_box_rel_xyxy") or sample.get("center_roi_box_rel_xyxy"),
            sample.get("center_crop_roi_box_xyxy") or sample.get("center_roi_box_xyxy"),
        ),
        "oracle_box": (
            sample.get("oracle_roi_box_rel_xyxy") or sample.get("target_box_rel_xyxy"),
            sample.get("oracle_roi_box_xyxy") or sample.get("target_box_xyxy"),
        ),
        "layout_proxy_box": (layout_proxy_rel, layout_proxy_abs),
        "detector_proxy_box": (detector_proxy_rel, detector_proxy_abs),
        "ocr_detector_box": (
            sample.get("ocr_detector_roi_box_rel_xyxy"),
            sample.get("ocr_detector_roi_box_xyxy"),
        ),
        "ocr_box_or_layout_box": (
            layout_proxy_rel or sample.get("oracle_roi_box_rel_xyxy"),
            layout_proxy_abs or sample.get("oracle_roi_box_xyxy"),
        ),
        "default": (
            sample.get("roi_box_rel_xyxy") or sample.get("oracle_roi_box_rel_xyxy"),
            sample.get("roi_box_xyxy") or sample.get("oracle_roi_box_xyxy"),
        ),
    }


def _clip_box(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    x0 = max(0, min(width - 1, x0))
    y0 = max(0, min(height - 1, y0))
    x1 = max(x0 + 1, min(width, x1))
    y1 = max(y0 + 1, min(height, y1))
    return x0, y0, x1, y1


def _box_from_sample(
    sample: dict[str, Any],
    width: int,
    height: int,
    *,
    visual_policy: str,
    roi_source_override: str | None = None,
) -> tuple[tuple[int, int, int, int], str]:
    if visual_policy == "oracle_roi":
        roi_source = "oracle_box"
    else:
        roi_source = _normalize_roi_source(roi_source_override or sample.get("roi_source") or "center_crop")
    candidates = _box_candidates(sample)
    rel_box, abs_box = candidates.get(roi_source, candidates["default"])
    if roi_source in DETECTOR_REQUIRED_SOURCES and not rel_box and not abs_box:
        sample_id = sample.get("sample_id") or "unknown"
        raise ValueError(
            f"ROI source {roi_source} requires detector boxes in manifest sample {sample_id}. "
            "Run scripts/prepare_ocr_detector_manifest.py first or choose layout_proxy_box."
        )
    if rel_box:
        box = _box_from_rel(rel_box, width, height)
    elif abs_box:
        box = tuple(int(float(value)) for value in abs_box)
    else:
        box = _center_crop_box(width, height)
        roi_source = "center_crop"
    return _clip_box(box, width, height), roi_source


def _box_iou(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    iw = max(0, ix1 - ix0)
    ih = max(0, iy1 - iy0)
    inter = iw * ih
    area_a = max(1, (ax1 - ax0) * (ay1 - ay0))
    area_b = max(1, (bx1 - bx0) * (by1 - by0))
    return round(inter / float(area_a + area_b - inter), 6)


def _target_box_from_sample(
    sample: dict[str, Any],
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    rel_box = sample.get("target_box_rel_xyxy") or sample.get("oracle_roi_box_rel_xyxy")
    abs_box = sample.get("target_box_xyxy") or sample.get("oracle_roi_box_xyxy")
    if rel_box:
        return _clip_box(_box_from_rel(rel_box, width, height), width, height)
    if abs_box:
        return _clip_box(tuple(int(float(value)) for value in abs_box), width, height)
    return None


def prepare_manifest_policy_images(
    *,
    sample: dict[str, Any],
    sample_index: int,
    visual_policy: str,
    run_dir: str | Path,
    repo_root: str | Path,
    roi_source_override: str | None = None,
) -> tuple[list[Path], str]:
    evidence = prepare_manifest_policy_evidence(
        sample=sample,
        sample_index=sample_index,
        visual_policy=visual_policy,
        run_dir=run_dir,
        repo_root=repo_root,
        roi_source_override=roi_source_override,
    )
    return evidence["image_paths"], str(evidence["roi_source"])


def prepare_manifest_policy_evidence(
    *,
    sample: dict[str, Any],
    sample_index: int,
    visual_policy: str,
    run_dir: str | Path,
    repo_root: str | Path,
    roi_source_override: str | None = None,
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
    roi_box, effective_roi_source = _box_from_sample(
        sample,
        image.width,
        image.height,
        visual_policy=visual_policy,
        roi_source_override=roi_source_override,
    )
    roi_path = out_dir / f"roi_{visual_policy}_{effective_roi_source}_448.jpg"

    if not full_path.exists():
        _resize_max_side(image, 1024).save(full_path, quality=95)
    if not low_path.exists():
        _resize_exact(image, (336, 336)).save(low_path, quality=95)
    if not roi_path.exists():
        _resize_exact(image.crop(roi_box), (448, 448)).save(roi_path, quality=95)

    target_box = _target_box_from_sample(sample, image.width, image.height)
    roi_target_iou = _box_iou(roi_box, target_box) if target_box else None
    roi_contains_target_evidence = bool(roi_target_iou is not None and roi_target_iou > 0.05)
    roi_source = effective_roi_source
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
        "roi_box_rel_xyxy": [
            round(roi_box[0] / image.width, 6),
            round(roi_box[1] / image.height, 6),
            round(roi_box[2] / image.width, 6),
            round(roi_box[3] / image.height, 6),
        ],
        "roi_box_xyxy": list(roi_box),
        "target_box_rel_xyxy": sample.get("target_box_rel_xyxy"),
        "target_box_xyxy": list(target_box) if target_box else None,
        "roi_target_iou": roi_target_iou,
        "roi_contains_target_evidence": roi_contains_target_evidence,
        "evidence_preparation": "manifest_image_resize_lowres_and_roi_crop",
    }
    return {
        "image_paths": [path for _, path in selected],
        "roi_source": roi_source,
        "source": source,
    }
