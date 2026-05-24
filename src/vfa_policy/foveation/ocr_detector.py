from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class OcrDetectionResult:
    available: bool
    engine: str
    box_xyxy: tuple[int, int, int, int] | None
    text: str
    confidence_mean: float | None
    error_type: str | None = None
    error_message: str | None = None


def _clip_box(box: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    x0 = max(0, min(width - 1, int(x0)))
    y0 = max(0, min(height - 1, int(y0)))
    x1 = max(x0 + 1, min(width, int(x1)))
    y1 = max(y0 + 1, min(height, int(y1)))
    return x0, y0, x1, y1


def _pad_box(
    box: tuple[int, int, int, int],
    *,
    width: int,
    height: int,
    pad_px: int,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return _clip_box((x0 - pad_px, y0 - pad_px, x1 + pad_px, y1 + pad_px), width, height)


def rel_box(box: tuple[int, int, int, int], *, width: int, height: int) -> list[float]:
    x0, y0, x1, y1 = box
    return [
        round(x0 / width, 6),
        round(y0 / height, 6),
        round(x1 / width, 6),
        round(y1 / height, 6),
    ]


def detect_ocr_roi_with_pytesseract(
    image_path: str | Path,
    *,
    min_confidence: float = 25.0,
    pad_px: int = 32,
) -> OcrDetectionResult:
    """Return a detector ROI from all confident OCR words without using labels."""

    try:
        import pytesseract
    except ImportError as exc:
        return OcrDetectionResult(
            available=False,
            engine="pytesseract",
            box_xyxy=None,
            text="",
            confidence_mean=None,
            error_type=type(exc).__name__,
            error_message="pytesseract is not installed; install requirements-ocr.txt and Tesseract OCR.",
        )

    path = Path(image_path)
    try:
        image = Image.open(path).convert("RGB")
        data: dict[str, list[Any]] = pytesseract.image_to_data(
            image,
            output_type=pytesseract.Output.DICT,
        )
    except Exception as exc:
        return OcrDetectionResult(
            available=False,
            engine="pytesseract",
            box_xyxy=None,
            text="",
            confidence_mean=None,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    boxes: list[tuple[int, int, int, int]] = []
    texts: list[str] = []
    confidences: list[float] = []
    for idx, raw_text in enumerate(data.get("text", [])):
        text = str(raw_text or "").strip()
        if not text:
            continue
        try:
            confidence = float(data.get("conf", [])[idx])
        except (TypeError, ValueError, IndexError):
            confidence = -1.0
        if confidence < min_confidence:
            continue
        left = int(float(data["left"][idx]))
        top = int(float(data["top"][idx]))
        width = int(float(data["width"][idx]))
        height = int(float(data["height"][idx]))
        if width <= 0 or height <= 0:
            continue
        boxes.append((left, top, left + width, top + height))
        texts.append(text)
        confidences.append(confidence)

    if not boxes:
        return OcrDetectionResult(
            available=False,
            engine="pytesseract",
            box_xyxy=None,
            text="",
            confidence_mean=None,
            error_type="NoTextBoxes",
            error_message=f"No OCR boxes met min_confidence={min_confidence}.",
        )

    union = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )
    padded = _pad_box(union, width=image.width, height=image.height, pad_px=int(pad_px))
    return OcrDetectionResult(
        available=True,
        engine="pytesseract",
        box_xyxy=padded,
        text=" ".join(texts),
        confidence_mean=round(float(mean(confidences)), 3) if confidences else None,
    )


def _quad_to_box(points: Any) -> tuple[int, int, int, int] | None:
    try:
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
    except (TypeError, ValueError, IndexError):
        return None
    if not xs or not ys:
        return None
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def detect_ocr_roi_with_rapidocr(
    image_path: str | Path,
    *,
    min_confidence: float = 0.5,
    pad_px: int = 32,
) -> OcrDetectionResult:
    """Return a detector ROI using RapidOCR/ONNXRuntime without Tesseract."""

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        return OcrDetectionResult(
            available=False,
            engine="rapidocr",
            box_xyxy=None,
            text="",
            confidence_mean=None,
            error_type=type(exc).__name__,
            error_message="rapidocr-onnxruntime is not installed; install requirements-ocr.txt.",
        )

    path = Path(image_path)
    try:
        image = Image.open(path).convert("RGB")
        engine = RapidOCR()
        result, _ = engine(path)
    except Exception as exc:
        return OcrDetectionResult(
            available=False,
            engine="rapidocr",
            box_xyxy=None,
            text="",
            confidence_mean=None,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    boxes: list[tuple[int, int, int, int]] = []
    texts: list[str] = []
    confidences: list[float] = []
    for item in result or []:
        if len(item) < 3:
            continue
        box = _quad_to_box(item[0])
        text = str(item[1] or "").strip()
        try:
            confidence = float(item[2])
        except (TypeError, ValueError):
            confidence = -1.0
        if not box or not text or confidence < min_confidence:
            continue
        boxes.append(box)
        texts.append(text)
        confidences.append(confidence)

    if not boxes:
        return OcrDetectionResult(
            available=False,
            engine="rapidocr",
            box_xyxy=None,
            text="",
            confidence_mean=None,
            error_type="NoTextBoxes",
            error_message=f"No OCR boxes met min_confidence={min_confidence}.",
        )

    union = (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )
    padded = _pad_box(union, width=image.width, height=image.height, pad_px=int(pad_px))
    return OcrDetectionResult(
        available=True,
        engine="rapidocr",
        box_xyxy=padded,
        text=" ".join(texts),
        confidence_mean=round(float(mean(confidences)), 3) if confidences else None,
    )


def detect_ocr_roi(
    image_path: str | Path,
    *,
    engine: str = "rapidocr",
    min_confidence: float | None = None,
    pad_px: int = 32,
) -> OcrDetectionResult:
    if engine == "rapidocr":
        return detect_ocr_roi_with_rapidocr(
            image_path,
            min_confidence=0.5 if min_confidence is None else float(min_confidence),
            pad_px=pad_px,
        )
    if engine == "pytesseract":
        return detect_ocr_roi_with_pytesseract(
            image_path,
            min_confidence=25.0 if min_confidence is None else float(min_confidence),
            pad_px=pad_px,
        )
    return OcrDetectionResult(
        available=False,
        engine=engine,
        box_xyxy=None,
        text="",
        confidence_mean=None,
        error_type="UnsupportedEngine",
        error_message=f"Unsupported OCR engine: {engine}",
    )
