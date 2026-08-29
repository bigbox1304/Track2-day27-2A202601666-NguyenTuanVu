#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from observability.anomaly import detect_anomaly
from observability.lineage import get_downstream_assets
from observability.openlineage import emit_dataset_event
from observability.rag_metrics import detect_text_length_shift
from observability.slo import calculate_slo, evaluate_multiwindow_burn
from src.contract_validator import failed_issues, load_contract, validate_dataframe
from src.io_utils import load_jsonl
from src.quarantine import quarantine_failed_rows


def main() -> None:
    orders = pd.read_csv(ROOT / "data" / "incoming" / "orders.csv")
    history = pd.read_csv(ROOT / "data" / "history" / "metrics_history.csv")
    contract = load_contract(ROOT / "contracts" / "orders_contract.yaml")
    issues = validate_dataframe(orders, contract)
    failed = failed_issues(issues)
    critical_failed = failed_issues(issues, min_severity="critical")

    docs = load_jsonl(ROOT / "data" / "incoming" / "kb_documents.jsonl")
    kb_contract = load_contract(ROOT / "contracts" / "kb_contract.yaml")
    kb_issues = validate_dataframe(pd.DataFrame(docs), kb_contract)
    kb_failed = failed_issues(kb_issues)
    orders_quarantine = quarantine_failed_rows(
        orders,
        issues,
        dataset="orders",
        output_dir=ROOT / "data" / "quarantine",
    )
    kb_quarantine = quarantine_failed_rows(
        pd.DataFrame(docs),
        kb_issues,
        dataset="kb_documents",
        output_dir=ROOT / "data" / "quarantine",
    )

    # Public example: segment by weekday before applying the simple detector.
    # Hidden evaluation still challenges students to make detect_metric(..., context=...)
    # context-aware instead of relying on caller-side preprocessing.
    current_dow = datetime.now().weekday()
    segment = history.loc[history["day_of_week"] == current_dow, "row_count"].tail(8).tolist()
    row_history = segment if len(segment) >= 3 else history["row_count"].tail(14).tolist()
    row_result = detect_anomaly(
        len(orders),
        row_history,
        method="auto",
        context={"metric_name": "row_count", "day_of_week": current_dow},
    )

    updated = pd.to_datetime(orders["updated_at"], utc=True, errors="coerce")
    freshness_minutes = (
        pd.Timestamp(datetime.now(timezone.utc)) - updated.max()
    ).total_seconds() / 60.0

    text_result = detect_text_length_shift(
        [d["content"] for d in docs], history["mean_text_length"].tail(14).tolist()
    )

    # Demo SLO: one check event for this run.
    bad = 1 if critical_failed else 0
    contract_slo = calculate_slo(0.999, bad_events=bad, total_events=1)
    burn_policy = evaluate_multiwindow_burn(
        short_window_burn=contract_slo["burn_rate"],
        long_window_burn=contract_slo["burn_rate"],
    )

    with open(ROOT / "data" / "baseline" / "lineage_graph.json", "r", encoding="utf-8") as f:
        lineage = json.load(f)["dataset_lineage"]
    blast_radius = get_downstream_assets(lineage, "stg_orders")
    kb_blast_radius = get_downstream_assets(lineage, "kb_documents")
    lineage_output = ROOT / "reports" / "openlineage_events.jsonl"
    emit_dataset_event(
        job_name="orders_to_revenue_dashboard",
        inputs=["raw_orders", "raw_customers"],
        outputs=["stg_orders", "stg_customers", "fct_daily_revenue", "ceo_revenue_dashboard"],
        output_path=lineage_output,
    )
    emit_dataset_event(
        job_name="kb_to_support_agent",
        inputs=["kb_documents"],
        outputs=["kb_active_docs", "rag_index", "support_agent"],
        output_path=lineage_output,
    )

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "orders_rows": int(len(orders)),
        "failed_contract_checks": len(failed),
        "critical_contract_failures": len(critical_failed),
        "contract_checks": issues,
        "kb_failed_checks": len(kb_failed),
        "kb_contract_checks": kb_issues,
        "row_count_anomaly": row_result,
        "freshness_minutes": freshness_minutes,
        "kb_text_length_signal": text_result,
        "contract_slo": contract_slo,
        "multiwindow_burn": burn_policy,
        "sample_blast_radius_from_stg_orders": blast_radius,
        "kb_blast_radius": kb_blast_radius,
        "quarantine": {"orders": orders_quarantine, "kb_documents": kb_quarantine},
        "openlineage_events": str(lineage_output.relative_to(ROOT)),
    }
    out = ROOT / "reports" / "latest_metrics.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print("=== DATA RELIABILITY BASELINE ===")
    print(f"orders rows              : {len(orders)}")
    print(f"contract failed checks   : {len(failed)}")
    print(f"critical contract fails  : {len(critical_failed)}")
    print(f"KB failed checks         : {len(kb_failed)}")
    if orders_quarantine:
        print(f"orders quarantine        : {orders_quarantine['path']}")
    if kb_quarantine:
        print(f"KB quarantine            : {kb_quarantine['path']}")
    print(f"row-count anomaly        : {row_result['is_anomaly']} ({row_result['method']}, score={row_result['score']:.2f})")
    print(f"freshness minutes        : {freshness_minutes:.1f}")
    print(f"KB length anomaly        : {text_result['is_anomaly']}")
    print(f"sample blast radius      : {', '.join(blast_radius)}")
    print(f"report                    : {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
