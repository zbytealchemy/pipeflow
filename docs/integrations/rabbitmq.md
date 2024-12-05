# RabbitMQ Integration

## Overview

Pipeflow provides native integration with RabbitMQ for building message-based data processing pipelines.

## Installation

Install Pipeflow with RabbitMQ support:

```bash
pip install pipeflow[rabbitmq]
```

## Configuration

Configure RabbitMQ connection:

```python
from pipeflow.integrations.rabbitmq import RabbitMQConfig

config = RabbitMQConfig(
    host="localhost",
    port=5672,
    username="guest",
    password="guest",
    virtual_host="/"
)
```

## Consumer

Create a RabbitMQ consumer:

```python
from pipeflow.integrations.rabbitmq import RabbitMQConsumerPipe

consumer = RabbitMQConsumerPipe(
    config=config,
    queue="my-queue",
    prefetch_count=10
)

async for message in consumer:
    print(f"Received: {message.body}")
    await message.ack()
```

## Producer

Create a RabbitMQ producer:

```python
from pipeflow.integrations.rabbitmq import RabbitMQProducerPipe

producer = RabbitMQProducerPipe(
    config=config,
    exchange="my-exchange",
    routing_key="my-key"
)

await producer.process({
    "message": "Hello, RabbitMQ!",
    "properties": {"content_type": "application/json"}
})
```

## Error Handling

Handle RabbitMQ-specific errors:

```python
from pipeflow.integrations.rabbitmq import RabbitMQError

try:
    await producer.process(data)
except RabbitMQError as e:
    print(f"RabbitMQ error: {e}")
```

## Testing

Use the provided test utilities:

```python
from pipeflow.testing.rabbitmq import RabbitMQTestMixin

class TestRabbitMQPipe(RabbitMQTestMixin):
    async def test_producer(self):
        producer = RabbitMQProducerPipe(self.config)
        await producer.process({"test": "data"})
        messages = await self.get_messages()
        assert len(messages) == 1
```

## Best Practices

1. Use appropriate queue configurations
2. Implement proper acknowledgments
3. Handle connection failures
4. Monitor queue metrics
5. Clean up resources properly
6. Test with realistic message volumes
