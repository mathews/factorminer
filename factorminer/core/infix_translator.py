"""Translate infix / qlib-style factor formulas into the FactorMiner prefix DSL.

The FactorMiner parser (see :mod:`factorminer.core.parser`) accepts **prefix
function notation only** -- there are no infix operators in the grammar::

    expression    := function_call | feature_ref | number
    function_call := IDENTIFIER '(' arg_list ')'

Externally sourced factor libraries (notably Microsoft Qlib's Alpha158 /
Alpha360) are written in infix notation with qlib operator names::

    ($close-$open)/$open
    Delay($close, 59)/$close
    Rank($close, 5)

This module converts such formulas into the equivalent prefix form using
Python's own :mod:`ast` parser, so operator precedence, associativity and
parenthesisation are handled by CPython rather than by a hand-rolled regex.

The conversion is **idempotent**: an already-prefix formula such as
``Div(Sub($close, $open), $open)`` is valid Python call syntax too, so it
round-trips unchanged (modulo whitespace normalisation).

Operator mapping (qlib -> FactorMiner)
--------------------------------------
===================  ==============================  =========================
qlib / infix        FactorMiner                     note
===================  ==============================  =========================
``a+b``/-/*//       ``Add``/``Sub``/``Mul``/``Div``
``a**b``            ``Pow``
``-a``              ``Neg``
``a>b``, ``a<b``... ``Greater``, ``Less``, ...
``Ref(x, n)``       ``Delay(x, n)``
``Rank(x, n)``      ``TsRank(x, n)``                 qlib time-series rank
``IdxMax(x, n)``    ``Add(TsArgMax(x, n), 1)``       qlib is 1-based
``IdxMin(x, n)``    ``Add(TsArgMin(x, n), 1)``       qlib is 1-based
``Slope(x, n)``     ``TsLinRegSlope(x, n)``
``Resi(x, n)``      ``TsLinRegResid(x, n)``
``Max(a, b)``       ``Max(a, b)``                    element-wise
``Min(a, b)``       ``Min(a, b)``                    element-wise
``Med(x, n)``       ``Median(x, n)``
``Count(x, n)``     ``CountNotNaN(x, n)``
``CSRank(x)``       ``CsRank(x)``
===================  ==============================  =========================

Any operator without an explicit entry in :data:`FUNCTION_MAP` is passed
through unchanged if it exists in the operator registry, otherwise a
:class:`ValueError` is raised.

Examples
--------
>>> to_prefix_dsl("($close-$open)/$open")
'Div(Sub($close, $open), $open)'
>>> to_prefix_dsl("Delay($close, 59)/$close")
'Div(Delay($close, 59), $close)'
>>> to_prefix_dsl("Rank($close, 5)")
'TsRank($close, 5)'
"""

from __future__ import annotations

import ast
import re

from factorminer.core.types import OPERATOR_REGISTRY

__all__ = ["to_prefix_dsl", "translate_formulas"]

# ---------------------------------------------------------------------------
# Token-level helpers
# ---------------------------------------------------------------------------

# ``$close`` is not valid Python, so features are masked before parsing.
_FEATURE_TOKEN = re.compile(r"\$([A-Za-z_]\w*)")
_FEATURE_PREFIX = "__fm_feature_"

_BIN_OPS: dict[type, str] = {
    ast.Add: "Add",
    ast.Sub: "Sub",
    ast.Mult: "Mul",
    ast.Div: "Div",
    ast.FloorDiv: "Div",
    ast.Pow: "Pow",
}

_CMP_OPS: dict[type, str] = {
    ast.Gt: "Greater",
    ast.GtE: "GreaterEqual",
    ast.Lt: "Less",
    ast.LtE: "LessEqual",
    ast.Eq: "Equal",
    ast.NotEq: "Ne",
}

_BOOL_OPS: dict[type, str] = {ast.And: "And", ast.Or: "Or"}

