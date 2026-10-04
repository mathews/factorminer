"""Re-run Phase-2 validation on an existing factor library.

Loads a mined factor library (JSON + NPZ signal cache), rebuilds the canonical
runtime dataset from the same market data, and runs the Helix Phase-2
validation stack (causal + regime + capacity + significance) over every factor.

The earlier version of this script hand-rolled the arrays with
``load_market_data(...).to_numpy()`` and ``compute_returns(...).to_numpy()``,
which produce flat ``(N, F)`` arrays (object dtype, datetime column included),
not the ``(M, T)`` panels the Phase-2 components require. That surfaced as:
  * ``unsupported operand type(s) for +: 'Timestamp' and 'Timestamp'`` (regime)
  * ``capacity config provided without volume data`` (capacity)
  * ``'SignificanceConfig' object has no attribute 'seed'`` (bootstrap)

All three are fixed by using the canonical builders used by the CLI:
``load_runtime_dataset`` for the panels and ``_build_phase2_runtime_configs``
for the runtime Phase-2 config objects (which, unlike the ``utils.config``
dataclasses, carry every field the evaluators read -- e.g. ``seed``).

A fourth, quieter bug: the library was mined on CSI500 (its signal panels are
(500, 2429)), so it must be validated against ``500_panel_f.parquet``, not the
1000-asset panel. And capacity must be given a RAW dollar-volume panel --
``preprocess`` cross-sectionally z-scores volume/amount, so the tensor slice
``_extract_capacity_volume`` returns is standardised, not dollars.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

import numpy as np

from factorminer.application.helix_validation import HelixValidationService
from factorminer.application.mining_budget import EvaluationResult
from factorminer.application.runtime_context import build_run_context
from factorminer.cli.app import _build_phase2_runtime_configs
from factorminer.core.helix_loop import HelixLoop
from factorminer.core.library_io import load_library
from factorminer.data.loader import load_market_data
from factorminer.evaluation.runtime import load_runtime_dataset
from factorminer.utils.config import load_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

LIBRARY_PATH = "/data/fuyao_data/output10-perhaps-wrong-cal/factor_library"
CONFIG_PATH = "/data/fuyao_data/factorminer/default_orcha.yaml"
# The library was mined on CSI500 (500 assets x 2429 periods); its saved
# signal panels are (500, 2429). Point at the matching panel -- validating
# them against the 1000-asset panel would misalign assets and crash.
DATA_PATH = "/data/local_data/hithink-finance/500_panel_f.parquet"
UNIVERSE = "CSI500"
OUTPUT_DIR = Path("/data/fuyao_data/output10-perhaps-wrong-cal")

# Dumping 500 factors x (M, T) float panels into JSON is impractical
# (gigabytes). Signal panels go to a companion .npz; the JSON keeps metadata.
EXPORT_SIGNALS_TO_NPZ = True

# --- Sign alignment -------------------------------------------------------
# Mining admits on |ICIR| (metrics.compute_ic_paper_icir = abs(mean/std)), so a
# factor with IC < 0 is admitted because you would simply trade it in reverse.
# The capacity gate, however, compares *signed* net_icir >= threshold, so every
# negative-IC factor looks like a failure regardless of quality. Flipping the
# signal of negative-IC factors puts both gates on the same (tradeable) footing.
SIGN_ALIGN = True

# Override net_icir_threshold without editing the YAML (None = use the config).
NET_ICIR_THRESHOLD_OVERRIDE: float | None = None

# The significance stage looks its trial family up in the ledger by
# (campaign_id, dataset_id, target_name). campaign_id is derived from
# {dataset_id, config, loop_type}, so a Helix validation of a library that was
# mined by the Ralph loop never matches the stored campaign. "*" matches any
# campaign and keeps dataset_id/target_name exact (the real scope keys).
LEDGER_CAMPAIGN_WILDCARD = True


# ---------------------------------------------------------------------------
# 1. Factor library -> EvaluationResult candidates
# ---------------------------------------------------------------------------

library = load_library(LIBRARY_PATH)

candidates: list[EvaluationResult] = []
sign_flipped: dict[str, bool] = {}
for factor in library.list_factors():
    signals = factor.signals  # (M, T) panel from the NPZ cache
    ic_mean = factor.ic_mean
    flipped = False
    if SIGN_ALIGN and signals is not None and ic_mean < 0:
        signals = -signals
        ic_mean = -ic_mean
        flipped = True
    sign_flipped[factor.name] = flipped
    candidates.append(
        EvaluationResult(
            factor_name=factor.name,
            formula=factor.formula,
            signals=signals,
            ic_mean=ic_mean,
            icir=factor.icir,
            admitted=True,
        )
    )

print(f"Loaded {len(candidates)} candidate factors")
with_signals = sum(1 for c in candidates if c.signals is not None)
print(f"  {with_signals} carry a signal panel, {len(candidates) - with_signals} have none")
if with_signals:
    sample = next(c for c in candidates if c.signals is not None)
    print(f"  sample signal panel shape: {sample.signals.shape}")
if SIGN_ALIGN:
    n_flipped = sum(sign_flipped.values())
    print(f"  sign-aligned {n_flipped} negative-IC factors (now tradeable direction)")


# ---------------------------------------------------------------------------
# 2. Canonical runtime dataset  (fixes the Timestamp / volume errors)
# ---------------------------------------------------------------------------

cfg = load_config(CONFIG_PATH)

raw_df = load_market_data(DATA_PATH, universe=UNIVERSE)
dataset = load_runtime_dataset(raw_df, cfg)

print(
    f"Dataset: data_tensor={dataset.data_tensor.shape} "
    f"returns={dataset.returns.shape} "
    f"(M={len(dataset.asset_ids)}, T={len(dataset.timestamps)})"
)

# Guard: these must be 2-D/3-D float panels, never object arrays.
assert dataset.returns.ndim == 2, f"returns must be (M, T), got {dataset.returns.shape}"
assert np.issubdtype(dataset.returns.dtype, np.floating), dataset.returns.dtype
assert dataset.data_tensor.ndim == 3, dataset.data_tensor.shape

# Guard: signal panels must align with the returns panel, else every
# per-period IC silently compares the wrong assets.
_expected = dataset.returns.shape
for _c in candidates:
    if _c.signals is not None and _c.signals.shape != _expected:
        raise ValueError(
            f"signal shape {_c.signals.shape} for '{_c.factor_name}' does not "
            f"match the returns panel {_expected}; check DATA_PATH/UNIVERSE "
            f"against the universe the library was mined on"
        )


# ---------------------------------------------------------------------------
# 3. Phase-2 runtime configs  (fixes the SignificanceConfig.seed error)
# ---------------------------------------------------------------------------

phase2_configs = _build_phase2_runtime_configs(cfg)

if NET_ICIR_THRESHOLD_OVERRIDE is not None and phase2_configs["capacity_config"] is not None:
    phase2_configs["capacity_config"].net_icir_threshold = NET_ICIR_THRESHOLD_OVERRIDE
if phase2_configs["capacity_config"] is not None:
    print(
        f"Capacity: capital={phase2_configs['capacity_config'].base_capital_usd:.0f} "
        f"bars_per_day={phase2_configs['capacity_config'].bars_per_day:.0f} "
        f"net_icir_threshold={phase2_configs['capacity_config'].net_icir_threshold}"
    )


# Capacity needs a RAW dollar-volume panel. Do NOT use
# _extract_capacity_volume(dataset.data_tensor): preprocess() cross-sectionally
# z-scores volume/amount, so that panel holds standardised values, not dollars.
# The square-root impact model divides capital by it as if it were dollar
# turnover, so z-scores (median ~ -0.34) saturate participation at the 10%
# limit and inflate impact ~2.7x -- which rejects every factor.
def _raw_dollar_volume(raw_df, dataset) -> np.ndarray | None:
    """Pivot raw amount (fallback volume) onto the dataset's (M, T) axes."""
    import pandas as pd

    for col in ("amount", "volume"):
        if col not in raw_df.columns:
            continue
        panel = (
            raw_df.pivot(index="asset_id", columns="datetime", values=col)
            .reindex(index=dataset.asset_ids, columns=pd.to_datetime(dataset.timestamps))
            .to_numpy(dtype=np.float64)
        )
        if np.any(np.isfinite(panel)):
            return panel
    return None


