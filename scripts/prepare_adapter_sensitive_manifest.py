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

from vfa_policy.logging_utils import append_jsonl, write_json
from vfa_policy.track_a.taxonomy import TAXONOMY_PROFILES, taxonomy_key

WIDTH = 1280
HEIGHT = 900


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rel(box: tuple[int, int, int, int]) -> list[float]:
    return [round(box[0] / WIDTH, 6), round(box[1] / HEIGHT, 6), round(box[2] / WIDTH, 6), round(box[3] / HEIGHT, 6)]


def _pad(box: tuple[int, int, int, int], pad: int = 70) -> tuple[int, int, int, int]:
    return (max(0, box[0] - pad), max(0, box[1] - pad), min(WIDTH, box[2] + pad), min(HEIGHT, box[3] + pad))


def _answer(domain_index: int, idx: int, split: str) -> str:
    base = 1000 if split == "train" else 5000
    return f"{chr(65 + domain_index)}{base + idx * 17:04d}{chr(65 + ((idx * 7 + domain_index) % 26))}"


def _draw_domain_background(draw: ImageDraw.ImageDraw, taxonomy: dict[str, str]) -> None:
    title = _font(38)
    small = _font(22)
    domain = taxonomy["domain"]
    if domain == "document":
        draw.rectangle((70, 55, 1210, 845), fill=(255, 255, 250), outline=(40, 40, 40), width=3)
        draw.text((105, 90), "SERVICE FORM", fill=(20, 50, 70), font=title)
        for y in range(190, 790, 85):
            draw.line((120, y, 930, y), fill=(190, 190, 190), width=2)
    elif domain == "scene_text":
        draw.rectangle((0, 0, WIDTH, HEIGHT), fill=(218, 229, 233))
        draw.rectangle((110, 230, 560, 440), fill=(240, 245, 236), outline=(60, 80, 90), width=4)
        draw.text((145, 285), "FIELD SIGN", fill=(30, 60, 75), font=title)
        draw.rectangle((0, 680, WIDTH, HEIGHT), fill=(176, 188, 195))
    elif domain == "ui_screen":
        draw.rectangle((70, 60, 1210, 840), fill=(247, 250, 252), outline=(35, 52, 70), width=5)
        draw.rectangle((70, 60, 1210, 145), fill=(34, 54, 73))
        draw.text((105, 88), "CONTROL UI", fill=(255, 255, 255), font=title)
        for x in range(140, 950, 220):
            draw.rounded_rectangle((x, 260, x + 160, 360), radius=10, fill=(230, 237, 242), outline=(95, 110, 125), width=2)
            draw.text((x + 22, 300), "BUTTON", fill=(70, 80, 90), font=small)
    else:
        draw.rectangle((70, 60, 1210, 840), fill=(255, 255, 255), outline=(40, 40, 40), width=3)
        draw.text((105, 88), "REGIONAL TABLE", fill=(20, 50, 70), font=title)
        for x in range(180, 1120, 170):
            draw.line((x, 210, x, 780), fill=(190, 190, 190), width=2)
        for y in range(220, 790, 90):
            draw.line((150, y, 1130, y), fill=(190, 190, 190), width=2)