#: qlib / generic function name -> FactorMiner operator name.
FUNCTION_MAP: dict[str, str] = {
    # time-series shift / difference
    "Ref": "Delay",
    "Delay": "Delay",
    "Delta": "Delta",
    # rolling statistics
    "Sum": "Sum",
    "Mean": "Mean",
    "Std": "Std",
    "Var": "Var",
    "Skew": "Skew",
    "Kurt": "Kurt",
    "Median": "Median",
    "Med": "Median",
    "Quantile": "Quantile",
    "TsRank": "TsRank",
    "Rank": "TsRank",  # qlib Rank(x, n) == rank within look-back window
    "Count": "CountNotNaN",
    "EMA": "EMA",
    "WMA": "WMA",
    # linear-regression family
    "Slope": "TsLinRegSlope",
    "TsLinRegSlope": "TsLinRegSlope",
    "Rsquare": "Rsquare",
    "Resi": "TsLinRegResid",
    "TsLinRegResid": "TsLinRegResid",
    # pair operators
    "Corr": "Corr",
    "Cov": "Cov",
    "Max": "Max",
    "Min": "Min",
    "Greater": "Greater",
    "Less": "Less",
    # element-wise
    "Abs": "Abs",
    "Log": "Log",
    "Sign": "Sign",
    "Sqrt": "Sqrt",
    "Power": "Power",
    "SignedPower": "SignedPower",
    "Neg": "Neg",
    "Inv": "Inv",
    "Not": "Not",
    # cross-sectional
    "CSRank": "CsRank",
    "CsRank": "CsRank",
    "CsZScore": "CsZScore",
    "CsDemean": "CsDemean",
    "CsScale": "CsScale",
    "CsNeutralize": "CsNeutralize",
}

#: qlib returns a **1-based** index; FactorMiner's ``TsArgMax``/``TsArgMin``
#: are 0-based, so ``+1`` is added to preserve qlib semantics.
_ONE_BASED_ARG_OPS: dict[str, str] = {
    "IdxMax": "TsArgMax",
    "IdxMin": "TsArgMin",
}


# ---------------------------------------------------------------------------
# Emitter
# ---------------------------------------------------------------------------


def _format_number(value: float) -> str:
    """Render a numeric literal for the DSL (keeps ``1e-12`` compact)."""
    if isinstance(value, bool):  # pragma: no cover - defensive
        raise ValueError("boolean literals are not valid factor operands")
    if isinstance(value, int):
        return str(value)
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return repr(float(value))


