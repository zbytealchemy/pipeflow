# Basic Concepts

## Overview

Pipeflow is built around a few core concepts that make it easy to build type-safe, async-first data processing pipelines.

## Pipes

A pipe is the basic building block in Pipeflow. It's a component that takes input data, processes it, and produces output data. Pipes are:

- **Type-safe**: Input and output types are checked at runtime
- **Async-first**: All processing is done asynchronously
- **Configurable**: Pipes can be configured using Pydantic models
- **Composable**: Pipes can be combined into pipelines

Example of a basic pipe:

```python
from pipeflow import ConfigurablePipe, PipeConfig
from typing import Dict, List

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
```

## Configuration

Pipeflow uses Pydantic for configuration management. This provides:

- Type validation
- Data parsing and conversion
- Environment variable support
- Nested configurations

## Pipelines

Pipelines are sequences of pipes that process data in order. They can be:

- Linear: Data flows from one pipe to the next
- Branching: Data can flow to multiple pipes
- Merging: Multiple data streams can be combined

## Stream Processing

Pipeflow supports stream processing through:

- Async iterators
- Batching
- Windowing
- Error handling and retries

## Error Handling

Pipeflow provides robust error handling through:

- Type validation
- Custom error types
- Retry mechanisms
- Error propagation control

## Monitoring

Monitor your pipelines with:

- Metrics collection
- Logging
- Performance tracking
- Error reporting