def _make_row(taxonomy: dict[str, str], domain_index: int, idx: int, split: str, out_dir: Path) -> dict[str, Any]:
    image = Image.new("RGB", (WIDTH, HEIGHT), (242, 244, 246))
    draw = ImageDraw.Draw(image)
    _draw_domain_background(draw, taxonomy)
    label_font = _font(28)
    answer_font = _font(22 if idx % 3 == 0 else 25)
    small_font = _font(20)

    positions = [(90, 690), (830, 110), (95, 130), (825, 650), (470, 415), (30, 420), (960, 420), (430, 70)]
    x, y = positions[idx % len(positions)]
    answer = _answer(domain_index, idx, split)
    label_by_domain = {
        "document": "WORK ORDER",
        "scene_text": "PANEL CODE",
        "ui_screen": "DISABLED ALERT",
        "chart": "Q2 EAST",
    }
    prompt_by_domain = {
        "document": "Return the code next to WORK ORDER.",
        "scene_text": "Return the small code printed on the PANEL CODE sign.",
        "ui_screen": "Return the alert code beside the disabled button.",
        "chart": "Return the code in row Q2 and column East.",
    }
    label = label_by_domain[taxonomy["domain"]]
    box = (x, y, min(WIDTH - 40, x + 335), min(HEIGHT - 35, y + 145))
    draw.rounded_rectangle(box, radius=12, fill=(255, 249, 215), outline=(205, 73, 45), width=5)
    draw.text((box[0] + 18, box[1] + 18), label, fill=(70, 50, 25), font=label_font)
    draw.text((box[0] + 22, box[1] + 86), answer, fill=(15, 22, 28), font=answer_font)
    hard_negatives: list[str] = []
    for d_idx in range(5):
        neg = _answer(domain_index, idx + d_idx + 41, "holdout" if split == "train" else "train")
        hard_negatives.append(neg)
        dx = 180 + (d_idx % 3) * 310
        dy = 245 + (d_idx // 3) * 245
        if box[0] - 40 <= dx <= box[2] + 40 and box[1] - 40 <= dy <= box[3] + 40:
            dy = max(180, dy - 150)
        draw.rounded_rectangle((dx, dy, dx + 210, dy + 62), radius=9, fill=(232, 236, 238), outline=(150, 160, 166), width=1)
        draw.text((dx + 15, dy + 18), neg, fill=(92, 102, 110), font=small_font)

    sample_id = f"tracka_{taxonomy['domain']}_{split}_{idx + 1:04d}"
    image_path = out_dir / "images" / f"{sample_id}.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(image_path, quality=95)
    oracle = _pad(box, 55)
    layout = _pad(box, 125)
    return {
        "sample_id": sample_id,
        "split": split,
        "taxonomy_label": taxonomy["domain"],
        "taxonomy_v2": taxonomy,
        "taxonomy_key": taxonomy_key(taxonomy),
        "task_family": f"track_a_v2_{taxonomy['domain']}",
        "prompt": prompt_by_domain[taxonomy["domain"]],
        "expected_answers": [answer],
        "hard_negatives": hard_negatives,
        "answer_type": "label",
        "difficulty": "adapter_sensitive",
        "full_image_path": str(image_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "target_box_rel_xyxy": _rel(box),
        "oracle_roi_box_rel_xyxy": _rel(oracle),
        "layout_roi_box_rel_xyxy": _rel(layout),
        "layout_proxy_roi_box_rel_xyxy": _rel(layout),
        "detector_proxy_roi_box_rel_xyxy": _rel(layout),
        "ocr_roi_box_rel_xyxy": _rel(layout),
        "roi_box_rel_xyxy": [0.25, 0.25, 0.75, 0.75],
        "source_dataset": "track_a_v2_adapter_sensitive_synthetic",
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _write_brief(path: Path, rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    lines = [
        "# Track A v2 Adapter-Sensitive Dataset Brief",
        "",
        "## 요약",
        "",
        "Track A v2 certification을 위해 taxonomy별 adapter-sensitive synthetic manifest를 생성했다.",
        "",
        "```yaml",
        f"manifest: \"{summary['manifest_path']}\"",
        f"samples: {summary['samples']}",
        f"train_samples: {summary['train_samples']}",
        f"holdout_samples: {summary['holdout_samples']}",
        "promotion_claim: false",
        "```",
        "",
        "## Claim Boundary",
        "",
        "- safe: manifest/schema/input generation path is available",
        "- not_yet: trained LoRA gain, router utility, broad benchmark generalization",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=".local/data/track_a_v2_adapter_sensitive")
    parser.add_argument("--train-per-taxonomy", type=int, default=32)
    parser.add_argument("--holdout-per-taxonomy", type=int, default=32)
    parser.add_argument("--brief", default="docs/20_results/2026-05-25_track_a_v2_dataset_brief_ko.md")
    args = parser.parse_args()

    out_dir = (REPO_ROOT / args.output_dir).resolve()
    rows: list[dict[str, Any]] = []
    for domain_index, taxonomy in enumerate(TAXONOMY_PROFILES):
        for idx in range(args.train_per_taxonomy):
            rows.append(_make_row(taxonomy, domain_index, idx, "train", out_dir))
        for idx in range(args.holdout_per_taxonomy):
            rows.append(_make_row(taxonomy, domain_index, idx, "holdout", out_dir))

    train_rows = [row for row in rows if row["split"] == "train"]
    holdout_rows = [row for row in rows if row["split"] == "holdout"]
    manifest = out_dir / "manifest.jsonl"
    _write_jsonl(manifest, rows)
    _write_jsonl(out_dir / "train.jsonl", train_rows)
    _write_jsonl(out_dir / "holdout.jsonl", holdout_rows)
    summary = {
        "manifest_path": str(manifest.relative_to(REPO_ROOT)).replace("\\", "/"),
        "samples": len(rows),
        "train_samples": len(train_rows),
        "holdout_samples": len(holdout_rows),
        "taxonomies": [taxonomy_key(item) for item in TAXONOMY_PROFILES],
    }
    write_json(out_dir / "manifest_summary.json", summary)
    _write_brief(REPO_ROOT / args.brief, rows, summary)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
