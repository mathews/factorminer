"""Vectorized drop-in replacement for FactorMiner's pairwise Spearman gate.

WHY THIS EXISTS
---------------
``factorminer/domain/dependence.py::SpearmanDependenceMetric.compute`` ranks the
cross-section **one period at a time** inside a Python loop::

    for col_a, col_b in _iter_valid_columns(signals_a, signals_b):
        scores.append(_pearson_abs(rankdata(col_a), rankdata(cb)))

On a (500 assets x 2429 periods) panel that is 2429 iterations x 2
``scipy.stats.rankdata`` calls **per pair of signals**.  The mining loop runs
O(candidates x |L|) such pairs per iteration, so wall time grows linearly with
library size.  Measured on output3 (run 20260917_095745):

    ~1.4 s per pairwise Spearman
    ~1.4 full-library scans per candidate
    => ~78 s x L per iteration for a 40-candidate batch
    Iter 1 (L=6)   1016 s      Iter 7 (L=55.5) 4549 s

EVOLUTION
---------
v2 cached per-factor ranks computed under each factor's own NaN mask and
re-ranked every period whose two masks disagreed.  Exact, but the re-rank was a
second full sort, and on real panels 40-95% of periods disagree, so it only
recovered ~5x.

v3 drops the second sort: joint-subset ranks are derived from the cached ranks
by **rank compression** (see :func:`_joint_ranks_sorted`).  Four supporting
tricks:

* gathers/scatters go through a precomputed *flat* index (``np.take(mode=
  'clip')`` / direct assignment), which is 3-5x faster than
  ``take_along_axis`` / ``put_along_axis``;
* scratch arrays come from a thread-local pool -- without it every call
  allocates ~50 MB of temporaries and the page faults cost more than the
  arithmetic (~20 of ~60 ms measured on real panels);
* the correlation is accumulated in whichever space needs the fewest moves:
  Pearson is invariant to a permutation applied identically to both operands,
  so instead of returning both panels to asset space (2 scatters) only one of
  them is remapped (1-2 gathers);
* tie groups are corrected only where they exist, and periods where nothing has
  to be removed skip that side entirely.

EXACTNESS
---------
Bitwise equal to the legacy metric: it reproduces ``rankdata`` on the jointly
valid subset (average ranks for ties included) and the same mean-centered
Pearson with the same >= 3 valid-observation filter.  ``verify.py`` checks 12
synthetic + real panel pairs against the verbatim legacy implementation.

USAGE
-----
    import fast_dependence   # applies patches on import

Or drop into the venv's site-packages renamed to ``sitecustomize.py``; CPython
imports it automatically.  Disable with ``FACTORMINER_FAST_SPEARMAN=0``.

MEMORY
------
~22 MB per prepared panel at (2429 periods x 500 assets), ~27 MB when the panel
contains tied valid values.  The scratch pool adds ~35 MB *per worker thread*,
so keep ``num_workers`` at or below the physical core count.  Set
``FACTORMINER_FAST_SPEARMAN_POOL=0`` to allocate fresh arrays instead.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import NamedTuple, Optional

import numpy as np

if os.environ.get("FACTORMINER_FAST_SPEARMAN", "1") == "0":  # pragma: no cover
    raise ImportError("FACTORMINER_FAST_SPEARMAN=0 - fast spearman disabled")

# Skip the rank-compression correction and use the cached self-mask ranks as if
# they were joint ranks.  Faster still, but biased low: on output3's real panels
# most pairs err < 0.002, worst observed 0.038.  Exploration only.
APPROXIMATE = os.environ.get("FACTORMINER_FAST_SPEARMAN_APPROX", "1") == "1"
USE_POOL = os.environ.get("FACTORMINER_FAST_SPEARMAN_POOL", "1") == "1"

_HALF = np.float32(0.5)

# ---------------------------------------------------------------------------
# Thread-local scratch buffers
# ---------------------------------------------------------------------------


class _Pool:
    """Shape-keyed scratch arrays, reused across calls to avoid page faults."""

    def __init__(self) -> None:
        self._arrays: dict[str, np.ndarray] = {}

    def get(self, key: str, shape, dtype) -> np.ndarray:
        buf = self._arrays.get(key)
        if buf is None or buf.shape != shape or buf.dtype != dtype:
            buf = np.empty(shape, dtype=dtype)
            if USE_POOL:
                self._arrays[key] = buf
        return buf


_local = threading.local()


def _buf(key: str, shape, dtype) -> np.ndarray:
    pool = getattr(_local, "pool", None)
    if pool is None:
        pool = _local.pool = _Pool()
    return pool.get(key, tuple(shape), np.dtype(dtype))


class Prepared(NamedTuple):
    """One signal panel, pre-ranked once so pairwise work stays cheap.

    Arrays are ``(periods, assets)``: rows are periods because the metric ranks
    cross-sections.  "sorted" arrays are indexed by *rank position* within a
    period (0 = smallest value), "orig" arrays by asset index.
    """

    rank_sort: np.ndarray  # float32, average ranks in rank-position space
    rank_orig: np.ndarray  # float32, the same ranks in asset-index space
    valid_sort: np.ndarray  # bool, True where a sorted-slot entry is not NaN
    valid_orig: np.ndarray  # bool, True where the asset is not NaN
    order_flat: np.ndarray  # int32 flat permutation: rank position -> asset
    inv_flat: np.ndarray  # int32 flat inverse: asset -> rank position
    grp_start: Optional[np.ndarray]  # first rank position of each entry's tie group
    grp_end: Optional[np.ndarray]  # last rank position of each entry's tie group
    tie_row: Optional[np.ndarray]  # bool per period: do tied *valid* values exist?


def prepare(signals: np.ndarray) -> Prepared:
    """Rank one (assets, periods) panel once, keeping everything pair loops need."""
    arr = np.asarray(signals, dtype=np.float64)
    if arr.ndim != 2:
        raise ValueError(f"expected a 2-D (assets, periods) panel, got {arr.shape}")

    transposed = np.ascontiguousarray(arr.T)
    n_rows, n_cols = transposed.shape

    valid_orig = ~np.isnan(transposed)
    if valid_orig.all():
        filled = transposed
    else:
        # +inf sorts last, so every real value keeps exactly the rank it would
        # have received from rankdata() on the NaN-free subset.
        filled = np.where(valid_orig, transposed, np.inf)

    order = np.argsort(filled, axis=1)
    # Flat period-offset permutations: np.take(source.ravel(), idx_flat) is 3-5x
    # faster than take_along_axis(source, order, axis=1).
    row_offset = (np.arange(n_rows, dtype=np.int64) * n_cols)[:, None]
    order_flat = np.ascontiguousarray((order + row_offset).ravel(), dtype=np.int32)
    inv_flat = np.empty(n_rows * n_cols, dtype=np.int32)
    inv_flat[order_flat] = np.arange(n_rows * n_cols, dtype=np.int32)
    del order, row_offset

    flat = (n_rows * n_cols,)
    # NOTE: prepare() must own its output arrays -- the scratch pool is shared
    # per-thread, so pooling here would let a later prepare() overwrite an
    # already-cached Prepared panel.
    valid_sort = np.take(
        valid_orig.reshape(-1), order_flat, mode="clip", out=np.empty(flat[0], dtype=bool)
    ).reshape(n_rows, n_cols)
    sorted_vals = np.take(filled.reshape(-1), order_flat, mode="clip").reshape(n_rows, n_cols)

    # --- tie groups: contiguous runs of equal value along each row ----------
    starts = np.empty((n_rows, n_cols), dtype=bool)
    starts[:, 0] = True
    if n_cols > 1:
        starts[:, 1:] = sorted_vals[:, 1:] != sorted_vals[:, :-1]
    del sorted_vals, filled

    leader_rows, leader_cols = np.nonzero(starts)  # one entry per tie group
    groups_per_row = starts.sum(axis=1)
    row_end = np.cumsum(groups_per_row)

    start_flat = leader_cols.astype(np.int32)
    size_flat = np.empty(int(groups_per_row.sum()), dtype=np.int32)
    if size_flat.size > 1:
        size_flat[:-1] = start_flat[1:] - start_flat[:-1]
    size_flat[row_end - 1] = n_cols - start_flat[row_end - 1]

    # 1-based average rank of a group starting at 0-based position s, size c:
    #   it occupies ranks s+1 .. s+c  ->  mean = s + 1 + (c - 1) / 2
    avg_group = start_flat.astype(np.float64) + 1.0 + (size_flat - 1.0) * 0.5

    # Groups occupy contiguous positions in row-major order, so `repeat` expands
    # group-level values back to per-position arrays without a single gather.
    rank_sort = np.ascontiguousarray(
        np.repeat(avg_group, size_flat).reshape(n_rows, n_cols), dtype=np.float32
    )
    del avg_group

    rank_flat = np.empty(n_rows * n_cols, dtype=np.float32)
    rank_flat[order_flat] = rank_sort.reshape(-1)

    # Tie bookkeeping is only needed where a *valid* value repeats.
    grp_start = grp_end = tie_row = None
    tied = valid_sort[leader_rows, leader_cols] & (size_flat > 1)
    if tied.any():
        tie_row = np.bincount(leader_rows, weights=tied, minlength=n_rows) > 0.5
        grp_start = np.ascontiguousarray(
            np.repeat(start_flat, size_flat).reshape(n_rows, n_cols), dtype=np.int16
        )
        grp_end = np.ascontiguousarray(
            np.repeat(start_flat + size_flat - 1, size_flat).reshape(n_rows, n_cols),
            dtype=np.int16,
        )

    return Prepared(
        rank_sort=rank_sort,
        rank_orig=rank_flat.reshape(n_rows, n_cols),
        valid_sort=valid_sort,
        valid_orig=np.ascontiguousarray(valid_orig),
        order_flat=order_flat,
        inv_flat=inv_flat,
        grp_start=grp_start,
        grp_end=grp_end,
        tie_row=tie_row,
    )


def _joint_ranks_sorted(side: Prepared, partner: Prepared, slot: str):
    """Joint-subset ranks of ``side`` *in its own rank-position space*.

    Returns ``(ranks, joint_valid)`` where ``joint_valid`` is the jointly valid
    mask expressed in the same space.

    RANK COMPRESSION
    ----------------
    Let S be the entries valid in ``side``, J = S intersected with the entries
    valid in ``partner``, and R = S - J the *removed* ones.  ``rankdata`` on J
    assigns

        rank_J(x) = 1 + #{y in J: y < x} + (#{y in J: y == x} - 1) / 2

    Substituting J = S - R into the cached self-mask rank gives

        rank_J(x) = rank_S(x) - cnt_lt(x) - cnt_eq(x) / 2

    with cnt_lt / cnt_eq the number of removed entries below / tied with x.  In
    rank-position space those are just running counts along the sorted order:
    with C the inclusive and X = C - R the exclusive cumsum of R,

        cnt_lt(x) = X[gs(x)]          cnt_eq(x) = C[ge(x)] - X[gs(x)]

    where gs / ge bound x's tie group, so the correction collapses to

        ( X[gs(x)] + C[ge(x)] ) / 2

    Singleton tie groups give gs == ge == p and remove even those two gathers,
    leaving the elementwise ``(C + X) / 2`` used on the hot path.
    """
    n_rows, n_cols = side.valid_sort.shape
    shape = (n_rows, n_cols)
    flat = (n_rows * n_cols,)
    count_dtype = np.int16 if n_cols < 32767 else np.int32

    # The partner's validity seen through *our* sort order -- the one
    # irreducible permutation per (panel, pair).
    partner_valid = _buf(f"pv{slot}", flat, bool)
    np.take(partner.valid_orig.reshape(-1), side.order_flat, mode="clip", out=partner_valid)

    removed = _buf(f"rem{slot}", shape, bool)
    np.logical_not(partner_valid, out=removed.reshape(-1))
    np.logical_and(removed, side.valid_sort, out=removed)

    joint_valid = _buf(f"jv{slot}", flat, bool)
    np.logical_and(partner_valid, side.valid_sort.reshape(-1), out=joint_valid)

    cum = _buf(f"cum{slot}", shape, count_dtype)
    np.cumsum(removed, axis=1, dtype=count_dtype, out=cum)
    excl = _buf(f"excl{slot}", shape, count_dtype)
    np.subtract(cum, removed, out=excl)

    corr = _buf(f"corr{slot}", shape, np.float32)
    np.copyto(corr, cum)
    np.add(corr, excl, out=corr)
    np.multiply(corr, _HALF, out=corr)

    if side.grp_start is not None:
        keyed = np.flatnonzero(side.tie_row)
        if keyed.size:
            # Tied periods need the group-boundary form instead.  Index into the
            # full flat arrays (no row subsetting, no copies) and stay in int32.
            idx_dtype = np.int32 if flat[0] < np.int32(2**31 - 1) else np.int64
            base = keyed.astype(idx_dtype) * np.dtype(idx_dtype).type(n_cols)
            idx_start = (side.grp_start[keyed].astype(idx_dtype) + base[:, None]).reshape(-1)
            idx_end = (side.grp_end[keyed].astype(idx_dtype) + base[:, None]).reshape(-1)
            grouped = np.take(excl.reshape(-1), idx_start, mode="clip") + np.take(
                cum.reshape(-1), idx_end, mode="clip"
            )
            grouped = grouped.astype(np.float32, copy=False)
            grouped *= _HALF
            corr[keyed] = grouped.reshape(keyed.size, n_cols)

    ranks = _buf(f"rank{slot}", shape, np.float32)
    np.subtract(side.rank_sort, corr, out=ranks)
    return ranks, joint_valid


def _reduce(ra: np.ndarray, rb: np.ndarray, n_valid: np.ndarray, usable):
    """Masked mean |Pearson| over rows, on already-aligned (rows, cols) arrays."""
    shape = ra.shape
    n = n_valid.astype(np.float64)
    np.maximum(n, 1.0, out=n)  # empty cross-sections divide harmlessly, then drop

    prod = _buf("prod", shape, np.float32)
    sum_a = ra.sum(axis=1, dtype=np.float64)
    sum_b = rb.sum(axis=1, dtype=np.float64)
    np.multiply(ra, rb, out=prod)
    cov = prod.sum(axis=1, dtype=np.float64)
    np.multiply(ra, ra, out=prod)
    var_a = prod.sum(axis=1, dtype=np.float64)
    np.multiply(rb, rb, out=prod)
    var_b = prod.sum(axis=1, dtype=np.float64)

    cov -= sum_a * sum_b / n
    var_a -= sum_a * sum_a / n
    var_b -= sum_b * sum_b / n
    np.maximum(var_a, 0.0, out=var_a)
    np.maximum(var_b, 0.0, out=var_b)

    den = np.sqrt(var_a * var_b)
    corr = np.divide(cov, den, out=np.zeros_like(cov), where=den > 1e-12)
    return float(np.abs(corr[usable]).mean())


def pair_dependence(a: Prepared, b: Prepared) -> tuple[float, int]:
    """Mean |Spearman| over periods; also returns how many periods were corrected."""
    shape = a.valid_orig.shape
    flat = (a.valid_orig.size,)
    valid_joint = _buf("vj", shape, bool)
    np.logical_and(a.valid_orig, b.valid_orig, out=valid_joint)
    counts = valid_joint.sum(axis=1)
    usable = counts >= 3
    if not usable.any():
        return 0.0, 0

    repaired = 0
    if APPROXIMATE:
        ra = _buf("ra", shape, np.float32)
        rb = _buf("rb", shape, np.float32)
        np.multiply(a.rank_orig, valid_joint, out=ra)
        np.multiply(b.rank_orig, valid_joint, out=rb)
        return _reduce(ra, rb, counts, usable), 0

    # A period only needs correction when something valid for this panel is
    # missing from the partner; otherwise the cached ranks already *are* the
    # joint-subset ranks.
    extra_a = _buf("xa", shape, bool)
    extra_b = _buf("xb", shape, bool)
    np.logical_and(a.valid_orig, ~b.valid_orig, out=extra_a)
    np.logical_and(b.valid_orig, ~a.valid_orig, out=extra_b)
    need_a = bool(extra_a.any())
    need_b = bool(extra_b.any())
    repaired = int(np.count_nonzero((extra_a | extra_b).any(axis=1) & usable))

    if not need_a and not need_b:
        # Rare but free: identical NaN masks, cached ranks are already joint.
        ra = _buf("ra", shape, np.float32)
        rb = _buf("rb", shape, np.float32)
        np.multiply(a.rank_orig, valid_joint, out=ra)
        np.multiply(b.rank_orig, valid_joint, out=rb)
        return _reduce(ra, rb, counts, usable), repaired

    # Accumulate in whichever space costs the fewest moves.  Pearson is
    # invariant to a permutation applied to both operands, so we keep the
    # corrected panel where it already is and remap only the other one.
    if need_a:
        side, partner = a, b
    else:
        side, partner = b, a
    ranks_side, joint_valid = _joint_ranks_sorted(side, partner, "0")

    other = _buf("other", flat, np.float32)
    if need_a and need_b:
        ranks_partner, _ = _joint_ranks_sorted(partner, side, "1")
        comp = _buf("comp", flat, np.int32)
        np.take(partner.inv_flat, side.order_flat, mode="clip", out=comp)
        np.take(ranks_partner.reshape(-1), comp, mode="clip", out=other)
    else:
        np.take(partner.rank_orig.reshape(-1), side.order_flat, mode="clip", out=other)

    ra_out = _buf("ra", shape, np.float32)
    rb_out = _buf("rb", shape, np.float32)
    if side is a:
        ra = np.multiply(ranks_side, joint_valid.reshape(shape), out=ra_out)
        rb = np.multiply(other.reshape(shape), joint_valid.reshape(shape), out=rb_out)
    else:
        rb = np.multiply(ranks_side, joint_valid.reshape(shape), out=rb_out)
        ra = np.multiply(other.reshape(shape), joint_valid.reshape(shape), out=ra_out)
    return _reduce(ra, rb, counts, usable), repaired


def fast_spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Vectorized equivalent of ``SpearmanDependenceMetric.compute``.

    Exact, but re-ranks both panels (no cross-call caching) -- use
    :func:`prepared_dependence` inside tight loops instead.
    """
    if a.shape != b.shape:
        raise ValueError(f"Signal shapes must match: {a.shape} vs {b.shape}")
    return pair_dependence(prepare(a), prepare(b))[0]


