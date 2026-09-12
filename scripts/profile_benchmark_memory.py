"""Report the memory footprint of a benchmark run before you launch it.

The dominant allocation in a FactorMiner benchmark is the set of recomputed
(M, T) signal panels — one per candidate factor, per retained split.  This
script loads a universe, evaluates a small sample of factors under each
retention mode and projects the peak for a full baseline.

Usage::

    uv run python scripts/profile_benchmark_memory.py \
        --data-path /data/fuyao_data/hithink-finance/1000_panel_f.parquet \
        --universe CSI500 --candidates 200 --sample 12

Exit code is always 0; the script is diagnostic only.
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
import time
from pathlib import Path

import numpy as np


def _rss_mb() -> float:
    with open(f"/proc/{os.getpid()}/statm") as fh:
        return int(fh.read().split()[1]) * 4096 / 1e6


def _retained_mb(artifacts) -> float:
    """Bytes actually held, discounting views that share one buffer."""
    seen: set[int] = set()
    total = 0
    for artifact in artifacts:
        arrays = list(artifact.split_signals.values())
        if artifact.signals_full is not None:
            arrays.append(artifact.signals_full)
        for arr in arrays:
            ptr = arr.__array_interface__["data"][0]
            if ptr not in seen:
                seen.add(ptr)
                total += arr.nbytes
    return total / 1e6


def main() -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-path", required=True)
    parser.add_argument("--config", default=None, help="Optional YAML config to load.")
    parser.add_argument("--universe", default=None, help="Overrides cfg.data.universe.")
    parser.add_argument("--candidates", type=int, default=200,
                        help="Candidate factor count to project for.")
    parser.add_argument("--sample", type=int, default=12,
                        help="How many factors to actually evaluate.")
    parser.add_argument("--baseline", default="factor_miner",
                        help="Catalog used for the sample factors.")
    args = parser.parse_args()

    from factorminer.benchmark.datasets import (
        _factors_from_entries,
        _get_baseline_entries,
        load_benchmark_dataset,
    )
    from factorminer.evaluation.runtime import evaluate_factors
    from factorminer.utils.config import load_config

    cfg = load_config(args.config) if args.config else load_config()
    universe = args.universe or cfg.data.universe

    print(f"universe      : {universe}")
    print(f"data          : {args.data_path}")

    t0 = time.perf_counter()
    dataset, _ = load_benchmark_dataset(
        cfg, data_path=args.data_path, universe=universe, mock=False
    )
    gc.collect()
    build_s = time.perf_counter() - t0
    M, T, F = dataset.data_tensor.shape
    rows = sum(len(dataset.get_split(name).indices) for name in dataset.splits)

    print(f"dataset build : {build_s:.1f}s   RSS={_rss_mb():.0f} MB")
    print(f"panel         : {M} assets x {T} periods x {F} features")
    print(f"tensor        : {dataset.data_tensor.nbytes / 1e6:.0f} MB (float64)")
    print("splits        : "
          + ", ".join(f"{n}={len(s.indices)}" for n, s in dataset.splits.items()))
    panel_mb = M * T * 8 / 1e6
    print(f"one panel     : {panel_mb:.1f} MB float64 / {panel_mb / 2:.1f} MB float32")
    print(f"legacy retained per factor (full + one copy per split) ~ "
          f"{(1 + rows / T) * panel_mb:.1f} MB")

    entries = list(_get_baseline_entries(args.baseline, cfg.benchmark.seed))[: args.sample]
    factors = _factors_from_entries(entries)

    modes = [
        ("default (views, f64)", {}),
        ("train-only f64", {"retain_splits": ("train",)}),
        ("train-only f32", {"retain_splits": ("train",), "signal_dtype": np.float32}),
        ("stats only", {"retain_splits": ()}),
    ]
    print(f"\nsample: {len(factors)} factors from '{args.baseline}'")
    print(f"{'mode':24s} {'retained':>10s} {'per factor':>12s} {'projected @ N':>16s}")
    for label, kwargs in modes:
        t0 = time.perf_counter()
        artifacts = evaluate_factors(
            factors, dataset, signal_failure_policy="reject", **kwargs
        )
        dt = time.perf_counter() - t0
        ok = max(len([a for a in artifacts if a.succeeded]), 1)
        mb = _retained_mb(artifacts)
        print(f"{label:24s} {mb:9.1f} MB {mb / ok:9.2f} MB "
              f"{mb / ok * args.candidates / 1000:13.2f} GB   ({dt:.0f}s)")
        del artifacts
        gc.collect()

    print(f"\nprojection assumes {args.candidates} candidates "
          f"(largest shipped baseline is factor_miner_no_memory with 200).")
    print("Set evaluation.signal_dtype: float32 for another 2x on CSI500/CSI1000.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
