#!/usr/bin/env python3
"""Profile the mining and benchmark evaluation paths on a fixed panel.

The profile records wall time, peak RSS, signal panel allocations, dependence
evaluations, and rejection outcomes per stage, together with the exact metrics
and admission decisions produced. Two profiles are comparable when their
``dataset`` and ``catalog`` digests match; ``--compare`` then requires the
exact metrics to be identical and reports timing and memory ratios.

Examples::

    uv run python scripts/profile_runtime.py --output output/profile.json
    uv run python scripts/profile_runtime.py --data panel.parquet \\
        --config my_panel.yaml --candidates 400 --compare output/profile.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factorminer.application.runtime_profile import RuntimeProfile  # noqa: E402

PROFILE_SCHEMA = "factorminer-runtime-profile-v1"
DEFAULT_DATA = ROOT / "data" / "binance_crypto_5m.csv"
DEFAULT_CONFIG = ROOT / "factorminer" / "configs" / "binance_sample.yaml"


@dataclass
class CountingDependenceMetric:
    """Delegate to a dependence metric while counting pair evaluations."""

    inner: Any
    profile: RuntimeProfile

    @property
    def name(self) -> str:
        return self.inner.name

    def describe(self) -> dict[str, str]:
        return self.inner.describe()

    def compute(self, signals_a: np.ndarray, signals_b: np.ndarray) -> float:
        self.profile.count("dependence_evaluations")
        return self.inner.compute(signals_a, signals_b)


def _digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""

    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def _exact(value: Any) -> Any:
    """Normalize a metric so JSON round-trips it exactly (NaN becomes a string)."""
    if isinstance(value, (float, np.floating)):
        value = float(value)
        return value if np.isfinite(value) else repr(value)
    if isinstance(value, np.integer):
        return int(value)
    return value


def build_catalog(candidates: int, seed: int) -> list[tuple[str, str]]:
    """Return the fixed, deterministic candidate catalog used for profiling."""
    from factorminer.benchmark.catalogs import (
        build_alpha101_adapted,
        build_random_exploration,
        dedupe_entries,
    )

    entries = dedupe_entries(
        [*build_alpha101_adapted(), *build_random_exploration(seed, count=candidates)]
    )
    return [(entry.name, entry.formula) for entry in entries[:candidates]]


def _dependence_metric(name: str, exact_index: bool) -> Any:
    from factorminer.domain.dependence import build_dependence_metric
    from factorminer.evaluation.dependence_index import indexed_dependence_metric

    return indexed_dependence_metric(name) if exact_index else build_dependence_metric(name)


def profile_mining(
    dataset: Any,
    cfg: Any,
    catalog: list[tuple[str, str]],
    *,
    batch_size: int,
    profile: RuntimeProfile,
    exact_index: bool = True,
) -> dict[str, Any]:
    """Run candidates through ``ValidationPipeline`` and admission in fixed batches."""
    from factorminer.application.validation_pipeline import ValidationPipeline
    from factorminer.architecture.library_services import FactorAdmissionService
    from factorminer.core.factor_library import FactorLibrary

    train = dataset.get_split("train")
    selector = train.indices
    data_dict = {name: panel[:, selector] for name, panel in dataset.data_dict.items()}
    target_panels = dict(train.target_returns) or {dataset.default_target: train.returns}
    library = FactorLibrary(
        correlation_threshold=cfg.mining.correlation_threshold,
        ic_threshold=cfg.mining.ic_threshold,
        dependence_metric=_dependence_metric(cfg.evaluation.redundancy_metric, exact_index),
    )
    index = getattr(library.dependence_metric, "index", None)
    library.dependence_metric = CountingDependenceMetric(library.dependence_metric, profile)
    pipeline = ValidationPipeline(
        data_tensor=data_dict,
        returns=train.get_target(dataset.default_target),
        target_panels=target_panels,
        library=library,
        ic_threshold=cfg.mining.ic_threshold,
        icir_threshold=cfg.mining.icir_threshold,
        replacement_ic_min=cfg.mining.replacement_ic_min,
        replacement_ic_ratio=cfg.mining.replacement_ic_ratio,
        fast_screen_assets=cfg.evaluation.fast_screen_assets,
        num_workers=1,
        redundancy_metric=cfg.evaluation.redundancy_metric,
        default_target=dataset.default_target,
    )
    admission = FactorAdmissionService(library)

    decisions: list[dict[str, Any]] = []
    growth: list[dict[str, Any]] = []
    for batch_index, start in enumerate(range(0, len(catalog), batch_size), start=1):
        batch = catalog[start : start + batch_size]
        before = profile.counters.get("dependence_evaluations", 0)
        with profile.stage("mining.evaluate") as stage:
            seconds_before = stage.seconds
            results = pipeline.evaluate_batch(batch)
        profile.record_panels("mining.evaluate", (result.signals for result in results))
        profile.record_outcomes("mining.evaluate", results)
        with profile.stage("mining.library_update"):
            admission.admit_results(results, iteration=batch_index)
        growth.append(
            {
                "batch": batch_index,
                "library_size": library.size,
                "evaluate_seconds": round(stage.seconds - seconds_before, 6),
                "dependence_evaluations": profile.counters.get("dependence_evaluations", 0)
                - before,
            }
        )
        for result in results:
            decisions.append(
                {
                    "name": result.factor_name,
                    "formula": result.formula,
                    "stage_passed": int(result.stage_passed),
                    "admitted": bool(result.admitted),
                    "replaced": result.replaced,
                    "rejection_reason": result.rejection_reason,
                    "ic_paper_mean": _exact(result.ic_paper_mean),
                    "ic_paper_icir": _exact(result.ic_paper_icir),
                    "max_correlation": _exact(result.max_correlation),
                }
            )
            result.signals = None
    if index is not None:
        for name, value in index.stats().items():
            if value is not None:
                profile.count(f"dependence_index.{name}", value)
    library_ids = [factor.name for factor in library.list_factors()]
    return {"decisions": decisions, "library": library_ids, "growth": growth}


def profile_benchmark(
    dataset: Any,
    cfg: Any,
    catalog: list[tuple[str, str]],
    *,
    profile: RuntimeProfile,
    signal_cache_mb: float | None = None,
) -> dict[str, Any]:
    """Recompute the catalog as frozen-benchmark artifacts and build the library."""
    from factorminer.benchmark.datasets import build_benchmark_library
    from factorminer.core.factor_library import Factor
    from factorminer.evaluation.runtime import evaluate_factors
    from factorminer.evaluation.signal_store import open_signal_store

    factors = [
        Factor(id=index, name=name, formula=formula, category="profile", ic_mean=0.0,
               icir=0.0, ic_win_rate=0.0, max_correlation=0.0, batch_number=0)
        for index, (name, formula) in enumerate(catalog, start=1)
    ]
    selection = "validation" if "validation" in dataset.splits else "train"
    store = open_signal_store(
        dataset,
        retain_splits=("train", selection),
        dtype=cfg.evaluation.signal_dtype,
        cache_mb=signal_cache_mb,
    )
    with profile.stage("benchmark.evaluate"):
        artifacts = evaluate_factors(
            factors,
            dataset,
            signal_failure_policy="reject",
            retain_splits=None if store else ("train", selection),
            signal_dtype=cfg.evaluation.signal_dtype,
            signal_store=store,
        )
    if store is None:
        profile.record_panels(
            "benchmark.evaluate",
            (panel for artifact in artifacts for panel in artifact.split_signals.values()),
        )
    with profile.stage("benchmark.library"):
        library, stats = build_benchmark_library(artifacts, cfg, split_name="train")
    metrics = [
        {
            "name": artifact.name,
            "error": artifact.error,
            "splits": {
                split: {
                    key: _exact(values.get(key))
                    for key in ("ic_paper_mean", "ic_paper_icir", "ic_mean", "icir")
                }
                for split, values in sorted(artifact.split_stats.items())
            },
        }
        for artifact in artifacts
    ]
    for artifact in artifacts:
        artifact.release_signals()
    if store is not None:
        for name, value in store.stats().items():
            if value is not None:
                profile.count(f"signal_store.{name}", value)
        store.close()
    return {
        "metrics": metrics,
        "library": [factor.name for factor in library.list_factors()],
        "library_stats": stats,
    }


def run_profile(
    *,
    data_path: Path,
    config_path: Path | None,
    candidates: int,
    seed: int,
    batch_size: int,
    trace_allocations: bool,
    signal_cache_mb: float | None = None,
    exact_index: bool = True,
) -> dict[str, Any]:
    from factorminer.data.loader import load_market_data
    from factorminer.evaluation.runtime import load_runtime_dataset
    from factorminer.utils.config import load_config

    profile = RuntimeProfile(trace_allocations=trace_allocations)
    cfg = load_config(config_path)
    with profile.stage("load"):
        raw_df = load_market_data(data_path)
        dataset = load_runtime_dataset(raw_df, cfg)
    del raw_df
    catalog = build_catalog(candidates, seed)

    mining = profile_mining(
        dataset, cfg, catalog, batch_size=batch_size, profile=profile, exact_index=exact_index
    )
    benchmark = profile_benchmark(
        dataset, cfg, catalog, profile=profile, signal_cache_mb=signal_cache_mb
    )
    exact = {"mining": mining["decisions"], "benchmark": benchmark["metrics"],
             "mining_library": mining["library"], "benchmark_library": benchmark["library"]}
    return {
        "schema_version": PROFILE_SCHEMA,
        "git": _git_state(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
        "dataset": {
            "path": str(data_path),
            "sha256": _file_sha256(data_path),
            "config": str(config_path) if config_path else None,
            "assets": int(dataset.returns.shape[0]),
            "periods": int(dataset.returns.shape[1]),
            "features": list(dataset.data_dict),
            "splits": {name: split.size for name, split in dataset.splits.items()},
        },
        "catalog": {
            "seed": seed,
            "candidates": len(catalog),
            "batch_size": batch_size,
            "digest": _digest(catalog),
        },
        "signal_cache_mb": signal_cache_mb,
        "dependence_index": exact_index,
        "runtime": profile.to_dict(),
        "library_growth": mining["growth"],
        "benchmark_library_stats": benchmark["library_stats"],
        "exact_digest": _digest(exact),
        "exact": exact,
    }


def compare_profiles(current: dict[str, Any], baseline: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return whether exact results match and a human-readable comparison."""
    lines: list[str] = []
    comparable = (
        current["dataset"]["sha256"] == baseline["dataset"]["sha256"]
        and current["catalog"]["digest"] == baseline["catalog"]["digest"]
    )
    if not comparable:
        return False, ["Profiles use different datasets or catalogs; not comparable."]
    matches = current["exact_digest"] == baseline["exact_digest"]
    lines.append(
        f"exact results: {'identical' if matches else 'DIFFERENT'} "
        f"(baseline commit {baseline['git']['commit'][:12]})"
    )
    if not matches:
        for section, rows in current["exact"].items():
            base_rows = baseline["exact"].get(section)
            if rows != base_rows:
                if isinstance(rows, list) and isinstance(base_rows, list):
                    first = next(
                        (i for i, (a, b) in enumerate(zip(rows, base_rows, strict=False)) if a != b),
                        min(len(rows), len(base_rows)),
                    )
                    lines.append(f"  {section}: first difference at row {first}")
                else:
                    lines.append(f"  {section}: differs")
    stages = current["runtime"]["stages"]
    for name, stage in stages.items():
        base = baseline["runtime"]["stages"].get(name)
        if not base:
            continue
        ratio = stage["seconds"] / base["seconds"] if base["seconds"] else float("nan")
        lines.append(
            f"  {name}: {stage['seconds']:.3f}s vs {base['seconds']:.3f}s ({ratio:.2f}x), "
            f"panels {stage['panel_bytes'] / 1e6:.1f}MB vs {base['panel_bytes'] / 1e6:.1f}MB"
        )
    lines.append(
        f"  peak RSS: {current['runtime']['peak_rss_bytes'] / 1e6:.1f}MB vs "
        f"{baseline['runtime']['peak_rss_bytes'] / 1e6:.1f}MB"
    )
    return matches, lines


