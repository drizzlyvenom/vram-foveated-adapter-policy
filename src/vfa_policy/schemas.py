from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AdapterCard:
    adapter_id: str
    base_model: str
    slot: str
    taxonomy: dict[str, Any]
    capability_probe: dict[str, Any]
    serving: dict[str, Any]
    certification: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteTrace:
    sample_id: str
    step_id: int
    stage: str
    baseline_id: str
    split: str
    evidence: dict[str, Any]
    input: dict[str, Any]
    routing: dict[str, Any]
    memory: dict[str, Any]
    timing: dict[str, Any]
    quality: dict[str, Any] = field(default_factory=dict)
    failure: dict[str, Any] = field(default_factory=dict)
    query: str | None = None
    run_id: str | None = None
    route_trace_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
