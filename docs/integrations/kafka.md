# Kafka Integration

## Overview

Pipeflow provides native integration with Apache Kafka for building streaming data pipelines.

## Configuration

Configure Kafka integration using the `KafkaConfig`:

```python
from pipeflow.integrations.kafka import KafkaConfig

config = KafkaConfig(
    bootstrap_servers=["localhost:9092"],
    topic="my-topic",
    group_id="my-consumer-group"
)
```

## Consumer Example

Create a Kafka consumer pipe:

```python
from pipeflow.integrations.kafka import KafkaConsumerPipe

consumer = KafkaConsumerPipe(config)
async for message in consumer:
    print(f"Received: {message}")
```

## Producer Example

Create a Kafka producer pipe:

```python
from pipeflow.integrations.kafka import KafkaProducerPipe

producer = KafkaProducerPipe(config)
await producer.process({"key": "value"})
```

## Error Handling

Handle Kafka-specific errors:

```python
from pipeflow.integrations.kafka import KafkaError

try:
    await producer.process(data)
except KafkaError as e:
    print(f"Kafka error: {e}")
```

## Testing

Use the provided test utilities:

```python
from pipeflow.testing.kafka import KafkaTestMixin

class TestKafkaPipe(KafkaTestMixin):
    async def test_producer(self):
        producer = KafkaProducerPipe(self.config)
        await producer.process({"test": "data"})
        messages = await self.consume_messages()
        assert len(messages) == 1
```

## Best Practices

1. Use appropriate serialization formats
2. Configure proper partitioning
3. Handle backpressure
4. Monitor consumer lag
5. Implement proper error handling
