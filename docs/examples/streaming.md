# Streaming Example

This example shows how to build a streaming pipeline using Pipeflow with Kafka and SQS integration.

## Setup

Install required dependencies:

```bash
pip install pipeflow[kafka,aws]
```

## Creating a Streaming Pipeline

Here's an example of a streaming pipeline that processes messages from Kafka and sends them to SQS:

```python
from pipeflow import Pipeline
from pipeflow.integrations.kafka import KafkaConsumerPipe, KafkaConfig
from pipeflow.integrations.sqs import SQSProducerPipe, SQSConfig
from pipeflow import ConfigurablePipe, PipeConfig
from typing import Dict
import json

# Configuration
class TransformConfig(PipeConfig):
    add_timestamp: bool = True

# Transform pipe
class TransformPipe(ConfigurablePipe[Dict, Dict]):
    def __init__(self, config: TransformConfig):
        super().__init__(config)
    
    async def process(self, data: Dict) -> Dict:
        if self.config.add_timestamp:
            from datetime import datetime
            data["processed_at"] = datetime.utcnow().isoformat()
        return data

# Create the pipeline
async def create_streaming_pipeline():
    # Configure Kafka consumer
    kafka_config = KafkaConfig(
        bootstrap_servers=["localhost:9092"],
        topic="input-topic",
        group_id="processor-group"
    )
    
    # Configure SQS producer
    sqs_config = SQSConfig(
        queue_url="https://sqs.region.amazonaws.com/account/queue",
        region_name="us-west-2"
    )
    
    # Create pipes
    kafka_consumer = KafkaConsumerPipe(kafka_config)
    transform = TransformPipe(TransformConfig(add_timestamp=True))
    sqs_producer = SQSProducerPipe(sqs_config)
    
    # Create pipeline
    pipeline = Pipeline()
    pipeline.add_pipe(kafka_consumer)
    pipeline.add_pipe(transform)
    pipeline.add_pipe(sqs_producer)
    
    return pipeline

# Run the pipeline
async def main():
    pipeline = await create_streaming_pipeline()
    
    try:
        async for result in pipeline:
            print(f"Processed message: {result}")
    except KeyboardInterrupt:
        print("Shutting down pipeline...")
    finally:
        await pipeline.cleanup()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## Error Handling

Add error handling to make the pipeline more robust:

```python
from pipeflow.integrations.kafka import KafkaError
from pipeflow.integrations.sqs import SQSError

async def main():
    pipeline = await create_streaming_pipeline()
    
    try:
        async for result in pipeline:
            try:
                print(f"Processed message: {result}")
            except KafkaError as e:
                print(f"Kafka error: {e}")
            except SQSError as e:
                print(f"SQS error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
    except KeyboardInterrupt:
        print("Shutting down pipeline...")
    finally:
        await pipeline.cleanup()
```

## Testing

Test the streaming pipeline:

```python
from pipeflow.testing.kafka import KafkaTestMixin
from pipeflow.testing.sqs import SQSTestMixin

class TestStreamingPipeline(KafkaTestMixin, SQSTestMixin):
    async def test_pipeline(self):
        # Setup test data
        test_message = {"key": "value"}
        await self.produce_kafka_message(test_message)
        
        # Create and run pipeline
        pipeline = await create_streaming_pipeline()
        async for _ in pipeline:
            break
        
        # Verify results
        messages = await self.receive_sqs_messages()
        assert len(messages) == 1
        assert "processed_at" in messages[0]
```

## Best Practices

1. Always implement proper error handling
2. Use appropriate batch sizes for better performance
3. Monitor pipeline health and metrics
4. Implement graceful shutdown
5. Test with realistic data volumes
