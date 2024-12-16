"""Tests for Redis source pipe."""
import json

import pytest
from pipeflow_redis import RedisConfig, RedisSourcePipe
from redis.asyncio import Redis

from pipeflow.core import PipeError


@pytest.mark.asyncio
async def test_source_pubsub(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis source pipe with pub/sub."""
    # Configure for pub/sub only
    config = RedisConfig(
        **{
            **redis_config.model_dump(),
            "key": None,
            "stream_name": None,
            "list_name": None,
        }
    )
    source = RedisSourcePipe(config)

    # Start the source
    await source.start()

    # Publish a message
    channel = "test_channel"
    test_data = {"message": "test"}
    await redis_client.publish(channel, json.dumps(test_data))

    # Receive the message
    message = await source.process(None)
    assert message.value == test_data
    assert message.source == "pubsub"
    assert message.key == channel

    await source.stop()


@pytest.mark.asyncio
async def test_source_stream(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis source pipe with streams."""
    # Configure for streams only
    config = RedisConfig(
        **{**redis_config.model_dump(), "key": None, "channel": None, "list_name": None}
    )
    source = RedisSourcePipe(config)

    # Start the source
    await source.start()

    # Add a message to the stream
    stream_name = "test_stream"
    test_data = {"field1": "value1"}
    result = await redis_client.xadd(stream_name, test_data)
    assert result is not None

    # Receive the message
    messages = await redis_client.xread({stream_name: "0"})
    assert messages is not None
    assert len(messages) > 0
    assert len(messages[0][1]) > 0
    message = await source.process(None)
    assert message.value == test_data
    assert message.source == "stream"
    assert message.key == stream_name
    metadata = message.metadata
    assert metadata is not None
    assert "id" in metadata

    await source.stop()


@pytest.mark.asyncio
async def test_source_list(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis source pipe with lists."""
    # Configure for lists only
    config = RedisConfig(
        **{
            **redis_config.model_dump(),
            "key": None,
            "channel": None,
            "stream_name": None,
        }
    )
    source = RedisSourcePipe(config)

    # Start the source
    await source.start()

    # Add a message to the list
    list_name = "test_list"
    test_data = {"message": "test"}
    result = await redis_client.rpush(list_name, json.dumps(test_data))
    assert result is not None

    # Receive the message
    message = await source.process(None)
    assert message.value == test_data
    assert message.source == "list"
    assert message.key == list_name

    await source.stop()


@pytest.mark.asyncio
async def test_source_key_value(redis_config: RedisConfig, redis_client: Redis) -> None:
    """Test Redis source pipe with key-value."""
    # Configure for key-value only
    config = RedisConfig(
        **{
            **redis_config.model_dump(),
            "channel": None,
            "stream_name": None,
            "list_name": None,
        }
    )
    source = RedisSourcePipe(config)

    # Start the source
    await source.start()

    # Set a value
    key = "test_key"
    test_data = {"message": "test"}
    await redis_client.set(key, json.dumps(test_data))

    # Receive the message
    message = await source.process(None)
    assert message.value == test_data
    assert message.source == "key-value"
    assert message.key == key

    await source.stop()


@pytest.mark.asyncio
async def test_source_connection_error(redis_config: RedisConfig) -> None:
    """Test Redis source pipe with connection error."""
    # Use invalid port
    config = RedisConfig(**{**redis_config.model_dump(), "port": 6380})
    source = RedisSourcePipe(config)

    with pytest.raises(ConnectionError):
        await source.start()


@pytest.mark.asyncio
async def test_source_no_message(redis_config: RedisConfig) -> None:
    """Test Redis source pipe with no message available."""
    source = RedisSourcePipe(redis_config)
    await source.start()

    with pytest.raises(PipeError):
        await source.process(None)

    await source.stop()


@pytest.mark.asyncio
async def test_source_stream_processing(
    redis_config: RedisConfig, redis_client: Redis
) -> None:
    """Test Redis source pipe stream processing."""
    source = RedisSourcePipe(redis_config)
    await source.start()

    # Add multiple messages
    test_data = [{"message": f"test{i}"} for i in range(3)]
    list_name = "test_list"
    for data in test_data:
        result = await redis_client.rpush(list_name, json.dumps(data))
        assert result is not None

    # Process stream
    received = []
    async for message in source.process_stream():
        received.append(message)
        if len(received) == len(test_data):
            break

    # Verify messages
    assert len(received) == len(test_data)
    for i, message in enumerate(received):
        assert message.value == test_data[i]
        assert message.source == "list"
        assert message.key == list_name

    await source.stop()
