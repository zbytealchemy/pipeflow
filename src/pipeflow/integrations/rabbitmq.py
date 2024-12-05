"""RabbitMQ integration for Pipeflow."""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, Optional, Union, cast

import aio_pika
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection, AbstractChannel, AbstractQueue
from aio_pika.pool import Pool
from pydantic import BaseModel, ConfigDict

from ..core.message import Message
from ..core.pipe import BasePipe, PipeConfig


class RabbitMQConfig(PipeConfig):
    """Configuration for RabbitMQ pipes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    vhost: str = "/"
    exchange: str = ""
    queue: str = ""
    routing_key: str = ""
    exchange_type: str = "direct"
    durable: bool = True
    arguments: Optional[Dict[str, Any]] = None

    @property
    def url(self) -> str:
        """Get the RabbitMQ connection URL."""
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/{self.vhost}"


class RabbitMQMessage(Message):
    """A message from RabbitMQ."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    body: Any
    routing_key: str = ""
    exchange: str = ""
    content_type: Optional[str] = None
    content_encoding: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    delivery_mode: Optional[int] = None
    priority: Optional[int] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    expiration: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: Optional[int] = None
    type: Optional[str] = None
    user_id: Optional[str] = None
    app_id: Optional[str] = None

    @classmethod
    def from_aio_pika(cls, message: AbstractIncomingMessage) -> "RabbitMQMessage":
        """Create a RabbitMQMessage from an aio_pika message."""
        expiration = str(message.expiration) if message.expiration is not None else None
        timestamp = int(message.timestamp.timestamp()) if message.timestamp else None

        return cls(
            body=message.body,
            routing_key=message.routing_key or "",
            exchange=message.exchange or "",
            content_type=message.content_type,
            content_encoding=message.content_encoding,
            headers=message.headers,
            delivery_mode=message.delivery_mode,
            priority=message.priority,
            correlation_id=message.correlation_id,
            reply_to=message.reply_to,
            expiration=expiration,
            message_id=message.message_id,
            timestamp=timestamp,
            type=message.type,
            user_id=message.user_id,
            app_id=message.app_id,
            value=message.body
        )

    def to_aio_pika_message(self) -> aio_pika.Message:
        """Convert to an aio_pika message."""
        # Convert expiration from string to float if present
        expiration_float: Optional[float] = float(self.expiration) if self.expiration is not None else None
        
        return aio_pika.Message(
            body=self.body,
            content_type=self.content_type,
            content_encoding=self.content_encoding,
            headers=self.headers,
            delivery_mode=self.delivery_mode,
            priority=self.priority,
            correlation_id=self.correlation_id,
            reply_to=self.reply_to,
            expiration=expiration_float,
            message_id=self.message_id,
            timestamp=datetime.fromtimestamp(self.timestamp) if self.timestamp else None,
            type=self.type,
            user_id=self.user_id,
            app_id=self.app_id,
        )


