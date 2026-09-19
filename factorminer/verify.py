"""Correctness + speed check for fast_dependence.py.

Run with the factorminer venv interpreter:

    /data/local_data/projects/factorminer/factorminer/.venv/bin/python verify.py

NOTE: this is a local validation harness only -- it must NOT be copied into
site-packages.  Only ``fast_dependence.py`` gets deployed (optionally renamed to
``sitecustomize.py``).  The loader below also locates the deployed copy.
"""

from __future__ import annotations

import importlib.util
import os
import site
import sys
import time

import numpy as np
from scipy.stats import rankdata

_MARKER = "FACTORMINER_FAST_SPEARMAN"


def _load_fast_dependence():
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.environ.get("FAST_DEPENDENCE_PATH", ""),
        os.path.join(here, "fast_dependence.py"),
    ]
    try:
        package_dirs = site.getsitepackages()
    except Exception:
        package_dirs = [p for p in sys.path if p.endswith("site-packages")]
    for pkg_dir in package_dirs:
        candidates.append(os.path.join(pkg_dir, "sitecustomize.py"))
        candidates.append(os.path.join(pkg_dir, "fast_dependence.py"))

    for path in candidates:
        if not path or not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                if _MARKER not in fh.read(4096):
                    continue
        except OSError:
            continue
        spec = importlib.util.spec_from_file_location("fd_under_test", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        print(f"loaded [{path}]")
        return module

    raise ImportError("fast_dependence.py not found; set FAST_DEPENDENCE_PATH=/path/to/file.py")


fd = _load_fast_dependence()


# ---------------------------------------------------------------------------
# Reference implementation (verbatim from factorminer/domain/dependence.py)
# ---------------------------------------------------------------------------


def _iter_valid_columns(a, b):
    for period in range(a.shape[1]):
        ca, cb = a[:, period], b[:, period]
        valid = ~(np.isnan(ca) | np.isnan(cb))
        if int(valid.sum()) < 3:
            continue
        yield ca[valid], cb[valid]


def _pearson_abs(x, y):
    xc = x - np.mean(x)
    yc = y - np.mean(y)
    denom = np.sqrt(np.sum(xc**2) * np.sum(yc**2))
    if float(denom) < 1e-12:
        return 0.0
    return float(abs(np.sum(xc * yc) / denom))


def reference_spearman(a, b):
    scores = [_pearson_abs(rankdata(ca), rankdata(cb)) for ca, cb in _iter_valid_columns(a, b)]
    return float(np.mean(scores)) if scores else 0.0


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------


def make_panel(m, t, rng, *, nan_frac=0.0, ties=False, warmup=0):
    x = rng.standard_normal((m, t))
    if ties:
        x = np.round(x * 2).astype(float)
    if warmup:
        x[:, :warmup] = np.nan
    if nan_frac:
        x[rng.random((m, t)) < nan_frac] = np.nan
    return x


def compare(name, a, b, repeats=3):
    """Compare reference vs fast with production-style cost accounting.

    In the real loop each candidate is prepared ONCE and then compared against
    every library factor, whose panels are cached across iterations.  So the
    honest unit costs are: one prepare per candidate + one pair_dependence per
    (candidate, library factor).
    """
    t0 = time.perf_counter()
    ref = reference_spearman(a, b)
    ref_ms = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    pa = fd.prepare(a)
    pb = fd.prepare(b)
    prepare_ms = (time.perf_counter() - t0) * 1e3

    t0 = time.perf_counter()
    for _ in range(repeats):
        new, repaired = fd.pair_dependence(pa, pb)
    pair_ms = (time.perf_counter() - t0) * 1e3 / repeats

    if repeats > 1:
        t0 = time.perf_counter()
        fd.pair_dependence(pa, pb)
        pair_cold_ms = (time.perf_counter() - t0) * 1e3
    else:
        pair_cold_ms = pair_ms

    periods = a.shape[1]
    print(
        f"  {name:<38} diff={abs(ref - new):.2e}  repaired={repaired:>5}/{periods}"
        f"  prep={prepare_ms / 2:6.1f}ms  pair={pair_ms:6.1f}ms"
        f"  ref={ref_ms:7.1f}ms ({ref_ms / max(pair_ms, 1e-9):5.1f}x)"
    )
    return abs(ref - new), ref_ms, pair_ms, prepare_ms / 2, repaired, periods


def main() -> None:
    print(f"fast_dependence patches applied: {fd.APPLIED}")
    rng = np.random.default_rng(42)
    m, t = 500, 2429

    print(f"\n[1] synthetic panels ({m} assets x {t} periods)")
    print("    target: diff == 0.00e+00 everywhere\n")

    a = make_panel(m, t, rng)
    b = make_panel(m, t, rng)
    compare("dense, no NaN", a, b)

    # Shared NaN pattern -> masks agree -> pure fast path, cache-friendly.
    a = make_panel(m, t, rng, warmup=20)
    b = make_panel(m, t, rng, warmup=20)
    compare("shared warm-up NaNs", a, b)

    scatter = rng.random((m, t)) < 0.02
    a = make_panel(m, t, rng)
    b = make_panel(m, t, rng)
    a[scatter] = np.nan
    b[scatter] = np.nan
    compare("2% scattered NaNs, SAME mask", a, b)

    # Differing NaN patterns -> exercises the exact repair branch.
    a = make_panel(m, t, rng, nan_frac=0.02)
    b = make_panel(m, t, rng, nan_frac=0.02)
    compare("2% scattered NaNs, DIFFERENT masks", a, b)

    a = make_panel(m, t, rng, nan_frac=0.05, ties=True)
    b = make_panel(m, t, rng, nan_frac=0.03, ties=True)
    compare("heavy ties + different NaN masks", a, b)

    a = make_panel(m, t, rng, nan_frac=0.10, ties=True)
    b = make_panel(m, t, rng, nan_frac=0.10)
    compare("ties only on one side", a, b)

    # -----------------------------------------------------------------
    cache = "/data/local_data/projects/factorminer/output3/checkpoint/library_signals.npz"
    print(f"\n[2] real factor panels from output3")
    if os.path.exists(cache):
        data = np.load(cache)
        keys = list(data.files)
        print(f"    {len(keys)} cached panels, shape {data[keys[0]].shape}\n")
        worst = 0.0
        worst_name = ""
        agg_pair = 0.0
        agg_prep = 0.0
        agg_ref = 0.0
        for i in range(min(6, len(keys) - 1)):
            d, rf, pf, pr, rep, npd = compare(
                f"{keys[i]} vs {keys[i + 1]}"[:38], data[keys[i]], data[keys[i + 1]]
            )
            agg_ref += rf
            agg_pair += pf
            agg_prep += pr
            if d > worst:
                worst, worst_name = d, f"{keys[i]} vs {keys[i + 1]}"
        print(f"\n    worst diff: {worst:.2e}  ({worst_name})")
        print(f"    mean prepare (per panel): {agg_prep / 6:.1f} ms")
        print(f"    mean pair time:           {agg_pair / 6:.1f} ms")
        print(f"    mean reference pair time: {agg_ref / 6:.1f} ms")
    ref_pair_s = (agg_ref / 6) / 1000.0
    pair_s = (agg_pair / 6) / 1000.0
    prep_s = (agg_prep / 6) / 1000.0
    print(
        "    projected iteration (40 cand, ~1.4 full-library scans each):\n"
        f"      {'L':>5} {'current':>11} {'patched':>11} {'speedup':>9}"
    )
    for L in (12, 32, 58, 100):
        n_pairs = 40 * 1.4 * L
        cur_s = n_pairs * ref_pair_s
        new_s = 40 * prep_s + n_pairs * pair_s
        print(
            f"      {L:>5} {cur_s / 60:>8.1f} m {new_s / 60:>8.1f} m "
            f"{cur_s / max(new_s, 1e-9):>8.1f}x"
        )
    # -----------------------------------------------------------------
    print("\n[3] sanity check against the observed run")
    print("    output3 iteration 7 measured 4549 s (76 min) at L=55.5;")
    print(
        f"    the 'current' column above gives {ref_pair_s * 40 * 1.4 * 55.5 / 60:.1f} min there."
    )


if __name__ == "__main__":
    main()
