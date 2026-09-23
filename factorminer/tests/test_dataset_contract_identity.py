"""Dataset provenance, replay identity, and Qlib baseline conformance."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from factorminer.architecture.dataset_contract import DatasetContract
from factorminer.benchmark.qlib_conformance import (
    NonConformantBaselineError,
    QlibHandlerSpec,
    check_qlib_conformance,
    compare_values,
    parse_qlib_label,
    require_conformance,
)
from factorminer.benchmark.runtime_contracts import _benchmark_dataset_contract
from factorminer.data.loader import load_market_data
from factorminer.evaluation.runtime import load_runtime_dataset
from factorminer.utils.config import load_config

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "binance_crypto_5m.csv"
SAMPLE_CONFIG = ROOT / "factorminer" / "configs" / "binance_sample.yaml"
LEGACY_KEYS = {
    "feature_names", "data_shape", "returns_shape", "default_target", "target_names",
    "target_horizons", "train_period", "test_period", "asset_count", "period_count",
    "split_sizes", "extra_features", "asset_class",
}


def _arrays(seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(5, 30, 8)), rng.normal(size=(5, 30))


def test_undeclared_provenance_keeps_historical_identity():
    cfg = load_config()
    data, returns = _arrays()
    contract = DatasetContract.from_arrays(cfg, data_tensor=data, returns=returns)
    assert set(contract.to_dict()) == LEGACY_KEYS
    assert contract.panel_digest and contract.target_digest
    assert contract.replay_identity()["panel_digest"] == contract.panel_digest


def test_declared_provenance_enters_identity_and_is_validated():
    cfg = load_config(overrides={"data": {
        "source_version": "vendor-2026-09", "availability": "bar_close",
        "universe_policy": "point_in_time", "adjustment_policy": "split_dividend_adjusted",
    }})
    data, returns = _arrays()
    payload = DatasetContract.from_arrays(cfg, data_tensor=data, returns=returns).to_dict()
    assert payload["source_version"] == "vendor-2026-09"
    assert payload["universe_policy"] == "point_in_time"
    assert "availability_lag_bars" not in payload
    with pytest.raises(ValueError, match="universe_policy"):
        load_config(overrides={"data": {"universe_policy": "whatever"}})


def test_replay_mismatches_identify_changed_panels_and_targets():
    cfg = load_config()
    data, returns = _arrays()
    recorded = DatasetContract.from_arrays(cfg, data_tensor=data, returns=returns).replay_identity()
    same = DatasetContract.from_arrays(cfg, data_tensor=data.copy(), returns=returns.copy())
    assert same.replay_mismatches(recorded) == []

    changed = data.copy()
    changed[0, 0, 0] += 1e-12
    assert DatasetContract.from_arrays(
        cfg, data_tensor=changed, returns=returns
    ).replay_mismatches(recorded) == ["panel_digest"]
    assert DatasetContract.from_arrays(
        cfg, data_tensor=data, returns=returns * 2
    ).replay_mismatches(recorded) == ["target_digest"]
    assert same.replay_mismatches({"panel_digest": recorded["panel_digest"]}) == []


def test_runtime_dataset_contract_records_preprocessing_and_replays():
    cfg = load_config(SAMPLE_CONFIG)
    first = load_runtime_dataset(load_market_data(SAMPLE), cfg)
    second = load_runtime_dataset(load_market_data(SAMPLE), cfg)
    contract = DatasetContract.from_runtime_dataset(cfg, first)
    assert first.preprocessing["config"]["winsor_lower"] == 1.0
    assert contract.preprocessing_digest
    assert DatasetContract.from_runtime_dataset(cfg, second).replay_mismatches(
        contract.replay_identity()
    ) == []

    benchmark_contract = _benchmark_dataset_contract(cfg, first)
    assert benchmark_contract["replay_identity"]["target_digest"] == contract.target_digest


def test_qlib_handler_defaults_and_workflow_config():
    alpha158 = QlibHandlerSpec.alpha158()
    alpha360 = QlibHandlerSpec.alpha360()
    assert alpha158.infer_processors == ()
    assert [p.name for p in alpha360.infer_processors] == ["ProcessInf", "ZScoreNorm", "Fillna"]
    assert [p.name for p in alpha158.learn_processors] == ["DropnaLabel", "CSZScoreNorm"]
    assert parse_qlib_label(alpha158.label) == ("close", "close", 1, 2)

    spec = QlibHandlerSpec.from_handler_config({
        "class": "Alpha158",
        "kwargs": {
            "instruments": "csi300", "fit_start_time": "2008-01-01", "fit_end_time": "2014-12-31",
            "infer_processors": [
                {"class": "RobustZScoreNorm",
                 "kwargs": {"fields_group": "feature", "clip_outlier": True}},
                {"class": "Fillna", "kwargs": {"fields_group": "feature"}},
            ],
            "learn_processors": [{"class": "DropnaLabel"},
                                 {"class": "CSRankNorm", "kwargs": {"fields_group": "label"}}],
        },
    })
    assert spec.instruments == "csi300"
    assert spec.infer_processors[0].name == "RobustZScoreNorm"
    assert spec.to_dict()["learn_processors"][1]["class"] == "CSRankNorm"


def _conformant_setup():
    cfg = load_config(SAMPLE_CONFIG, overrides={"data": {
        "targets": [{"name": "paper", "entry_delay_bars": 1, "holding_bars": 1,
                     "price_pair": "close_to_close", "return_transform": "simple"}],
        "availability": "bar_close", "universe_policy": "static", "adjustment_policy": "none",
    }})
    spec = QlibHandlerSpec.alpha158(
        instruments="Binance", freq="5min", learn_processors=["DropnaLabel"],
        fit_start_time=cfg.data.train_period[0], fit_end_time=cfg.data.train_period[1],
    )
    return cfg, spec


def _frames():
    index = pd.MultiIndex.from_product(
        [pd.date_range("2026-02-15", periods=4, freq="5min"), ["BTC", "ETH"]],
        names=["datetime", "instrument"],
    )
    qlib = pd.DataFrame({"KMID": np.arange(8.0), "LABEL0": np.linspace(-1, 1, 8)}, index=index)
    qlib.iloc[3, 0] = np.nan
    ours = qlib.rename(columns={"KMID": "kmid", "LABEL0": "target"}).copy()
    return qlib, ours


def test_qlib_comparison_requires_matching_rules_and_values():
    cfg, spec = _conformant_setup()
    contract = {"availability": "bar_close", "universe_policy": "static",
                "adjustment_policy": "none"}
    qlib, ours = _frames()
    columns = {"KMID": "kmid", "LABEL0": "target"}
    report = check_qlib_conformance(
        spec, cfg, dataset_contract=contract, qlib_values=qlib, factorminer_values=ours,
        columns=columns,
    )
    assert report.issues == []
    assert report.conformant
    require_conformance(report)

    # Default paper target is open-to-close: the labels are not the same quantity.
    mismatched = check_qlib_conformance(
        QlibHandlerSpec.alpha158(), load_config(SAMPLE_CONFIG),
        qlib_values=qlib, factorminer_values=ours, columns=columns,
    )
    fields = {issue.field for issue in mismatched.issues}
    assert {"label", "freq", "instruments", "learn_processors", "universe_policy"} <= fields
    with pytest.raises(NonConformantBaselineError, match="label"):
        require_conformance(mismatched)

    no_values = check_qlib_conformance(spec, cfg, dataset_contract=contract)
    with pytest.raises(NonConformantBaselineError, match="no shared-panel value checks"):
        require_conformance(no_values)

    waived = check_qlib_conformance(
        QlibHandlerSpec.alpha360(instruments="Binance", freq="5min",
                                 learn_processors=["DropnaLabel"]),
        cfg, dataset_contract=contract, qlib_values=qlib, factorminer_values=ours,
        columns=columns, accepted_differences=["infer_processors"],
    )
    assert waived.conformant and waived.to_dict()["accepted_differences"] == ["infer_processors"]


def test_value_checks_report_nan_value_and_row_mismatches():
    qlib, ours = _frames()
    ours.iloc[0, 0] = 99.0
    ours.iloc[1, 0] = np.nan
    check = compare_values(qlib, ours.iloc[:-1], columns={"KMID": "kmid"})[0]
    assert (check.value_mismatches, check.nan_mismatches, check.missing_rows) == (1, 1, 1)
    assert check.max_abs_diff == 99.0 and not check.passed
