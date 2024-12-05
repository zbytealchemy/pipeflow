# Prefect Integration Example

This example demonstrates how to integrate Pipeflow with Prefect for workflow orchestration.

## Setup

First, install the required dependencies:

```bash
pip install pipeflow[prefect]
```

## Basic Integration

```python
from pipeflow import ConfigurablePipe, PipeConfig, Pipeline
from pipeflow.integrations.prefect import PrefectPipeline
from prefect import flow, task
from typing import Dict, List

# Define pipes
class ProcessConfig(PipeConfig):
    multiply_by: float = 2.0

class ProcessPipe(ConfigurablePipe[Dict, Dict]):
    async def process(self, data: Dict) -> Dict:
        data["value"] *= self.config.multiply_by
        return data

# Create Prefect flow
@flow(name="data-processing-flow")
async def process_data(data: Dict) -> Dict:
    # Create pipeline
    pipe = ProcessPipe(ProcessConfig(multiply_by=2.0))
    pipeline = Pipeline([pipe])
    
    # Wrap with Prefect
    prefect_pipeline = PrefectPipeline(pipeline)
    
    return await prefect_pipeline.run(data)
```

## Task Configuration

```python
from pipeflow.integrations.prefect import task_config

@task_config(
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=lambda context, *args, **kwargs: "cache_key"
)
class CachablePipe(ConfigurablePipe[Dict, Dict]):
    async def process(self, data: Dict) -> Dict:
        # Process data
        return processed_data
```

## Complex Workflow

```python
from prefect import flow, task
from datetime import timedelta

# Define tasks
@task(retries=2)
async def fetch_data() -> List[Dict]:
    # Fetch data from source
    return data

@task
async def validate_data(data: List[Dict]) -> List[Dict]:
    # Validate data
    return valid_data

# Define flow
@flow(
    name="etl-pipeline",
    description="ETL pipeline using Pipeflow and Prefect",
    schedule=timedelta(hours=1)
)
async def etl_pipeline():
    # Fetch and validate data
    raw_data = await fetch_data()
    valid_data = await validate_data(raw_data)
    
    # Create pipeline
    transform_pipe = ProcessPipe(ProcessConfig(multiply_by=2.0))
    pipeline = Pipeline([transform_pipe])
    
    # Process data
    prefect_pipeline = PrefectPipeline(pipeline)
    results = []
    
    for item in valid_data:
        result = await prefect_pipeline.run(item)
        results.append(result)
    
    return results
```

## Error Handling

```python
from prefect import flow
from prefect.utilities.annotations import task

@flow
async def resilient_pipeline(data: Dict):
    try:
        # Create and run pipeline
        pipeline = create_pipeline()
        prefect_pipeline = PrefectPipeline(pipeline)
        return await prefect_pipeline.run(data)
    except Exception as e:
        # Log error to Prefect
        logger = get_run_logger()
        logger.error(f"Pipeline failed: {e}")
        raise
```

## Monitoring

```python
from pipeflow.integrations.prefect import PrefectMonitor

# Create monitor
monitor = PrefectMonitor()

# Create pipeline with monitoring
pipeline = Pipeline()
pipeline.set_monitor(monitor)

# Metrics will be available in Prefect UI
```

## Deployment

```python
from prefect.deployments import Deployment
from prefect.orion.schemas.schedules import IntervalSchedule

# Create deployment
deployment = Deployment.build_from_flow(
    flow=etl_pipeline,
    name="etl-pipeline-hourly",
    schedule=IntervalSchedule(interval=timedelta(hours=1)),
    tags=["etl", "production"]
)

# Apply deployment
deployment.apply()
```

## Best Practices

1. Use appropriate task configurations
2. Implement proper error handling
3. Monitor pipeline execution
4. Use Prefect features like caching and retries
5. Document flow behavior
6. Test flows before deployment
