# Bonus Evidence

The repository now contains runnable evidence for every optional bonus that
does not depend on the instructor's mystery dataset.

| Bonus | Implementation | Verification |
|---|---|---|
| MAD/same-weekday anomaly | `observability/anomaly.py` | `student_api.detect_metric(..., method="auto")` |
| dbt native unit test | `dbt_project/models/marts/unit_tests.yml` | `dbt build` |
| GX severity/actions | `gx/validate_orders.py` | `reports/gx_validation_action.json` |
| Automatic quarantine | `src/quarantine.py` | Duplicate PK writes `data/quarantine/orders_*.csv` |
| Soda Data Contract | `contracts/orders_soda.yml` | `python scripts/validate_soda.py` |
| Elementary OSS | `dbt_project/packages.yml` | `dbt deps` and `dbt build` |
| OpenLineage dataset lineage | `observability/openlineage.py` | `reports/openlineage_events.jsonl` |
| Column lineage | `observability/lineage.py` | `student_api.column_downstream(...)` |
| Multi-window burn-rate | `observability/slo.py` | `student_api.multiwindow_burn(...)` |
| RAG embedding/token drift | `observability/rag_metrics.py` | `student_api.rag_length_shift(...)` and `rag_embedding_shift(...)` |

## Commands

```powershell
python scripts/reset_lab.py
dbt deps --project-dir dbt_project --profiles-dir dbt_project
dbt build --project-dir dbt_project --profiles-dir dbt_project
python scripts/validate_soda.py
python gx/validate_orders.py
```

The only rubric item intentionally not claimable before the instructor sends
the mystery data is the 15-point mystery incident RCA.
