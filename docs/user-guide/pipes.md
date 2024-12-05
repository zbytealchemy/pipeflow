# Working with Pipes

## Introduction

Pipes are the fundamental building blocks in Pipeflow. Each pipe is responsible for a specific data transformation task and can be combined with other pipes to create complex data processing pipelines.

## Creating a Basic Pipe

Here's how to create a basic pipe:

```python
from pipeflow import ConfigurablePipe, PipeConfig
from typing import List, Dict

class TransformConfig(PipeConfig):
    field_mapping: Dict[str, str]

class TransformPipe(ConfigurablePipe[Dict, Dict]):
    def __init__(self, config: TransformConfig):
        super().__init__(config)
    
    async def process(self, data: Dict) -> Dict:
        return {
            new_key: data.get(old_key)
            for new_key, old_key in self.config.field_mapping.items()
        }
```

## Type Safety

Pipeflow enforces type safety through:

- Type hints
- Runtime type checking
- Pydantic validation

## Configuration

Configure your pipes using Pydantic models:

```python
config = TransformConfig(
    field_mapping={
        "new_name": "old_name",
        "new_age": "old_age"
    }
)
pipe = TransformPipe(config)
```

## Async Processing

All pipes in Pipeflow are async by default:

```python
async def main():
    data = {"old_name": "John", "old_age": 30}
    result = await pipe.process(data)
```

## Error Handling

Handle errors gracefully:

```python
from pipeflow import PipeError

try:
    result = await pipe.process(data)
except PipeError as e:
    print(f"Error in pipe {e.pipe}: {e.error}")
```

## Best Practices

1. Keep pipes focused on a single responsibility
2. Use type hints consistently
3. Handle errors appropriately
4. Document your pipes
5. Write tests for your pipes
