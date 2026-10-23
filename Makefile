.PHONY: install test lint format format-check retrain serve clean docs drift drift-guard calibrate replay

install:
	pip install -e ".[lgbm,dev,docs]"
	pre-commit install

test:
	pytest

lint:
	ruff check src/fraud_detect/ api/ scripts/ tests/

format:
	ruff format src/fraud_detect/ api/ scripts/ tests/

format-check:
	ruff format --check src/fraud_detect/ api/ scripts/ tests/

retrain:
	python scripts/retrain.py

drift:
	PYTHONPATH=src python scripts/drift_report.py

drift-guard:
	PYTHONPATH=src python scripts/drift_guard.py

calibrate:
	PYTHONPATH=src python scripts/calibrate_model.py

replay:
	PYTHONPATH=src python scripts/labelled_replay.py

serve:
	uvicorn api.main:app --reload

docs:
	sphinx-build -b html docs/source docs/build -W

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov .ruff_cache
