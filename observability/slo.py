from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")
    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }
    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate)
    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    policy: str = "starter",
) -> dict[str, Any]:
    """Apply a two-window policy so a short spike alone does not page."""
    if short_window_burn < 0 or long_window_burn < 0:
        raise ValueError("burn rates must be non-negative")
    # Canonical-style alert bands: page only when the fast window and the
    # confirming long window both show material budget consumption.
    page = bool(short_window_burn >= 14.0 and long_window_burn >= 5.0)
    warning = bool(short_window_burn >= 2.0 or long_window_burn >= 1.0)
    severity = "critical" if page else ("warning" if warning else "info")
    if page:
        reason = "sustained_fast_burn_both_windows_exceeded"
    elif short_window_burn >= 14.0:
        reason = "transient_short_window_spike_long_window_below_page_threshold"
    elif warning:
        reason = "budget_burn_requires_monitoring_but_not_paging"
    else:
        reason = "burn_within_normal_range"
    return {
        "page": page,
        "severity": severity,
        "reason": reason,
        "short_window_burn": short_window_burn,
        "long_window_burn": long_window_burn,
    }
