from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROOT = REPO_ROOT / ".local"

DEFAULT_TWO_TRACK_CONFIG = "configs/3090/two_track_pilot.yaml"
DEFAULT_ADAPTER_CARDS = "configs/3090/adapter_cards.yaml"
DEFAULT_RUNS_DIR = ".local/runs"
DEFAULT_REAL_TASK_DIR = ".local/data/real_task_smoke"
DEFAULT_TINY_SCORED_DIR = ".local/data/tiny_scored_manifest"


def resolve_repo_path(path_text: str | Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def repo_relative(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(resolved).replace("\\", "/")
