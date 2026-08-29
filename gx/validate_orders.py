#!/usr/bin/env python3
"""Small Great Expectations Core 1.21 example.

This file demonstrates the modern dataframe flow with a few expectations.
Students should extend it into a reusable Expectation Suite / Validation
Definition / Checkpoint and design actions based on severity.
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    import great_expectations as gx
except ImportError as exc:  # friendlier classroom failure
    raise SystemExit("great_expectations is not installed. Run: pip install -r requirements.txt") from exc

from great_expectations.checkpoint.actions import ValidationAction, _VALIDATION_ACTION_REGISTRY


class WriteValidationEvidenceAction(ValidationAction):
    """Persist a checkpoint decision as an auditable local action result."""

    type: str = "write_validation_evidence"
    name: str = "write_validation_evidence"
    output_path: str

    def run(self, checkpoint_result, action_context=None) -> dict:
        payload = {
            "success": bool(checkpoint_result.success),
            "action": "continue" if checkpoint_result.success else "block_or_quarantine",
            "checkpoint": "orders_contract_checkpoint",
        }
        path = Path(self.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload


try:
    _VALIDATION_ACTION_REGISTRY.register("write_validation_evidence", WriteValidationEvidenceAction)
except Exception:
    # The module may be imported more than once in an interactive session.
    pass


def main() -> None:
    df = pd.read_csv(ROOT / "data" / "incoming" / "orders.csv")
    context = gx.get_context()

    # Use unique names so re-running inside an ephemeral context is simple.
    data_source = context.data_sources.add_pandas("orders_pandas")
    asset = data_source.add_dataframe_asset(name="orders_dataframe")
    batch_definition = asset.add_batch_definition_whole_dataframe("whole_orders")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    suite = gx.ExpectationSuite(name="orders_contract_suite")
    expectations = [
        (gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id"), "critical"),
        (gx.expectations.ExpectColumnValuesToBeUnique(column="order_id"), "critical"),
        (gx.expectations.ExpectColumnValuesToBeBetween(column="amount", min_value=0), "critical"),
        (gx.expectations.ExpectColumnValuesToBeInSet(column="currency", value_set=["USD", "VND"]), "critical"),
        (gx.expectations.ExpectColumnValuesToBeInSet(
            column="status", value_set=["pending", "completed", "refunded", "cancelled"]
        ), "warning"),
    ]
    for expectation, severity in expectations:
        expectation.meta = {"severity": severity, "action": "block" if severity == "critical" else "warn"}
        suite.add_expectation(expectation)

    # GX Core objects make the run reproducible and allow the same validation
    # to be attached to a Checkpoint in a real deployment.
    context.suites.add(suite)
    validation_definition = gx.ValidationDefinition(
        data=batch_definition,
        suite=suite,
        name="orders_contract_validation",
    )
    context.validation_definitions.add(validation_definition)
    checkpoint = gx.Checkpoint(
        name="orders_contract_checkpoint",
        validation_definitions=[validation_definition],
        actions=[WriteValidationEvidenceAction(output_path=str(ROOT / "reports" / "gx_validation_action.json"))],
    )
    context.checkpoints.add(checkpoint)
    result = checkpoint.run(
        batch_parameters={"dataframe": df}
    )

    success = bool(result.success)
    print("GX checkpoint:", "PASS" if success else "FAIL")
    print("Action:", "continue" if success else "block/quarantine critical failures")
    if not success:
        print("The checkpoint result contains expectation-level failure details and severity metadata.")


if __name__ == "__main__":
    main()
