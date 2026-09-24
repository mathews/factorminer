"""Identity and handles for stored factor signal panels.

A :class:`SignalKey` names one formula's signals on one dataset under one set
of operator semantics, so a stored panel can be reused or audited without
recomputation. A :class:`SignalRef` is a lightweight handle that reads split
panels from a :class:`SignalStore` and releases them explicitly.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping
from dataclasses import asdict, dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class SignalKey:
    """Provenance-complete identity of one signal panel."""

    dataset_digest: str
    formula_digest: str
    operator_version: str
    backend: str = "numpy"
    dtype: str = "float64"

    @property
    def token(self) -> str:
        """Stable, filename-safe digest of every key field."""
        payload = "\x00".join(
            (self.dataset_digest, self.formula_digest, self.operator_version, self.backend, self.dtype)
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class SignalStore(Protocol):
    """Storage for signal panels addressed by :class:`SignalKey`."""

    def get_split(self, key: SignalKey, split: str) -> np.ndarray: ...

    def put(self, key: SignalKey, panel: np.ndarray) -> None: ...

    def release(self, key: SignalKey) -> None: ...

    def has(self, key: SignalKey) -> bool: ...


@dataclass(frozen=True)
class SignalRef:
    """Handle to one stored panel and the splits it can serve."""

    key: SignalKey
    store: SignalStore
    splits: tuple[str, ...]

    def get_split(self, split: str) -> np.ndarray:
        return self.store.get_split(self.key, split)

    def release(self) -> None:
        self.store.release(self.key)


class SplitSignalView(Mapping[str, np.ndarray]):
    """Read-only ``split -> panel`` mapping backed by a :class:`SignalRef`.

    It stands in for an in-memory ``dict`` of split panels. Reads go through
    the store, so they may be served from disk after eviction. ``clear``
    releases the stored panel.
    """

    def __init__(self, ref: SignalRef) -> None:
        self.ref = ref
        self._released = False

    def _live(self) -> bool:
        return not self._released and self.ref.store.has(self.ref.key)

    def __getitem__(self, split: str) -> np.ndarray:
        if split not in self.ref.splits or not self._live():
            raise KeyError(split)
        return self.ref.get_split(split)

    def __iter__(self) -> Iterator[str]:
        return iter(self.ref.splits if self._live() else ())

    def __len__(self) -> int:
        return len(self.ref.splits) if self._live() else 0

    def clear(self) -> None:
        if not self._released:
            self._released = True
            self.ref.release()
