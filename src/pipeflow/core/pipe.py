"""Base pipe interface and implementations."""
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

InputType = TypeVar("InputType")
OutputType = TypeVar("OutputType")
ConfigType = TypeVar("ConfigType", bound="PipeConfig")


class PipeError(Exception):
    """Error raised when a pipe fails to process data."""

    def __init__(self, pipe: "BasePipe[Any, Any]", cause: Exception) -> None:
        """Initialize pipe error.

        Args:
            pipe: Pipe that failed
            cause: Original exception
        """
        self.pipe = pipe
        self.cause = cause
        super().__init__(str(cause))


class PipeConfig(BaseModel):
    """Base configuration for pipes.

    All fields are optional to allow for flexible configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = None


class BasePipe(ABC, Generic[InputType, OutputType]):
    """Base class for all pipes.

    A pipe is a processing unit that takes input data and produces output data.
    Pipes can be composed into pipelines for more complex processing.
    """

    def __init__(self) -> None:
        """Initialize base pipe."""
        self.name: Optional[str] = None

    async def __call__(self, data: InputType) -> OutputType:
        """Process data through the pipe.

        Args:
            data: Input data

        Returns:
            Processed output data
        """
        return await self.process(data)

    @abstractmethod
    async def process(self, data: InputType) -> OutputType:
        """Process data through the pipe.

        Args:
            data: Input data

        Returns:
            Processed output data

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError("Pipe must implement process method")


class ConfigurablePipe(
    BasePipe[InputType, OutputType], Generic[InputType, OutputType, ConfigType]
):
    """Base class for configurable pipes.

    This is an abstract base class that provides configuration support.
    Subclasses must implement the process method.
    """

    def __init__(self, config: ConfigType) -> None:
        """Initialize configurable pipe.

        Args:
            config: Pipe configuration
        """
        super().__init__()
        self.config = config
        self.name: Optional[str] = config.name or self.__class__.__name__

    async def process(self, data: InputType) -> OutputType:
        """Process data through the pipe.

        Args:
            data: Input data

        Returns:
            Processed output data

        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError(
            f"Pipe {self.__class__.__name__} must implement process method"
        )
