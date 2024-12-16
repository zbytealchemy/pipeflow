.PHONY: install format lint test clean build publish

install:
	poetry install

format:
	poetry run black .
	poetry run ruff --fix .

lint:
	poetry run mypy .
	poetry run black --check .
	poetry run ruff .

test:
	poetry run pytest -v --cov=pipeflow_redis --cov-report=term-missing tests/

clean:
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

build: clean
	poetry build

publish: build
	poetry publish

# Development workflow targets
dev: install format lint test
