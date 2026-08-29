#!/usr/bin/env python3
"""Run the SodaCL orders data contract against the local DuckDB warehouse."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
from soda.scan import Scan

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    db_path = ROOT / "warehouse" / "lab.duckdb"
    if not db_path.exists():
        raise SystemExit("Run dbt build first to create warehouse/lab.duckdb")

    scan = Scan()
    scan.set_data_source_name("duckdb")
    connection = duckdb.connect(str(db_path), read_only=True)
    scan.add_duckdb_connection(connection)
    scan.add_sodacl_yaml_file(str(ROOT / "contracts" / "orders_soda.yml"))
    output = ROOT / "reports" / "soda_scan.json"
    scan.set_scan_results_file(str(output))
    exit_code = scan.execute()
    results = scan.get_scan_results()
    print(f"Soda checks: {len(results.get('checks', []))}")
    print(f"Soda status: {'PASS' if exit_code == 0 else 'FAIL'}")
    print(f"Soda evidence: {output.relative_to(ROOT)}")
    connection.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
