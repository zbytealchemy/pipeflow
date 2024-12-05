# Working with Pipelines

## Overview

Pipelines in Pipeflow are sequences of pipes that process data in a specific order. They can be linear, branching, or merging, allowing you to build complex data processing workflows.

## Creating Pipelines

There are several ways to create pipelines:

### Using the Pipeline Class

```python
from pipeflow import Pipeline, ConfigurablePipe

# Create pipes
filter_pipe = FilterPipe(filter_config)
transform_pipe = TransformPipe(transform_config)

# Create pipeline
pipeline = Pipeline()
pipeline.add_pipe(filter_pipe)
pipeline.add_pipe(transform_pipe)
```

### Using the >> Operator

```python
# Create pipeline using operator
pipeline = filter_pipe >> transform_pipe
```

## Pipeline Configuration

Configure pipeline-wide settings:

```python
from pipeflow import PipelineConfig

config = PipelineConfig(
    max_retries=3,
    retry_delay=5,
    timeout=30
)

pipeline = Pipeline(config=config)
```

## Error Handling

Handle errors at the pipeline level:

```python
try:
    result = await pipeline.process(data)
except PipelineError as e:
    print(f"Pipeline error: {e}")
    print(f"Failed pipe: {e.pipe}")
    print(f"Original error: {e.original_error}")
```

## Monitoring

Monitor pipeline performance:

```python
from pipeflow.monitoring import PipelineMonitor

monitor = PipelineMonitor()
pipeline.set_monitor(monitor)

# Process data
await pipeline.process(data)

# Get metrics
metrics = monitor.get_metrics()
print(f"Total processing time: {metrics.total_time}")
print(f"Records processed: {metrics.record_count}")
```

## Best Practices

1. Keep pipelines focused and modular
2. Handle errors appropriately
3. Monitor pipeline performance
4. Use type hints consistently
5. Document pipeline behavior and requirements
