from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None, digits: int = 3) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


@dataclass(frozen=True)
class AfterLoadMemory:
    allocated_mb: float
    reserved_mb: float
    measurement_source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_after_load_allocated_mb": self.allocated_mb,
            "base_after_load_reserved_mb": self.reserved_mb,
            "measurement_source": self.measurement_source,
        }


@dataclass(frozen=True)
class PeakMemoryBreakdown:
    base_after_load_allocated_mb: float
    base_after_load_reserved_mb: float
    adapter_bank_resident_mb: float
    active_adapter_resident_mb: float
    visual_incremental_peak_mb: float
    decode_incremental_peak_mb: float
    total_peak_mb: float
    normal_path_peak_mb: float
    controlled_fallback_peak_mb: float | None
    emergency_fallback_peak_mb: float | None
    measurement_source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def record_after_model_load(
    allocated_mb: float | None = None,
    reserved_mb: float | None = None,
    *,
    fallback_allocated_mb: float = 8420.5,
    fallback_reserved_mb: float = 9200.0,
    measurement_source: str = "dry_run_config_estimate",
) -> AfterLoadMemory:
    """Record or estimate memory immediately after loading the shared backbone."""

    allocated = _float_or_none(allocated_mb)
    reserved = _float_or_none(reserved_mb)
    return AfterLoadMemory(
        allocated_mb=_round(allocated if allocated is not None else fallback_allocated_mb, 3) or 0.0,
        reserved_mb=_round(reserved if reserved is not None else fallback_reserved_mb, 3) or 0.0,
        measurement_source=measurement_source,
    )


def compute_incremental_peak(after_load_mb: float | None, peak_mb: float | None) -> float | None:
    after_load = _float_or_none(after_load_mb)
    peak = _float_or_none(peak_mb)
    if after_load is None or peak is None:
        return None
    return _round(max(0.0, peak - after_load), 3)


def estimate_multi_specialist_residency(
    per_model_after_load_mb: float | None,
    specialist_count: int,
) -> float | None:
    per_model = _float_or_none(per_model_after_load_mb)
    if per_model is None or specialist_count <= 0:
        return None
    return _round(per_model * specialist_count, 3)


def compute_resident_saving(
    shared_plus_lora_resident_mb: float | None,
    multi_specialist_resident_estimate_mb: float | None,
) -> float | None:
    shared = _float_or_none(shared_plus_lora_resident_mb)
    multi = _float_or_none(multi_specialist_resident_estimate_mb)
    if shared is None or multi is None or multi <= 0:
        return None
    return _round(1.0 - (shared / multi), 6)


def record_peak_memory(
    *,
    after_load: AfterLoadMemory,
    adapter_bank_resident_mb: float = 0.0,
    active_adapter_resident_mb: float = 0.0,
    visual_incremental_peak_mb: float = 0.0,
    decode_incremental_peak_mb: float = 0.0,
    controlled_fallback_extra_mb: float | None = None,
    emergency_fallback_extra_mb: float | None = None,
    measurement_source: str = "dry_run_config_estimate",
) -> PeakMemoryBreakdown:
    """Build the separated memory accounting required by the 3090 contract."""

    normal = (
        after_load.allocated_mb
        + float(adapter_bank_resident_mb or 0.0)
        + float(visual_incremental_peak_mb or 0.0)
        + float(decode_incremental_peak_mb or 0.0)
    )
    controlled = None
    if controlled_fallback_extra_mb is not None:
        controlled = normal + float(controlled_fallback_extra_mb)
    emergency = None
    if emergency_fallback_extra_mb is not None:
        emergency = normal + float(emergency_fallback_extra_mb)

    return PeakMemoryBreakdown(
        base_after_load_allocated_mb=_round(after_load.allocated_mb) or 0.0,
        base_after_load_reserved_mb=_round(after_load.reserved_mb) or 0.0,
        adapter_bank_resident_mb=_round(adapter_bank_resident_mb) or 0.0,
        active_adapter_resident_mb=_round(active_adapter_resident_mb) or 0.0,
        visual_incremental_peak_mb=_round(visual_incremental_peak_mb) or 0.0,
        decode_incremental_peak_mb=_round(decode_incremental_peak_mb) or 0.0,
        total_peak_mb=_round(normal) or 0.0,
        normal_path_peak_mb=_round(normal) or 0.0,
        controlled_fallback_peak_mb=_round(controlled),
        emergency_fallback_peak_mb=_round(emergency),
        measurement_source=measurement_source,
    )


def estimate_kv_cache_mb(
    visual_token_count: int | float | None,
    *,
    mb_per_token: float = 0.2977,
) -> float | None:
    tokens = _float_or_none(visual_token_count)
    if tokens is None:
        return None
    return _round(tokens * mb_per_token, 3)


def mean_numeric(values: list[Any]) -> float | None:
    clean = [v for v in (_float_or_none(value) for value in values) if v is not None]
    if not clean:
        return None
    return _round(sum(clean) / len(clean), 6)


def p95_numeric(values: list[Any]) -> float | None:
    clean = sorted(v for v in (_float_or_none(value) for value in values) if v is not None)
    if not clean:
        return None
    if len(clean) == 1:
        return _round(clean[0], 6)
    pos = (len(clean) - 1) * 0.95
    lo = int(pos)
    hi = min(lo + 1, len(clean) - 1)
    frac = pos - lo
    return _round(clean[lo] * (1 - frac) + clean[hi] * frac, 6)


def require_memory_contract(trace: Mapping[str, Any]) -> list[str]:
    required = [
        "base_after_load_allocated_mb",
        "base_after_load_reserved_mb",
        "adapter_bank_resident_mb",
        "active_adapter_resident_mb",
        "visual_incremental_peak_mb",
        "decode_incremental_peak_mb",
        "total_peak_mb",
        "normal_path_peak_mb",
        "controlled_fallback_peak_mb",
        "emergency_fallback_peak_mb",
    ]
    memory = trace.get("memory", {}) if isinstance(trace, Mapping) else {}
    return [key for key in required if key not in memory]
