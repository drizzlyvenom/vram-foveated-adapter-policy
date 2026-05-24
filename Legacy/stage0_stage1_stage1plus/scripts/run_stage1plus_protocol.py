from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vfa_policy.stage1plus_protocol import run_stage1plus_protocol


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/stage1plus_protocol.yaml")
    parser.add_argument("--max-samples", type=int, default=None)
    args = parser.parse_args()
    return run_stage1plus_protocol(args.config, max_samples_override=args.max_samples)


if __name__ == "__main__":
    raise SystemExit(main())
