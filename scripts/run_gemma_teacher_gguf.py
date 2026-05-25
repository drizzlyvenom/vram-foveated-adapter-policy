from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.logging_utils import append_jsonl, write_json
from vfa_policy.paths import repo_relative, resolve_repo_path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _select_representatives(rows: list[dict[str, Any]], per_taxonomy: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row.get("taxonomy_label") or row.get("taxonomy_v2", {}).get("domain") or "")
        if counts.get(key, 0) >= per_taxonomy:
            continue
        selected.append(row)
        counts[key] = counts.get(key, 0) + 1
    return selected


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


def _prompt(sample: dict[str, Any]) -> str:
    taxonomy = sample.get("taxonomy_v2") or {}
    return (
        "You are the offline Gemma teacher for Track A v2. "
        "Inspect the image and return STRICT JSON only with keys: "
        "taxonomy, expected_answer_candidate, hard_negatives, rationale, label_is_final_truth. "
        "label_is_final_truth must be false. "
        f"Question: {sample.get('prompt')} "
        f"Candidate taxonomy: {json.dumps(taxonomy, ensure_ascii=False)} "
        f"Known candidate answer for audit: {(sample.get('expected_answers') or [''])[0]}. "
        "Do not wrap the JSON in markdown."
    )


def _fallback_annotation(sample: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "taxonomy": sample.get("taxonomy_v2") or {},
        "expected_answer_candidate": (sample.get("expected_answers") or [""])[0],
        "hard_negatives": sample.get("hard_negatives") or [],
        "rationale": f"deterministic fallback after teacher failure: {reason}",
        "label_is_final_truth": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=".local/data/track_a_v2_adapter_sensitive/manifest.jsonl")
    parser.add_argument("--llama-cli", default=".local/tools/llama.cpp/llama-mtmd-cli.exe")
    parser.add_argument("--model", default=".local/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf")
    parser.add_argument("--mmproj", default=".local/mmproj-F16.gguf")
    parser.add_argument("--output", default=".local/data/track_a_v2_adapter_sensitive/teacher_annotations.jsonl")
    parser.add_argument("--samples-per-taxonomy", type=int, default=1)
    parser.add_argument("--timeout-sec", type=int, default=900)
    parser.add_argument("--ctx-size", type=int, default=4096)
    parser.add_argument("--image-max-tokens", type=int, default=768)
    parser.add_argument("--gpu-layers", default="999")
    parser.add_argument("--allow-deterministic-fallback", action="store_true")
    args = parser.parse_args()

    manifest = resolve_repo_path(args.manifest)
    llama_cli = resolve_repo_path(args.llama_cli)
    model = resolve_repo_path(args.model)
    mmproj = resolve_repo_path(args.mmproj)
    output = resolve_repo_path(args.output)
    rows = _select_representatives(_read_jsonl(manifest), args.samples_per_taxonomy)
    if not llama_cli.exists():
        if not args.allow_deterministic_fallback:
            raise FileNotFoundError(f"llama-mtmd-cli not found: {llama_cli}")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-gemma_teacher_gguf")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    result_rows: list[dict[str, Any]] = []
    for sample in rows:
        image = resolve_repo_path(sample["full_image_path"])
        status = "ok"
        raw_output = ""
        error = None
        annotation: dict[str, Any]
        if llama_cli.exists():
            command = [
                str(llama_cli),
                "-m",
                str(model),
                "--mmproj",
                str(mmproj),
                "--image",
                str(image),
                "-p",
                _prompt(sample),
                "-n",
                "384",
                "-c",
                str(args.ctx_size),
                "--temp",
                "0",
                "-ngl",
                str(args.gpu_layers),
                "--image-max-tokens",
                str(args.image_max_tokens),
                "--no-warmup",
            ]
            try:
                completed = subprocess.run(
                    command,
                    cwd=REPO_ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=args.timeout_sec,
                )
                raw_output = (completed.stdout or "") + "\n" + (completed.stderr or "")
                if completed.returncode != 0:
                    raise RuntimeError(f"llama-mtmd-cli returned {completed.returncode}")
                annotation = _extract_json(completed.stdout)
            except Exception as exc:
                status = "fallback" if args.allow_deterministic_fallback else "failed"
                error = str(exc)
                if not args.allow_deterministic_fallback:
                    annotation = {}
                else:
                    annotation = _fallback_annotation(sample, error)
        else:
            status = "fallback"
            error = f"llama-mtmd-cli missing: {llama_cli}"
            annotation = _fallback_annotation(sample, error)

        row = {
            "teacher_annotation_id": f"teacher_{sample['sample_id']}",
            "run_id": run_id,
            "teacher_model": "google/gemma-4-26B-A4B-it",
            "teacher_runtime": "llama.cpp gguf",
            "sample_id": sample["sample_id"],
            "annotation_source": "gemma4_26b_gguf" if status == "ok" else "deterministic_fallback",
            "status": status,
            "error": error,
            "raw_output_excerpt": raw_output[:2000],
            **annotation,
        }
        result_rows.append(row)
        append_jsonl(output, row)

    summary = {
        "run_id": run_id,
        "manifest": repo_relative(manifest),
        "output": repo_relative(output),
        "samples": len(result_rows),
        "ok": sum(1 for row in result_rows if row["status"] == "ok"),
        "fallback": sum(1 for row in result_rows if row["status"] == "fallback"),
        "failed": sum(1 for row in result_rows if row["status"] == "failed"),
        "llama_cli": repo_relative(llama_cli),
        "model": repo_relative(model),
        "mmproj": repo_relative(mmproj),
    }
    write_json(output.with_suffix(".summary.json"), summary)
    if summary["failed"]:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
