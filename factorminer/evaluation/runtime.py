"""Shared runtime evaluation helpers for strict factor recomputation."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt
import pandas as pd

from factorminer.core.factor_library import Factor
from factorminer.core.parser import try_parse
from factorminer.data.tensor_builder import TargetSpec, compute_targets
from factorminer.evaluation.metrics import (
    compute_factor_stats,
    compute_pairwise_correlation,
)

logger = logging.getLogger(__name__)

# Static paper defaults kept for backwards-compatible imports. Prefer the
# helpers below so extra registered leaves (fundamentals, futures, ...) map too.
FEATURE_TO_COLUMN = {
    "$open": "open",
    "$high": "high",
    "$low": "low",
    "$close": "close",
    "$volume": "volume",
    "$amt": "amount",
    "$vwap": "vwap",
    "$returns": "returns",
}

COLUMN_TO_FEATURE = {value: key for key, value in FEATURE_TO_COLUMN.items()}


def _feature_to_column(name: str) -> str:
    """Map a DSL leaf (or bare name) onto a panel DataFrame column."""
    from factorminer.core.types import feature_to_column

    return feature_to_column(name)


def _column_to_feature(column: str) -> str:
    """Map a panel column onto a DSL leaf name."""
    from factorminer.core.types import column_to_feature

    if column in COLUMN_TO_FEATURE:
        return COLUMN_TO_FEATURE[column]
    return column_to_feature(column)


class SignalComputationError(RuntimeError):
    """Raised when a factor cannot be recomputed under strict policies."""


@dataclass
class DatasetSplit:
    """One temporal view into the evaluation dataset."""

    name: str
    indices: np.ndarray
    timestamps: np.ndarray
    returns: np.ndarray
    target_returns: dict[str, np.ndarray] = field(default_factory=dict)
    default_target: str = "target"

    @property
    def size(self) -> int:
        return int(len(self.indices))

    def get_target(self, name: str | None = None) -> np.ndarray:
        target_name = name or self.default_target
        if target_name in self.target_returns:
            return self.target_returns[target_name]
        return self.returns


@dataclass
class EvaluationDataset:
    """Canonical dataset used for analysis commands."""

    data_dict: dict[str, np.ndarray]
    data_tensor: np.ndarray
    returns: np.ndarray
    timestamps: np.ndarray
    asset_ids: np.ndarray
    splits: dict[str, DatasetSplit]
    processed_df: pd.DataFrame = field(repr=False)
    target_panels: dict[str, np.ndarray] = field(default_factory=dict)
    target_specs: dict[str, TargetSpec] = field(default_factory=dict)
    default_target: str = "target"

    def get_split(self, name: str) -> DatasetSplit:
        if name not in self.splits:
            raise KeyError(f"Unknown split: {name}")
        return self.splits[name]

    def get_target(self, name: str | None = None) -> np.ndarray:
        target_name = name or self.default_target
        if target_name in self.target_panels:
            return self.target_panels[target_name]
        return self.returns


def build_runtime_dataset_from_arrays(
    data: Mapping[str, np.ndarray],
    returns: np.ndarray,
    *,
    feature_order: Sequence[str] | None = None,
    target_panels: Mapping[str, np.ndarray] | None = None,
    target_specs: Mapping[str, TargetSpec] | None = None,
    default_target: str = "target",
    split_indices: Mapping[str, Sequence[int] | np.ndarray] | None = None,
    timestamps: Sequence | np.ndarray | None = None,
    asset_ids: Sequence | np.ndarray | None = None,
) -> EvaluationDataset:
    """Build the canonical runtime dataset from aligned numerical panels.

    This is the array-native counterpart to :func:`load_runtime_dataset` and
    is used by synthetic benchmarks and programmatic callers.  All feature and
    target panels must share the canonical ``(assets, periods)`` orientation.
    """
    returns_array = np.asarray(returns, dtype=np.float64)
    if returns_array.ndim != 2:
        raise ValueError(
            f"returns must have shape (assets, periods); got {returns_array.shape}"
        )
    asset_count, period_count = returns_array.shape

    ordered_features = list(feature_order or data.keys())
    if not ordered_features:
        raise ValueError("at least one feature panel is required")
    missing = [name for name in ordered_features if name not in data]
    if missing:
        raise ValueError(f"feature_order contains missing panels: {missing}")

    data_dict: dict[str, np.ndarray] = {}
    for name in ordered_features:
        panel = np.asarray(data[name], dtype=np.float64)
        if panel.shape != returns_array.shape:
            raise ValueError(
                f"feature {name!r} has shape {panel.shape}; expected {returns_array.shape}"
            )
        data_dict[str(name)] = panel
    data_tensor = np.stack([data_dict[name] for name in ordered_features], axis=2)

    targets = {
        str(name): np.asarray(panel, dtype=np.float64)
        for name, panel in (target_panels or {default_target: returns_array}).items()
    }
    if default_target not in targets:
        raise ValueError(f"default target {default_target!r} is not present in target_panels")
    for name, panel in targets.items():
        if panel.shape != returns_array.shape:
            raise ValueError(
                f"target {name!r} has shape {panel.shape}; expected {returns_array.shape}"
            )

    timestamp_array = (
        np.arange(period_count) if timestamps is None else np.asarray(timestamps)
    )
    asset_array = np.arange(asset_count) if asset_ids is None else np.asarray(asset_ids)
    if timestamp_array.shape != (period_count,):
        raise ValueError(
            f"timestamps must have length {period_count}; got {timestamp_array.shape}"
        )
    if asset_array.shape != (asset_count,):
        raise ValueError(f"asset_ids must have length {asset_count}; got {asset_array.shape}")

    partitions = split_indices or {"full": np.arange(period_count)}
    splits: dict[str, DatasetSplit] = {}
    for name, raw_indices in partitions.items():
        indices = np.asarray(raw_indices, dtype=np.int64)
        if indices.ndim != 1:
            raise ValueError(f"split {name!r} indices must be one-dimensional")
        if indices.size and (int(indices.min()) < 0 or int(indices.max()) >= period_count):
            raise ValueError(f"split {name!r} contains out-of-range period indices")
        splits[str(name)] = DatasetSplit(
            name=str(name),
            indices=indices,
            timestamps=timestamp_array[indices],
            returns=returns_array[:, indices],
            target_returns={target: panel[:, indices] for target, panel in targets.items()},
            default_target=default_target,
        )

    return EvaluationDataset(
        data_dict=data_dict,
        data_tensor=data_tensor,
        returns=returns_array,
        timestamps=timestamp_array,
        asset_ids=asset_array,
        splits=splits,
        processed_df=pd.DataFrame(),
        target_panels=targets,
        target_specs=dict(target_specs or {}),
        default_target=default_target,
    )


@dataclass
class FactorEvaluationArtifact:
    """Recomputed signals and metrics for one factor."""

    factor_id: int
    name: str
    formula: str
    category: str
    parse_ok: bool
    signals_full: np.ndarray | None = None
    split_signals: dict[str, np.ndarray] = field(default_factory=dict)
    split_stats: dict[str, dict] = field(default_factory=dict)
    target_stats: dict[str, dict[str, dict]] = field(default_factory=dict)
    score_vector: dict | None = None
    research_metrics: dict[str, float] = field(default_factory=dict)
    error: str = ""
    # Set once signals have been computed successfully.  Kept separate from
    # ``signals_full`` so callers may release the panels (see
    # :meth:`release_signals`) without the artifact flipping to "failed".
    signals_ok: bool = False
    signals_released: bool = False

    @property
    def succeeded(self) -> bool:
        if not self.parse_ok or self.error:
            return False
        return self.signals_ok or self.signals_full is not None

    @property
    def has_signals(self) -> bool:
        """True while at least one signal panel is still resident."""
        return self.signals_full is not None or bool(self.split_signals)

    def release_signals(self) -> None:
        """Drop retained signal panels.

        Metrics in ``split_stats`` / ``target_stats`` are preserved, so an
        artifact stays usable for ranking, freezing and reporting after its
        (M, T) panels are freed.  This is the primary memory control for large
        universes: a released artifact costs kilobytes instead of
        ``M * T * 8`` bytes per retained split.
        """
        self.signals_full = None
        self.split_signals.clear()
        self.signals_released = True


def release_artifact_signals(artifacts) -> int:
    """Release signal panels on every artifact; returns the count released."""
    released = 0
    for artifact in artifacts:
        if artifact.has_signals:
            artifact.release_signals()
            released += 1
    return released


def _contiguous_slice(indices: np.ndarray) -> slice | None:
    """Return a ``slice`` equivalent to *indices* when they form a single run.

    Benchmark splits are always contiguous in time, so this lets split panels
    become views of the full panel instead of independent copies.
    """
    if indices.size == 0:
        return None
    if indices.size == 1:
        return slice(int(indices[0]), int(indices[0]) + 1)
    if not np.all(np.diff(indices) == 1):
        return None
    return slice(int(indices[0]), int(indices[-1]) + 1)


def load_runtime_dataset(
    raw_df: pd.DataFrame,
    cfg,
) -> EvaluationDataset:
    """Load raw market data into a canonical evaluation dataset."""
    from factorminer.data.preprocessor import preprocess
    from factorminer.data.tensor_builder import TensorConfig, build_tensor

    if not pd.api.types.is_datetime64_any_dtype(raw_df["datetime"]):
        raw_df = raw_df.copy()
        raw_df["datetime"] = pd.to_datetime(raw_df["datetime"])

    target_specs = _resolve_target_specs(cfg)
    target_df = compute_targets(raw_df, target_specs)
    target_columns = [spec.column_name for spec in target_specs]
    merge_columns = ["datetime", "asset_id", *target_columns]
    processed_df = preprocess(raw_df)
    processed_df = processed_df.merge(
        target_df[merge_columns],
        on=["datetime", "asset_id"],
        how="left",
    )
    processed_df = processed_df.sort_values(["datetime", "asset_id"]).reset_index(drop=True)

    feature_columns = _resolve_feature_columns(getattr(cfg.data, "features", []))
    tensor_cfg = TensorConfig(
        features=feature_columns,
        backend="numpy",
        dtype="float64",
        target_columns=target_columns,
        default_target=_target_column_for_name(cfg.data.default_target, target_specs),
    )
    dataset = build_tensor(processed_df, tensor_cfg)

    data_tensor = np.asarray(dataset.data, dtype=np.float64)
    returns = np.asarray(dataset.target, dtype=np.float64)
    target_panels = {
        spec.name: np.asarray(dataset.targets[spec.column_name], dtype=np.float64)
        for spec in target_specs
        if spec.column_name in dataset.targets
    }
    timestamps = pd.to_datetime(dataset.timestamps).to_numpy()
    asset_ids = np.asarray(dataset.asset_ids)

    if returns.ndim != 2:
        raise ValueError("Runtime dataset target must be a 2-D (M, T) array")

    data_dict = {
        _column_to_feature(column): data_tensor[:, :, idx]
        for idx, column in enumerate(dataset.feature_names)
    }

    splits = {
        "train": _build_named_split(
            "train",
            timestamps,
            returns,
            target_panels,
            cfg.data.default_target,
            start=cfg.data.train_period[0],
            end=cfg.data.train_period[1],
        ),
        "test": _build_named_split(
            "test",
            timestamps,
            returns,
            target_panels,
            cfg.data.default_target,
            start=cfg.data.test_period[0],
            end=cfg.data.test_period[1],
        ),
        "full": DatasetSplit(
            name="full",
            indices=np.arange(len(timestamps)),
            timestamps=timestamps,
            returns=returns,
            target_returns=target_panels,
            default_target=cfg.data.default_target,
        ),
    }

    validation_period = list(getattr(cfg.data, "validation_period", []))
    if validation_period:
        splits["validation"] = _build_named_split(
            "validation",
            timestamps,
            returns,
            target_panels,
            cfg.data.default_target,
            start=validation_period[0],
            end=validation_period[1],
        )

    for split_name in ("train", "validation", "test"):
        if split_name not in splits:
            continue
        if splits[split_name].size == 0:
            raise ValueError(
                f"{split_name} split is empty for configured period "
                f"{getattr(cfg.data, f'{split_name}_period')}"
            )

    return EvaluationDataset(
        data_dict=data_dict,
        data_tensor=data_tensor,
        returns=returns,
        timestamps=timestamps,
        asset_ids=asset_ids,
        splits=splits,
        processed_df=processed_df,
        target_panels=target_panels,
        target_specs={spec.name: spec for spec in target_specs},
        default_target=cfg.data.default_target,
    )


def evaluate_factors(
    factors: Sequence[Factor],
    dataset: EvaluationDataset,
    signal_failure_policy: str = "reject",
    target_name: str | None = None,
    *,
    retain_splits: Sequence[str] | None = None,
    retain_full: bool | None = None,
    signal_dtype: npt.DTypeLike | None = None,
) -> list[FactorEvaluationArtifact]:
    """Recompute factor signals and metrics across all dataset splits.

    Memory controls
    ---------------
    Each retained signal panel costs ``assets * periods * itemsize`` bytes, and
    a full benchmark keeps one artifact per candidate factor alive at once.  On
    a CSI1000 daily panel that is ~19 MB per float64 panel, so retention
    strategy decides whether a large-universe run fits in RAM:

    * Split panels are stored as **views** of the full panel whenever the split
      is contiguous in time (always true for train/validation/test).  That
      removes the two redundant full-size copies per factor the previous
      implementation made, at identical numerical output.
    * ``retain_splits`` restricts which split panels are kept.  Retained splits
      are stored as standalone copies so ``signals_full`` can then be dropped.
      Callers that only need metrics for ranking should pass the single split
      used for library admission (typically ``("train",)``).
    * ``retain_full=False`` keeps the per-split panels and drops the full panel.
    * ``signal_dtype`` stores panels in a narrower dtype (``np.float32`` halves
      the footprint; signal/IC statistics are unaffected at reporting
      precision).

    Parameters
    ----------
    factors, dataset, signal_failure_policy, target_name
        As before.
    retain_splits : sequence of str, optional
        Split names whose signal panels should be retained.  ``None`` keeps all
        of them as views of the full panel.
    retain_full : bool, optional
        Whether to keep ``signals_full``.  Defaults to ``retain_splits is None``.
    signal_dtype : dtype-like, optional
        Storage dtype for retained panels.  ``None`` keeps float64.
    """
    artifacts: list[FactorEvaluationArtifact] = []
    active_target_name = target_name or dataset.default_target
    active_returns = dataset.get_target(active_target_name)

    keep_splits = None if retain_splits is None else set(retain_splits)
    keep_full = (keep_splits is None) if retain_full is None else bool(retain_full)
    # Panels must be detached from the full array whenever the full array is
    # going to be dropped, otherwise the view would keep it alive anyway.
    detach = not keep_full or keep_splits is not None

    # Resolve split selectors once instead of per factor.
    split_selectors: dict[str, slice | np.ndarray] = {}
    for split_name, split in dataset.splits.items():
        selector = _contiguous_slice(np.asarray(split.indices))
        split_selectors[split_name] = (
            selector if selector is not None else np.asarray(split.indices)
        )

    for factor in factors:
        artifact = FactorEvaluationArtifact(
            factor_id=factor.id,
            name=factor.name,
            formula=factor.formula,
            category=factor.category,
            parse_ok=False,
        )

        tree = try_parse(factor.formula)
        if tree is None:
            artifact.error = "Parse failure"
            artifacts.append(artifact)
            continue

        artifact.parse_ok = True

        try:
            signals = compute_tree_signals(
                tree,
                dataset.data_dict,
                active_returns.shape,
                signal_failure_policy=signal_failure_policy,
            )
        except Exception as exc:
            artifact.error = str(exc)
            artifacts.append(artifact)
            continue

        if signals is None or np.all(np.isnan(signals)):
            artifact.error = "Signal computation produced only NaN values"
            artifacts.append(artifact)
            continue

        signals = np.asarray(signals, dtype=np.float64)
        if signal_dtype is not None and np.dtype(signal_dtype) != signals.dtype:
            signals = signals.astype(signal_dtype, copy=False)
        artifact.signals_ok = True

        for split_name, split in dataset.splits.items():
            split_signals = signals[:, split_selectors[split_name]]
            if keep_splits is None or split_name in keep_splits:
                artifact.split_signals[split_name] = (
                    np.array(split_signals, copy=True, order="C") if detach else split_signals
                )
            active_split_target = split.get_target(active_target_name)
            active_stats = compute_factor_stats(split_signals, active_split_target)
            artifact.split_stats[split_name] = active_stats
            artifact.target_stats[split_name] = {}
            for available_target_name, split_target in split.target_returns.items():
                artifact.target_stats[split_name][available_target_name] = (
                    active_stats
                    if available_target_name == active_target_name
                    else compute_factor_stats(split_signals, split_target)
                )

        artifact.signals_full = signals if keep_full else None
        artifacts.append(artifact)

    return artifacts


def compute_tree_signals(
    tree,
    data_dict: dict[str, np.ndarray],
    returns_shape: tuple[int, int],
    signal_failure_policy: str = "reject",
) -> np.ndarray:
    """Evaluate an expression tree under an explicit failure policy."""
    formula_str = tree.to_string()

    try:
        signals = tree.evaluate(data_dict)
    except Exception as exc:
        return _handle_signal_failure(
            formula_str=formula_str,
            returns_shape=returns_shape,
            signal_failure_policy=signal_failure_policy,
            cause=exc,
        )

    if signals is None or np.all(np.isnan(signals)):
        return _handle_signal_failure(
            formula_str=formula_str,
            returns_shape=returns_shape,
            signal_failure_policy=signal_failure_policy,
            cause=SignalComputationError("Signal computation produced only NaN values"),
        )

    return np.asarray(signals, dtype=np.float64)


def compute_correlation_matrix(
    artifacts: Sequence[FactorEvaluationArtifact],
    split_name: str,
) -> np.ndarray:
    """Compute a true pairwise factor correlation matrix on one split."""
    selected = [a for a in artifacts if a.succeeded]
    n = len(selected)
    matrix = np.zeros((n, n), dtype=np.float64)

    for i in range(n):
        for j in range(i + 1, n):
            corr = compute_pairwise_correlation(
                selected[i].split_signals[split_name],
                selected[j].split_signals[split_name],
            )
            matrix[i, j] = corr
            matrix[j, i] = corr

    return matrix


def select_top_k(
    artifacts: Sequence[FactorEvaluationArtifact],
    split_name: str,
    top_k: int | None = None,
) -> list[FactorEvaluationArtifact]:
    """Sort succeeded artifacts by split paper IC and return the top-k subset."""
    succeeded = [a for a in artifacts if a.succeeded]
    succeeded.sort(
        key=lambda artifact: abs(
            artifact.split_stats[split_name].get(
                "ic_paper_mean",
                artifact.split_stats[split_name].get("ic_abs_mean", 0.0),
            )
        ),
        reverse=True,
    )
    if top_k is None or top_k >= len(succeeded):
        return succeeded
    return succeeded[:top_k]


def summarize_failures(
    artifacts: Sequence[FactorEvaluationArtifact],
) -> list[str]:
    """Return human-readable failure summaries."""
    return [
        f"{artifact.name or artifact.factor_id}: {artifact.error}"
        for artifact in artifacts
        if not artifact.succeeded
    ]


def resolve_split_for_fit_eval(period: str) -> str:
    """Map fit/eval CLI period values to runtime split names."""
    return "full" if period == "both" else period


def analysis_split_names(period: str) -> list[str]:
    """Map analysis CLI period values to one or two runtime split names."""
    if period == "both":
        return ["train", "test"]
    return [period]


def _resolve_feature_columns(config_features: Sequence[str]) -> list[str]:
    if not config_features:
        return list(COLUMN_TO_FEATURE.values())

    resolved: list[str] = []
    seen: set[str] = set()
    for feature in config_features:
        col = _feature_to_column(str(feature))
        if col not in seen:
            seen.add(col)
            resolved.append(col)
    return resolved


def _build_named_split(
    name: str,
    timestamps: np.ndarray,
    returns: np.ndarray,
    target_panels: dict[str, np.ndarray],
    default_target: str,
    start: str,
    end: str,
) -> DatasetSplit:
    ts = pd.to_datetime(timestamps)
    mask = (ts >= pd.Timestamp(start)) & (ts <= pd.Timestamp(end))
    indices = np.where(mask)[0]
    return DatasetSplit(
        name=name,
        indices=indices,
        timestamps=timestamps[indices],
        returns=returns[:, indices],
        target_returns={
            target_name: panel[:, indices]
            for target_name, panel in target_panels.items()
        },
        default_target=default_target,
    )


def _resolve_target_specs(cfg) -> list[TargetSpec]:
    raw_targets = getattr(cfg.data, "targets", None) or [
        {
            "name": "paper",
            "entry_delay_bars": 1,
            "holding_bars": 1,
            "price_pair": "open_to_close",
            "return_transform": "simple",
        }
    ]
    return [
        TargetSpec(
            name=str(target["name"]),
            entry_delay_bars=int(target.get("entry_delay_bars", 0)),
            holding_bars=int(target.get("holding_bars", 1)),
            price_pair=str(target.get("price_pair", "open_to_close")),
            return_transform=str(target.get("return_transform", "simple")),
        )
        for target in raw_targets
    ]


def _target_column_for_name(target_name: str, specs: Sequence[TargetSpec]) -> str:
    for spec in specs:
        if spec.name == target_name:
            return spec.column_name
    return "target"


def _handle_signal_failure(
    formula_str: str,
    returns_shape: tuple[int, int],
    signal_failure_policy: str,
    cause: Exception,
) -> np.ndarray:
    if signal_failure_policy == "raise":
        raise cause

    if signal_failure_policy == "reject":
        raise SignalComputationError(
            f"Expression evaluation failed for '{formula_str}': {cause}"
        ) from cause

    if signal_failure_policy != "synthetic":
        raise ValueError(
            "signal_failure_policy must be one of: reject, synthetic, raise"
        )

    logger.warning(
        "Expression evaluation failed for '%s': %s — falling back to synthetic signals",
        formula_str,
        cause,
    )
    return generate_synthetic_signals(formula_str, returns_shape)


def generate_synthetic_signals(
    formula_str: str,
    returns_shape: tuple[int, int],
) -> np.ndarray:
    """Deterministic pseudo-signals for demo/mock workflows."""
    m, t = returns_shape
    digest = hashlib.sha256(formula_str.encode("utf-8")).digest()
    seed = int.from_bytes(digest[:8], "big") % (2**31)
    rng = np.random.RandomState(seed)
    signals = rng.randn(m, t).astype(np.float64)
    nan_mask = rng.random((m, t)) < 0.02
    signals[nan_mask] = np.nan
    return signals
