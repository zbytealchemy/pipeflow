"""Integration tests for Redis pipes."""
import asyncio

import pytest
from redis.asyncio import Redis

from pipeflow.integrations.redis import (
    RedisConfig,
    RedisMessage,
    RedisSinkPipe,
    RedisSourcePipe,
)


@pytest.fixture
async def redis_config():
    """Redis configuration fixture."""
    config = RedisConfig(host="localhost", port=6379, key="test-key")

    # Clean up any existing test data
    redis = Redis(host=config.host, port=config.port, decode_responses=True)
    try:
        await redis.delete(config.key)
        if config.channel:
            await redis.delete(config.channel)
    finally:
        await redis.aclose()

    yield config

    # Cleanup after tests
    redis = Redis(host=config.host, port=config.port, decode_responses=True)
    try:
        await redis.delete(config.key)
        if config.channel:
            await redis.delete(config.channel)
    finally:
        await redis.aclose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_sink_source(redis_config):
    """Test Redis sink and source pipes."""
    sink = RedisSinkPipe(redis_config)
    source = RedisSourcePipe(redis_config)

    try:
        await sink.start()
        await source.start()

        data = {"key": "value"}
        message = RedisMessage(key=redis_config.key, value=data, source="test")
        await sink.process(message)

        result = await source.process(None)
        assert result.value == data
    finally:
        await sink.stop()
        await source.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_list_operations(redis_config):
    """Test Redis list operations."""
    # Create config for list operations
    list_config = RedisConfig(
        host="localhost", port=6379, key="test-key", list_name="test-list"
    )

    # Create pipes
    sink = RedisSinkPipe(list_config)
    source = RedisSourcePipe(list_config)

    # Test data
    test_data = [
        {"id": 1, "value": "one"},
        {"id": 2, "value": "two"},
        {"id": 3, "value": "three"},
    ]

    try:
        # Send messages
        await sink.start()
        for data in test_data:
            message = RedisMessage(key=list_config.key, value=data, source="test")
            await sink.process(message)
        await sink.stop()

        # Receive messages
        received = []
        await source.start()
        for _ in range(len(test_data)):
            message = await source.process(None)
            received.append(message.value)
        await source.stop()

        # Verify (messages should be in FIFO order)
        assert len(received) == len(test_data)
        for expected, actual in zip(test_data, received):
            assert expected == actual

    finally:
        await asyncio.gather(sink.stop(), source.stop())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_pubsub(redis_config):
    """Test Redis pub/sub operations."""
    # Create config for pub/sub
    pubsub_config = RedisConfig(
        host="localhost", port=6379, key="test-key", channel="test-channel"
    )

    # Create pipes
    sink = RedisSinkPipe(pubsub_config)
    source = RedisSourcePipe(pubsub_config)

    # Test data
    test_data = {"message": "hello"}

    try:
        # Start subscriber
        await source.start()

        # Send message
        await sink.start()
        message = RedisMessage(key=pubsub_config.key, value=test_data, source="test")
        await sink.process(message)

        # Receive message
        result = await source.process(None)

        # Verify
        assert isinstance(result, RedisMessage)
        assert result.value == test_data
        assert result.source == "pubsub"

    finally:
        # Cleanup
        await source.stop()
        await sink.stop()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_error_handling(redis_config):
    """Test Redis error handling."""
    # Create pipe with invalid config (using non-existent port)
    invalid_config = RedisConfig(
        host="localhost", port=65535, key="test-key"  # Invalid port number
    )
    sink = RedisSinkPipe(invalid_config)

    # Verify error handling
    with pytest.raises(ConnectionError):
        await sink.start()
