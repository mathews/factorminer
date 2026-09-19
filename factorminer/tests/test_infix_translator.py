"""Tests for the infix -> prefix DSL translator and the qlib catalogs."""

from __future__ import annotations

import numpy as np
import pytest

from factorminer.core.infix_translator import to_prefix_dsl
from factorminer.core.parser import parse, try_parse

# ---------------------------------------------------------------------------
# Translator
# ---------------------------------------------------------------------------


class TestInfixToPrefix:
    """Conversion of infix / qlib-style formulas into the prefix DSL."""

    @pytest.mark.parametrize(
        ("infix", "expected"),
        [
            ("($close-$open)/$open", "Div(Sub($close, $open), $open)"),
            ("Delay($close, 59)/$close", "Div(Delay($close, 59), $close)"),
            ("$volume/($volume+1e-12)", "Div($volume, Add($volume, 1e-12))"),
            ("2*$close-$high-$low", "Sub(Sub(Mul(2, $close), $high), $low)"),
            (
                "($close-$open)/($high-$low+1e-12)",
                "Div(Sub($close, $open), Add(Sub($high, $low), 1e-12))",
            ),
            ("Corr($close, Log($volume+1), 5)", "Corr($close, Log(Add($volume, 1)), 5)"),
            ("Mean($close>Delay($close, 1), 5)", "Mean(Greater($close, Delay($close, 1)), 5)"),
            ("Mean($close<Delay($close, 1), 5)", "Mean(Less($close, Delay($close, 1)), 5)"),
            (
                "Sum(Max($close-Delay($close, 1), 0), 5)",
                "Sum(Max(Sub($close, Delay($close, 1)), 0), 5)",
            ),
            (
                "Std(Abs($close/Delay($close, 1)-1)*$volume, 5)",
                "Std(Mul(Abs(Sub(Div($close, Delay($close, 1)), 1)), $volume), 5)",
            ),
            # qlib-specific operator renaming
            ("Rank($close, 5)", "TsRank($close, 5)"),
            ("Ref($close, 1)", "Delay($close, 1)"),
            ("Slope($close, 5)", "TsLinRegSlope($close, 5)"),
            ("Resi($close, 5)", "TsLinRegResid($close, 5)"),
            # qlib IdxMax/IdxMin are 1-based, TsArgMax/TsArgMin are 0-based
            ("IdxMax($high, 5)", "Add(TsArgMax($high, 5), 1)"),
            ("IdxMin($low, 5)", "Add(TsArgMin($low, 5), 1)"),
        ],
    )
    def test_conversion(self, infix: str, expected: str):
        assert to_prefix_dsl(infix) == expected

    def test_output_is_parseable(self):
        """Every conversion result must be accepted by the real parser."""
        for infix in ("($close-$open)/$open", "Rank($close, 5)", "IdxMax($high, 5)"):
            assert try_parse(to_prefix_dsl(infix)) is not None

    def test_idempotent(self):
        once = to_prefix_dsl("($close-TsMin($low, 10))/(TsMax($high, 10)-TsMin($low, 10)+1e-12)")
        assert to_prefix_dsl(once) == once

    def test_prefix_input_round_trips(self):
        prefix = "Div(Sub($close, $open), $open)"
        assert to_prefix_dsl(prefix) == prefix

    def test_unknown_operator_raises(self):
        with pytest.raises(ValueError, match="unknown operator"):
            to_prefix_dsl("Mad($close, 5)")

    def test_bare_identifier_raises(self):
        with pytest.raises(ValueError):
            to_prefix_dsl("close / open")

    def test_validate_flag_surfaces_arity_errors(self):
        """A wrong arity must fail here rather than during evaluation."""
        with pytest.raises(SyntaxError, match="expects 2 expression"):
            to_prefix_dsl("Greater($close)")

    def test_validate_can_be_disabled(self):
        assert to_prefix_dsl("Greater($close)", validate=False) == "Greater($close)"


# ---------------------------------------------------------------------------
# Semantic equivalence: infix source vs parsed prefix tree
# ---------------------------------------------------------------------------