volume = _raw_dollar_volume(raw_df, dataset) if cfg.phase2.capacity.enabled else None
if cfg.phase2.capacity.enabled and volume is None:
    print("WARNING: capacity enabled but no raw dollar-volume panel found")
elif volume is not None:
    print(
        f"Capacity volume (raw dollars): shape={volume.shape} "
        f"median={np.nanmedian(volume):.3e}"
    )


# ---------------------------------------------------------------------------
# 4. Build the loop and run Phase-2 validation
# ---------------------------------------------------------------------------

# The run context carries target_panels/target_horizons. Without it the
# dataset contract falls back to target_names=["paper"], the dataset_scope
# hash differs from the mining run's, and the significance stage cannot find
# its trial family in the ledger ("no trial observations match ...").
run_context = build_run_context(cfg, output_dir=str(OUTPUT_DIR), dataset=dataset)
print(f"Run context target_panels: {list(run_context.target_panels or {})}")

loop = HelixLoop(
    config=cfg,
    data_tensor=dataset.data_tensor,
    returns=dataset.returns,
    llm_provider=None,
    causal_config=phase2_configs["causal_config"],
    regime_config=phase2_configs["regime_config"],
    capacity_config=phase2_configs["capacity_config"],
    significance_config=phase2_configs["significance_config"],
    volume=volume,
    run_context=run_context,
)

