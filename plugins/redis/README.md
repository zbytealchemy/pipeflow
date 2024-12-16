# Pipeflow Redis Plugin

This plugin provides Redis integration for the Pipeflow data processing framework.

## Features

- Pub/Sub support
- Stream processing
- List operations
- Key-value operations
- SSL support
- Comprehensive error handling

## Installation

```bash
pip install pipeflow-redis
```

## Usage

```python
from pipeflow_redis import RedisSourcePipe, RedisSinkPipe, RedisConfig

# Create configuration
config = RedisConfig(
    host="localhost",
    port=6379,
    channel="my-channel"  # For pub/sub
)

# Create source pipe
source = RedisSourcePipe(config)

# Create sink pipe
sink = RedisSinkPipe(config)

# Use in your pipeline
async def process():
    async for message in source.process_stream():
        # Process message
        await sink.process(message)
```

## Configuration Options

- `host`: Redis host (default: "localhost")
- `port`: Redis port (default: 6379)
- `db`: Redis database number (default: 0)
- `password`: Optional Redis password
- `ssl`: Enable SSL (default: False)
- `ssl_ca_certs`: Path to CA certificate
- `ssl_certfile`: Path to client certificate
- `ssl_keyfile`: Path to client key
- `ssl_password`: Optional key password

### Operation Modes

The plugin supports different operation modes:

1. **Pub/Sub**
   ```python
   config = RedisConfig(channel="my-channel")
   ```

2. **Streams**
   ```python
   config = RedisConfig(stream_name="my-stream")
   ```

3. **Lists**
   ```python
   config = RedisConfig(list_name="my-list")
   ```

4. **Key-Value**
   ```python
   config = RedisConfig(key="my-key")
   ```

## Error Handling

The plugin includes comprehensive error handling:
- Connection retries
- Automatic reconnection
- Timeout handling
- JSON parsing error handling

## Development

```bash
# Install development dependencies
poetry install

# Run tests
poetry run pytest

# Run type checking
poetry run mypy .
```
