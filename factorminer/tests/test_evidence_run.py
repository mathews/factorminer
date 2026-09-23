"""Completed benchmark evidence must be linked, comparable, and verifiable."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from factorminer.benchmark.datasets import _cfg_with_overrides, load_benchmark_dataset
from factorminer.benchmark.evidence_run import (
    _qlib_panel,
    _qlib_preflight,
    _require_complete,
    run_evidence_benchmark,
)
from factorminer.benchmark.qlib_conformance import NonConformantBaselineError
from factorminer.benchmark.receipt import verify_research_receipt
from factorminer.utils.config import load_config

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "factorminer" / "configs" / "binance_sample.yaml"
DATA = ROOT / "data" / "binance_crypto_5m.csv"


def test_evidence_run_publishes_verified_receipt_and_detects_tampering(tmp_path):
    cfg = load_config(CONFIG)
    data_copy = tmp_path / "input.csv"
    shutil.copyfile(DATA, data_copy)
    result = run_evidence_benchmark(
        cfg, tmp_path, data_path=str(data_copy), baseline_names=["alpha101_adapted"]
    )
    manifest = json.loads(Path(result["manifest_path"]).read_text())
    receipt_path = Path(result["receipt_path"])
    receipt = json.loads(receipt_path.read_text())
    assert manifest["selected_factors"]["alpha101_adapted"]
    assert manifest["dataset_hashes"]["alpha101_adapted"]["Binance"]
    assert manifest["qlib"] == {"comparable": False}
    assert receipt["factor_library_sha256"]
    assert set(receipt["baseline_provenance"]) == {"alpha101_adapted"}
    assert verify_research_receipt(receipt_path.parent, commitment_input=data_copy).passed

    portable_manifest = json.loads((receipt_path.parent / "manifest.json").read_text())
    nested_path = receipt_path.parent / portable_manifest["artifact_paths"]["alpha101_adapted_manifest"]
    nested = json.loads(nested_path.read_text())
    assert (nested_path.parent / nested["artifact_paths"]["result"]).resolve() == (
        receipt_path.parent / portable_manifest["artifact_paths"]["alpha101_adapted_result"]
    ).resolve()
    assert (nested_path.parent / nested["artifact_paths"]["manifest"]).resolve() == nested_path
    relocated = tmp_path / "relocated" / receipt_path.parent.name
    shutil.copytree(receipt_path.parent, relocated)
    assert verify_research_receipt(relocated, commitment_input=data_copy).passed

    with pytest.raises(FileExistsError, match="fresh output"):
        run_evidence_benchmark(
            cfg, tmp_path, data_path=str(data_copy), baseline_names=["alpha101_adapted"]
        )

    with data_copy.open("a") as stream:
        stream.write("\n")
    assert not verify_research_receipt(receipt_path.parent, commitment_input=data_copy).passed
    shutil.copyfile(DATA, data_copy)
    assert verify_research_receipt(receipt_path.parent, commitment_input=data_copy).passed

    artifact = receipt_path.parent / portable_manifest["artifact_paths"]["alpha101_adapted_result"]
    artifact.write_bytes(artifact.read_bytes() + b"\n")
    assert not verify_research_receipt(receipt_path.parent, commitment_input=data_copy).passed


def test_evidence_run_rejects_unavailable_selection(tmp_path, monkeypatch):
    import factorminer.benchmark.evidence_run as module

    called = False

    def incomplete(*args, **kwargs):
        nonlocal called
        called = True
        return {"alpha101_adapted": {
            "frozen_top_k": [{"name": "one"}],
            "universes": {"Binance": {
                "factor_count": 1,
                "library": {"ic": 0.1, "icir": 0.2},
                "selections": {"xgboost": {"status": "unavailable"}},
            }},
        }}

    monkeypatch.setattr(module, "run_table1_benchmark", incomplete)
    with pytest.raises(ValueError, match="unavailable selections"):
        run_evidence_benchmark(
            load_config(CONFIG), tmp_path, data_path=str(DATA),
            baseline_names=["alpha101_adapted"],
        )
    assert called
    assert not (tmp_path / "releases").exists()


def test_complete_run_requires_all_baselines_universes_and_factors():
    result = {"a": {"frozen_top_k": [{"name": "x"}], "universes": {
        "Binance": {"factor_count": 1, "library": {"ic": 0.1, "icir": 0.2},
                    "selections": {name: {"factor_count": 1} for name in (
                        "lasso", "forward_stepwise", "xgboost")}},
    }}}
    _require_complete(result, ["a"], ["Binance"])
    with pytest.raises(ValueError, match="exactly"):
        _require_complete(result, ["a", "b"], ["Binance"])
    with pytest.raises(ValueError, match="every report universe"):
        _require_complete(result, ["a"], ["Binance", "CSI500"])
    result["a"]["universes"]["Binance"]["library"]["ic"] = float("nan")
    with pytest.raises(ValueError, match="finite library ic"):
        _require_complete(result, ["a"], ["Binance"])
    result["a"]["universes"]["Binance"]["library"]["ic"] = 0.1
    del result["a"]["universes"]["Binance"]["selections"]["xgboost"]
    with pytest.raises(ValueError, match="omitted selections"):
        _require_complete(result, ["a"], ["Binance"])


def test_missing_baseline_artifact_cannot_be_receipted(tmp_path, monkeypatch):
    import factorminer.benchmark.evidence_run as module

    monkeypatch.setattr(module, "run_table1_benchmark", lambda *args, **kwargs: {
        "alpha101_adapted": {
            "frozen_top_k": [{"name": "one"}],
            "universes": {"Binance": {
                "factor_count": 1, "library": {"ic": 0.1, "icir": 0.2},
                "selections": {name: {"factor_count": 0} for name in (
                    "lasso", "forward_stepwise", "xgboost")},
            }},
        },
    })
    with pytest.raises(FileNotFoundError):
        run_evidence_benchmark(
            load_config(CONFIG), tmp_path, data_path=str(DATA),
            baseline_names=["alpha101_adapted"],
        )
    assert not (tmp_path / "releases").exists()


def test_qlib_preflight_checks_actual_panels_and_policy(tmp_path):
    cfg = load_config(CONFIG, overrides={"data": {
        "targets": [{"name": "paper", "entry_delay_bars": 1, "holding_bars": 1,
                     "price_pair": "close_to_close", "return_transform": "simple"}],
        "availability": "bar_close", "universe_policy": "static", "adjustment_policy": "none",
    }})
    freeze_cfg = _cfg_with_overrides(cfg, cfg.benchmark.freeze_universe)
    dataset, _ = load_benchmark_dataset(freeze_cfg, data_path=str(DATA))
    columns = {"CLOSE": "feature:$close", "LABEL0": "target:paper"}
    export = _qlib_panel(dataset, columns).rename(columns={v: k for k, v in columns.items()})
    values_path = tmp_path / "values.csv"
    export.reset_index().to_csv(values_path, index=False)
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps({"IC": 0.04}))
    bundle = {
        "handler": {"class": "Alpha158", "kwargs": {
            "instruments": "Binance", "freq": "5min",
            "learn_processors": ["DropnaLabel"],
            "fit_start_time": cfg.data.train_period[0],
            "fit_end_time": cfg.data.train_period[1],
        }},
        "dataset_contract": {"availability": "bar_close", "universe_policy": "static",
                             "adjustment_policy": "none"},
        "columns": columns,
        "values_path": values_path.name,
        "metrics_path": metrics_path.name,
    }
    bundle_path = tmp_path / "qlib.json"
    bundle_path.write_text(json.dumps(bundle))
    result, artifacts = _qlib_preflight(cfg, bundle_path, DATA, False, tmp_path)
    assert result["comparable"] and result["conformance"]["conformant"]
    assert set(artifacts) == {"qlib_evidence", "qlib_values", "qlib_metrics", "qlib_conformance"}
    run = run_evidence_benchmark(
        cfg, tmp_path / "run", data_path=str(DATA),
        baseline_names=["alpha101_adapted"], qlib_evidence_path=str(bundle_path),
    )
    assert run["qlib_comparable"]
    released = Path(run["receipt_path"]).parent
    assert verify_research_receipt(released, commitment_input=DATA).passed
    portable = json.loads((released / "manifest.json").read_text())
    qlib_spec_path = released / portable["artifact_paths"]["qlib_evidence"]
    qlib_spec = json.loads(qlib_spec_path.read_text())
    for field in ("values_path", "metrics_path"):
        assert (qlib_spec_path.parent / qlib_spec[field]).is_file()

    changed = pd.read_csv(values_path)
    changed.loc[0, "CLOSE"] += 1.0
    changed.to_csv(values_path, index=False)
    with pytest.raises(NonConformantBaselineError, match="value"):
        _qlib_preflight(cfg, bundle_path, DATA, False, tmp_path)

    bundle["dataset_contract"]["availability"] = "next_bar_open"
    bundle_path.write_text(json.dumps(bundle))
    with pytest.raises(NonConformantBaselineError, match="availability"):
        _qlib_preflight(cfg, bundle_path, DATA, False, tmp_path)

    metrics_path.write_text(json.dumps({"IC": None}))
    with pytest.raises(ValueError, match="finite numbers"):
        _qlib_preflight(cfg, bundle_path, DATA, False, tmp_path)


def test_failed_qlib_preflight_does_not_claim_evidence_output(tmp_path):
    cfg = load_config(CONFIG)
    bundle_path = tmp_path / "qlib.json"
    bundle_path.write_text("{}")
    with pytest.raises(ValueError, match="missing handler"):
        run_evidence_benchmark(
            cfg, tmp_path, data_path=str(DATA), baseline_names=["alpha101_adapted"],
            qlib_evidence_path=str(bundle_path),
        )
    assert not (tmp_path / "benchmark" / "evidence").exists()
