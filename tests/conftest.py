"""Test configuration and fixtures."""
import asyncio
import os
import warnings
from typing import Any, AsyncGenerator, Callable, Generator, List, Optional

import aio_pika
import aioboto3
import pytest
from aiokafka import AIOKafkaProducer
from pydantic import ConfigDict
from pydantic._internal._config import PydanticDeprecatedSince20
from redis.asyncio import Redis

from pipeflow import BasePipe
from pipeflow.streams import Stream, StreamConfig

# Supress PydanticDeprecatedSince20 warning
warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def redis_client() -> AsyncGenerator[Redis, None]:
    """Create a Redis client for testing."""
    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
    yield client
    await client.close()


@pytest.fixture
async def rabbitmq_connection() -> AsyncGenerator[aio_pika.Connection, None]:
    """Create a RabbitMQ connection for testing."""
    connection = await aio_pika.connect_robust(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        login=os.getenv("RABBITMQ_USER", "guest"),
        password=os.getenv("RABBITMQ_PASSWORD", "guest"),
    )
    yield connection
    await connection.close()


@pytest.fixture
async def kafka_producer() -> AsyncGenerator[AIOKafkaProducer, None]:
    """Create a Kafka producer for testing."""
    producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    )
    await producer.start()
    yield producer
    await producer.stop()


# @pytest.fixture
# def aws_sqs_client() -> Generator[boto3.client, None, None]:
#     """Create a LocalStack SQS client for testing."""
#     endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
#     client = boto3.client(
#         "sqs",
#         endpoint_url=endpoint_url,
#         region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
#         aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
#         aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
#     )
#     yield client

@pytest.fixture
async def aws_sqs_client() -> AsyncGenerator[aioboto3.Session.client, None]:
    """Create a LocalStack SQS client for testing."""
    endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    session = aioboto3.Session()
    async with session.client(
        "sqs",
        endpoint_url=endpoint_url,
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    ) as client:
        yield client


class MockPipe(BasePipe[Any, Any]):
    """Mock pipe for testing."""

    def __init__(
        self,
        return_value: Optional[Callable] = None,
        error: Optional[Exception] = None,
        delay: float = 0,
    ):
        """Initialize mock pipe."""
        super().__init__()  # Initialize BasePipe
        self.return_value = return_value or (lambda x: x)
        self.error = error
        self.delay = delay
        self.calls: List[Any] = []

    async def process(self, input_data: Any) -> Any:
        """Process input data."""
        self.calls.append(input_data)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.return_value(input_data)

    async def __call__(self, input_data: Any) -> Any:
        """Call the pipe."""
        return await self.process(input_data)


@pytest.fixture
def mock_pipe():
    """Mock pipe fixture."""

    def _mock_pipe(
        return_value: Optional[Callable] = None,
        error: Optional[Exception] = None,
        delay: float = 0,
    ) -> MockPipe:
        return MockPipe(return_value, error, delay)

    return _mock_pipe


class MockAsyncIterator:
    """Mock async iterator for testing."""

    def __init__(self, items: List[Any], delay: float = 0):
        """Initialize mock iterator."""
        self.items = items.copy()  # Make a copy to avoid modifying the original
        self.delay = delay

    def __aiter__(self):
        """Return self as async iterator."""
        return self

    async def __anext__(self):
        """Get next item from stream."""
        if not self.items:
            raise StopAsyncIteration
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.items.pop(0)


class MockStream(Stream[Any]):
    """Mock stream for testing."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self, items: List[Any], config: Optional[StreamConfig] = None, delay: float = 0
    ):
        """Initialize mock stream."""
        source = MockAsyncIterator(items, delay)
        super().__init__(source, config or StreamConfig())


@pytest.fixture
def mock_stream():
    """Mock stream fixture."""

    def _mock_stream(
        items: List[Any],
        config: Optional[StreamConfig] = None,
        delay: float = 0,
    ) -> MockStream:
        return MockStream(items, config, delay)

    return _mock_stream
