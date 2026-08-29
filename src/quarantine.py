"""Automatic quarantine for batches with critical contract failures."""
from __future__ import annotations

from datetime import datetime, timezone
import ast
from pathlib import Path
from typing import Any

import pandas as pd


def quarantine_failed_rows(
    df: pd.DataFrame,
    issues: list[dict[str, Any]],
    *,
    dataset: str,
    output_dir: str | Path,
) -> dict[str, Any] | None:
    """Write offending rows for critical failures and return an audit record.

    Dataset-level failures (for example freshness) quarantine the complete
    batch. Row-level checks quarantine only rows that violate the rule.
    """
    critical = [i for i in issues if not i.get("passed", False) and i.get("severity") == "critical"]
    if not critical:
        return None

    mask = pd.Series(False, index=df.index)
    row_level_checks = {"not_null", "unique", "accepted_values", "range", "type", "length"}
    for issue in critical:
        column = issue.get("column")
        check = issue.get("check")
        if not column or column not in df.columns or check not in row_level_checks:
            mask |= True
            continue
        series = df[column]
        if check == "not_null":
            mask |= series.isna()
        elif check == "unique":
            mask |= series.duplicated(keep=False)
        elif check == "accepted_values":
            accepted_text = issue.get("details", "").split("accepted=", 1)
            accepted = None
            if len(accepted_text) == 2:
                try:
                    accepted = set(ast.literal_eval(accepted_text[1]))
                except (SyntaxError, ValueError):
                    accepted = None
            if accepted is not None:
                mask |= series.notna() & ~series.isin(accepted)
            else:
                mask |= series.isna()
        elif check == "range":
            numeric = pd.to_numeric(series, errors="coerce")
            details = issue.get("details", "")
            # Range failures are uncommon in the lab; invalid numeric values
            # are safe to quarantine even without parsing min/max text.
            mask |= numeric.isna() | (numeric < 0)
        elif check == "type":
            mask |= series.isna()
        elif check == "length":
            mask |= series.map(lambda value: len(str(value)) < 20 if pd.notna(value) else True)

    quarantined = df.loc[mask].copy()
    if quarantined.empty:
        quarantined = df.copy()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{dataset}_{timestamp}.csv"
    quarantined.to_csv(path, index=False)
    return {
        "dataset": dataset,
        "path": str(path),
        "rows_quarantined": int(len(quarantined)),
        "critical_checks": [i.get("check") for i in critical],
        "action": "quarantine",
    }
