from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from vfa_policy.core.memory_accounting import estimate_kv_cache_mb
from vfa_policy.foveation.roi_metrics import visual_estimate


@dataclass(frozen=True)
class RealProbeLoadResult:
    allocated_mb: float
    reserved_mb: float
    measurement_source: str
    model_load_latency_ms: float
    gpu_name: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealVisualMeasurement:
    visual: dict[str, Any]
    memory: dict[str, Any]
    timing: dict[str, Any]
    answer_text: str


def _mb(value_bytes: int | float) -> float:
    return round(float(value_bytes) / (1024.0 * 1024.0), 3)


def _cuda_allocated_mb(torch_module: Any) -> float:
    return _mb(torch_module.cuda.memory_allocated())


def _cuda_reserved_mb(torch_module: Any) -> float:
    return _mb(torch_module.cuda.memory_reserved())


def _cuda_peak_allocated_mb(torch_module: Any) -> float:
    return _mb(torch_module.cuda.max_memory_allocated())


def _sync(torch_module: Any) -> None:
    if torch_module.cuda.is_available():
        torch_module.cuda.synchronize()


def _reset_peak(torch_module: Any) -> None:
    _sync(torch_module)
    torch_module.cuda.reset_peak_memory_stats()


def _dtype_from_name(torch_module: Any, dtype_name: str) -> Any:
    normalized = (dtype_name or "float16").lower()
    if normalized in {"float16", "fp16", "half"}:
        return torch_module.float16
    if normalized in {"bfloat16", "bf16"}:
        return torch_module.bfloat16
    if normalized in {"float32", "fp32"}:
        return torch_module.float32
    return torch_module.float16


