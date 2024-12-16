"""Tests for stream processing functionality."""

import pytest
import asyncio
from datetime import timedelta

from pipeflow.core.pipe import PipeError
from pipeflow.streams.stream import StreamConfig


@pytest.mark.asyncio
async def test_stream_basic_processing(mock_stream, mock_pipe):
    """Test basic stream processing."""

    items = [1, 2, 3, 4, 5]
    pipe = mock_pipe(return_value=lambda x: x * 2)
    stream = mock_stream(items)

    results = []
    async for result in stream.process(pipe):
        results.append(result)

    # Verify
    assert results == [2, 4, 6, 8, 10]
    assert pipe.calls == items


@pytest.mark.asyncio
async def test_stream_batch_processing(mock_stream, mock_pipe):
    """Test batch processing."""

    items = list(range(10))
    config = StreamConfig(batch_size=3)
    stream = mock_stream(items, config=config)
    pipe = mock_pipe()

    batches = []
    async for batch in stream.process(pipe):
        batches.append(batch)

    assert len(batches) == 4
    assert len(batches[0]) == 3
    assert len(batches[-1]) == 1


@pytest.mark.asyncio
async def test_stream_window_processing(mock_stream, mock_pipe):
    """Test window-based processing."""

    items = list(range(10))
    config = StreamConfig(window_size=timedelta(seconds=0.1))
    stream = mock_stream(items, config=config, delay=0.05)
    pipe = mock_pipe()

    windows = []
    async for window in stream.process(pipe):
        windows.append(window)

    assert len(windows) > 1  # Ensure we have multiple windows
    assert all(isinstance(w, list) for w in windows)
    assert sum(len(w) for w in windows) == 10  # Total items processed
    
    # Check that each window contains the correct items
    flattened = [item for window in windows for item in window]
    assert flattened == items


@pytest.mark.asyncio
async def test_stream_error_handling(mock_stream, mock_pipe):
    """Test error handling and retries."""

    items = [1, 2, 3]
    error = ValueError("Test error")
    config = StreamConfig(retry_attempts=2, retry_delay=0.1)
    stream = mock_stream(items, config=config)
    pipe = mock_pipe(error=error)

    with pytest.raises(PipeError) as exc_info:
        async for _ in stream.process(pipe):
            pass

    assert isinstance(exc_info.value.__cause__, ValueError)
    assert len(pipe.calls) == 2


@pytest.mark.asyncio
async def test_stream_filtering(mock_stream):
    """Test stream filtering."""
    items = list(range(10))
    stream = mock_stream(items)

    results = []
    async for item in stream.filter(lambda x: x % 2 == 0):
        results.append(item)

    assert results == [0, 2, 4, 6, 8]


@pytest.mark.asyncio
async def test_stream_mapping(mock_stream):
    """Test stream mapping."""

    items = list(range(5))
    stream = mock_stream(items)

    results = []
    async for item in stream.map(lambda x: x * x):
        results.append(item)

    assert results == [0, 1, 4, 9, 16]


@pytest.mark.asyncio
async def test_stream_metrics(mock_stream, mock_pipe):
    """Test metrics collection."""

    items = list(range(5))
    stream = mock_stream(items)
    pipe = mock_pipe(delay=0.1)

    async for _ in stream.process(pipe):
        pass

    metrics = stream.metrics_dict()
    assert "buffer_size" in metrics
    assert "metrics" in metrics
    assert metrics["metrics"]["processing_time"]["avg"] is not None
