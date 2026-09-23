"""Conformance checks before comparing FactorMiner with Qlib baselines.

Alpha158 and Alpha360 are Qlib *handler workflows*: a feature set together
with a label expression, inference and learning processors, a fit window,
an instrument universe, and a frequency. Matching formulas alone does not
make a comparison fair. This module states those settings as a
:class:`QlibHandlerSpec` (defaults from ``qlib/contrib/data/handler.py``) and
compares them with a FactorMiner configuration and dataset. It also compares
feature and label values that both systems exported for the same panel.
:func:`require_conformance` refuses to report performance until both the
processing rules and the values agree.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from factorminer.architecture.dataset_contract import (
    ADJUSTMENT_POLICIES,
    AVAILABILITY_POLICIES,
    UNIVERSE_POLICIES,
)
from factorminer.data.tensor_builder import TargetSpec, _resolve_target_offsets

QLIB_DEFAULT_LABEL = "Ref($close, -2)/Ref($close, -1) - 1"

_LABEL_PATTERN = re.compile(
    r"^\s*Ref\(\$(?P<end_field>\w+),\s*-(?P<end>\d+)\)\s*/\s*"
    r"Ref\(\$(?P<start_field>\w+),\s*-(?P<start>\d+)\)\s*-\s*1\s*$"
)
_FREQUENCY_ALIASES = {
    "day": "1d", "1d": "1d", "d": "1d", "daily": "1d",
    "1min": "1min", "min": "1min", "5min": "5min", "10min": "10min",
    "30min": "30min", "60min": "1h", "1h": "1h",
}


class NonConformantBaselineError(RuntimeError):
    """Raised when a Qlib comparison would be reported without conformance."""


@dataclass(frozen=True)
class QlibProcessor:
    """One Qlib data processor, e.g. ``ZScoreNorm`` or ``CSRankNorm``."""

    name: str
    kwargs: tuple[tuple[str, Any], ...] = ()

    @classmethod
    def parse(cls, value: str | Mapping[str, Any] | QlibProcessor) -> QlibProcessor:
        if isinstance(value, QlibProcessor):
            return value
        if isinstance(value, str):
            return cls(value)
        kwargs = dict(value.get("kwargs") or {})
        return cls(str(value["class"]), tuple(sorted(kwargs.items())))

    def to_dict(self) -> dict[str, Any]:
        return {"class": self.name, "kwargs": dict(self.kwargs)}


_DEFAULT_LEARN = (
    QlibProcessor("DropnaLabel"),
    QlibProcessor("CSZScoreNorm", (("fields_group", "label"),)),
)
_DEFAULT_INFER = (QlibProcessor("ProcessInf"), QlibProcessor("ZScoreNorm"), QlibProcessor("Fillna"))


@dataclass(frozen=True)
class QlibHandlerSpec:
    """Settings that define a Qlib handler workflow."""

    handler: str
    instruments: str = "csi500"
    freq: str = "day"
    label: str = QLIB_DEFAULT_LABEL
    infer_processors: tuple[QlibProcessor, ...] = ()
    learn_processors: tuple[QlibProcessor, ...] = _DEFAULT_LEARN
    fit_start_time: str | None = None
    fit_end_time: str | None = None

    @classmethod
    def alpha158(cls, **overrides: Any) -> QlibHandlerSpec:
        """Alpha158 defaults: no inference processors."""
        return cls._build("Alpha158", {"infer_processors": ()}, overrides)

    @classmethod
    def alpha360(cls, **overrides: Any) -> QlibHandlerSpec:
        """Alpha360 defaults: ``ProcessInf``, ``ZScoreNorm``, ``Fillna``."""
        return cls._build("Alpha360", {"infer_processors": _DEFAULT_INFER}, overrides)

    @classmethod
    def from_handler_config(cls, config: Mapping[str, Any]) -> QlibHandlerSpec:
        """Build from a Qlib workflow ``handler`` block (``class`` + ``kwargs``)."""
        handler = str(config.get("class", "custom"))
        kwargs = dict(config.get("kwargs") or {})
        base = {"Alpha158": cls.alpha158, "Alpha360": cls.alpha360}.get(handler)
        overrides = {
            key: kwargs[key]
            for key in (
                "instruments", "freq", "label", "fit_start_time", "fit_end_time",
                "infer_processors", "learn_processors",
            )
            if key in kwargs
        }
        if "label" in overrides and not isinstance(overrides["label"], str):
            overrides["label"] = list(overrides["label"])[0][0]
        if base is not None:
            return base(**overrides)
        return cls._build(handler, {}, overrides)

    @classmethod
    def _build(
        cls, handler: str, defaults: dict[str, Any], overrides: Mapping[str, Any]
    ) -> QlibHandlerSpec:
        values = {**defaults, **overrides}
        for key in ("infer_processors", "learn_processors"):
            if key in values:
                values[key] = tuple(QlibProcessor.parse(item) for item in values[key])
        for key in ("fit_start_time", "fit_end_time"):
            if values.get(key) is not None:
                values[key] = str(values[key])
        return cls(handler=handler, **values)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["infer_processors"] = [p.to_dict() for p in self.infer_processors]
        payload["learn_processors"] = [p.to_dict() for p in self.learn_processors]
        return payload


@dataclass(frozen=True)
class ConformanceIssue:
    """One difference between the Qlib workflow and the FactorMiner setup."""

    field: str
    qlib: Any
    factorminer: Any
    detail: str
    blocking: bool = True


@dataclass(frozen=True)
class ValueCheck:
    """Element-wise agreement of one exported column on the shared panel."""

    column: str
    compared: int
    nan_mismatches: int
    value_mismatches: int
    max_abs_diff: float
    missing_rows: int

    @property
    def passed(self) -> bool:
        return (
            self.compared > 0
            and self.nan_mismatches == 0
            and self.value_mismatches == 0
            and self.missing_rows == 0
        )


@dataclass
class ConformanceReport:
    """Processing and value conformance for one Qlib baseline comparison."""

    handler: dict[str, Any]
    issues: list[ConformanceIssue] = field(default_factory=list)
    value_checks: list[ValueCheck] = field(default_factory=list)
    accepted: list[str] = field(default_factory=list)

    @property
    def blocking_issues(self) -> list[ConformanceIssue]:
        return [
            issue for issue in self.issues if issue.blocking and issue.field not in self.accepted
        ]

    @property
    def conformant(self) -> bool:
        """True when no unaccepted difference remains and every value check passed."""
        return (
            not self.blocking_issues
            and bool(self.value_checks)
            and all(check.passed for check in self.value_checks)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "handler": self.handler,
            "conformant": self.conformant,
            "accepted_differences": list(self.accepted),
            "issues": [asdict(issue) for issue in self.issues],
            "value_checks": [
                {**asdict(check), "passed": check.passed} for check in self.value_checks
            ],
        }


def parse_qlib_label(label: str) -> tuple[str, str, int, int]:
    """Return ``(start_field, end_field, start_offset, end_offset)`` of a ratio label."""
    match = _LABEL_PATTERN.match(label)
    if match is None:
        raise ValueError(f"Unsupported Qlib label expression: {label!r}")
    return (
        match["start_field"], match["end_field"], int(match["start"]), int(match["end"])
    )


def _target_spec(cfg: Any) -> TargetSpec | None:
    data_cfg = getattr(cfg, "data", None)
    name = str(getattr(data_cfg, "default_target", "paper"))
    for raw in getattr(data_cfg, "targets", None) or []:
        if str(raw.get("name")) == name:
            return TargetSpec(
                name=name,
                entry_delay_bars=int(raw.get("entry_delay_bars", 0)),
                holding_bars=int(raw.get("holding_bars", 1)),
                price_pair=str(raw.get("price_pair", "open_to_close")),
                return_transform=str(raw.get("return_transform", "simple")),
            )
    return None


def compare_processing(
    spec: QlibHandlerSpec,
    cfg: Any,
    *,
    dataset_contract: Mapping[str, Any] | None = None,
    qlib_dataset_contract: Mapping[str, Any] | None = None,
) -> list[ConformanceIssue]:
    """List workflow settings where FactorMiner and Qlib would process data differently."""
    issues: list[ConformanceIssue] = []
    data_cfg = getattr(cfg, "data", None)

    target = _target_spec(cfg)
    try:
        qlib_label = parse_qlib_label(spec.label)
    except ValueError as exc:
        issues.append(ConformanceIssue("label", spec.label, None, str(exc)))
    else:
        ours = None
        if target is not None:
            start, end, start_offset, end_offset = _resolve_target_offsets(target)
            ours = (start, end, start_offset, end_offset)
            if target.return_transform != "simple":
                issues.append(ConformanceIssue(
                    "label.transform", "simple", target.return_transform,
                    "Qlib ratio labels are simple returns",
                ))
        if ours != qlib_label:
            issues.append(ConformanceIssue(
                "label", list(qlib_label), list(ours) if ours else None,
                "(start price, end price, start offset, end offset) differ",
            ))

    ours_freq = str(getattr(data_cfg, "frequency", ""))
    if _FREQUENCY_ALIASES.get(spec.freq.lower(), spec.freq) != _FREQUENCY_ALIASES.get(
        ours_freq.lower(), ours_freq
    ):
        issues.append(ConformanceIssue("freq", spec.freq, ours_freq, "bar frequency differs"))

    universe = str(getattr(data_cfg, "universe", ""))
    if spec.instruments.lower() != universe.lower():
        issues.append(ConformanceIssue(
            "instruments", spec.instruments, universe, "instrument universe differs"
        ))

    fit = [spec.fit_start_time, spec.fit_end_time]
    train = list(getattr(data_cfg, "train_period", []))
    if any(fit) and [str(value)[:10] for value in fit] != [str(value)[:10] for value in train]:
        issues.append(ConformanceIssue(
            "fit_window", fit, train,
            "processor statistics are fitted on a different window than FactorMiner's train split",
        ))

    feature_processors = [p.to_dict() for p in spec.infer_processors]
    ours_preprocessing = "factorminer.data.preprocessor.preprocess"
    if feature_processors:
        issues.append(ConformanceIssue(
            "infer_processors", feature_processors, ours_preprocessing,
            "Qlib normalizes handler features with these processors; FactorMiner "
            "evaluates formulas on its own preprocessed panel",
        ))
    label_processors = [p.to_dict() for p in spec.learn_processors]
    if any(p["class"] != "DropnaLabel" for p in label_processors):
        issues.append(ConformanceIssue(
            "learn_processors", label_processors, "raw target panel",
            "Qlib transforms the training label; FactorMiner IC uses the raw target "
            "(per-date monotone transforms leave rank IC unchanged but not Pearson IC)",
        ))

    contract = dict(dataset_contract or {})
    qlib_contract = dict(qlib_dataset_contract or {})
    policy_values = {
        "availability": AVAILABILITY_POLICIES,
        "universe_policy": UNIVERSE_POLICIES,
        "adjustment_policy": ADJUSTMENT_POLICIES,
    }
    for name, allowed in policy_values.items():
        ours = contract.get(name, "unspecified")
        qlib = qlib_contract.get(name, "unspecified")
        if ours not in allowed or qlib not in allowed:
            issues.append(ConformanceIssue(
                name, qlib, ours, f"policy must be one of {sorted(allowed)}",
            ))
        elif ours == "unspecified" or qlib == "unspecified":
            issues.append(ConformanceIssue(
                name, qlib, ours,
                f"declare {name} for both Qlib provider data and FactorMiner data",
            ))
        elif ours != qlib:
            issues.append(ConformanceIssue(
                name, qlib, ours, "provider data policies differ",
            ))
    return issues


def compare_values(
    qlib_values: pd.DataFrame,
    factorminer_values: pd.DataFrame,
    *,
    columns: Mapping[str, str] | Sequence[str] | None = None,
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> list[ValueCheck]:
    """Compare values both systems produced for the same ``(datetime, instrument)`` rows.

    ``columns`` maps Qlib column names to FactorMiner column names (or lists
    names shared by both). Rows present on one side only are counted as
    missing; NaN positions must agree exactly.
    """
    if not qlib_values.index.is_unique or not factorminer_values.index.is_unique:
        raise ValueError("Qlib and FactorMiner value exports must have unique row keys")
    if columns is None:
        mapping = {name: name for name in qlib_values.columns if name in factorminer_values.columns}
    elif isinstance(columns, Mapping):
        mapping = dict(columns)
    else:
        mapping = {name: name for name in columns}
    index = qlib_values.index.intersection(factorminer_values.index)
    missing = len(qlib_values.index.symmetric_difference(factorminer_values.index))
    checks: list[ValueCheck] = []
    for qlib_column, ours_column in mapping.items():
        left = qlib_values.loc[index, qlib_column].to_numpy(dtype=np.float64)
        right = factorminer_values.loc[index, ours_column].to_numpy(dtype=np.float64)
        left_nan, right_nan = np.isnan(left), np.isnan(right)
        both = ~(left_nan | right_nan)
        finite = np.isfinite(left[both]) & np.isfinite(right[both])
        close = np.isclose(left[both][finite], right[both][finite], rtol=rtol, atol=atol)
        diffs = np.abs(left[both][finite] - right[both][finite])
        checks.append(ValueCheck(
            column=f"{qlib_column}->{ours_column}",
            compared=int(finite.sum()),
            nan_mismatches=int((left_nan != right_nan).sum()),
            value_mismatches=int((~close).sum() + (~finite).sum()),
            max_abs_diff=float(diffs.max()) if diffs.size else 0.0,
            missing_rows=missing,
        ))
    return checks


def check_qlib_conformance(
    spec: QlibHandlerSpec,
    cfg: Any,
    *,
    dataset_contract: Mapping[str, Any] | None = None,
    qlib_dataset_contract: Mapping[str, Any] | None = None,
    qlib_values: pd.DataFrame | None = None,
    factorminer_values: pd.DataFrame | None = None,
    columns: Mapping[str, str] | Sequence[str] | None = None,
    accepted_differences: Sequence[str] = (),
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> ConformanceReport:
    """Check processing rules and, when exports are supplied, shared-panel values.

    ``accepted_differences`` names issue fields the caller deliberately
    tolerates. They stay in the report so readers see what was waived.
    """
    report = ConformanceReport(
        handler=spec.to_dict(),
        issues=compare_processing(
            spec, cfg, dataset_contract=dataset_contract,
            qlib_dataset_contract=qlib_dataset_contract,
        ),
        accepted=list(accepted_differences),
    )
    if qlib_values is not None and factorminer_values is not None:
        report.value_checks = compare_values(
            qlib_values, factorminer_values, columns=columns, rtol=rtol, atol=atol
        )
    return report


def require_conformance(report: ConformanceReport) -> None:
    """Raise unless a Qlib comparison may be reported as a like-for-like baseline."""
    if report.conformant:
        return
    reasons = [f"{issue.field}: {issue.detail}" for issue in report.blocking_issues]
    if not report.value_checks:
        reasons.append("no shared-panel value checks were supplied")
    reasons += [
        f"values {check.column}: {check.value_mismatches} value / "
        f"{check.nan_mismatches} NaN mismatches, {check.missing_rows} missing rows"
        for check in report.value_checks
        if not check.passed
    ]
    raise NonConformantBaselineError(
        "Qlib baseline is not comparable: " + "; ".join(reasons)
    )
