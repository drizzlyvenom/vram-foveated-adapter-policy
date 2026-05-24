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

from PIL import Image, ImageDraw, ImageFont

from vfa_policy.paths import DEFAULT_TINY_SCORED_DIR


WIDTH = 1600
HEIGHT = 1200
CENTER_CROP_REL = [0.25, 0.25, 0.75, 0.75]


TASKS: list[dict[str, Any]] = [
    {"domain": "document_or_receipt", "taxonomy_label": "document", "sample_id": "doc_invoice_code_01", "answer": "A17K", "label": "INVOICE CODE", "xy": (1160, 110)},
    {"domain": "document_or_receipt", "taxonomy_label": "document", "sample_id": "doc_receipt_gate_02", "answer": "R82M", "label": "RECEIPT GATE", "xy": (90, 870)},
    {"domain": "document_or_receipt", "taxonomy_label": "document", "sample_id": "doc_workorder_ref_03", "answer": "W45Q", "label": "WORK ORDER", "xy": (1130, 850)},
    {"domain": "document_or_receipt", "taxonomy_label": "document", "sample_id": "doc_package_tag_04", "answer": "P03L", "label": "PACKAGE TAG", "xy": (120, 90)},
    {"domain": "document_or_receipt", "taxonomy_label": "document", "sample_id": "doc_center_pass_05", "answer": "D64N", "label": "CENTER FIELD", "xy": (650, 525)},
    {"domain": "scene_text_or_ocr", "taxonomy_label": "scene_text", "sample_id": "scene_sign_code_01", "answer": "S29B", "label": "STREET SIGN", "xy": (1180, 180)},
    {"domain": "scene_text_or_ocr", "taxonomy_label": "scene_text", "sample_id": "scene_panel_code_02", "answer": "L71C", "label": "PANEL CODE", "xy": (80, 820)},
    {"domain": "scene_text_or_ocr", "taxonomy_label": "scene_text", "sample_id": "scene_badge_03", "answer": "K55T", "label": "BADGE", "xy": (1150, 760)},
    {"domain": "scene_text_or_ocr", "taxonomy_label": "scene_text", "sample_id": "scene_marker_04", "answer": "M90V", "label": "MARKER", "xy": (130, 140)},
    {"domain": "scene_text_or_ocr", "taxonomy_label": "scene_text", "sample_id": "scene_center_plate_05", "answer": "C12P", "label": "CENTER PLATE", "xy": (620, 540)},
    {"domain": "ui_screen", "taxonomy_label": "ui_screen", "sample_id": "ui_alert_code_01", "answer": "U38H", "label": "ALERT CODE", "xy": (1130, 120)},
    {"domain": "ui_screen", "taxonomy_label": "ui_screen", "sample_id": "ui_button_ref_02", "answer": "B14Z", "label": "BUTTON REF", "xy": (120, 850)},
    {"domain": "ui_screen", "taxonomy_label": "ui_screen", "sample_id": "ui_ticket_id_03", "answer": "T62R", "label": "TICKET ID", "xy": (1110, 820)},
    {"domain": "ui_screen", "taxonomy_label": "ui_screen", "sample_id": "ui_menu_key_04", "answer": "N04X", "label": "MENU KEY", "xy": (130, 130)},
    {"domain": "ui_screen", "taxonomy_label": "ui_screen", "sample_id": "ui_center_status_05", "answer": "G77Y", "label": "CENTER STATUS", "xy": (640, 540)},
    {"domain": "chart_or_table", "taxonomy_label": "chart", "sample_id": "chart_peak_label_01", "answer": "Q51E", "label": "PEAK LABEL", "xy": (1130, 120)},
    {"domain": "chart_or_table", "taxonomy_label": "chart", "sample_id": "chart_axis_code_02", "answer": "X26J", "label": "AXIS CODE", "xy": (120, 850)},
    {"domain": "chart_or_table", "taxonomy_label": "chart", "sample_id": "table_cell_ref_03", "answer": "H09S", "label": "CELL REF", "xy": (1120, 820)},
    {"domain": "chart_or_table", "taxonomy_label": "chart", "sample_id": "table_corner_key_04", "answer": "Z33A", "label": "CORNER KEY", "xy": (120, 120)},
    {"domain": "chart_or_table", "taxonomy_label": "chart", "sample_id": "chart_center_value_05", "answer": "V88D", "label": "CENTER VALUE", "xy": (620, 540)},
]


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rel_box(box: tuple[int, int, int, int]) -> list[float]:
    x0, y0, x1, y1 = box
    return [
        round(x0 / WIDTH, 6),
        round(y0 / HEIGHT, 6),
        round(x1 / WIDTH, 6),
        round(y1 / HEIGHT, 6),
    ]


