"""Tests for core pipe functionality."""
import pytest
from pydantic import ConfigDict

from pipeflow.core import BasePipe, ConfigurablePipe, PipeConfig


class PipeTestConfig(PipeConfig):
    """Test configuration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: str
    name: str = "test"


class SimplePipe(ConfigurablePipe[str, str, PipeTestConfig]):
    """Simple pipe implementation."""

    def __init__(self, config: PipeTestConfig):
        """Initialize simple pipe."""
        super().__init__(config)
        self.config = config

    async def process(self, data: str) -> str:
        """Process input data."""
        return data + self.config.value


@pytest.mark.asyncio
async def test_simple_pipe():
    """Test basic pipe functionality."""
    config = PipeTestConfig(value=" world", name="test")
    pipe = SimplePipe(config)

    result = await pipe("hello")
    assert result == "hello world"


@pytest.mark.asyncio
async def test_pipe_error_handling():
    """Test pipe error handling."""

    class ErrorPipe(BasePipe[str, str]):
        """Pipe that raises an error."""

        def __init__(self):
            """Initialize error pipe."""
            super().__init__()

        async def process(self, data: str) -> str:
            """Process input data."""
            raise ValueError("test error")

        async def __call__(self, data: str) -> str:
            """Call the pipe."""
            return await self.process(data)

    pipe = ErrorPipe()
    with pytest.raises(ValueError, match="test error"):
        await pipe.process("test")
