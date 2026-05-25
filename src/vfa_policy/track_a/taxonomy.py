from __future__ import annotations

from typing import Any


DOMAINS = {"document", "scene_text", "ui_screen", "chart"}
EVIDENCE_TYPES = {"small_text", "field_value", "table_cell", "axis_label", "ui_status", "visual_symbol"}
OPERATIONS = {"read", "locate", "bind_label_to_value", "compare", "normalize_answer", "structured_output"}
FAILURE_MODES = {
    "missed_evidence",
    "wrong_region",
    "label_value_mismatch",
    "distractor_confusion",
    "low_res_ambiguity",
    "wrong_adapter_confidence_gain",
}

TAXONOMY_PROFILES: list[dict[str, str]] = [
    {
        "domain": "document",
        "evidence_type": "field_value",
        "operation": "bind_label_to_value",
        "failure_mode": "distractor_confusion",
    },
    {
        "domain": "scene_text",
        "evidence_type": "small_text",
        "operation": "read",
        "failure_mode": "low_res_ambiguity",
    },
    {
        "domain": "ui_screen",
        "evidence_type": "ui_status",
        "operation": "bind_label_to_value",
        "failure_mode": "distractor_confusion",
    },
    {
        "domain": "chart",
        "evidence_type": "table_cell",
        "operation": "locate",
        "failure_mode": "label_value_mismatch",
    },
]


def taxonomy_key(taxonomy: dict[str, Any]) -> str:
    return "/".join(
        str(taxonomy.get(field) or "")
        for field in ("domain", "evidence_type", "operation", "failure_mode")
    )


def validate_taxonomy(taxonomy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    checks = [
        ("domain", DOMAINS),
        ("evidence_type", EVIDENCE_TYPES),
        ("operation", OPERATIONS),
        ("failure_mode", FAILURE_MODES),
    ]
    for field, allowed in checks:
        value = taxonomy.get(field)
        if value not in allowed:
            errors.append(f"taxonomy.{field} must be one of {sorted(allowed)}, got {value!r}")
    return errors


def taxonomy_for_domain(domain: str) -> dict[str, str]:
    for profile in TAXONOMY_PROFILES:
        if profile["domain"] == domain:
            return dict(profile)
    raise KeyError(f"Unknown Track A v2 domain: {domain}")
