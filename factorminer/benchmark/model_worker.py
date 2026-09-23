"""Run optional native-model selections in an isolated worker process.

Native libraries such as XGBoost can abort the interpreter (for example an
OpenMP runtime conflict) rather than raise. Running them in a child process
turns a crash, a missing dependency, or a hang into a recorded
:class:`ModelOutcome`, so the benchmark continues and reports that selection
as unavailable instead of dying or reporting partial results as complete.

The child runs ``python -m factorminer.benchmark.model_worker <target> <in> <out>``
where ``target`` is ``"module:function"`` taking ``(factor_signals, returns)``
and returning ``[(factor_id, score), ...]``.
"""

from __future__ import annotations

import importlib
import json
import os
import signal
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

XGBOOST_SELECTION = "factorminer.benchmark.model_worker:xgboost_selection"


@dataclass(frozen=True)
class ModelOutcome:
    """Result of one isolated model selection."""

    name: str
    status: str  # "ok" | "error" | "crashed" | "timeout"
    ranking: list[tuple[int, float]] = field(default_factory=list)
    cause: str = ""
    exit_code: int | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def unavailable_record(self) -> dict[str, Any]:
        """Selection entry for reports: explicit unavailability, never a zero score."""
        return {"status": "unavailable", "failure": self.status, "cause": self.cause,
                "exit_code": self.exit_code, "factor_count": 0}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def xgboost_selection(
    factor_signals: dict[int, np.ndarray], returns: np.ndarray
) -> list[tuple[int, float]]:
    """XGBoost gain-importance ranking (runs inside the worker)."""
    from factorminer.evaluation.selection import FactorSelector

    return FactorSelector().xgboost_selection(factor_signals, returns)


def _describe_exit(code: int) -> str:
    if code < 0:
        try:
            return f"terminated by signal {signal.Signals(-code).name}"
        except ValueError:
            return f"terminated by signal {-code}"
    return f"exited with status {code}"


def run_isolated_selection(
    name: str,
    factor_signals: dict[int, np.ndarray],
    returns: np.ndarray,
    *,
    target: str = XGBOOST_SELECTION,
    timeout_s: float = 900.0,
) -> ModelOutcome:
    """Run ``target`` in a child process and classify how it ended."""
    with tempfile.TemporaryDirectory(prefix="factorminer-model-") as tmp:
        inputs = Path(tmp) / "inputs.npz"
        output = Path(tmp) / "ranking.json"
        arrays: dict[str, Any] = {"returns": np.asarray(returns)}
        arrays.update(
            {f"signal_{int(fid)}": np.asarray(panel) for fid, panel in factor_signals.items()}
        )
        np.savez(inputs, **arrays)
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "factorminer.benchmark.model_worker",
                 target, str(inputs), str(output)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired:
            return ModelOutcome(name, "timeout", cause=f"no result within {timeout_s:.0f}s")

        if completed.returncode == 0 and output.exists():
            payload = json.loads(output.read_text())
            ranking = [(int(fid), float(score)) for fid, score in payload["ranking"]]
            return ModelOutcome(name, "ok", ranking=ranking, exit_code=0)

        stderr = (completed.stderr or "").strip().splitlines()
        detail = stderr[-1] if stderr else ""
        if completed.returncode < 0:
            status, cause = "crashed", _describe_exit(completed.returncode)
        else:
            status, cause = "error", _describe_exit(completed.returncode)
        return ModelOutcome(
            name, status, cause=f"{cause}: {detail}" if detail else cause,
            exit_code=completed.returncode,
        )


def _load_target(target: str) -> Any:
    module_name, _, function_name = target.partition(":")
    if not module_name or not function_name:
        raise ValueError(f"target must be 'module:function', got {target!r}")
    return getattr(importlib.import_module(module_name), function_name)


def _worker_main(argv: list[str]) -> int:
    target, inputs, output = argv
    with np.load(inputs) as data:
        returns = data["returns"]
        signals = {
            int(key.removeprefix("signal_")): data[key]
            for key in data.files
            if key.startswith("signal_")
        }
    ranking = _load_target(target)(signals, returns)
    Path(output).write_text(
        json.dumps({"ranking": [[int(fid), float(score)] for fid, score in ranking]})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_worker_main(sys.argv[1:]))
