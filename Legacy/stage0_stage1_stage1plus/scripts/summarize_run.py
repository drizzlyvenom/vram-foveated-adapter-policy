from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.logging_utils import read_jsonl, summarize_traces, write_summary_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("route_traces_jsonl")
    args = parser.parse_args()

    trace_path = Path(args.route_traces_jsonl)
    rows = summarize_traces(read_jsonl(trace_path))
    summary_path = trace_path.parent / "summary.csv"
    write_summary_csv(summary_path, rows)

    print(f"wrote {summary_path}")
    for row in rows:
        print(
            "{stage} {baseline_id} split={split} {source_baseline} n={n_samples} tokens={visual_tokens_mean} peak={peak_vram_mb_mean} adapter={adapter_resident_mb_mean}".format(
                **row
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
