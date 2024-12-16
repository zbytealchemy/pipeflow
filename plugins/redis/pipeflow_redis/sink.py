"""Redis sink implementation."""
import json
from typing import Any, List, Optional

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from pipeflow.core import BasePipe, PipeError

from .config import RedisConfig
from .message import RedisMessage


class RedisSinkPipe(BasePipe[RedisMessage, None]):
    """Sink pipe for Redis."""

    def __init__(self, config: RedisConfig) -> None:
        """Initialize the Redis sink pipe."""
        if not config.key and not any(
            [config.channel, config.stream_name, config.list_name]
        ):
            raise ValueError(
                "Redis configuration must include either 'key', 'channel', 'stream_name', or 'list_name'"
            )

        super().__init__()
        self.config = config
        self._redis_client: Optional[Redis[bytes]] = None
        self._pending_messages: List[Any] = []

    async def start(self) -> None:
        """Start the Redis connection."""
        if not self._redis_client:
            try:
                connection_kwargs = {
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
                await self._redis_client.ping()
            except Exception as e:
                self._redis_client = None
                raise ConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    async def stop(self) -> None:
        """Stop the sink pipe."""
        if self._redis_client:
            await self._redis_client.close()  # Redis client doesn't support aclose yet
            self._redis_client = None

    async def process(self, message: RedisMessage) -> None:
        """Send a message to Redis."""
        if not self._redis_client:
            await self.start()
            if not self._redis_client:
                raise PipeError(self, ValueError("Failed to connect to Redis"))

        try:
            if self.config.channel:
                await self._redis_client.publish(
                    self.config.channel, json.dumps(message.value)
                )
            elif self.config.stream_name:
                await self._redis_client.xadd(
                    self.config.stream_name,
                    message.value,
                    maxlen=self.config.max_entries,
                )
            elif self.config.list_name:
                await self._redis_client.rpush(
                    self.config.list_name, json.dumps(message.value)
                )
            else:
                await self._redis_client.set(message.key, json.dumps(message.value))
        except Exception as e:
            raise PipeError(self, e) from e
