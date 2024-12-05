# Installation

## Requirements

- Python 3.10 or higher
- Poetry (recommended) or pip

## Using Poetry (Recommended)

```bash
poetry add pipeflow
```

## Using pip

```bash
pip install pipeflow
```

## Development Installation

To install Pipeflow for development:

1. Clone the repository:
```bash
git clone https://github.com/zbytealchemy/pipeflow.git
cd pipeflow
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Install pre-commit hooks (optional but recommended):
```bash
pre-commit install
```

## Docker Installation

For integration testing or development with Docker:

```bash
# Clone the repository
git clone https://github.com/zbytealchemy/pipeflow.git
cd pipeflow

# Build and run tests in Docker
make docker-test

# Or start individual services
make docker-up
```

## Verifying Installation

After installation, you can verify everything is working by running the tests:

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration
```
