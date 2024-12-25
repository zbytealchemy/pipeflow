.PHONY: help install test lint format clean docs build publish docker-test docker-up docker-down test-unit test-integration test-watch update-deps

help:  ## Show this help menu
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "%-30s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

install:  ## Install the package and dependencies
	poetry install

test:  ## Run all tests with coverage
	poetry run pytest tests/ --cov=pipeflow --cov-report=term-missing

test-unit:  ## Run only unit tests
	poetry run pytest tests/test_pipeflow -v

test-integration:  ## Run only integration tests
	poetry run pytest tests/integrations -v

test-watch:  ## Run tests in watch mode (requires pytest-watch)
	poetry run ptw tests/ --onpass "echo 'All tests passed!'" --onfail "echo 'Tests failed!'"

update-deps:  ## Update dependencies and regenerate lock file
	poetry update
	poetry lock --no-update

lint:  ## Run code linting
	poetry run black . --check
	poetry run isort . --check-only
	poetry run mypy src/pipeflow

format:  ## Format code
	poetry run black .
	poetry run isort .

clean:  ## Clean up build artifacts
	rm -rf dist/
	rm -rf build/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf site/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

docs:  ## Build documentation
	poetry run mkdocs build

docs-serve:  ## Serve documentation locally
	poetry run mkdocs serve

build:  ## Build package
	poetry build

publish:  ## Publish package to PyPI
	poetry publish

docker-test:  ## Run tests in Docker
	docker compose -f docker-compose.test.yml build --no-cache
	docker compose -f docker-compose.test.yml run --rm test

docker-up:  ## Start all Docker services for integration tests
	docker compose up -d localstack kafka redis

docker-down:  ## Stop all Docker services
	docker compose down