def _summary(result: dict[str, Any]) -> list[str]:
    lines = [
        f"commit {result['git']['commit'][:12]}{' (dirty)' if result['git']['dirty'] else ''}; "
        f"panel {result['dataset']['assets']}x{result['dataset']['periods']}; "
        f"{result['catalog']['candidates']} candidates",
        f"exact digest {result['exact_digest'][:16]}",
    ]
    for name, stage in result["runtime"]["stages"].items():
        outcomes = ", ".join(f"{key}={value}" for key, value in stage["outcomes"].items())
        lines.append(
            f"  {name}: {stage['seconds']:.3f}s, {stage['panel_count']} panels "
            f"({stage['panel_bytes'] / 1e6:.1f}MB), peak RSS {stage['peak_rss_bytes'] / 1e6:.1f}MB"
            + (f", traced peak {stage['traced_peak_bytes'] / 1e6:.1f}MB" if stage["traced_peak_bytes"] else "")
            + (f"; {outcomes}" if outcomes else "")
        )
    for name, value in result["runtime"]["counters"].items():
        lines.append(f"  {name}: {value}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--config", type=Path, default=None,
                        help="Config whose data periods match --data (default: Binance sample)")
    parser.add_argument("--candidates", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--trace-allocations", action="store_true")
    parser.add_argument("--signal-cache-mb", type=float, default=None,
                        help="Resident budget for retained benchmark signals (spills beyond it)")
    parser.add_argument("--no-dependence-index", dest="exact_index", action="store_false",
                        help="Use the unindexed reference Spearman metric in mining")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--compare", type=Path, default=None,
                        help="Baseline profile; exit 1 unless exact results match")
    args = parser.parse_args(argv)

    config = args.config
    if config is None and args.data.resolve() == DEFAULT_DATA:
        config = DEFAULT_CONFIG
    result = run_profile(
        data_path=args.data,
        config_path=config,
        candidates=args.candidates,
        seed=args.seed,
        batch_size=args.batch_size,
        trace_allocations=args.trace_allocations,
        signal_cache_mb=args.signal_cache_mb,
        exact_index=args.exact_index,
    )
    print("\n".join(_summary(result)))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"wrote {args.output}")
    if args.compare:
        baseline = json.loads(args.compare.read_text())
        matches, lines = compare_profiles(result, baseline)
        print("\n".join(lines))
        return 0 if matches else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
