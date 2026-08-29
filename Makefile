PYTHON ?= python

.PHONY: reset baseline tests gx soda dbt dashboard generate elementary

reset:
	$(PYTHON) scripts/reset_lab.py

baseline:
	$(PYTHON) scripts/run_baseline.py

tests:
	pytest tests_public -q

gx:
	$(PYTHON) gx/validate_orders.py

soda:
	$(PYTHON) scripts/validate_soda.py

dbt:
	$(PYTHON) scripts/sync_dbt_seeds.py
	dbt deps --project-dir dbt_project --profiles-dir dbt_project
	dbt build --project-dir dbt_project --profiles-dir dbt_project

elementary:
	dbt deps --project-dir dbt_project
	dbt build --project-dir dbt_project --profiles-dir dbt_project --select elementary

dashboard:
	streamlit run dashboard/app.py

generate:
	$(PYTHON) scripts/generate_data.py --rows 600 --days 42 --seed 27
