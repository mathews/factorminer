"""Compiled expression plans must reproduce recursive tree evaluation exactly."""

from __future__ import annotations

import numpy as np
import pytest

from factorminer.benchmark.catalogs import (
    build_alpha101_adapted,
    build_factor_miner_catalog,
    build_gplearn_style,
    build_random_exploration,
)
from factorminer.core.expression_plan import (
    OPERATOR_SEMANTICS_VERSION,
    compile_batch,
    compile_tree,
)
from factorminer.core.expression_tree import (
    ConstantNode,
    LeafNode,
    OperatorNode,
    _dispatch_operator,
)
from factorminer.core.parser import parse, try_parse
from factorminer.core.types import OPERATOR_REGISTRY, SignatureType, get_features


def _panel(assets: int = 12, periods: int = 90, seed: int = 5) -> dict[str, np.ndarray]:
    """Panel with NaNs, rounded (tied) values, and a halted asset."""
    rng = np.random.default_rng(seed)
    close = np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.02, (assets, periods)), axis=1)), 1)
    data = {
        "$open": np.round(close * (1 + rng.normal(0, 0.005, close.shape)), 1),
        "$high": close * 1.01,
        "$low": close * 0.99,
        "$close": close,
        "$volume": np.round(rng.lognormal(10, 1, close.shape), -3),
        "$amt": close * 1000.0,
        "$vwap": np.round(close, 0),
        "$returns": np.round(rng.normal(0, 0.01, close.shape), 3),
    }
    for name, panel in data.items():
        mask = rng.random(panel.shape) < 0.04
        panel[mask] = np.nan
        panel[3, 40:55] = np.nan
        data[name] = panel
    return {name: data[name] for name in get_features() if name in data}


def _catalog() -> list[str]:
    entries = [
        *build_alpha101_adapted(),
        *build_random_exploration(11, count=60),
        *build_gplearn_style(11, count=40),
        *build_factor_miner_catalog(),
    ]
    formulas = [entry.formula for entry in entries if try_parse(entry.formula) is not None]
    return list(dict.fromkeys(formulas))


def _tree_outcome(tree, data):
    try:
        return tree.evaluate(data)
    except Exception as exc:  # noqa: BLE001
        return exc


def _assert_same(actual, expected):
    if isinstance(expected, BaseException):
        assert type(actual) is type(expected)
        assert str(actual) == str(expected)
    else:
        assert isinstance(actual, np.ndarray)
        np.testing.assert_array_equal(actual, expected)
        assert actual.dtype == expected.dtype


@pytest.mark.parametrize("periods", [90, 7])
def test_plan_and_batch_match_tree_evaluation_bit_for_bit(periods):
    data = _panel(periods=periods)
    trees = [parse(formula) for formula in _catalog()]
    batch = compile_batch(trees)
    for index, value in batch.iter_outputs(data):
        expected = _tree_outcome(trees[index], data)
        _assert_same(value, expected)
        _assert_same(_tree_outcome(compile_tree(trees[index]), data), expected)
    assert batch.reused_steps > 0
    assert len(batch.steps) < sum(len(plan.steps) for plan in batch.plans)


def test_batch_shares_subexpressions_and_isolates_outputs():
    data = _panel()
    formulas = [
        "CsRank(Mean($close, 5))",
        "Neg(CsRank(Mean($close, 5)))",
        "CsRank(Mean($close, 5))",
        "Mean($close, 5)",
    ]
    batch = compile_batch([parse(formula) for formula in formulas])
    # $close, Mean, CsRank, Neg are the only distinct nodes.
    assert len(batch.steps) == 4
    outputs = dict(batch.iter_outputs(data))
    assert outputs[0] is not outputs[2]
    outputs[0][:] = 0.0
    np.testing.assert_array_equal(outputs[2], parse(formulas[2]).evaluate(data))
    np.testing.assert_array_equal(outputs[1], parse(formulas[1]).evaluate(data))


def test_compiled_plan_snapshots_mutable_tree_fields():
    data = _panel()
    leaf = LeafNode("$close")
    constant = ConstantNode(2.0)
    root = OperatorNode(OPERATOR_REGISTRY["Add"], [leaf, constant])
    plan = compile_tree(root)
    expected = plan.evaluate(data)
    leaf.feature_name = "$open"
    constant.value = 7.0
    np.testing.assert_array_equal(plan.evaluate(data), expected)
    assert plan.required_features == frozenset({"$close"})