def _pad_box(box: tuple[int, int, int, int], pad_x: int, pad_y: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (
        max(0, x0 - pad_x),
        max(0, y0 - pad_y),
        min(WIDTH, x1 + pad_x),
        min(HEIGHT, y1 + pad_y),
    )


def _draw_background(draw: ImageDraw.ImageDraw, task: dict[str, Any], title_font: ImageFont.ImageFont, small_font: ImageFont.ImageFont) -> None:
    domain = str(task["domain"])
    if domain == "document_or_receipt":
        draw.rectangle((80, 70, 1520, 1110), fill=(255, 255, 255), outline=(40, 40, 40), width=3)
        for y in range(240, 900, 105):
            draw.line((150, y, 1180, y), fill=(185, 185, 185), width=2)
        draw.text((140, 120), "SERVICE DOCUMENT", fill=(25, 55, 75), font=title_font)
    elif domain == "scene_text_or_ocr":
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(230, 238, 242))
        draw.rectangle((90, 760, 1520, 1120), fill=(198, 208, 214), outline=(112, 122, 128), width=2)
        draw.rectangle((150, 180, 650, 430), fill=(210, 225, 229), outline=(72, 92, 105), width=4)
        draw.text((180, 240), "FIELD VIEW", fill=(35, 60, 70), font=title_font)
    elif domain == "ui_screen":
        draw.rectangle((80, 80, 1520, 1120), fill=(246, 248, 250), outline=(35, 50, 65), width=5)
        draw.rectangle((80, 80, 1520, 180), fill=(34, 54, 73))
        draw.text((130, 115), "CONTROL PANEL", fill=(255, 255, 255), font=title_font)
        for x in range(160, 1160, 250):
            draw.rounded_rectangle((x, 310, x + 190, 430), radius=12, fill=(235, 241, 245), outline=(88, 116, 130), width=2)
            draw.text((x + 35, 350), "STATUS", fill=(70, 78, 84), font=small_font)
    else:
        draw.rectangle((80, 80, 1520, 1120), fill=(255, 255, 255), outline=(45, 45, 45), width=3)
        draw.line((220, 930, 1320, 930), fill=(40, 40, 40), width=4)
        draw.line((220, 250, 220, 930), fill=(40, 40, 40), width=4)
        for idx, value in enumerate([280, 440, 620, 360]):
            x0 = 310 + idx * 210
            draw.rectangle((x0, 930 - value, x0 + 110, 930), fill=(160, 198, 214), outline=(50, 90, 110), width=2)
        draw.text((260, 120), "QUARTERLY TABLE", fill=(25, 55, 75), font=title_font)


def _make_image(task: dict[str, Any], image_path: Path) -> dict[str, Any]:
    image = Image.new("RGB", (WIDTH, HEIGHT), (242, 244, 246))
    draw = ImageDraw.Draw(image)
    title_font = _font(44)
    label_font = _font(32)
    answer_font = _font(26)
    small_font = _font(24)

    _draw_background(draw, task, title_font, small_font)

    x, y = task["xy"]
    box = (x, y, min(WIDTH - 50, x + 360), min(HEIGHT - 40, y + 190))
    draw.rounded_rectangle(box, radius=16, fill=(255, 250, 214), outline=(210, 78, 44), width=6)
    draw.text((box[0] + 22, box[1] + 20), str(task["label"]), fill=(76, 55, 25), font=label_font)
    draw.text((box[0] + 28, box[1] + 104), str(task["answer"]), fill=(20, 30, 35), font=answer_font)
    draw.rectangle((box[0] - 14, box[1] - 14, box[2] + 14, box[3] + 14), outline=(214, 35, 35), width=5)

    image_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(image_path, quality=95)

    oracle_box = _pad_box(box, 60, 60)
    layout_box = _pad_box(box, 140, 110)
    return {
        "target_box_rel_xyxy": _rel_box(box),
        "oracle_roi_box_rel_xyxy": _rel_box(oracle_box),
        "layout_roi_box_rel_xyxy": _rel_box(layout_box),
        "ocr_roi_box_rel_xyxy": _rel_box(layout_box),
        "center_crop_roi_box_rel_xyxy": CENTER_CROP_REL,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=DEFAULT_TINY_SCORED_DIR)
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    image_dir = output_dir / "images"
    manifest_path = output_dir / "manifest.jsonl"
    selected = TASKS[: args.max_samples] if args.max_samples is not None else TASKS

    rows = []
    for index, task in enumerate(selected):
        image_path = image_dir / f"{task['sample_id']}.jpg"
        boxes = _make_image(task, image_path)
        row = {
            "sample_id": task["sample_id"],
            "taxonomy_label": task["taxonomy_label"],
            "task_family": task["domain"],
            "prompt": "Read the highlighted evidence region. Answer only the four-character code.",
            "expected_answers": [task["answer"]],
            "answer_type": "label",
            "full_image_path": str(image_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "roi_source": "center_crop",
            "roi_box_rel_xyxy": boxes["center_crop_roi_box_rel_xyxy"],
            "source_dataset": "VFA tiny scored controlled image set v0",
            "source_url": None,
            **boxes,
        }
        rows.append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(json.dumps({"manifest_path": str(manifest_path), "samples": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
