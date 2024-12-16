"""Redis source implementation."""
import asyncio
import json
from typing import Any, AsyncIterator, Optional, TypedDict

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from pipeflow.core import BasePipe, PipeError

from .config import RedisConfig
from .message import RedisMessage


class RedisConnectionKwargs(TypedDict, total=False):
    """Type hints for Redis connection kwargs."""

    host: str
    port: int
    db: int
    password: Optional[str]
    decode_responses: bool
    ssl: bool
    ssl_ca_certs: Optional[str]
    ssl_certfile: Optional[str]
    ssl_keyfile: Optional[str]
    ssl_password: Optional[str]


class RedisSourcePipe(BasePipe[None, RedisMessage]):
    """Source pipe for Redis."""

    def __init__(self, config: RedisConfig) -> None:
        """Initialize the Redis source pipe."""
        if not config.key and not any(
            [config.channel, config.stream_name, config.list_name]
        ):
            raise ValueError(
                "Redis configuration must include either 'key', 'channel', 'stream_name', or 'list_name'"
            )

        super().__init__()
        self.config = config
        self._redis_client: Optional[Redis[bytes]] = None
        self.pubsub: Optional[Any] = None
        self._retries: int = 3

    async def start(self) -> None:
        """Start the Redis connection."""
        if not self._redis_client:
            try:
                connection_kwargs: RedisConnectionKwargs = {
                    "host": self.config.host,
                    "port": self.config.port,
                    "db": self.config.db,
                    "password": self.config.password,
                }

                if self.config.ssl:
                    connection_kwargs.update(
                        {
                            "ssl": self.config.ssl,
                            "ssl_ca_certs": self.config.ssl_ca_certs,
                            "ssl_certfile": self.config.ssl_certfile,
                            "ssl_keyfile": self.config.ssl_keyfile,
                            "ssl_password": self.config.ssl_password,
                        }
                    )

                pool = ConnectionPool(max_connections=None, **connection_kwargs)
                self._redis_client = Redis(connection_pool=pool)

                if self._redis_client:
                    await self._redis_client.ping()
                    if self.config.channel:
                        self.pubsub = self._redis_client.pubsub()
                        await self.pubsub.subscribe(self.config.channel)
            except RedisError as e:
                self._redis_client = None
                raise ConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    async def stop(self) -> None:
        """Stop the source pipe."""
        if self.pubsub:
            await self.pubsub.aclose()
            self.pubsub = None
        if self._redis_client:
            await self._redis_client.close()  # Redis client doesn't support aclose yet
            self._redis_client = None

    async def process(self, _: None) -> RedisMessage:
        """Process messages from Redis."""
        if not self._redis_client:
            await self.start()
            if not self._redis_client:
                raise PipeError(self, ValueError("Failed to connect to Redis"))

        for attempt in range(self._retries):
            if self.config.channel and self.pubsub:
                message = await self.pubsub.get_message()
                if message and message["type"] == "message":
                    try:
                        value = json.loads(message["data"])
                    except json.JSONDecodeError:
                        value = message["data"]
                    return RedisMessage(
                        key=self.config.channel,
                        value=value,
                        source="pubsub",
                    )

            if self.config.stream_name and self._redis_client:
                messages = await self._redis_client.xread(
                    {self.config.stream_name: "0"}, count=1
                )
                if messages:
                    stream_messages = messages[0][1]
                    if stream_messages:
                        message_id, message_data = stream_messages[0]
                        return RedisMessage(
                            key=self.config.stream_name,
                            value=message_data,
                            source="stream",
                            metadata={"id": message_id},
                        )

            if self.config.list_name and self._redis_client:
                message = await self._redis_client.lpop(self.config.list_name)
                if message:
                    try:
                        value = json.loads(message)
                    except json.JSONDecodeError:
                        value = message
                    return RedisMessage(
                        key=self.config.list_name,
                        value=value,
                        source="list",
                    )

            if self.config.key and self._redis_client:
                message = await self._redis_client.get(self.config.key)
                if message:
                    try:
                        value = json.loads(message)
                    except json.JSONDecodeError:
                        value = message
                    return RedisMessage(
                        key=self.config.key,
                        value=value,
                        source="key-value",
                    )

            await asyncio.sleep(0.1)

        raise PipeError(self, ValueError("No message available after retries"))

    async def process_stream(self) -> AsyncIterator[RedisMessage]:
        """Process a stream of messages from Redis."""
        if not self._redis_client:
            await self.start()
            if not self._redis_client:
                raise PipeError(self, ValueError("Failed to connect to Redis"))

        try:
            while True:
                try:
                    message = await self.process(None)
                    yield message
                except PipeError:
                    await asyncio.sleep(0.1)
        except Exception as e:
            await self.stop()
            raise RuntimeError(f"Failed to process Redis stream: {str(e)}") from e
