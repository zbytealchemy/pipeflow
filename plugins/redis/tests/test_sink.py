"""Tests for Redis sink pipe."""
import json

import pytest
from pipeflow_redis import RedisConfig, RedisSinkPipe
from pipeflow_redis.message import RedisMessage
from redis.asyncio import Redis

from pipeflow.core import PipeError


@pytest.mark.asyncio
async def test_sink_pubsub(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis sink pipe with pub/sub."""
    # Configure for pub/sub only
    channel = "test_channel"
    config = RedisConfig(
        **{
            **redis_config.model_dump(),
            "key": None,
            "stream_name": None,
            "list_name": None,
            "channel": channel,
        }
    )
    sink = RedisSinkPipe(config)

    # Start the sink
    await sink.start()

    # Subscribe to the channel
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    # Send a message
    test_data = {"message": "test"}
    await sink.process(RedisMessage(value=test_data, key=channel, source="pubsub"))

    # Verify message was published
    message = await pubsub.get_message(timeout=1)  # Skip subscription message
    message = await pubsub.get_message(timeout=1)
    assert message is not None
    assert json.loads(message["data"]) == {"message": "test"}

    await sink.stop()
    await pubsub.close()  # Redis pubsub doesn't support aclose yet


@pytest.mark.asyncio
async def test_sink_stream(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis sink pipe with streams."""
    # Configure for streams only
    stream_name = "test_stream"
    config = RedisConfig(
        **{
            **redis_config.model_dump(),
            "key": None,
            "channel": None,
            "list_name": None,
            "stream_name": stream_name,
        }
    )
    sink = RedisSinkPipe(config)

    await sink.start()

    # Send a message
    test_data = {"field1": "value1"}
    await sink.process(RedisMessage(value=test_data, key=stream_name, source="stream"))

    # Verify message was added to stream
    messages = await redis_client.xread({stream_name: "0"})
    assert messages is not None
    assert messages[0][1][0][1] == test_data

    await sink.stop()


@pytest.mark.asyncio
async def test_sink_list(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis sink pipe with lists."""
    # Configure for lists only
    list_name = "test_list"
    config = RedisConfig(
        **{
            **redis_config.model_dump(),
            "key": None,
            "channel": None,
            "stream_name": None,
            "list_name": list_name,
        }
    )
    sink = RedisSinkPipe(config)

    await sink.start()

    # Send a message
    test_data = {"message": "test"}
    await sink.process(RedisMessage(value=test_data, key=list_name, source="list"))

    # Verify message was added to list
    result = await redis_client.rpop(list_name)
    assert result is not None
    assert json.loads(result.decode()) == test_data

    await sink.stop()


@pytest.mark.asyncio
async def test_sink_key_value(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis sink pipe with key-value."""
    # Configure for key-value only
    key = "test_key"
    config = RedisConfig(
        **{
            **redis_config.model_dump(),
            "channel": None,
            "stream_name": None,
            "list_name": None,
            "key": key,
        }
    )
    sink = RedisSinkPipe(config)

    await sink.start()

    # Send a message
    test_data = {"message": "test"}
    await sink.process(RedisMessage(value=test_data, key=key, source="key-value"))

    # Verify value was set
    result = await redis_client.get(key)
    assert result is not None
    assert json.loads(result.decode()) == test_data

    await sink.stop()


@pytest.mark.asyncio
async def test_sink_connection_error(redis_config: RedisConfig) -> None:
    """Test Redis sink pipe with connection error."""
    config = RedisConfig(**{**redis_config.model_dump(), "port": 1234})
    sink = RedisSinkPipe(config)

    with pytest.raises(ConnectionError):
        await sink.start()


@pytest.mark.asyncio
async def test_sink_invalid_message(redis_config: RedisConfig) -> None:
    """Test Redis sink pipe with invalid message."""
    config = RedisConfig(**redis_config.model_dump())
    sink = RedisSinkPipe(config)

    with pytest.raises(PipeError):
        await sink.process(
            RedisMessage(value={"message": "test"}, key="test", source="invalid")
        )