class _Translator:
    """Recursive AST visitor producing prefix-DSL text."""

    def __init__(self, source: str) -> None:
        self.source = source

    # -- entry ------------------------------------------------------------

    def emit(self, node: ast.AST) -> str:
        method = getattr(self, f"_emit_{type(node).__name__.lower()}", None)
        if method is None:
            raise ValueError(
                f"unsupported syntax element {type(node).__name__} in formula: {self.source!r}"
            )
        return method(node)

    # -- leaves -----------------------------------------------------------

    def _emit_constant(self, node: ast.Constant) -> str:
        if isinstance(node.value, bool) or node.value is None:
            raise ValueError(f"invalid literal {node.value!r} in {self.source!r}")
        if not isinstance(node.value, (int, float)):
            raise ValueError(f"string literals are not supported in formulas: {self.source!r}")
        return _format_number(node.value)

    def _emit_name(self, node: ast.Name) -> str:
        if node.id.startswith(_FEATURE_PREFIX):
            return "$" + node.id[len(_FEATURE_PREFIX) :]
        raise ValueError(
            f"unknown identifier {node.id!r} in formula {self.source!r}; "
            f"features must be referenced as $name"
        )

    # -- operators --------------------------------------------------------

    def _emit_binop(self, node: ast.BinOp) -> str:
        name = _BIN_OPS.get(type(node.op))
        if name is None:
            raise ValueError(
                f"unsupported binary operator {type(node.op).__name__} in {self.source!r}"
            )
        return self._call(name, [self.emit(node.left), self.emit(node.right)])

    def _emit_unaryop(self, node: ast.UnaryOp) -> str:
        if isinstance(node.op, ast.USub):
            return self._call("Neg", [self.emit(node.operand)])
        if isinstance(node.op, ast.UAdd):
            return self.emit(node.operand)
        if isinstance(node.op, ast.Not):
            return self._call("Not", [self.emit(node.operand)])
        raise ValueError(f"unsupported unary operator {type(node.op).__name__} in {self.source!r}")

    def _emit_compare(self, node: ast.Compare) -> str:
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError(f"chained comparisons are not supported: {self.source!r}")
        name = _CMP_OPS.get(type(node.ops[0]))
        if name is None:
            raise ValueError(
                f"unsupported comparison {type(node.ops[0]).__name__} in {self.source!r}"
            )
        return self._call(name, [self.emit(node.left), self.emit(node.comparators[0])])

    def _emit_boolop(self, node: ast.BoolOp) -> str:
        name = _BOOL_OPS.get(type(node.op))
        if name is None:
            raise ValueError(
                f"unsupported boolean operator {type(node.op).__name__} in {self.source!r}"
            )
        if len(node.values) != 2:
            raise ValueError(
                f"only binary And/Or are supported (got {len(node.values)} "
                f"operands) in {self.source!r}"
            )
        return self._call(name, [self.emit(node.values[0]), self.emit(node.values[1])])

    # -- function calls ---------------------------------------------------

    def _emit_call(self, node: ast.Call) -> str:
        if not isinstance(node.func, ast.Name):
            raise ValueError(f"unsupported call target in {self.source!r}")
        raw_name = node.func.id
        args = [self.emit(a) for a in node.args]
        if node.keywords:
            raise ValueError(f"keyword arguments are not supported in {self.source!r}")

        if raw_name in _ONE_BASED_ARG_OPS:
            # qlib IdxMax/IdxMin are 1-based -> shift FactorMiner's 0-based index
            return self._call("Add", [self._call(_ONE_BASED_ARG_OPS[raw_name], args), "1"])

        name = FUNCTION_MAP.get(raw_name, raw_name)
        if name not in OPERATOR_REGISTRY:
            raise ValueError(
                f"unknown operator {raw_name!r} (mapped to {name!r}) in "
                f"{self.source!r}. Add it to "
                f"factorminer.core.infix_translator.FUNCTION_MAP."
            )
        return self._call(name, args)

    # -- helpers ----------------------------------------------------------

    @staticmethod
    def _call(name: str, args: list[str]) -> str:
        return f"{name}({', '.join(args)})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def to_prefix_dsl(formula: str, *, validate: bool = True) -> str:
    """Convert an infix (or already-prefix) formula to the prefix DSL.

    Parameters
    ----------
    formula : str
        Formula written with infix arithmetic and/or qlib-style operator
        names, e.g. ``"($close-$open)/$open"``.  Formulas already in prefix
        form are returned unchanged (whitespace-normalised).
    validate : bool
        When ``True`` (default) the produced string is run through the real
        FactorMiner parser, so arity / feature / operator errors surface here
        instead of later during evaluation.

    Returns
    -------
    str
        The equivalent prefix-DSL formula.

    Raises
    ------
    ValueError
        If the formula uses unsupported syntax or unknown operators.
    SyntaxError
        If ``validate`` is set and the resulting string is not parseable.
    """
    from factorminer.core.parser import parse  # local import avoids a cycle

    masked = _FEATURE_TOKEN.sub(lambda m: _FEATURE_PREFIX + m.group(1), formula)
    try:
        tree = ast.parse(masked, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"cannot parse formula {formula!r}: {exc}") from exc

    result = _Translator(formula).emit(tree.body)
    if validate:
        parse(result)  # raises SyntaxError with a precise message
    return result


def translate_formulas(formulas: dict[str, str], *, validate: bool = True) -> dict[str, str]:
    """Apply :func:`to_prefix_dsl` to a ``{name: formula}`` mapping."""
    return {k: to_prefix_dsl(v, validate=validate) for k, v in formulas.items()}
