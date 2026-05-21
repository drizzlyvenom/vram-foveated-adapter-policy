from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from PIL import Image


@dataclass
class RoiPlan:
    mode: str
    boxes_xyxy: list[list[float]]
    oracle_available: bool
    oracle_coverage: float | None
    roi_recall_at_1: float | None


class PatchTransformerProfiler(torch.nn.Module):
    def __init__(
        self,
        patch_size: int = 16,
        embed_dim: int = 192,
        depth: int = 2,
        heads: int = 4,
        mlp_ratio: int = 2,
    ) -> None:
        super().__init__()
        self.patch_size = patch_size
        self.patch_embed = torch.nn.Conv2d(3, embed_dim, kernel_size=patch_size, stride=patch_size)
        layer = torch.nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=heads,
            dim_feedforward=embed_dim * mlp_ratio,
            dropout=0.0,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = torch.nn.TransformerEncoder(layer, num_layers=depth)
        self.norm = torch.nn.LayerNorm(embed_dim)

    def token_count(self, height: int, width: int) -> int:
        return (height // self.patch_size) * (width // self.patch_size)

    def forward(self, segments: list[torch.Tensor]) -> torch.Tensor:
        tokens = []
        for segment in segments:
            patch = self.patch_embed(segment)
            patch = patch.flatten(2).transpose(1, 2)
            tokens.append(patch)
        x = torch.cat(tokens, dim=1)
        x = self.encoder(x)
        return self.norm(x).mean(dim=1)


def read_manifest(path: str | Path) -> list[dict[str, Any]]:
    import json

    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_rgb(path: str | Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def resize_exact(image: Image.Image, size_hw: list[int]) -> Image.Image:
    height, width = size_hw
    return image.resize((width, height), Image.Resampling.BICUBIC)


def resize_max_side_multiple(image: Image.Image, max_side: int, patch_size: int) -> Image.Image:
    width, height = image.size
    scale = min(1.0, max_side / max(width, height))
    new_width = max(patch_size, int(width * scale))
    new_height = max(patch_size, int(height * scale))
    new_width = max(patch_size, (new_width // patch_size) * patch_size)
    new_height = max(patch_size, (new_height // patch_size) * patch_size)
    return image.resize((new_width, new_height), Image.Resampling.BICUBIC)


def image_to_tensor(image: Image.Image, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    import numpy as np

    arr = np.asarray(image, dtype="float32") / 255.0
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)
    tensor = (tensor - mean) / std
    return tensor.to(device=device, dtype=dtype, non_blocking=True)


def expand_box(box: list[float], width: int, height: int, factor: float = 2.5) -> list[float]:
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    bw = max(1.0, (x2 - x1) * factor)
    bh = max(1.0, (y2 - y1) * factor)
    side = max(bw, bh, min(width, height) * 0.18)
    return [
        max(0.0, cx - side / 2),
        max(0.0, cy - side / 2),
        min(float(width), cx + side / 2),
        min(float(height), cy + side / 2),
    ]


def center_box(width: int, height: int, frac: float = 0.45) -> list[float]:
    bw = width * frac
    bh = height * frac
    return [(width - bw) / 2, (height - bh) / 2, (width + bw) / 2, (height + bh) / 2]


def random_box(width: int, height: int, rng: random.Random, frac: float = 0.45) -> list[float]:
    bw = width * frac
    bh = height * frac
    x1 = rng.uniform(0, max(1.0, width - bw))
    y1 = rng.uniform(0, max(1.0, height - bh))
    return [x1, y1, min(width, x1 + bw), min(height, y1 + bh)]


def crop_resize(image: Image.Image, box: list[float], roi_size_hw: list[int]) -> Image.Image:
    x1, y1, x2, y2 = box
    crop = image.crop((int(x1), int(y1), int(x2), int(y2)))
    return resize_exact(crop, roi_size_hw)


def _coverage(selected: list[float], oracle: list[float]) -> float:
    sx1, sy1, sx2, sy2 = selected
    ox1, oy1, ox2, oy2 = oracle
    ix1 = max(sx1, ox1)
    iy1 = max(sy1, oy1)
    ix2 = min(sx2, ox2)
    iy2 = min(sy2, oy2)
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    oracle_area = max(1.0, (ox2 - ox1) * (oy2 - oy1))
    return inter / oracle_area


def roi_plan(record: dict[str, Any], mode: str, seed: int) -> RoiPlan:
    width = int(record["image_width"])
    height = int(record["image_height"])
    oracle_boxes = record.get("oracle_boxes_xyxy") or []
    oracle_available = bool(oracle_boxes)

    if mode == "none" or mode == "fullres":
        boxes: list[list[float]] = []
    elif mode == "random":
        boxes = [random_box(width, height, random.Random(f"{seed}:{record['sample_id']}"))]
    elif mode == "oracle" and oracle_available:
        boxes = [expand_box(oracle_boxes[0], width, height, factor=2.0)]
    elif mode == "heuristic" and oracle_available:
        boxes = [expand_box(oracle_boxes[0], width, height, factor=3.0)]
    else:
        boxes = [center_box(width, height)]

    if oracle_available and boxes:
        best = max(_coverage(box, oracle) for box in boxes for oracle in oracle_boxes)
        recall = 1.0 if best >= 0.5 else 0.0
    elif oracle_available:
        best = 0.0
        recall = 0.0
    else:
        best = None
        recall = None

    return RoiPlan(
        mode=mode,
        boxes_xyxy=boxes,
        oracle_available=oracle_available,
        oracle_coverage=best,
        roi_recall_at_1=recall,
    )


def make_segments(
    image: Image.Image,
    plan: RoiPlan,
    low_res_hw: list[int],
    roi_res_hw: list[int],
    full_res_max_side: int,
    patch_size: int,
) -> list[Image.Image]:
    if plan.mode == "fullres":
        return [resize_max_side_multiple(image, full_res_max_side, patch_size)]
    segments = [resize_exact(image, low_res_hw)]
    for box in plan.boxes_xyxy:
        segments.append(crop_resize(image, box, roi_res_hw))
    return segments


def count_tokens(model: PatchTransformerProfiler, segments: list[Image.Image]) -> int:
    return sum(model.token_count(seg.size[1], seg.size[0]) for seg in segments)


def profile_segments(
    model: PatchTransformerProfiler,
    segments: list[Image.Image],
    device: torch.device,
    dtype: torch.dtype,
) -> dict[str, Any]:
    tensors = [image_to_tensor(seg, device, dtype) for seg in segments]
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device)
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    failure = None
    output_norm = None
    try:
        with torch.inference_mode():
            output = model(tensors)
            output_norm = float(output.float().norm().detach().cpu().item())
        end.record()
        torch.cuda.synchronize(device)
        latency_ms = float(start.elapsed_time(end))
    except RuntimeError as exc:
        torch.cuda.synchronize(device)
        latency_ms = None
        failure = str(exc)
    peak_vram_mb = torch.cuda.max_memory_allocated(device) / (1024 * 1024)
    reserved_vram_mb = torch.cuda.max_memory_reserved(device) / (1024 * 1024)
    del tensors
    torch.cuda.empty_cache()
    return {
        "latency_ms": latency_ms,
        "peak_vram_mb": peak_vram_mb,
        "reserved_vram_mb": reserved_vram_mb,
        "output_norm": output_norm,
        "failure": failure,
    }


def warmup(model: PatchTransformerProfiler, device: torch.device, dtype: torch.dtype, low_res_hw: list[int]) -> None:
    image = Image.new("RGB", (low_res_hw[1], low_res_hw[0]), color=(127, 127, 127))
    _ = profile_segments(model, [image], device, dtype)
    time.sleep(0.05)
