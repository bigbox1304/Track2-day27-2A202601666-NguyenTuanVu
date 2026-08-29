"""Anomaly detection starter.

Z-score is deliberately the default baseline. Students should improve `auto`
mode for seasonality/outliers rather than deleting the simple implementation.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    """Robust detector using the modified z-score."""
    values = np.asarray(list(history), dtype=float)
    values = values[np.isfinite(values)]
    if values.size < 5:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    if mad == 0:
        different = not np.isclose(float(current), median)
        return {
            "is_anomaly": bool(different),
            "score": float("inf") if different else 0.0,
            "method": "mad",
            "reason": f"median={median:.3f}, mad=0; constant_baseline={different is False}",
        }
    modified_z = 0.6745 * abs(float(current) - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }


def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Detect a metric anomaly with explicit or context-aware baselines."""
    if not np.isfinite(float(current)):
        return {"is_anomaly": True, "score": float("inf"), "method": method, "reason": "current_value_not_finite"}
    if method == "mad":
        return mad_detector(current, history)
    if method == "zscore":
        return zscore_detector(current, history, threshold=threshold)
    if method == "auto":
        context = context or {}
        if context.get("known_event"):
            return {
                "is_anomaly": False,
                "score": 0.0,
                "method": "auto:event_suppressed",
                "reason": f"known_event={context['known_event']}",
            }

        selected_history = context.get("same_segment_history")
        baseline_name = "same_segment_history"
        selected_history = list(selected_history) if selected_history is not None else []
        if len(selected_history) < 3:
            selected_history = history
            baseline_name = "history"
        # Materialize once because callers often pass generators.
        selected_history = list(selected_history)
        clean = [float(v) for v in selected_history if np.isfinite(float(v))]
        if len(clean) >= 5:
            result = mad_detector(current, clean, threshold=max(3.5, threshold))
            result["method"] = "auto:mad"
        else:
            result = zscore_detector(current, clean, threshold=threshold)
            result["method"] = "auto:zscore"
        result["reason"] += f"; baseline={baseline_name}"
        if context.get("day_of_week") is not None:
            result["reason"] += f"; day_of_week={context['day_of_week']}"
        return result
    raise ValueError(f"Unsupported method: {method}")
