# Prefect Integration

## Overview

Pipeflow integrates seamlessly with Prefect, allowing you to build and manage data pipelines as Prefect flows.

## Installation

Install Pipeflow with Prefect support:

```bash
pip install pipeflow[prefect]
```

## Basic Integration

Create a Prefect flow from a Pipeflow pipeline:

```python
from pipeflow import Pipeline
from pipeflow.integrations.prefect import PrefectPipeline
from prefect import flow

# Create Pipeflow pipeline
pipeline = Pipeline([
    FilterPipe(filter_config),
    TransformPipe(transform_config)
])

# Create Prefect flow
@flow(name="data-processing-flow")
async def process_data(data):
    prefect_pipeline = PrefectPipeline(pipeline)
    return await prefect_pipeline.run(data)

# Run the flow
result = await process_data(input_data)
```

## Task Configuration

Configure Prefect task settings:

```python
from prefect import task
from pipeflow.integrations.prefect import task_config

@task_config(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=lambda context, *args, **kwargs: "cache_key"
)
class ProcessingPipe(ConfigurablePipe[Dict, Dict]):
    async def process(self, data: Dict) -> Dict:
        return process_data(data)
```

## Monitoring

Monitor pipeline execution in Prefect:

```python
from pipeflow.integrations.prefect import PrefectMonitor

monitor = PrefectMonitor()
pipeline.set_monitor(monitor)

# Metrics will be available in Prefect UI
```

## Error Handling

Handle errors with Prefect:

```python
from prefect import flow
from prefect.utilities.annotations import task

@flow
async def resilient_pipeline(data):
    try:
        result = await pipeline.run(data)
        return result
    except Exception as e:
        # Log error to Prefect
        logger = get_run_logger()
        logger.error(f"Pipeline failed: {e}")
        raise
```

## Scheduling

Schedule pipeline execution:

```python
from prefect.schedules import IntervalSchedule
from datetime import timedelta

schedule = IntervalSchedule(
    interval=timedelta(hours=1)
)

@flow(schedule=schedule)
async def scheduled_pipeline(data):
    return await pipeline.run(data)
```

## Best Practices

1. Use appropriate task configurations
2. Implement proper error handling
3. Monitor pipeline execution
4. Use Prefect features like caching and retries
5. Document flow behavior
6. Test flows before deployment
