.PHONY: install dev lint format test clean build

PYTHON := python

install:
	$(PYTHON) -m pip install -e .

dev:
	$(PYTHON) -m pip install -e ".[dev]"

lint:
	ruff check src tests
	mypy src

format:
	ruff format src tests

test:
	pytest

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

build:
	$(PYTHON) -m build
