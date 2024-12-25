# AWS SQS Integration

## Overview

Pipeflow provides seamless integration with AWS Simple Queue Service (SQS) for building reliable message processing pipelines.

## Configuration

Configure SQS integration using the `SQSConfig`:

```python
from pipeflow.integrations.aws import SQSConfig

config = SQSConfig(
    queue_url="https://sqs.region.amazonaws.com/account/queue-name",
    region_name="us-west-2",
    aws_access_key_id="your_access_key",  # Optional
    aws_secret_access_key="your_secret_key",  # Optional
    endpoint_url="http://localhost:4566",  # Optional, for local testing
    max_messages=10,
    wait_time_seconds=20,
    visibility_timeout=30,
    message_attributes={"attribute_name": "attribute_value"}  # Optional
)
```

## SQSSourcePipe

The `SQSSourcePipe` is used to read messages from an SQS queue.

```python
from pipeflow.integrations.aws import SQSSourcePipe, SQSConfig

config = SQSConfig(queue_url="your_queue_url", region_name="your_region")
source = SQSSourcePipe(config)

# Process messages as a stream
async for message in source.process_stream():
    print(f"Received: {message.body}")
    # Message is automatically deleted after processing

# Or process a single message
message = await source.process(None)
if message:
    print(f"Received: {message.body}")
    # You need to manually delete the message if using this method
```

## SQSSinkPipe

The `SQSSinkPipe` is used to send messages to an SQS queue.

```python
from pipeflow.integrations.aws import SQSSinkPipe, SQSConfig

config = SQSConfig(queue_url="your_queue_url", region_name="your_region")
sink = SQSSinkPipe(config)

# Send a message
await sink.process({"message": "Hello, SQS!"})
```

## Error Handling

Handle SQS-specific errors and manage resources properly:

```python
from pipeflow.integrations.aws import SQSError

source = SQSSourcePipe(config)
try:
    await source.start()
    async for message in source.process_stream():
        try:
            # Process message
            print(f"Processing: {message.body}")
        except SQSError as e:
            print(f"SQS error: {e}")
finally:
    await source.stop()
```

## Testing

Use the provided test utilities:

```python
from pipeflow.testing.sqs import SQSTestMixin

class TestSQSPipe(SQSTestMixin):
    async def test_producer(self):
        producer = SQSSinkPipe(self.config)
        await producer.process({"test": "data"})
        messages = await self.receive_messages()
        assert len(messages) == 1
```

## Best Practices

1. Use `process_stream()` for continuous message processing
2. Implement proper error handling and retries
3. Use appropriate visibility timeout
4. Implement dead-letter queues for failed message processing
5. Monitor queue metrics
6. Clean up resources properly using `start()` and `stop()` methods
7. Use message attributes for metadata to avoid parsing the message body
