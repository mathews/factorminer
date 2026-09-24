"""The fast admission gate must retain the paper's pairwise rank semantics."""

import numpy as np
import pytest
from scipy.stats import rankdata

from factorminer.domain.dependence import SpearmanDependenceMetric


def _reference(a: np.ndarray, b: np.ndarray) -> float:
    scores = []
    for period in range(a.shape[1]):
        valid = ~(np.isnan(a[:, period]) | np.isnan(b[:, period]))
        if valid.sum() < 3:
            continue
        x = rankdata(a[valid, period])
        y = rankdata(b[valid, period])
        x -= x.mean()
        y -= y.mean()
        denominator = np.sqrt(np.sum(x * x) * np.sum(y * y))
        scores.append(abs(np.sum(x * y) / denominator) if denominator >= 1e-12 else 0.0)
    return float(np.mean(scores)) if scores else 0.0


def test_spearman_matches_joint_mask_reference_across_chunks():
    rng = np.random.default_rng(8)
    a = np.round(rng.normal(size=(21, 530)), 1)
    b = np.round(rng.normal(size=(21, 530)), 1)
    a[rng.random(a.shape) < 0.13] = np.nan
    b[rng.random(b.shape) < 0.19] = np.nan
    a[:, 257] = 1.0
    a[:, 258] = np.nan
    b[:, 259] = np.nan
    a[:3, 259] = [1.0, 2.0, 3.0]
    b[:3, 259] = [3.0, 2.0, 1.0]

    got = SpearmanDependenceMetric().compute(a, b)
    assert got == pytest.approx(_reference(a, b), abs=1e-14)
    assert got == pytest.approx(SpearmanDependenceMetric().compute(b, a), abs=1e-14)


def test_spearman_rejects_mismatched_shapes():
    with pytest.raises(ValueError, match="shapes"):
        SpearmanDependenceMetric().compute(np.ones((3, 4)), np.ones((4, 3)))
