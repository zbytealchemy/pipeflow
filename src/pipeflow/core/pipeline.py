"""Pipeline implementation for composing pipes."""
import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar, cast

from pipeflow.core.pipe import BasePipe, InputType, OutputType

T = TypeVar("T")


class Pipeline(BasePipe[InputType, OutputType]):
    """A pipeline that composes multiple pipes.

    Example:
        >>> pipe1 = SomePipe()
        >>> pipe2 = AnotherPipe()
        >>> pipeline = Pipeline([pipe1, pipe2])
        >>> result = await pipeline(input_data)
    """

    def __init__(
        self, pipes: List[BasePipe[Any, Any]], name: Optional[str] = None
    ) -> None:
        """Initialize pipeline.

        Args:
            pipes: List of pipes to compose
            name: Optional name for the pipeline
        """
        super().__init__()
        if not pipes:
            raise ValueError("Pipeline must contain at least one pipe")
        self.pipes = pipes
        self.name: str | None = name or "Pipeline"

    async def process(self, data: InputType) -> OutputType:
        """Process data through the pipeline.

        Args:
            data: Input data

        Returns:
            Processed output data
        """
        result: Any = data
        for pipe in self.pipes:
            if result is None:
                raise ValueError("Input data cannot be None")
            result = await pipe(result)
        return cast(OutputType, result)

    async def execute_parallel(self, data: List[Any]) -> List[Any]:
        """Execute the pipeline on multiple inputs in parallel.

        Args:
            data: List of input data

        Returns:
            List of processed results

        Raises:
            PipeError: If any pipe fails
        """
        tasks: List[Awaitable[Any]] = [self.process(item) for item in data]
        return await asyncio.gather(*tasks)

    async def execute_conditional(
        self, data: Any, condition: Callable[[Any], bool]
    ) -> Any:
        """Execute the pipeline only if condition is met.

        Args:
            data: Input data
            condition: Function that returns True if pipeline should execute

        Returns:
            Processed data if condition is met, otherwise original data
        """
        if condition(data):
            return await self.process(data)
        return data

    async def process_stream(
        self, stream: Any, batch_size: Optional[int] = None
    ) -> Any:
        """Process a stream of data through the pipeline.

        Args:
            stream: Input data stream
            batch_size: Optional batch size for parallel processing

        Yields:
            Processed data items
        """
        if batch_size:
            batch: List[Any] = []
            async for item in stream:
                batch.append(item)
                if len(batch) >= batch_size:
                    results = await self.execute_parallel(batch)
                    for result in results:
                        yield result
                    batch = []

            if batch:
                results = await self.execute_parallel(batch)
                for result in results:
                    yield result
        else:
            async for item in stream:
                result = await self.process(item)
                yield result

    def __rshift__(
        self, other: BasePipe[Any, Any]
    ) -> "Pipeline[InputType, OutputType]":
        """Compose this pipeline with another pipe using the >> operator."""
        return Pipeline(self.pipes + [other])

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from all pipes in the pipeline."""
        metrics: Dict[str, Any] = {}
        for pipe in self.pipes:
            if (
                hasattr(pipe, "name")
                and hasattr(pipe, "metrics")
                and pipe.name is not None
            ):
                metrics[pipe.name] = pipe.metrics.to_dict()
        return metrics
