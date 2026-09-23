"""Worker targets used by model-worker isolation tests."""

from __future__ import annotations

import os
import time


def rank_by_id(factor_signals, returns):
    return [(fid, float(fid)) for fid in sorted(factor_signals, reverse=True)]


def raise_error(factor_signals, returns):
    raise RuntimeError("model rejected the panel")


def abort(factor_signals, returns):
    os.abort()


def hang(factor_signals, returns):
    time.sleep(60)
    return []


def nonfinite(factor_signals, returns):
    return [(next(iter(factor_signals)), float("nan"))]
