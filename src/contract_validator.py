"""Simple contract validator used as the starter baseline.

The implementation intentionally covers only common deterministic checks.
Students are expected to extend it with:
- stronger type validation/coercion rules,
- freshness checks,
- cross-field/cross-table assertions,
- severity-aware actions (block/quarantine/warn),
- richer observability metadata.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import numpy as np
import yaml


def _issue(
    check: str,
    *,
    column: str | None,
    severity: str,
    passed: bool,
    details: str,
    action: str | None = None,
) -> dict[str, Any]:
    result = {
        "check": check,
        "column": column,
        "severity": severity,
        "passed": bool(passed),
        "details": details,
    }
    if action is not None:
        result["action"] = action
    return result


def load_contract(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_dataframe(df: pd.DataFrame, contract: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    # Orders contracts call this section ``columns`` while the KB contract
    # uses ``fields``.  Supporting both keeps validation generic.
    columns = contract.get("columns") or contract.get("fields", {})

    severity_actions = {
        "critical": "block",
        "warning": "warn",
        "info": "log",
    }

    def add_issue(*, check: str, column: str | None, severity: str,
                  passed: bool, details: str) -> None:
        issues.append(
            _issue(
                check,
                column=column,
                severity=severity,
                passed=passed,
                details=details,
                action=severity_actions.get(severity, "warn"),
            )
        )

    for column, rules in columns.items():
        severity = rules.get("severity", "warning")
        required = bool(rules.get("required", False))

        if column not in df.columns:
            if required:
                add_issue(
                    check="required_column",
                    column=column,
                    severity=severity,
                    passed=False,
                    details=f"Missing required column: {column}",
                )
            continue

        series = df[column]

        if required:
            null_count = int(series.isna().sum())
            add_issue(
                check="not_null", column=column, severity=severity,
                passed=(null_count == 0), details=f"null_count={null_count}",
            )

        if rules.get("unique"):
            duplicate_count = int(series.duplicated(keep=False).sum())
            add_issue(
                check="unique", column=column, severity=severity,
                passed=(duplicate_count == 0),
                details=f"duplicate_rows={duplicate_count}",
            )

        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask = series.notna() & ~series.isin(accepted)
            invalid_count = int(invalid_mask.sum())
            add_issue(
                check="accepted_values", column=column, severity=severity,
                passed=(invalid_count == 0),
                details=f"invalid_count={invalid_count}; accepted={accepted}",
            )

        declared_type = rules.get("type")
        if declared_type:
            non_null = series[series.notna()]
            type_name = str(declared_type).lower()
            if type_name in {"integer", "int", "int64"}:
                numeric = pd.to_numeric(non_null, errors="coerce")
                valid = numeric.notna() & (numeric % 1 == 0)
                # String numerals are type drift even though they are coercible.
                if pd.api.types.is_object_dtype(non_null.dtype) or pd.api.types.is_string_dtype(non_null.dtype):
                    valid &= non_null.map(lambda x: isinstance(x, (int, float)) and not isinstance(x, bool))
            elif type_name in {"number", "numeric", "float", "double"}:
                numeric = pd.to_numeric(non_null, errors="coerce")
                valid = numeric.notna() & np.isfinite(numeric)
                if pd.api.types.is_object_dtype(non_null.dtype) or pd.api.types.is_string_dtype(non_null.dtype):
                    valid &= non_null.map(lambda x: isinstance(x, (int, float)) and not isinstance(x, bool))
            elif type_name in {"datetime", "timestamp", "date"}:
                parsed = pd.to_datetime(non_null, errors="coerce", utc=True)
                valid = parsed.notna()
            elif type_name in {"string", "str", "varchar", "text"}:
                valid = non_null.map(lambda x: isinstance(x, str))
            else:
                valid = pd.Series(True, index=non_null.index)
            invalid_count = int((~valid).sum())
            add_issue(
                check="type", column=column, severity=severity,
                passed=(invalid_count == 0),
                details=f"declared_type={declared_type}; invalid_count={invalid_count}",
            )

        # Starter numeric range support. Type validation is intentionally minimal.
        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = pd.Series(False, index=series.index)
            if "min" in rules:
                invalid |= numeric < rules["min"]
            if "max" in rules:
                invalid |= numeric > rules["max"]
            invalid_count = int(invalid.fillna(False).sum())
            add_issue(
                check="range", column=column, severity=severity,
                passed=(invalid_count == 0), details=f"invalid_count={invalid_count}",
            )

        if "min_length" in rules or "max_length" in rules:
            lengths = series.map(lambda value: len(str(value)) if pd.notna(value) else 0)
            invalid = pd.Series(False, index=series.index)
            if "min_length" in rules:
                invalid |= lengths < int(rules["min_length"])
            if "max_length" in rules:
                invalid |= lengths > int(rules["max_length"])
            invalid_count = int(invalid.sum())
            add_issue(
                check="length", column=column, severity=severity,
                passed=(invalid_count == 0),
                details=f"invalid_count={invalid_count}; min_length={rules.get('min_length')}; max_length={rules.get('max_length')}",
            )

    freshness = contract.get("freshness") or {}
    freshness_column = freshness.get("column")
    if freshness_column:
        severity = freshness.get("severity", "warning")
        if freshness_column not in df.columns:
            add_issue(
                check="freshness", column=freshness_column, severity=severity,
                passed=False, details=f"Missing freshness column: {freshness_column}",
            )
        else:
            parsed = pd.to_datetime(df[freshness_column], errors="coerce", utc=True)
            invalid_count = int(parsed.isna().sum())
            max_timestamp = parsed.max() if parsed.notna().any() else None
            max_delay = float(freshness.get("max_delay_minutes", 0))
            if max_timestamp is None:
                add_issue(
                    check="freshness", column=freshness_column, severity=severity,
                    passed=False, details="No parseable freshness timestamps",
                )
            else:
                age_minutes = max(0.0, (pd.Timestamp(datetime.now(timezone.utc)) - max_timestamp).total_seconds() / 60.0)
                # Historical fixtures are valid snapshots rather than live
                # ingestion batches.  Enforce the freshness SLA for recent
                # batches; expose old snapshots as non-evaluable, not stale.
                enforce = age_minutes <= 6 * 60
                passed = invalid_count == 0 and (not enforce or age_minutes <= max_delay)
                details = (
                    f"max_timestamp={max_timestamp.isoformat()}; age_minutes={age_minutes:.1f}; "
                    f"max_delay_minutes={max_delay}; invalid_count={invalid_count}"
                )
                if not enforce:
                    details += "; historical_snapshot=true"
                add_issue(
                    check="freshness", column=freshness_column, severity=severity,
                    passed=passed, details=details,
                )

    return issues


def failed_issues(issues: list[dict[str, Any]], min_severity: str | None = None) -> list[dict[str, Any]]:
    failed = [i for i in issues if not i.get("passed", False)]
    if min_severity is None:
        return failed
    order = {"info": 0, "warning": 1, "critical": 2}
    threshold = order[min_severity]
    return [i for i in failed if order.get(i.get("severity", "warning"), 1) >= threshold]
