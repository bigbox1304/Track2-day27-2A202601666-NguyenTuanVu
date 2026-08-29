"""Distribution shift and statistical drift detection."""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect location and shape drift using KS and robust quantile distance.

    The KS threshold is calculated from both sample sizes, which avoids making
    small samples look healthy merely because an asymptotic p-value has low
    power. Quantile distance and median/IQR effect size then provide a robust
    signal for same-mean shape changes.
    """
    current = np.asarray(list(current_values), dtype=float)
    baseline = np.asarray(list(baseline_values), dtype=float)
    current = current[np.isfinite(current)]
    baseline = baseline[np.isfinite(baseline)]
    if current.size == 0 or baseline.size == 0:
        return {
            "is_anomaly": False,
            "score": 0.0,
            "method": "ks_2sample",
            "reason": "empty_or_nonfinite_input",
        }

    current_mean = float(np.mean(current))
    baseline_mean = float(np.mean(baseline))

    current_sorted = np.sort(current)
    baseline_sorted = np.sort(baseline)
    merged = np.sort(np.concatenate([current, baseline]))
    current_cdf = np.searchsorted(current_sorted, merged, side="right") / current.size
    baseline_cdf = np.searchsorted(baseline_sorted, merged, side="right") / baseline.size
    ks_stat = float(np.max(np.abs(current_cdf - baseline_cdf)))

    # Critical value for approximately alpha=0.01, capped to avoid an
    # excessively permissive threshold for very small batches.
    ks_critical = float(
        1.63 * np.sqrt((current.size + baseline.size) / (current.size * baseline.size))
    )
    effective_threshold = min(0.75, ks_critical)
    ks_normalized_score = (
        ks_stat / effective_threshold if effective_threshold > 0 else 0.0
    )

    baseline_median = float(np.median(baseline))
    baseline_q25, baseline_q75 = np.percentile(baseline, [25, 75])
    baseline_iqr = float(baseline_q75 - baseline_q25)
    scale = max(
        baseline_iqr,
        float(np.std(baseline)),
        abs(baseline_median) * 0.05,
        1e-9,
    )
    location_score = abs(float(np.median(current)) - baseline_median) / scale

    quantiles = np.linspace(0.0, 1.0, 101)
    quantile_shift = float(
        np.mean(np.abs(np.quantile(current, quantiles) - np.quantile(baseline, quantiles)))
        / scale
    )

    combined_score = max(ks_normalized_score, location_score / ratio_threshold)
    shape_shifted = ks_stat >= effective_threshold and quantile_shift >= 1.0
    location_shifted = location_score >= ratio_threshold
    is_anomaly = bool(shape_shifted or location_shifted)
    return {
        "is_anomaly": is_anomaly,
        "score": float(combined_score),
        "method": "ks_2sample+robust_location",
        "reason": (
            f"ks={ks_stat:.4f}, ks_threshold={effective_threshold:.4f}, "
            f"location_score={location_score:.4f}, quantile_shift={quantile_shift:.4f}, "
            f"baseline_mean={baseline_mean:.3f}, current_mean={current_mean:.3f}"
        ),
    }
