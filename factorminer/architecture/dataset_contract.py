"""Stable dataset pipeline contracts for mining and analysis."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
from typing import Any

import numpy as np

AVAILABILITY_POLICIES = frozenset(
    {"unspecified", "bar_close", "next_bar_open", "declared_timestamp"}
)
UNIVERSE_POLICIES = frozenset(
    {"unspecified", "static", "point_in_time", "survivorship_biased"}
)
ADJUSTMENT_POLICIES = frozenset(
    {"unspecified", "none", "split_adjusted", "split_dividend_adjusted", "back_adjusted_futures"}
)

# Provenance fields added after the original contract. They enter ``to_dict``
# (and therefore trial/campaign identity) only when declared, so contracts
# that declare nothing keep their historical identity.
_DECLARED_FIELDS = (
    "source_version",
    "availability",
    "availability_lag_bars",
    "universe_policy",
    "adjustment_policy",
    "preprocessing_digest",
)
# Content digests are replay evidence, not identity inputs: mining identity
# already hashes the exact panels.
_REPLAY_ONLY_FIELDS = ("panel_digest", "target_digest")


def _safe_len(value: Any) -> int:
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 0


def _digest_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


def panel_digest(panels: Mapping[str, Any] | Any) -> str:
    """Digest named numerical panels (or one array) by dtype, shape, and bytes."""
    digest = hashlib.sha256()
    items = panels.items() if isinstance(panels, Mapping) else [("", panels)]
    for name, value in sorted(items, key=lambda item: str(item[0])):
        array = np.ascontiguousarray(np.asarray(value))
        digest.update(f"{name}\0{array.dtype}\0{list(array.shape)}\0".encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def preprocessing_digest(spec: Mapping[str, Any] | None) -> str:
    """Digest a preprocessing description; empty when nothing was declared."""
    return _digest_json(dict(spec)) if spec else ""


def _declared_provenance(cfg: Any) -> dict[str, Any]:
    data_cfg = getattr(cfg, "data", None)
    return {
        "source_version": str(getattr(data_cfg, "source_version", "") or ""),
        "availability": str(getattr(data_cfg, "availability", "unspecified") or "unspecified"),
        "availability_lag_bars": int(getattr(data_cfg, "availability_lag_bars", 0) or 0),
        "universe_policy": str(getattr(data_cfg, "universe_policy", "unspecified") or "unspecified"),
        "adjustment_policy": str(
            getattr(data_cfg, "adjustment_policy", "unspecified") or "unspecified"
        ),
    }


@dataclass(frozen=True)
class DatasetContract:
    """Canonical description of how raw data became the mining tensors.

    Beyond shapes and targets, the contract records where the data came from
    (``source_version``), when each bar's values became knowable
    (``availability`` plus ``availability_lag_bars``), how universe membership
    was decided (``universe_policy``), how prices were adjusted
    (``adjustment_policy``), and a digest of the preprocessing applied.
    ``panel_digest`` and ``target_digest`` identify the exact feature and
    target panels so a replay can prove it used the same inputs.
    """

    feature_names: list[str]
    data_shape: tuple[int, ...]
    returns_shape: tuple[int, ...]
    default_target: str
    target_names: list[str]
    target_horizons: dict[str, int] = field(default_factory=dict)
    train_period: list[str] = field(default_factory=list)
    test_period: list[str] = field(default_factory=list)
    asset_count: int = 0
    period_count: int = 0
    split_sizes: dict[str, int] = field(default_factory=dict)
    extra_features: list[str] = field(default_factory=list)
    asset_class: str = "equity"
    source_version: str = ""
    availability: str = "unspecified"
    availability_lag_bars: int = 0
    universe_policy: str = "unspecified"
    adjustment_policy: str = "unspecified"
    preprocessing_digest: str = ""
    panel_digest: str = ""
    target_digest: str = ""

    def __post_init__(self) -> None:
        if self.availability not in AVAILABILITY_POLICIES:
            raise ValueError(f"availability must be one of {sorted(AVAILABILITY_POLICIES)}")
        if self.universe_policy not in UNIVERSE_POLICIES:
            raise ValueError(f"universe_policy must be one of {sorted(UNIVERSE_POLICIES)}")
        if self.adjustment_policy not in ADJUSTMENT_POLICIES:
            raise ValueError(f"adjustment_policy must be one of {sorted(ADJUSTMENT_POLICIES)}")
        if self.availability_lag_bars < 0:
            raise ValueError("availability_lag_bars must be non-negative")

    @classmethod
    def from_runtime_dataset(cls, cfg: Any, dataset: Any) -> DatasetContract:
        target_specs = getattr(dataset, "target_specs", {}) or {}
        asset_ids = getattr(dataset, "asset_ids", None)
        timestamps = getattr(dataset, "timestamps", None)
        splits = getattr(dataset, "splits", None) or {}
        data_dict = getattr(dataset, "data_dict", {}) or {}
        target_panels = getattr(dataset, "target_panels", {}) or {}
        feature_names = list(data_dict.keys())
        default_feats = {
            "$open", "$high", "$low", "$close", "$volume", "$amt", "$vwap", "$returns",
            "open", "high", "low", "close", "volume", "amount", "vwap", "returns",
        }
        extras = [f for f in feature_names if f not in default_feats]
        asset_class = str(
            getattr(getattr(cfg, "data", None), "asset_class", None)
            or getattr(getattr(cfg, "data", None), "market", "equity")
            or "equity"
        )
        target_definitions = {
            name: asdict(spec) if hasattr(spec, "__dataclass_fields__") else str(spec)
            for name, spec in target_specs.items()
        }
        return cls(
            feature_names=feature_names,
            data_shape=tuple(np.shape(getattr(dataset, "data_tensor", ()))),
            returns_shape=tuple(np.shape(getattr(dataset, "returns", ()))),
            default_target=str(
                getattr(dataset, "default_target", getattr(cfg.data, "default_target", "paper"))
            ),
            target_names=list(target_panels.keys())
            or [str(getattr(cfg.data, "default_target", "paper"))],
            target_horizons={
                name: max(int(getattr(spec, "holding_bars", 1)), 1)
                for name, spec in target_specs.items()
            },
            train_period=list(getattr(cfg.data, "train_period", [])),
            test_period=list(getattr(cfg.data, "test_period", [])),
            asset_count=int(_safe_len(asset_ids)),
            period_count=int(_safe_len(timestamps)),
            split_sizes={
                name: int(getattr(split, "size", 0))
                for name, split in splits.items()
            },
            extra_features=extras,
            asset_class=asset_class,
            **_declared_provenance(cfg),
            preprocessing_digest=preprocessing_digest(getattr(dataset, "preprocessing", None)),
            panel_digest=panel_digest(
                {
                    **{f"feature:{k}": v for k, v in data_dict.items()},
                    "axis:timestamps": np.asarray(timestamps).astype(str),
                    "axis:assets": np.asarray(asset_ids).astype(str),
                }
            ),
            target_digest=_digest_json(
                {
                    "panels": panel_digest(target_panels),
                    "definitions": target_definitions,
                    "default": getattr(dataset, "default_target", None),
                }
            ),
        )

    @classmethod
    def from_arrays(
        cls,
        cfg: Any,
        *,
        data_tensor: Any,
        returns: np.ndarray,
        target_panels: dict[str, np.ndarray] | None = None,
        target_horizons: dict[str, int] | None = None,
        preprocessing: Mapping[str, Any] | None = None,
    ) -> DatasetContract:
        feature_names = list(getattr(getattr(cfg, "data", None), "features", []))
        default_feats = {
            "$open", "$high", "$low", "$close", "$volume", "$amt", "$vwap", "$returns",
        }
        extras = [f for f in feature_names if f not in default_feats]
        asset_class = str(
            getattr(getattr(cfg, "data", None), "asset_class", None)
            or getattr(getattr(cfg, "data", None), "market", "equity")
            or "equity"
        )
        default_target = str(getattr(getattr(cfg, "data", None), "default_target", "paper"))
        return cls(
            feature_names=feature_names,
            data_shape=tuple(np.shape(data_tensor)),
            returns_shape=tuple(np.shape(returns)),
            default_target=default_target,
            target_names=list((target_panels or {}).keys()) or ["paper"],
            target_horizons=dict(target_horizons or {}),
            train_period=list(getattr(getattr(cfg, "data", None), "train_period", [])),
            test_period=list(getattr(getattr(cfg, "data", None), "test_period", [])),
            asset_count=int(np.shape(returns)[0]) if np.ndim(returns) >= 1 else 0,
            period_count=int(np.shape(returns)[1]) if np.ndim(returns) >= 2 else 0,
            extra_features=extras,
            asset_class=asset_class,
            **_declared_provenance(cfg),
            preprocessing_digest=preprocessing_digest(preprocessing),
            panel_digest=panel_digest(data_tensor),
            target_digest=_digest_json(
                {
                    "panels": panel_digest(target_panels or {"paper": returns}),
                    "horizons": dict(target_horizons or {}),
                    "default": default_target,
                }
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Identity-bearing description; undeclared provenance is omitted."""
        payload = asdict(self)
        defaults = {item.name: item.default for item in fields(self)}
        for name in _DECLARED_FIELDS:
            if payload[name] == defaults[name]:
                payload.pop(name)
        for name in _REPLAY_ONLY_FIELDS:
            payload.pop(name)
        return payload

    def replay_identity(self) -> dict[str, Any]:
        """Everything a replay must reproduce: declarations plus content digests."""
        payload = asdict(self)
        payload["data_shape"] = list(self.data_shape)
        payload["returns_shape"] = list(self.returns_shape)
        return payload

    def replay_mismatches(self, recorded: Mapping[str, Any]) -> list[str]:
        """Fields of a recorded replay identity that differ from this contract.

        Fields absent from ``recorded`` (older manifests) are not compared.
        """
        current = self.replay_identity()
        mismatches = []
        for name, value in recorded.items():
            if name in current and _normalize(current[name]) != _normalize(value):
                mismatches.append(name)
        return sorted(mismatches)


def _normalize(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))