def make_probe_images(output_dir: str | Path) -> dict[str, Path]:
    """Create deterministic local probe images for R0/R3 accounting."""

    from PIL import Image, ImageDraw, ImageFont

    image_dir = Path(output_dir) / "probe_images"
    image_dir.mkdir(parents=True, exist_ok=True)

    def save_probe(path: Path, size: tuple[int, int], title: str, detail: str) -> Path:
        image = Image.new("RGB", size, (246, 248, 250))
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        w, h = size
        draw.rectangle((24, 24, w - 24, h - 24), outline=(36, 94, 130), width=4)
        draw.rectangle((48, 72, w - 48, 150), fill=(224, 239, 244), outline=(36, 94, 130), width=2)
        draw.text((64, 96), title, fill=(12, 38, 52), font=font)
        for idx, label in enumerate(["DOC", "ROI", "VRAM", "3090"]):
            x0 = 72 + (idx % 2) * (w // 2 - 40)
            y0 = 220 + (idx // 2) * 160
            draw.rounded_rectangle((x0, y0, x0 + w // 3, y0 + 90), radius=8, fill=(255, 255, 255), outline=(82, 122, 140), width=2)
            draw.text((x0 + 18, y0 + 28), f"{label}: {idx + 1}", fill=(18, 54, 70), font=font)
        draw.text((64, h - 96), detail, fill=(72, 72, 72), font=font)
        image.save(path)
        return path

    return {
        "full": save_probe(image_dir / "probe_full_1024.png", (1024, 1024), "Full visual context", "Full 1024x1024 probe"),
        "low": save_probe(image_dir / "probe_low_336.png", (336, 336), "Low-res global view", "Global 336x336 probe"),
        "roi": save_probe(image_dir / "probe_roi_448.png", (448, 448), "High-res ROI glimpse", "ROI 448x448 probe"),
    }


def image_paths_for_policy(visual_policy: str, image_bank: dict[str, Path]) -> list[Path]:
    if visual_policy == "full_image":
        return [image_bank["full"]]
    if visual_policy == "low_res_only":
        return [image_bank["low"]]
    if visual_policy in {"foveater_roi", "oracle_roi", "foveater_roi_controlled_fallback"}:
        return [image_bank["low"], image_bank["roi"]]
    return [image_bank["full"]]


def _token_counts_from_grid(image_grid_thw: Any, merge_size: int) -> list[int]:
    if image_grid_thw is None:
        return []
    rows = image_grid_thw.detach().cpu().tolist()
    counts: list[int] = []
    divisor = max(1, int(merge_size) ** 2)
    for row in rows:
        if len(row) < 3:
            continue
        t, h, w = (int(row[0]), int(row[1]), int(row[2]))
        counts.append(int((t * h * w) / divisor))
    return counts


def _split_visual_counts(visual_policy: str, per_image_tokens: list[int]) -> dict[str, int]:
    total = int(sum(per_image_tokens))
    if visual_policy == "low_res_only":
        return {"visual_token_count": total, "global_token_count": total, "roi_token_count": 0, "roi_count": 0}
    if visual_policy in {"foveater_roi", "oracle_roi", "foveater_roi_controlled_fallback"}:
        global_tokens = per_image_tokens[0] if per_image_tokens else 0
        roi_tokens = int(sum(per_image_tokens[1:]))
        return {
            "visual_token_count": total,
            "global_token_count": int(global_tokens),
            "roi_token_count": roi_tokens,
            "roi_count": max(0, len(per_image_tokens) - 1),
        }
    return {"visual_token_count": total, "global_token_count": 0, "roi_token_count": total, "roi_count": 0}


class Qwen3VLRealProbe:
    def __init__(
        self,
        *,
        model_path: str | Path,
        dtype_name: str = "float16",
        run_dir: str | Path,
        max_new_tokens: int = 4,
    ) -> None:
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available; R0 real measurement requires the RTX 3090 CUDA device.")

        self.torch = torch
        self.device = "cuda:0"
        self.max_new_tokens = int(max_new_tokens)
        self.measurement_source = "qwen3_vl_4b_local_cuda_prefill_generate"
        self.image_bank = make_probe_images(run_dir)

        model_path = Path(model_path)
        dtype = _dtype_from_name(torch, dtype_name)
        started = time.perf_counter()
        self.processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=True,
            local_files_only=True,
        )
        load_kwargs = {
            "trust_remote_code": True,
            "local_files_only": True,
            "device_map": {"": self.device},
            "dtype": dtype,
            "attn_implementation": "sdpa",
        }
        try:
            self.model = AutoModelForImageTextToText.from_pretrained(model_path, **load_kwargs)
        except TypeError:
            load_kwargs.pop("dtype", None)
            load_kwargs["torch_dtype"] = dtype
            self.model = AutoModelForImageTextToText.from_pretrained(model_path, **load_kwargs)
        self.model.eval()
        _sync(torch)
        self.load_result = RealProbeLoadResult(
            allocated_mb=_cuda_allocated_mb(torch),
            reserved_mb=_cuda_reserved_mb(torch),
            measurement_source=self.measurement_source,
            model_load_latency_ms=round((time.perf_counter() - started) * 1000.0, 3),
            gpu_name=torch.cuda.get_device_name(0),
        )

    def _messages(self, image_paths: list[Path], prompt: str) -> list[dict[str, Any]]:
        content = [{"type": "image", "image": str(path)} for path in image_paths]
        content.append({"type": "text", "text": prompt})
        return [{"role": "user", "content": content}]

    def _prepare_inputs(self, image_paths: list[Path], prompt: str) -> tuple[Any, list[int]]:
        from qwen_vl_utils import process_vision_info

        messages = self._messages(image_paths, prompt)
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        merge_size = getattr(getattr(self.processor, "image_processor", None), "merge_size", None)
        if merge_size is None:
            merge_size = getattr(getattr(self.processor, "image_processor", None), "spatial_merge_size", 2)
        per_image_tokens = _token_counts_from_grid(inputs.get("image_grid_thw"), int(merge_size or 2))
        return inputs, per_image_tokens

    def measure_visual_policy(
        self,
        *,
        visual_policy: str,
        prompt: str,
        max_new_tokens: int | None = None,
    ) -> RealVisualMeasurement:
        torch = self.torch
        image_paths = image_paths_for_policy(visual_policy, self.image_bank)
        cpu_inputs, per_image_tokens = self._prepare_inputs(image_paths, prompt)
        split_counts = _split_visual_counts(visual_policy, per_image_tokens)
        estimate = visual_estimate(visual_policy)

        torch.cuda.empty_cache()
        _sync(torch)
        prefill_baseline = max(_cuda_allocated_mb(torch), self.load_result.allocated_mb)
        _reset_peak(torch)
        started = time.perf_counter()
        with torch.inference_mode():
            cuda_inputs = cpu_inputs.to(self.device)
            outputs = self.model(**cuda_inputs, use_cache=True)
        _sync(torch)
        prefill_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        prefill_peak_abs_mb = _cuda_peak_allocated_mb(torch)
        visual_incremental_peak_mb = round(max(0.0, prefill_peak_abs_mb - prefill_baseline), 3)
        del outputs
        del cuda_inputs
        del cpu_inputs
        torch.cuda.empty_cache()
        _sync(torch)

        generate_inputs, _ = self._prepare_inputs(image_paths, prompt)
        torch.cuda.empty_cache()
        _sync(torch)
        generate_baseline = max(_cuda_allocated_mb(torch), self.load_result.allocated_mb)
        _reset_peak(torch)
        started = time.perf_counter()
        with torch.inference_mode():
            cuda_generate_inputs = generate_inputs.to(self.device)
            generated = self.model.generate(
                **cuda_generate_inputs,
                max_new_tokens=int(max_new_tokens or self.max_new_tokens),
                do_sample=False,
            )
        _sync(torch)
        generation_latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        generate_peak_abs_mb = _cuda_peak_allocated_mb(torch)
        generate_incremental_peak_mb = round(max(0.0, generate_peak_abs_mb - generate_baseline), 3)
        decode_incremental_peak_mb = round(max(0.0, generate_incremental_peak_mb - visual_incremental_peak_mb), 3)
        answer_text = self.processor.batch_decode(generated, skip_special_tokens=True)[0]
        del generated
        del cuda_generate_inputs
        del generate_inputs
        torch.cuda.empty_cache()
        _sync(torch)

        visual = dict(estimate)
        visual.update(split_counts)
        visual["policy"] = visual_policy
        visual["per_image_visual_tokens"] = per_image_tokens
        visual["visual_token_count_source"] = "qwen3_vl_image_grid_thw"
        visual["kv_cache_estimate_mb"] = estimate_kv_cache_mb(visual.get("visual_token_count"))
        visual["prefill_latency_ms"] = prefill_latency_ms
        visual["generation_latency_ms"] = generation_latency_ms
        visual["prefill_peak_abs_mb"] = prefill_peak_abs_mb
        visual["generate_peak_abs_mb"] = generate_peak_abs_mb
        if estimate.get("full_image_visual_token_count_reference"):
            visual["dry_run_reference_tokens"] = estimate.get("full_image_visual_token_count_reference")
            visual["full_image_visual_token_count_reference"] = None
            visual["visual_token_reduction_vs_full"] = None

        memory = {
            "visual_incremental_peak_mb": visual_incremental_peak_mb,
            "decode_incremental_peak_mb": decode_incremental_peak_mb,
            "generate_incremental_peak_mb": generate_incremental_peak_mb,
            "prefill_baseline_allocated_mb": round(prefill_baseline, 3),
            "generate_baseline_allocated_mb": round(generate_baseline, 3),
            "prefill_peak_abs_mb": prefill_peak_abs_mb,
            "generate_peak_abs_mb": generate_peak_abs_mb,
            "measurement_source": self.measurement_source,
        }
        timing = {
            "prefill_latency_ms": prefill_latency_ms,
            "generation_latency_ms": generation_latency_ms,
        }
        return RealVisualMeasurement(visual=visual, memory=memory, timing=timing, answer_text=answer_text)
