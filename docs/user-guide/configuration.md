# Configuration

## Overview

Pipeflow uses Pydantic for configuration management, providing type safety, validation, and easy integration with environment variables.

## Basic Configuration

All configurations in Pipeflow inherit from `PipeConfig`:

```python
from pipeflow import PipeConfig
from pydantic import Field

class MyConfig(PipeConfig):
    field1: str
    field2: int = Field(default=10, ge=0)
    field3: bool = False
```

## Environment Variables

Load configuration from environment variables:

```python
class DatabaseConfig(PipeConfig):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    username: str
    password: str
    
    class Config:
        env_prefix = "DB_"

# Can be loaded from:
# DB_HOST=myhost.com
# DB_PORT=5432
# DB_USERNAME=user
# DB_PASSWORD=pass
```

## Nested Configuration

Create complex configurations:

```python
class KafkaConfig(PipeConfig):
    bootstrap_servers: List[str]
    topic: str
    group_id: str

class ProcessingConfig(PipeConfig):
    batch_size: int = 100
    timeout: int = 30
    kafka: KafkaConfig

config = ProcessingConfig(
    batch_size=200,
    kafka=KafkaConfig(
        bootstrap_servers=["localhost:9092"],
        topic="my-topic",
        group_id="my-group"
    )
)
```

## Validation

Add validation rules:

```python
from pydantic import validator

class BatchConfig(PipeConfig):
    size: int = Field(ge=1, le=1000)
    timeout: int = Field(ge=0)
    
    @validator("timeout")
    def validate_timeout(cls, v, values):
        if v == 0 and values["size"] > 100:
            raise ValueError("Timeout required for large batch sizes")
        return v
```

## Best Practices

1. Use type hints for all fields
2. Provide sensible defaults
3. Add field descriptions
4. Use environment variables for sensitive data
5. Validate configuration values
