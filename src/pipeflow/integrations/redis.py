"""Redis integration for pipeflow."""
import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional, TypedDict

from pydantic import ConfigDict
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from ..core.message import Message
from ..core.pipe import BasePipe, PipeConfig, PipeError


class RedisConfig(PipeConfig):
    """Configuration for Redis pipes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_password: Optional[str] = None
    channel: Optional[str] = None
    key_prefix: str = ""
    encoding: str = "utf-8"
    key: str
    stream_name: Optional[str] = None
    list_name: Optional[str] = None
    consumer_group: Optional[str] = None
    consumer_name: Optional[str] = None
    max_entries: int = 1000


class RedisMessage(Message):
    """A message from Redis."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    key: str
    value: Any
    source: str
    metadata: Optional[Dict[str, Any]] = None


class RedisConnectionKwargs(TypedDict, total=False):
    """Type hints for Redis connection kwargs."""

    host: str
    port: int
    db: int
    password: Optional[str]
    decode_responses: bool
    ssl_ca_certs: Optional[str]
    ssl_certfile: Optional[str]
    ssl_keyfile: Optional[str]
    ssl_password: Optional[str]
    socket_timeout: Optional[float]
    socket_connect_timeout: Optional[float]


class RedisSourcePipe(BasePipe[None, RedisMessage]):
    """A pipe that reads messages from Redis."""

    def __init__(self, config: RedisConfig) -> None:
        """Initialize the Redis source pipe."""
        if not config.key:
            raise ValueError("Redis configuration must include 'key'")

        super().__init__()
        self.config = config
        self.redis: Optional[Redis[bytes]] = None
        self.pubsub: Optional[Any] = None
        self._retries: int = 3

    async def start(self) -> None:
        """Start the Redis connection."""
        if not self.redis:
            try:
                connection_kwargs: RedisConnectionKwargs = {
                    "host": self.config.host,
                    "port": self.config.port,
                    "db": self.config.db,
                    "password": self.config.password,
                    "decode_responses": True,
                }

                # Only add SSL-related parameters if SSL is enabled
                if self.config.ssl:
                    connection_kwargs.update(
                        {
                            "ssl_ca_certs": self.config.ssl_ca_certs,
                            "ssl_certfile": self.config.ssl_certfile,
                            "ssl_keyfile": self.config.ssl_keyfile,
                            "ssl_password": self.config.ssl_password,
                        }
                    )

                pool = ConnectionPool(**connection_kwargs)
                self.redis = Redis(connection_pool=pool)

                if self.redis:
                    await self.redis.ping()
                    if self.config.channel:
                        self.pubsub = self.redis.pubsub()
                        await self.pubsub.subscribe(self.config.channel)
            except RedisError as e:
                self.redis = None
                raise ConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    async def stop(self) -> None:
        """Stop the Redis connection."""
        if self.pubsub:
            await self.pubsub.aclose()
            self.pubsub = None
        if self.redis:
            await self.redis.aclose()  # type: ignore[attr-defined]
            self.redis = None

    async def process(self, _: None) -> RedisMessage:
        """Receive a message from Redis.

        Args:
            _: Not used

        Returns:
            Received message

        Raises:
            PipeError: If no message is available after retries
        """
        if not self.redis:
            await self.start()
            if not self.redis:
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

            if self.config.stream_name and self.redis:
                messages = await self.redis.xread(
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

            if self.config.list_name and self.redis:
                message = await self.redis.lpop(self.config.list_name)
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

            # Handle regular key-value operation if no special modes are configured
            if not any(
                [self.config.channel, self.config.stream_name, self.config.list_name]
            ):
                message = await self.redis.get(self.config.key)
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

            await asyncio.sleep(0.1)  # Short delay between retries

        raise PipeError(self, ValueError("No message available after retries"))

    async def process_stream(self) -> AsyncIterator[RedisMessage]:
        """Process a stream of messages from Redis.

        Yields:
            Messages from Redis
        """
        if not self.redis:
            await self.start()
            if not self.redis:
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


class RedisSinkPipe(BasePipe[RedisMessage, None]):
    """A pipe that writes messages to Redis."""

    def __init__(self, config: RedisConfig) -> None:
        """Initialize the Redis sink pipe."""
        if not config.key:
            raise ValueError("Redis configuration must include 'key'")

        super().__init__()
        self.config = config
        self.redis: Optional[Redis[bytes]] = None
        self._pending_messages: List[Any] = []

    async def start(self) -> None:
        """Start the Redis connection."""
        if not self.redis:
            try:
                connection_kwargs: RedisConnectionKwargs = {
                    "host": self.config.host,
                    "port": self.config.port,
                    "db": self.config.db,
                    "password": self.config.password,
                    "decode_responses": True,
                    "socket_timeout": 1.0,  # 1 second timeout
                    "socket_connect_timeout": 1.0,  # 1 second connect timeout
                }

                # Only add SSL-related parameters if SSL is enabled
                if self.config.ssl:
                    connection_kwargs.update(
                        {
                            "ssl_ca_certs": self.config.ssl_ca_certs,
                            "ssl_certfile": self.config.ssl_certfile,
                            "ssl_keyfile": self.config.ssl_keyfile,
                            "ssl_password": self.config.ssl_password,
                        }
                    )

                pool = ConnectionPool(**connection_kwargs)
                self.redis = Redis(connection_pool=pool)
                # Test connection with timeout
                await asyncio.wait_for(self.redis.ping(), timeout=1.0)
            except (Exception, asyncio.TimeoutError) as e:
                self.redis = None
                raise ConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    async def stop(self) -> None:
        """Stop the Redis connection."""
        if self.redis:
            await self.redis.aclose()  # type: ignore[attr-defined]
            self.redis = None

    async def process(self, message: RedisMessage) -> None:
        """Send a message to Redis.

        Args:
            message: Message to send

        Raises:
            PipeError: If message cannot be sent
        """
        if not self.redis:
            await self.start()
            if not self.redis:
                raise PipeError(self, ValueError("Failed to connect to Redis"))

        try:
            if self.config.channel:
                await self.redis.publish(self.config.channel, json.dumps(message.value))
            elif self.config.stream_name:
                await self.redis.xadd(
                    self.config.stream_name,
                    message.value,
                    maxlen=self.config.max_entries,
                )
            elif self.config.list_name:
                await self.redis.rpush(self.config.list_name, json.dumps(message.value))
            else:
                await self.redis.set(message.key, json.dumps(message.value))
        except Exception as e:
            raise PipeError(self, e) from e
