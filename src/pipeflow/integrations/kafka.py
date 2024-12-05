"""Kafka integration for pipeflow."""
import asyncio
import json
import ssl
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from kafka.errors import KafkaError  # type: ignore[import-untyped]
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, TopicPartition
from pydantic import BaseModel, ConfigDict

from pipeflow.core import BasePipe, ConfigurablePipe, PipeConfig, PipeError


class KafkaConfig(PipeConfig):
    """Configuration for Kafka pipes."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    bootstrap_servers: Union[str, List[str]] = "localhost:9092"
    topic: str
    group_id: Optional[str] = None
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True
    max_poll_records: int = 500
    consumer_timeout_ms: int = 1000
    client_id: Optional[str] = None
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_plain_username: Optional[str] = None
    sasl_plain_password: Optional[str] = None
    ssl_cafile: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_password: Optional[str] = None
    consumer_group: Optional[str] = None  # Added for backward compatibility
    session_timeout_ms: int = 10000  # 10 seconds
    heartbeat_interval_ms: int = 3000  # 3 seconds
    max_poll_interval_ms: int = 300000  # 5 minutes
    rebalance_timeout_ms: int = 30000  # 30 seconds


class KafkaMessage(BaseModel):
    """A message from Kafka."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    topic: str
    partition: int
    offset: int
    timestamp: Optional[int] = None
    timestamp_type: Optional[Union[str, int]] = None
    headers: Optional[List[tuple[str, bytes]]] = None
    key: Optional[bytes] = None
    value: Any


class KafkaSourcePipe(ConfigurablePipe[None, KafkaMessage, KafkaConfig]):
    """Pipe that reads messages from Kafka."""

    def __init__(self, config: KafkaConfig) -> None:
        """Initialize the Kafka source pipe.

        Args:
            config: Kafka configuration
        """
        super().__init__(config)
        self.config = config
        self.consumer: Optional[AIOKafkaConsumer] = None

    async def start(self) -> None:
        """Start the Kafka consumer.

        Raises:
            PipeError: If there is an error starting the consumer
        """
        if self.consumer is None:
            ssl_context: Optional[ssl.SSLContext] = None
            if self.config.security_protocol == "SSL":
                ssl_context = ssl.create_default_context(
                    cafile=self.config.ssl_cafile,
                )
                if self.config.ssl_certfile:
                    ssl_context.load_cert_chain(
                        certfile=self.config.ssl_certfile,
                        keyfile=self.config.ssl_keyfile,
                        password=self.config.ssl_password,
                    )

            # Set up consumer
            self.consumer = AIOKafkaConsumer(
                bootstrap_servers=self.config.bootstrap_servers,
                client_id=self.config.client_id,
                security_protocol=self.config.security_protocol,
                sasl_mechanism=self.config.sasl_mechanism,
                sasl_plain_username=self.config.sasl_plain_username,
                sasl_plain_password=self.config.sasl_plain_password,
                ssl_context=ssl_context,
                consumer_timeout_ms=self.config.consumer_timeout_ms,
                auto_offset_reset=self.config.auto_offset_reset,
                enable_auto_commit=self.config.enable_auto_commit,
                max_poll_records=self.config.max_poll_records,
                value_deserializer=lambda v: json.loads(v.decode("utf-8"))
                if v
                else None,
                key_deserializer=lambda k: k if k else None,
                session_timeout_ms=self.config.session_timeout_ms,
                heartbeat_interval_ms=self.config.heartbeat_interval_ms,
                max_poll_interval_ms=self.config.max_poll_interval_ms,
                rebalance_timeout_ms=self.config.rebalance_timeout_ms,
                request_timeout_ms=30000,  # 30 seconds
            )

            try:
                await self.consumer.start()

                # Subscribe to topic
                self.consumer.subscribe([self.config.topic])

                # Wait for assignment
                deadline = asyncio.get_event_loop().time() + 10
                while asyncio.get_event_loop().time() < deadline:
                    assignment = self.consumer.assignment()
                    if assignment:
                        # Seek to beginning if auto_offset_reset is earliest
                        if self.config.auto_offset_reset == "earliest":
                            for partition in assignment:
                                await self.consumer.seek_to_beginning(partition)
                        break
                    await asyncio.sleep(0.1)
                else:
                    raise PipeError(self, RuntimeError(f"Timeout waiting for topic {self.config.topic}"))

            except Exception as e:
                if self.consumer:
                    try:
                        await self.consumer.stop()
                    except Exception:
                        pass
                    self.consumer = None
                raise PipeError(self, e)

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        if self.consumer:
            try:
                await self.consumer.stop()
            except Exception:
                pass
            finally:
                self.consumer = None

    async def process(self, _: None) -> KafkaMessage:
        """Receive a message from Kafka.

        Args:
            _: Not used

        Returns:
            Received message

        Raises:
            PipeError: If consumer is not started or no message is available
        """
        if self.consumer is None:
            await self.start()

        if not self.consumer:
            raise PipeError(self, RuntimeError("Consumer not started"))

        try:
            message = await self.consumer.getone()
            return KafkaMessage(
                topic=message.topic,
                partition=message.partition,
                offset=message.offset,
                timestamp=message.timestamp,
                timestamp_type=message.timestamp_type,
                headers=message.headers,
                key=message.key,
                value=message.value,
            )
        except Exception as e:
            raise PipeError(self, e)

    async def process_stream(self) -> AsyncIterator[KafkaMessage]:
        """Process a stream of messages from Kafka.

        Yields:
            Messages from Kafka

        Raises:
            PipeError: If consumer is not started
        """
        if self.consumer is None:
            await self.start()

        if not self.consumer:
            raise PipeError(self, RuntimeError("Consumer not started"))

        try:
            async for message in self.consumer:
                yield KafkaMessage(
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    timestamp=message.timestamp,
                    timestamp_type=message.timestamp_type,
                    headers=message.headers,
                    key=message.key,
                    value=message.value,
                )
        finally:
            await self.stop()


