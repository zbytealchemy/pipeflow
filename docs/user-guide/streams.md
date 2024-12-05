# Stream Processing

## Overview

Pipeflow provides native support for stream processing, allowing you to build efficient data streaming pipelines.

## Basic Streaming

Create a streaming pipeline:

```python
from pipeflow.streams import StreamPipe
from typing import AsyncIterator, Dict

class MyStreamPipe(StreamPipe[Dict, Dict]):
    async def process_stream(self, stream: AsyncIterator[Dict]) -> AsyncIterator[Dict]:
        async for item in stream:
            yield await self.process_item(item)
    
    async def process_item(self, item: Dict) -> Dict:
        return {"processed": item}

# Use the stream pipe
pipe = MyStreamPipe()
async for result in pipe.stream(source_data):
    print(result)
```

## Windowing

Process data in windows:

```python
from pipeflow.streams import WindowedStreamPipe
from datetime import timedelta

class WindowProcessor(WindowedStreamPipe[Dict, List]):
    def __init__(self, window_size: timedelta):
        super().__init__(window_size)
    
    async def process_window(self, window: List[Dict]) -> List:
        return self.aggregate_window(window)
```

## Batching

Process data in batches:

```python
from pipeflow.streams import BatchStreamPipe

class BatchProcessor(BatchStreamPipe[Dict, List]):
    def __init__(self, batch_size: int):
        super().__init__(batch_size)
    
    async def process_batch(self, batch: List[Dict]) -> List:
        return await self.process_items(batch)
```

## Backpressure

Handle backpressure:

```python
from pipeflow.streams import BackpressureConfig

config = BackpressureConfig(
    max_buffer_size=1000,
    throttle_threshold=0.8,
    min_processing_time=0.1
)

pipe = StreamPipe(config=config)
```

## Error Handling

Handle stream errors:

```python
from pipeflow.streams import StreamError

try:
    async for result in pipe.stream(data):
        try:
            process_result(result)
        except StreamError as e:
            handle_stream_error(e)
except Exception as e:
    handle_fatal_error(e)
```

## Monitoring

Monitor stream processing:

```python
from pipeflow.monitoring import StreamMonitor

monitor = StreamMonitor()
pipe.set_monitor(monitor)

# Get stream metrics
metrics = monitor.get_metrics()
print(f"Throughput: {metrics.throughput}")
print(f"Backpressure: {metrics.backpressure}")
```

## Best Practices

1. Use appropriate window/batch sizes
2. Handle backpressure
3. Implement proper error handling
4. Monitor stream performance
5. Clean up resources properly
6. Test with realistic data volumes