class TestTranslatorSemantics:
    """The translated tree must reproduce hand-written prefix formulas."""

    def _eval_same(self, infix: str, prefix: str) -> None:
        tree_a = parse(to_prefix_dsl(infix))
        tree_b = parse(prefix)
        assert tree_a.to_string() == tree_b.to_string()

    def test_kmid(self):
        self._eval_same("($close-$open)/$open", "Div(Sub($close, $open), $open)")

    def test_rsv(self):
        self._eval_same(
            "($close-TsMin($low, 5))/(TsMax($high, 5)-TsMin($low, 5)+1e-12)",
            "Div(Sub($close, TsMin($low, 5)), Add(Sub(TsMax($high, 5), TsMin($low, 5)), 1e-12))",
        )

    def test_cntd(self):
        self._eval_same(
            "Mean($close>Delay($close, 1), 5)-Mean($close<Delay($close, 1), 5)",
            "Sub(Mean(Greater($close, Delay($close, 1)), 5),"
            " Mean(Less($close, Delay($close, 1)), 5))",
        )


# ---------------------------------------------------------------------------
# qlib catalogs
# ---------------------------------------------------------------------------


class TestQlibCatalogs:
    """Every formula shipped in the qlib catalogs must be parseable."""

    def test_qlib158_all_parseable(self):
        from factorminer.qlib158_alphas import build_qlib158

        entries = list(build_qlib158())
        assert len(entries) == 158
        unparsed = [e.name for e in entries if try_parse(e.formula) is None]
        assert not unparsed, f"unparseable: {unparsed[:10]}"

    def test_qlib360_all_parseable(self):
        from factorminer.qlib_alpha import build_qlib360

        entries = list(build_qlib360())
        assert len(entries) == 360
        unparsed = [e.name for e in entries if try_parse(e.formula) is None]
        assert not unparsed, f"unparseable: {unparsed[:10]}"

    def test_qlib158_getter_all_parseable(self):
        from factorminer.qlib158_alphas import get_qlib158

        entries = get_qlib158()
        unparsed = [e["name"] for e in entries if try_parse(e["formula"]) is None]
        assert not unparsed, f"unparseable: {unparsed[:10]}"

    def test_no_infix_operators_remain(self):
        """Guard against regressions to infix notation."""
        import re

        from factorminer.qlib158_alphas import build_qlib158
        from factorminer.qlib_alpha import build_qlib360

        # An infix operator appears as an arithmetic sign *outside* any call
        # argument separator -- approximated by ')' followed by an operator.
        infix_hint = re.compile(r"[\)\w]\s*[-+*/]\s*[\$\(]")
        offenders = [
            e.name
            for e in list(build_qlib158()) + list(build_qlib360())
            if infix_hint.search(e.formula)
        ]
        assert not offenders, f"infix-looking formulas: {offenders[:10]}"

    def test_formulas_are_unique(self):
        from factorminer.qlib158_alphas import build_qlib158

        formulas = [e.formula for e in build_qlib158()]
        assert len(set(formulas)) == len(formulas)


# ---------------------------------------------------------------------------
# Numerical smoke test on a small synthetic panel
# ---------------------------------------------------------------------------


class TestQlibSignalValues:
    """Translated qlib formulas must produce finite signals, not all-NaN."""

    def test_kmid_matches_manual_computation(self):
        from factorminer.evaluation.runtime import compute_tree_signals

        data = {
            "$close": np.array([[11.0, 12.0, 13.0, 14.0]]),
            "$open": np.array([[10.0, 10.0, 10.0, 10.0]]),
        }
        tree = parse(to_prefix_dsl("($close-$open)/$open"))
        got = compute_tree_signals(tree, data, (1, 4))
        assert np.allclose(got, np.array([[0.1, 0.2, 0.3, 0.4]]))

    def test_roc_matches_manual_computation(self):
        from factorminer.evaluation.runtime import compute_tree_signals

        close = np.array([[10.0, 11.0, 12.0, 13.0]])
        tree = parse(to_prefix_dsl("Delay($close, 1)/$close"))
        got = compute_tree_signals(tree, {"$close": close}, (1, 4))
        # Delay(x, 1) lags by one bar -> first column is warm-up NaN
        assert np.isnan(got[0, 0])
        assert np.allclose(got[0, 1:], [10 / 11, 11 / 12, 12 / 13])
