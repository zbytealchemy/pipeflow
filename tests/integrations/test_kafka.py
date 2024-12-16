"""Tests for Kafka integration."""
import asyncio
import uuid

import pytest
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, UnknownTopicOrPartitionError

from pipeflow.core import PipeError
from pipeflow.integrations.kafka import KafkaConfig, KafkaSinkPipe, KafkaSourcePipe


async def wait_for_topic(config: KafkaConfig, exists: bool = True, timeout: int = 10):
    """Wait for topic to exist or not exist.

    Args:
        config: Kafka configuration
        exists: If True, wait for topic to exist, otherwise wait for it to not exist
        timeout: Timeout in seconds
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        consumer = AIOKafkaConsumer(
            bootstrap_servers=config.bootstrap_servers,
            request_timeout_ms=1000,
        )
        try:
            await consumer.start()
            topics = await consumer.topics()
            if (config.topic in topics) == exists:
                return
        except Exception:
            pass
        finally:
            await consumer.stop()
        await asyncio.sleep(0.1)
    raise TimeoutError(
        f"Timeout waiting for topic {config.topic} to {'exist' if exists else 'not exist'}"
    )


@pytest.fixture
async def kafka_config():
    """Fixture for Kafka configuration."""
    topic = f"test-topic-{uuid.uuid4()}"
    config = KafkaConfig(
        bootstrap_servers="localhost:9092",
        topic=topic,
        auto_offset_reset="earliest",  # Start from beginning
        consumer_timeout_ms=5000,  # 5 seconds
        request_timeout_ms=5000,  # 5 seconds
    )

    # Verify Kafka is running
    producer = AIOKafkaProducer(
        bootstrap_servers=config.bootstrap_servers,
        request_timeout_ms=5000,
    )
    try:
        await producer.start()
        await producer.stop()
    except Exception as e:
        pytest.skip(f"Kafka server is not available: {e}")

    # Create topic using synchronous admin client
    admin = KafkaAdminClient(
        bootstrap_servers=config.bootstrap_servers,
        request_timeout_ms=5000,
    )
    try:
        admin.create_topics(
            [NewTopic(name=topic, num_partitions=1, replication_factor=1)]
        )
    except TopicAlreadyExistsError:
        pass
    finally:
        admin.close()

    # Wait for topic to be created
    try:
        await wait_for_topic(config, exists=True)
    except TimeoutError as e:
        pytest.skip(f"Failed to create topic: {e}")

    yield config

    # Cleanup topic after tests
    admin = KafkaAdminClient(
        bootstrap_servers=config.bootstrap_servers,
        request_timeout_ms=5000,
    )
    try:
        admin.delete_topics([topic])
        await wait_for_topic(config, exists=False)
    except (UnknownTopicOrPartitionError, TimeoutError):
        pass  # Topic already deleted or timeout waiting for deletion
    finally:
        admin.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kafka_sink_source(kafka_config):
    """Test Kafka sink and source pipes."""
    sink = KafkaSinkPipe(kafka_config)
    source = KafkaSourcePipe(kafka_config)

    try:
        # Start producer
        await sink.start()

        # Send test message and wait for it to be sent
        message = {"key": "value"}
        await sink.process(message)

        # Start consumer
        await source.start()

        # Process message with timeout
        try:
            result = await asyncio.wait_for(source.process(None), timeout=10)
            assert result.value == message
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for message")

    finally:
        await asyncio.gather(
            source.stop(),
            sink.stop(),
            return_exceptions=True,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kafka_stream_processing(kafka_config):
    """Test Kafka stream processing."""
    # Create pipes
    sink = KafkaSinkPipe(kafka_config)
    source = KafkaSourcePipe(kafka_config)

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
            await sink.process(data)
        await sink.stop()

        # Receive messages with timeout
        received = []

        async def receive_messages():
            async for message in source.process_stream():
                received.append(message.value)
                if len(received) == len(test_data):
                    break

        try:
            await asyncio.wait_for(receive_messages(), timeout=10)
        except asyncio.TimeoutError:
            pytest.fail("Timeout waiting for messages")

        # Verify
        assert len(received) == len(test_data)
        for expected, actual in zip(test_data, received):
            assert expected == actual

    finally:
        await asyncio.gather(
            sink.stop(),
            source.stop(),
            return_exceptions=True,
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kafka_error_handling(kafka_config):
    """Test Kafka error handling."""
    # Create pipe with invalid config
    invalid_config = KafkaConfig(
        bootstrap_servers="invalid:9092",
        topic="test-topic",
        consumer_timeout_ms=1000,
    )
    sink = KafkaSinkPipe(invalid_config)

    # Verify error handling
    with pytest.raises(PipeError):
        await sink.process({"key": "value"})
