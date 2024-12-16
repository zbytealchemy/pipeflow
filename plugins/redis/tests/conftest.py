"""Test fixtures for Redis plugin."""
from typing import AsyncGenerator

import pytest
from redis.asyncio import Redis


@pytest.fixture
def redis_config() -> RedisConfig:
    """Create a test Redis configuration."""
    return RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        key="test-key",
        channel="test-channel",
        stream_name="test-stream",
        list_name="test-list",
    )


@pytest.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Create a Redis client for testing."""
    client = Redis(host="localhost", port=6379, db=0, decode_responses=True)
    try:
        await client.ping()
        yield client
    finally:
        await client.close()  # Redis client doesn't support aclose yet


@pytest.fixture(autouse=True)
async def clean_redis(redis_client: Redis) -> AsyncGenerator[None, None]:
    """Clean Redis database before and after each test."""
    await redis_client.flushdb()
    yield
    await redis_client.flushdb()