def test_failures_propagate_only_to_dependent_formulas():
    data = _panel()
    data.pop("$volume")
    formulas = ["CsRank($volume)", "Neg($close)", "Add(CsRank($volume), $close)"]
    trees = [parse(formula) for formula in formulas]
    outputs = dict(compile_batch(trees).iter_outputs(data))
    for index, tree in enumerate(trees):
        _assert_same(outputs[index], _tree_outcome(tree, data))
    assert isinstance(outputs[0], KeyError)
    assert isinstance(outputs[1], np.ndarray)


def test_plan_metadata_describes_features_lookback_and_cross_section():
    plan = compile_tree(parse("CsRank(Corr(Delta($close, 3), Mean($volume, 10), 5))"))
    assert plan.required_features == frozenset({"$close", "$volume"})
    assert plan.max_lookback == max(3, 10 - 1) + (5 - 1)
    assert plan.cross_sectional is True
    assert plan.operator_order[-1] == "CsRank"
    assert compile_tree(parse("Div($close, $open)")).max_lookback == 0
    assert compile_tree(parse("Div($close, $open)")).cross_sectional is False
    assert compile_tree(parse("EMA($close, 5)")).max_lookback is None

    same = compile_tree(parse("CsRank(Corr(Delta($close, 3), Mean($volume, 10), 5))"))
    other = compile_tree(parse("CsRank(Corr(Delta($close, 3), Mean($volume, 20), 5))"))
    assert plan.digest == same.digest != other.digest
    assert OPERATOR_SEMANTICS_VERSION


def test_finite_lookback_reproduces_values_after_a_split_boundary():
    data = _panel(periods=120)
    boundary = 70
    checked = 0
    for formula in _catalog():
        plan = compile_tree(parse(formula))
        if plan.max_lookback is None or plan.max_lookback >= boundary:
            continue
        start = boundary - plan.max_lookback
        full = _tree_outcome(parse(formula), data)
        tile = _tree_outcome(parse(formula), {k: v[:, start:] for k, v in data.items()})
        if isinstance(full, BaseException):
            continue
        np.testing.assert_array_equal(tile[:, plan.max_lookback :], full[:, boundary:])
        checked += 1
    assert checked > 50


def test_every_temporal_operator_has_a_safe_lookback():
    data = _panel(periods=90)
    boundary = 60
    for spec in OPERATOR_REGISTRY.values():
        if spec.signature not in (
            SignatureType.TIME_SERIES_TO_TIME_SERIES, SignatureType.REDUCE_TIME
        ):
            continue
        children = [LeafNode("$close") for _ in range(spec.arity)]
        node = OperatorNode(spec, children, {"window": 5.0} if "window" in spec.param_names else {})
        plan = compile_tree(node)
        if spec.name in {"EMA", "DEMA", "KAMA", "CumSum", "CumProd", "CumMax", "CumMin"}:
            assert plan.max_lookback is None, spec.name
            continue
        assert plan.max_lookback is not None, spec.name
        start = boundary - plan.max_lookback
        full = plan.evaluate(data)
        tiled = plan.evaluate({name: panel[:, start:] for name, panel in data.items()})
        np.testing.assert_array_equal(
            tiled[:, plan.max_lookback:], full[:, boundary:], err_msg=spec.name
        )


def test_operators_never_mutate_their_inputs():
    """Shared subexpressions are safe only if every operator treats inputs as read-only."""
    data = _panel(periods=40)
    base = data["$close"]
    for spec in OPERATOR_REGISTRY.values():
        children = [base.copy() + index for index in range(spec.arity)]
        snapshots = [child.copy() for child in children]
        params = {name: min(3.0, spec.param_defaults.get(name, 3.0)) if name == "window"
                  else spec.param_defaults[name] for name in spec.param_names}
        try:
            _dispatch_operator(spec, children, dict(params))
        except NotImplementedError:
            continue
        for child, snapshot in zip(children, snapshots, strict=True):
            np.testing.assert_array_equal(child, snapshot, err_msg=spec.name)


