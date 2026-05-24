from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
DEFAULT_ROI_SOURCES = ["center_crop", "oracle_box", "layout_proxy_box", "ocr_detector_box"]


def _python_exe() -> str:
    return str(PYTHON if PYTHON.exists() else Path(sys.executable))


def _plan_commands(args: argparse.Namespace) -> list[list[str]]:
    commands: list[list[str]] = []
    for repeat in range(int(args.repeats)):
        for roi_source in args.roi_sources:
            command = [
                _python_exe(),
                "scripts/run_3090_two_track_validation.py",
                "--config",
                args.config,
                "--real-run",
                "--max-samples",
                str(args.max_samples),
                "--roi-source",
                roi_source,
                "--max-new-tokens",
                str(args.max_new_tokens),
            ]
            if args.manifest:
                command.extend(["--manifest", args.manifest])
            commands.append(command)
    return commands


def _write_plan(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolve(path_text: str | None) -> Path | None:
    if not path_text:
        return None
    path = Path(path_text)
    return path if path.is_absolute() else (REPO_ROOT / path)


def _manifest_count(path_text: str | None) -> int | None:
    path = _resolve(path_text)
    if path is None or not path.exists():
        return None
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def _last_json_line(output: str) -> dict[str, Any] | None:
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def _read_summary(run_dir_text: str | None) -> list[dict[str, Any]]:
    if not run_dir_text:
        return []
    run_dir = Path(run_dir_text)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    summary_path = run_dir / "summary.csv"
    if not summary_path.exists():
        return []
    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/3090/tiny_scored_validation.yaml")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--max-samples", type=int, default=32)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-new-tokens", type=int, default=8)
    parser.add_argument("--roi-sources", nargs="+", default=DEFAULT_ROI_SOURCES)
    parser.add_argument("--execute", action="store_true", help="Run the planned commands. Default only writes a plan.")
    parser.add_argument("--output", default=None, help="Plan/result JSON path under .local/runs by default.")
    args = parser.parse_args()

    commands = _plan_commands(args)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(args.output) if args.output else REPO_ROOT / ".local" / "runs" / f"{stamp}-roi_source_stability_plan.json"
    if not output.is_absolute():
        output = REPO_ROOT / output

    payload: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": args.config,
        "manifest_override": args.manifest,
        "unique_manifest_samples": _manifest_count(args.manifest),
        "max_samples": int(args.max_samples),
        "repeats": int(args.repeats),
        "max_new_tokens": int(args.max_new_tokens),
        "roi_sources": list(args.roi_sources),
        "commands": commands,
        "execute": bool(args.execute),
        "report_fields": [
            "task_score_mean",
            "task_score_std",
            "actual_task_score_available_rate",
            "visual_token_count_mean",
            "visual_token_count_p95",
            "normal_path_peak_mb_mean",
            "normal_path_peak_mb_p95",
            "controlled_fallback_peak_mb_conditional_mean",
            "controlled_fallback_peak_mb_all_samples_mean",
            "controlled_fallback_rate",
        ],
        "claim_boundary": "This plan strengthens stability/oracle-gap evidence only; it is not production p95/p99 validation.",
    }
    if payload["unique_manifest_samples"] is not None and int(args.max_samples) > int(payload["unique_manifest_samples"]):
        payload["cyclic_sampling_warning"] = (
            f"Requested max_samples={args.max_samples} exceeds unique manifest samples={payload['unique_manifest_samples']}."
        )

    results = []
    if args.execute:
        for command in commands:
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            parsed = _last_json_line(completed.stdout)
            run_dir_text = str(parsed.get("run_dir")) if parsed and parsed.get("run_dir") else None
            results.append(
                {
                    "command": command,
                    "returncode": completed.returncode,
                    "output": completed.stdout,
                    "run_dir": run_dir_text,
                    "summary_rows": _read_summary(run_dir_text),
                }
            )
            if completed.returncode != 0:
                payload["results"] = results
                _write_plan(output, payload)
                print(json.dumps({"ok": False, "output": str(output), "failed_command": command}, ensure_ascii=False))
                return completed.returncode
    payload["results"] = results
    _write_plan(output, payload)
    print(json.dumps({"ok": True, "output": str(output), "commands": len(commands), "executed": bool(args.execute)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
