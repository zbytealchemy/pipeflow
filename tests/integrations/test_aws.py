"""Tests for AWS integrations."""
import asyncio
from typing import AsyncIterator

import aioboto3
import pytest

from pipeflow.integrations.aws import SQSConfig, SQSMessage, SQSSinkPipe, SQSSourcePipe


@pytest.fixture
async def sqs_config():
    """Fixture for SQS configuration."""
    config = SQSConfig(
        queue_url="http://localhost:4566/000000000000/test-queue",
        region_name="us-east-1",
        # LocalStack credentials
        aws_access_key_id="test",
        aws_secret_access_key="test",
        endpoint_url="http://localhost:4566",  # LocalStack endpoint
    )

    # Create queue if it doesn't exist
    session = aioboto3.Session()
    async with session.client(
        "sqs",
        endpoint_url=config.endpoint_url,
        region_name=config.region_name,
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
    ) as client:
        try:
            await client.create_queue(QueueName="test-queue")
            # Purge the queue to ensure it's empty
            await client.purge_queue(QueueUrl=config.queue_url)
        except client.exceptions.QueueNameExists:
            # Queue exists, purge it
            await client.purge_queue(QueueUrl=config.queue_url)
        except Exception as e:
            print(f"Error setting up queue: {e}")

    return config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sqs_sink_source(sqs_config):
    """Test SQS sink and source pipes."""
    # Create pipes
    sink = SQSSinkPipe(sqs_config)
    source = SQSSourcePipe(sqs_config)

    # Test data
    test_data = {"key": "value"}

    try:
        # Send message
        await sink.start()
        await sink.process(test_data)
        await sink.stop()

        # Receive message
        await source.start()
        message = await source.process(None)
        await source.stop()

        # Verify
        assert isinstance(message, SQSMessage)
        assert message.body == test_data
        assert message.message_id is not None
        assert message.receipt_handle is not None

    finally:
        await asyncio.gather(sink.stop(), source.stop())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sqs_stream_processing(sqs_config):
    """Test SQS stream processing."""
    # Create pipes
    sink = SQSSinkPipe(sqs_config)
    source = SQSSourcePipe(sqs_config)

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

        # Receive messages
        received = []
        async for message in source.process_stream():
            received.append(message.body)
            if len(received) == len(test_data):
                break

        # Verify
        assert len(received) == len(test_data)
        # Sort both lists by id to make comparison order-independent
        received.sort(key=lambda x: x["id"])
        test_data.sort(key=lambda x: x["id"])
        for expected, actual in zip(test_data, received):
            assert expected == actual

    finally:
        await asyncio.gather(sink.stop(), source.stop())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sqs_message_attributes(sqs_config):
    """Test SQS message attributes."""
    # Update config with message attributes
    sqs_config.message_attributes = {"Environment": "test", "Version": "1.0"}

    # Create pipes
    sink = SQSSinkPipe(sqs_config)
    source = SQSSourcePipe(sqs_config)

    # Test data
    test_data = {"key": "value"}

    try:
        # Send message
        await sink.start()
        await sink.process(test_data)
        await sink.stop()

        # Receive message
        await source.start()
        message = await source.process(None)
        await source.stop()

        # Verify message attributes
        assert message.message_attributes["Environment"]["StringValue"] == "test"
        assert message.message_attributes["Version"]["StringValue"] == "1.0"

    finally:
        await asyncio.gather(sink.stop(), source.stop())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sqs_error_handling(sqs_config):
    """Test SQS error handling."""
    # Create pipe with invalid config
    invalid_config = SQSConfig(
        queue_url="http://invalid:4566/000000000000/test-queue", region_name="us-east-1"
    )
    sink = SQSSinkPipe(invalid_config)

    # Verify error handling
    with pytest.raises(Exception):
        await sink.process({"key": "value"})
