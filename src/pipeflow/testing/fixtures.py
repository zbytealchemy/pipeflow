"""Test fixtures and utilities for Pipeflow."""
import asyncio
from datetime import datetime
from typing import Any, AsyncIterator, List, Optional, TypeVar

import pytest

from pipeflow.core.pipe import BasePipe
from pipeflow.streams.stream import Stream, StreamConfig

T = TypeVar("T")


class MockPipe(BasePipe[Any, Any]):
    """Mock pipe for testing."""

    def __init__(
        self,
        return_value: Any = None,
        error: Optional[Exception] = None,
        delay: float = 0,
    ):
        """Initialize mock pipe.

        Args:
            return_value: Value to return
            error: Error to raise
            delay: Processing delay in seconds
        """
        super().__init__()
        self.return_value = return_value
        self.error = error
        self.delay = delay
        self.calls: List[Any] = []

    async def process(self, data: Any) -> Any:
        """Process data through mock pipe."""
        self.calls.append(data)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.return_value if self.return_value is not None else data


async def mock_stream_source(items: List[T], delay: float = 0) -> AsyncIterator[T]:
    """Create a mock stream source.

    Args:
        items: Items to yield
        delay: Delay between items in seconds

    Yields:
        Items from the list
    """
    for item in items:
        if delay:
            await asyncio.sleep(delay)
        yield item


@pytest.fixture
def mock_pipe() -> Any:
    """Fixture for creating mock pipes."""

    def _create_mock_pipe(
        return_value: Any = None, error: Optional[Exception] = None, delay: float = 0
    ) -> MockPipe:
        return MockPipe(return_value, error, delay)

    return _create_mock_pipe


@pytest.fixture
def mock_stream() -> Any:
    """Fixture for creating mock streams."""

    def _create_mock_stream(
        items: List[Any], config: Optional[StreamConfig] = None, delay: float = 0
    ) -> Stream[Any]:
        return Stream(mock_stream_source(items, delay), config=config)

    return _create_mock_stream


@pytest.fixture
def assert_processing_time() -> Any:
    """Fixture for asserting processing time."""

    def _assert_processing_time(
        start_time: datetime, expected_duration: float, tolerance: float = 0.1
    ) -> None:
        duration = (datetime.now() - start_time).total_seconds()
        assert abs(duration - expected_duration) <= tolerance

    return _assert_processing_time
