"""Runtime profile accounting and the fixed-panel profiling script."""

from __future__ import annotations

import copy
from types import SimpleNamespace

import numpy as np

from factorminer.application.runtime_profile import RuntimeProfile, classify_rejection
from scripts import profile_runtime


def _result(**fields):
    base = {"admitted": False, "replaced": None, "parse_ok": True, "rejection_reason": ""}
    base.update(fields)
    return SimpleNamespace(**base)


def test_classify_rejection_covers_pipeline_reasons():
    cases = {
        "admitted": _result(admitted=True),
        "replaced": _result(admitted=True, replaced=3),
        "parse_failure": _result(parse_ok=False, rejection_reason="Parse failure"),
        "signal_error": _result(parse_ok=False, rejection_reason="Signal computation error: x"),
        "all_nan": _result(rejection_reason="All-NaN signals"),
        "fast_screen": _result(rejection_reason="Fast-screen paper IC 0.01 < threshold 0.04"),
        "quality": _result(rejection_reason="Paper IC 0.01 < threshold 0.04"),
        "icir": _result(rejection_reason="Paper ICIR 0.1 < threshold 0.5"),
        "dependence": _result(rejection_reason="Max spearman dependence 0.9 >= threshold 0.5"),
        "dedup": _result(rejection_reason="Intra-batch deduplication (correlated with ...)"),
    }
    assert {label: classify_rejection(result) for label, result in cases.items()} == {
        label: label for label in cases
    }


def test_profile_accumulates_stages_panels_outcomes_and_counters():
    profile = RuntimeProfile(trace_allocations=True)
    for _ in range(2):
        with profile.stage("evaluate"):
            panel = np.ones((10, 50))
    profile.record_panels("evaluate", [panel, None, panel])
    profile.record_outcomes("evaluate", [_result(admitted=True), _result(parse_ok=False)])
    profile.count("signal_cache_hits", 3)

    payload = profile.to_dict()
    stage = payload["stages"]["evaluate"]
    assert stage["calls"] == 2
    assert stage["panel_count"] == 2
    assert stage["panel_bytes"] == 2 * panel.nbytes
    assert stage["traced_peak_bytes"] >= panel.nbytes
    assert stage["outcomes"] == {"admitted": 1, "signal_error": 1}
    assert payload["counters"] == {"signal_cache_hits": 3}
    assert payload["peak_rss_bytes"] >= 0


def test_profile_script_records_exact_results_and_detects_changes():
    kwargs = dict(
        data_path=profile_runtime.DEFAULT_DATA,
        config_path=profile_runtime.DEFAULT_CONFIG,
        candidates=6,
        seed=3,
        batch_size=3,
        trace_allocations=False,
    )
    first = profile_runtime.run_profile(**kwargs)
    second = profile_runtime.run_profile(**kwargs)

    assert first["dataset"]["assets"] == 20
    assert len(first["exact"]["mining"]) == 6
    assert [row["library_size"] for row in first["library_growth"]] == sorted(
        row["library_size"] for row in first["library_growth"]
    )
    assert first["runtime"]["counters"]["dependence_evaluations"] > 0
    matches, lines = profile_runtime.compare_profiles(second, first)
    assert matches, lines

    different_inputs = copy.deepcopy(first)
    different_inputs["dataset"]["replay_digest"] = "changed"
    matches, lines = profile_runtime.compare_profiles(second, different_inputs)
    assert not matches and "not comparable" in lines[0]

    old_schema = copy.deepcopy(first)
    old_schema["schema_version"] = "factorminer-runtime-profile-v1"
    assert not profile_runtime.compare_profiles(second, old_schema)[0]

    first["exact"]["mining"][0]["ic_paper_mean"] = -1.0
    matches, lines = profile_runtime.compare_profiles(second, first)
    assert not matches
    assert any("mining: first difference at row 0" in line for line in lines)
