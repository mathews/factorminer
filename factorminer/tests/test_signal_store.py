"""Bounded signal storage keeps exact values, scores, and provenance."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from factorminer.core.factor_library import Factor
from factorminer.domain.signal_ref import SignalKey, SignalRef, SplitSignalView
from factorminer.evaluation.runtime import build_runtime_dataset_from_arrays, evaluate_factors
from factorminer.evaluation.signal_store import (
    SignalUnavailableError,
    SplitSignalStore,
    dataset_fingerprint,
)

ROOT = Path(__file__).resolve().parents[2]


def _dataset(assets: int = 16, periods: int = 120, seed: int = 3):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, (assets, periods)), axis=1))
    data = {
        "$open": close * (1 + rng.normal(0, 0.002, close.shape)),
        "$high": close * 1.01,
        "$low": close * 0.99,
        "$close": close,
        "$volume": rng.lognormal(10, 1, close.shape),
    }
    data["$close"][2, 30:40] = np.nan
    returns = np.roll(close, -1, axis=1) / close - 1.0
    returns[:, -1] = np.nan
    return build_runtime_dataset_from_arrays(
        data,
        returns,
        split_indices={"train": np.arange(70), "validation": np.arange(70, 95),
                       "test": np.arange(95, periods)},
    )


def _factors(count: int = 24) -> list[Factor]:
    formulas = [f"Neg(CsRank(Return($close, {w})))" for w in range(1, 9)]
    formulas += [f"CsRank(Div(Sub($close, Mean($close, {w})), Std($close, {w})))" for w in range(3, 11)]
    formulas += [f"Neg(CsRank(Corr($close, $volume, {w})))" for w in range(3, 11)]
    formulas = (formulas + ["Neg(CsRank(Return($close, 1)))", "Broken("])[: count + 2]
    return [
        Factor(id=i, name=f"f{i}", formula=formula, category="t", ic_mean=0.0, icir=0.0,
               ic_win_rate=0.0, max_correlation=0.0, batch_number=0)
        for i, formula in enumerate(formulas)
    ]


def _key(name: str, digest: str = "d") -> SignalKey:
    return SignalKey(dataset_digest=digest, formula_digest=name, operator_version="v1")


def test_key_token_covers_every_identity_field():
    base = _key("a")
    variants = [
        SignalKey("x", "a", "v1"), SignalKey("d", "b", "v1"), SignalKey("d", "a", "v2"),
        SignalKey("d", "a", "v1", backend="torch"), SignalKey("d", "a", "v1", dtype="float32"),
    ]
    assert len({base.token, *(key.token for key in variants)}) == 6
    assert base.to_dict()["operator_version"] == "v1"


def test_budget_bounds_resident_bytes_and_spills_exactly(tmp_path):
    panel_bytes = 4 * 30 * 8
    store = SplitSignalStore(
        selectors={"train": slice(0, 30), "test": np.array([30, 32, 34])},
        retain_splits=("train",),
        dataset_digest="d",
        max_resident_bytes=2 * panel_bytes,
        spill_dir=tmp_path,
    )
    panels = {f"s{i}": np.random.default_rng(i).normal(size=(4, 40)) for i in range(6)}
    for name, panel in panels.items():
        store.put(_key(name), panel)
        assert store.resident_bytes <= 2 * panel_bytes
    assert store.evictions == 4
    for name, panel in panels.items():
        stored = store.get_split(_key(name), "train")
        np.testing.assert_array_equal(stored, panel[:, :30])
        assert not stored.flags.writeable
    stats = store.stats()
    assert stats["spill_reads"] >= 4 and stats["hits"] >= 1
    assert stats["peak_resident_bytes"] <= 3 * panel_bytes

    store.release(_key("s0"))
    assert not store.has(_key("s0"))
    with pytest.raises(SignalUnavailableError):
        store.get_split(_key("s0"), "train")
    store.close()
    assert list(tmp_path.iterdir()) == []


def test_duplicate_puts_share_storage_until_every_reference_is_released():
    store = SplitSignalStore(
        selectors={"train": slice(0, 3)}, retain_splits=("train",), dataset_digest="d"
    )
    panel = np.arange(12.0).reshape(3, 4)
    store.put(_key("a"), panel)
    store.put(_key("a"), panel)
    assert store.resident_bytes == 3 * 3 * 8
    view_a = SplitSignalView(SignalRef(_key("a"), store, ("train",)))
    view_b = SplitSignalView(SignalRef(_key("a"), store, ("train",)))
    view_a.clear()
    assert dict(view_a) == {}
    np.testing.assert_array_equal(view_b["train"], panel[:, :3])
    view_b.clear()
    assert store.resident_bytes == 0 and not store.has(_key("a"))


def test_evaluate_factors_with_bounded_store_matches_in_memory_results():
    dataset = _dataset()
    factors = _factors()
    reference = evaluate_factors(factors, dataset, retain_splits=("train", "validation"))
    panel_bytes = 16 * 70 * 8
    with SplitSignalStore.for_dataset(
        dataset, retain_splits=("train", "validation"), max_resident_bytes=3 * panel_bytes
    ) as store:
        bounded = evaluate_factors(factors, dataset, signal_store=store)
        stats = store.stats()
        assert stats["evictions"] > 0
        assert stats["resident_bytes"] <= 3 * panel_bytes
        for expected, actual in zip(reference, bounded, strict=True):
            assert (expected.error, expected.succeeded) == (actual.error, actual.succeeded)
            assert repr(expected.split_stats) == repr(actual.split_stats)
            assert set(expected.split_signals) == set(actual.split_signals)
            for split, panel in expected.split_signals.items():
                np.testing.assert_array_equal(actual.split_signals[split], panel)

        artifact = bounded[1]
        key = artifact.signal_ref.key
        assert key.dataset_digest == dataset_fingerprint(dataset)
        artifact.release_signals()
        assert artifact.succeeded and artifact.split_signals == {}
        assert artifact.split_stats["test"]["ic_paper_mean"] == reference[1].split_stats["test"][
            "ic_paper_mean"
        ]
        assert artifact.signal_ref.key == key and not store.has(key)
        with pytest.raises(ValueError, match="must match"):
            evaluate_factors(factors, dataset, retain_splits=("train",), signal_store=store)


def test_dataset_fingerprint_changes_with_values_and_splits():
    base = dataset_fingerprint(_dataset())
    assert base == dataset_fingerprint(_dataset())
    assert base != dataset_fingerprint(_dataset(seed=4))
    shifted = _dataset()
    shifted.splits["train"].indices = np.arange(69)
    assert base != dataset_fingerprint(shifted)


def test_table1_benchmark_is_unchanged_by_a_bounded_signal_cache(tmp_path):
    from factorminer.benchmark.runtime import run_table1_benchmark
    from factorminer.utils.config import load_config

    def run(cache_mb, name):
        cfg = load_config(ROOT / "factorminer" / "configs" / "binance_sample.yaml")
        cfg.benchmark.baselines = ["alpha101_adapted"]
        cfg.benchmark.freeze_top_k = 5
        cfg.evaluation.signal_cache_mb = cache_mb
        summary = run_table1_benchmark(
            cfg, tmp_path / name, data_path=str(ROOT / "data" / "binance_crypto_5m.csv")
        )
        return summary["alpha101_adapted"]

    unbounded = run(None, "unbounded")
    bounded = run(0.05, "bounded")
    cache = bounded.pop("signal_cache")
    assert unbounded.pop("signal_cache") is None
    assert cache["evictions"] > 0 and cache["resident_bytes"] == 0
    assert json.dumps(bounded, sort_keys=True, default=str) == json.dumps(
        unbounded, sort_keys=True, default=str
    )
