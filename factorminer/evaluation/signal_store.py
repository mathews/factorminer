"""Bounded storage for split signal panels.

``SplitSignalStore`` keeps retained split panels resident up to a byte budget.
When the budget is exceeded, least-recently-used panels are written to
``.npy`` files and later read back as read-only memory maps. Evicted signals
therefore keep their exact values, and resident memory is bounded by the
budget rather than by the number of candidates.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from factorminer.domain.signal_ref import SignalKey


class SignalUnavailableError(KeyError):
    """Raised when a released or never-stored signal is read."""


def dataset_fingerprint(dataset: Any) -> str:
    """Digest the numerical content and axes of an ``EvaluationDataset``."""
    digest = hashlib.sha256()
    for name in sorted(dataset.data_dict):
        panel = np.ascontiguousarray(dataset.data_dict[name], dtype=np.float64)
        digest.update(f"feature:{name}:{panel.shape}".encode())
        digest.update(panel.tobytes())
    for name in sorted(dataset.target_panels or {}):
        panel = np.ascontiguousarray(dataset.target_panels[name], dtype=np.float64)
        digest.update(f"target:{name}:{panel.shape}".encode())
        digest.update(panel.tobytes())
    digest.update(np.asarray(dataset.timestamps).astype(str).tobytes())
    digest.update(np.asarray(dataset.asset_ids).astype(str).tobytes())
    for name in sorted(dataset.splits):
        digest.update(f"split:{name}".encode())
        digest.update(np.asarray(dataset.splits[name].indices, dtype=np.int64).tobytes())
    return digest.hexdigest()


def split_selectors(splits: Mapping[str, Any]) -> dict[str, slice | np.ndarray]:
    """Return a contiguous slice (a view) or index array for each split."""
    selectors: dict[str, slice | np.ndarray] = {}
    for name, split in splits.items():
        indices = np.asarray(getattr(split, "indices", split))
        if indices.size and np.array_equal(
            indices, np.arange(indices[0], indices[0] + indices.size)
        ):
            selectors[name] = slice(int(indices[0]), int(indices[-1]) + 1)
        else:
            selectors[name] = indices
    return selectors


def open_signal_store(
    dataset: Any,
    *,
    retain_splits: Sequence[str],
    dtype: str = "float64",
    cache_mb: float | None = None,
) -> SplitSignalStore | None:
    """Build a bounded store for ``dataset``, or ``None`` when no budget is configured."""
    if cache_mb is None:
        return None
    return SplitSignalStore.for_dataset(
        dataset,
        retain_splits=tuple(dict.fromkeys(retain_splits)),
        dtype=dtype,
        max_resident_bytes=int(float(cache_mb) * 1024 * 1024),
    )


class SplitSignalStore:
    """Split-panel store with an optional resident-byte budget and disk spill.

    ``max_resident_bytes=None`` keeps every panel in memory. A duplicate
    ``put`` of the same key adds a reference instead of storing again. The
    panel is freed when every reference is released.
    """

    def __init__(
        self,
        *,
        selectors: Mapping[str, slice | np.ndarray],
        retain_splits: Sequence[str],
        dataset_digest: str,
        dtype: str = "float64",
        max_resident_bytes: int | None = None,
        spill_dir: str | Path | None = None,
    ) -> None:
        unknown = set(retain_splits) - set(selectors)
        if unknown:
            raise ValueError(f"Unknown retained splits: {sorted(unknown)}")
        if np.dtype(dtype) not in (np.dtype("float32"), np.dtype("float64")):
            raise ValueError("signal dtype must be float32 or float64")
        if max_resident_bytes is not None and max_resident_bytes < 0:
            raise ValueError("max_resident_bytes must be non-negative")
        self.selectors = dict(selectors)
        self.retain_splits = tuple(retain_splits)
        self.dataset_digest = dataset_digest
        self.dtype = np.dtype(dtype)
        self.max_resident_bytes = max_resident_bytes
        self._spill_root = Path(spill_dir) if spill_dir is not None else None
        self._owned_spill: tempfile.TemporaryDirectory[str] | None = None
        self._resident: OrderedDict[tuple[str, str], np.ndarray] = OrderedDict()
        self._spilled: dict[tuple[str, str], Path] = {}
        self._refs: dict[str, int] = {}
        self._lock = threading.Lock()
        self.resident_bytes = 0
        self.peak_resident_bytes = 0
        self.spilled_bytes = 0
        self.hits = 0
        self.spill_reads = 0
        self.evictions = 0

    @classmethod
    def for_dataset(
        cls,
        dataset: Any,
        *,
        retain_splits: Sequence[str],
        dtype: str = "float64",
        max_resident_bytes: int | None = None,
        spill_dir: str | Path | None = None,
        dataset_digest: str | None = None,
    ) -> SplitSignalStore:
        return cls(
            selectors=split_selectors(dataset.splits),
            retain_splits=retain_splits,
            dataset_digest=dataset_digest or dataset_fingerprint(dataset),
            dtype=dtype,
            max_resident_bytes=max_resident_bytes,
            spill_dir=spill_dir,
        )

    # ------------------------------------------------------------------
    # SignalStore protocol
    # ------------------------------------------------------------------

    def put(self, key: SignalKey, panel: np.ndarray) -> None:
        token = key.token
        with self._lock:
            if token in self._refs:
                self._refs[token] += 1
                return
            self._refs[token] = 1
            for split in self.retain_splits:
                stored = np.array(panel[:, self.selectors[split]], dtype=self.dtype, order="C")
                stored.flags.writeable = False
                self._resident[(token, split)] = stored
                self.resident_bytes += stored.nbytes
            self.peak_resident_bytes = max(self.peak_resident_bytes, self.resident_bytes)
            self._enforce_budget()

    def get_split(self, key: SignalKey, split: str) -> np.ndarray:
        entry = (key.token, split)
        with self._lock:
            panel = self._resident.get(entry)
            if panel is not None:
                self._resident.move_to_end(entry)
                self.hits += 1
                return panel
            path = self._spilled.get(entry)
            if path is None:
                raise SignalUnavailableError(f"No stored {split!r} signals for {key.formula_digest[:12]}")
            self.spill_reads += 1
        mapped: np.ndarray = np.load(path, mmap_mode="r")
        return mapped

    def release(self, key: SignalKey) -> None:
        token = key.token
        with self._lock:
            count = self._refs.get(token, 0)
            if count > 1:
                self._refs[token] = count - 1
                return
            self._refs.pop(token, None)
            for split in self.retain_splits:
                panel = self._resident.pop((token, split), None)
                if panel is not None:
                    self.resident_bytes -= panel.nbytes
                path = self._spilled.pop((token, split), None)
                if path is not None:
                    self.spilled_bytes -= path.stat().st_size
                    path.unlink(missing_ok=True)

    def has(self, key: SignalKey) -> bool:
        with self._lock:
            return key.token in self._refs

    # ------------------------------------------------------------------

    def _spill_dir(self) -> Path:
        if self._spill_root is None:
            self._owned_spill = tempfile.TemporaryDirectory(prefix="factorminer-signals-")
            self._spill_root = Path(self._owned_spill.name)
        self._spill_root.mkdir(parents=True, exist_ok=True)
        return self._spill_root

    def _enforce_budget(self) -> None:
        if self.max_resident_bytes is None:
            return
        while self._resident and self.resident_bytes > self.max_resident_bytes:
            (token, split), panel = self._resident.popitem(last=False)
            path = self._spill_dir() / f"{token}.{split}.npy"
            np.save(path, panel)
            self._spilled[(token, split)] = path
            self.resident_bytes -= panel.nbytes
            self.spilled_bytes += path.stat().st_size
            self.evictions += 1

    def stats(self) -> dict[str, int | None]:
        with self._lock:
            return {
                "max_resident_bytes": self.max_resident_bytes,
                "resident_bytes": self.resident_bytes,
                "peak_resident_bytes": self.peak_resident_bytes,
                "spilled_bytes": self.spilled_bytes,
                "signals": len(self._refs),
                "hits": self.hits,
                "spill_reads": self.spill_reads,
                "evictions": self.evictions,
            }

    def close(self) -> None:
        """Release every panel and remove spill files this store created."""
        with self._lock:
            for path in self._spilled.values():
                path.unlink(missing_ok=True)
            self._resident.clear()
            self._spilled.clear()
            self._refs.clear()
            self.resident_bytes = 0
            self.spilled_bytes = 0
        if self._owned_spill is not None:
            self._owned_spill.cleanup()
            self._owned_spill = None
            self._spill_root = None

    def __enter__(self) -> SplitSignalStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        owned = getattr(self, "_owned_spill", None)
        if owned is not None:
            shutil.rmtree(owned.name, ignore_errors=True)
