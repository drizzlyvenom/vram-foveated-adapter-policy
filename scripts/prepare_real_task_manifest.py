from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]


COCO_SAMPLES = [
    {
        "sample_id": "coco_cats_039769",
        "taxonomy_label": "scene_text",
        "url": "http://images.cocodataset.org/val2017/000000039769.jpg",
        "prompt": "Describe the main animals and visible objects in this image in one short sentence.",
        "roi_box_rel_xyxy": [0.08, 0.10, 0.92, 0.92],
        "roi_source": "center_crop",
        "source_dataset": "COCO val2017",
    },
    {
        "sample_id": "coco_street_000139",
        "taxonomy_label": "scene_text",
        "url": "http://images.cocodataset.org/val2017/000000000139.jpg",
        "prompt": "Describe the main scene and the most salient object in one short sentence.",
        "roi_box_rel_xyxy": [0.15, 0.12, 0.88, 0.88],
        "roi_source": "center_crop",
        "source_dataset": "COCO val2017",
    },
    {
        "sample_id": "coco_scene_000785",
        "taxonomy_label": "ui_screen",
        "url": "http://images.cocodataset.org/val2017/000000000785.jpg",
        "prompt": "Describe the central visual evidence in one short sentence.",
        "roi_box_rel_xyxy": [0.18, 0.18, 0.82, 0.82],
        "roi_source": "center_crop",
        "source_dataset": "COCO val2017",
    },
    {
        "sample_id": "coco_scene_000632",
        "taxonomy_label": "chart",
        "url": "http://images.cocodataset.org/val2017/000000000632.jpg",
        "prompt": "Describe the most important visible region in one short sentence.",
        "roi_box_rel_xyxy": [0.12, 0.12, 0.88, 0.88],
        "roi_source": "center_crop",
        "source_dataset": "COCO val2017",
    },
]


PICSUM_HIGHRES_SAMPLES = [
    {
        "sample_id": "picsum_highres_1",
        "taxonomy_label": "scene_text",
        "url": "https://picsum.photos/seed/vfa_real_1/1600/1200",
        "prompt": "Describe the central visual scene in one short sentence.",
        "roi_box_rel_xyxy": [0.18, 0.16, 0.82, 0.84],
        "roi_source": "center_crop",
        "source_dataset": "Lorem Picsum high-resolution real image smoke",
    },
    {
        "sample_id": "picsum_highres_2",
        "taxonomy_label": "document",
        "url": "https://picsum.photos/seed/vfa_real_2/1600/1200",
        "prompt": "Describe the main visible evidence in one short sentence.",
        "roi_box_rel_xyxy": [0.15, 0.15, 0.85, 0.85],
        "roi_source": "center_crop",
        "source_dataset": "Lorem Picsum high-resolution real image smoke",
    },
    {
        "sample_id": "picsum_highres_3",
        "taxonomy_label": "ui_screen",
        "url": "https://picsum.photos/seed/vfa_real_3/1600/1200",
        "prompt": "Describe the most salient visual region in one short sentence.",
        "roi_box_rel_xyxy": [0.20, 0.18, 0.80, 0.82],
        "roi_source": "center_crop",
        "source_dataset": "Lorem Picsum high-resolution real image smoke",
    },
    {
        "sample_id": "picsum_highres_4",
        "taxonomy_label": "chart",
        "url": "https://picsum.photos/seed/vfa_real_4/1600/1200",
        "prompt": "Describe the central visual evidence in one short sentence.",
        "roi_box_rel_xyxy": [0.16, 0.16, 0.84, 0.84],
        "roi_source": "center_crop",
        "source_dataset": "Lorem Picsum high-resolution real image smoke",
    },
]


SAMPLE_SETS = {
    "picsum_highres": PICSUM_HIGHRES_SAMPLES,
    "coco_val2017": COCO_SAMPLES,
}


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return
    with urlopen(url, timeout=60) as response:
        payload = response.read()
    destination.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/real_task_smoke")
    parser.add_argument("--source", choices=sorted(SAMPLE_SETS), default="picsum_highres")
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()

    output_dir = (REPO_ROOT / args.output_dir).resolve()
    image_dir = output_dir / "images"
    manifest_path = output_dir / "manifest.jsonl"
    source_samples = SAMPLE_SETS[args.source]
    max_samples = args.max_samples if args.max_samples is not None else len(source_samples)
    selected = source_samples[: max(1, min(max_samples, len(source_samples)))]

    rows = []
    for sample in selected:
        image_path = image_dir / f"{sample['sample_id']}.jpg"
        _download(str(sample["url"]), image_path)
        row = {
            "sample_id": sample["sample_id"],
            "taxonomy_label": sample["taxonomy_label"],
            "prompt": sample["prompt"],
            "full_image_path": str(image_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "roi_box_rel_xyxy": sample["roi_box_rel_xyxy"],
            "roi_source": sample["roi_source"],
            "source_dataset": sample["source_dataset"],
            "source_url": sample["url"],
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
