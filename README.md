# Pipeflow

[![Test](https://github.com/zmastylo/pipeflow/actions/workflows/test.yml/badge.svg)](https://github.com/zmastylo/pipeflow/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/zmastylo/pipeflow/branch/main/graph/badge.svg)](https://codecov.io/gh/zmastylo/pipeflow)
[![PyPI version](https://badge.fury.io/py/pipeflow.svg)](https://badge.fury.io/py/pipeflow)

A type-safe, async-first data processing pipeline framework built with Python.

## Features

- Generic, type-safe data processing pipeline framework
- Built-in configuration management using Pydantic
- Async-first design
- Integration with Prefect for workflow management
- Clean, modular architecture that's easy to extend

## Installation

```bash
pip install pipeflow
```

## Quick Start

Here are some examples of how to use Pipeflow:

### Basic Data Transformation

```python
from pipeflow import ConfigurablePipe, PipeConfig
from typing import List, Dict

class FilterConfig(PipeConfig):
    field: str
    value: str

class FilterPipe(ConfigurablePipe[List[Dict], List[Dict]]):
    def __init__(self, config: FilterConfig):
        super().__init__(config)
    
    async def process(self, data: List[Dict]) -> List[Dict]:
        return [
            record for record in data 
            if record.get(self.config.field) == self.config.value
        ]

# Use the pipe
config = FilterConfig(field="status", value="active")
pipe = FilterPipe(config)
result = await pipe(data)
```

### DataFrame Processing

```python
from pipeflow import DataFramePipe, DataFramePipeConfig
import pandas as pd

class AggregateConfig(DataFramePipeConfig):
    group_by: List[str]
    agg_column: str

class AggregatePipe(DataFramePipe):
    def __init__(self, config: AggregateConfig):
        super().__init__(config)
    
    async def process(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby(self.config.group_by)[self.config.agg_column].mean().reset_index()

# Use the pipe
config = AggregateConfig(group_by=["category"], agg_column="sales")
pipe = AggregatePipe(config)
result = await pipe(df)
```

### Pipeline Composition

```python
from pipeflow import BasePipe
from typing import List, Any

class Pipeline:
    def __init__(self, pipes: List[BasePipe]):
        self.pipes = pipes
    
    async def process(self, data: Any) -> Any:
        result = data
        for pipe in self.pipes:
            result = await pipe(result)
        return result

# Create and use pipeline
pipeline = Pipeline([
    ValidationPipe(),
    TransformPipe(config),
    StoragePipe(config)
])
result = await pipeline.process(data)
```

## More Examples

Check out the `examples` directory for complete working examples:

- `basic_transformation.py`: Shows how to filter and transform dictionary data
- `dataframe_processing.py`: Demonstrates DataFrame operations with validation
- `pipeline_composition.py`: Illustrates how to compose pipes into a pipeline
- `lambda_composition.py`: Shows how to create quick pipes using lambda functions and function composition
- `prefect_integration.py`: Demonstrates advanced Prefect integration with retries and flows

### Lambda Function Composition

```python
from pipeflow import BasePipe
from typing import Callable, TypeVar

T = TypeVar('T')
U = TypeVar('U')

class LambdaPipe(BasePipe[T, U]):
    def __init__(self, func: Callable[[T], U], name: str = None):
        super().__init__(name=name or func.__name__)
        self.func = func
    
    async def process(self, data: T) -> U:
        return self.func(data)

# Create pipes using lambda functions
double = LambdaPipe(lambda x: x * 2, name="double")
add_ten = LambdaPipe(lambda x: x + 10, name="add_ten")

# Compose pipes
pipeline = compose(double, add_ten)
result = await pipeline(5)  # Returns: 20
```

### Prefect Integration

```python
from prefect import flow, task
from pipeflow import ConfigurablePipe, PipeConfig

class LoadConfig(PipeConfig):
    filename: str

class LoadPipe(ConfigurablePipe[None, pd.DataFrame]):
    async def process(self, _: None) -> pd.DataFrame:
        return pd.read_csv(self.config.filename)

@task(retries=3, retry_delay_seconds=5)
async def load_data(config: Dict[str, Any]) -> pd.DataFrame:
    pipe = LoadPipe(LoadConfig(**config))
    return await pipe(None)

@flow(name="process_data")
async def process_data(input_file: str, output_file: str) -> str:
    # Load data with retries
    df = await load_data({"filename": input_file})
    
    # Process data through pipes
    df = await transform_data(df, transforms)
    
    # Save results
    return await save_data(df, {"filename": output_file})
```

## Integration Testing

Pipeflow includes integration tests for various external services. To run the integration tests, you'll need to set up the following dependencies:

### Prerequisites

- **LocalStack**: For AWS services (SQS)
  ```bash
  docker run -d -p 4566:4566 localstack/localstack
  ```

- **Kafka**: For message streaming
  ```bash
  docker run -d -p 9092:9092 -p 2181:2181 wurstmeister/kafka
  ```

- **Redis**: For caching and message queues
  ```bash
  docker run -d -p 6379:6379 redis
  ```

### Running Integration Tests

Run all integration tests:
```bash
poetry run pytest tests/integrations -v
```

Run specific integration tests:
```bash
# Run SQS tests
poetry run pytest tests/integrations/test_aws.py -v

# Run Kafka tests
poetry run pytest tests/integrations/test_kafka.py -v

# Run Redis tests
poetry run pytest tests/integrations/test_redis.py -v
```

### Test Configuration

- **SQS Tests**: Uses LocalStack with endpoint `http://localhost:4566` and test credentials
- **Kafka Tests**: Connects to `localhost:9092` with auto topic creation enabled
- **Redis Tests**: Connects to `localhost:6379` with default configuration

### Writing Integration Tests

When writing integration tests for Pipeflow:

1. Use the provided fixtures in `tests/conftest.py` for service configurations
2. Mark tests with `@pytest.mark.integration` to separate them from unit tests
3. Ensure proper cleanup of resources in test teardown
4. Use async/await patterns consistently for all I/O operations

Example integration test:
```python
import pytest
from pipeflow.integrations.aws import SQSConfig, SQSSinkPipe, SQSSourcePipe

@pytest.mark.integration
@pytest.mark.asyncio
async def test_sqs_message_flow(sqs_config):
    # Create pipes
    sink = SQSSinkPipe(sqs_config)
    source = SQSSourcePipe(sqs_config)
    
    # Test data
    test_data = {"key": "value"}
    
    try:
        # Send message
        await sink.start()
        await sink.process(test_data)
        
        # Receive message
        message = await source.process(None)
        
        # Verify
        assert message.body == test_data
    finally:
        # Cleanup
        await asyncio.gather(
            sink.stop(),
            source.stop()
        )
```

## License

MIT
