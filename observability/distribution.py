from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect both shape and location drift with a two-sample KS statistic."""
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)
    cur = cur[np.isfinite(cur)]
    base = base[np.isfinite(base)]
    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "ks", "reason": "empty_input"}
    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))
    if base_mean == 0:
        score = float("inf") if cur_mean != 0 else 1.0
    else:
        score = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean)) if cur_mean != 0 else float("inf")
    combined = np.sort(np.concatenate([cur, base]))
    cur_cdf = np.searchsorted(np.sort(cur), combined, side="right") / cur.size
    base_cdf = np.searchsorted(np.sort(base), combined, side="right") / base.size
    ks_score = float(np.max(np.abs(cur_cdf - base_cdf)))
    # A KS threshold of .2 is useful for the small batches in this lab.  Keep
    # the ratio guard for extreme shifts where the samples are tiny.
    is_anomaly = ks_score >= 0.2 or score >= ratio_threshold
    return {
        "is_anomaly": bool(is_anomaly),
        "score": float(ks_score),
        "method": "ks+mean_ratio",
        "reason": (
            f"ks={ks_score:.3f}; baseline_mean={base_mean:.3f}; "
            f"current_mean={cur_mean:.3f}; mean_ratio={score:.3f}"
        ),
    }