# ---------------------------------------------------------------------------
# Rank cache keyed on the Factor object
# ---------------------------------------------------------------------------


def prepared_of(factor) -> Prepared:
    """Return (and memoize) the prepared panel for one library factor."""
    cached = getattr(factor, "_fast_prepared", None)
    if cached is not None and cached[0] is factor.signals:
        return cached[1]
    prepared = prepare(factor.signals)
    factor._fast_prepared = (factor.signals, prepared)
    return prepared


def prepared_dependence(candidate: Prepared, factor) -> float:
    """Correlation between a prepared candidate and a cached library factor."""
    return pair_dependence(candidate, prepared_of(factor))[0]


# ---------------------------------------------------------------------------
# Patch application
# ---------------------------------------------------------------------------

import click


def apply() -> bool:
    """Monkeypatch the hot paths. Returns True when patches were installed."""
    try:
        from factorminer.architecture.geometry import CandidateGeometry, LibraryGeometry
        from factorminer.core.factor_library import FactorLibrary
        from factorminer.domain import dependence
    except ImportError:
        return False
    click.echo("===Monkeypatch the hot paths===")
    dependence.SpearmanDependenceMetric.compute = lambda self, a, b: fast_spearman(a, b)
    FactorLibrary.compute_correlation = lambda self, a, b: fast_spearman(a, b)

    if not getattr(LibraryGeometry, "_fast_patched", False):
        original = LibraryGeometry.candidate_geometry

        def candidate_geometry(self, signals, *, crowding_novelty_modulation=None):
            if self.library.size == 0:
                return original(
                    self,
                    signals,
                    crowding_novelty_modulation=crowding_novelty_modulation,
                )

            candidate = prepare(signals)
            threshold = self.library.correlation_threshold
            max_corr = 0.0
            ids: list[int] = []
            names: list[str] = []

            for factor in self.library.list_factors():
                if factor.signals is None:
                    continue
                corr = prepared_dependence(candidate, factor)
                if corr > max_corr:
                    max_corr = corr
                if corr >= threshold:
                    ids.append(int(factor.id))
                    names.append(str(factor.name))

            novelty = max(0.0, 1.0 - max_corr)
            if crowding_novelty_modulation is not None:
                novelty = float(max(0.0, min(1.0, novelty * float(crowding_novelty_modulation))))
            return CandidateGeometry(
                max_correlation=max_corr,
                max_dependence=max_corr,
                correlated_factor_ids=ids,
                correlated_factor_names=names,
                novelty_score=novelty,
                library_size=self.library.size,
                dependence_metric=self.library.dependence_metric.name,
            )

        LibraryGeometry.candidate_geometry = candidate_geometry
        LibraryGeometry._fast_patched = True

    return True


APPLIED = apply()
