"""Per-stage runtime measurements for mining and benchmark evaluation.

The profile is observational: it records wall time, process memory, signal
panel allocations, cache counters, and rejection outcomes without changing
which candidates are evaluated or how they are scored.
"""

from __future__ import annotations

import sys
import threading
import time
import tracemalloc
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

RUNTIME_PROFILE_SCHEMA = "runtime-profile-v1"

try:  # ``resource`` is unavailable on Windows.
    import resource
except ImportError:  # pragma: no cover - platform dependent
    resource = None  # type: ignore[assignment]


def peak_rss_bytes() -> int:
    """Return the process high-water resident set size in bytes (0 if unknown)."""
    if resource is None:
        return 0
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports KiB; macOS reports bytes.
    return peak if sys.platform == "darwin" else peak * 1024


def classify_rejection(result: Any) -> str:
    """Map one evaluation result onto a stable outcome label."""
    if getattr(result, "admitted", False):
        return "replaced" if getattr(result, "replaced", None) is not None else "admitted"
    reason = str(getattr(result, "rejection_reason", "") or "").lower()
    if not getattr(result, "parse_ok", False):
        return "parse_failure" if "parse" in reason else "signal_error"
    if "all-nan" in reason:
        return "all_nan"
    if reason.startswith("fast-screen"):
        return "fast_screen"
    if "deduplication" in reason:
        return "dedup"
    if "icir" in reason:
        return "icir"
    if "< threshold" in reason or "below threshold" in reason:
        return "quality"
    if "dependence" in reason or "correlat" in reason or "replace" in reason:
        return "dependence"
    return "other"


@dataclass
class StageProfile:
    """Accumulated measurements for one named stage."""

    calls: int = 0
    seconds: float = 0.0
    peak_rss_bytes: int = 0
    rss_growth_bytes: int = 0
    traced_peak_bytes: int = 0
    panel_count: int = 0
    panel_bytes: int = 0
    outcomes: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "seconds": round(self.seconds, 6),
            "peak_rss_bytes": self.peak_rss_bytes,
            "rss_growth_bytes": self.rss_growth_bytes,
            "traced_peak_bytes": self.traced_peak_bytes,
            "panel_count": self.panel_count,
            "panel_bytes": self.panel_bytes,
            "outcomes": dict(sorted(self.outcomes.items())),
        }


class RuntimeProfile:
    """Thread-safe accumulator for per-stage runtime measurements.

    ``trace_allocations`` enables :mod:`tracemalloc`, whose per-stage peak
    includes NumPy buffers. It is precise but slows execution, so it is
    reserved for explicit profiling runs.
    """

    def __init__(self, *, trace_allocations: bool = False) -> None:
        self.trace_allocations = trace_allocations
        self.stages: dict[str, StageProfile] = {}
        self.counters: dict[str, int] = {}
        self._lock = threading.Lock()
        self._started = time.perf_counter()

    def _stage(self, name: str) -> StageProfile:
        return self.stages.setdefault(name, StageProfile())

    @contextmanager
    def stage(self, name: str) -> Iterator[StageProfile]:
        """Measure one execution of ``name``.

        Allocation tracing is process-wide, so traced stages must not nest or
        run concurrently; wall time and RSS are safe either way.
        """
        tracing = self.trace_allocations
        owns_trace = tracing and not tracemalloc.is_tracing()
        if owns_trace:
            tracemalloc.start()
        if tracing:
            tracemalloc.reset_peak()
            traced_start, _ = tracemalloc.get_traced_memory()
        rss_start = peak_rss_bytes()
        started = time.perf_counter()
        with self._lock:
            record = self._stage(name)
        try:
            yield record
        finally:
            elapsed = time.perf_counter() - started
            rss_end = peak_rss_bytes()
            traced_peak = 0
            if tracing:
                _, peak = tracemalloc.get_traced_memory()
                traced_peak = max(peak - traced_start, 0)
                if owns_trace:
                    tracemalloc.stop()
            with self._lock:
                record.calls += 1
                record.seconds += elapsed
                record.peak_rss_bytes = max(record.peak_rss_bytes, rss_end)
                record.rss_growth_bytes += max(rss_end - rss_start, 0)
                record.traced_peak_bytes = max(record.traced_peak_bytes, traced_peak)

    def record_panels(self, stage: str, panels: Iterable[Any]) -> None:
        """Count materialized signal panels attributed to ``stage``."""
        count = 0
        nbytes = 0
        for panel in panels:
            if panel is None:
                continue
            count += 1
            nbytes += int(getattr(panel, "nbytes", 0))
        with self._lock:
            record = self._stage(stage)
            record.panel_count += count
            record.panel_bytes += nbytes

    def record_outcomes(self, stage: str, results: Iterable[Any]) -> None:
        """Count candidate outcomes (admissions and rejection classes)."""
        labels = [classify_rejection(result) for result in results]
        with self._lock:
            outcomes = self._stage(stage).outcomes
            for label in labels:
                outcomes[label] = outcomes.get(label, 0) + 1

    def count(self, name: str, amount: int = 1) -> None:
        """Increment a named counter such as ``signal_cache_hits``."""
        with self._lock:
            self.counters[name] = self.counters.get(name, 0) + int(amount)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "schema_version": RUNTIME_PROFILE_SCHEMA,
                "wall_seconds": round(time.perf_counter() - self._started, 6),
                "peak_rss_bytes": peak_rss_bytes(),
                "trace_allocations": self.trace_allocations,
                "stages": {name: stage.to_dict() for name, stage in self.stages.items()},
                "counters": dict(sorted(self.counters.items())),
            }
