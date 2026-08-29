from __future__ import annotations

from typing import Any, Iterable

import numpy as np

try:
    from scipy.stats import ks_2samp
except ImportError:  # pragma: no cover - scipy is installed with the lab stack
    ks_2samp = None


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect shape, quantile and location drift.

    Mean-only checks miss important cases such as a wider distribution with the
    same mean.  KS significance handles overall shape, while robust quantiles
    handle small/constant samples where a p-value has little power.
    """
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)
    cur = cur[np.isfinite(cur)]
    base = base[np.isfinite(base)]
    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "ks", "reason": "empty_input"}
    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))
    base_q = np.quantile(base, [0.10, 0.25, 0.50, 0.75, 0.90])
    cur_q = np.quantile(cur, [0.10, 0.25, 0.50, 0.75, 0.90])
    base_mad = float(np.median(np.abs(base - np.median(base))))
    base_iqr = float(base_q[3] - base_q[1])
    # Relative floor prevents a tiny numerical baseline from producing an
    # infinite ratio while still making a meaningful constant-baseline shift
    # visible.
    scale = max(base_iqr, 1.4826 * base_mad, abs(base_mean) * 0.01, 1e-12)
    quantile_score = float(np.median(np.abs(cur_q - base_q)) / scale)
    location_score = float(abs(cur_mean - base_mean) / scale)
    if abs(base_mean) <= scale:
        ratio_score = float("inf") if abs(cur_mean - base_mean) > scale else 1.0
    elif abs(cur_mean) <= scale:
        ratio_score = float("inf")
    else:
        ratio_score = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean))
    combined = np.sort(np.concatenate([cur, base]))
    cur_cdf = np.searchsorted(np.sort(cur), combined, side="right") / cur.size
    base_cdf = np.searchsorted(np.sort(base), combined, side="right") / base.size
    ks_score = float(np.max(np.abs(cur_cdf - base_cdf)))
    if ks_2samp is not None:
        ks_pvalue = float(ks_2samp(cur, base, alternative="two-sided", mode="auto").pvalue)
    else:
        ks_pvalue = 0.0 if ks_score >= 0.2 else 1.0
    ks_anomaly = ks_score >= 0.2 and ks_pvalue < 0.05
    is_anomaly = (
        ratio_score >= ratio_threshold
        or ks_anomaly
        or quantile_score >= 1.5
        or (location_score >= 3.0 and min(cur.size, base.size) >= 5)
    )
    combined_score = max(ks_score, quantile_score, location_score)
    return {
        "is_anomaly": bool(is_anomaly),
        "score": float(combined_score),
        "method": "ks+quantiles+mean_ratio",
        "reason": (
            f"ks={ks_score:.3f} (p={ks_pvalue:.4f}); quantile_shift={quantile_score:.3f}; "
            f"location_shift={location_score:.3f}; baseline_mean={base_mean:.3f}; "
            f"current_mean={cur_mean:.3f}; mean_ratio={ratio_score:.3f}"
        ),
    }
