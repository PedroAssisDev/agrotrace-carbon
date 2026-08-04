.PHONY: install test example clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest

example:
	PYTHONPATH=src python -m model_training_service.cli train-all --csv examples/approved_results.csv --config configs/training.yaml

clean:
	rm -rf artifacts/* data/processed/* .pytest_cache
	touch artifacts/.gitkeep data/processed/.gitkeep
