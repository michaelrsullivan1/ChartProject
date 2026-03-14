PYTHON ?= $(shell if [ -x /usr/local/bin/python3 ]; then echo /usr/local/bin/python3; else command -v python3; fi)

.PHONY: install bootstrap validate-schemas check-x ingest-posts ingest-btc aggregate-btc freeze-snapshot backup-data test lint

install:
	$(PYTHON) -m pip install -e ".[dev]"

bootstrap:
	$(PYTHON) scripts/bootstrap_project.py

validate-schemas:
	$(PYTHON) scripts/validate_schemas.py

check-x:
	$(PYTHON) scripts/check_x_api_setup.py

ingest-posts:
	$(PYTHON) scripts/ingest_saylor_posts.py

ingest-btc:
	$(PYTHON) scripts/ingest_btc_prices.py

aggregate-btc:
	$(PYTHON) scripts/aggregate_btc_prices.py

freeze-snapshot:
	$(PYTHON) scripts/freeze_saylor_bitcoin_snapshot.py

backup-data:
	$(PYTHON) scripts/backup_saylor_bitcoin_data.py

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check src tests scripts
