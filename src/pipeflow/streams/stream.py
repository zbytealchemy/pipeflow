"""Stream processing implementation."""
import asyncio
import logging
import time
from datetime import timedelta
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
)

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from pipeflow.core import BasePipe, PipeError
from pipeflow.monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

T = TypeVar("T")
BatchT = TypeVar("BatchT", bound=List[Any])


class StreamConfig(BaseModel):
    """Configuration for streams.

    All fields are optional to allow for flexible configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = None
    retry_attempts: int = 3
    retry_delay: float = 1.0
    timeout: float = 30.0  # Default to 30 seconds timeout
    batch_size: int = 1  # default to 1
    window_size: timedelta = timedelta(minutes=0)

    @field_validator("batch_size", mode="before")
    def set_default_batch_size(cls, value):
        if value is None:
            return 1
        if not isinstance(value, int) or value < 1:
            raise ValueError(
                "batch_size must be an integer greater than or equal to 1."
            )
        return value

    @field_validator("window_size", mode="before")
    def convert_window_size(cls, value):
        if isinstance(value, (int, float)):  # If float or int, interpret as seconds
            if value < 0:
                raise ValueError("window_size must be greater than or equal to 0.")
            return timedelta(minutes=value)
        if isinstance(value, timedelta):
            if value < timedelta(minutes=0):
                raise ValueError("window_size must be greater than or equal to 0.")
            return value
        raise ValueError("window_size must be a float or a timedelta.")

    @model_validator(mode="after")
    def validate_model(cls, values):
        # Ensure all fields are properly validated
        batch_size = values.batch_size
        window_size = values.window_size
        if batch_size is None or batch_size < 1:
            raise ValueError(
                "batch_size must be an integer greater than or equal to 1."
            )
        if not isinstance(window_size, timedelta) or window_size < timedelta(seconds=0):
            raise ValueError("window_size must be a positive timedelta.")
        return values


def get_stream_config_defaults() -> StreamConfig:
    """Get default values for stream configuration."""
    return StreamConfig()


class Stream(Generic[T]):
    """A stream of data that can be processed through a pipeline."""

    def __init__(
        self,
        source: AsyncIterator[T],
        config: Optional[StreamConfig] = None,
        metrics: Optional[MetricsCollector] = None,
    ) -> None:
        """Initialize stream.

        Args:
            source: Source of data
            config: Stream configuration
            metrics: Metrics collector
        """
        self.source = source
        self.config = config or StreamConfig()
        self.metrics = metrics or MetricsCollector()
        self._buffer: List[T] = []
        self._window_buffer: List[T] = []
        self._last_window_time = time.time()

    async def process(
        self, pipe: BasePipe[Union[T, List[T]], Union[T, List[T]]]
    ) -> AsyncIterator[Union[T, List[T]]]:
        """Process the stream through the pipeline.

        Args:
            pipe: Pipeline to process data through

        Yields:
            Single items for basic processing, batches/windows for batch/window processing

        Raises:
            PipeError: If processing fails
        """
        if self.config.batch_size > 1:
            batch_pipe = cast(BasePipe[List[T], List[T]], pipe)
            async for batch in self._process_batches(batch_pipe):
                yield batch
        elif self.config.window_size.total_seconds() > 0:
            window_pipe = cast(BasePipe[List[T], List[T]], pipe)
            async for window in self._process_windows(window_pipe):
                yield window
        else:
            async for item in self.source:
                try:
                    result = await self._process_item(pipe, item)
                    yield result
                except PipeError as e:
                    logger.error("Failed to process stream item: %s", str(e))
                    raise

    async def _process_item(
        self, pipe: BasePipe[Union[T, List[T]], Union[T, List[T]]], item: T
    ) -> Union[T, List[T]]:
        """Process a single item through the pipeline with retries.

        Args:
            pipe: Pipeline to process data through
            item: Item to process

        Returns:
            Processed item

        Raises:
            PipeError: If processing fails after retries
        """
        attempts = 0
        last_error = None

        while attempts < self.config.retry_attempts:
            start_time = time.time()
            try:
                if self.config.timeout:
                    result = await asyncio.wait_for(
                        pipe(item), timeout=self.config.timeout
                    )
                else:
                    result = await pipe(item)
                self.metrics.record_success()
                return result
            except Exception as e:
                last_error = e
                self.metrics.record_error()
                if attempts == self.config.retry_attempts - 1:
                    raise PipeError(pipe, last_error) from last_error
                attempts += 1
                await asyncio.sleep(self.config.retry_delay * attempts)
            finally:
                elapsed = time.time() - start_time
                self.metrics.record_processing_time(elapsed)

        raise PipeError(pipe, last_error) if last_error else RuntimeError(
            "Unexpected error in _process_item"
        )

    async def _process_batches(
        self, pipe: BasePipe[List[T], List[T]]
    ) -> AsyncIterator[List[T]]:
        """Process items in batches.

        Args:
            pipe: Pipeline to process data through

        Yields:
            Processed batches
        """
        batch: List[T] = []
        batch_size = self.config.batch_size
        async for item in self.source:
            batch.append(item)
            if len(batch) >= batch_size:
                result = await pipe(batch)
                yield result
                batch = []

        if batch:
            result = await pipe(batch)
            yield result

    async def _process_windows(
        self, pipe: BasePipe[List[T], List[T]]
    ) -> AsyncIterator[List[T]]:
        """Process items in time-based windows.

        Args:
            pipe: Pipeline to process data through

        Yields:
            Processed windows
        """
        window: List[T] = []
        window_start = asyncio.get_event_loop().time()

        async for item in self.source:
            current_time = asyncio.get_event_loop().time()
            if current_time - window_start >= self.config.window_size.total_seconds():
                if window:
                    result = await pipe(window)
                    yield result
                    window = []
                window_start = current_time
            window.append(item)

        if window:
            result = await pipe(window)
            yield result

    async def filter(self, predicate: Callable[[T], bool]) -> AsyncIterator[T]:
        """Filter stream items.

        Args:
            predicate: Function to filter items

        Yields:
            Filtered items
        """
        async for item in self.source:
            if predicate(item):
                yield item

    async def map(self, func: Callable[[T], Any]) -> AsyncIterator[Any]:
        """Map function over stream items.

        Args:
            func: Function to apply to items

        Yields:
            Mapped items
        """
        async for item in self.source:
            yield func(item)

    def metrics_dict(self) -> Dict[str, Any]:
        """Get stream metrics.

        Returns:
            Dictionary containing metrics
        """
        return {
            "buffer_size": len(self._buffer),
            "window_buffer_size": len(self._window_buffer),
            "metrics": self.metrics.get_metrics(),
        }


class StreamProcessor:
    """Processes data streams through a pipeline with metrics collection.

    This class handles stream processing with support for:
    - Batching
    - Retries with backoff
    - Timeouts
    - Metrics collection
    """

    def __init__(
        self,
        pipeline: BasePipe[Any, Any],
        config: Optional[StreamConfig] = None,
        metrics: Optional[MetricsCollector] = None,
    ) -> None:
        """Initialize stream processor.

        Args:
            pipeline: Pipeline to process data through
            config: Optional stream configuration
            metrics: Optional metrics collector
        """
        self.pipeline = pipeline
        self.config = config or StreamConfig()
        self.metrics = metrics or MetricsCollector()

    async def process_stream(self, stream: AsyncIterator[Any]) -> AsyncIterator[Any]:
        """Process a stream of data through the pipeline.

        Args:
            stream: Input data stream

        Yields:
            Processed output data

        Raises:
            PipeError: If processing fails
        """
        logger.info("Starting stream processing with pipeline %s", self.pipeline.name)
        batch: List[Any] = []
        errors: List[Exception] = []

        try:
            async for item in stream:
                try:
                    if self.config.batch_size > 1:
                        batch.append(item)
                        if len(batch) >= self.config.batch_size:
                            async for result in self._process_batch(batch):
                                yield result
                            batch = []
                    else:
                        async for result in self._process_batch([item]):
                            yield result
                except PipeError as e:
                    errors.append(e)
                    logger.error(
                        "Failed to process stream item in pipeline %s: %s",
                        self.pipeline.name,
                        str(e),
                    )
                    raise

            # Process remaining items in the last batch
            if batch:
                async for result in self._process_batch(batch):
                    yield result

        except PipeError:
            raise
        except Exception as e:
            logger.error("Stream processing failed: %s", str(e))
            raise PipeError(self.pipeline, e) from e
        finally:
            if errors:
                logger.warning(
                    "Stream processing completed with %d errors", len(errors)
                )

    async def _process_batch(self, batch: List[Any]) -> AsyncIterator[Any]:
        """Process a batch of items with retries.

        Args:
            batch: List of items to process

        Yields:
            Processed items

        Raises:
            PipeError: If processing fails after max retries
        """
        for item in batch:
            retries = 0
            while True:
                try:
                    start_time = time.time()
                    if self.config.timeout:
                        result = await asyncio.wait_for(
                            self.pipeline(item), timeout=self.config.timeout
                        )
                    else:
                        result = await self.pipeline(item)

                    elapsed = time.time() - start_time
                    self.metrics.record_success()
                    self.metrics.record_processing_time(elapsed)
                    yield result
                    break

                except (asyncio.TimeoutError, Exception) as e:
                    retries += 1
                    if retries >= self.config.retry_attempts:
                        logger.error(
                            "Failed to process item after %d retries: %s",
                            self.config.retry_attempts,
                            str(e),
                        )
                        self.metrics.record_error()
                        raise PipeError(self.pipeline, e) from e

                    logger.warning(
                        "Retry %d/%d for item processing: %s",
                        retries,
                        self.config.retry_attempts,
                        str(e),
                    )
                    await asyncio.sleep(self.config.retry_delay * retries)
