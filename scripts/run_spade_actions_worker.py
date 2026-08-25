#!/usr/bin/env python3
"""CPU-only, single-thread dispatch wrapper for one distributed SPADE shard."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence


_FROZEN_ENV = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "PYTHONHASHSEED": "0",
    "CUDA_VISIBLE_DEVICES": "",
}


def configure_runtime() -> dict[str, object]:
    for name, expected in _FROZEN_ENV.items():
        if os.environ.get(name) != expected:
            raise RuntimeError(f"{name} must equal {expected}")

    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise RuntimeError("Torch intra/inter-op thread freeze failed")
    if torch.cuda.is_available():
        raise RuntimeError("distributed registered runner must remain CPU-only")
    return {
        "cuda_available": False,
        "torch_interop_threads": 1,
        "torch_threads": 1,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--phase", choices=("development", "lockbox"))
    parser.add_argument("--family")
    parser.add_argument("--start", type=int)
    parser.add_argument("--stop", type=int)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if not args.preflight and any(
        value is None
        for value in (args.phase, args.family, args.start, args.stop, args.out)
    ):
        parser.error("registered shard dispatch requires phase/family/start/stop/out")
    if args.preflight and any(
        value is not None
        for value in (args.phase, args.family, args.start, args.stop, args.out)
    ):
        parser.error("preflight cannot be combined with shard arguments")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    runtime = configure_runtime()
    if args.preflight:
        print(json.dumps(runtime, sort_keys=True, separators=(",", ":")))
        return 0

    runner_args = (
        "--family",
        args.family,
        "--start",
        str(args.start),
        "--stop",
        str(args.stop),
        "--out",
        str(args.out),
    )
    if args.phase == "development":
        from scripts.run_spade_development import main as runner_main
    else:
        from scripts.run_spade_lockbox import main as runner_main
    return runner_main(runner_args)


if __name__ == "__main__":
    raise SystemExit(main())