def test_opaque_nodes_are_evaluated_as_units():
    class Opaque:
        def evaluate(self, data):
            return data["$close"] * 2.0

        def to_string(self):
            return "Opaque()"

    root = OperatorNode(OPERATOR_REGISTRY["Add"], [Opaque(), LeafNode("$close")])
    plan = compile_tree(root)
    data = _panel()
    np.testing.assert_array_equal(plan.evaluate(data), data["$close"] * 2.0 + data["$close"])
    assert plan.max_lookback is None and plan.cross_sectional is True
    assert compile_tree(ConstantNode(2.0)).required_features == frozenset()


@pytest.mark.parametrize("policy", ["reject", "synthetic"])
def test_kernel_batch_signals_match_single_formula_path(policy):
    from factorminer.application.validation_pipeline import ValidationPipeline
    from factorminer.evaluation.runtime import SignalComputationError

    data = _panel()
    returns = np.nan_to_num(data["$returns"])
    kernel = ValidationPipeline(data_tensor=data, returns=returns).kernel
    formulas = ["NotAnOperator($close)", "Neg($close)", "Sub($close, $close)",
                "CsRank(Mean($close, 5))", "Neg(CsRank(Mean($close, 5)))"]
    batch = kernel.compute_batch_signals(
        formulas=formulas, data_dict=data, returns_shape=returns.shape,
        signal_failure_policy=policy,
    )
    for formula, (_tree, signals, error) in zip(formulas, batch, strict=True):
        try:
            _, expected = kernel.compute_signals(
                formula=formula, data_dict=data, returns_shape=returns.shape,
                signal_failure_policy=policy,
            )
        except SignalComputationError as exc:
            assert type(error) is type(exc) and str(error) == str(exc)
            continue
        assert error is None
        np.testing.assert_array_equal(signals, expected)


def test_parallel_batch_evaluation_matches_single_worker():
    from factorminer.application.validation_pipeline import ValidationPipeline

    data = _panel(assets=30, periods=80)
    returns = np.nan_to_num(data["$returns"])
    candidates = [
        (f"f{i}", formula) for i, formula in enumerate([
            "CsRank(Mean($close, 5))", "Neg(CsRank(Mean($close, 5)))",
            "CsRank(Mean($close, 5))", "Broken(", "Return($open, 3)",
            "Neg(Return($open, 3))", "CsRank($volume)", "Mean($close, 10)",
        ])
    ]
    def run(workers):
        pipeline = ValidationPipeline(
            data_tensor=data, returns=returns, fast_screen_assets=10,
            num_workers=workers, ic_threshold=0.02,
        )
        return pipeline.evaluate_batch(candidates)

    single, parallel = run(1), run(3)
    for left, right in zip(single, parallel, strict=True):
        assert (left.factor_name, left.formula, left.stage_passed, left.admitted,
                left.rejection_reason) == (right.factor_name, right.formula,
                                          right.stage_passed, right.admitted,
                                          right.rejection_reason)
        if left.signals is not None:
            np.testing.assert_array_equal(left.signals, right.signals)


def test_evaluate_factors_is_independent_of_plan_batch_size():
    from factorminer.core.factor_library import Factor
    from factorminer.evaluation.runtime import build_runtime_dataset_from_arrays, evaluate_factors

    data = _panel(periods=80)
    returns = np.nan_to_num(np.roll(data["$close"], -1, axis=1) / data["$close"] - 1.0)
    dataset = build_runtime_dataset_from_arrays(
        data, returns, split_indices={"train": np.arange(50), "test": np.arange(50, 80)}
    )
    factors = [
        Factor(id=i, name=f"f{i}", formula=formula, category="t", ic_mean=0.0, icir=0.0,
               ic_win_rate=0.0, max_correlation=0.0, batch_number=0)
        for i, formula in enumerate(_catalog()[:30] + ["Broken(", "$close"])
    ]
    single = evaluate_factors(factors, dataset, plan_batch_size=1)
    batched = evaluate_factors(factors, dataset, plan_batch_size=16)
    for a, b in zip(single, batched, strict=True):
        assert (a.name, a.parse_ok, a.error, a.succeeded) == (b.name, b.parse_ok, b.error, b.succeeded)
        for split in a.split_signals:
            np.testing.assert_array_equal(a.split_signals[split], b.split_signals[split])
        assert repr(a.split_stats) == repr(b.split_stats)