class KafkaSinkPipe(ConfigurablePipe[Any, None, KafkaConfig]):
    """Pipe that writes messages to Kafka."""

    def __init__(self, config: KafkaConfig) -> None:
        """Initialize the Kafka sink pipe.

        Args:
            config: Kafka configuration
        """
        super().__init__(config)
        self.config = config
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Start the Kafka producer.

        Raises:
            PipeError: If there is an error starting the producer
        """
        if self.producer is None:
            ssl_context: Optional[ssl.SSLContext] = None
            if self.config.security_protocol == "SSL":
                ssl_context = ssl.create_default_context(
                    cafile=self.config.ssl_cafile,
                )
                if self.config.ssl_certfile:
                    ssl_context.load_cert_chain(
                        certfile=self.config.ssl_certfile,
                        keyfile=self.config.ssl_keyfile,
                        password=self.config.ssl_password,
                    )

            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                client_id=self.config.client_id,
                security_protocol=self.config.security_protocol,
                sasl_mechanism=self.config.sasl_mechanism,
                sasl_plain_username=self.config.sasl_plain_username,
                sasl_plain_password=self.config.sasl_plain_password,
                ssl_context=ssl_context,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                request_timeout_ms=30000,  # 30 seconds
            )

            try:
                await self.producer.start()
            except Exception as e:
                if self.producer:
                    try:
                        await self.producer.stop()
                    except Exception:
                        pass
                    self.producer = None
                raise PipeError(self, e)

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self.producer:
            try:
                await self.producer.stop()
            except Exception:
                pass
            finally:
                self.producer = None

    async def process(self, data: Any) -> None:
        """Send a message to Kafka.

        Args:
            data: Message to send

        Raises:
            PipeError: If producer is not started
        """
        if self.producer is None:
            await self.start()

        if not self.producer:
            raise PipeError(self, RuntimeError("Producer not started"))

        try:
            await self.producer.send_and_wait(self.config.topic, value=data)
        except Exception as e:
            raise PipeError(self, e)
