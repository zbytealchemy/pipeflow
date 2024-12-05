# AWS SQS Integration

## Overview

Pipeflow provides seamless integration with AWS Simple Queue Service (SQS) for building reliable message processing pipelines.

## Configuration

Configure SQS integration using the `SQSConfig`:

```python
from pipeflow.integrations.sqs import SQSConfig

config = SQSConfig(
    queue_url="https://sqs.region.amazonaws.com/account/queue-name",
    region_name="us-west-2",
    max_messages=10,
    wait_time_seconds=20
)
```

## Consumer Example

Create an SQS consumer pipe:

```python
from pipeflow.integrations.sqs import SQSConsumerPipe

consumer = SQSConsumerPipe(config)
async for messages in consumer:
    for message in messages:
        print(f"Received: {message.body}")
        await message.delete()
```

## Producer Example

Create an SQS producer pipe:

```python
from pipeflow.integrations.sqs import SQSProducerPipe

producer = SQSProducerPipe(config)
await producer.process({
    "message": "Hello, SQS!",
    "attributes": {"type": "greeting"}
})
```

## Error Handling

Handle SQS-specific errors:

```python
from pipeflow.integrations.sqs import SQSError

try:
    await producer.process(data)
except SQSError as e:
    print(f"SQS error: {e}")
```

## Testing

Use the provided test utilities:

```python
from pipeflow.testing.sqs import SQSTestMixin

class TestSQSPipe(SQSTestMixin):
    async def test_producer(self):
        producer = SQSProducerPipe(self.config)
        await producer.process({"test": "data"})
        messages = await self.receive_messages()
        assert len(messages) == 1
```

## Best Practices

1. Handle message deduplication
2. Use appropriate visibility timeout
3. Implement dead-letter queues
4. Monitor queue metrics
5. Clean up resources properly
