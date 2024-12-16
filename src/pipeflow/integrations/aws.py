"""AWS integrations for Pipeflow."""
import asyncio
import json
from typing import Any, AsyncIterator, Dict, Optional

import aioboto3
from pydantic import BaseModel

from pipeflow.core import ConfigurablePipe, PipeConfig


class SQSConfig(PipeConfig):
    """Configuration for SQS pipes."""

    queue_url: str
    region_name: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None
    max_messages: int = 10
    wait_time_seconds: int = 20
    visibility_timeout: int = 30
    message_attributes: Optional[Dict[str, str]] = None


class SQSMessage(BaseModel):
    """A message from SQS."""

    message_id: str
    body: Any
    receipt_handle: str
    attributes: Dict[str, Any] = {}
    message_attributes: Dict[str, Any] = {}


class SQSSourcePipe(ConfigurablePipe[None, SQSMessage, SQSConfig]):
    """Pipe that reads messages from SQS."""

    def __init__(self, config: SQSConfig) -> None:
        """Initialize the SQS source pipe.

        Args:
            config: SQS configuration
        """
        super().__init__(config)
        self.config = config
        self._session = aioboto3.Session(
            aws_access_key_id=config.aws_access_key_id or "test",
            aws_secret_access_key=config.aws_secret_access_key or "test",
            region_name=config.region_name,
        )
        self._client: Optional[Any] = None

    async def start(self) -> None:
        """Start the SQS client."""
        if self._client is None:
            self._client = await self._session.client(
                "sqs",
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region_name,
                aws_access_key_id=self.config.aws_access_key_id or "test",
                aws_secret_access_key=self.config.aws_secret_access_key or "test",
            ).__aenter__()

    async def stop(self) -> None:
        """Stop the SQS client."""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def process(self, _: None) -> Optional[SQSMessage]:
        """Process a single message from SQS.

        This method is not typically used directly. Use process_stream instead.

        Args:
            _: Not used

        Returns:
            A message from SQS if available, None otherwise

        Raises:
            ValueError: If no message is available
        """
        if self._client is None:
            await self.start()

        if not self._client:
            return None

        response = await self._client.receive_message(
            QueueUrl=self.config.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=self.config.wait_time_seconds,
            VisibilityTimeout=self.config.visibility_timeout,
            MessageAttributeNames=["All"],
        )

        if "Messages" in response:
            message = response["Messages"][0]
            message_attributes: Dict[str, Dict[str, str]] = {}
            raw_attrs = message.get("MessageAttributes", {})
            for key, attr in raw_attrs.items():
                message_attributes[key] = {
                    "StringValue": attr["StringValue"],
                    "DataType": attr["DataType"],
                }

            return SQSMessage(
                message_id=message["MessageId"],
                body=json.loads(message["Body"]),
                receipt_handle=message["ReceiptHandle"],
                attributes=message.get("Attributes", {}),
                message_attributes=message_attributes,
            )
        return None


    async def process_stream(self) -> AsyncIterator[SQSMessage]:
        """Process a stream of messages from SQS.

        Yields:
            Messages from SQS
        """
        if self._client is None:
            await self.start()

        try:
            while True:
                try:
                    message = await self.process(None)
                    if message is not None:
                        yield message

                        # Delete the message after processing
                        if self._client:
                            await self._client.delete_message(
                                QueueUrl=self.config.queue_url,
                                ReceiptHandle=message.receipt_handle,
                            )
                except ValueError:
                    await asyncio.sleep(0.1)
        finally:
            await self.stop()


class SQSSinkPipe(ConfigurablePipe[Any, None, SQSConfig]):
    """Pipe that writes messages to SQS."""

    def __init__(self, config: SQSConfig) -> None:
        """Initialize the SQS sink pipe.

        Args:
            config: SQS configuration
        """
        super().__init__(config)
        self.config = config
        self._session = aioboto3.Session(
            aws_access_key_id=config.aws_access_key_id or "test",
            aws_secret_access_key=config.aws_secret_access_key or "test",
            region_name=config.region_name,
        )
        self._client: Optional[Any] = None

    async def start(self) -> None:
        """Start the SQS client."""
        if self._client is None:
            self._client = await self._session.client(
                "sqs",
                endpoint_url=self.config.endpoint_url,
                region_name=self.config.region_name,
                aws_access_key_id=self.config.aws_access_key_id or "test",
                aws_secret_access_key=self.config.aws_secret_access_key or "test",
            ).__aenter__()

    async def stop(self) -> None:
        """Stop the SQS client."""
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def process(self, data: Any) -> None:
        """Send a message to SQS.

        Args:
            data: Message to send
        """
        if self._client is None:
            await self.start()

        if not self._client:
            return None

        message_attributes: Dict[str, Dict[str, str]] = {}
        if self.config.message_attributes:
            for key, value in self.config.message_attributes.items():
                message_attributes[key] = {"DataType": "String", "StringValue": value}

        await self._client.send_message(
            QueueUrl=self.config.queue_url,
            MessageBody=json.dumps(data),
            MessageAttributes=message_attributes,
        )