class RabbitMQSourcePipe(BasePipe[None, RabbitMQMessage]):
    """A pipe that reads messages from RabbitMQ.

    Example:
        >>> config = RabbitMQConfig(
        ...     host="localhost",
        ...     port=5672,
        ...     username="guest",
        ...     password="guest",
        ...     vhost="/",
        ...     queue="my-queue"
        ... )
        >>> source = RabbitMQSourcePipe(config)
        >>> async for message in source.process_stream():
        ...     print(message.body)
    """

    def __init__(self, config: RabbitMQConfig) -> None:
        """Initialize the RabbitMQ source pipe."""
        super().__init__()
        self.name = config.name
        self.config = config
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._queue: Optional[AbstractQueue] = None
        self._consumer_tag: Optional[str] = None

    async def start(self) -> None:
        """Start consuming messages from RabbitMQ."""
        if self._connection is None:
            self._connection = await aio_pika.connect_robust(
                self.config.url,
                client_properties={"connection_name": self.name},
            )

        if self._channel is None:
            self._channel = await self._connection.channel()

        if self.config.exchange:
            # Declare exchange if specified
            exchange = await self._channel.declare_exchange(
                self.config.exchange,
                type=self.config.exchange_type or "direct",
                durable=self.config.durable,
            )

            # Declare queue and bind to exchange
            self._queue = await self._channel.declare_queue(
                self.config.queue,
                durable=self.config.durable,
            )
            await self._queue.bind(
                exchange=exchange,
                routing_key=self.config.routing_key or self.config.queue,
            )
        else:
            # Just declare queue if no exchange specified
            self._queue = await self._channel.declare_queue(
                self.config.queue,
                durable=self.config.durable,
            )

    async def process_stream(self) -> AsyncIterator[RabbitMQMessage]:
        """Process a stream of messages from RabbitMQ.

        Yields:
            RabbitMQ messages

        Raises:
            RuntimeError: If queue is not initialized
            Exception: If there is an error processing messages
        """
        if not self._channel or not self._queue:
            await self.start()
            if not self._channel or not self._queue:
                raise RuntimeError("Channel or queue not initialized")

        async with self._queue.iterator() as queue_iter:
            async for message in queue_iter:
                try:
                    yield RabbitMQMessage.from_aio_pika(message)
                    await message.ack()
                except Exception as e:
                    await message.reject(requeue=True)
                    raise RuntimeError(f"Failed to process message: {str(e)}") from e

    async def process(self, _: None) -> RabbitMQMessage:
        """Process a single message from RabbitMQ.

        Args:
            _: Not used

        Returns:
            RabbitMQMessage: The next message from the queue

        Raises:
            RuntimeError: If no message is available or if there is an error
        """
        async for message in self.process_stream():
            return message
        raise RuntimeError("No message available")

    async def stop(self) -> None:
        """Stop consuming messages from RabbitMQ."""
        if self._channel:
            await self._channel.close()
            self._channel = None

        if self._connection:
            await self._connection.close()
            self._connection = None

        self._queue = None


class RabbitMQSinkPipe(BasePipe[RabbitMQMessage, None]):
    """A pipe that writes messages to RabbitMQ.

    Example:
        >>> config = RabbitMQConfig(
        ...     host="localhost",
        ...     port=5672,
        ...     username="guest",
        ...     password="guest",
        ...     vhost="/",
        ...     queue="my-queue"
        ... )
        >>> sink = RabbitMQSinkPipe(config)
        >>> await sink({"key": "value"})
    """

    def __init__(self, config: RabbitMQConfig) -> None:
        """Initialize the RabbitMQ sink pipe."""
        super().__init__()
        self.name = config.name
        self.config = config
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[AbstractChannel] = None
        self._exchange: Optional[str] = None

    async def start(self) -> None:
        """Start the RabbitMQ producer.

        Raises:
            RuntimeError: If there is an error starting the producer
        """
        if self._connection is None:
            try:
                self._connection = await aio_pika.connect_robust(
                    host=self.config.host,
                    port=self.config.port,
                    login=self.config.username,
                    password=self.config.password,
                    virtualhost=self.config.vhost,
                )
                self._channel = await self._connection.channel()

                if self.config.exchange:
                    exchange = await self._channel.declare_exchange(
                        self.config.exchange,
                        type=aio_pika.ExchangeType.DIRECT,
                        durable=True,
                        auto_delete=False,
                        arguments=self.config.arguments,
                    )
                    self._exchange = exchange.name

                    await self._channel.declare_queue(
                        self.config.queue,
                        durable=True,
                        auto_delete=False,
                        arguments=self.config.arguments,
                    )
                else:
                    await self._channel.declare_queue(
                        self.config.queue,
                        durable=True,
                        auto_delete=False,
                        arguments=self.config.arguments,
                    )
            except Exception as e:
                if self._connection:
                    try:
                        await self._connection.close()
                    except Exception:
                        pass
                    self._connection = None
                    self._channel = None
                    self._exchange = None
                raise RuntimeError(f"Failed to start RabbitMQ producer: {str(e)}")

    async def stop(self) -> None:
        """Stop the RabbitMQ producer."""
        if self._connection:
            try:
                await self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None
                self._channel = None
                self._exchange = None

    async def process(self, data: RabbitMQMessage) -> None:
        """Send a message to RabbitMQ.

        Args:
            data: Message to send

        Raises:
            RuntimeError: If channel is not initialized or if there is an error sending the message
        """
        if not self._channel:
            await self.start()
            if not self._channel:
                raise RuntimeError("Channel not initialized")

        try:
            message = data.to_aio_pika_message()
            await self._channel.default_exchange.publish(
                message,
                routing_key=data.routing_key or self.config.routing_key or self.config.queue,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to send message: {str(e)}") from e