print(f"Active Phase-2 features: {', '.join(loop._phase2_features()) or 'none'}")
for label, component in (
    ("causal validator", loop._causal_validator),
    ("regime evaluator", loop._regime_evaluator),
    ("capacity estimator", loop._capacity_estimator),
    ("bootstrap tester", loop._bootstrap_tester),
    ("FDR controller", loop._fdr_controller),
):
    print(f"  {label:<20} {'OK' if component is not None else 'MISSING'}")

if LEDGER_CAMPAIGN_WILDCARD:
    print(f"Ledger campaign: {loop.trial_ledger.campaign_id[:16]}... -> '*'")
    loop.trial_ledger.campaign_id = "*"
    try:
        _fam = loop.trial_ledger.build_inference_family(
            dataset_id=loop.trial_dataset_id,
            target_name=loop.dataset_contract.default_target,
            periods=int(loop.returns.shape[1]),
            estimate_effective=False,
        )
        print(f"  trial family resolved: {_fam.raw_trial_count} canonical trials")
    except Exception as exc:
        print(f"  WARNING: trial family unresolved ({exc})")

validator = HelixValidationService(loop)
result = candidates.copy()
rejected_count = validator.validate(result, candidates)

print(f"Phase 2 rejected {rejected_count}/{len(candidates)} factors")
print(f"  admitted after validation: {sum(1 for r in result if r.admitted)}")


# ---------------------------------------------------------------------------
# 5. Save results
# ---------------------------------------------------------------------------


def _result_to_dict(r: EvaluationResult) -> dict:
    """Dataclass -> JSON-safe dict; the signal panel is exported separately."""
    d = asdict(r)
    signals = d.get("signals")
    if signals is not None:
        d["signals_shape"] = list(np.shape(signals))
        d["signals"] = None
    return d


def _json_safe(obj):
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Tag outputs by threshold so runs at different thresholds don't overwrite
# each other (validation_signals.npz is 1.9 GB; share it across runs).
_thr = (
    NET_ICIR_THRESHOLD_OVERRIDE
    if NET_ICIR_THRESHOLD_OVERRIDE is not None
    else (phase2_configs["capacity_config"].net_icir_threshold
          if phase2_configs["capacity_config"] is not None else None)
)
_tag = f"thr{_thr}" if _thr is not None else "thr_default"

json_path = OUTPUT_DIR / f"validation_results_{_tag}.json"
with open(json_path, "w") as f:
    json.dump(
        _json_safe([_result_to_dict(r) for r in result]),
        f,
        indent=2,
        ensure_ascii=False,
    )
print(f"Saved {len(result)} results to {json_path}")

if EXPORT_SIGNALS_TO_NPZ:
    signal_arrays = {
        f"factor_{i}": r.signals for i, r in enumerate(result) if r.signals is not None
    }
    if signal_arrays:
        npz_path = OUTPUT_DIR / "validation_signals.npz"
        np.savez_compressed(npz_path, **signal_arrays)
        print(f"Saved {len(signal_arrays)} signal panels to {npz_path}")

rejected = [r for r in result if not r.admitted]
if rejected:
    summary_path = OUTPUT_DIR / f"validation_rejections_{_tag}.json"
    with open(summary_path, "w") as f:
        json.dump(
            [
                {
                    "factor_name": r.factor_name,
                    "formula": r.formula,
                    "sign_flipped": sign_flipped.get(r.factor_name, False),
                    "reason": r.rejection_reason,
                }
                for r in rejected
            ],
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"Saved {len(rejected)} rejection reasons to {summary_path}")
