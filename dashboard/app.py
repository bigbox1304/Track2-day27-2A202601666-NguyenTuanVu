from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "latest_metrics.json"
HISTORY = ROOT / "data" / "history" / "metrics_history.csv"

st.set_page_config(page_title="Data Reliability Lab", layout="wide")
st.title("Data Reliability Game Day")
st.caption("Starter dashboard - improve it only if it helps incident decisions.")

if not REPORT.exists():
    st.warning("Run `make baseline` first to generate reports/latest_metrics.json")
    st.stop()

report = json.loads(REPORT.read_text(encoding="utf-8"))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Orders rows", report["orders_rows"])
c2.metric("Freshness (min)", f"{report['freshness_minutes']:.1f}")
c3.metric("Contract failures", report["failed_contract_checks"])
c4.metric("KB failures", report.get("kb_failed_checks", 0))

st.subheader("Current signals")
st.json({
    "row_count_anomaly": report["row_count_anomaly"],
    "kb_text_length_signal": report["kb_text_length_signal"],
    "contract_slo": report["contract_slo"],
    "multiwindow_burn": report.get("multiwindow_burn", {}),
})

slo = report.get("contract_slo", {})
st.subheader("SLO and error budget")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Target", f"{slo.get('target', 0) * 100:.3f}%")
s2.metric("Actual bad rate", f"{slo.get('actual_bad_rate', 0) * 100:.3f}%")
s3.metric("Burn rate", f"{slo.get('burn_rate', 0):.2f}x")
s4.metric("Remaining budget", f"{slo.get('remaining_error_budget_fraction', 0) * 100:.1f}%")

history = pd.read_csv(HISTORY)
st.subheader("Historical row count")
st.line_chart(history.set_index("date")[["row_count"]])

st.subheader("Example blast radius")
st.write("stg_orders -> " + " -> ".join(report["sample_blast_radius_from_stg_orders"]))
if report.get("kb_blast_radius"):
    st.write("kb_documents -> " + " -> ".join(report["kb_blast_radius"]))

st.info("Incident policy: critical contract failures block/quarantine; warning signals require investigation and owner acknowledgement.")
